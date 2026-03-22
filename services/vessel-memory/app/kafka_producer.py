"""
Kafka producer for vessel-memory service events.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from kafka import KafkaProducer
from kafka.errors import KafkaError

from .config import settings

logger = logging.getLogger(__name__)


class MemoryKafkaProducer:
    """Kafka producer for memory events."""
    
    def __init__(self):
        self.producer: Optional[KafkaProducer] = None
        self.topics = settings.kafka_topics
    
    async def connect(self):
        """Initialize Kafka producer."""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers.split(','),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1
            )
            logger.info(f"Connected to Kafka at {settings.kafka_bootstrap_servers}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise
    
    async def disconnect(self):
        """Close Kafka producer."""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Disconnected from Kafka")
    
    async def publish_memory_created(
        self,
        tenant_id: str,
        node_id: str,
        memory_type: str,
        agent_id: Optional[str] = None
    ):
        """Publish memory created event."""
        event = {
            "event_type": "memory.created",
            "tenant_id": tenant_id,
            "node_id": node_id,
            "memory_type": memory_type,
            "agent_id": agent_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._publish(self.topics["memory_created"], tenant_id, event)
    
    async def publish_memory_updated(
        self,
        tenant_id: str,
        node_id: str,
        updates: Dict[str, Any]
    ):
        """Publish memory updated event."""
        event = {
            "event_type": "memory.updated",
            "tenant_id": tenant_id,
            "node_id": node_id,
            "updates": updates,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._publish(self.topics["memory_updated"], tenant_id, event)
    
    async def publish_memory_deleted(
        self,
        tenant_id: str,
        node_id: str
    ):
        """Publish memory deleted event."""
        event = {
            "event_type": "memory.deleted",
            "tenant_id": tenant_id,
            "node_id": node_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._publish(self.topics["memory_deleted"], tenant_id, event)
    
    async def publish_memory_retrieved(
        self,
        tenant_id: str,
        query: str,
        result_count: int,
        agent_id: Optional[str] = None
    ):
        """Publish memory retrieved event."""
        event = {
            "event_type": "memory.retrieved",
            "tenant_id": tenant_id,
            "query": query,
            "result_count": result_count,
            "agent_id": agent_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._publish(self.topics["memory_retrieved"], tenant_id, event)
    
    async def publish_graph_updated(
        self,
        tenant_id: str,
        update_type: str,  # node_created, edge_created, etc.
        entity_id: str,
        details: Dict[str, Any]
    ):
        """Publish graph updated event."""
        event = {
            "event_type": "graph.updated",
            "tenant_id": tenant_id,
            "update_type": update_type,
            "entity_id": entity_id,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._publish(self.topics["graph_updated"], tenant_id, event)
    
    async def _publish(self, topic: str, key: str, event: Dict[str, Any]):
        """Publish event to Kafka topic."""
        try:
            if not self.producer:
                logger.warning("Kafka producer not initialized, skipping event")
                return
            
            future = self.producer.send(topic, key=key, value=event)
            
            # Wait for send to complete (with timeout)
            record_metadata = future.get(timeout=10)
            
            logger.debug(
                f"Published event to {topic}: "
                f"partition={record_metadata.partition}, "
                f"offset={record_metadata.offset}"
            )
            
        except KafkaError as e:
            logger.error(f"Failed to publish event to {topic}: {e}")
            # Don't raise - we don't want Kafka failures to break the service
        except Exception as e:
            logger.error(f"Unexpected error publishing to Kafka: {e}")


# Global Kafka producer instance
kafka_producer = MemoryKafkaProducer()

# Made with Bob