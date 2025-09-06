"""
Task scheduler for market monitoring system.
Manages periodic processing of screenshots, status checks, and maintenance tasks.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any, List
from pathlib import Path

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
    SCHEDULER_AVAILABLE = True
except ImportError as e:
    SCHEDULER_AVAILABLE = False
    SCHEDULER_ERROR = str(e)

from config.settings import SettingsManager
from core.database_manager import DatabaseManager
from core.image_processor import ImageProcessor
from core.ocr_client import YandexOCRClient
from core.text_parser import TextParser
from core.monitoring_engine import MonitoringEngine


class SchedulerError(Exception):
    """Exception raised for scheduler errors."""
    pass


class TaskScheduler:
    """
    Manages automated task scheduling for the market monitoring system.
    Handles hotkey processing timers, status checks, and maintenance tasks.
    """
    
    def __init__(self, settings_manager: SettingsManager, 
                 database_manager: DatabaseManager,
                 image_processor: ImageProcessor,
                 ocr_queue,  # OCRQueue instance
                 text_parser: TextParser,
                 monitoring_engine: MonitoringEngine):
        """
        Initialize task scheduler.
        
        Args:
            settings_manager: Settings manager instance
            database_manager: Database manager instance
            image_processor: Image processor instance
            ocr_queue: OCR queue instance for asynchronous processing
            text_parser: Text parser instance
            monitoring_engine: Monitoring engine instance
        """
        if not SCHEDULER_AVAILABLE:
            raise SchedulerError(f"APScheduler not available: {SCHEDULER_ERROR}")
        
        self.settings = settings_manager
        self.db = database_manager
        self.image_processor = image_processor
        self.ocr_queue = ocr_queue
        self.text_parser = text_parser
        self.monitoring_engine = monitoring_engine
        self.logger = logging.getLogger(__name__)
        
        # Scheduler instance
        self.scheduler = BackgroundScheduler()
        
        # Job tracking
        self._job_stats = {}
        self._is_running = False
        self._lock = threading.Lock()
        
        # Setup scheduler event listeners
        self._setup_event_listeners()
    
    def _setup_event_listeners(self) -> None:
        """Setup scheduler event listeners for monitoring."""
        def job_listener(event):
            job_id = event.job_id
            
            if event.code == EVENT_JOB_EXECUTED:
                self.logger.debug(f"Job {job_id} executed successfully")
                self._update_job_stats(job_id, 'success')
                
            elif event.code == EVENT_JOB_ERROR:
                self.logger.error(f"Job {job_id} failed: {event.exception}")
                self._update_job_stats(job_id, 'error')
                
            elif event.code == EVENT_JOB_MISSED:
                self.logger.warning(f"Job {job_id} missed execution")
                self._update_job_stats(job_id, 'missed')
        
        self.scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)
    
    def setup_hotkey_timers(self) -> None:
        """Setup periodic processing timers for all enabled hotkeys."""
        try:
            enabled_hotkeys = self.settings.get_enabled_hotkeys()
            
            for hotkey_name, config in enabled_hotkeys.items():
                job_id = f"process_hotkey_{hotkey_name}"
                
                # Remove existing job if it exists
                if self.scheduler.get_job(job_id):
                    self.scheduler.remove_job(job_id)
                
                # Add new job
                self.scheduler.add_job(
                    func=self.process_hotkey_folder,
                    trigger=IntervalTrigger(seconds=config.merge_interval),
                    args=[hotkey_name],
                    id=job_id,
                    name=f"Process {hotkey_name} screenshots",
                    max_instances=1,  # Prevent overlap
                    coalesce=True,    # Combine missed runs
                    misfire_grace_time=30
                )
                
                # Initialize job stats
                self._job_stats[job_id] = {
                    'total_runs': 0,
                    'successful_runs': 0,
                    'failed_runs': 0,
                    'missed_runs': 0,
                    'last_run': None,
                    'average_duration': 0.0,
                    'last_error': None
                }
                
                self.logger.info(
                    f"Scheduled {hotkey_name} processing every {config.merge_interval}s"
                )
            
            self.logger.info(f"Setup {len(enabled_hotkeys)} hotkey processing timers")
            
        except Exception as e:
            raise SchedulerError(f"Failed to setup hotkey timers: {e}")
    
    def process_hotkey_folder(self, hotkey_name: str) -> None:
        """
        Process screenshots for a specific hotkey using asynchronous OCR queue.
        
        Args:
            hotkey_name: Name of the hotkey to process
        """
        job_id = f"process_hotkey_{hotkey_name}"
        start_time = time.time()
        
        try:
            self.logger.debug(f"Starting processing for hotkey {hotkey_name}")
            
            # Check if hotkey is still enabled
            if not self.settings.is_hotkey_enabled(hotkey_name):
                self.logger.info(f"Skipping disabled hotkey {hotkey_name}")
                return
            
            # Process images
            merged_image_path = self.image_processor.process_hotkey_folder(hotkey_name)
            
            if not merged_image_path:
                self.logger.debug(f"No images to process for {hotkey_name}")
                return
            
            # Create OCR session record
            session_id = self.db.create_ocr_session(hotkey_name)
            session_start_time = time.time()
            
            # Create callback for OCR completion
            def ocr_completion_callback(ocr_job):
                """
                Callback function called when OCR job completes.
                
                Args:
                    ocr_job: Completed OCRJob instance
                """
                try:
                    # Calculate OCR duration
                    ocr_duration = time.time() - session_start_time
                    
                    if ocr_job.status.value == "completed" and ocr_job.result:
                        # Get processing type from hotkey configuration
                        hotkey_config = self.settings.hotkeys.get(hotkey_name.lower())
                        processing_type = hotkey_config.processing_type if hotkey_config else 'full'
                        screenshot_type = hotkey_config.screenshot_type if hotkey_config else "individual_seller_items"
                        
                        # Parse the extracted text
                        parsing_result = self.text_parser.parse_items_data(
                            ocr_job.result, 
                            hotkey_name,
                            screenshot_type=screenshot_type,
                            processing_type=processing_type
                        )
                        
                        if parsing_result.errors:
                            self.logger.warning(
                                f"Parsing errors for {hotkey_name}: {parsing_result.errors}"
                            )
                        
                        # Save extracted items
                        items_saved = 0
                        if parsing_result.items:
                            items_saved = self.db.save_items_data(parsing_result.items, session_id)
                        
                        # Update OCR session with success
                        self.db.update_ocr_session(session_id, ocr_duration)
                        
                        # Process through monitoring engine
                        if parsing_result.items:
                            detection_result = self.monitoring_engine.process_parsing_results([parsing_result])
                            
                            self.logger.info(
                                f"Processed {hotkey_name}: {items_saved} items saved, "
                                f"{len(detection_result.detected_changes)} changes detected "
                                f"(OCR job {ocr_job.job_id})"
                            )
                        else:
                            self.logger.info(
                                f"Processed {hotkey_name}: no items extracted "
                                f"(OCR job {ocr_job.job_id})"
                            )
                    
                    else:
                        # OCR failed
                        error_msg = ocr_job.error or "Unknown OCR error"
                        self.logger.error(
                            f"OCR failed for {hotkey_name}: {error_msg} "
                            f"(OCR job {ocr_job.job_id})"
                        )
                        
                        # Update OCR session with failure
                        self.db.update_ocr_session(session_id, ocr_duration, error_msg)
                
                except Exception as callback_error:
                    self.logger.error(
                        f"Error in OCR callback for {hotkey_name}: {callback_error} "
                        f"(OCR job {ocr_job.job_id})"
                    )
                    # Still update session to avoid orphaned records
                    try:
                        self.db.update_ocr_session(
                            session_id, 
                            time.time() - session_start_time, 
                            f"Callback error: {callback_error}"
                        )
                    except Exception:
                        pass
            
            # Submit OCR job to queue
            from core.ocr_queue import OCRJobPriority
            
            ocr_job_id = self.ocr_queue.submit_job(
                image_path=merged_image_path,
                hotkey=hotkey_name,
                priority=OCRJobPriority.NORMAL,
                cleanup_image=True,  # Clean up merged image after OCR
                callback=ocr_completion_callback
            )
            
            self.logger.info(
                f"Submitted OCR job {ocr_job_id} for {hotkey_name} "
                f"(session {session_id})"
            )
            
        except Exception as e:
            self.logger.error(f"Error processing hotkey {hotkey_name}: {e}")
            # Try to update OCR session with error if it was created
            try:
                if 'session_id' in locals():
                    self.db.update_ocr_session(
                        session_id, 
                        time.time() - session_start_time if 'session_start_time' in locals() else 0,
                        f"Processing error: {e}"
                    )
            except Exception:
                pass
            raise
        finally:
            # Update job statistics
            duration = time.time() - start_time
            self._update_job_duration(job_id, duration)
    
    def setup_status_check_cycle(self) -> None:
        """Setup periodic status check and transition processing."""
        try:
            interval = self.settings.monitoring.status_check_interval
            
            job_id = "status_check_cycle"
            
            # Remove existing job if it exists
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # Add status check job
            self.scheduler.add_job(
                func=self.run_status_check_cycle,
                trigger=IntervalTrigger(seconds=interval),
                id=job_id,
                name="Status check and transition cycle",
                max_instances=1,
                coalesce=True,
                misfire_grace_time=60
            )
            
            # Initialize job stats
            self._job_stats[job_id] = {
                'total_runs': 0,
                'successful_runs': 0,
                'failed_runs': 0,
                'missed_runs': 0,
                'last_run': None,
                'average_duration': 0.0,
                'last_error': None
            }
            
            self.logger.info(f"Scheduled status check cycle every {interval}s")
            
        except Exception as e:
            raise SchedulerError(f"Failed to setup status check cycle: {e}")
    
    def run_status_check_cycle(self) -> None:
        """Run status check and transition cycle."""
        start_time = time.time()
        
        try:
            self.logger.debug("Starting status check cycle")
            
            # Process status transitions
            transitions = self.monitoring_engine.process_status_transitions()
            
            # Remove inactive combinations
            inactive_threshold = getattr(self.settings.monitoring, 'inactive_threshold_days', 7)
            removed_count = self.monitoring_engine.remove_inactive_combinations(inactive_threshold)
            
            self.logger.info(
                f"Status check cycle completed: {len(transitions)} transitions, "
                f"{removed_count} inactive combinations removed"
            )
            
        except Exception as e:
            self.logger.error(f"Status check cycle failed: {e}")
            raise
        finally:
            duration = time.time() - start_time
            self._update_job_duration("status_check_cycle", duration)
    
    def setup_maintenance_tasks(self) -> None:
        """Setup periodic maintenance tasks."""
        try:
            # Daily cleanup at 2 AM
            cleanup_job_id = "daily_cleanup"
            
            if self.scheduler.get_job(cleanup_job_id):
                self.scheduler.remove_job(cleanup_job_id)
            
            self.scheduler.add_job(
                func=self.run_maintenance_cleanup,
                trigger=CronTrigger(hour=2, minute=0),
                id=cleanup_job_id,
                name="Daily maintenance cleanup",
                max_instances=1,
                coalesce=True,
                misfire_grace_time=3600  # 1 hour grace time
            )
            
            # Weekly database vacuum on Sundays at 3 AM
            vacuum_job_id = "weekly_vacuum"
            
            if self.scheduler.get_job(vacuum_job_id):
                self.scheduler.remove_job(vacuum_job_id)
            
            self.scheduler.add_job(
                func=self.run_database_maintenance,
                trigger=CronTrigger(day_of_week=6, hour=3, minute=0),  # Sunday
                id=vacuum_job_id,
                name="Weekly database maintenance",
                max_instances=1,
                coalesce=True,
                misfire_grace_time=3600
            )
            
            # Initialize job stats
            for job_id in [cleanup_job_id, vacuum_job_id]:
                self._job_stats[job_id] = {
                    'total_runs': 0,
                    'successful_runs': 0,
                    'failed_runs': 0,
                    'missed_runs': 0,
                    'last_run': None,
                    'average_duration': 0.0,
                    'last_error': None
                }
            
            self.logger.info("Scheduled maintenance tasks")
            
        except Exception as e:
            raise SchedulerError(f"Failed to setup maintenance tasks: {e}")
    
    def run_maintenance_cleanup(self) -> None:
        """Run daily maintenance cleanup tasks."""
        start_time = time.time()
        
        try:
            self.logger.info("Starting daily maintenance cleanup")
            
            # Clean up old database records
            cleanup_days = self.settings.monitoring.cleanup_old_data_days
            deleted_records = self.db.cleanup_expired_records(cleanup_days)
            
            # Clean up old merged images
            deleted_images = self.image_processor.cleanup_old_merged_images(24)
            
            # Clean up old screenshot files
            # (This would typically be handled by the screenshot capture module)
            
            self.logger.info(
                f"Daily cleanup completed: {deleted_records} database records, "
                f"{deleted_images} merged images removed"
            )
            
        except Exception as e:
            self.logger.error(f"Daily cleanup failed: {e}")
            raise
        finally:
            duration = time.time() - start_time
            self._update_job_duration("daily_cleanup", duration)
    
    def run_database_maintenance(self) -> None:
        """Run database maintenance tasks."""
        start_time = time.time()
        
        try:
            self.logger.info("Starting database maintenance")
            
            # Vacuum database
            self.db.vacuum_database()
            
            # Get database statistics
            stats = self.db.get_monitoring_status_summary()
            self.logger.info(f"Database statistics after maintenance: {stats}")
            
        except Exception as e:
            self.logger.error(f"Database maintenance failed: {e}")
            raise
        finally:
            duration = time.time() - start_time
            self._update_job_duration("weekly_vacuum", duration)
    
    def start_monitoring(self) -> None:
        """Start the task scheduler and all periodic tasks."""
        try:
            if self._is_running:
                self.logger.warning("Scheduler is already running")
                return
            
            self.logger.info("Starting task scheduler")
            
            # Setup all scheduled tasks
            self.setup_hotkey_timers()
            self.setup_status_check_cycle()
            self.setup_maintenance_tasks()
            
            # Start the scheduler
            self.scheduler.start()
            self._is_running = True
            
            # Log scheduled jobs
            jobs = self.scheduler.get_jobs()
            self.logger.info(f"Scheduler started with {len(jobs)} jobs:")
            for job in jobs:
                next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "Unknown"
                self.logger.info(f"  - {job.name} (next run: {next_run})")
            
        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {e}")
            raise SchedulerError(f"Failed to start scheduler: {e}")
    
    def stop_monitoring(self) -> None:
        """Stop the task scheduler."""
        try:
            if not self._is_running:
                return
            
            self.logger.info("Stopping task scheduler")
            
            # Shutdown scheduler
            self.scheduler.shutdown(wait=True)
            self._is_running = False
            
            self.logger.info("Task scheduler stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping scheduler: {e}")
    
    def pause_job(self, job_id: str) -> bool:
        """
        Pause a specific scheduled job.
        
        Args:
            job_id: ID of the job to pause
            
        Returns:
            True if job was paused successfully
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                self.scheduler.pause_job(job_id)
                self.logger.info(f"Paused job {job_id}")
                return True
            else:
                self.logger.warning(f"Job {job_id} not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to pause job {job_id}: {e}")
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """
        Resume a paused job.
        
        Args:
            job_id: ID of the job to resume
            
        Returns:
            True if job was resumed successfully
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                self.scheduler.resume_job(job_id)
                self.logger.info(f"Resumed job {job_id}")
                return True
            else:
                self.logger.warning(f"Job {job_id} not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to resume job {job_id}: {e}")
            return False
    
    def _update_job_stats(self, job_id: str, result_type: str) -> None:
        """Update job statistics."""
        with self._lock:
            if job_id not in self._job_stats:
                return
            
            stats = self._job_stats[job_id]
            stats['total_runs'] += 1
            stats['last_run'] = datetime.now().isoformat()
            
            if result_type == 'success':
                stats['successful_runs'] += 1
            elif result_type == 'error':
                stats['failed_runs'] += 1
            elif result_type == 'missed':
                stats['missed_runs'] += 1
    
    def _update_job_duration(self, job_id: str, duration: float) -> None:
        """Update job duration statistics."""
        with self._lock:
            if job_id not in self._job_stats:
                return
            
            stats = self._job_stats[job_id]
            
            # Update average duration
            if stats['successful_runs'] > 0:
                current_avg = stats['average_duration']
                successful_count = stats['successful_runs']
                stats['average_duration'] = (
                    (current_avg * (successful_count - 1) + duration) / successful_count
                )
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """
        Get scheduler status and statistics.
        
        Returns:
            Dictionary with scheduler status information
        """
        status = {
            'is_running': self._is_running,
            'scheduler_state': self.scheduler.state.name if hasattr(self.scheduler, 'state') else 'Unknown',
            'total_jobs': len(self.scheduler.get_jobs()) if self._is_running else 0,
            'job_statistics': {}
        }
        
        if self._is_running:
            # Get job information
            for job in self.scheduler.get_jobs():
                job_info = {
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger),
                    'max_instances': job.max_instances,
                    'coalesce': job.coalesce
                }
                
                # Add statistics if available
                if job.id in self._job_stats:
                    job_info.update(self._job_stats[job.id])
                
                status['job_statistics'][job.id] = job_info
        
        return status
    
    def run_job_now(self, job_id: str) -> bool:
        """
        Run a scheduled job immediately.
        
        Args:
            job_id: ID of the job to run
            
        Returns:
            True if job was triggered successfully
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.modify(next_run_time=datetime.now())
                self.logger.info(f"Triggered immediate run for job {job_id}")
                return True
            else:
                self.logger.warning(f"Job {job_id} not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to run job {job_id}: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry."""
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_monitoring()