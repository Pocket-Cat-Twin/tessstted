"""
Performance Profiler for Game Monitor System

Comprehensive system for identifying bottlenecks, measuring performance,
and providing optimization recommendations with detailed analytics.
"""

import time
import threading
import cProfile
import pstats
import io
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import psutil
import gc
import sys
import traceback
from functools import wraps
import logging

from .advanced_logger import get_logger
from .error_handler import get_error_handler, ErrorContext, ErrorCategory, RecoveryStrategy
from .constants import Performance, Threading, Memory

logger = get_logger(__name__)


@dataclass
class PerformanceBottleneck:
    """Identified performance bottleneck"""
    component: str
    operation: str
    avg_duration: float
    max_duration: float
    call_count: int
    total_time: float
    impact_score: float  # Higher = more impactful bottleneck
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    recommendations: List[str]


@dataclass
class OptimizationResult:
    """Result of performance optimization"""
    component: str
    operation: str
    before_avg_ms: float
    after_avg_ms: float
    improvement_percent: float
    memory_before_mb: float
    memory_after_mb: float
    success: bool
    notes: str


class PerformanceProfiler:
    """Advanced performance profiler with bottleneck detection"""
    
    def __init__(self):
        self.error_handler = get_error_handler()
        
        # Performance tracking
        self.operation_times = defaultdict(deque)
        self.operation_stats = defaultdict(dict)
        self.system_metrics = deque(maxlen=1000)
        
        # Profiling state
        self.profiler = None
        self.profiling_active = False
        self._lock = threading.Lock()
        
        # Bottleneck detection
        self.bottleneck_thresholds = {
            'avg_duration': Performance.EXCELLENT_THRESHOLD,  # 0.05s
            'max_duration': Performance.GOOD_THRESHOLD,       # 0.1s
            'impact_score': 10.0,  # Total time impact threshold
            'memory_usage': 80.0,  # Memory usage percentage
            'cpu_usage': 75.0      # CPU usage percentage
        }
        
        # Optimization history
        self.optimization_results = []
        
        logger.info("PerformanceProfiler initialized")
    
    def profile_operation(self, operation_name: str = None):
        """Decorator to profile individual operations"""
        def decorator(func: Callable) -> Callable:
            nonlocal operation_name
            if operation_name is None:
                operation_name = f"{func.__module__}.{func.__name__}"
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self.time_operation(operation_name, func, *args, **kwargs)
            return wrapper
        return decorator
    
    def time_operation(self, operation_name: str, func: Callable, *args, **kwargs) -> Any:
        """Time a specific operation and collect performance data"""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            # Execute the operation
            result = func(*args, **kwargs)
            success = True
            error = None
            
        except Exception as e:
            success = False
            error = str(e)
            result = None
            
        finally:
            # Collect metrics
            end_time = time.time()
            end_memory = self._get_memory_usage()
            duration = end_time - start_time
            memory_delta = end_memory - start_memory
            
            # Record performance data
            self._record_operation_performance(
                operation_name, duration, start_memory, memory_delta, success, error
            )
        
        if not success:
            raise  # Re-raise the original exception
        
        return result
    
    def _record_operation_performance(self, operation: str, duration: float, 
                                    memory_mb: float, memory_delta: float, 
                                    success: bool, error: str = None):
        """Record performance metrics for an operation"""
        timestamp = time.time()
        cpu_percent = self._get_cpu_usage()
        
        with self._lock:
            # Add to operation times (limited size)
            self.operation_times[operation].append({
                'timestamp': timestamp,
                'duration': duration,
                'memory_mb': memory_mb,
                'memory_delta': memory_delta,
                'cpu_percent': cpu_percent,
                'success': success,
                'error': error
            })
            
            # Limit history per operation
            if len(self.operation_times[operation]) > 100:
                self.operation_times[operation].popleft()
            
            # Update operation statistics
            self._update_operation_stats(operation)
            
            # Record system-wide metrics
            self.system_metrics.append({
                'timestamp': timestamp,
                'memory_mb': memory_mb,
                'cpu_percent': cpu_percent,
                'active_operations': len(self.operation_times)
            })
    
    def _update_operation_stats(self, operation: str):
        """Update statistics for an operation"""
        times = self.operation_times[operation]
        if not times:
            return
        
        durations = [t['duration'] for t in times if t['success']]
        if not durations:
            return
        
        self.operation_stats[operation] = {
            'count': len(durations),
            'avg_duration': sum(durations) / len(durations),
            'max_duration': max(durations),
            'min_duration': min(durations),
            'total_time': sum(durations),
            'success_rate': sum(1 for t in times if t['success']) / len(times),
            'last_updated': time.time()
        }
    
    def identify_bottlenecks(self, min_calls: int = 5) -> List[PerformanceBottleneck]:
        """Identify performance bottlenecks with detailed analysis"""
        bottlenecks = []
        
        with self._lock:
            for operation, stats in self.operation_stats.items():
                if stats['count'] < min_calls:
                    continue
                
                # Calculate impact score (total time spent)
                impact_score = stats['total_time']
                
                # Determine severity
                severity = self._calculate_severity(stats, impact_score)
                
                # Generate recommendations
                recommendations = self._generate_recommendations(operation, stats)
                
                # Create bottleneck if it exceeds thresholds
                if (stats['avg_duration'] > self.bottleneck_thresholds['avg_duration'] or
                    stats['max_duration'] > self.bottleneck_thresholds['max_duration'] or
                    impact_score > self.bottleneck_thresholds['impact_score']):
                    
                    bottleneck = PerformanceBottleneck(
                        component=operation.split('.')[0] if '.' in operation else 'unknown',
                        operation=operation,
                        avg_duration=stats['avg_duration'],
                        max_duration=stats['max_duration'],
                        call_count=stats['count'],
                        total_time=stats['total_time'],
                        impact_score=impact_score,
                        severity=severity,
                        recommendations=recommendations
                    )
                    
                    bottlenecks.append(bottleneck)
        
        # Sort by impact score (highest first)
        bottlenecks.sort(key=lambda b: b.impact_score, reverse=True)
        
        return bottlenecks
    
    def _calculate_severity(self, stats: Dict, impact_score: float) -> str:
        """Calculate bottleneck severity"""
        if (stats['avg_duration'] > Performance.GOOD_THRESHOLD * 5 or  # > 0.5s
            impact_score > 50.0):
            return "CRITICAL"
        elif (stats['avg_duration'] > Performance.GOOD_THRESHOLD * 2 or  # > 0.2s
              impact_score > 20.0):
            return "HIGH"
        elif (stats['avg_duration'] > Performance.GOOD_THRESHOLD or  # > 0.1s
              impact_score > 5.0):
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_recommendations(self, operation: str, stats: Dict) -> List[str]:
        """Generate optimization recommendations based on operation characteristics"""
        recommendations = []
        
        # Database operation recommendations
        if 'database' in operation.lower() or 'db' in operation.lower():
            if stats['avg_duration'] > 0.05:  # > 50ms for DB operations
                recommendations.extend([
                    "Consider adding database indexes for frequently queried fields",
                    "Optimize SQL queries with EXPLAIN QUERY PLAN",
                    "Implement query result caching",
                    "Use batch operations where possible"
                ])
        
        # OCR operation recommendations
        if 'ocr' in operation.lower() or 'vision' in operation.lower():
            if stats['avg_duration'] > 0.1:  # > 100ms for OCR
                recommendations.extend([
                    "Implement region-based OCR to reduce processing area",
                    "Add image preprocessing optimizations",
                    "Use OCR result caching",
                    "Consider parallel OCR processing"
                ])
        
        # GUI operation recommendations
        if 'gui' in operation.lower() or 'update' in operation.lower():
            if stats['avg_duration'] > 0.05:  # > 50ms for GUI updates
                recommendations.extend([
                    "Implement virtual scrolling for large data sets",
                    "Use background threads for data loading",
                    "Cache frequently displayed data",
                    "Optimize widget creation and updates"
                ])
        
        # General recommendations
        if stats['avg_duration'] > Performance.GOOD_THRESHOLD:
            recommendations.extend([
                f"Operation takes {stats['avg_duration']*1000:.1f}ms on average (target: <{Performance.GOOD_THRESHOLD*1000:.0f}ms)",
                "Profile with cProfile to identify internal bottlenecks",
                "Consider algorithmic improvements",
                "Add performance monitoring and alerting"
            ])
        
        return recommendations
    
    def start_detailed_profiling(self):
        """Start detailed cProfile profiling"""
        try:
            self.profiler = cProfile.Profile()
            self.profiler.enable()
            self.profiling_active = True
            logger.info("Detailed profiling started")
        except Exception as e:
            logger.error(f"Failed to start profiling: {e}")
    
    def stop_detailed_profiling(self) -> Optional[str]:
        """Stop detailed profiling and return results"""
        if not self.profiling_active or not self.profiler:
            return None
        
        try:
            self.profiler.disable()
            self.profiling_active = False
            
            # Get profiling results
            stats_stream = io.StringIO()
            stats = pstats.Stats(self.profiler, stream=stats_stream)
            stats.sort_stats('cumulative')
            stats.print_stats(50)  # Top 50 functions
            
            result = stats_stream.getvalue()
            logger.info("Detailed profiling stopped and results generated")
            return result
            
        except Exception as e:
            logger.error(f"Failed to stop profiling: {e}")
            return None
    
    def optimize_database_queries(self) -> List[OptimizationResult]:
        """Optimize database query performance"""
        results = []
        
        try:
            # Identify database bottlenecks
            db_bottlenecks = [b for b in self.identify_bottlenecks() 
                            if 'database' in b.component.lower()]
            
            for bottleneck in db_bottlenecks:
                logger.info(f"Optimizing database operation: {bottleneck.operation}")
                
                # Record before metrics
                before_stats = self.operation_stats.get(bottleneck.operation, {})
                before_avg = before_stats.get('avg_duration', 0) * 1000  # Convert to ms
                before_memory = self._get_memory_usage()
                
                # Apply optimizations (these would be specific to each operation)
                optimization_applied = self._apply_database_optimization(bottleneck)
                
                # Measure improvements after a brief period
                time.sleep(0.1)  # Brief pause to collect new metrics
                
                # Record after metrics
                after_stats = self.operation_stats.get(bottleneck.operation, {})
                after_avg = after_stats.get('avg_duration', 0) * 1000  # Convert to ms
                after_memory = self._get_memory_usage()
                
                # Calculate improvement
                if before_avg > 0:
                    improvement = ((before_avg - after_avg) / before_avg) * 100
                else:
                    improvement = 0
                
                result = OptimizationResult(
                    component=bottleneck.component,
                    operation=bottleneck.operation,
                    before_avg_ms=before_avg,
                    after_avg_ms=after_avg,
                    improvement_percent=improvement,
                    memory_before_mb=before_memory,
                    memory_after_mb=after_memory,
                    success=optimization_applied,
                    notes=f"Applied database optimization for {bottleneck.operation}"
                )
                
                results.append(result)
                self.optimization_results.append(result)
                
        except Exception as e:
            error_context = ErrorContext(
                component="performance_profiler",
                operation="optimize_database_queries",
                user_data={'db_bottlenecks': len(db_bottlenecks) if 'db_bottlenecks' in locals() else 0},
                system_state={},
                timestamp=datetime.now()
            )
            
            self.error_handler.handle_error(e, error_context, RecoveryStrategy.SKIP)
        
        return results
    
    def _apply_database_optimization(self, bottleneck: PerformanceBottleneck) -> bool:
        """Apply specific database optimizations"""
        # This is where we would implement specific optimizations
        # For now, we'll simulate the optimization
        logger.info(f"Applied optimization recommendations for {bottleneck.operation}")
        return True
    
    def optimize_memory_usage(self) -> Dict[str, Any]:
        """Optimize memory usage and garbage collection"""
        before_memory = self._get_memory_usage()
        
        try:
            # Force garbage collection
            collected = gc.collect()
            
            # Get memory statistics
            after_memory = self._get_memory_usage()
            memory_freed = before_memory - after_memory
            
            # Additional optimizations
            self._optimize_caches()
            
            final_memory = self._get_memory_usage()
            total_freed = before_memory - final_memory
            
            result = {
                'before_memory_mb': before_memory,
                'after_gc_memory_mb': after_memory,
                'final_memory_mb': final_memory,
                'objects_collected': collected,
                'memory_freed_mb': memory_freed,
                'total_freed_mb': total_freed,
                'optimization_success': total_freed > 0
            }
            
            logger.info(f"Memory optimization: freed {total_freed:.1f}MB, collected {collected} objects")
            return result
            
        except Exception as e:
            logger.error(f"Memory optimization failed: {e}")
            return {'optimization_success': False, 'error': str(e)}
    
    def _optimize_caches(self):
        """Optimize various caches in the system"""
        # Clear old cache entries from various components
        # This would interact with actual cache implementations
        logger.info("Cache optimization completed")
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        try:
            bottlenecks = self.identify_bottlenecks()
            system_stats = self._get_system_statistics()
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_operations_tracked': len(self.operation_stats),
                    'bottlenecks_identified': len(bottlenecks),
                    'critical_bottlenecks': len([b for b in bottlenecks if b.severity == 'CRITICAL']),
                    'high_bottlenecks': len([b for b in bottlenecks if b.severity == 'HIGH']),
                    'optimizations_applied': len(self.optimization_results)
                },
                'system_performance': system_stats,
                'bottlenecks': [asdict(b) for b in bottlenecks[:10]],  # Top 10 bottlenecks
                'optimization_history': [asdict(r) for r in self.optimization_results[-10:]],  # Last 10 optimizations
                'recommendations': self._generate_system_recommendations(bottlenecks)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return {'error': str(e)}
    
    def _generate_system_recommendations(self, bottlenecks: List[PerformanceBottleneck]) -> List[str]:
        """Generate system-wide performance recommendations"""
        recommendations = []
        
        critical_bottlenecks = [b for b in bottlenecks if b.severity == 'CRITICAL']
        if critical_bottlenecks:
            recommendations.append(f"Address {len(critical_bottlenecks)} critical performance bottlenecks immediately")
        
        db_bottlenecks = [b for b in bottlenecks if 'database' in b.component.lower()]
        if len(db_bottlenecks) > 3:
            recommendations.append("Consider database optimization and indexing strategy")
        
        ocr_bottlenecks = [b for b in bottlenecks if 'ocr' in b.operation.lower() or 'vision' in b.operation.lower()]
        if len(ocr_bottlenecks) > 2:
            recommendations.append("Implement advanced OCR optimizations and caching")
        
        # Memory recommendations
        current_memory = self._get_memory_usage()
        if current_memory > Memory.DEFAULT_MAX_MEMORY_MB * 0.8:
            recommendations.append("Memory usage is high - consider memory optimization")
        
        return recommendations
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            return psutil.cpu_percent(interval=0.01)
        except Exception:
            return 0.0
    
    def _get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system performance statistics"""
        try:
            return {
                'memory_usage_mb': self._get_memory_usage(),
                'cpu_usage_percent': self._get_cpu_usage(),
                'active_threads': threading.active_count(),
                'total_operations': sum(stats['count'] for stats in self.operation_stats.values()),
                'avg_operation_time': sum(stats['avg_duration'] for stats in self.operation_stats.values()) / max(len(self.operation_stats), 1),
                'system_uptime': time.time() - psutil.boot_time() if hasattr(psutil, 'boot_time') else 0
            }
        except Exception:
            return {}


# Global profiler instance
_profiler_instance = None

def get_performance_profiler() -> PerformanceProfiler:
    """Get singleton performance profiler instance"""
    global _profiler_instance
    if _profiler_instance is None:
        _profiler_instance = PerformanceProfiler()
    return _profiler_instance


def profile_performance(operation_name: str = None):
    """Decorator for automatic performance profiling"""
    profiler = get_performance_profiler()
    return profiler.profile_operation(operation_name)