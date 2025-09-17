"""Thread coordination and management for Voice-to-AI system."""

import threading
import time
import queue
import signal
from typing import Any, Callable, Dict, Optional, List, Set
from concurrent.futures import ThreadPoolExecutor, Future
import logging
from dataclasses import dataclass
from enum import Enum

from .event_bus import EventBus, EventType, get_event_bus
from .state_manager import StateManager, ComponentState, get_state_manager

logger = logging.getLogger(__name__)


class ThreadType(Enum):
    """Types of threads in the system."""
    MAIN = "main"
    AUDIO_CAPTURE = "audio_capture"
    AUDIO_PROCESSING = "audio_processing"
    STT_PROCESSING = "stt_processing"
    AI_PROCESSING = "ai_processing"
    OVERLAY_UPDATE = "overlay_update"
    HOTKEY_MONITOR = "hotkey_monitor"
    PERFORMANCE_MONITOR = "performance_monitor"
    EVENT_PROCESSOR = "event_processor"
    BACKGROUND_TASK = "background_task"


@dataclass
class ThreadInfo:
    """Information about a managed thread."""
    thread_id: int
    name: str
    thread_type: ThreadType
    thread: threading.Thread
    start_time: float
    is_daemon: bool
    is_alive: bool
    cpu_time: float = 0.0
    memory_usage: float = 0.0


class ManagedThread:
    """A managed thread with enhanced monitoring capabilities."""
    
    def __init__(
        self,
        name: str,
        target: Callable,
        thread_type: ThreadType,
        daemon: bool = True,
        args: tuple = (),
        kwargs: Optional[Dict] = None
    ):
        self.name = name
        self.target = target
        self.thread_type = thread_type
        self.args = args
        self.kwargs = kwargs or {}
        self.daemon = daemon
        
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._start_time: Optional[float] = None
        self._coordinator: Optional['ThreadCoordinator'] = None
        
    def start(self, coordinator: 'ThreadCoordinator') -> bool:
        """Start the managed thread."""
        if self._thread and self._thread.is_alive():
            logger.warning(f"Thread {self.name} is already running")
            return False
        
        try:
            self._coordinator = coordinator
            self._stop_event.clear()
            
            # Wrap target function to handle stop events
            def wrapped_target():
                try:
                    logger.debug(f"Thread {self.name} started")
                    self.target(self._stop_event, *self.args, **self.kwargs)
                except Exception as e:
                    logger.error(f"Error in thread {self.name}: {e}")
                    coordinator._handle_thread_error(self.name, e)
                finally:
                    logger.debug(f"Thread {self.name} finished")
                    coordinator._unregister_thread(self.name)
            
            self._thread = threading.Thread(
                target=wrapped_target,
                name=self.name,
                daemon=self.daemon
            )
            
            self._start_time = time.time()
            self._thread.start()
            
            logger.info(f"Started thread: {self.name} (type: {self.thread_type.value})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start thread {self.name}: {e}")
            return False
    
    def stop(self, timeout: float = 5.0) -> bool:
        """Stop the managed thread."""
        if not self._thread or not self._thread.is_alive():
            return True
        
        try:
            logger.debug(f"Stopping thread: {self.name}")
            self._stop_event.set()
            
            self._thread.join(timeout=timeout)
            
            if self._thread.is_alive():
                logger.warning(f"Thread {self.name} did not stop within {timeout} seconds")
                return False
            
            logger.info(f"Stopped thread: {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping thread {self.name}: {e}")
            return False
    
    def is_alive(self) -> bool:
        """Check if thread is alive."""
        return self._thread is not None and self._thread.is_alive()
    
    def get_info(self) -> ThreadInfo:
        """Get thread information."""
        return ThreadInfo(
            thread_id=self._thread.ident if self._thread else 0,
            name=self.name,
            thread_type=self.thread_type,
            thread=self._thread,
            start_time=self._start_time or 0.0,
            is_daemon=self.daemon,
            is_alive=self.is_alive()
        )


class ThreadCoordinator:
    """Coordinates and manages all system threads."""
    
    def __init__(
        self,
        max_threads: int = 10,
        event_bus: Optional[EventBus] = None,
        state_manager: Optional[StateManager] = None
    ):
        self.max_threads = max_threads
        self._event_bus = event_bus or get_event_bus()
        self._state_manager = state_manager or get_state_manager()
        
        self._threads: Dict[str, ManagedThread] = {}
        self._thread_pool = ThreadPoolExecutor(max_workers=max_threads, thread_name_prefix="VoiceAI")
        self._futures: Dict[str, Future] = {}
        self._lock = threading.RLock()
        self._shutdown_initiated = False
        
        # Performance monitoring
        self._monitor_thread: Optional[ManagedThread] = None
        self._monitor_interval = 5.0  # seconds
        
        # Signal handling for graceful shutdown
        self._setup_signal_handlers()
        
        logger.info(f"ThreadCoordinator initialized with max {max_threads} threads")
    
    def start_thread(
        self,
        name: str,
        target: Callable,
        thread_type: ThreadType,
        daemon: bool = True,
        args: tuple = (),
        kwargs: Optional[Dict] = None
    ) -> bool:
        """Start a new managed thread.
        
        Args:
            name: Unique thread name
            target: Target function (must accept stop_event as first parameter)
            thread_type: Type of thread
            daemon: Whether thread should be daemon
            args: Additional arguments for target function
            kwargs: Additional keyword arguments for target function
            
        Returns:
            True if thread started successfully
        """
        with self._lock:
            if self._shutdown_initiated:
                logger.warning("Cannot start new threads during shutdown")
                return False
            
            if name in self._threads:
                logger.warning(f"Thread {name} already exists")
                return False
            
            if len(self._threads) >= self.max_threads:
                logger.error(f"Maximum number of threads ({self.max_threads}) reached")
                return False
            
            try:
                managed_thread = ManagedThread(name, target, thread_type, daemon, args, kwargs)
                
                if managed_thread.start(self):
                    self._threads[name] = managed_thread
                    
                    # Update state manager
                    self._state_manager.update_performance_state(
                        active_threads=len(self._threads)
                    )
                    
                    # Emit event
                    self._event_bus.emit(
                        EventType.APPLICATION_STARTED,
                        "thread_coordinator",
                        {
                            "thread_name": name,
                            "thread_type": thread_type.value,
                            "total_threads": len(self._threads)
                        }
                    )
                    
                    return True
                
                return False
                
            except Exception as e:
                logger.error(f"Failed to start thread {name}: {e}")
                return False
    
    def stop_thread(self, name: str, timeout: float = 5.0) -> bool:
        """Stop a managed thread.
        
        Args:
            name: Thread name to stop
            timeout: Maximum time to wait for thread to stop
            
        Returns:
            True if thread stopped successfully
        """
        with self._lock:
            if name not in self._threads:
                logger.warning(f"Thread {name} not found")
                return False
            
            thread = self._threads[name]
            success = thread.stop(timeout)
            
            if success:
                del self._threads[name]
                
                # Update state manager
                self._state_manager.update_performance_state(
                    active_threads=len(self._threads)
                )
            
            return success
    
    def submit_task(
        self,
        name: str,
        target: Callable,
        args: tuple = (),
        kwargs: Optional[Dict] = None
    ) -> Optional[Future]:
        """Submit a task to the thread pool.
        
        Args:
            name: Unique task name
            target: Target function
            args: Function arguments
            kwargs: Function keyword arguments
            
        Returns:
            Future object or None if submission failed
        """
        with self._lock:
            if self._shutdown_initiated:
                logger.warning("Cannot submit new tasks during shutdown")
                return None
            
            try:
                future = self._thread_pool.submit(target, *(args or ()), **(kwargs or {}))
                self._futures[name] = future
                
                logger.debug(f"Submitted task: {name}")
                return future
                
            except Exception as e:
                logger.error(f"Failed to submit task {name}: {e}")
                return None
    
    def get_task_result(self, name: str, timeout: Optional[float] = None) -> Any:
        """Get result of a submitted task.
        
        Args:
            name: Task name
            timeout: Maximum time to wait for result
            
        Returns:
            Task result or None if task not found/failed
        """
        with self._lock:
            if name not in self._futures:
                logger.warning(f"Task {name} not found")
                return None
            
            try:
                future = self._futures[name]
                result = future.result(timeout=timeout)
                
                # Clean up completed future
                del self._futures[name]
                return result
                
            except Exception as e:
                logger.error(f"Error getting result for task {name}: {e}")
                return None
    
    def is_thread_alive(self, name: str) -> bool:
        """Check if a thread is alive."""
        with self._lock:
            return name in self._threads and self._threads[name].is_alive()
    
    def get_thread_info(self, name: str) -> Optional[ThreadInfo]:
        """Get information about a thread."""
        with self._lock:
            if name in self._threads:
                return self._threads[name].get_info()
            return None
    
    def get_all_threads_info(self) -> Dict[str, ThreadInfo]:
        """Get information about all threads."""
        with self._lock:
            return {name: thread.get_info() for name, thread in self._threads.items()}
    
    def get_thread_count(self) -> int:
        """Get current number of active threads."""
        with self._lock:
            return len(self._threads)
    
    def get_active_thread_types(self) -> Set[ThreadType]:
        """Get set of active thread types."""
        with self._lock:
            return {thread.thread_type for thread in self._threads.values()}
    
    def start_performance_monitoring(self) -> bool:
        """Start performance monitoring thread."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            logger.warning("Performance monitoring already running")
            return False
        
        def monitor_performance(stop_event: threading.Event):
            """Performance monitoring loop."""
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            
            while not stop_event.wait(self._monitor_interval):
                try:
                    # Get system metrics
                    cpu_percent = process.cpu_percent()
                    memory_info = process.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024
                    thread_count = process.num_threads()
                    
                    # Update state manager
                    self._state_manager.update_performance_state(
                        cpu_usage=cpu_percent,
                        memory_usage=memory_mb,
                        active_threads=thread_count
                    )
                    
                    # Check for performance warnings
                    settings = self._state_manager.get_state().performance
                    if cpu_percent > settings.max_cpu_usage:
                        self._event_bus.emit(
                            EventType.PERFORMANCE_WARNING,
                            "thread_coordinator",
                            {
                                "metric": "cpu_usage",
                                "value": cpu_percent,
                                "threshold": settings.max_cpu_usage
                            }
                        )
                    
                    if memory_mb > settings.max_memory_usage:
                        self._event_bus.emit(
                            EventType.RESOURCE_USAGE_HIGH,
                            "thread_coordinator",
                            {
                                "metric": "memory_usage",
                                "value": memory_mb,
                                "threshold": settings.max_memory_usage
                            }
                        )
                    
                    logger.debug(f"Performance: CPU {cpu_percent:.1f}%, Memory {memory_mb:.1f}MB, Threads {thread_count}")
                    
                except Exception as e:
                    logger.error(f"Error in performance monitoring: {e}")
        
        return self.start_thread(
            "performance_monitor",
            monitor_performance,
            ThreadType.PERFORMANCE_MONITOR,
            daemon=True
        )
    
    def stop_performance_monitoring(self) -> bool:
        """Stop performance monitoring thread."""
        return self.stop_thread("performance_monitor")
    
    def shutdown(self, timeout: float = 10.0) -> bool:
        """Shutdown all threads and cleanup resources.
        
        Args:
            timeout: Maximum time to wait for all threads to stop
            
        Returns:
            True if all threads stopped successfully
        """
        logger.info("ThreadCoordinator shutdown initiated")
        
        with self._lock:
            self._shutdown_initiated = True
        
        # Stop performance monitoring first
        self.stop_performance_monitoring()
        
        # Stop all managed threads
        thread_names = list(self._threads.keys())
        success = True
        
        for name in thread_names:
            if not self.stop_thread(name, timeout / len(thread_names) if thread_names else timeout):
                success = False
        
        # Shutdown thread pool
        try:
            self._thread_pool.shutdown(wait=True, timeout=timeout)
            logger.info("Thread pool shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down thread pool: {e}")
            success = False
        
        # Cancel any remaining futures
        for name, future in self._futures.items():
            if not future.done():
                future.cancel()
                logger.debug(f"Cancelled future: {name}")
        
        self._futures.clear()
        
        logger.info(f"ThreadCoordinator shutdown {'successful' if success else 'completed with errors'}")
        return success
    
    def _unregister_thread(self, name: str) -> None:
        """Unregister a thread (called when thread finishes)."""
        with self._lock:
            if name in self._threads:
                del self._threads[name]
                logger.debug(f"Unregistered thread: {name}")
    
    def _handle_thread_error(self, name: str, error: Exception) -> None:
        """Handle thread error."""
        logger.error(f"Thread {name} encountered error: {error}")
        
        # Record error in state manager
        self._state_manager.record_error(f"thread_{name}", str(error), critical=True)
        
        # Emit error event
        self._event_bus.emit(
            EventType.APPLICATION_ERROR,
            "thread_coordinator",
            {
                "thread_name": name,
                "error": str(error),
                "thread_count": len(self._threads)
            }
        )
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown")
            self.shutdown()
        
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            logger.debug("Signal handlers registered")
        except Exception as e:
            logger.warning(f"Could not register signal handlers: {e}")


# Global thread coordinator instance
_thread_coordinator: Optional[ThreadCoordinator] = None


def get_thread_coordinator() -> ThreadCoordinator:
    """Get global thread coordinator instance."""
    global _thread_coordinator
    if _thread_coordinator is None:
        _thread_coordinator = ThreadCoordinator()
    return _thread_coordinator