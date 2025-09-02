#!/usr/bin/env python3

import threading
import time
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
import logging
import statistics
import math

logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class AlertLevel(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ErrorTrend:
    component: str
    category: str
    period: str  # "1h", "24h", "7d", "30d"
    error_count: int
    error_rate: float
    direction: TrendDirection
    change_percentage: float
    prediction: int
    confidence: float


@dataclass
class SystemAlert:
    alert_id: str
    timestamp: datetime
    level: AlertLevel
    component: str
    title: str
    message: str
    metrics: Dict[str, Any]
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class HealthMetrics:
    component: str
    timestamp: datetime
    availability: float
    error_rate: float
    recovery_rate: float
    mean_time_to_recovery: float
    uptime_percentage: float
    performance_score: float


@dataclass
class ErrorPattern:
    pattern_id: str
    category: str
    error_types: List[str]
    frequency: int
    severity_distribution: Dict[str, int]
    time_pattern: str  # "peak_hours", "random", "periodic"
    components_affected: List[str]
    recovery_success_rate: float
    recommended_actions: List[str]


class ErrorAnalytics:
    def __init__(self):
        from .error_recovery_manager import error_recovery_manager
        
        self.error_recovery_manager = error_recovery_manager
        self.trends: Dict[str, List[ErrorTrend]] = defaultdict(list)
        self.alerts: Dict[str, SystemAlert] = {}
        self.health_metrics: Dict[str, List[HealthMetrics]] = defaultdict(list)
        self.error_patterns: Dict[str, ErrorPattern] = {}
        self.analysis_cache: Dict[str, Any] = {}
        
        # Configuration
        self.analysis_intervals = {
            "1h": 3600,
            "24h": 86400,
            "7d": 604800,
            "30d": 2592000
        }
        
        self.thresholds = {
            "error_rate_critical": 10.0,  # errors per minute
            "error_rate_warning": 5.0,
            "availability_critical": 0.95,  # 95%
            "availability_warning": 0.98,  # 98%
            "recovery_rate_warning": 0.8,  # 80%
            "mttr_warning": 300,  # 5 minutes
        }
        
        # Threading
        self._lock = threading.RLock()
        self.analysis_thread = None
        self.running = False
        self.analysis_interval = 300  # 5 minutes
    
    def start(self):
        """Start the analytics engine"""
        with self._lock:
            if self.running:
                return
                
            self.running = True
            self.analysis_thread = threading.Thread(
                target=self._analysis_worker,
                daemon=True,
                name="ErrorAnalyticsWorker"
            )
            self.analysis_thread.start()
            logger.info("Error Analytics started")
    
    def stop(self):
        """Stop the analytics engine"""
        with self._lock:
            self.running = False
            logger.info("Error Analytics stopped")
    
    def analyze_error_trends(self) -> Dict[str, List[ErrorTrend]]:
        """Analyze error trends across different time periods"""
        
        current_time = datetime.now()
        trends = {}
        
        # Get recent errors for analysis
        recent_errors = self.error_recovery_manager.get_recent_errors(limit=1000)
        
        for period, seconds in self.analysis_intervals.items():
            period_start = current_time - timedelta(seconds=seconds)
            period_errors = [e for e in recent_errors if e.timestamp >= period_start]
            
            # Group errors by component and category
            component_errors = defaultdict(list)
            category_errors = defaultdict(list)
            
            for error in period_errors:
                component_errors[error.component].append(error)
                category_errors[error.category.value].append(error)
            
            period_trends = []
            
            # Analyze component trends
            for component, errors in component_errors.items():
                trend = self._calculate_trend(component, "component", errors, period, seconds)
                if trend:
                    period_trends.append(trend)
            
            # Analyze category trends
            for category, errors in category_errors.items():
                trend = self._calculate_trend(category, "category", errors, period, seconds)
                if trend:
                    period_trends.append(trend)
            
            trends[period] = period_trends
        
        with self._lock:
            self.trends = trends
        
        return trends
    
    def _calculate_trend(self, name: str, type_: str, errors: List, period: str, period_seconds: int) -> Optional[ErrorTrend]:
        """Calculate trend for a specific component/category"""
        
        if len(errors) < 2:
            return None
        
        current_time = datetime.now()
        error_count = len(errors)
        error_rate = error_count / (period_seconds / 3600)  # errors per hour
        
        # Calculate trend direction
        half_period = period_seconds / 2
        mid_point = current_time - timedelta(seconds=half_period)
        
        early_errors = [e for e in errors if e.timestamp < mid_point]
        recent_errors = [e for e in errors if e.timestamp >= mid_point]
        
        early_rate = len(early_errors) / (half_period / 3600) if early_errors else 0
        recent_rate = len(recent_errors) / (half_period / 3600) if recent_errors else 0
        
        # Determine trend direction
        if early_rate == 0:
            direction = TrendDirection.INCREASING
            change_percentage = 100.0
        elif recent_rate == 0:
            direction = TrendDirection.DECREASING
            change_percentage = -100.0
        else:
            change_percentage = ((recent_rate - early_rate) / early_rate) * 100
            
            if abs(change_percentage) < 10:
                direction = TrendDirection.STABLE
            elif change_percentage > 50:
                direction = TrendDirection.VOLATILE
            elif change_percentage > 0:
                direction = TrendDirection.INCREASING
            else:
                direction = TrendDirection.DECREASING
        
        # Simple prediction (linear extrapolation)
        prediction = max(0, int(recent_rate * 2)) if recent_rate > 0 else 0
        confidence = min(0.9, len(errors) / 20.0)  # More data = higher confidence
        
        return ErrorTrend(
            component=name,
            category=type_,
            period=period,
            error_count=error_count,
            error_rate=error_rate,
            direction=direction,
            change_percentage=change_percentage,
            prediction=prediction,
            confidence=confidence
        )
    
    def generate_health_metrics(self) -> Dict[str, HealthMetrics]:
        """Generate health metrics for all components"""
        
        current_time = datetime.now()
        health_data = self.error_recovery_manager.get_component_health_status()
        error_stats = self.error_recovery_manager.get_error_statistics()
        
        metrics = {}
        
        for component, health in health_data.items():
            # Calculate availability (uptime percentage)
            uptime_seconds = (current_time - health.uptime_start).total_seconds()
            downtime_estimate = health.consecutive_errors * 60  # Assume 1 min per consecutive error
            availability = max(0, 1 - (downtime_estimate / uptime_seconds))
            
            # Calculate error rate (errors per hour)
            error_rate = health.error_count / (uptime_seconds / 3600) if uptime_seconds > 0 else 0
            
            # Calculate recovery rate
            recovery_rate = health.recovery_count / max(1, health.error_count)
            
            # Estimate mean time to recovery (simplified)
            mttr = self._estimate_mttr(component)
            
            # Calculate uptime percentage
            uptime_percentage = availability * 100
            
            # Calculate performance score (composite metric)
            performance_score = self._calculate_performance_score(
                availability, error_rate, recovery_rate, mttr
            )
            
            metric = HealthMetrics(
                component=component,
                timestamp=current_time,
                availability=availability,
                error_rate=error_rate,
                recovery_rate=recovery_rate,
                mean_time_to_recovery=mttr,
                uptime_percentage=uptime_percentage,
                performance_score=performance_score
            )
            
            metrics[component] = metric
        
        with self._lock:
            for component, metric in metrics.items():
                self.health_metrics[component].append(metric)
                # Keep only last 24 hours of metrics
                cutoff_time = current_time - timedelta(hours=24)
                self.health_metrics[component] = [
                    m for m in self.health_metrics[component] if m.timestamp >= cutoff_time
                ]
        
        return metrics
    
    def _estimate_mttr(self, component: str) -> float:
        """Estimate Mean Time To Recovery for component"""
        
        recent_errors = self.error_recovery_manager.get_recent_errors(limit=100)
        component_errors = [e for e in recent_errors if e.component == component and e.resolved]
        
        if not component_errors:
            return 0.0
        
        recovery_times = []
        for error in component_errors:
            if error.resolution_time:
                recovery_time = (error.resolution_time - error.timestamp).total_seconds()
                recovery_times.append(recovery_time)
        
        if recovery_times:
            return statistics.mean(recovery_times)
        
        return 0.0
    
    def _calculate_performance_score(self, availability: float, error_rate: float, 
                                   recovery_rate: float, mttr: float) -> float:
        """Calculate composite performance score (0-100)"""
        
        # Normalize metrics to 0-1 scale
        availability_score = availability
        error_score = max(0, 1 - (error_rate / 20))  # Assume 20 errors/hour = 0 score
        recovery_score = recovery_rate
        mttr_score = max(0, 1 - (mttr / 600))  # Assume 10 min MTTR = 0 score
        
        # Weighted composite score
        weights = [0.4, 0.3, 0.2, 0.1]  # availability, error, recovery, mttr
        scores = [availability_score, error_score, recovery_score, mttr_score]
        
        performance_score = sum(w * s for w, s in zip(weights, scores)) * 100
        return min(100, max(0, performance_score))
    
    def detect_anomalies(self) -> List[SystemAlert]:
        """Detect system anomalies and generate alerts"""
        
        alerts = []
        current_time = datetime.now()
        health_metrics = self.generate_health_metrics()
        
        for component, metrics in health_metrics.items():
            # Check availability
            if metrics.availability < self.thresholds["availability_critical"]:
                alert = SystemAlert(
                    alert_id=f"availability_critical_{component}_{int(current_time.timestamp())}",
                    timestamp=current_time,
                    level=AlertLevel.CRITICAL,
                    component=component,
                    title=f"Critical Availability Issue: {component}",
                    message=f"Component {component} availability is {metrics.availability:.1%}, below critical threshold",
                    metrics={"availability": metrics.availability, "threshold": self.thresholds["availability_critical"]}
                )
                alerts.append(alert)
            elif metrics.availability < self.thresholds["availability_warning"]:
                alert = SystemAlert(
                    alert_id=f"availability_warning_{component}_{int(current_time.timestamp())}",
                    timestamp=current_time,
                    level=AlertLevel.WARNING,
                    component=component,
                    title=f"Availability Warning: {component}",
                    message=f"Component {component} availability is {metrics.availability:.1%}",
                    metrics={"availability": metrics.availability, "threshold": self.thresholds["availability_warning"]}
                )
                alerts.append(alert)
            
            # Check error rate
            if metrics.error_rate > self.thresholds["error_rate_critical"]:
                alert = SystemAlert(
                    alert_id=f"error_rate_critical_{component}_{int(current_time.timestamp())}",
                    timestamp=current_time,
                    level=AlertLevel.CRITICAL,
                    component=component,
                    title=f"High Error Rate: {component}",
                    message=f"Component {component} error rate is {metrics.error_rate:.1f} errors/hour",
                    metrics={"error_rate": metrics.error_rate, "threshold": self.thresholds["error_rate_critical"]}
                )
                alerts.append(alert)
            elif metrics.error_rate > self.thresholds["error_rate_warning"]:
                alert = SystemAlert(
                    alert_id=f"error_rate_warning_{component}_{int(current_time.timestamp())}",
                    timestamp=current_time,
                    level=AlertLevel.WARNING,
                    component=component,
                    title=f"Elevated Error Rate: {component}",
                    message=f"Component {component} error rate is {metrics.error_rate:.1f} errors/hour",
                    metrics={"error_rate": metrics.error_rate, "threshold": self.thresholds["error_rate_warning"]}
                )
                alerts.append(alert)
            
            # Check recovery rate
            if metrics.recovery_rate < self.thresholds["recovery_rate_warning"]:
                alert = SystemAlert(
                    alert_id=f"recovery_rate_warning_{component}_{int(current_time.timestamp())}",
                    timestamp=current_time,
                    level=AlertLevel.WARNING,
                    component=component,
                    title=f"Low Recovery Rate: {component}",
                    message=f"Component {component} recovery rate is {metrics.recovery_rate:.1%}",
                    metrics={"recovery_rate": metrics.recovery_rate, "threshold": self.thresholds["recovery_rate_warning"]}
                )
                alerts.append(alert)
            
            # Check MTTR
            if metrics.mean_time_to_recovery > self.thresholds["mttr_warning"]:
                alert = SystemAlert(
                    alert_id=f"mttr_warning_{component}_{int(current_time.timestamp())}",
                    timestamp=current_time,
                    level=AlertLevel.WARNING,
                    component=component,
                    title=f"High Mean Time to Recovery: {component}",
                    message=f"Component {component} MTTR is {metrics.mean_time_to_recovery:.0f} seconds",
                    metrics={"mttr": metrics.mean_time_to_recovery, "threshold": self.thresholds["mttr_warning"]}
                )
                alerts.append(alert)
        
        # Store alerts
        with self._lock:
            for alert in alerts:
                if alert.alert_id not in self.alerts:  # Avoid duplicates
                    self.alerts[alert.alert_id] = alert
        
        return alerts
    
    def identify_error_patterns(self) -> Dict[str, ErrorPattern]:
        """Identify common error patterns"""
        
        recent_errors = self.error_recovery_manager.get_recent_errors(limit=500)
        patterns = {}
        
        # Group errors by category and error type
        category_groups = defaultdict(list)
        for error in recent_errors:
            key = f"{error.category.value}_{error.error_type}"
            category_groups[key].append(error)
        
        for pattern_key, errors in category_groups.items():
            if len(errors) < 3:  # Need at least 3 occurrences to be a pattern
                continue
            
            category, error_type = pattern_key.split("_", 1)
            
            # Analyze severity distribution
            severity_dist = Counter([e.severity.value for e in errors])
            
            # Analyze time patterns (simplified)
            hours = [e.timestamp.hour for e in errors]
            if len(set(hours)) <= 3:  # Errors clustered in few hours
                time_pattern = "peak_hours"
            elif len(hours) > len(errors) * 0.8:
                time_pattern = "random"
            else:
                time_pattern = "periodic"
            
            # Calculate recovery success rate
            resolved_count = len([e for e in errors if e.resolved])
            recovery_success_rate = resolved_count / len(errors)
            
            # Get affected components
            components_affected = list(set([e.component for e in errors]))
            
            # Generate recommendations
            recommendations = self._generate_pattern_recommendations(
                category, error_type, recovery_success_rate, time_pattern
            )
            
            pattern = ErrorPattern(
                pattern_id=pattern_key,
                category=category,
                error_types=[error_type],
                frequency=len(errors),
                severity_distribution=dict(severity_dist),
                time_pattern=time_pattern,
                components_affected=components_affected,
                recovery_success_rate=recovery_success_rate,
                recommended_actions=recommendations
            )
            
            patterns[pattern_key] = pattern
        
        with self._lock:
            self.error_patterns = patterns
        
        return patterns
    
    def _generate_pattern_recommendations(self, category: str, error_type: str, 
                                        recovery_rate: float, time_pattern: str) -> List[str]:
        """Generate recommendations based on error patterns"""
        
        recommendations = []
        
        # Generic recommendations based on recovery rate
        if recovery_rate < 0.5:
            recommendations.append(f"Improve recovery procedures for {error_type} errors")
            recommendations.append("Consider adding fallback mechanisms")
        
        # Category-specific recommendations
        if category == "database":
            recommendations.append("Review database connection pooling settings")
            recommendations.append("Consider implementing database health checks")
        elif category == "network":
            recommendations.append("Implement exponential backoff for network retries")
            recommendations.append("Add network connectivity monitoring")
        elif category == "ocr":
            recommendations.append("Review image preprocessing parameters")
            recommendations.append("Consider alternative OCR engines for fallback")
        elif category == "performance":
            recommendations.append("Analyze system resource usage")
            recommendations.append("Consider scaling or optimization")
        
        # Time pattern recommendations
        if time_pattern == "peak_hours":
            recommendations.append("Implement load balancing during peak hours")
            recommendations.append("Consider resource scaling during high-usage periods")
        elif time_pattern == "periodic":
            recommendations.append("Investigate recurring system maintenance tasks")
            recommendations.append("Schedule preventive maintenance")
        
        return recommendations
    
    def generate_analytics_report(self) -> Dict[str, Any]:
        """Generate comprehensive analytics report"""
        
        current_time = datetime.now()
        
        # Gather all analytics data
        trends = self.analyze_error_trends()
        health_metrics = self.generate_health_metrics()
        alerts = self.detect_anomalies()
        patterns = self.identify_error_patterns()
        error_stats = self.error_recovery_manager.get_error_statistics()
        
        # Calculate summary metrics
        total_components = len(health_metrics)
        healthy_components = len([h for h in health_metrics.values() if h.performance_score > 80])
        critical_alerts = len([a for a in alerts if a.level == AlertLevel.CRITICAL])
        warning_alerts = len([a for a in alerts if a.level == AlertLevel.WARNING])
        
        # System-wide availability
        if health_metrics:
            avg_availability = statistics.mean([h.availability for h in health_metrics.values()])
            avg_performance = statistics.mean([h.performance_score for h in health_metrics.values()])
        else:
            avg_availability = 1.0
            avg_performance = 100.0
        
        report = {
            "report_timestamp": current_time.isoformat(),
            "summary": {
                "total_components": total_components,
                "healthy_components": healthy_components,
                "system_availability": avg_availability,
                "system_performance_score": avg_performance,
                "critical_alerts": critical_alerts,
                "warning_alerts": warning_alerts,
                "total_error_patterns": len(patterns)
            },
            "error_statistics": error_stats,
            "trends": {period: [t.__dict__ for t in trend_list] for period, trend_list in trends.items()},
            "health_metrics": {comp: metrics.__dict__ for comp, metrics in health_metrics.items()},
            "active_alerts": [alert.__dict__ for alert in alerts],
            "error_patterns": {pid: pattern.__dict__ for pid, pattern in patterns.items()},
            "recommendations": self._generate_system_recommendations(health_metrics, patterns, trends)
        }
        
        return report
    
    def _generate_system_recommendations(self, health_metrics: Dict, patterns: Dict, trends: Dict) -> List[str]:
        """Generate system-wide recommendations"""
        
        recommendations = []
        
        # Performance-based recommendations
        low_performance = [comp for comp, metrics in health_metrics.items() if metrics.performance_score < 70]
        if low_performance:
            recommendations.append(f"Review performance issues in components: {', '.join(low_performance)}")
        
        # Pattern-based recommendations
        high_frequency_patterns = [p for p in patterns.values() if p.frequency > 10]
        if high_frequency_patterns:
            for pattern in high_frequency_patterns:
                recommendations.extend(pattern.recommended_actions)
        
        # Trend-based recommendations
        for period_trends in trends.values():
            increasing_trends = [t for t in period_trends if t.direction == TrendDirection.INCREASING and t.error_rate > 5]
            if increasing_trends:
                components = [t.component for t in increasing_trends]
                recommendations.append(f"Monitor increasing error trends in: {', '.join(components)}")
        
        # Remove duplicates
        recommendations = list(set(recommendations))
        
        return recommendations[:10]  # Top 10 recommendations
    
    def _analysis_worker(self):
        """Background analysis worker"""
        while self.running:
            try:
                # Run analysis
                self.analyze_error_trends()
                self.generate_health_metrics()
                self.detect_anomalies()
                self.identify_error_patterns()
                
                # Clean up old data
                self._cleanup_old_data()
                
                time.sleep(self.analysis_interval)
            except Exception as e:
                logger.error(f"Error in analysis worker: {e}")
                time.sleep(60)  # Wait 1 minute before retry
    
    def _cleanup_old_data(self):
        """Clean up old analytics data"""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=24)
        
        with self._lock:
            # Clean up old alerts
            old_alerts = [aid for aid, alert in self.alerts.items() 
                         if alert.timestamp < cutoff_time and alert.resolved]
            for aid in old_alerts:
                del self.alerts[aid]
            
            # Clean up health metrics (already done in generate_health_metrics)
            # Clean up cache
            self.analysis_cache.clear()


# Singleton instance
error_analytics = ErrorAnalytics()