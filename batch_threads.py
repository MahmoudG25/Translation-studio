"""
Batch translation threads for parallel file processing.
Extends single-file translation threads to work with batch queue.
"""

import os
import time
from typing import Optional, Dict, Callable
from PySide6.QtCore import QThread, Signal, QMutex, QWaitCondition

from batch_processor import (
    BatchTranslationQueue, TranslationJob, TranslationEngineType,
    TranslationStatus
)


class BatchTranslationManager(QThread):
    """
    Manages parallel translation of multiple files.
    Processes jobs from queue, respecting max parallel limit.
    """
    
    job_started = Signal(str)  # job_id
    job_progress = Signal(str, int, str)  # job_id, progress, message
    job_completed = Signal(str, str)  # job_id, output_path
    job_failed = Signal(str, str)  # job_id, error_message
    queue_updated = Signal(dict)  # stats dict
    all_jobs_completed = Signal(dict)  # final stats
    
    def __init__(self, queue: BatchTranslationQueue, 
                 execute_callback: Callable[[TranslationJob], bool]):
        """
        Initialize batch translation manager.
        
        Args:
            queue: BatchTranslationQueue to process
            execute_callback: Function to execute single job
                             Should return True on success, False on failure
                             Callback responsible for emitting signals
        """
        super().__init__()
        self.queue = queue
        self.execute_callback = execute_callback
        self.is_running = False
        self.active_threads: Dict[str, QThread] = {}
        self.mutex = QMutex()

    def run(self):
        """Process all jobs in queue with concurrency control."""
        self.is_running = True
        self.active_threads.clear()

        try:
            while self.is_running:
                # Check for completed threads
                self.mutex.lock()
                try:
                    completed_ids = []
                    for job_id, thread in list(self.active_threads.items()):
                        if not thread.isRunning():
                            completed_ids.append(job_id)
                    
                    # Remove completed threads
                    for job_id in completed_ids:
                        self.active_threads.pop(job_id, None)
                finally:
                    self.mutex.unlock()

                # Start new jobs if capacity available
                while self.is_running and len(self.active_threads) < self.queue.max_parallel_jobs:
                    next_job = self.queue.get_next_job()
                    if not next_job:
                        break

                    self.queue.mark_started(next_job.job_id)
                    self.job_started.emit(next_job.job_id)

                    # Create worker thread for this job
                    worker = SingleJobWorker(
                        next_job,
                        self.execute_callback,
                        self.queue
                    )
                    worker.progress.connect(self._on_job_progress, type=1)  # Qt.AutoConnection
                    worker.completed.connect(self._on_job_completed, type=1)
                    worker.failed.connect(self._on_job_failed, type=1)
                    worker.start()

                    self.mutex.lock()
                    try:
                        self.active_threads[next_job.job_id] = worker
                    finally:
                        self.mutex.unlock()

                # Update queue status
                stats = self.queue.get_statistics()
                self.queue_updated.emit(stats)

                # Check if all jobs are done
                pending = self.queue.get_pending_jobs()
                if not self.active_threads and not pending:
                    break

                # Allow other threads to run
                time.sleep(0.2)

        finally:
            self.is_running = False
            # Wait for all active threads to finish
            self.mutex.lock()
            try:
                for thread in self.active_threads.values():
                    if thread.isRunning():
                        thread.wait(timeout=5000)
            finally:
                self.mutex.unlock()
            
            final_stats = self.queue.get_statistics()
            self.all_jobs_completed.emit(final_stats)

    def stop(self):
        """Stop processing."""
        self.is_running = False
        self.wait()

    def _on_job_progress(self, job_id: str, progress: int, message: str):
        """Handle job progress update."""
        self.queue.update_progress(job_id, progress, message)
        self.job_progress.emit(job_id, progress, message)
        self.queue_updated.emit(self.queue.get_statistics())

    def _on_job_completed(self, job_id: str, output_path: str):
        """Handle job completion."""
        self.queue.mark_completed(job_id, output_path)
        self.job_completed.emit(job_id, output_path)
        self.queue_updated.emit(self.queue.get_statistics())

    def _on_job_failed(self, job_id: str, error_message: str):
        """Handle job failure."""
        self.queue.mark_failed(job_id, error_message)
        self.job_failed.emit(job_id, error_message)
        self.queue_updated.emit(self.queue.get_statistics())


class SingleJobWorker(QThread):
    """Worker thread for processing a single translation job."""
    
    progress = Signal(str, int, str)  # job_id, progress, message
    completed = Signal(str, str)  # job_id, output_path
    failed = Signal(str, str)  # job_id, error_message

    def __init__(self, job: TranslationJob, 
                 execute_callback: Callable[[TranslationJob], bool],
                 queue: BatchTranslationQueue):
        super().__init__()
        self.job = job
        self.execute_callback = execute_callback
        self.queue = queue

    def run(self):
        """Execute the translation job."""
        try:
            # Create callback proxies to emit signals
            def on_progress(progress: int, message: str):
                self.progress.emit(self.job.job_id, progress, message)

            def on_completed(output_path: Optional[str] = None):
                # Always emit completion signal, even if output_path is None
                self.completed.emit(self.job.job_id, output_path or "")

            def on_failed(error_message: str):
                self.failed.emit(self.job.job_id, error_message)

            # Store callbacks in job for executor to use
            self.job.config['_on_progress'] = on_progress
            self.job.config['_on_completed'] = on_completed
            self.job.config['_on_failed'] = on_failed

            # Execute the translation
            success = self.execute_callback(self.job)

            if not success:
                self.failed.emit(self.job.job_id, "Translation failed")

        except Exception as e:
            self.failed.emit(self.job.job_id, str(e))


class MultiFileBatchProcessor:
    """
    High-level interface for batch translation.
    Handles engine selection and job creation.
    """

    def __init__(self, max_parallel: int = 2):
        """Initialize batch processor."""
        self.queue = BatchTranslationQueue(max_parallel)
        self.manager: Optional[BatchTranslationManager] = None
        self.execute_callback: Optional[Callable] = None

    def add_files(self, file_paths: list, engine: str, config: Optional[Dict] = None) -> list:
        """
        Add multiple files for translation.
        
        Args:
            file_paths: List of file paths
            engine: Engine type ("whisper", "argos", "chatgpt")
            config: Engine configuration
            
        Returns:
            List of job IDs
        """
        try:
            engine_type = TranslationEngineType[engine.upper()]
        except KeyError:
            raise ValueError(f"Unknown engine: {engine}")

        jobs = self.queue.add_multiple_jobs(file_paths, engine_type, config)
        return [job.job_id for job in jobs]

    def start_processing(self, execute_callback: Callable) -> BatchTranslationManager:
        """
        Start processing jobs in queue.
        
        Args:
            execute_callback: Function to execute single job
            
        Returns:
            BatchTranslationManager thread
        """
        if self.manager and self.manager.isRunning():
            raise RuntimeError("Processing already in progress")

        self.execute_callback = execute_callback
        self.manager = BatchTranslationManager(self.queue, execute_callback)
        self.manager.start()
        return self.manager

    def stop_processing(self):
        """Stop current processing."""
        if self.manager:
            self.manager.stop()

    def get_queue(self) -> BatchTranslationQueue:
        """Get the translation queue."""
        return self.queue

    def get_statistics(self) -> Dict:
        """Get current queue statistics."""
        return self.queue.get_statistics()
