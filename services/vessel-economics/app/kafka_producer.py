"""
Kafka event producer for vessel-economics service.
Publishes economic events to Kafka topics.
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError

from .config import settings

logger = logging.getLogger(__name__)


class EconomicsKafkaProducer:
    """Kafka producer for economic events."""
    
    def __init__(self):
        """Initialize Kafka producer."""
        self.producer: Optional[KafkaProducer] = None
        self.topic_prefix = settings.kafka_topic_prefix
        
    async def connect(self):
        """Connect to Kafka."""
        try:
            kafka_config = {
                'bootstrap_servers': settings.kafka_bootstrap_servers.split(','),
                'value_serializer': lambda v: json.dumps(v).encode('utf-8'),
                'key_serializer': lambda k: k.encode('utf-8') if k else None,
                'acks': 'all',
                'retries': 3,
                'max_in_flight_requests_per_connection': 1
            }
            
            # Add SSL/SASL configuration if enabled
            if settings.kafka_enable_ssl:
                kafka_config['security_protocol'] = 'SASL_SSL'
                
            if settings.kafka_sasl_mechanism:
                kafka_config['sasl_mechanism'] = settings.kafka_sasl_mechanism
                kafka_config['sasl_plain_username'] = settings.kafka_sasl_username
                kafka_config['sasl_plain_password'] = settings.kafka_sasl_password
                
            self.producer = KafkaProducer(**kafka_config)
            
            logger.info("Connected to Kafka")
            
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            # Don't raise - allow service to run without Kafka
            self.producer = None
            
    async def disconnect(self):
        """Disconnect from Kafka."""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Disconnected from Kafka")
            
    async def publish_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        key: Optional[str] = None
    ):
        """
        Publish an event to Kafka.
        
        Args:
            event_type: Type of event (e.g., 'cost.tracked', 'budget.exceeded')
            data: Event data
            key: Optional partition key
        """
        if not self.producer:
            logger.warning("Kafka producer not connected, skipping event publication")
            return
            
        try:
            # Construct topic name
            topic = f"{self.topic_prefix}.{event_type}"
            
            # Add metadata
            event = {
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "service": settings.service_name,
                "version": settings.service_version,
                "data": data
            }
            
            # Publish to Kafka
            future = self.producer.send(
                topic,
                value=event,
                key=key
            )
            
            # Wait for confirmation (with timeout)
            record_metadata = future.get(timeout=10)
            
            logger.debug(
                f"Published event to Kafka: topic={topic}, "
                f"partition={record_metadata.partition}, "
                f"offset={record_metadata.offset}"
            )
            
        except KafkaError as e:
            logger.error(f"Failed to publish event to Kafka: {e}")
        except Exception as e:
            logger.error(f"Unexpected error publishing event: {e}")
            
    async def publish_cost_tracked(
        self,
        cost_id: str,
        tenant_id: str,
        task_id: str,
        cost: str,
        category: str,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ):
        """Publish cost tracked event."""
        await self.publish_event(
            "cost.tracked",
            {
                "cost_id": cost_id,
                "tenant_id": tenant_id,
                "task_id": task_id,
                "cost": cost,
                "category": category,
                "provider": provider,
                "model": model
            },
            key=tenant_id
        )
        
    async def publish_budget_exceeded(
        self,
        tenant_id: str,
        task_id: str,
        estimated_cost: str,
        available_budget: str,
        total_budget: str,
        used_budget: str
    ):
        """Publish budget exceeded event."""
        await self.publish_event(
            "budget.exceeded",
            {
                "tenant_id": tenant_id,
                "task_id": task_id,
                "estimated_cost": estimated_cost,
                "available_budget": available_budget,
                "total_budget": total_budget,
                "used_budget": used_budget
            },
            key=tenant_id
        )
        
    async def publish_budget_alert(
        self,
        tenant_id: str,
        status: str,
        usage_percentage: str,
        used_budget: str,
        total_budget: str,
        remaining_budget: str
    ):
        """Publish budget alert event."""
        await self.publish_event(
            "budget.alert",
            {
                "tenant_id": tenant_id,
                "status": status,
                "usage_percentage": usage_percentage,
                "used_budget": used_budget,
                "total_budget": total_budget,
                "remaining_budget": remaining_budget
            },
            key=tenant_id
        )
        
    async def publish_escrow_allocated(
        self,
        transaction_id: str,
        tenant_id: str,
        amount: str,
        balance: str
    ):
        """Publish escrow allocated event."""
        await self.publish_event(
            "escrow.allocated",
            {
                "transaction_id": transaction_id,
                "tenant_id": tenant_id,
                "amount": amount,
                "balance": balance
            },
            key=tenant_id
        )
        
    async def publish_escrow_released(
        self,
        transaction_id: str,
        tenant_id: str,
        amount: str,
        task_id: str,
        balance: str
    ):
        """Publish escrow released event."""
        await self.publish_event(
            "escrow.released",
            {
                "transaction_id": transaction_id,
                "tenant_id": tenant_id,
                "amount": amount,
                "task_id": task_id,
                "balance": balance
            },
            key=tenant_id
        )
        
    async def publish_escrow_refunded(
        self,
        transaction_id: str,
        tenant_id: str,
        amount: str,
        task_id: str,
        reason: Optional[str] = None
    ):
        """Publish escrow refunded event."""
        await self.publish_event(
            "escrow.refunded",
            {
                "transaction_id": transaction_id,
                "tenant_id": tenant_id,
                "amount": amount,
                "task_id": task_id,
                "reason": reason
            },
            key=tenant_id
        )
        
    async def publish_invoice_generated(
        self,
        invoice_id: str,
        tenant_id: str,
        total_amount: str,
        billing_period_start: str,
        billing_period_end: str
    ):
        """Publish invoice generated event."""
        await self.publish_event(
            "invoice.generated",
            {
                "invoice_id": invoice_id,
                "tenant_id": tenant_id,
                "total_amount": total_amount,
                "billing_period_start": billing_period_start,
                "billing_period_end": billing_period_end
            },
            key=tenant_id
        )
        
    async def publish_compliance_report_created(
        self,
        report_id: str,
        report_type: str,
        tenant_id: Optional[str],
        total_transactions: int,
        total_cost: str
    ):
        """Publish compliance report created event."""
        await self.publish_event(
            "compliance.report.created",
            {
                "report_id": report_id,
                "report_type": report_type,
                "tenant_id": tenant_id,
                "total_transactions": total_transactions,
                "total_cost": total_cost
            },
            key=tenant_id if tenant_id else "system"
        )


# Global Kafka producer instance
kafka_producer = EconomicsKafkaProducer()

# Made with Bob
