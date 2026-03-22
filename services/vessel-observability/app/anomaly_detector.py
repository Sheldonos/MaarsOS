"""
Anomaly detection engine using statistical methods.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics

import numpy as np
from scipy import stats

from .config import settings
from .models import (
    AnomalyDetectionRequest,
    AnomalyDetectionResponse,
    AnomalyDetection,
    AnomalyType,
    MetricType,
)
from .database import db_manager

logger = logging.getLogger(__name__)


class MetricBaseline:
    """Maintains baseline statistics for a metric."""
    
    def __init__(self, window_size: int = 100):
        """
        Initialize metric baseline.
        
        Args:
            window_size: Number of samples to keep for baseline calculation
        """
        self.window_size = window_size
        self.values = deque(maxlen=window_size)
        self.timestamps = deque(maxlen=window_size)
    
    def add_value(self, value: float, timestamp: datetime):
        """Add a new value to the baseline."""
        self.values.append(value)
        self.timestamps.append(timestamp)
    
    def get_stats(self) -> Dict[str, float]:
        """Calculate baseline statistics."""
        if len(self.values) < settings.anomaly_min_samples:
            return {
                "mean": 0.0,
                "std": 0.0,
                "min": 0.0,
                "max": 0.0,
                "median": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "count": len(self.values)
            }
        
        values_array = np.array(list(self.values))
        
        return {
            "mean": float(np.mean(values_array)),
            "std": float(np.std(values_array)),
            "min": float(np.min(values_array)),
            "max": float(np.max(values_array)),
            "median": float(np.median(values_array)),
            "p95": float(np.percentile(values_array, 95)),
            "p99": float(np.percentile(values_array, 99)),
            "count": len(self.values)
        }
    
    def calculate_z_score(self, value: float) -> float:
        """Calculate z-score for a value."""
        if len(self.values) < settings.anomaly_min_samples:
            return 0.0
        
        stats_dict = self.get_stats()
        mean = stats_dict["mean"]
        std = stats_dict["std"]
        
        if std == 0:
            return 0.0
        
        return abs((value - mean) / std)
    
    def is_sufficient_data(self) -> bool:
        """Check if there's enough data for anomaly detection."""
        return len(self.values) >= settings.anomaly_min_samples


class AnomalyDetector:
    """Engine for detecting anomalies in metrics."""
    
    def __init__(self):
        """Initialize anomaly detector."""
        self.baselines: Dict[str, MetricBaseline] = defaultdict(
            lambda: MetricBaseline(window_size=settings.anomaly_window_size)
        )
        
        # Track recent anomalies to avoid duplicate alerts
        self.recent_anomalies: Dict[str, datetime] = {}
        self.anomaly_cooldown = timedelta(minutes=5)
    
    async def detect(
        self,
        request: AnomalyDetectionRequest
    ) -> AnomalyDetectionResponse:
        """
        Detect anomalies in metric data.
        
        Args:
            request: Anomaly detection request
            
        Returns:
            Detection response with anomaly information
        """
        start_time = datetime.utcnow()
        
        try:
            # Get or create baseline for this metric
            baseline_key = f"{request.tenant_id}:{request.metric_name}"
            baseline = self.baselines[baseline_key]
            
            # Add current value to baseline
            timestamp = request.timestamp or datetime.utcnow()
            baseline.add_value(request.metric_value, timestamp)
            
            # Check if we have enough data
            if not baseline.is_sufficient_data():
                return AnomalyDetectionResponse(
                    is_anomaly=False,
                    anomaly=None,
                    baseline_stats=baseline.get_stats(),
                    detection_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                )
            
            # Calculate z-score
            z_score = baseline.calculate_z_score(request.metric_value)
            baseline_stats = baseline.get_stats()
            
            # Determine if this is an anomaly
            is_anomaly = z_score > settings.anomaly_z_score_threshold
            
            # Check cooldown to avoid duplicate alerts
            if is_anomaly and baseline_key in self.recent_anomalies:
                last_anomaly = self.recent_anomalies[baseline_key]
                if datetime.utcnow() - last_anomaly < self.anomaly_cooldown:
                    is_anomaly = False
            
            anomaly = None
            if is_anomaly:
                # Determine anomaly type
                anomaly_type = self._determine_anomaly_type(request.metric_name)
                
                # Calculate confidence
                confidence = min(z_score / settings.anomaly_z_score_threshold, 1.0)
                
                # Create anomaly record
                anomaly = AnomalyDetection(
                    tenant_id=request.tenant_id,
                    anomaly_type=anomaly_type,
                    metric_name=request.metric_name,
                    observed_value=request.metric_value,
                    expected_value=baseline_stats["mean"],
                    deviation=request.metric_value - baseline_stats["mean"],
                    z_score=z_score,
                    confidence=confidence,
                    timestamp=timestamp,
                    metadata=request.metadata
                )
                
                # Record anomaly in database
                await db_manager.record_anomaly(anomaly)
                
                # Update recent anomalies
                self.recent_anomalies[baseline_key] = datetime.utcnow()
                
                logger.warning(
                    f"Anomaly detected: {request.metric_name} = {request.metric_value} "
                    f"(expected: {baseline_stats['mean']:.2f}, z-score: {z_score:.2f})"
                )
            
            detection_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return AnomalyDetectionResponse(
                is_anomaly=is_anomaly,
                anomaly=anomaly,
                baseline_stats=baseline_stats,
                detection_time_ms=detection_time_ms
            )
            
        except Exception as e:
            logger.error(f"Error detecting anomaly: {e}")
            return AnomalyDetectionResponse(
                is_anomaly=False,
                anomaly=None,
                baseline_stats={},
                detection_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
            )
    
    def _determine_anomaly_type(self, metric_name: str) -> AnomalyType:
        """Determine anomaly type based on metric name."""
        metric_lower = metric_name.lower()
        
        if "latency" in metric_lower or "duration" in metric_lower or "time" in metric_lower:
            return AnomalyType.LATENCY
        elif "error" in metric_lower or "failure" in metric_lower:
            return AnomalyType.ERROR_RATE
        elif "cost" in metric_lower or "price" in metric_lower:
            return AnomalyType.COST
        elif "cpu" in metric_lower or "memory" in metric_lower or "disk" in metric_lower:
            return AnomalyType.RESOURCE_USAGE
        else:
            return AnomalyType.PATTERN
    
    async def detect_latency_anomaly(
        self,
        tenant_id: str,
        service_name: str,
        latency_ms: float
    ) -> Optional[AnomalyDetection]:
        """
        Detect latency anomalies.
        
        Args:
            tenant_id: Tenant identifier
            service_name: Service name
            latency_ms: Latency in milliseconds
            
        Returns:
            Anomaly detection if anomaly found
        """
        request = AnomalyDetectionRequest(
            tenant_id=tenant_id,
            metric_name=f"{service_name}.latency",
            metric_value=latency_ms,
            metric_type=MetricType.HISTOGRAM,
            metadata={"service": service_name}
        )
        
        response = await self.detect(request)
        return response.anomaly
    
    async def detect_error_rate_anomaly(
        self,
        tenant_id: str,
        service_name: str,
        error_rate: float
    ) -> Optional[AnomalyDetection]:
        """
        Detect error rate anomalies.
        
        Args:
            tenant_id: Tenant identifier
            service_name: Service name
            error_rate: Error rate (0-100)
            
        Returns:
            Anomaly detection if anomaly found
        """
        request = AnomalyDetectionRequest(
            tenant_id=tenant_id,
            metric_name=f"{service_name}.error_rate",
            metric_value=error_rate,
            metric_type=MetricType.GAUGE,
            metadata={"service": service_name}
        )
        
        response = await self.detect(request)
        return response.anomaly
    
    async def detect_cost_anomaly(
        self,
        tenant_id: str,
        cost: float,
        context: str = "general"
    ) -> Optional[AnomalyDetection]:
        """
        Detect cost anomalies.
        
        Args:
            tenant_id: Tenant identifier
            cost: Cost amount
            context: Cost context (e.g., "llm", "compute")
            
        Returns:
            Anomaly detection if anomaly found
        """
        request = AnomalyDetectionRequest(
            tenant_id=tenant_id,
            metric_name=f"cost.{context}",
            metric_value=cost,
            metric_type=MetricType.COUNTER,
            metadata={"context": context}
        )
        
        response = await self.detect(request)
        return response.anomaly
    
    async def detect_resource_anomaly(
        self,
        tenant_id: str,
        resource_type: str,
        usage: float
    ) -> Optional[AnomalyDetection]:
        """
        Detect resource usage anomalies.
        
        Args:
            tenant_id: Tenant identifier
            resource_type: Type of resource (cpu, memory, disk)
            usage: Resource usage value
            
        Returns:
            Anomaly detection if anomaly found
        """
        request = AnomalyDetectionRequest(
            tenant_id=tenant_id,
            metric_name=f"resource.{resource_type}",
            metric_value=usage,
            metric_type=MetricType.GAUGE,
            metadata={"resource_type": resource_type}
        )
        
        response = await self.detect(request)
        return response.anomaly
    
    async def analyze_pattern(
        self,
        tenant_id: str,
        metric_name: str,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Analyze patterns in metric data over time.
        
        Args:
            tenant_id: Tenant identifier
            metric_name: Metric name
            time_window_hours: Time window for analysis
            
        Returns:
            Pattern analysis results
        """
        try:
            # Get historical data
            start_time = datetime.utcnow() - timedelta(hours=time_window_hours)
            metrics = await db_manager.get_metrics(
                metric_name=metric_name,
                tenant_id=tenant_id,
                start_time=start_time
            )
            
            if len(metrics) < settings.anomaly_min_samples:
                return {
                    "status": "insufficient_data",
                    "sample_count": len(metrics),
                    "required_samples": settings.anomaly_min_samples
                }
            
            # Extract values
            values = [m.get('value', 0) for m in metrics]
            values_array = np.array(values)
            
            # Calculate statistics
            mean = float(np.mean(values_array))
            std = float(np.std(values_array))
            
            # Detect trend using linear regression
            x = np.arange(len(values))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
            
            # Determine trend direction
            if abs(slope) < std * 0.1:
                trend = "stable"
            elif slope > 0:
                trend = "increasing"
            else:
                trend = "decreasing"
            
            # Calculate volatility
            volatility = float(std / mean) if mean != 0 else 0
            
            return {
                "status": "success",
                "sample_count": len(metrics),
                "time_window_hours": time_window_hours,
                "statistics": {
                    "mean": mean,
                    "std": std,
                    "min": float(np.min(values_array)),
                    "max": float(np.max(values_array)),
                    "median": float(np.median(values_array)),
                    "p95": float(np.percentile(values_array, 95)),
                    "p99": float(np.percentile(values_array, 99))
                },
                "trend": {
                    "direction": trend,
                    "slope": float(slope),
                    "r_squared": float(r_value ** 2),
                    "p_value": float(p_value)
                },
                "volatility": volatility
            }
            
        except Exception as e:
            logger.error(f"Error analyzing pattern: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def get_anomaly_summary(
        self,
        tenant_id: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get summary of anomalies for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            hours: Time window in hours
            
        Returns:
            Anomaly summary
        """
        start_time = datetime.utcnow() - timedelta(hours=hours)
        anomalies = await db_manager.get_anomalies(
            tenant_id=tenant_id,
            start_time=start_time
        )
        
        # Group by type
        by_type = defaultdict(int)
        by_metric = defaultdict(int)
        total_confidence = 0.0
        
        for anomaly in anomalies:
            by_type[anomaly.get('anomaly_type')] += 1
            by_metric[anomaly.get('metric_name')] += 1
            total_confidence += anomaly.get('confidence', 0)
        
        avg_confidence = total_confidence / len(anomalies) if anomalies else 0
        
        return {
            "tenant_id": tenant_id,
            "time_window_hours": hours,
            "total_anomalies": len(anomalies),
            "average_confidence": avg_confidence,
            "by_type": dict(by_type),
            "by_metric": dict(by_metric),
            "recent_anomalies": anomalies[:10]  # Last 10 anomalies
        }
    
    def clear_baseline(self, tenant_id: str, metric_name: str):
        """Clear baseline for a specific metric."""
        baseline_key = f"{tenant_id}:{metric_name}"
        if baseline_key in self.baselines:
            del self.baselines[baseline_key]
            logger.info(f"Cleared baseline for {baseline_key}")
    
    def get_baseline_info(self, tenant_id: str, metric_name: str) -> Dict[str, Any]:
        """Get information about a metric's baseline."""
        baseline_key = f"{tenant_id}:{metric_name}"
        baseline = self.baselines.get(baseline_key)
        
        if not baseline:
            return {
                "exists": False,
                "message": "No baseline found for this metric"
            }
        
        return {
            "exists": True,
            "sample_count": len(baseline.values),
            "window_size": baseline.window_size,
            "sufficient_data": baseline.is_sufficient_data(),
            "statistics": baseline.get_stats()
        }


# Global anomaly detector instance
anomaly_detector = AnomalyDetector()

# Made with Bob
