#!/usr/bin/env python3
"""
Test script for batch processing functionality.
"""

import sys
import os
from pathlib import Path

# Add the workspace directory to path
workspace_dir = Path(__file__).parent
sys.path.insert(0, str(workspace_dir))

# Import only batch processing modules, NOT main.py
from batch_processor import TranslationJob, TranslationStatus
from simple_batch import SimpleBatchProcessor

def mock_executor(job: TranslationJob) -> bool:
    """Mock executor that simulates translation."""
    print("  Executing: {}".format(job.file_path))
    
    # Get callbacks
    on_progress = job.config.get('_on_progress', lambda *args: None)
    on_completed = job.config.get('_on_completed', lambda *args: None)
    
    # Simulate progress updates
    on_progress(25, "Reading file...")
    on_progress(50, "Translating...")
    on_progress(75, "Saving...")
    
    # Create mock output file
    output_path = job.file_path.replace('.srt', '.ar.srt')
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("1\n00:00:01,000 --> 00:00:05,000\nMocking translation\n")
    except Exception as e:
        print("  Error writing file: {}".format(e))
        return False
    
    on_completed(output_path)
    return True

def test_batch_processing():
    """Test batch processing with multiple files."""
    print("="*70)
    print("BATCH PROCESSING TEST")
    print("="*70)
    
    # Create test jobs
    test_files = [
        Path(workspace_dir) / "test1.srt",
        Path(workspace_dir) / "test2.srt", 
        Path(workspace_dir) / "test3.srt"
    ]
    
    # Verify test files exist
    for test_file in test_files:
        if not test_file.exists():
            print("WARNING: Test file not found: {}".format(test_file))
            return False
    
    jobs = []
    for test_file in test_files:
        job = TranslationJob(
            file_path=str(test_file),
            engine='ARGOS',
            config={'_on_progress': None, '_on_completed': None, '_on_failed': None}
        )
        jobs.append(job)
        print("Created job for: {}".format(test_file.name))
    
    print("\nTotal jobs: {}".format(len(jobs)))
    print("=" * 70)
    
    # Track results
    results = {
        'started': [],
        'progressed': [],
        'completed': [],
        'failed': [],
        'batch_progress': [],
        'batch_finished': None
    }
    
    # Create signal handlers
    def on_started(job_id):
        results['started'].append(job_id)
        print("  Job started: {}".format(job_id))
    
    def on_progress(job_id, progress, message):
        results['progressed'].append((job_id, progress, message))
        print("    Progress {}: {}% - {}".format(job_id, progress, message))
    
    def on_completed(job_id, output_path):
        results['completed'].append((job_id, output_path))
        print("  Job completed: {} -> {}".format(job_id, output_path))
    
    def on_failed(job_id, error):
        results['failed'].append((job_id, error))
        print("  Job failed: {} - {}".format(job_id, error))
    
    def on_batch_progress(stats):
        results['batch_progress'].append(stats)
        total = stats.get('total', 0)
        completed = stats.get('completed', 0)
        failed = stats.get('failed', 0)
        print("Batch Progress: {}/{} completed, {} failed".format(completed, total, failed))
    
    def on_batch_finished(final_stats):
        results['batch_finished'] = final_stats
        total = final_stats.get('total', 0)
        completed = final_stats.get('completed', 0)
        failed = final_stats.get('failed', 0)
        print("\nBatch finished: {}/{} completed, {} failed".format(completed, total, failed))
    
    # Create processor
    processor = SimpleBatchProcessor(jobs, mock_executor)
    
    # Connect signals
    processor.job_started.connect(on_started)
    processor.job_progress.connect(on_progress)
    processor.job_completed.connect(on_completed)
    processor.job_failed.connect(on_failed)
    processor.batch_progress.connect(on_batch_progress)
    processor.batch_finished.connect(on_batch_finished)
    
    # Start processing
    print("\nStarting batch processor...\n")
    processor.start()
    processor.wait()  # Wait for thread to finish
    
    # Print results
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)
    print("Jobs started: {}".format(len(results['started'])))
    print("Jobs completed: {}".format(len(results['completed'])))
    print("Jobs failed: {}".format(len(results['failed'])))
    print("Batch progress updates: {}".format(len(results['batch_progress'])))
    print("Batch finished: {}".format(results['batch_finished'] is not None))
    
    # Verify outputs exist
    print("\n" + "="*70)
    print("OUTPUT VERIFICATION")
    print("="*70)
    output_files = [
        Path(workspace_dir) / "test1.ar.srt",
        Path(workspace_dir) / "test2.ar.srt",
        Path(workspace_dir) / "test3.ar.srt"
    ]
    
    for output_file in output_files:
        if output_file.exists():
            size = output_file.stat().st_size
            print("FOUND: {} ({} bytes)".format(output_file.name, size))
        else:
            print("MISSING: {}".format(output_file.name))
    
    # Summary
    print("\n" + "="*70)
    if len(results['completed']) == len(jobs) and len(results['failed']) == 0:
        print("ALL TESTS PASSED!")
        return True
    else:
        print("TESTS FAILED!")
        return False

if __name__ == '__main__':
    success = test_batch_processing()
    sys.exit(0 if success else 1)

