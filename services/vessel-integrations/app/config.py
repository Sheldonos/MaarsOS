"""
Configuration management for vessel-integrations service.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Service Configuration
    SERVICE_NAME: str = "vessel-integrations"
    SERVICE_VERSION: str = "1.0.0"
    PORT: int = 8091
    HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "INFO"
    
    # Database Configuration
    DATABASE_URL: str = "postgresql://maars:maars@localhost:5432/maars"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:19092"
    KAFKA_TOPIC_PREFIX: str = "maars"
    KAFKA_CONSUMER_GROUP: str = "vessel-integrations"
    
    # Slack Configuration
    SLACK_BOT_TOKEN: Optional[str] = None
    SLACK_SIGNING_SECRET: Optional[str] = None
    SLACK_APP_TOKEN: Optional[str] = None  # For Socket Mode
    SLACK_CLIENT_ID: Optional[str] = None
    SLACK_CLIENT_SECRET: Optional[str] = None
    
    # Vault Configuration (for storing OAuth tokens)
    VAULT_ADDR: str = "http://localhost:8200"
    VAULT_TOKEN: Optional[str] = None
    VAULT_MOUNT_POINT: str = "secret"
    
    # Gateway Configuration
    GATEWAY_URL: str = "http://localhost:8000"
    INTERNAL_SERVICE_TOKEN: Optional[str] = None
    
    # MCP Server Configuration
    MCP_SERVER_TIMEOUT: int = 30
    MCP_SERVER_MAX_RETRIES: int = 3
    
    # Metrics Configuration
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9091
    
    # OpenTelemetry Configuration
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    OTEL_SERVICE_NAME: str = "vessel-integrations"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Made with Bob
