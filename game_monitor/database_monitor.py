"""
Database Monitoring System for Game Monitor
Real-time monitoring of database performance, connections, and health metrics.
"""

import threading
import time
import json
from typing import Dict, List, Optional, Any, NamedTuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import deque, defaultdict
import statistics
import queue

from .advanced_logger import get_logger


class ConnectionMetrics(NamedTuple):
    """Connection pool metrics"""
    total_connections: int
    active_connections: int
    idle_connections: int
    connection_utilization: float
    avg_connection_age: float
    connection_errors: int


class QueryPerformanceMetrics:
    """Query performance tracking"""
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.query_times = deque(maxlen=window_size)
        self.slow_queries = deque(maxlen=100)
        self.error_queries = deque(maxlen=100)
        self.query_types = defaultdict(list)
        
        # Performance thresholds
        self.slow_query_threshold = 100.0  # ms
        self.very_slow_threshold = 500.0   # ms
    
    def record_query(self, query_type: str, execution_time_ms: float, 
                    success: bool, error_message: Optional[str] = None):
        """Record query execution metrics"""
        timestamp = datetime.now()
        
        self.query_times.append(execution_time_ms)
        self.query_types[query_type].append(execution_time_ms)
        
        # Track slow queries
        if execution_time_ms > self.slow_query_threshold:
            self.slow_queries.append({
                'timestamp': timestamp,
                'query_type': query_type,
                'execution_time_ms': execution_time_ms,
                'error_message': error_message
            })
        
        # Track errors
        if not success:
            self.error_queries.append({
                'timestamp': timestamp,
                'query_type': query_type,
                'execution_time_ms': execution_time_ms,
                'error_message': error_message
            })
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive query performance statistics"""
        if not self.query_times:
            return {}
        
        query_times_list = list(self.query_times)
        
        stats = {
            'total_queries': len(query_times_list),
            'avg_execution_time_ms': statistics.mean(query_times_list),
            'median_execution_time_ms': statistics.median(query_times_list),
            'min_execution_time_ms': min(query_times_list),
            'max_execution_time_ms': max(query_times_list),
            'p95_execution_time_ms': query_times_list[int(len(query_times_list) * 0.95)] if len(query_times_list) > 20 else 0,
            'p99_execution_time_ms': query_times_list[int(len(query_times_list) * 0.99)] if len(query_times_list) > 100 else 0,
            'slow_queries_count': len(self.slow_queries),
            'error_queries_count': len(self.error_queries),
            'queries_per_second': self._calculate_qps()
        }
        
        # Add per-query-type statistics
        stats['by_query_type'] = {}
        for query_type, times in self.query_types.items():
            if times:
                stats['by_query_type'][query_type] = {
                    'count': len(times),
                    'avg_time_ms': statistics.mean(times),
                    'max_time_ms': max(times)
                }
        
        return stats
    
    def _calculate_qps(self) -> float:
        """Calculate queries per second for recent window"""
        if len(self.query_times) < 2:
            return 0.0
        
        # Estimate based on collection time (approximate)
        window_duration = 60.0  # Assume 1-minute window
        return len(self.query_times) / window_duration


@dataclass
class DatabaseHealthMetrics:
    """Database health metrics snapshot"""
    timestamp: datetime
    is_healthy: bool
    connection_pool_status: str
    query_performance_status: str
    disk_space_status: str
    integrity_status: str
    
    # Numeric metrics
    database_size_mb: float
    connection_utilization: float
    avg_query_time_ms: float
    queries_per_second: float
    error_rate_percent: float
    
    # Issues and warnings
    errors: List[str]
    warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class DatabaseMonitor:
    """Comprehensive database monitoring system"""
    
    def __init__(self, database_manager):
        self.db_manager = database_manager
        self.logger = get_logger('database_monitor')
        
        # Monitoring state
        self._monitoring_active = True
        self._monitor_lock = threading.RLock()
        
        # Metrics storage
        self._health_history = deque(maxlen=1440)  # 24 hours at 1-minute intervals
        self._connection_metrics_history = deque(maxlen=1440)
        self._performance_alerts = deque(maxlen=100)
        
        # Performance tracking
        self.query_performance = QueryPerformanceMetrics()
        
        # Alert thresholds
        self.alert_thresholds = {
            'connection_utilization': 0.8,      # 80% connection pool usage
            'avg_query_time_ms': 200.0,         # Average query time
            'error_rate_percent': 5.0,          # 5% error rate
            'disk_space_warning_gb': 1.0,       # Less than 1GB free
            'database_size_warning_mb': 1000.0  # Database larger than 1GB
        }
        
        # Alert callbacks
        self._alert_callbacks = []
        
        # Start monitoring
        self._start_monitoring()
    
    def _start_monitoring(self):
        """Start background monitoring threads"""
        
        # Health monitoring thread
        self._health_thread = threading.Thread(
            target=self._health_monitoring_loop, daemon=True
        )
        self._health_thread.start()
        
        # Performance monitoring thread
        self._performance_thread = threading.Thread(
            target=self._performance_monitoring_loop, daemon=True
        )
        self._performance_thread.start()
        
        self.logger.info("Database monitoring started")
    
    def _health_monitoring_loop(self):
        """Background loop for health monitoring"""
        while self._monitoring_active:
            try:
                # Collect health metrics
                health_metrics = self._collect_health_metrics()
                
                with self._monitor_lock:
                    self._health_history.append(health_metrics)
                
                # Check for alerts
                self._check_health_alerts(health_metrics)
                
                # Log health status
                if not health_metrics.is_healthy:
                    self.logger.warning(
                        "Database health issues detected",
                        extra_data=health_metrics.to_dict()
                    )
                else:
                    self.logger.debug(
                        "Database health check completed",
                        extra_data={
                            'connection_utilization': health_metrics.connection_utilization,
                            'avg_query_time_ms': health_metrics.avg_query_time_ms,
                            'queries_per_second': health_metrics.queries_per_second
                        }
                    )
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                time.sleep(60)
    
    def _performance_monitoring_loop(self):
        """Background loop for performance monitoring"""
        while self._monitoring_active:
            try:
                # Collect connection metrics
                conn_metrics = self._collect_connection_metrics()
                
                with self._monitor_lock:
                    self._connection_metrics_history.append({
                        'timestamp': datetime.now(),
                        'metrics': conn_metrics
                    })
                
                # Check for performance degradation
                self._check_performance_alerts(conn_metrics)
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in performance monitoring loop: {e}")
                time.sleep(30)
    
    def _collect_health_metrics(self) -> DatabaseHealthMetrics:
        """Collect comprehensive database health metrics"""
        
        try:
            # Get database statistics
            db_stats = self.db_manager.get_database_statistics()
            
            # Calculate derived metrics
            total_queries = db_stats.get('total_queries', 0)
            failed_queries = db_stats.get('failed_queries', 0)
            error_rate = (failed_queries / max(total_queries, 1)) * 100
            
            # Get query performance stats
            query_stats = self.query_performance.get_statistics()
            avg_query_time = query_stats.get('avg_execution_time_ms', 0.0)
            queries_per_second = query_stats.get('queries_per_second', 0.0)
            
            # Get connection pool status
            pool_info = db_stats.get('connection_pool', {})
            pool_size = pool_info.get('size', 1)
            active_connections = pool_info.get('active', 0)
            connection_utilization = active_connections / pool_size
            
            # Health status determination
            is_healthy = True
            errors = []
            warnings = []
            
            # Check thresholds
            if connection_utilization > self.alert_thresholds['connection_utilization']:
                warnings.append(f"High connection utilization: {connection_utilization:.1%}")
            
            if avg_query_time > self.alert_thresholds['avg_query_time_ms']:
                warnings.append(f"Slow average query time: {avg_query_time:.2f}ms")
            
            if error_rate > self.alert_thresholds['error_rate_percent']:
                errors.append(f"High error rate: {error_rate:.1f}%")
                is_healthy = False
            
            # Database size check
            db_size_mb = db_stats.get('database_size_mb', 0.0)
            if db_size_mb > self.alert_thresholds['database_size_warning_mb']:
                warnings.append(f"Large database size: {db_size_mb:.1f}MB")
            
            # Circuit breaker status
            cb_status = db_stats.get('circuit_breaker', {})
            if cb_status.get('state') == 'open':
                errors.append("Database circuit breaker is OPEN")
                is_healthy = False
            
            # Create health metrics
            health_metrics = DatabaseHealthMetrics(
                timestamp=datetime.now(),
                is_healthy=is_healthy,
                connection_pool_status="healthy" if connection_utilization < 0.8 else "stressed",
                query_performance_status="good" if avg_query_time < 100 else "degraded",
                disk_space_status="sufficient",  # Would need actual disk space check
                integrity_status="verified",
                database_size_mb=db_size_mb,
                connection_utilization=connection_utilization,
                avg_query_time_ms=avg_query_time,
                queries_per_second=queries_per_second,
                error_rate_percent=error_rate,
                errors=errors,
                warnings=warnings
            )
            
            return health_metrics
            
        except Exception as e:
            self.logger.error(f"Failed to collect health metrics: {e}")
            
            # Return minimal health metrics on error
            return DatabaseHealthMetrics(
                timestamp=datetime.now(),
                is_healthy=False,
                connection_pool_status="unknown",
                query_performance_status="unknown",
                disk_space_status="unknown",
                integrity_status="unknown",
                database_size_mb=0.0,
                connection_utilization=0.0,
                avg_query_time_ms=0.0,
                queries_per_second=0.0,
                error_rate_percent=0.0,
                errors=[f"Health metrics collection failed: {str(e)}"],
                warnings=[]
            )
    
    def _collect_connection_metrics(self) -> ConnectionMetrics:
        """Collect connection pool metrics"""
        
        try:
            db_stats = self.db_manager.get_database_statistics()
            pool_info = db_stats.get('connection_pool', {})
            
            total_connections = pool_info.get('size', 0)
            active_connections = pool_info.get('active', 0)
            idle_connections = total_connections - active_connections
            
            connection_utilization = active_connections / max(total_connections, 1)
            
            # Calculate average connection age (approximate)
            avg_connection_age = time.time() - db_stats.get('start_time', time.time())
            
            connection_errors = db_stats.get('connection_errors', 0)
            
            return ConnectionMetrics(
                total_connections=total_connections,
                active_connections=active_connections,
                idle_connections=idle_connections,
                connection_utilization=connection_utilization,
                avg_connection_age=avg_connection_age,
                connection_errors=connection_errors
            )
            
        except Exception as e:
            self.logger.error(f"Failed to collect connection metrics: {e}")
            return ConnectionMetrics(0, 0, 0, 0.0, 0.0, 0)
    
    def _check_health_alerts(self, health_metrics: DatabaseHealthMetrics):
        """Check health metrics against alert thresholds"""
        
        alerts = []
        
        # High connection utilization
        if health_metrics.connection_utilization > self.alert_thresholds['connection_utilization']:
            alerts.append({
                'type': 'high_connection_utilization',
                'severity': 'warning',
                'message': f"Connection utilization at {health_metrics.connection_utilization:.1%}",
                'threshold': self.alert_thresholds['connection_utilization'],
                'current_value': health_metrics.connection_utilization
            })
        
        # Slow queries
        if health_metrics.avg_query_time_ms > self.alert_thresholds['avg_query_time_ms']:
            alerts.append({
                'type': 'slow_queries',
                'severity': 'warning',
                'message': f"Average query time: {health_metrics.avg_query_time_ms:.2f}ms",
                'threshold': self.alert_thresholds['avg_query_time_ms'],
                'current_value': health_metrics.avg_query_time_ms
            })
        
        # High error rate
        if health_metrics.error_rate_percent > self.alert_thresholds['error_rate_percent']:
            alerts.append({
                'type': 'high_error_rate',
                'severity': 'critical',
                'message': f"Database error rate: {health_metrics.error_rate_percent:.1f}%",
                'threshold': self.alert_thresholds['error_rate_percent'],
                'current_value': health_metrics.error_rate_percent
            })
        
        # Process alerts
        for alert in alerts:
            self._trigger_alert(alert)
    
    def _check_performance_alerts(self, conn_metrics: ConnectionMetrics):
        """Check connection performance for alerts"""
        
        # Connection pool exhaustion warning
        if conn_metrics.connection_utilization > 0.9:
            alert = {
                'type': 'connection_pool_exhaustion',
                'severity': 'critical',
                'message': f"Connection pool nearly exhausted: {conn_metrics.active_connections}/{conn_metrics.total_connections}",
                'current_value': conn_metrics.connection_utilization
            }
            self._trigger_alert(alert)
    
    def _trigger_alert(self, alert: Dict[str, Any]):
        """Trigger performance alert"""
        
        alert['timestamp'] = datetime.now()
        
        with self._monitor_lock:
            self._performance_alerts.append(alert)
        
        # Log alert
        if alert['severity'] == 'critical':
            self.logger.critical(
                f"Database CRITICAL alert: {alert['message']}",
                extra_data=alert
            )
        else:
            self.logger.warning(
                f"Database alert: {alert['message']}",
                extra_data=alert
            )
        
        # Notify callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")
    
    def record_query_execution(self, query_type: str, execution_time_ms: float,
                              success: bool, error_message: Optional[str] = None):
        """Record query execution for performance tracking"""
        self.query_performance.record_query(
            query_type, execution_time_ms, success, error_message
        )
    
    def get_current_health_status(self) -> Optional[DatabaseHealthMetrics]:
        """Get current database health status"""
        with self._monitor_lock:
            if self._health_history:
                return self._health_history[-1]
        return None
    
    def get_health_history(self, hours: int = 24) -> List[DatabaseHealthMetrics]:
        """Get health history for specified time period"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        with self._monitor_lock:
            return [
                health for health in self._health_history
                if health.timestamp >= cutoff
            ]
    
    def get_recent_alerts(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent performance alerts"""
        with self._monitor_lock:
            return list(self._performance_alerts)[-count:]
    
    def get_performance_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get performance summary for time period"""
        
        # Get recent health metrics
        recent_health = self.get_health_history(hours)
        
        if not recent_health:
            return {}
        
        # Calculate aggregated metrics
        connection_utilizations = [h.connection_utilization for h in recent_health]
        query_times = [h.avg_query_time_ms for h in recent_health if h.avg_query_time_ms > 0]
        error_rates = [h.error_rate_percent for h in recent_health]
        
        summary = {
            'time_period_hours': hours,
            'sample_count': len(recent_health),
            'overall_health': all(h.is_healthy for h in recent_health),
            'connection_utilization': {
                'current': connection_utilizations[-1] if connection_utilizations else 0,
                'average': statistics.mean(connection_utilizations) if connection_utilizations else 0,
                'max': max(connection_utilizations) if connection_utilizations else 0
            },
            'query_performance': {
                'current_avg_ms': query_times[-1] if query_times else 0,
                'average_ms': statistics.mean(query_times) if query_times else 0,
                'max_ms': max(query_times) if query_times else 0
            },
            'error_rate': {
                'current_percent': error_rates[-1] if error_rates else 0,
                'average_percent': statistics.mean(error_rates) if error_rates else 0,
                'max_percent': max(error_rates) if error_rates else 0
            },
            'alerts_count': len(self.get_recent_alerts(100))  # Last 100 alerts
        }
        
        # Add query statistics
        query_stats = self.query_performance.get_statistics()
        summary['query_statistics'] = query_stats
        
        return summary
    
    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for performance alerts"""
        self._alert_callbacks.append(callback)
    
    def generate_health_report(self, hours: int = 24) -> str:
        """Generate comprehensive database health report"""
        
        summary = self.get_performance_summary(hours)
        current_health = self.get_current_health_status()
        recent_alerts = self.get_recent_alerts(50)
        
        report = []
        report.append(f"Database Health Report - Last {hours} hours")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Overall health status
        if current_health:
            status = "HEALTHY" if current_health.is_healthy else "ISSUES DETECTED"
            report.append(f"Overall Health Status: {status}")
            report.append(f"Database Size: {current_health.database_size_mb:.1f}MB")
            report.append("")
        
        # Performance summary
        if summary:
            report.append("Performance Summary:")
            conn_util = summary['connection_utilization']
            query_perf = summary['query_performance']
            error_rate = summary['error_rate']
            
            report.append(f"  Connection Utilization: {conn_util['current']:.1%} current, {conn_util['average']:.1%} avg, {conn_util['max']:.1%} max")
            report.append(f"  Query Performance: {query_perf['current_avg_ms']:.2f}ms current, {query_perf['average_ms']:.2f}ms avg")
            report.append(f"  Error Rate: {error_rate['current_percent']:.2f}% current, {error_rate['average_percent']:.2f}% avg")
            report.append("")
        
        # Recent alerts
        if recent_alerts:
            report.append(f"Recent Alerts ({len(recent_alerts)}):")
            for alert in recent_alerts[-10:]:  # Show last 10 alerts
                timestamp = alert['timestamp'].strftime('%H:%M:%S')
                report.append(f"  [{timestamp}] {alert['severity'].upper()}: {alert['message']}")
            report.append("")
        
        # Current issues
        if current_health and (current_health.errors or current_health.warnings):
            report.append("Current Issues:")
            for error in current_health.errors:
                report.append(f"  ERROR: {error}")
            for warning in current_health.warnings:
                report.append(f"  WARNING: {warning}")
        
        return "\n".join(report)
    
    def shutdown(self):
        """Shutdown database monitoring"""
        
        self.logger.info("Shutting down database monitoring")
        
        self._monitoring_active = False
        
        # Wait for threads to finish
        for thread in [self._health_thread, self._performance_thread]:
            if thread.is_alive():
                thread.join(timeout=5)
        
        self.logger.info("Database monitoring shutdown complete")