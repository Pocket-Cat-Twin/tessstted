#!/usr/bin/env python3

import threading
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class DashboardMetrics:
    timestamp: datetime
    system_health_score: float
    total_errors_24h: int
    resolved_errors_24h: int
    active_alerts: int
    recovery_success_rate: float
    avg_recovery_time: float
    critical_components: List[str]
    performance_score: float
    error_trends: Dict[str, float]


class ErrorHandlingDashboard:
    """Comprehensive error handling dashboard that aggregates all error management data"""
    
    def __init__(self):
        from .error_recovery_manager import error_recovery_manager
        from .error_analytics import error_analytics
        from .automated_recovery import automated_recovery
        
        self.error_recovery_manager = error_recovery_manager
        self.error_analytics = error_analytics
        self.automated_recovery = automated_recovery
        
        # Dashboard state
        self.metrics_history: List[DashboardMetrics] = []
        self.alerts_cache: Dict[str, Any] = {}
        self.health_cache: Dict[str, Any] = {}
        
        # Configuration
        self.update_interval = 60  # 1 minute
        self.max_history_hours = 24
        self.health_thresholds = {
            'excellent': 95,
            'good': 80,
            'warning': 60,
            'critical': 40
        }
        
        # Threading
        self._lock = threading.RLock()
        self.update_thread = None
        self.running = False
    
    def start(self):
        """Start the dashboard update thread"""
        with self._lock:
            if self.running:
                return
            
            self.running = True
            self.update_thread = threading.Thread(
                target=self._update_worker,
                daemon=True,
                name="ErrorDashboardUpdater"
            )
            self.update_thread.start()
            logger.info("Error Handling Dashboard started")
    
    def stop(self):
        """Stop the dashboard"""
        with self._lock:
            self.running = False
            logger.info("Error Handling Dashboard stopped")
    
    def get_current_dashboard(self) -> Dict[str, Any]:
        """Get current dashboard data"""
        try:
            # Generate current metrics
            current_metrics = self._generate_current_metrics()
            
            # Get detailed component health
            component_health = self._get_component_health_details()
            
            # Get recent error patterns
            error_patterns = self._get_error_pattern_summary()
            
            # Get recovery statistics
            recovery_stats = self._get_recovery_statistics_summary()
            
            # Get system alerts
            alerts = self._get_active_alerts()
            
            # Get performance trends
            performance_trends = self._get_performance_trends()
            
            dashboard = {
                'timestamp': datetime.now().isoformat(),
                'overall_metrics': asdict(current_metrics),
                'component_health': component_health,
                'error_patterns': error_patterns,
                'recovery_statistics': recovery_stats,
                'active_alerts': alerts,
                'performance_trends': performance_trends,
                'historical_data': self._get_historical_summary(),
                'recommendations': self._generate_recommendations()
            }
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Failed to generate dashboard: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    def _generate_current_metrics(self) -> DashboardMetrics:
        """Generate current dashboard metrics"""
        
        current_time = datetime.now()
        
        # Get error statistics
        error_stats = self.error_recovery_manager.get_error_statistics()
        
        # Get recovery statistics
        recovery_stats = self.automated_recovery.get_recovery_statistics()
        
        # Get component health
        component_health = self.error_recovery_manager.get_component_health_status()
        
        # Get analytics data
        try:
            analytics_report = self.error_analytics.generate_analytics_report()
        except Exception as e:
            logger.warning(f"Failed to get analytics report: {e}")
            analytics_report = {}
        
        # Calculate 24-hour error counts
        recent_errors = self.error_recovery_manager.get_recent_errors(limit=500)
        cutoff_time = current_time - timedelta(hours=24)
        recent_errors_24h = [e for e in recent_errors if e.timestamp >= cutoff_time]
        
        total_errors_24h = len(recent_errors_24h)
        resolved_errors_24h = len([e for e in recent_errors_24h if e.resolved])
        
        # Calculate system health score
        system_health_score = self._calculate_system_health_score(
            component_health, error_stats, recovery_stats
        )
        
        # Get active alerts
        active_alerts = analytics_report.get('active_alerts', [])
        
        # Calculate recovery success rate
        exec_stats = recovery_stats.get('execution_stats', {})
        total_recoveries = exec_stats.get('total_recoveries', 0)
        successful_recoveries = exec_stats.get('successful_recoveries', 0)
        recovery_success_rate = (successful_recoveries / total_recoveries * 100) if total_recoveries > 0 else 100
        
        # Average recovery time
        avg_recovery_time = exec_stats.get('average_recovery_time', 0.0)
        
        # Critical components
        critical_components = [
            comp for comp, health in component_health.items()
            if health.status in ['critical', 'failed']
        ]
        
        # Performance score (simplified)
        performance_score = min(100, max(0, system_health_score))
        
        # Error trends (simplified)
        error_trends = self._calculate_error_trends(recent_errors_24h)
        
        return DashboardMetrics(
            timestamp=current_time,
            system_health_score=system_health_score,
            total_errors_24h=total_errors_24h,
            resolved_errors_24h=resolved_errors_24h,
            active_alerts=len(active_alerts),
            recovery_success_rate=recovery_success_rate,
            avg_recovery_time=avg_recovery_time,
            critical_components=critical_components,
            performance_score=performance_score,
            error_trends=error_trends
        )
    
    def _calculate_system_health_score(self, component_health: Dict, 
                                     error_stats: Dict, recovery_stats: Dict) -> float:
        """Calculate overall system health score (0-100)"""
        
        # Component health score (40% weight)
        if component_health:
            healthy_components = len([
                h for h in component_health.values() 
                if h.status in ['healthy', 'degraded']
            ])
            total_components = len(component_health)
            component_score = (healthy_components / total_components) * 40
        else:
            component_score = 40  # No components = perfect score
        
        # Error resolution score (30% weight)
        total_errors = error_stats.get('total_errors', 0)
        resolved_errors = error_stats.get('resolved_errors', 0)
        
        if total_errors > 0:
            error_resolution_rate = resolved_errors / total_errors
            error_score = error_resolution_rate * 30
        else:
            error_score = 30  # No errors = perfect score
        
        # Recovery success score (30% weight)
        exec_stats = recovery_stats.get('execution_stats', {})
        total_recoveries = exec_stats.get('total_recoveries', 0)
        successful_recoveries = exec_stats.get('successful_recoveries', 0)
        
        if total_recoveries > 0:
            recovery_success_rate = successful_recoveries / total_recoveries
            recovery_score = recovery_success_rate * 30
        else:
            recovery_score = 30  # No recovery attempts = perfect score
        
        total_score = component_score + error_score + recovery_score
        return min(100, max(0, total_score))
    
    def _calculate_error_trends(self, recent_errors: List) -> Dict[str, float]:
        """Calculate error trends for different categories"""
        
        if not recent_errors:
            return {}
        
        # Group errors by category
        category_counts = {}
        for error in recent_errors:
            category = error.category.value if hasattr(error.category, 'value') else str(error.category)
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Calculate trend percentages (simplified)
        total_errors = len(recent_errors)
        trends = {}
        
        for category, count in category_counts.items():
            percentage = (count / total_errors) * 100
            trends[category] = round(percentage, 1)
        
        return trends
    
    def _get_component_health_details(self) -> Dict[str, Any]:
        """Get detailed component health information"""
        
        try:
            component_health = self.error_recovery_manager.get_component_health_status()
            
            health_details = {}
            for component, health in component_health.items():
                health_details[component] = {
                    'status': health.status,
                    'error_count': health.error_count,
                    'consecutive_errors': health.consecutive_errors,
                    'recovery_count': health.recovery_count,
                    'last_error': health.last_error.isoformat() if health.last_error else None,
                    'uptime_hours': (datetime.now() - health.uptime_start).total_seconds() / 3600,
                    'health_grade': self._get_health_grade(health)
                }
            
            return health_details
            
        except Exception as e:
            logger.error(f"Failed to get component health details: {e}")
            return {}
    
    def _get_health_grade(self, health) -> str:
        """Get health grade based on component status and error count"""
        
        if health.status == 'healthy' and health.consecutive_errors == 0:
            return 'A'
        elif health.status in ['healthy', 'degraded'] and health.consecutive_errors <= 2:
            return 'B'
        elif health.status == 'degraded' and health.consecutive_errors <= 5:
            return 'C'
        elif health.status in ['unhealthy', 'critical']:
            return 'D'
        elif health.status == 'failed':
            return 'F'
        else:
            return 'C'  # Default
    
    def _get_error_pattern_summary(self) -> Dict[str, Any]:
        """Get summary of error patterns"""
        
        try:
            patterns = self.error_analytics.identify_error_patterns()
            
            pattern_summary = {
                'total_patterns': len(patterns),
                'high_frequency_patterns': [],
                'low_recovery_patterns': [],
                'recent_patterns': []
            }
            
            for pattern_id, pattern in patterns.items():
                # High frequency patterns (>10 occurrences)
                if pattern.frequency > 10:
                    pattern_summary['high_frequency_patterns'].append({
                        'category': pattern.category,
                        'frequency': pattern.frequency,
                        'recovery_rate': pattern.recovery_success_rate,
                        'components': pattern.components_affected
                    })
                
                # Low recovery patterns (<50% success rate)
                if pattern.recovery_success_rate < 0.5:
                    pattern_summary['low_recovery_patterns'].append({
                        'category': pattern.category,
                        'frequency': pattern.frequency,
                        'recovery_rate': pattern.recovery_success_rate,
                        'recommendations': pattern.recommended_actions[:3]  # Top 3
                    })
                
                # Recent patterns (for trending)
                pattern_summary['recent_patterns'].append({
                    'category': pattern.category,
                    'frequency': pattern.frequency,
                    'time_pattern': pattern.time_pattern
                })
            
            return pattern_summary
            
        except Exception as e:
            logger.error(f"Failed to get error pattern summary: {e}")
            return {}
    
    def _get_recovery_statistics_summary(self) -> Dict[str, Any]:
        """Get summary of recovery statistics"""
        
        try:
            recovery_stats = self.automated_recovery.get_recovery_statistics()
            
            summary = {
                'overall_success_rate': 0.0,
                'total_attempts': 0,
                'avg_recovery_time': 0.0,
                'best_performing_procedures': [],
                'worst_performing_procedures': [],
                'recent_recovery_history': []
            }
            
            exec_stats = recovery_stats.get('execution_stats', {})
            procedure_stats = recovery_stats.get('procedure_stats', {})
            
            # Overall metrics
            total_recoveries = exec_stats.get('total_recoveries', 0)
            successful_recoveries = exec_stats.get('successful_recoveries', 0)
            
            if total_recoveries > 0:
                summary['overall_success_rate'] = (successful_recoveries / total_recoveries) * 100
            
            summary['total_attempts'] = total_recoveries
            summary['avg_recovery_time'] = exec_stats.get('average_recovery_time', 0.0)
            
            # Procedure performance
            procedures = [(name, stats) for name, stats in procedure_stats.items()]
            procedures.sort(key=lambda x: x[1].get('success_rate', 0), reverse=True)
            
            # Best performing (top 3)
            summary['best_performing_procedures'] = [
                {'name': name, 'success_rate': stats.get('success_rate', 0) * 100}
                for name, stats in procedures[:3]
            ]
            
            # Worst performing (bottom 3)
            summary['worst_performing_procedures'] = [
                {'name': name, 'success_rate': stats.get('success_rate', 0) * 100}
                for name, stats in procedures[-3:]
            ]
            
            # Recent history
            recovery_history = self.automated_recovery.get_recovery_history(limit=10)
            summary['recent_recovery_history'] = recovery_history
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get recovery statistics summary: {e}")
            return {}
    
    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active system alerts"""
        
        try:
            alerts = self.error_analytics.detect_anomalies()
            
            active_alerts = []
            for alert in alerts:
                if not alert.resolved:
                    active_alerts.append({
                        'level': alert.level.value,
                        'component': alert.component,
                        'title': alert.title,
                        'message': alert.message,
                        'timestamp': alert.timestamp.isoformat(),
                        'metrics': alert.metrics
                    })
            
            # Sort by severity
            severity_order = {'critical': 0, 'warning': 1, 'info': 2}
            active_alerts.sort(key=lambda x: severity_order.get(x['level'], 3))
            
            return active_alerts
            
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []
    
    def _get_performance_trends(self) -> Dict[str, Any]:
        """Get performance trends"""
        
        try:
            trends = self.error_analytics.analyze_error_trends()
            
            trend_summary = {
                'error_rate_trends': {},
                'component_trends': {},
                'category_trends': {}
            }
            
            for period, trend_list in trends.items():
                trend_summary['error_rate_trends'][period] = []
                
                for trend in trend_list:
                    trend_info = {
                        'name': trend.component,
                        'category': trend.category,
                        'direction': trend.direction.value,
                        'change_percentage': trend.change_percentage,
                        'error_rate': trend.error_rate,
                        'confidence': trend.confidence
                    }
                    
                    if trend.category == 'component':
                        if period not in trend_summary['component_trends']:
                            trend_summary['component_trends'][period] = []
                        trend_summary['component_trends'][period].append(trend_info)
                    else:
                        if period not in trend_summary['category_trends']:
                            trend_summary['category_trends'][period] = []
                        trend_summary['category_trends'][period].append(trend_info)
                    
                    trend_summary['error_rate_trends'][period].append(trend_info)
            
            return trend_summary
            
        except Exception as e:
            logger.error(f"Failed to get performance trends: {e}")
            return {}
    
    def _get_historical_summary(self) -> Dict[str, Any]:
        """Get historical metrics summary"""
        
        with self._lock:
            if not self.metrics_history:
                return {}
            
            # Get metrics from last 24 hours
            cutoff_time = datetime.now() - timedelta(hours=24)
            recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
            
            if not recent_metrics:
                return {}
            
            # Calculate averages and trends
            avg_health_score = sum(m.system_health_score for m in recent_metrics) / len(recent_metrics)
            avg_recovery_rate = sum(m.recovery_success_rate for m in recent_metrics) / len(recent_metrics)
            total_errors = sum(m.total_errors_24h for m in recent_metrics[-1:])  # Latest only
            total_resolved = sum(m.resolved_errors_24h for m in recent_metrics[-1:])  # Latest only
            
            return {
                'time_period_hours': 24,
                'data_points': len(recent_metrics),
                'avg_health_score': round(avg_health_score, 1),
                'avg_recovery_rate': round(avg_recovery_rate, 1),
                'total_errors_24h': total_errors,
                'total_resolved_24h': total_resolved,
                'health_trend': self._calculate_health_trend(recent_metrics)
            }
    
    def _calculate_health_trend(self, metrics_list: List[DashboardMetrics]) -> str:
        """Calculate health trend direction"""
        
        if len(metrics_list) < 2:
            return 'stable'
        
        # Compare first half vs second half
        mid_point = len(metrics_list) // 2
        first_half_avg = sum(m.system_health_score for m in metrics_list[:mid_point]) / mid_point
        second_half_avg = sum(m.system_health_score for m in metrics_list[mid_point:]) / (len(metrics_list) - mid_point)
        
        change = second_half_avg - first_half_avg
        
        if change > 5:
            return 'improving'
        elif change < -5:
            return 'declining'
        else:
            return 'stable'
    
    def _generate_recommendations(self) -> List[str]:
        """Generate system recommendations based on current state"""
        
        recommendations = []
        
        try:
            # Get current metrics
            current_metrics = self._generate_current_metrics()
            
            # Health-based recommendations
            if current_metrics.system_health_score < self.health_thresholds['critical']:
                recommendations.append("CRITICAL: System health is below 40%. Immediate attention required.")
            elif current_metrics.system_health_score < self.health_thresholds['warning']:
                recommendations.append("WARNING: System health is declining. Review component issues.")
            
            # Error rate recommendations
            if current_metrics.total_errors_24h > 50:
                recommendations.append("High error rate detected. Consider reviewing error patterns and root causes.")
            
            # Recovery rate recommendations
            if current_metrics.recovery_success_rate < 70:
                recommendations.append("Recovery success rate is low. Review automated recovery procedures.")
            
            # Critical component recommendations
            if current_metrics.critical_components:
                components_str = ', '.join(current_metrics.critical_components)
                recommendations.append(f"Critical components requiring attention: {components_str}")
            
            # Alert recommendations
            if current_metrics.active_alerts > 5:
                recommendations.append("Multiple active alerts. Prioritize resolution of critical and warning alerts.")
            
            # Performance recommendations
            if current_metrics.avg_recovery_time > 30:
                recommendations.append("Recovery times are high. Consider optimizing recovery procedures.")
            
            # Add analytics-based recommendations
            try:
                analytics_report = self.error_analytics.generate_analytics_report()
                system_recommendations = analytics_report.get('recommendations', [])
                recommendations.extend(system_recommendations[:3])  # Top 3
            except:
                pass
            
            # Ensure we have some recommendations
            if not recommendations:
                recommendations.append("System is operating normally. Continue monitoring.")
            
            return recommendations[:10]  # Top 10 recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            return ["Unable to generate recommendations due to system error."]
    
    def _update_worker(self):
        """Background worker to update dashboard metrics"""
        
        while self.running:
            try:
                # Generate and store current metrics
                current_metrics = self._generate_current_metrics()
                
                with self._lock:
                    self.metrics_history.append(current_metrics)
                    
                    # Cleanup old metrics
                    cutoff_time = datetime.now() - timedelta(hours=self.max_history_hours)
                    self.metrics_history = [
                        m for m in self.metrics_history if m.timestamp >= cutoff_time
                    ]
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in dashboard update worker: {e}")
                time.sleep(60)  # Wait 1 minute before retry


# Singleton instance
error_dashboard = ErrorHandlingDashboard()