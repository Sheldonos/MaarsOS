"""Kafka producer for vessel-swarm events"""
import json
from typing import Optional
from datetime import datetime
from aiokafka import AIOKafkaProducer
import structlog

from .config import settings

logger = structlog.get_logger()


class KafkaProducer:
    """Kafka producer for publishing agent events"""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.logger = logger.bind(component="kafka_producer")
    
    async def start(self):
        """Start Kafka producer"""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BROKERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
            )
            await self.producer.start()
            self.logger.info("kafka_producer_started", brokers=settings.KAFKA_BROKERS)
        except Exception as e:
            self.logger.error("kafka_producer_start_failed", error=str(e))
            raise
    
    async def stop(self):
        """Stop Kafka producer"""
        if self.producer:
            await self.producer.stop()
            self.logger.info("kafka_producer_stopped")
    
    async def send_event(
        self,
        topic: str,
        event_type: str,
        payload: dict,
        key: Optional[str] = None,
    ):
        """Send event to Kafka topic"""
        if not self.producer:
            self.logger.warning("kafka_producer_not_started")
            return
        
        try:
            event = {
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "payload": payload,
            }
            
            await self.producer.send(topic, value=event, key=key)
            
            self.logger.debug(
                "event_sent",
                topic=topic,
                event_type=event_type,
                key=key,
            )
            
        except Exception as e:
            self.logger.error(
                "send_event_failed",
                error=str(e),
                topic=topic,
                event_type=event_type,
            )
    
    async def health_check(self) -> bool:
        """Check if Kafka producer is healthy"""
        return self.producer is not None


# Global Kafka producer instance
kafka_producer = KafkaProducer()


# Made with Bob