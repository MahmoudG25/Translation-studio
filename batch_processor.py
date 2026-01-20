"""
Batch processing system for handling multiple file translations simultaneously.
Manages queues, scheduling, and parallel execution.
"""

import os
from pathlib import Path
from typing import List, Dict, Callable, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import threading


class TranslationEngineType(Enum):
    """Supported translation engines."""
    WHISPER = "whisper"
    ARGOS = "argos"
    CHATGPT = "chatgpt"


class TranslationStatus(Enum):
    """Status of a translation job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TranslationJob:
    """Single file translation job."""
    file_path: str
    engine: TranslationEngineType
    job_id: str = field(default_factory=lambda: str(datetime.now().timestamp()))
    status: TranslationStatus = TranslationStatus.PENDING
    progress: int = 0
    message: str = ""
    output_path: Optional[str] = None
    config: Dict = field(default_factory=dict)  # Engine-specific config (model, api_key, etc.)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert job to dictionary."""
        return {
            "job_id": self.job_id,
            "file_path": self.file_path,
            "engine": self.engine.value,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "output_path": self.output_path,
            "config": self.config,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }


class BatchTranslationQueue:
    """Manages a queue of translation jobs."""

    def __init__(self, max_parallel_jobs: int = 2):
        """
        Initialize batch translation queue.
        
        Args:
            max_parallel_jobs: Maximum number of simultaneous translations
        """
        self.max_parallel_jobs = max_parallel_jobs
        self.jobs: List[TranslationJob] = []
        self.active_jobs: Dict[str, TranslationJob] = {}
        self.completed_jobs: List[TranslationJob] = []
        self.failed_jobs: List[TranslationJob] = []
        self.lock = threading.RLock()

    def add_job(self, file_path: str, engine: TranslationEngineType, 
                config: Optional[Dict] = None) -> TranslationJob:
        """
        Add a file to the translation queue.
        
        Args:
            file_path: Path to file to translate
            engine: Translation engine to use
            config: Engine-specific configuration
            
        Returns:
            TranslationJob object
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with self.lock:
            job = TranslationJob(
                file_path=file_path,
                engine=engine,
                config=config or {}
            )
            self.jobs.append(job)
            return job

    def add_multiple_jobs(self, file_paths: List[str], 
                         engine: TranslationEngineType,
                         config: Optional[Dict] = None) -> List[TranslationJob]:
        """
        Add multiple files to the queue at once.
        
        Args:
            file_paths: List of file paths
            engine: Translation engine to use
            config: Engine-specific configuration
            
        Returns:
            List of TranslationJob objects
        """
        jobs = []
        for file_path in file_paths:
            try:
                job = self.add_job(file_path, engine, config)
                jobs.append(job)
            except FileNotFoundError as e:
                # Log but continue with other files
                print(f"Skipping: {e}")
        return jobs

    def get_pending_jobs(self) -> List[TranslationJob]:
        """Get all pending jobs."""
        with self.lock:
            return [job for job in self.jobs if job.status == TranslationStatus.PENDING]

    def get_next_job(self) -> Optional[TranslationJob]:
        """Get next pending job if queue capacity allows."""
        with self.lock:
            if len(self.active_jobs) < self.max_parallel_jobs:
                # Get pending jobs without acquiring lock again
                pending = [job for job in self.jobs if job.status == TranslationStatus.PENDING]
                if pending:
                    return pending[0]
        return None

    def mark_started(self, job_id: str):
        """Mark a job as started."""
        with self.lock:
            for job in self.jobs:
                if job.job_id == job_id:
                    job.status = TranslationStatus.RUNNING
                    job.started_at = datetime.now().isoformat()
                    self.active_jobs[job_id] = job
                    break

    def update_progress(self, job_id: str, progress: int, message: str = ""):
        """Update job progress."""
        with self.lock:
            for job in self.jobs:
                if job.job_id == job_id:
                    job.progress = min(100, max(0, progress))
                    if message:
                        job.message = message
                    break

    def mark_completed(self, job_id: str, output_path: Optional[str] = None, 
                      message: str = ""):
        """Mark job as completed successfully."""
        with self.lock:
            for job in self.jobs:
                if job.job_id == job_id:
                    job.status = TranslationStatus.COMPLETED
                    job.progress = 100
                    job.completed_at = datetime.now().isoformat()
                    job.output_path = output_path
                    if message:
                        job.message = message
                    self.completed_jobs.append(job)
                    self.active_jobs.pop(job_id, None)
                    break

    def mark_failed(self, job_id: str, error_message: str = ""):
        """Mark job as failed."""
        with self.lock:
            for job in self.jobs:
                if job.job_id == job_id:
                    job.status = TranslationStatus.FAILED
                    job.completed_at = datetime.now().isoformat()
                    if error_message:
                        job.message = error_message
                    self.failed_jobs.append(job)
                    self.active_jobs.pop(job_id, None)
                    break

    def mark_skipped(self, job_id: str, reason: str = ""):
        """Mark job as skipped."""
        with self.lock:
            for job in self.jobs:
                if job.job_id == job_id:
                    job.status = TranslationStatus.SKIPPED
                    job.completed_at = datetime.now().isoformat()
                    if reason:
                        job.message = reason
                    self.active_jobs.pop(job_id, None)
                    break

    def get_job(self, job_id: str) -> Optional[TranslationJob]:
        """Get job by ID."""
        with self.lock:
            for job in self.jobs:
                if job.job_id == job_id:
                    return job
        return None

    def get_all_jobs(self) -> List[TranslationJob]:
        """Get all jobs in order added."""
        with self.lock:
            return self.jobs.copy()

    def get_active_jobs(self) -> Dict[str, TranslationJob]:
        """Get all currently active (running) jobs."""
        with self.lock:
            return self.active_jobs.copy()

    def get_statistics(self) -> Dict:
        """Get queue statistics."""
        with self.lock:
            # Count pending jobs without acquiring lock again
            pending_count = len([job for job in self.jobs if job.status == TranslationStatus.PENDING])
            return {
                "total_jobs": len(self.jobs),
                "pending": pending_count,
                "active": len(self.active_jobs),
                "completed": len(self.completed_jobs),
                "failed": len(self.failed_jobs),
                "capacity": self.max_parallel_jobs
            }

    def clear_completed(self):
        """Clear completed jobs from history."""
        with self.lock:
            self.completed_jobs.clear()
            self.failed_jobs.clear()

    def get_progress_summary(self) -> Dict:
        """Get overall progress summary."""
        with self.lock:
            total = len(self.jobs)
            if total == 0:
                return {"percentage": 0, "completed": 0, "total": 0}
            
            completed = len(self.completed_jobs)
            total_progress = sum(job.progress for job in self.jobs)
            avg_progress = total_progress / total if total > 0 else 0
            
            return {
                "percentage": int(avg_progress),
                "completed": completed,
                "total": total,
                "active": len(self.active_jobs)
            }
