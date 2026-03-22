"""
Kafka event producer for vessel-integrations service.
"""

from aiokafka import AIOKafkaProducer
from typing import Dict, Any, Optional
import json
import logging
from datetime import datetime
import uuid

from app.config import settings

logger = logging.getLogger(__name__)


class KafkaEventProducer:
    """Async Kafka producer for publishing integration events."""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.topic_prefix = settings.KAFKA_TOPIC_PREFIX
        
    async def start(self):
        """Start Kafka producer."""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                compression_type='gzip',
                acks='all',
                retries=3
            )
            await self.producer.start()
            logger.info("Kafka producer started successfully")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise
    
    async def stop(self):
        """Stop Kafka producer."""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")
    
    async def publish_event(
        self,
        topic: str,
        event_type: str,
        payload: Dict[str, Any],
        tenant_id: str,
        key: Optional[str] = None
    ) -> None:
        """
        Publish an event to Kafka.
        
        Args:
            topic: Topic name (without prefix)
            event_type: Type of event
            payload: Event payload
            tenant_id: Tenant ID
            key: Optional partition key
        """
        if not self.producer:
            logger.error("Kafka producer not started")
            return
        
        full_topic = f"{self.topic_prefix}.{topic}"
        
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "tenant_id": tenant_id,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload
        }
        
        try:
            await self.producer.send(
                full_topic,
                value=event,
                key=key or tenant_id
            )
            logger.debug(f"Published event {event_type} to {full_topic}")
        except Exception as e:
            logger.error(f"Failed to publish event to {full_topic}: {e}")
            raise
    
    async def publish_goal_event(
        self,
        goal_id: str,
        event_type: str,
        payload: Dict[str, Any],
        tenant_id: str
    ) -> None:
        """Publish goal-related event."""
        await self.publish_event(
            topic=f"goals.{goal_id}",
            event_type=event_type,
            payload=payload,
            tenant_id=tenant_id,
            key=goal_id
        )
    
    async def publish_slack_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        tenant_id: str,
        workspace_id: str
    ) -> None:
        """Publish Slack integration event."""
        await self.publish_event(
            topic="integrations.slack",
            event_type=event_type,
            payload={**payload, "workspace_id": workspace_id},
            tenant_id=tenant_id,
            key=workspace_id
        )
    
    async def publish_mcp_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        tenant_id: str,
        server_id: str
    ) -> None:
        """Publish MCP server event."""
        await self.publish_event(
            topic="integrations.mcp",
            event_type=event_type,
            payload={**payload, "server_id": server_id},
            tenant_id=tenant_id,
            key=server_id
        )


# Global producer instance
kafka_producer = KafkaEventProducer()

# Made with Bob
