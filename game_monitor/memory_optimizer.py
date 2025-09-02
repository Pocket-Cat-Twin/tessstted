"""
Memory Optimization System for Game Monitor

Advanced memory management, cache optimization, and garbage collection
strategies to maintain optimal memory usage and prevent memory leaks.
"""

import gc
import weakref
import threading
import time
import sys
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict, OrderedDict
import psutil
import logging

from .advanced_logger import get_logger
from .error_handler import get_error_handler, ErrorContext, ErrorCategory, RecoveryStrategy
from .performance_profiler import get_performance_profiler, profile_performance
from .constants import Memory, Performance

logger = get_logger(__name__)


@dataclass
class MemoryUsage:
    """Memory usage snapshot"""
    timestamp: float
    rss_mb: float  # Resident Set Size
    vms_mb: float  # Virtual Memory Size
    percent: float  # Memory percentage
    available_mb: float
    gc_objects: int
    gc_generations: Tuple[int, int, int]


@dataclass
class CacheStats:
    """Cache statistics and optimization info"""
    cache_name: str
    current_size: int
    max_size: int
    hit_rate: float
    memory_usage_mb: float
    optimization_potential: str


class MemoryTracker:
    """Tracks memory usage and identifies memory leaks"""
    
    def __init__(self, max_snapshots: int = 1000):
        self.max_snapshots = max_snapshots
        self.snapshots = []
        self.object_tracking = defaultdict(list)
        self._lock = threading.Lock()
        
        # Track specific object types that commonly cause leaks
        self.tracked_types = {
            'dict', 'list', 'tuple', 'set', 'str',
            'function', 'method', 'frame', 'thread'
        }
    
    def take_snapshot(self) -> MemoryUsage:
        """Take a memory usage snapshot"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            system_memory = psutil.virtual_memory()
            
            # Get garbage collection stats
            gc_stats = gc.get_stats()
            gc_objects = len(gc.get_objects())
            gc_generations = tuple(len(gc.get_objects(gen)) for gen in range(3))
            
            snapshot = MemoryUsage(
                timestamp=time.time(),
                rss_mb=memory_info.rss / 1024 / 1024,
                vms_mb=memory_info.vms / 1024 / 1024,
                percent=system_memory.percent,
                available_mb=system_memory.available / 1024 / 1024,
                gc_objects=gc_objects,
                gc_generations=gc_generations
            )
            
            with self._lock:
                self.snapshots.append(snapshot)
                if len(self.snapshots) > self.max_snapshots:
                    self.snapshots.pop(0)
            
            return snapshot
            
        except Exception as e:
            logger.warning(f"Failed to take memory snapshot: {e}")
            return MemoryUsage(
                timestamp=time.time(), rss_mb=0, vms_mb=0, 
                percent=0, available_mb=0, gc_objects=0, 
                gc_generations=(0, 0, 0)
            )
    
    def detect_memory_leaks(self, window_minutes: int = 10) -> List[Dict[str, Any]]:
        """Detect potential memory leaks by analyzing trends"""
        leaks = []
        cutoff_time = time.time() - (window_minutes * 60)
        
        with self._lock:
            recent_snapshots = [s for s in self.snapshots if s.timestamp > cutoff_time]
        
        if len(recent_snapshots) < 5:
            return leaks
        
        # Analyze memory growth trends
        memory_values = [s.rss_mb for s in recent_snapshots]
        
        # Simple trend analysis - look for consistent growth
        if len(memory_values) > 1:
            growth_rate = (memory_values[-1] - memory_values[0]) / len(memory_values)
            
            if growth_rate > 1.0:  # More than 1MB growth per snapshot
                leaks.append({
                    'type': 'memory_growth',
                    'growth_rate_mb_per_minute': growth_rate * (60 / window_minutes),
                    'severity': 'HIGH' if growth_rate > 5.0 else 'MEDIUM',
                    'current_usage_mb': memory_values[-1],
                    'recommendation': 'Investigate memory allocation patterns'
                })
        
        # Check for excessive garbage collection objects
        gc_objects = [s.gc_objects for s in recent_snapshots]
        if gc_objects and gc_objects[-1] > 100000:  # More than 100k objects
            avg_objects = sum(gc_objects) / len(gc_objects)
            if avg_objects > 50000:
                leaks.append({
                    'type': 'excessive_objects',
                    'current_objects': gc_objects[-1],
                    'average_objects': avg_objects,
                    'severity': 'MEDIUM',
                    'recommendation': 'Review object creation and cleanup patterns'
                })
        
        return leaks
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        if not self.snapshots:
            return {'error': 'No memory snapshots available'}
        
        with self._lock:
            latest = self.snapshots[-1]
            
            if len(self.snapshots) > 1:
                memory_trend = latest.rss_mb - self.snapshots[0].rss_mb
            else:
                memory_trend = 0
        
        return {
            'current_usage_mb': latest.rss_mb,
            'virtual_memory_mb': latest.vms_mb,
            'memory_percent': latest.percent,
            'available_memory_mb': latest.available_mb,
            'gc_objects': latest.gc_objects,
            'memory_trend_mb': memory_trend,
            'snapshots_count': len(self.snapshots),
            'potential_leaks': len(self.detect_memory_leaks())
        }


class CacheOptimizer:
    """Optimizes various caches in the system"""
    
    def __init__(self):
        self.cache_registry = {}
        self.cache_stats = {}
        self._lock = threading.Lock()
    
    def register_cache(self, name: str, cache_obj: Any, max_size: int = None):
        """Register a cache for monitoring and optimization"""
        with self._lock:
            self.cache_registry[name] = {
                'object': weakref.ref(cache_obj),
                'max_size': max_size,
                'registered_at': time.time()
            }
    
    def optimize_cache(self, cache_name: str) -> Dict[str, Any]:
        """Optimize a specific cache"""
        if cache_name not in self.cache_registry:
            return {'error': f'Cache {cache_name} not registered'}
        
        cache_ref = self.cache_registry[cache_name]['object']
        cache_obj = cache_ref()
        
        if cache_obj is None:
            return {'error': f'Cache {cache_name} no longer exists'}
        
        optimization_result = {
            'cache_name': cache_name,
            'actions_taken': [],
            'memory_freed_mb': 0,
            'items_removed': 0
        }
        
        try:
            # Get cache size before optimization
            before_size = self._get_cache_size(cache_obj)
            before_memory = sys.getsizeof(cache_obj) / 1024 / 1024
            
            # Apply optimization strategies
            if hasattr(cache_obj, 'clear'):
                # For dict-like caches, remove old entries
                if isinstance(cache_obj, dict):
                    self._optimize_dict_cache(cache_obj, optimization_result)
                elif isinstance(cache_obj, OrderedDict):
                    self._optimize_ordered_dict_cache(cache_obj, optimization_result)
            
            # Get cache size after optimization
            after_size = self._get_cache_size(cache_obj)
            after_memory = sys.getsizeof(cache_obj) / 1024 / 1024
            
            optimization_result['memory_freed_mb'] = before_memory - after_memory
            optimization_result['items_removed'] = before_size - after_size
            
        except Exception as e:
            optimization_result['error'] = str(e)
        
        return optimization_result
    
    def _optimize_dict_cache(self, cache_dict: dict, result: Dict):
        """Optimize a dictionary-based cache"""
        if not cache_dict:
            return
        
        # Remove items if cache is too large
        max_size = self.cache_registry.get('max_size', 1000)
        if len(cache_dict) > max_size:
            # Keep only the most recent items (if they have timestamps)
            items_to_remove = len(cache_dict) - max_size
            
            # Try to find timestamped items
            timestamped_items = []
            for key, value in cache_dict.items():
                if isinstance(value, dict) and 'timestamp' in value:
                    timestamped_items.append((key, value['timestamp']))
            
            if timestamped_items:
                # Sort by timestamp and remove oldest
                timestamped_items.sort(key=lambda x: x[1])
                for i in range(min(items_to_remove, len(timestamped_items))):
                    del cache_dict[timestamped_items[i][0]]
                
                result['actions_taken'].append(f'Removed {min(items_to_remove, len(timestamped_items))} old items')
    
    def _optimize_ordered_dict_cache(self, cache_dict: OrderedDict, result: Dict):
        """Optimize an OrderedDict-based cache (LRU-style)"""
        max_size = self.cache_registry.get('max_size', 1000)
        if len(cache_dict) > max_size:
            items_to_remove = len(cache_dict) - max_size
            
            # Remove oldest items (FIFO)
            for _ in range(items_to_remove):
                if cache_dict:
                    cache_dict.popitem(last=False)
            
            result['actions_taken'].append(f'Removed {items_to_remove} oldest items')
    
    def _get_cache_size(self, cache_obj: Any) -> int:
        """Get the size of a cache object"""
        if hasattr(cache_obj, '__len__'):
            return len(cache_obj)
        elif hasattr(cache_obj, 'qsize'):  # Queue-like objects
            return cache_obj.qsize()
        else:
            return 0
    
    def get_cache_statistics(self) -> List[CacheStats]:
        """Get statistics for all registered caches"""
        stats = []
        
        with self._lock:
            for name, info in self.cache_registry.items():
                cache_obj = info['object']()
                if cache_obj is None:
                    continue
                
                try:
                    current_size = self._get_cache_size(cache_obj)
                    memory_usage = sys.getsizeof(cache_obj) / 1024 / 1024
                    max_size = info.get('max_size', 'Unknown')
                    
                    # Estimate hit rate (would need instrumentation for accurate rate)
                    estimated_hit_rate = 0.8  # Default estimate
                    
                    # Determine optimization potential
                    if current_size > 1000:
                        optimization_potential = "HIGH - Consider size limits"
                    elif memory_usage > 10:
                        optimization_potential = "MEDIUM - Monitor memory usage"
                    else:
                        optimization_potential = "LOW - Well optimized"
                    
                    stats.append(CacheStats(
                        cache_name=name,
                        current_size=current_size,
                        max_size=max_size,
                        hit_rate=estimated_hit_rate,
                        memory_usage_mb=memory_usage,
                        optimization_potential=optimization_potential
                    ))
                    
                except Exception as e:
                    logger.warning(f"Failed to get stats for cache {name}: {e}")
        
        return stats


class MemoryOptimizer:
    """Main memory optimization coordinator"""
    
    def __init__(self):
        self.error_handler = get_error_handler()
        self.profiler = get_performance_profiler()
        self.memory_tracker = MemoryTracker()
        self.cache_optimizer = CacheOptimizer()
        
        # Optimization settings
        self.gc_threshold_mb = Memory.DEFAULT_MAX_MEMORY_MB * 0.8  # 80% of limit
        self.optimization_interval = 300  # 5 minutes
        self.last_optimization = 0
        
        # Start monitoring
        self._start_monitoring()
        
        logger.info("MemoryOptimizer initialized")
    
    def _start_monitoring(self):
        """Start background memory monitoring"""
        def monitor():
            while True:
                try:
                    self.memory_tracker.take_snapshot()
                    
                    # Check if optimization is needed
                    if self._should_optimize():
                        self.run_optimization()
                    
                    time.sleep(60)  # Monitor every minute
                    
                except Exception as e:
                    logger.error(f"Memory monitoring error: {e}")
                    time.sleep(300)  # Wait longer after errors
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def _should_optimize(self) -> bool:
        """Determine if memory optimization should run"""
        current_time = time.time()
        
        # Time-based optimization
        if current_time - self.last_optimization < self.optimization_interval:
            return False
        
        # Memory threshold-based optimization
        latest_snapshot = self.memory_tracker.snapshots[-1] if self.memory_tracker.snapshots else None
        if latest_snapshot and latest_snapshot.rss_mb > self.gc_threshold_mb:
            return True
        
        # Leak detection-based optimization
        leaks = self.memory_tracker.detect_memory_leaks()
        if any(leak['severity'] in ['HIGH', 'CRITICAL'] for leak in leaks):
            return True
        
        return False
    
    @profile_performance("memory_optimizer.run_optimization")
    def run_optimization(self) -> Dict[str, Any]:
        """Run comprehensive memory optimization"""
        optimization_start = time.time()
        self.last_optimization = optimization_start
        
        results = {
            'timestamp': optimization_start,
            'optimizations': {},
            'memory_before_mb': 0,
            'memory_after_mb': 0,
            'total_time_ms': 0
        }
        
        try:
            # Get memory before optimization
            before_snapshot = self.memory_tracker.take_snapshot()
            results['memory_before_mb'] = before_snapshot.rss_mb
            
            logger.info(f"Starting memory optimization - current usage: {before_snapshot.rss_mb:.1f}MB")
            
            # 1. Garbage collection optimization
            results['optimizations']['garbage_collection'] = self._optimize_garbage_collection()
            
            # 2. Cache optimization
            results['optimizations']['caches'] = self._optimize_all_caches()
            
            # 3. Object cleanup
            results['optimizations']['object_cleanup'] = self._cleanup_unreferenced_objects()
            
            # 4. Memory leak detection and reporting
            results['optimizations']['leak_detection'] = self._detect_and_report_leaks()
            
            # Get memory after optimization
            after_snapshot = self.memory_tracker.take_snapshot()
            results['memory_after_mb'] = after_snapshot.rss_mb
            results['memory_freed_mb'] = before_snapshot.rss_mb - after_snapshot.rss_mb
            
            results['total_time_ms'] = (time.time() - optimization_start) * 1000
            results['success'] = True
            
            logger.info(
                f"Memory optimization completed in {results['total_time_ms']:.1f}ms - "
                f"freed {results['memory_freed_mb']:.1f}MB "
                f"({before_snapshot.rss_mb:.1f}MB -> {after_snapshot.rss_mb:.1f}MB)"
            )
            
        except Exception as e:
            results['success'] = False
            results['error'] = str(e)
            results['total_time_ms'] = (time.time() - optimization_start) * 1000
            
            error_context = ErrorContext(
                component="memory_optimizer",
                operation="run_optimization",
                user_data={'optimization_time_ms': results['total_time_ms']},
                system_state={},
                timestamp=time.time()
            )
            
            self.error_handler.handle_error(Exception(e), error_context, RecoveryStrategy.SKIP)
            logger.error(f"Memory optimization failed: {e}")
        
        return results
    
    def _optimize_garbage_collection(self) -> Dict[str, Any]:
        """Optimize garbage collection"""
        gc_start = time.time()
        
        try:
            # Get GC stats before
            before_objects = len(gc.get_objects())
            
            # Perform full garbage collection
            collected_gen0 = gc.collect(0)
            collected_gen1 = gc.collect(1)
            collected_gen2 = gc.collect(2)
            
            # Get GC stats after
            after_objects = len(gc.get_objects())
            objects_freed = before_objects - after_objects
            
            return {
                'success': True,
                'objects_before': before_objects,
                'objects_after': after_objects,
                'objects_freed': objects_freed,
                'collected_by_generation': [collected_gen0, collected_gen1, collected_gen2],
                'time_ms': (time.time() - gc_start) * 1000
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'time_ms': (time.time() - gc_start) * 1000
            }
    
    def _optimize_all_caches(self) -> Dict[str, Any]:
        """Optimize all registered caches"""
        cache_results = {
            'caches_optimized': 0,
            'total_memory_freed_mb': 0,
            'total_items_removed': 0,
            'details': []
        }
        
        cache_stats = self.cache_optimizer.get_cache_statistics()
        
        for cache_stat in cache_stats:
            if cache_stat.optimization_potential in ['HIGH', 'MEDIUM']:
                result = self.cache_optimizer.optimize_cache(cache_stat.cache_name)
                cache_results['details'].append(result)
                
                if 'error' not in result:
                    cache_results['caches_optimized'] += 1
                    cache_results['total_memory_freed_mb'] += result.get('memory_freed_mb', 0)
                    cache_results['total_items_removed'] += result.get('items_removed', 0)
        
        return cache_results
    
    def _cleanup_unreferenced_objects(self) -> Dict[str, Any]:
        """Clean up unreferenced objects and weak references"""
        cleanup_start = time.time()
        
        try:
            # Clean up weak references
            weakref_count_before = len(weakref.getweakrefs(object))
            
            # Force cleanup of circular references
            gc.set_debug(0)  # Disable debug output
            collected = gc.collect()
            
            weakref_count_after = len(weakref.getweakrefs(object))
            
            return {
                'success': True,
                'circular_refs_collected': collected,
                'weakrefs_before': weakref_count_before,
                'weakrefs_after': weakref_count_after,
                'time_ms': (time.time() - cleanup_start) * 1000
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'time_ms': (time.time() - cleanup_start) * 1000
            }
    
    def _detect_and_report_leaks(self) -> Dict[str, Any]:
        """Detect and report potential memory leaks"""
        leaks = self.memory_tracker.detect_memory_leaks()
        
        leak_report = {
            'leaks_detected': len(leaks),
            'high_severity_leaks': len([l for l in leaks if l.get('severity') == 'HIGH']),
            'medium_severity_leaks': len([l for l in leaks if l.get('severity') == 'MEDIUM']),
            'details': leaks
        }
        
        if leaks:
            logger.warning(f"Detected {len(leaks)} potential memory leaks")
            for leak in leaks:
                if leak.get('severity') == 'HIGH':
                    logger.error(f"High severity memory leak: {leak}")
        
        return leak_report
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive memory usage report"""
        return {
            'timestamp': time.time(),
            'memory_statistics': self.memory_tracker.get_memory_statistics(),
            'cache_statistics': [
                {
                    'cache_name': stat.cache_name,
                    'current_size': stat.current_size,
                    'memory_usage_mb': stat.memory_usage_mb,
                    'optimization_potential': stat.optimization_potential
                }
                for stat in self.cache_optimizer.get_cache_statistics()
            ],
            'potential_leaks': self.memory_tracker.detect_memory_leaks(),
            'gc_statistics': {
                'objects': len(gc.get_objects()),
                'generations': [len(gc.get_objects(i)) for i in range(3)],
                'thresholds': gc.get_threshold()
            }
        }


# Global optimizer instance
_memory_optimizer_instance = None

def get_memory_optimizer() -> MemoryOptimizer:
    """Get singleton memory optimizer instance"""
    global _memory_optimizer_instance
    if _memory_optimizer_instance is None:
        _memory_optimizer_instance = MemoryOptimizer()
    return _memory_optimizer_instance