"""
Performance Monitor for Game Monitor System

Comprehensive system for monitoring performance metrics, resource usage,
error tracking, and alerting with real-time data collection.
"""

import time
import threading
import logging
import psutil
import gc
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import deque, defaultdict
import traceback
import queue
import json


@dataclass 
class PerformanceMetric:
    """Individual performance metric data"""
    timestamp: float
    operation: str
    duration: float
    success: bool
    memory_usage: float
    cpu_usage: float
    metadata: Dict[str, Any] = None


@dataclass
class SystemAlert:
    """System performance alert"""
    timestamp: float
    level: str  # INFO, WARNING, ERROR, CRITICAL
    category: str  # performance, memory, error, etc
    message: str
    value: float = None
    threshold: float = None
    metadata: Dict[str, Any] = None


class PerformanceCollector:
    """Collects and manages performance metrics"""
    
    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self.metrics = deque(maxlen=max_metrics)
        self.operation_stats = defaultdict(list)
        self._lock = threading.Lock()
        
        # Performance thresholds
        self.thresholds = {
            'response_time': 1.0,  # seconds
            'memory_usage': 80.0,  # percentage
            'cpu_usage': 75.0,     # percentage
            'error_rate': 5.0      # percentage
        }
    
    def record_operation(self, operation: str, duration: float, 
                        success: bool = True, metadata: Dict = None):
        """Record an operation's performance"""
        timestamp = time.time()
        
        # Get current system metrics
        try:
            memory_usage = psutil.virtual_memory().percent
            cpu_usage = psutil.cpu_percent(interval=0.1)
        except Exception:
            memory_usage = 0.0
            cpu_usage = 0.0
        
        metric = PerformanceMetric(
            timestamp=timestamp,
            operation=operation,
            duration=duration,
            success=success,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            metadata=metadata or {}
        )
        
        with self._lock:
            self.metrics.append(metric)
            self.operation_stats[operation].append(metric)
            
            # Limit per-operation metrics
            if len(self.operation_stats[operation]) > 1000:
                self.operation_stats[operation] = self.operation_stats[operation][-500:]
    
    def get_operation_stats(self, operation: str, hours: int = 1) -> Dict[str, Any]:
        """Get statistics for a specific operation"""
        cutoff_time = time.time() - (hours * 3600)
        
        with self._lock:
            recent_metrics = [
                m for m in self.operation_stats.get(operation, [])
                if m.timestamp >= cutoff_time
            ]
        
        if not recent_metrics:
            return {
                'count': 0,
                'avg_duration': 0,
                'min_duration': 0,
                'max_duration': 0,
                'success_rate': 0,
                'error_count': 0
            }
        
        durations = [m.duration for m in recent_metrics]
        successes = [m.success for m in recent_metrics]
        
        return {
            'count': len(recent_metrics),
            'avg_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'success_rate': (sum(successes) / len(successes)) * 100,
            'error_count': len([m for m in recent_metrics if not m.success])
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system performance statistics"""
        cutoff_time = time.time() - 3600  # Last hour
        
        with self._lock:
            recent_metrics = [m for m in self.metrics if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {
                'total_operations': 0,
                'avg_response_time': 0,
                'memory_usage': psutil.virtual_memory().percent,
                'cpu_usage': psutil.cpu_percent(),
                'success_rate': 100
            }
        
        durations = [m.duration for m in recent_metrics]
        successes = [m.success for m in recent_metrics]
        
        return {
            'total_operations': len(recent_metrics),
            'avg_response_time': sum(durations) / len(durations),
            'min_response_time': min(durations),
            'max_response_time': max(durations),
            'memory_usage': psutil.virtual_memory().percent,
            'cpu_usage': psutil.cpu_percent(),
            'success_rate': (sum(successes) / len(successes)) * 100,
            'error_rate': ((len(successes) - sum(successes)) / len(successes)) * 100
        }


class ErrorTracker:
    """Tracks and categorizes system errors"""
    
    def __init__(self, max_errors: int = 1000):
        self.max_errors = max_errors
        self.errors = deque(maxlen=max_errors)
        self.error_counts = defaultdict(int)
        self._lock = threading.Lock()
    
    def record_error(self, error: Exception, operation: str = None, 
                    metadata: Dict = None):
        """Record an error with context"""
        timestamp = time.time()
        error_type = type(error).__name__
        error_message = str(error)
        stack_trace = traceback.format_exc()
        
        error_data = {
            'timestamp': timestamp,
            'operation': operation,
            'error_type': error_type,
            'error_message': error_message,
            'stack_trace': stack_trace,
            'metadata': metadata or {}
        }
        
        with self._lock:
            self.errors.append(error_data)
            self.error_counts[error_type] += 1
        
        # Log the error
        logging.error(f"Error in {operation}: {error_type}: {error_message}")
    
    def get_error_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get error summary for specified time period"""
        cutoff_time = time.time() - (hours * 3600)
        
        with self._lock:
            recent_errors = [
                e for e in self.errors 
                if e['timestamp'] >= cutoff_time
            ]
        
        error_types = defaultdict(int)
        operations = defaultdict(int)
        
        for error in recent_errors:
            error_types[error['error_type']] += 1
            if error['operation']:
                operations[error['operation']] += 1
        
        return {
            'total_errors': len(recent_errors),
            'error_types': dict(error_types),
            'operations_with_errors': dict(operations),
            'recent_errors': recent_errors[-10:]  # Last 10 errors
        }


class AlertManager:
    """Manages performance alerts and notifications"""
    
    def __init__(self):
        self.alerts = deque(maxlen=1000)
        self.alert_callbacks = []
        self._lock = threading.Lock()
        
        # Alert thresholds
        self.thresholds = {
            'response_time_warning': 0.5,
            'response_time_critical': 1.0,
            'memory_warning': 80.0,
            'memory_critical': 90.0,
            'cpu_warning': 75.0,
            'cpu_critical': 90.0,
            'error_rate_warning': 5.0,
            'error_rate_critical': 10.0
        }
    
    def add_alert_callback(self, callback: Callable[[SystemAlert], None]):
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)
    
    def create_alert(self, level: str, category: str, message: str,
                    value: float = None, threshold: float = None,
                    metadata: Dict = None):
        """Create and process a new alert"""
        alert = SystemAlert(
            timestamp=time.time(),
            level=level,
            category=category,
            message=message,
            value=value,
            threshold=threshold,
            metadata=metadata or {}
        )
        
        with self._lock:
            self.alerts.append(alert)
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logging.error(f"Error in alert callback: {e}")
        
        # Log alert
        log_level = getattr(logging, level, logging.INFO)
        logging.log(log_level, f"ALERT [{category}]: {message}")
    
    def check_performance_thresholds(self, stats: Dict[str, Any]):
        """Check performance stats against thresholds"""
        # Response time alerts
        if 'avg_response_time' in stats:
            response_time = stats['avg_response_time']
            if response_time > self.thresholds['response_time_critical']:
                self.create_alert(
                    'CRITICAL', 'performance',
                    f"Response time critical: {response_time:.3f}s",
                    response_time, self.thresholds['response_time_critical']
                )
            elif response_time > self.thresholds['response_time_warning']:
                self.create_alert(
                    'WARNING', 'performance',
                    f"Response time high: {response_time:.3f}s",
                    response_time, self.thresholds['response_time_warning']
                )
        
        # Memory usage alerts
        if 'memory_usage' in stats:
            memory_usage = stats['memory_usage']
            if memory_usage > self.thresholds['memory_critical']:
                self.create_alert(
                    'CRITICAL', 'memory',
                    f"Memory usage critical: {memory_usage:.1f}%",
                    memory_usage, self.thresholds['memory_critical']
                )
            elif memory_usage > self.thresholds['memory_warning']:
                self.create_alert(
                    'WARNING', 'memory',
                    f"Memory usage high: {memory_usage:.1f}%",
                    memory_usage, self.thresholds['memory_warning']
                )
        
        # CPU usage alerts
        if 'cpu_usage' in stats:
            cpu_usage = stats['cpu_usage']
            if cpu_usage > self.thresholds['cpu_critical']:
                self.create_alert(
                    'CRITICAL', 'cpu',
                    f"CPU usage critical: {cpu_usage:.1f}%",
                    cpu_usage, self.thresholds['cpu_critical']
                )
            elif cpu_usage > self.thresholds['cpu_warning']:
                self.create_alert(
                    'WARNING', 'cpu',
                    f"CPU usage high: {cpu_usage:.1f}%",
                    cpu_usage, self.thresholds['cpu_warning']
                )
        
        # Error rate alerts
        if 'error_rate' in stats:
            error_rate = stats['error_rate']
            if error_rate > self.thresholds['error_rate_critical']:
                self.create_alert(
                    'CRITICAL', 'errors',
                    f"Error rate critical: {error_rate:.1f}%",
                    error_rate, self.thresholds['error_rate_critical']
                )
            elif error_rate > self.thresholds['error_rate_warning']:
                self.create_alert(
                    'WARNING', 'errors',
                    f"Error rate high: {error_rate:.1f}%",
                    error_rate, self.thresholds['error_rate_warning']
                )
    
    def get_recent_alerts(self, hours: int = 1) -> List[SystemAlert]:
        """Get recent alerts"""
        cutoff_time = time.time() - (hours * 3600)
        
        with self._lock:
            return [
                alert for alert in self.alerts 
                if alert.timestamp >= cutoff_time
            ]


class MemoryProfiler:
    """Monitors memory usage and detects leaks"""
    
    def __init__(self):
        self.snapshots = deque(maxlen=100)
        self._lock = threading.Lock()
    
    def take_snapshot(self, label: str = None):
        """Take a memory usage snapshot"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            snapshot = {
                'timestamp': time.time(),
                'label': label or f"snapshot_{len(self.snapshots)}",
                'rss': memory_info.rss,  # Resident Set Size
                'vms': memory_info.vms,  # Virtual Memory Size
                'percent': process.memory_percent(),
                'available': psutil.virtual_memory().available
            }
            
            with self._lock:
                self.snapshots.append(snapshot)
            
            return snapshot
            
        except Exception as e:
            logging.error(f"Error taking memory snapshot: {e}")
            return None
    
    def detect_memory_leaks(self, threshold_mb: float = 10.0) -> List[Dict]:
        """Detect potential memory leaks"""
        if len(self.snapshots) < 5:
            return []
        
        with self._lock:
            recent_snapshots = list(self.snapshots)[-10:]
        
        leaks = []
        for i in range(1, len(recent_snapshots)):
            prev_rss = recent_snapshots[i-1]['rss']
            curr_rss = recent_snapshots[i]['rss']
            
            growth_mb = (curr_rss - prev_rss) / (1024 * 1024)
            
            if growth_mb > threshold_mb:
                leaks.append({
                    'from_snapshot': recent_snapshots[i-1]['label'],
                    'to_snapshot': recent_snapshots[i]['label'],
                    'growth_mb': growth_mb,
                    'timestamp': recent_snapshots[i]['timestamp']
                })
        
        return leaks
    
    def get_memory_trend(self, hours: int = 1) -> Dict[str, Any]:
        """Get memory usage trend"""
        cutoff_time = time.time() - (hours * 3600)
        
        with self._lock:
            recent_snapshots = [
                s for s in self.snapshots 
                if s['timestamp'] >= cutoff_time
            ]
        
        if len(recent_snapshots) < 2:
            return {'trend': 'insufficient_data'}
        
        first_rss = recent_snapshots[0]['rss']
        last_rss = recent_snapshots[-1]['rss']
        
        growth_mb = (last_rss - first_rss) / (1024 * 1024)
        growth_rate = growth_mb / hours  # MB per hour
        
        return {
            'trend': 'increasing' if growth_mb > 0 else 'decreasing',
            'growth_mb': growth_mb,
            'growth_rate_mb_per_hour': growth_rate,
            'current_usage_mb': last_rss / (1024 * 1024),
            'snapshots_analyzed': len(recent_snapshots)
        }


class PerformanceMonitor:
    """Main performance monitoring system"""
    
    def __init__(self):
        self.collector = PerformanceCollector()
        self.error_tracker = ErrorTracker()
        self.alert_manager = AlertManager()
        self.memory_profiler = MemoryProfiler()
        
        # Background monitoring thread
        self._monitoring = False
        self._monitor_thread = None
        self._monitor_interval = 30  # seconds
        
        # Setup structured logging
        self._setup_logging()
        
        logging.info("PerformanceMonitor initialized")
    
    def _setup_logging(self):
        """Setup structured logging for performance monitoring"""
        # Create performance log formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # File handler for performance logs
        try:
            log_handler = logging.FileHandler('logs/performance.log')
            log_handler.setFormatter(formatter)
            log_handler.setLevel(logging.INFO)
            
            # Add handler to root logger
            perf_logger = logging.getLogger('performance')
            perf_logger.addHandler(log_handler)
            perf_logger.setLevel(logging.INFO)
        except Exception as e:
            logging.warning(f"Could not setup performance log file: {e}")
    
    def start_monitoring(self):
        """Start background monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        logging.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        logging.info("Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self._monitoring:
            try:
                # Collect system stats
                stats = self.get_system_performance()
                
                # Check thresholds and create alerts
                self.alert_manager.check_performance_thresholds(stats)
                
                # Take memory snapshot
                self.memory_profiler.take_snapshot(f"auto_{time.time()}")
                
                # Check for memory leaks
                leaks = self.memory_profiler.detect_memory_leaks()
                if leaks:
                    for leak in leaks:
                        self.alert_manager.create_alert(
                            'WARNING', 'memory',
                            f"Potential memory leak detected: {leak['growth_mb']:.1f}MB growth",
                            leak['growth_mb'], metadata=leak
                        )
                
                # Force garbage collection periodically
                if int(time.time()) % 300 == 0:  # Every 5 minutes
                    collected = gc.collect()
                    logging.info(f"Garbage collection: collected {collected} objects")
                
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
            
            time.sleep(self._monitor_interval)
    
    def record_timing(self, operation: str):
        """Context manager for timing operations"""
        return TimingContext(self.collector, operation)
    
    def record_error(self, error: Exception, operation: str = None, metadata: Dict = None):
        """Record an error"""
        self.error_tracker.record_error(error, operation, metadata)
    
    def get_system_performance(self) -> Dict[str, Any]:
        """Get comprehensive system performance data"""
        system_stats = self.collector.get_system_stats()
        error_summary = self.error_tracker.get_error_summary()
        memory_trend = self.memory_profiler.get_memory_trend()
        recent_alerts = self.alert_manager.get_recent_alerts()
        
        return {
            'timestamp': time.time(),
            'system': system_stats,
            'errors': error_summary,
            'memory': memory_trend,
            'alerts': len(recent_alerts),
            'alert_levels': {
                level: len([a for a in recent_alerts if a.level == level])
                for level in ['INFO', 'WARNING', 'ERROR', 'CRITICAL']
            }
        }
    
    def get_operation_performance(self, operation: str, hours: int = 1) -> Dict[str, Any]:
        """Get performance data for specific operation"""
        return self.collector.get_operation_stats(operation, hours)
    
    def export_performance_data(self, filename: str, hours: int = 1):
        """Export performance data to JSON file"""
        try:
            data = {
                'export_timestamp': time.time(),
                'system_performance': self.get_system_performance(),
                'memory_snapshots': list(self.memory_profiler.snapshots),
                'recent_errors': self.error_tracker.get_error_summary(hours),
                'recent_alerts': [asdict(alert) for alert in self.alert_manager.get_recent_alerts(hours)]
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            logging.info(f"Performance data exported to {filename}")
            
        except Exception as e:
            logging.error(f"Error exporting performance data: {e}")


class TimingContext:
    """Context manager for operation timing"""
    
    def __init__(self, collector: PerformanceCollector, operation: str):
        self.collector = collector
        self.operation = operation
        self.start_time = None
        self.metadata = {}
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        success = exc_type is None
        
        if exc_type:
            self.metadata['error'] = str(exc_val)
            self.metadata['error_type'] = exc_type.__name__
        
        self.collector.record_operation(
            self.operation, duration, success, self.metadata
        )
    
    def add_metadata(self, **kwargs):
        """Add metadata to the timing context"""
        self.metadata.update(kwargs)


# Global performance monitor instance
_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor