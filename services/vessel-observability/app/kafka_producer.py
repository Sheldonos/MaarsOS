"""
Kafka producer for streaming observability events.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from kafka import KafkaProducer
from kafka.errors import KafkaError

from .config import settings
from .models import PolicyViolation, AnomalyDetection

logger = logging.getLogger(__name__)


class ObservabilityKafkaProducer:
    """Kafka producer for observability events."""
    
    def __init__(self):
        """Initialize Kafka producer."""
        self.producer: Optional[KafkaProducer] = None
        self.topics = settings.kafka_topics
    
    def connect(self):
        """Connect to Kafka."""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers.split(','),
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1,
                compression_type='gzip'
            )
            logger.info(f"Connected to Kafka at {settings.kafka_bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from Kafka."""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Disconnected from Kafka")
    
    async def send_event(
        self,
        topic: str,
        event_data: Dict[str, Any],
        key: Optional[str] = None
    ) -> bool:
        """
        Send an event to Kafka.
        
        Args:
            topic: Kafka topic
            event_data: Event data
            key: Optional message key for partitioning
            
        Returns:
            True if successful, False otherwise
        """
        if not self.producer:
            logger.warning("Kafka producer not connected")
            return False
        
        try:
            # Add timestamp if not present
            if 'timestamp' not in event_data:
                event_data['timestamp'] = datetime.utcnow().isoformat()
            
            # Send message
            future = self.producer.send(
                topic,
                value=event_data,
                key=key
            )
            
            # Wait for send to complete (with timeout)
            record_metadata = future.get(timeout=10)
            
            logger.debug(
                f"Event sent to {topic} "
                f"(partition: {record_metadata.partition}, offset: {record_metadata.offset})"
            )
            
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to send event to Kafka: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending event: {e}")
            return False
    
    async def send_guardrail_violation(self, violation: PolicyViolation) -> bool:
        """
        Send guardrail violation event.
        
        Args:
            violation: Policy violation
            
        Returns:
            True if successful
        """
        event_data = {
            "event_type": "guardrail_violation",
            "violation_id": violation.violation_id,
            "policy_id": violation.policy_id,
            "policy_name": violation.policy_name,
            "policy_type": violation.policy_type.value,
            "tenant_id": violation.tenant_id,
            "task_id": violation.task_id,
            "agent_id": violation.agent_id,
            "severity": violation.severity.value,
            "action_taken": violation.action_taken.value,
            "violation_details": violation.violation_details,
            "timestamp": violation.timestamp.isoformat(),
            "resolved": violation.resolved
        }
        
        return await self.send_event(
            self.topics["guardrail_violation"],
            event_data,
            key=violation.tenant_id
        )
    
    async def send_anomaly_detected(self, anomaly: AnomalyDetection) -> bool:
        """
        Send anomaly detection event.
        
        Args:
            anomaly: Anomaly detection
            
        Returns:
            True if successful
        """
        event_data = {
            "event_type": "anomaly_detected",
            "anomaly_id": anomaly.anomaly_id,
            "tenant_id": anomaly.tenant_id,
            "anomaly_type": anomaly.anomaly_type.value,
            "metric_name": anomaly.metric_name,
            "observed_value": anomaly.observed_value,
            "expected_value": anomaly.expected_value,
            "deviation": anomaly.deviation,
            "z_score": anomaly.z_score,
            "confidence": anomaly.confidence,
            "timestamp": anomaly.timestamp.isoformat(),
            "metadata": anomaly.metadata,
            "acknowledged": anomaly.acknowledged
        }
        
        return await self.send_event(
            self.topics["anomaly_detected"],
            event_data,
            key=anomaly.tenant_id
        )
    
    async def send_policy_created(
        self,
        policy_id: str,
        tenant_id: str,
        policy_name: str,
        policy_type: str
    ) -> bool:
        """
        Send policy created event.
        
        Args:
            policy_id: Policy identifier
            tenant_id: Tenant identifier
            policy_name: Policy name
            policy_type: Policy type
            
        Returns:
            True if successful
        """
        event_data = {
            "event_type": "policy_created",
            "policy_id": policy_id,
            "tenant_id": tenant_id,
            "policy_name": policy_name,
            "policy_type": policy_type
        }
        
        return await self.send_event(
            self.topics["policy_created"],
            event_data,
            key=tenant_id
        )
    
    async def send_policy_updated(
        self,
        policy_id: str,
        tenant_id: str,
        policy_name: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Send policy updated event.
        
        Args:
            policy_id: Policy identifier
            tenant_id: Tenant identifier
            policy_name: Policy name
            updates: Updated fields
            
        Returns:
            True if successful
        """
        event_data = {
            "event_type": "policy_updated",
            "policy_id": policy_id,
            "tenant_id": tenant_id,
            "policy_name": policy_name,
            "updates": updates
        }
        
        return await self.send_event(
            self.topics["policy_updated"],
            event_data,
            key=tenant_id
        )
    
    async def send_metric_threshold_exceeded(
        self,
        tenant_id: str,
        metric_name: str,
        current_value: float,
        threshold: float,
        severity: str = "warning"
    ) -> bool:
        """
        Send metric threshold exceeded event.
        
        Args:
            tenant_id: Tenant identifier
            metric_name: Metric name
            current_value: Current metric value
            threshold: Threshold value
            severity: Severity level
            
        Returns:
            True if successful
        """
        event_data = {
            "event_type": "metric_threshold_exceeded",
            "tenant_id": tenant_id,
            "metric_name": metric_name,
            "current_value": current_value,
            "threshold": threshold,
            "severity": severity,
            "exceeded_by": current_value - threshold,
            "exceeded_percent": ((current_value - threshold) / threshold * 100) if threshold > 0 else 0
        }
        
        return await self.send_event(
            self.topics["metric_threshold_exceeded"],
            event_data,
            key=tenant_id
        )
    
    async def send_alert(
        self,
        tenant_id: str,
        alert_type: str,
        severity: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send generic alert event.
        
        Args:
            tenant_id: Tenant identifier
            alert_type: Type of alert
            severity: Severity level (low, medium, high, critical)
            message: Alert message
            details: Additional details
            
        Returns:
            True if successful
        """
        event_data = {
            "event_type": "alert",
            "tenant_id": tenant_id,
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "details": details or {}
        }
        
        # Use appropriate topic based on severity
        topic = self.topics.get("metric_threshold_exceeded")  # Default topic
        
        return await self.send_event(
            topic,
            event_data,
            key=tenant_id
        )
    
    def get_producer_metrics(self) -> Dict[str, Any]:
        """
        Get Kafka producer metrics.
        
        Returns:
            Producer metrics
        """
        if not self.producer:
            return {"status": "disconnected"}
        
        try:
            metrics = self.producer.metrics()
            
            # Extract key metrics
            return {
                "status": "connected",
                "topics": list(self.topics.values()),
                "bootstrap_servers": settings.kafka_bootstrap_servers,
                "metrics_count": len(metrics)
            }
        except Exception as e:
            logger.error(f"Error getting producer metrics: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# Global Kafka producer instance
kafka_producer = ObservabilityKafkaProducer()

# Made with Bob
