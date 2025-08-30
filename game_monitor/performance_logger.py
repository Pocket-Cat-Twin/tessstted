"""
Performance Monitoring and Logging System for Game Monitor
Real-time performance tracking, bottleneck detection, and optimization suggestions.
"""

import threading
import time
import psutil
import os
from typing import Dict, List, Optional, Any, Callable, NamedTuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import deque, defaultdict
import statistics
import json

from .advanced_logger import get_logger


class OperationType(NamedTuple):
    """Operation type classification"""
    component: str
    operation: str


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for an operation"""
    trace_id: str
    component: str
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    
    # System metrics
    cpu_percent_before: Optional[float] = None
    cpu_percent_after: Optional[float] = None
    memory_mb_before: Optional[float] = None
    memory_mb_after: Optional[float] = None
    memory_delta_mb: Optional[float] = None
    
    # Operation-specific metrics
    data_size_bytes: Optional[int] = None
    records_processed: Optional[int] = None
    cache_hits: Optional[int] = None
    cache_misses: Optional[int] = None
    
    # Quality metrics
    success: bool = True
    error_count: int = 0
    retry_count: int = 0
    
    # Context
    context: Optional[Dict[str, Any]] = None
    
    def finish(self, success: bool = True, error_count: int = 0):
        """Mark operation as finished and calculate final metrics"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.success = success
        self.error_count = error_count
        
        # Capture final system state
        try:
            process = psutil.Process()
            self.cpu_percent_after = process.cpu_percent()
            memory_info = process.memory_info()
            self.memory_mb_after = memory_info.rss / 1024 / 1024
            
            if self.memory_mb_before is not None:
                self.memory_delta_mb = self.memory_mb_after - self.memory_mb_before
        except:
            pass  # Non-critical if psutil fails
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert None values and format timestamps
        return {k: v for k, v in data.items() if v is not None}


@dataclass
class OperationStats:
    """Statistical analysis for operation type"""
    operation_type: OperationType
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    
    # Timing stats
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    median_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    p99_duration_ms: float = 0.0
    
    # Resource usage
    avg_memory_delta_mb: float = 0.0
    max_memory_delta_mb: float = 0.0
    avg_cpu_usage: float = 0.0
    
    # Recent performance (last 100 calls)
    recent_durations: deque = None
    
    def __post_init__(self):
        if self.recent_durations is None:
            self.recent_durations = deque(maxlen=100)
    
    def update(self, metrics: PerformanceMetrics):
        """Update statistics with new metrics"""
        if not metrics.duration_ms:
            return
        
        self.total_calls += 1
        
        if metrics.success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
        
        # Update timing stats
        duration = metrics.duration_ms
        self.recent_durations.append(duration)
        
        self.min_duration_ms = min(self.min_duration_ms, duration)
        self.max_duration_ms = max(self.max_duration_ms, duration)
        
        # Calculate percentiles from recent data
        if self.recent_durations:
            sorted_durations = sorted(self.recent_durations)
            self.median_duration_ms = statistics.median(sorted_durations)
            
            if len(sorted_durations) >= 20:  # Need reasonable sample size
                self.p95_duration_ms = sorted_durations[int(len(sorted_durations) * 0.95)]
                self.p99_duration_ms = sorted_durations[int(len(sorted_durations) * 0.99)]
            
            self.avg_duration_ms = statistics.mean(sorted_durations)
        
        # Update resource stats
        if metrics.memory_delta_mb is not None:
            if self.total_calls == 1:
                self.avg_memory_delta_mb = metrics.memory_delta_mb
                self.max_memory_delta_mb = abs(metrics.memory_delta_mb)
            else:
                # Running average
                self.avg_memory_delta_mb = (
                    (self.avg_memory_delta_mb * (self.total_calls - 1) + metrics.memory_delta_mb) 
                    / self.total_calls
                )
                self.max_memory_delta_mb = max(self.max_memory_delta_mb, abs(metrics.memory_delta_mb))
        
        if metrics.cpu_percent_after is not None:
            if self.total_calls == 1:
                self.avg_cpu_usage = metrics.cpu_percent_after
            else:
                self.avg_cpu_usage = (
                    (self.avg_cpu_usage * (self.total_calls - 1) + metrics.cpu_percent_after)
                    / self.total_calls
                )


class PerformanceThresholds:
    """Performance threshold configuration"""
    
    def __init__(self):
        # Default thresholds in milliseconds
        self.thresholds = {
            # Vision system
            ('vision_system', 'screenshot'): {
                'warning': 100.0,
                'critical': 500.0
            },
            ('vision_system', 'ocr_processing'): {
                'warning': 300.0,
                'critical': 800.0
            },
            ('vision_system', 'capture_and_process'): {
                'warning': 500.0,
                'critical': 1000.0  # Our main target
            },
            
            # Database operations  
            ('database_manager', 'insert'): {
                'warning': 50.0,
                'critical': 200.0
            },
            ('database_manager', 'query'): {
                'warning': 30.0,
                'critical': 100.0
            },
            ('database_manager', 'batch_operation'): {
                'warning': 100.0,
                'critical': 500.0
            },
            
            # Hotkey processing
            ('hotkey_manager', 'process_hotkey'): {
                'warning': 10.0,
                'critical': 50.0
            },
            
            # Default thresholds
            'default': {
                'warning': 200.0,
                'critical': 1000.0
            }
        }
    
    def get_threshold(self, component: str, operation: str, level: str) -> float:
        """Get performance threshold for operation"""
        key = (component, operation)
        if key in self.thresholds:
            return self.thresholds[key].get(level, self.thresholds['default'][level])
        return self.thresholds['default'][level]


class PerformanceMonitor:
    """Comprehensive performance monitoring system"""
    
    def __init__(self):
        self.logger = get_logger('performance_monitor')
        
        # Active operations tracking
        self._active_operations = {}
        self._operation_lock = threading.RLock()
        
        # Historical data storage
        self._completed_operations = deque(maxlen=10000)  # Keep last 10K operations
        self._operation_stats = {}  # OperationType -> OperationStats
        
        # Thresholds
        self.thresholds = PerformanceThresholds()
        
        # System monitoring
        self._system_metrics = deque(maxlen=1440)  # 24 hours at 1-minute intervals
        self._system_monitoring_active = True
        
        # Performance alerts
        self._alert_callbacks = []
        
        # Start background monitoring
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
    
    def start_operation(self, component: str, operation: str, 
                       trace_id: Optional[str] = None,
                       context: Optional[Dict[str, Any]] = None) -> str:
        """Start tracking a new operation"""
        if not trace_id:
            trace_id = f"{component}_{operation}_{int(time.time() * 1000)}"
        
        # Capture initial system state
        cpu_percent = None
        memory_mb = None
        try:
            process = psutil.Process()
            cpu_percent = process.cpu_percent()
            memory_mb = process.memory_info().rss / 1024 / 1024
        except:
            pass
        
        metrics = PerformanceMetrics(
            trace_id=trace_id,
            component=component,
            operation=operation,
            start_time=time.time(),
            cpu_percent_before=cpu_percent,
            memory_mb_before=memory_mb,
            context=context
        )
        
        with self._operation_lock:
            self._active_operations[trace_id] = metrics
        
        self.logger.trace(
            f"Started operation: {component}.{operation}",
            extra_data={
                'trace_id': trace_id,
                'component': component,
                'operation': operation,
                'start_time': metrics.start_time,
                'context': context
            }
        )
        
        return trace_id
    
    def finish_operation(self, trace_id: str, success: bool = True, 
                        error_count: int = 0, 
                        operation_data: Optional[Dict[str, Any]] = None):
        """Finish tracking an operation"""
        with self._operation_lock:
            if trace_id not in self._active_operations:
                self.logger.warning(f"Attempted to finish unknown operation: {trace_id}")
                return
            
            metrics = self._active_operations.pop(trace_id)
        
        # Finish metrics calculation
        metrics.finish(success=success, error_count=error_count)
        
        # Add operation-specific data
        if operation_data:
            if metrics.context:
                metrics.context.update(operation_data)
            else:
                metrics.context = operation_data
        
        # Store completed operation
        self._completed_operations.append(metrics)
        
        # Update statistics
        op_type = OperationType(metrics.component, metrics.operation)
        if op_type not in self._operation_stats:
            self._operation_stats[op_type] = OperationStats(operation_type=op_type)
        
        self._operation_stats[op_type].update(metrics)
        
        # Check performance thresholds
        self._check_performance_thresholds(metrics)
        
        # Log performance
        self._log_performance_metrics(metrics)
    
    def _check_performance_thresholds(self, metrics: PerformanceMetrics):
        """Check if operation exceeded performance thresholds"""
        if not metrics.duration_ms:
            return
        
        warning_threshold = self.thresholds.get_threshold(
            metrics.component, metrics.operation, 'warning'
        )
        critical_threshold = self.thresholds.get_threshold(
            metrics.component, metrics.operation, 'critical'
        )
        
        if metrics.duration_ms >= critical_threshold:
            self.logger.critical(
                f"CRITICAL: Operation {metrics.component}.{metrics.operation} "
                f"took {metrics.duration_ms:.2f}ms (threshold: {critical_threshold}ms)",
                extra_data={
                    'trace_id': metrics.trace_id,
                    'duration_ms': metrics.duration_ms,
                    'threshold_ms': critical_threshold,
                    'performance_level': 'critical'
                }
            )
            self._trigger_alerts('critical', metrics)
            
        elif metrics.duration_ms >= warning_threshold:
            self.logger.warning(
                f"SLOW: Operation {metrics.component}.{metrics.operation} "
                f"took {metrics.duration_ms:.2f}ms (threshold: {warning_threshold}ms)",
                extra_data={
                    'trace_id': metrics.trace_id,
                    'duration_ms': metrics.duration_ms,
                    'threshold_ms': warning_threshold,
                    'performance_level': 'warning'
                }
            )
    
    def _log_performance_metrics(self, metrics: PerformanceMetrics):
        """Log detailed performance metrics"""
        log_data = {
            'trace_id': metrics.trace_id,
            'component': metrics.component,
            'operation': metrics.operation,
            'duration_ms': metrics.duration_ms,
            'success': metrics.success,
            'memory_delta_mb': metrics.memory_delta_mb,
            'cpu_usage': metrics.cpu_percent_after
        }
        
        if metrics.context:
            log_data['context'] = metrics.context
        
        self.logger.performance(
            f"Operation completed: {metrics.component}.{metrics.operation} "
            f"({metrics.duration_ms:.2f}ms)",
            metrics=log_data
        )
    
    def get_operation_stats(self, component: Optional[str] = None,
                          operation: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics for operations"""
        with self._operation_lock:
            if component and operation:
                # Get stats for specific operation
                op_type = OperationType(component, operation)
                if op_type in self._operation_stats:
                    stats = self._operation_stats[op_type]
                    return {
                        'operation_type': f"{component}.{operation}",
                        'total_calls': stats.total_calls,
                        'success_rate': stats.successful_calls / max(stats.total_calls, 1),
                        'avg_duration_ms': stats.avg_duration_ms,
                        'median_duration_ms': stats.median_duration_ms,
                        'p95_duration_ms': stats.p95_duration_ms,
                        'min_duration_ms': stats.min_duration_ms,
                        'max_duration_ms': stats.max_duration_ms,
                        'avg_memory_delta_mb': stats.avg_memory_delta_mb,
                        'avg_cpu_usage': stats.avg_cpu_usage
                    }
                else:
                    return {}
            
            # Get summary stats for all operations
            summary = {
                'total_operations': len(self._completed_operations),
                'active_operations': len(self._active_operations),
                'by_component': defaultdict(lambda: {
                    'count': 0,
                    'avg_duration': 0.0,
                    'success_rate': 0.0
                }),
                'slowest_operations': [],
                'most_frequent_operations': []
            }
            
            # Aggregate by component
            for op_type, stats in self._operation_stats.items():
                comp_stats = summary['by_component'][op_type.component]
                comp_stats['count'] += stats.total_calls
                comp_stats['avg_duration'] = (
                    comp_stats['avg_duration'] * (comp_stats['count'] - stats.total_calls) +
                    stats.avg_duration_ms * stats.total_calls
                ) / comp_stats['count']
                comp_stats['success_rate'] = stats.successful_calls / max(stats.total_calls, 1)
            
            # Get slowest operations
            slowest = sorted(
                self._operation_stats.items(),
                key=lambda x: x[1].avg_duration_ms,
                reverse=True
            )[:10]
            
            summary['slowest_operations'] = [
                {
                    'operation': f"{op_type.component}.{op_type.operation}",
                    'avg_duration_ms': stats.avg_duration_ms,
                    'call_count': stats.total_calls
                }
                for op_type, stats in slowest
            ]
            
            # Get most frequent operations
            most_frequent = sorted(
                self._operation_stats.items(),
                key=lambda x: x[1].total_calls,
                reverse=True
            )[:10]
            
            summary['most_frequent_operations'] = [
                {
                    'operation': f"{op_type.component}.{op_type.operation}",
                    'call_count': stats.total_calls,
                    'avg_duration_ms': stats.avg_duration_ms
                }
                for op_type, stats in most_frequent
            ]
        
        return dict(summary)
    
    def get_system_metrics(self, hours: int = 1) -> Dict[str, Any]:
        """Get system performance metrics"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        # Get recent system metrics
        recent_metrics = [
            metric for metric in self._system_metrics
            if metric['timestamp'] >= cutoff
        ]
        
        if not recent_metrics:
            return {}
        
        # Calculate aggregated metrics
        cpu_values = [m['cpu_percent'] for m in recent_metrics if m.get('cpu_percent')]
        memory_values = [m['memory_mb'] for m in recent_metrics if m.get('memory_mb')]
        
        return {
            'cpu_usage': {
                'current': cpu_values[-1] if cpu_values else 0,
                'average': statistics.mean(cpu_values) if cpu_values else 0,
                'max': max(cpu_values) if cpu_values else 0
            },
            'memory_usage': {
                'current_mb': memory_values[-1] if memory_values else 0,
                'average_mb': statistics.mean(memory_values) if memory_values else 0,
                'max_mb': max(memory_values) if memory_values else 0
            },
            'sample_count': len(recent_metrics)
        }
    
    def _monitoring_loop(self):
        """Background monitoring loop for system metrics"""
        while self._system_monitoring_active:
            try:
                # Collect system metrics
                try:
                    process = psutil.Process()
                    cpu_percent = process.cpu_percent()
                    memory_info = process.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024
                    
                    metric = {
                        'timestamp': datetime.now(),
                        'cpu_percent': cpu_percent,
                        'memory_mb': memory_mb,
                        'active_operations': len(self._active_operations)
                    }
                    
                    self._system_metrics.append(metric)
                    
                except Exception as e:
                    self.logger.debug(f"Failed to collect system metrics: {e}")
                
                # Check for long-running operations
                self._check_long_running_operations()
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in performance monitoring loop: {e}")
                time.sleep(60)
    
    def _check_long_running_operations(self):
        """Check for operations that have been running too long"""
        current_time = time.time()
        
        with self._operation_lock:
            for trace_id, metrics in list(self._active_operations.items()):
                runtime_ms = (current_time - metrics.start_time) * 1000
                
                critical_threshold = self.thresholds.get_threshold(
                    metrics.component, metrics.operation, 'critical'
                )
                
                if runtime_ms > critical_threshold * 2:  # 2x critical threshold
                    self.logger.warning(
                        f"Long-running operation detected: {metrics.component}.{metrics.operation} "
                        f"running for {runtime_ms:.2f}ms",
                        extra_data={
                            'trace_id': trace_id,
                            'runtime_ms': runtime_ms,
                            'component': metrics.component,
                            'operation': metrics.operation
                        }
                    )
    
    def add_alert_callback(self, callback: Callable[[str, PerformanceMetrics], None]):
        """Add callback for performance alerts"""
        self._alert_callbacks.append(callback)
    
    def _trigger_alerts(self, level: str, metrics: PerformanceMetrics):
        """Trigger performance alerts"""
        for callback in self._alert_callbacks:
            try:
                callback(level, metrics)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")
    
    def generate_performance_report(self, hours: int = 24) -> str:
        """Generate comprehensive performance report"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        # Get operations from time period
        recent_ops = [
            op for op in self._completed_operations
            if datetime.fromtimestamp(op.start_time) >= cutoff
        ]
        
        report = []
        report.append(f"Performance Report - Last {hours} hours")
        report.append("=" * 50)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Operations: {len(recent_ops)}")
        report.append("")
        
        if recent_ops:
            # Success rate
            successful = len([op for op in recent_ops if op.success])
            success_rate = successful / len(recent_ops) * 100
            report.append(f"Overall Success Rate: {success_rate:.1f}%")
            
            # Duration statistics
            durations = [op.duration_ms for op in recent_ops if op.duration_ms]
            if durations:
                report.append(f"Average Duration: {statistics.mean(durations):.2f}ms")
                report.append(f"Median Duration: {statistics.median(durations):.2f}ms")
                report.append(f"95th Percentile: {sorted(durations)[int(len(durations) * 0.95)]:.2f}ms")
                report.append(f"Max Duration: {max(durations):.2f}ms")
            
            # Component breakdown
            report.append("\nBy Component:")
            by_component = defaultdict(list)
            for op in recent_ops:
                by_component[op.component].append(op)
            
            for component, ops in by_component.items():
                durations = [op.duration_ms for op in ops if op.duration_ms]
                success_rate = len([op for op in ops if op.success]) / len(ops) * 100
                avg_duration = statistics.mean(durations) if durations else 0
                
                report.append(f"  {component}: {len(ops)} ops, "
                            f"{success_rate:.1f}% success, "
                            f"{avg_duration:.2f}ms avg")
        
        # System metrics
        system_metrics = self.get_system_metrics(hours)
        if system_metrics:
            report.append("\nSystem Metrics:")
            report.append(f"  CPU Usage: {system_metrics['cpu_usage']['average']:.1f}% avg, "
                         f"{system_metrics['cpu_usage']['max']:.1f}% max")
            report.append(f"  Memory Usage: {system_metrics['memory_usage']['average_mb']:.1f}MB avg, "
                         f"{system_metrics['memory_usage']['max_mb']:.1f}MB max")
        
        return "\n".join(report)
    
    def shutdown(self):
        """Shutdown performance monitor"""
        self._system_monitoring_active = False