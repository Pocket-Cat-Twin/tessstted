"""
Threading and Concurrency Optimizer for Game Monitor System

Advanced thread pool management, lock optimization, and concurrency
improvements to maximize parallel processing performance.
"""

import threading
import concurrent.futures
import queue
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass
import weakref
import logging
from collections import defaultdict
import psutil

from .advanced_logger import get_logger
from .error_handler import get_error_handler, ErrorContext, ErrorCategory, RecoveryStrategy
from .performance_profiler import get_performance_profiler, profile_performance
from .constants import Threading, Performance

logger = get_logger(__name__)


@dataclass
class ThreadPoolStats:
    """Statistics for a thread pool"""
    pool_name: str
    max_workers: int
    active_threads: int
    pending_tasks: int
    completed_tasks: int
    failed_tasks: int
    avg_task_time: float
    utilization_percent: float
    optimization_score: float  # 0-100, higher is better


@dataclass
class LockAnalysis:
    """Analysis of lock usage and contention"""
    lock_name: str
    acquisition_count: int
    total_wait_time: float
    avg_wait_time: float
    max_wait_time: float
    contention_rate: float
    recommendations: List[str]


class ThreadPoolOptimizer:
    """Optimizes thread pool configurations and performance"""
    
    def __init__(self):
        self.pools = {}
        self.pool_stats = {}
        self._lock = threading.Lock()
        
        # Monitoring data
        self.task_completion_times = defaultdict(list)
        self.pool_utilization_history = defaultdict(list)
        
    def register_pool(self, name: str, pool: concurrent.futures.ThreadPoolExecutor):
        """Register a thread pool for monitoring and optimization"""
        with self._lock:
            self.pools[name] = weakref.ref(pool)
            self.pool_stats[name] = {
                'created_at': time.time(),
                'tasks_submitted': 0,
                'tasks_completed': 0,
                'tasks_failed': 0,
                'total_execution_time': 0,
                'max_workers': pool._max_workers
            }
        
        logger.info(f"Registered thread pool '{name}' with {pool._max_workers} workers")
    
    def get_pool_statistics(self) -> List[ThreadPoolStats]:
        """Get comprehensive statistics for all registered pools"""
        stats = []
        
        with self._lock:
            for name, pool_ref in self.pools.items():
                pool = pool_ref()
                if pool is None:
                    continue
                
                pool_data = self.pool_stats[name]
                
                # Calculate utilization
                active_threads = getattr(pool, '_threads', set())
                active_count = len(active_threads) if active_threads else 0
                utilization = (active_count / pool_data['max_workers']) * 100 if pool_data['max_workers'] > 0 else 0
                
                # Calculate average task time
                avg_task_time = 0
                if pool_data['tasks_completed'] > 0:
                    avg_task_time = pool_data['total_execution_time'] / pool_data['tasks_completed']
                
                # Calculate optimization score
                optimization_score = self._calculate_optimization_score(name, pool_data, utilization)
                
                stats.append(ThreadPoolStats(
                    pool_name=name,
                    max_workers=pool_data['max_workers'],
                    active_threads=active_count,
                    pending_tasks=getattr(pool._work_queue, 'qsize', lambda: 0)(),
                    completed_tasks=pool_data['tasks_completed'],
                    failed_tasks=pool_data['failed_tasks'],
                    avg_task_time=avg_task_time,
                    utilization_percent=utilization,
                    optimization_score=optimization_score
                ))
        
        return stats
    
    def _calculate_optimization_score(self, pool_name: str, pool_data: Dict, utilization: float) -> float:
        """Calculate optimization score for a thread pool (0-100)"""
        score = 50  # Base score
        
        # Utilization scoring (sweet spot is 60-80%)
        if 60 <= utilization <= 80:
            score += 25
        elif 40 <= utilization < 60 or 80 < utilization <= 90:
            score += 15
        elif utilization < 40 or utilization > 90:
            score -= 15
        
        # Task completion rate
        total_tasks = pool_data['tasks_completed'] + pool_data['tasks_failed']
        if total_tasks > 0:
            success_rate = pool_data['tasks_completed'] / total_tasks
            score += (success_rate - 0.8) * 50  # Bonus for >80% success rate
        
        # Task timing consistency
        completion_times = self.task_completion_times.get(pool_name, [])
        if len(completion_times) > 10:
            # Consistency bonus (lower variance is better)
            avg_time = sum(completion_times) / len(completion_times)
            variance = sum((t - avg_time) ** 2 for t in completion_times) / len(completion_times)
            consistency_score = max(0, 10 - variance)
            score += consistency_score
        
        return max(0, min(100, score))
    
    def optimize_pool_sizes(self) -> Dict[str, Any]:
        """Optimize thread pool sizes based on usage patterns"""
        optimization_results = {
            'pools_optimized': 0,
            'recommendations': [],
            'changes_made': []
        }
        
        stats = self.get_pool_statistics()
        
        for stat in stats:
            pool_ref = self.pools.get(stat.pool_name)
            if not pool_ref:
                continue
            
            pool = pool_ref()
            if pool is None:
                continue
            
            # Analyze optimization needs
            recommendation = self._generate_pool_optimization_recommendation(stat)
            if recommendation:
                optimization_results['recommendations'].append({
                    'pool_name': stat.pool_name,
                    'current_workers': stat.max_workers,
                    'recommended_workers': recommendation['recommended_size'],
                    'reason': recommendation['reason'],
                    'expected_improvement': recommendation['expected_improvement']
                })
        
        return optimization_results
    
    def _generate_pool_optimization_recommendation(self, stat: ThreadPoolStats) -> Optional[Dict[str, Any]]:
        """Generate optimization recommendation for a specific pool"""
        current_workers = stat.max_workers
        
        # High utilization - increase workers
        if stat.utilization_percent > 85 and stat.pending_tasks > current_workers:
            recommended_size = min(current_workers * 2, Threading.MAX_THREAD_POOL_SIZE)
            return {
                'recommended_size': recommended_size,
                'reason': f'High utilization ({stat.utilization_percent:.1f}%) and pending tasks',
                'expected_improvement': '20-40% throughput increase'
            }
        
        # Low utilization - decrease workers
        elif stat.utilization_percent < 30 and current_workers > 2:
            recommended_size = max(current_workers // 2, 2)
            return {
                'recommended_size': recommended_size,
                'reason': f'Low utilization ({stat.utilization_percent:.1f}%)',
                'expected_improvement': 'Reduced resource usage, better cache locality'
            }
        
        # Poor optimization score
        elif stat.optimization_score < 60:
            # Calculate optimal size based on CPU cores and workload
            cpu_cores = psutil.cpu_count()
            if stat.avg_task_time > 0.1:  # I/O bound tasks
                recommended_size = min(cpu_cores * 2, Threading.MAX_THREAD_POOL_SIZE)
            else:  # CPU bound tasks
                recommended_size = cpu_cores
            
            if recommended_size != current_workers:
                return {
                    'recommended_size': recommended_size,
                    'reason': f'Poor optimization score ({stat.optimization_score:.1f})',
                    'expected_improvement': 'Improved task throughput and resource usage'
                }
        
        return None


class LockAnalyzer:
    """Analyzes lock usage and identifies contention bottlenecks"""
    
    def __init__(self):
        self.lock_registry = {}
        self.lock_metrics = defaultdict(lambda: {
            'acquisitions': 0,
            'total_wait_time': 0,
            'wait_times': [],
            'contention_events': 0
        })
        self._analysis_lock = threading.Lock()
    
    def register_lock(self, name: str, lock_obj: threading.Lock):
        """Register a lock for monitoring"""
        with self._analysis_lock:
            self.lock_registry[name] = weakref.ref(lock_obj)
        
        # Monkey-patch the lock to add monitoring
        self._instrument_lock(name, lock_obj)
    
    def _instrument_lock(self, name: str, lock_obj: threading.Lock):
        """Add monitoring instrumentation to a lock"""
        original_acquire = lock_obj.acquire
        original_release = lock_obj.release
        
        def monitored_acquire(*args, **kwargs):
            start_time = time.time()
            result = original_acquire(*args, **kwargs)
            wait_time = time.time() - start_time
            
            with self._analysis_lock:
                metrics = self.lock_metrics[name]
                metrics['acquisitions'] += 1
                metrics['total_wait_time'] += wait_time
                metrics['wait_times'].append(wait_time)
                
                # Keep only recent wait times
                if len(metrics['wait_times']) > 1000:
                    metrics['wait_times'] = metrics['wait_times'][-500:]
                
                # Count contention (wait time > 1ms indicates contention)
                if wait_time > 0.001:
                    metrics['contention_events'] += 1
            
            return result
        
        def monitored_release(*args, **kwargs):
            return original_release(*args, **kwargs)
        
        lock_obj.acquire = monitored_acquire
        lock_obj.release = monitored_release
    
    def analyze_lock_contention(self) -> List[LockAnalysis]:
        """Analyze lock contention and generate recommendations"""
        analyses = []
        
        with self._analysis_lock:
            for lock_name, metrics in self.lock_metrics.items():
                if metrics['acquisitions'] == 0:
                    continue
                
                avg_wait_time = metrics['total_wait_time'] / metrics['acquisitions']
                max_wait_time = max(metrics['wait_times']) if metrics['wait_times'] else 0
                contention_rate = metrics['contention_events'] / metrics['acquisitions']
                
                recommendations = self._generate_lock_recommendations(lock_name, metrics, contention_rate)
                
                analyses.append(LockAnalysis(
                    lock_name=lock_name,
                    acquisition_count=metrics['acquisitions'],
                    total_wait_time=metrics['total_wait_time'],
                    avg_wait_time=avg_wait_time,
                    max_wait_time=max_wait_time,
                    contention_rate=contention_rate,
                    recommendations=recommendations
                ))
        
        # Sort by contention rate (highest first)
        analyses.sort(key=lambda a: a.contention_rate, reverse=True)
        return analyses
    
    def _generate_lock_recommendations(self, lock_name: str, metrics: Dict, contention_rate: float) -> List[str]:
        """Generate recommendations for reducing lock contention"""
        recommendations = []
        
        if contention_rate > 0.1:  # More than 10% contention
            recommendations.append(f"High contention detected ({contention_rate:.1%}) - consider lock-free alternatives")
            
            if metrics['avg_wait_time'] > 0.01:  # More than 10ms average wait
                recommendations.append("Long wait times suggest critical section is too large - consider reducing scope")
            
            recommendations.append("Consider using concurrent data structures or thread-local storage")
            recommendations.append("Evaluate if read-write locks would be beneficial")
        
        elif contention_rate > 0.05:  # More than 5% contention
            recommendations.append("Moderate contention - monitor and consider optimizations if performance degrades")
        
        if len(metrics['wait_times']) > 100:
            # Analyze wait time distribution
            sorted_times = sorted(metrics['wait_times'])
            p95_time = sorted_times[int(len(sorted_times) * 0.95)]
            
            if p95_time > 0.05:  # 95th percentile > 50ms
                recommendations.append(f"95th percentile wait time is {p95_time*1000:.1f}ms - investigate long critical sections")
        
        return recommendations


class ThreadingOptimizer:
    """Main threading and concurrency optimizer"""
    
    def __init__(self):
        self.error_handler = get_error_handler()
        self.profiler = get_performance_profiler()
        self.thread_pool_optimizer = ThreadPoolOptimizer()
        self.lock_analyzer = LockAnalyzer()
        
        # System threading statistics
        self.threading_stats = {
            'optimization_runs': 0,
            'last_optimization': 0,
            'total_threads_created': 0,
            'total_threads_destroyed': 0
        }
        
        logger.info("ThreadingOptimizer initialized")
    
    @profile_performance("threading_optimizer.run_comprehensive_analysis")
    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """Run comprehensive threading analysis and optimization"""
        analysis_start = time.time()
        
        analysis_results = {
            'timestamp': analysis_start,
            'system_threading_info': self._get_system_threading_info(),
            'thread_pool_analysis': [],
            'lock_analysis': [],
            'optimization_recommendations': [],
            'total_time_ms': 0
        }
        
        try:
            logger.info("Starting comprehensive threading analysis")
            
            # Analyze thread pools
            pool_stats = self.thread_pool_optimizer.get_pool_statistics()
            analysis_results['thread_pool_analysis'] = [
                {
                    'pool_name': stat.pool_name,
                    'max_workers': stat.max_workers,
                    'active_threads': stat.active_threads,
                    'utilization_percent': stat.utilization_percent,
                    'optimization_score': stat.optimization_score,
                    'avg_task_time': stat.avg_task_time
                }
                for stat in pool_stats
            ]
            
            # Analyze lock contention
            lock_analyses = self.lock_analyzer.analyze_lock_contention()
            analysis_results['lock_analysis'] = [
                {
                    'lock_name': analysis.lock_name,
                    'contention_rate': analysis.contention_rate,
                    'avg_wait_time': analysis.avg_wait_time,
                    'recommendations': analysis.recommendations
                }
                for analysis in lock_analyses
            ]
            
            # Generate system-wide recommendations
            analysis_results['optimization_recommendations'] = self._generate_system_recommendations(
                pool_stats, lock_analyses
            )
            
            analysis_results['total_time_ms'] = (time.time() - analysis_start) * 1000
            analysis_results['success'] = True
            
            logger.info(f"Threading analysis completed in {analysis_results['total_time_ms']:.1f}ms")
            
        except Exception as e:
            analysis_results['success'] = False
            analysis_results['error'] = str(e)
            analysis_results['total_time_ms'] = (time.time() - analysis_start) * 1000
            
            logger.error(f"Threading analysis failed: {e}")
        
        return analysis_results
    
    def _get_system_threading_info(self) -> Dict[str, Any]:
        """Get system-wide threading information"""
        try:
            return {
                'active_threads': threading.active_count(),
                'cpu_cores': psutil.cpu_count(),
                'cpu_usage_percent': psutil.cpu_percent(interval=0.1),
                'system_load_avg': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                'context_switches': psutil.cpu_stats().ctx_switches if hasattr(psutil, 'cpu_stats') else None
            }
        except Exception as e:
            logger.warning(f"Failed to get system threading info: {e}")
            return {}
    
    def _generate_system_recommendations(self, pool_stats: List[ThreadPoolStats], 
                                       lock_analyses: List[LockAnalysis]) -> List[str]:
        """Generate system-wide threading optimization recommendations"""
        recommendations = []
        
        # Thread pool recommendations
        high_contention_pools = [stat for stat in pool_stats if stat.optimization_score < 60]
        if high_contention_pools:
            recommendations.append(f"Optimize {len(high_contention_pools)} poorly performing thread pools")
        
        over_utilized_pools = [stat for stat in pool_stats if stat.utilization_percent > 85]
        if over_utilized_pools:
            recommendations.append(f"Increase worker count for {len(over_utilized_pools)} over-utilized thread pools")
        
        under_utilized_pools = [stat for stat in pool_stats if stat.utilization_percent < 30]
        if under_utilized_pools:
            recommendations.append(f"Consider reducing workers for {len(under_utilized_pools)} under-utilized thread pools")
        
        # Lock recommendations
        high_contention_locks = [analysis for analysis in lock_analyses if analysis.contention_rate > 0.1]
        if high_contention_locks:
            recommendations.append(f"Address high contention in {len(high_contention_locks)} locks")
        
        # System-wide recommendations
        total_threads = sum(stat.max_workers for stat in pool_stats)
        cpu_cores = psutil.cpu_count()
        
        if total_threads > cpu_cores * 3:
            recommendations.append("Consider reducing total thread count - high thread/core ratio may cause context switching overhead")
        elif total_threads < cpu_cores:
            recommendations.append("Consider increasing parallelism - thread count is lower than CPU cores")
        
        return recommendations
    
    @profile_performance("threading_optimizer.optimize_concurrency")
    def optimize_concurrency(self) -> Dict[str, Any]:
        """Run threading optimizations based on analysis"""
        optimization_start = time.time()
        self.threading_stats['optimization_runs'] += 1
        self.threading_stats['last_optimization'] = optimization_start
        
        results = {
            'timestamp': optimization_start,
            'optimizations_applied': [],
            'thread_pool_optimizations': {},
            'lock_optimizations': {},
            'total_time_ms': 0
        }
        
        try:
            logger.info("Starting threading optimizations")
            
            # Optimize thread pools
            pool_optimization = self.thread_pool_optimizer.optimize_pool_sizes()
            results['thread_pool_optimizations'] = pool_optimization
            
            # Analyze and report lock contention (optimization would require code changes)
            lock_analysis = self.lock_analyzer.analyze_lock_contention()
            high_contention_locks = [l for l in lock_analysis if l.contention_rate > 0.1]
            
            results['lock_optimizations'] = {
                'high_contention_locks': len(high_contention_locks),
                'recommendations': [l.recommendations for l in high_contention_locks],
                'total_locks_analyzed': len(lock_analysis)
            }
            
            # Log recommendations for manual implementation
            if pool_optimization['recommendations']:
                logger.info(f"Thread pool optimization recommendations: {len(pool_optimization['recommendations'])} pools need adjustment")
            
            if high_contention_locks:
                logger.warning(f"Lock contention detected in {len(high_contention_locks)} locks")
            
            results['total_time_ms'] = (time.time() - optimization_start) * 1000
            results['success'] = True
            
            logger.info(f"Threading optimizations completed in {results['total_time_ms']:.1f}ms")
            
        except Exception as e:
            results['success'] = False
            results['error'] = str(e)
            results['total_time_ms'] = (time.time() - optimization_start) * 1000
            
            error_context = ErrorContext(
                component="threading_optimizer",
                operation="optimize_concurrency",
                user_data={'optimization_time_ms': results['total_time_ms']},
                system_state={},
                timestamp=time.time()
            )
            
            self.error_handler.handle_error(Exception(e), error_context, RecoveryStrategy.SKIP)
            logger.error(f"Threading optimization failed: {e}")
        
        return results
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive threading optimization report"""
        analysis = self.run_comprehensive_analysis()
        
        return {
            'timestamp': time.time(),
            'analysis_results': analysis,
            'optimization_history': {
                'total_optimization_runs': self.threading_stats['optimization_runs'],
                'last_optimization_time': self.threading_stats['last_optimization']
            },
            'recommendations_summary': analysis.get('optimization_recommendations', []),
            'critical_issues': [
                rec for rec in analysis.get('optimization_recommendations', [])
                if 'high contention' in rec.lower() or 'over-utilized' in rec.lower()
            ]
        }


# Global optimizer instance
_threading_optimizer_instance = None

def get_threading_optimizer() -> ThreadingOptimizer:
    """Get singleton threading optimizer instance"""
    global _threading_optimizer_instance
    if _threading_optimizer_instance is None:
        _threading_optimizer_instance = ThreadingOptimizer()
    return _threading_optimizer_instance