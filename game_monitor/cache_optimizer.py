"""
Comprehensive Caching Strategy for Game Monitor System

Advanced caching optimizations for OCR results, database queries,
image processing, and frequently accessed data to maximize performance.
"""

import time
import threading
import hashlib
import pickle
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, asdict
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
import weakref
import gc
import logging

from .advanced_logger import get_logger
from .error_handler import get_error_handler, ErrorContext, ErrorCategory, RecoveryStrategy
from .performance_profiler import get_performance_profiler, profile_performance
from .constants import Performance, Memory, Queues

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Individual cache entry with metadata"""
    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    size_bytes: int
    ttl: Optional[float] = None  # Time to live in seconds


@dataclass
class CacheStats:
    """Cache statistics and performance metrics"""
    cache_name: str
    total_entries: int
    total_size_mb: float
    hit_rate: float
    miss_rate: float
    eviction_count: int
    avg_access_time_ms: float
    memory_efficiency: float  # Value per MB
    optimization_score: float  # 0-100


class LRUCache:
    """High-performance LRU cache with advanced features"""
    
    def __init__(self, max_size: int = 1000, ttl: Optional[float] = None, 
                 name: str = "unnamed"):
        self.max_size = max_size
        self.default_ttl = ttl
        self.name = name
        
        # Core cache storage
        self._cache = OrderedDict()
        self._lock = threading.RLock()  # Reentrant lock for nested operations
        
        # Statistics tracking
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_access_time': 0.0,
            'total_accesses': 0,
            'created_at': time.time()
        }
        
        # Background cleanup
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread for TTL expiration"""
        if self.default_ttl is not None:
            def cleanup_expired():
                while not self._stop_cleanup.wait(60):  # Check every minute
                    self._cleanup_expired_entries()
            
            self._cleanup_thread = threading.Thread(target=cleanup_expired, daemon=True)
            self._cleanup_thread.start()
    
    def _cleanup_expired_entries(self):
        """Remove expired entries based on TTL"""
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for key, entry in self._cache.items():
                if entry.ttl and (current_time - entry.created_at) > entry.ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                self.stats['evictions'] += 1
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache with statistics tracking"""
        access_start = time.time()
        
        try:
            with self._lock:
                if key in self._cache:
                    entry = self._cache[key]
                    
                    # Check TTL expiration
                    if entry.ttl and (time.time() - entry.created_at) > entry.ttl:
                        del self._cache[key]
                        self.stats['misses'] += 1
                        return default
                    
                    # Move to end (most recently used)
                    self._cache.move_to_end(key)
                    
                    # Update entry statistics
                    entry.last_accessed = time.time()
                    entry.access_count += 1
                    
                    self.stats['hits'] += 1
                    return entry.value
                else:
                    self.stats['misses'] += 1
                    return default
        
        finally:
            # Track access time
            access_time = time.time() - access_start
            with self._lock:
                self.stats['total_access_time'] += access_time
                self.stats['total_accesses'] += 1
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Put value in cache with optional TTL override"""
        try:
            with self._lock:
                # Calculate entry size
                size_bytes = self._calculate_size(value)
                
                # Create cache entry
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=time.time(),
                    last_accessed=time.time(),
                    access_count=0,
                    size_bytes=size_bytes,
                    ttl=ttl or self.default_ttl
                )
                
                # Handle existing key
                if key in self._cache:
                    self._cache[key] = entry
                    self._cache.move_to_end(key)
                else:
                    # Add new entry
                    self._cache[key] = entry
                    
                    # Evict oldest entries if necessary
                    while len(self._cache) > self.max_size:
                        oldest_key, _ = self._cache.popitem(last=False)
                        self.stats['evictions'] += 1
                
                return True
        
        except Exception as e:
            logger.warning(f"Cache put failed for key {key}: {e}")
            return False
    
    def _calculate_size(self, obj: Any) -> int:
        """Calculate approximate size of object in bytes"""
        try:
            return len(pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL))
        except Exception:
            # Fallback to sys.getsizeof
            import sys
            return sys.getsizeof(obj)
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            # Reset statistics except creation time
            creation_time = self.stats['created_at']
            self.stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'total_access_time': 0.0,
                'total_accesses': 0,
                'created_at': creation_time
            }
    
    def get_statistics(self) -> CacheStats:
        """Get comprehensive cache statistics"""
        with self._lock:
            total_entries = len(self._cache)
            total_size_bytes = sum(entry.size_bytes for entry in self._cache.values())
            total_size_mb = total_size_bytes / (1024 * 1024)
            
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests) if total_requests > 0 else 0
            miss_rate = (self.stats['misses'] / total_requests) if total_requests > 0 else 0
            
            avg_access_time_ms = 0
            if self.stats['total_accesses'] > 0:
                avg_access_time_ms = (self.stats['total_access_time'] / self.stats['total_accesses']) * 1000
            
            # Calculate memory efficiency (hits per MB)
            memory_efficiency = self.stats['hits'] / max(total_size_mb, 0.001)
            
            # Calculate optimization score
            optimization_score = self._calculate_optimization_score(hit_rate, memory_efficiency, total_entries)
            
            return CacheStats(
                cache_name=self.name,
                total_entries=total_entries,
                total_size_mb=total_size_mb,
                hit_rate=hit_rate,
                miss_rate=miss_rate,
                eviction_count=self.stats['evictions'],
                avg_access_time_ms=avg_access_time_ms,
                memory_efficiency=memory_efficiency,
                optimization_score=optimization_score
            )
    
    def _calculate_optimization_score(self, hit_rate: float, memory_efficiency: float, 
                                    total_entries: int) -> float:
        """Calculate cache optimization score (0-100)"""
        score = 0
        
        # Hit rate scoring (0-50 points)
        score += hit_rate * 50
        
        # Memory efficiency scoring (0-25 points)
        # Normalize memory efficiency (typical range 0-1000 hits per MB)
        normalized_efficiency = min(memory_efficiency / 1000, 1.0)
        score += normalized_efficiency * 25
        
        # Utilization scoring (0-25 points)
        utilization = min(total_entries / self.max_size, 1.0) if self.max_size > 0 else 0
        # Sweet spot is 70-90% utilization
        if 0.7 <= utilization <= 0.9:
            score += 25
        elif 0.5 <= utilization < 0.7 or 0.9 < utilization <= 1.0:
            score += 15
        else:
            score += utilization * 10  # Partial points for low utilization
        
        return min(score, 100)
    
    def optimize(self) -> Dict[str, Any]:
        """Optimize cache by removing low-value entries"""
        optimization_start = time.time()
        
        with self._lock:
            original_size = len(self._cache)
            original_memory = sum(entry.size_bytes for entry in self._cache.values())
            
            # Identify low-value entries for removal
            entries_to_remove = []
            current_time = time.time()
            
            for key, entry in self._cache.items():
                # Calculate value score based on access frequency and recency
                age_hours = (current_time - entry.created_at) / 3600
                last_access_hours = (current_time - entry.last_accessed) / 3600
                
                # Value score: access frequency / (age * time since last access)
                value_score = entry.access_count / max(age_hours * max(last_access_hours, 0.1), 0.1)
                
                # Remove entries with very low value scores
                if value_score < 0.1 or last_access_hours > 24:  # Not accessed in 24 hours
                    entries_to_remove.append(key)
            
            # Remove low-value entries
            for key in entries_to_remove:
                del self._cache[key]
            
            final_size = len(self._cache)
            final_memory = sum(entry.size_bytes for entry in self._cache.values())
            
            optimization_time = time.time() - optimization_start
            
            return {
                'success': True,
                'entries_removed': original_size - final_size,
                'memory_freed_bytes': original_memory - final_memory,
                'optimization_time_ms': optimization_time * 1000,
                'final_entries': final_size,
                'cache_name': self.name
            }
    
    def __del__(self):
        """Cleanup on destruction"""
        if self._stop_cleanup:
            self._stop_cleanup.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=1.0)


class CacheManager:
    """Manages multiple caches with system-wide optimization"""
    
    def __init__(self):
        self.caches = {}
        self.cache_registry = {}
        self._lock = threading.Lock()
        self.error_handler = get_error_handler()
        self.profiler = get_performance_profiler()
        
        # System-wide cache statistics
        self.global_stats = {
            'total_caches': 0,
            'optimizations_run': 0,
            'last_optimization': 0
        }
        
        # Initialize default caches
        self._initialize_default_caches()
        
        logger.info("CacheManager initialized with default caches")
    
    def _initialize_default_caches(self):
        """Initialize commonly used caches"""
        # OCR results cache - high TTL, large size for expensive operations
        self.create_cache(
            name="ocr_results",
            max_size=5000,
            ttl=3600  # 1 hour TTL
        )
        
        # Database query cache - medium TTL for frequently accessed data
        self.create_cache(
            name="db_queries",
            max_size=2000,
            ttl=300  # 5 minutes TTL
        )
        
        # Image processing cache - short TTL, smaller size
        self.create_cache(
            name="image_processing",
            max_size=1000,
            ttl=600  # 10 minutes TTL
        )
        
        # Configuration cache - very long TTL
        self.create_cache(
            name="configuration",
            max_size=100,
            ttl=86400  # 24 hours TTL
        )
    
    def create_cache(self, name: str, max_size: int = 1000, 
                    ttl: Optional[float] = None) -> LRUCache:
        """Create a new cache with specified parameters"""
        with self._lock:
            if name in self.caches:
                logger.warning(f"Cache '{name}' already exists, returning existing cache")
                return self.caches[name]
            
            cache = LRUCache(max_size=max_size, ttl=ttl, name=name)
            self.caches[name] = cache
            self.cache_registry[name] = {
                'created_at': time.time(),
                'max_size': max_size,
                'ttl': ttl
            }
            
            self.global_stats['total_caches'] += 1
            
            logger.info(f"Created cache '{name}' with max_size={max_size}, ttl={ttl}")
            return cache
    
    def get_cache(self, name: str) -> Optional[LRUCache]:
        """Get cache by name"""
        with self._lock:
            return self.caches.get(name)
    
    def get_all_cache_statistics(self) -> List[CacheStats]:
        """Get statistics for all caches"""
        stats = []
        with self._lock:
            for cache in self.caches.values():
                stats.append(cache.get_statistics())
        return stats
    
    @profile_performance("cache_manager.optimize_all_caches")
    def optimize_all_caches(self) -> Dict[str, Any]:
        """Optimize all caches in the system"""
        optimization_start = time.time()
        self.global_stats['optimizations_run'] += 1
        self.global_stats['last_optimization'] = optimization_start
        
        results = {
            'timestamp': optimization_start,
            'caches_optimized': 0,
            'total_entries_removed': 0,
            'total_memory_freed_mb': 0,
            'optimization_details': {},
            'total_time_ms': 0
        }
        
        try:
            logger.info("Starting system-wide cache optimization")
            
            with self._lock:
                caches_to_optimize = list(self.caches.items())
            
            for cache_name, cache in caches_to_optimize:
                try:
                    optimization_result = cache.optimize()
                    
                    if optimization_result['success']:
                        results['caches_optimized'] += 1
                        results['total_entries_removed'] += optimization_result['entries_removed']
                        results['total_memory_freed_mb'] += optimization_result['memory_freed_bytes'] / (1024 * 1024)
                        
                        results['optimization_details'][cache_name] = {
                            'entries_removed': optimization_result['entries_removed'],
                            'memory_freed_mb': optimization_result['memory_freed_bytes'] / (1024 * 1024),
                            'optimization_time_ms': optimization_result['optimization_time_ms']
                        }
                    
                except Exception as e:
                    logger.warning(f"Failed to optimize cache '{cache_name}': {e}")
                    results['optimization_details'][cache_name] = {'error': str(e)}
            
            results['total_time_ms'] = (time.time() - optimization_start) * 1000
            results['success'] = True
            
            logger.info(
                f"Cache optimization completed in {results['total_time_ms']:.1f}ms - "
                f"optimized {results['caches_optimized']} caches, "
                f"freed {results['total_memory_freed_mb']:.2f}MB"
            )
            
        except Exception as e:
            results['success'] = False
            results['error'] = str(e)
            results['total_time_ms'] = (time.time() - optimization_start) * 1000
            
            error_context = ErrorContext(
                component="cache_manager",
                operation="optimize_all_caches",
                user_data={'optimization_time_ms': results['total_time_ms']},
                system_state={},
                timestamp=time.time()
            )
            
            self.error_handler.handle_error(Exception(e), error_context, RecoveryStrategy.SKIP)
            logger.error(f"Cache optimization failed: {e}")
        
        return results
    
    def generate_cache_report(self) -> Dict[str, Any]:
        """Generate comprehensive cache performance report"""
        try:
            all_stats = self.get_all_cache_statistics()
            
            # Aggregate statistics
            total_entries = sum(stat.total_entries for stat in all_stats)
            total_size_mb = sum(stat.total_size_mb for stat in all_stats)
            weighted_hit_rate = sum(stat.hit_rate * stat.total_entries for stat in all_stats) / max(total_entries, 1)
            
            # Identify performance issues
            low_performance_caches = [stat for stat in all_stats if stat.optimization_score < 60]
            high_memory_caches = [stat for stat in all_stats if stat.total_size_mb > 50]
            
            return {
                'timestamp': time.time(),
                'summary': {
                    'total_caches': len(all_stats),
                    'total_entries': total_entries,
                    'total_memory_mb': total_size_mb,
                    'overall_hit_rate': weighted_hit_rate,
                    'low_performance_caches': len(low_performance_caches),
                    'high_memory_caches': len(high_memory_caches)
                },
                'cache_details': [asdict(stat) for stat in all_stats],
                'performance_issues': [
                    {
                        'cache_name': stat.cache_name,
                        'issue_type': 'low_performance',
                        'optimization_score': stat.optimization_score,
                        'recommendation': 'Consider tuning cache size or TTL'
                    }
                    for stat in low_performance_caches
                ] + [
                    {
                        'cache_name': stat.cache_name,
                        'issue_type': 'high_memory_usage',
                        'memory_mb': stat.total_size_mb,
                        'recommendation': 'Consider reducing cache size or implementing more aggressive eviction'
                    }
                    for stat in high_memory_caches
                ],
                'optimization_history': {
                    'total_optimizations': self.global_stats['optimizations_run'],
                    'last_optimization': self.global_stats['last_optimization']
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate cache report: {e}")
            return {'error': str(e)}
    
    def clear_all_caches(self):
        """Clear all caches - use with caution"""
        with self._lock:
            for cache in self.caches.values():
                cache.clear()
        logger.info("All caches cleared")


# Global cache manager instance
_cache_manager_instance = None

def get_cache_manager() -> CacheManager:
    """Get singleton cache manager instance"""
    global _cache_manager_instance
    if _cache_manager_instance is None:
        _cache_manager_instance = CacheManager()
    return _cache_manager_instance


# Convenience functions for common cache operations
def cache_ocr_result(image_hash: str, result: Any, ttl: float = 3600) -> bool:
    """Cache an OCR result"""
    cache_manager = get_cache_manager()
    ocr_cache = cache_manager.get_cache("ocr_results")
    if ocr_cache:
        return ocr_cache.put(image_hash, result, ttl)
    return False


def get_cached_ocr_result(image_hash: str) -> Optional[Any]:
    """Get cached OCR result"""
    cache_manager = get_cache_manager()
    ocr_cache = cache_manager.get_cache("ocr_results")
    if ocr_cache:
        return ocr_cache.get(image_hash)
    return None


def cache_db_query_result(query_hash: str, result: Any, ttl: float = 300) -> bool:
    """Cache a database query result"""
    cache_manager = get_cache_manager()
    db_cache = cache_manager.get_cache("db_queries")
    if db_cache:
        return db_cache.put(query_hash, result, ttl)
    return False


def get_cached_db_query_result(query_hash: str) -> Optional[Any]:
    """Get cached database query result"""
    cache_manager = get_cache_manager()
    db_cache = cache_manager.get_cache("db_queries")
    if db_cache:
        return db_cache.get(query_hash)
    return None