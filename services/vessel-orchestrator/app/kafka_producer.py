"""Kafka event producer for vessel-orchestrator"""
import json
from datetime import datetime
from typing import Any, Dict, List

import structlog
from aiokafka import AIOKafkaProducer

logger = structlog.get_logger()


class KafkaProducer:
    """Async Kafka producer for publishing events"""
    
    def __init__(self, bootstrap_servers: List[str]):
        self.bootstrap_servers = bootstrap_servers
        self.producer: AIOKafkaProducer = None
        
    async def start(self):
        """Start the Kafka producer"""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            compression_type='gzip',
        )
        await self.producer.start()
        logger.info("Kafka producer started", servers=self.bootstrap_servers)
        
    async def stop(self):
        """Stop the Kafka producer"""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")
    
    async def send_event(
        self,
        topic: str,
        event_type: str,
        payload: Dict[str, Any],
        key: str = None,
    ):
        """
        Send an event to Kafka
        
        Args:
            topic: Kafka topic name
            event_type: Event type identifier
            payload: Event payload data
            key: Optional partition key
        """
        event = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
        }
        
        try:
            await self.producer.send_and_wait(
                topic,
                value=event,
                key=key.encode('utf-8') if key else None,
            )
            logger.debug(
                "Event published",
                topic=topic,
                event_type=event_type,
                key=key,
            )
        except Exception as e:
            logger.error(
                "Failed to publish event",
                topic=topic,
                event_type=event_type,
                error=str(e),
            )
            raise

# Made with Bob
