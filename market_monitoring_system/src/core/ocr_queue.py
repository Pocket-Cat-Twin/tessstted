"""
OCR processing queue for market monitoring system.
Handles asynchronous OCR requests with priority queuing and retry logic.
"""

import logging
import threading
import queue
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class OCRJobStatus(Enum):
    """Status of OCR processing job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OCRJobPriority(Enum):
    """Priority levels for OCR jobs."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class OCRJob:
    """OCR processing job."""
    job_id: str
    image_path: Path
    hotkey: str
    priority: OCRJobPriority = OCRJobPriority.NORMAL
    language_codes: Optional[List[str]] = None
    cleanup_image: bool = True
    callback: Optional[Callable] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: OCRJobStatus = OCRJobStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    result: Optional[str] = None
    error: Optional[str] = None
    
    def __lt__(self, other):
        """Compare jobs for priority queue ordering."""
        if not isinstance(other, OCRJob):
            return NotImplemented
        # Higher priority values come first, then older jobs
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.created_at < other.created_at


class OCRProcessingError(Exception):
    """Exception raised for OCR processing errors."""
    pass


class OCRQueue:
    """
    Asynchronous OCR processing queue with worker threads.
    Handles job queuing, prioritization, retry logic, and result callbacks.
    """
    
    def __init__(self, ocr_client, num_workers: int = 2, max_queue_size: int = 100):
        """
        Initialize OCR queue.
        
        Args:
            ocr_client: OCR client instance
            num_workers: Number of worker threads
            max_queue_size: Maximum queue size before blocking
        """
        self.ocr_client = ocr_client
        self.num_workers = num_workers
        self.max_queue_size = max_queue_size
        self.logger = logging.getLogger(__name__)
        
        # Queue and threading
        self.job_queue = queue.PriorityQueue(maxsize=max_queue_size)
        self.workers = []
        self.is_running = False
        self._shutdown_event = threading.Event()
        self._lock = threading.Lock()
        
        # Job tracking
        self.active_jobs: Dict[str, OCRJob] = {}
        self.completed_jobs: Dict[str, OCRJob] = {}
        self.failed_jobs: Dict[str, OCRJob] = {}
        
        # Statistics
        self.stats = {
            'total_jobs_queued': 0,
            'total_jobs_completed': 0,
            'total_jobs_failed': 0,
            'jobs_in_queue': 0,
            'active_workers': 0,
            'average_processing_time': 0.0,
            'queue_wait_time': 0.0,
            'last_activity': None
        }
        
        # Cleanup old completed/failed jobs periodically
        self.max_job_history = 1000
        self.job_cleanup_interval = 3600  # 1 hour
        self.last_cleanup = time.time()
    
    def start(self) -> None:
        """Start the OCR queue processing."""
        if self.is_running:
            self.logger.warning("OCR queue is already running")
            return
        
        self.is_running = True
        self._shutdown_event.clear()
        
        # Start worker threads
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"OCRWorker-{i+1}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        self.logger.info(f"OCR queue started with {self.num_workers} workers")
    
    def stop(self, timeout: float = 30.0) -> None:
        """Stop the OCR queue processing."""
        if not self.is_running:
            return
        
        self.logger.info("Stopping OCR queue...")
        self.is_running = False
        self._shutdown_event.set()
        
        # Cancel all pending jobs
        self._cancel_pending_jobs()
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=timeout)
            if worker.is_alive():
                self.logger.warning(f"Worker {worker.name} did not stop gracefully")
        
        self.workers.clear()
        self.logger.info("OCR queue stopped")
    
    def submit_job(self, image_path: Path, hotkey: str,
                   priority: OCRJobPriority = OCRJobPriority.NORMAL,
                   language_codes: Optional[List[str]] = None,
                   cleanup_image: bool = True,
                   callback: Optional[Callable] = None) -> str:
        """
        Submit OCR job to queue.
        
        Args:
            image_path: Path to image file
            hotkey: Hotkey that triggered the job
            priority: Job priority
            language_codes: Optional language codes
            cleanup_image: Whether to cleanup image after processing
            callback: Optional callback function for results
            
        Returns:
            Job ID string
            
        Raises:
            OCRProcessingError: If queue is full or system is not running
        """
        if not self.is_running:
            raise OCRProcessingError("OCR queue is not running")
        
        if not image_path.exists():
            raise OCRProcessingError(f"Image file not found: {image_path}")
        
        # Create job
        job_id = f"ocr_{hotkey}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        job = OCRJob(
            job_id=job_id,
            image_path=image_path,
            hotkey=hotkey,
            priority=priority,
            language_codes=language_codes,
            cleanup_image=cleanup_image,
            callback=callback
        )
        
        try:
            # Add to queue (this may block if queue is full)
            self.job_queue.put(job, timeout=5.0)
            
            with self._lock:
                self.active_jobs[job_id] = job
                self.stats['total_jobs_queued'] += 1
                self.stats['jobs_in_queue'] = self.job_queue.qsize()
            
            self.logger.debug(f"Queued OCR job {job_id} for {hotkey} with priority {priority.name}")
            return job_id
            
        except queue.Full:
            raise OCRProcessingError("OCR queue is full, try again later")
    
    def get_job_status(self, job_id: str) -> Optional[OCRJob]:
        """Get job status by ID."""
        with self._lock:
            # Check active jobs
            if job_id in self.active_jobs:
                return self.active_jobs[job_id]
            
            # Check completed jobs
            if job_id in self.completed_jobs:
                return self.completed_jobs[job_id]
            
            # Check failed jobs
            if job_id in self.failed_jobs:
                return self.failed_jobs[job_id]
        
        return None
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job if it's still pending."""
        with self._lock:
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                if job.status == OCRJobStatus.PENDING:
                    job.status = OCRJobStatus.CANCELLED
                    job.completed_at = datetime.now()
                    self.logger.info(f"Cancelled OCR job {job_id}")
                    return True
        
        return False
    
    def _worker_loop(self) -> None:
        """Main worker thread loop."""
        worker_name = threading.current_thread().name
        self.logger.debug(f"OCR worker {worker_name} started")
        
        try:
            while self.is_running and not self._shutdown_event.is_set():
                try:
                    # Get next job from queue (with timeout)
                    job = self.job_queue.get(timeout=1.0)
                    
                    if job.status == OCRJobStatus.CANCELLED:
                        continue
                    
                    self._process_job(job, worker_name)
                    
                except queue.Empty:
                    # Normal timeout, continue loop
                    continue
                except Exception as e:
                    self.logger.error(f"Worker {worker_name} encountered error: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Worker {worker_name} crashed: {e}")
        finally:
            self.logger.debug(f"OCR worker {worker_name} stopped")
    
    def _process_job(self, job: OCRJob, worker_name: str) -> None:
        """Process a single OCR job."""
        job_start_time = time.time()
        
        try:
            # Update job status
            job.status = OCRJobStatus.PROCESSING
            job.started_at = datetime.now()
            job.attempts += 1
            
            with self._lock:
                self.stats['active_workers'] = len([j for j in self.active_jobs.values() 
                                                  if j.status == OCRJobStatus.PROCESSING])
            
            self.logger.info(f"Worker {worker_name} processing job {job.job_id} (attempt {job.attempts})")
            
            # Process image through OCR
            result = self.ocr_client.process_image_full_pipeline(
                image_path=job.image_path,
                cleanup_image=job.cleanup_image,
                language_codes=job.language_codes
            )
            
            if result:
                # Job completed successfully
                job.status = OCRJobStatus.COMPLETED
                job.result = result
                job.completed_at = datetime.now()
                
                # Call callback if provided
                if job.callback:
                    try:
                        job.callback(job)
                    except Exception as e:
                        self.logger.error(f"Job callback failed for {job.job_id}: {e}")
                
                # Move to completed jobs
                with self._lock:
                    self.active_jobs.pop(job.job_id, None)
                    self.completed_jobs[job.job_id] = job
                    self.stats['total_jobs_completed'] += 1
                    self._update_processing_time_stats(time.time() - job_start_time)
                
                self.logger.info(f"Job {job.job_id} completed successfully in {time.time() - job_start_time:.3f}s")
            
            else:
                # OCR returned no result
                raise OCRProcessingError("OCR processing returned no result")
        
        except Exception as e:
            self.logger.error(f"Job {job.job_id} failed on attempt {job.attempts}: {e}")
            
            # Check if we should retry
            if job.attempts < job.max_attempts:
                # Requeue for retry with exponential backoff
                retry_delay = min(30, 2 ** job.attempts)
                self.logger.info(f"Requeuing job {job.job_id} for retry in {retry_delay}s")
                
                def requeue_job():
                    time.sleep(retry_delay)
                    if self.is_running:
                        job.status = OCRJobStatus.PENDING
                        try:
                            self.job_queue.put(job, timeout=1.0)
                        except queue.Full:
                            self._handle_failed_job(job, "Failed to requeue: queue full")
                
                retry_thread = threading.Thread(target=requeue_job, daemon=True)
                retry_thread.start()
            else:
                # Max attempts reached, mark as failed
                self._handle_failed_job(job, str(e))
        
        finally:
            # Update statistics
            with self._lock:
                self.stats['jobs_in_queue'] = self.job_queue.qsize()
                self.stats['active_workers'] = len([j for j in self.active_jobs.values() 
                                                  if j.status == OCRJobStatus.PROCESSING])
                self.stats['last_activity'] = datetime.now().isoformat()
            
            # Cleanup old jobs periodically
            if time.time() - self.last_cleanup > self.job_cleanup_interval:
                self._cleanup_old_jobs()
    
    def _handle_failed_job(self, job: OCRJob, error_message: str) -> None:
        """Handle permanently failed job."""
        job.status = OCRJobStatus.FAILED
        job.error = error_message
        job.completed_at = datetime.now()
        
        # Call callback if provided
        if job.callback:
            try:
                job.callback(job)
            except Exception as e:
                self.logger.error(f"Failed job callback failed for {job.job_id}: {e}")
        
        # Move to failed jobs
        with self._lock:
            self.active_jobs.pop(job.job_id, None)
            self.failed_jobs[job.job_id] = job
            self.stats['total_jobs_failed'] += 1
        
        self.logger.error(f"Job {job.job_id} permanently failed: {error_message}")
    
    def _update_processing_time_stats(self, processing_time: float) -> None:
        """Update average processing time statistics."""
        completed_count = self.stats['total_jobs_completed']
        if completed_count > 0:
            current_avg = self.stats['average_processing_time']
            self.stats['average_processing_time'] = (
                (current_avg * (completed_count - 1) + processing_time) / completed_count
            )
    
    def _cancel_pending_jobs(self) -> None:
        """Cancel all pending jobs during shutdown."""
        cancelled_count = 0
        
        with self._lock:
            for job in self.active_jobs.values():
                if job.status == OCRJobStatus.PENDING:
                    job.status = OCRJobStatus.CANCELLED
                    job.completed_at = datetime.now()
                    cancelled_count += 1
        
        if cancelled_count > 0:
            self.logger.info(f"Cancelled {cancelled_count} pending OCR jobs")
    
    def _cleanup_old_jobs(self) -> None:
        """Clean up old completed and failed jobs."""
        try:
            with self._lock:
                # Remove old completed jobs
                if len(self.completed_jobs) > self.max_job_history:
                    # Sort by completion time and keep only the most recent
                    sorted_jobs = sorted(
                        self.completed_jobs.items(),
                        key=lambda x: x[1].completed_at or datetime.min,
                        reverse=True
                    )
                    
                    # Keep only the most recent jobs
                    jobs_to_keep = dict(sorted_jobs[:self.max_job_history // 2])
                    removed_count = len(self.completed_jobs) - len(jobs_to_keep)
                    self.completed_jobs = jobs_to_keep
                    
                    if removed_count > 0:
                        self.logger.debug(f"Cleaned up {removed_count} old completed jobs")
                
                # Similar cleanup for failed jobs
                if len(self.failed_jobs) > self.max_job_history:
                    sorted_failed = sorted(
                        self.failed_jobs.items(),
                        key=lambda x: x[1].completed_at or datetime.min,
                        reverse=True
                    )
                    
                    jobs_to_keep = dict(sorted_failed[:self.max_job_history // 2])
                    removed_count = len(self.failed_jobs) - len(jobs_to_keep)
                    self.failed_jobs = jobs_to_keep
                    
                    if removed_count > 0:
                        self.logger.debug(f"Cleaned up {removed_count} old failed jobs")
            
            self.last_cleanup = time.time()
        
        except Exception as e:
            self.logger.error(f"Error during job cleanup: {e}")
    
    def get_queue_statistics(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics."""
        with self._lock:
            stats = self.stats.copy()
            
            # Add real-time data
            stats.update({
                'is_running': self.is_running,
                'active_jobs_count': len(self.active_jobs),
                'completed_jobs_count': len(self.completed_jobs),
                'failed_jobs_count': len(self.failed_jobs),
                'worker_threads': len(self.workers),
                'queue_size': self.job_queue.qsize(),
                'queue_maxsize': self.max_queue_size
            })
            
            # Calculate success rate
            total_finished = stats['total_jobs_completed'] + stats['total_jobs_failed']
            if total_finished > 0:
                stats['success_rate'] = stats['total_jobs_completed'] / total_finished
            else:
                stats['success_rate'] = 0.0
            
            # Job status breakdown
            status_counts = {}
            for status in OCRJobStatus:
                status_counts[status.value] = len([
                    job for job in self.active_jobs.values() 
                    if job.status == status
                ])
            stats['job_status_counts'] = status_counts
        
        return stats
    
    def get_recent_jobs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get list of recent jobs with their status."""
        recent_jobs = []
        
        with self._lock:
            # Collect all jobs
            all_jobs = list(self.active_jobs.values()) + list(self.completed_jobs.values()) + list(self.failed_jobs.values())
            
            # Sort by creation time (most recent first)
            all_jobs.sort(key=lambda x: x.created_at, reverse=True)
            
            # Convert to dictionaries for serialization
            for job in all_jobs[:limit]:
                job_dict = {
                    'job_id': job.job_id,
                    'hotkey': job.hotkey,
                    'status': job.status.value,
                    'priority': job.priority.name,
                    'created_at': job.created_at.isoformat(),
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                    'attempts': job.attempts,
                    'max_attempts': job.max_attempts,
                    'has_result': bool(job.result),
                    'error': job.error
                }
                recent_jobs.append(job_dict)
        
        return recent_jobs
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()