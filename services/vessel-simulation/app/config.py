"""
Configuration management for vessel-simulation service
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration"""
    
    # Service Identity
    SERVICE_NAME: str = "vessel-simulation"
    SERVICE_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8088
    
    # Database Configuration
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "maars"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "maars"
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_DB: int = 0
    REDIS_MAX_CONNECTIONS: int = 50
    
    # Kafka Configuration
    KAFKA_BROKERS: str = "localhost:9092"
    KAFKA_TOPIC_SIMULATIONS: str = "maars.simulations"
    KAFKA_TOPIC_EVENTS: str = "maars.events"
    KAFKA_CONSUMER_GROUP: str = "vessel-simulation"
    
    # Simulation Configuration
    SIMULATION_TIMEOUT: int = 300  # 5 minutes max per simulation
    MAX_CONCURRENT_SIMULATIONS: int = 10
    SIMULATION_ITERATIONS: int = 100  # Monte Carlo iterations
    CONFIDENCE_THRESHOLD: float = 0.75  # Minimum confidence for auto-approval
    
    # Scenario Configuration
    SCENARIO_MAX_STEPS: int = 1000
    SCENARIO_TIME_HORIZON: int = 86400  # 24 hours in seconds
    
    # Metrics Configuration
    METRICS_WINDOW_SIZE: int = 3600  # 1 hour
    METRICS_RETENTION_DAYS: int = 90
    
    # External Services
    ORCHESTRATOR_URL: str = "http://localhost:8081"
    MEMORY_URL: str = "http://localhost:8084"
    ECONOMICS_URL: str = "http://localhost:8090"
    OBSERVABILITY_URL: str = "http://localhost:8087"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Performance
    WORKER_THREADS: int = 4
    MAX_QUEUE_SIZE: int = 1000
    
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    @property
    def kafka_brokers_list(self) -> list[str]:
        """Parse Kafka brokers into list"""
        return [b.strip() for b in self.KAFKA_BROKERS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Made with Bob
