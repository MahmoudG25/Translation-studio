"""
Simplified batch processing for sequential and parallel translation of multiple files.
"""

import os
import time
from typing import Dict, List, Callable, Optional
from PySide6.QtCore import QThread, Signal

from batch_processor import TranslationJob, TranslationStatus


class SimpleBatchProcessor(QThread):
    """
    Simplified batch processor that handles multiple jobs sequentially.
    Emits signals for UI updates.
    """
    
    job_started = Signal(str)           # job_id
    job_progress = Signal(str, int, str)  # job_id, progress, message
    job_completed = Signal(str, str)    # job_id, output_path
    job_failed = Signal(str, str)       # job_id, error_message
    batch_progress = Signal(dict)       # stats
    batch_finished = Signal(dict)       # final stats
    
    def __init__(self, jobs: List[TranslationJob], 
                 executor: Callable[[TranslationJob], bool]):
        super().__init__()
        self.jobs = jobs
        self.executor = executor
        self.is_running = False
    
    def run(self):
        """Process all jobs sequentially."""
        self.is_running = True
        completed = 0
        failed = 0
        
        try:
            for job_index, job in enumerate(self.jobs):
                if not self.is_running:
                    break
                
                # Mark job as running
                job.status = TranslationStatus.RUNNING
                job.progress = 0
                self.job_started.emit(job.job_id)
                
                # Create callbacks for this job (must capture job properly)
                current_job = job  # Capture job in current scope to avoid closure issues
                
                def make_on_progress(current_job):
                    def on_progress(progress: int, message: str = ""):
                        self.job_progress.emit(current_job.job_id, progress, message)
                    return on_progress
                
                def make_on_completed(current_job):
                    def on_completed(output_path: Optional[str] = None):
                        current_job.status = TranslationStatus.COMPLETED
                        self.job_completed.emit(current_job.job_id, output_path or "")
                    return on_completed
                
                def make_on_failed(current_job):
                    def on_failed(error: str):
                        current_job.status = TranslationStatus.FAILED
                        self.job_failed.emit(current_job.job_id, error)
                        current_job.config['error_emitted'] = True
                    return on_failed
                
                # Store callbacks in job config
                current_job.config['_on_progress'] = make_on_progress(current_job)
                current_job.config['_on_completed'] = make_on_completed(current_job)
                current_job.config['_on_failed'] = make_on_failed(current_job)
                
                try:
                    # Execute the translation
                    success = self.executor(current_job)
                    
                    if success:
                        if current_job.status != TranslationStatus.COMPLETED:  # Callback may have set this
                            current_job.status = TranslationStatus.COMPLETED
                        completed += 1
                    else:
                        current_job.status = TranslationStatus.FAILED
                        failed += 1
                        # Only emit if callback didn't already
                        if 'error_emitted' not in current_job.config or not current_job.config['error_emitted']:
                            self.job_failed.emit(current_job.job_id, "Translation failed")
                        
                except Exception as e:
                    current_job.status = TranslationStatus.FAILED
                    failed += 1
                    self.job_failed.emit(current_job.job_id, str(e))
                
                # Emit progress
                stats = {
                    "total": len(self.jobs),
                    "completed": completed,
                    "failed": failed,
                    "current": job_index + 1
                }
                self.batch_progress.emit(stats)
        
        finally:
            self.is_running = False
            final_stats = {
                "total": len(self.jobs),
                "completed": completed,
                "failed": failed
            }
            self.batch_finished.emit(final_stats)
    
    def stop(self):
        """Stop processing."""
        self.is_running = False
        self.wait(timeout=5000)


