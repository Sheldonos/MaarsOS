"""Configuration management for vessel-orchestrator"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    SERVICE_NAME: str = "vessel-orchestrator"
    SERVICE_VERSION: str = "0.2.0"  # Updated for Phase 2 features
    HOST: str = "0.0.0.0"
    PORT: int = 8081
    
    # Kafka configuration
    KAFKA_BROKERS: str = "localhost:19092"
    KAFKA_TOPIC_GOALS: str = "maars.goals"
    KAFKA_TOPIC_TASKS: str = "maars.tasks"
    KAFKA_TOPIC_EVENTS: str = "maars.events"
    
    # Sandbox service
    SANDBOX_URL: str = "http://localhost:8085"
    
    # LLM Router service
    LLM_ROUTER_URL: str = "http://localhost:8082"
    
    # Database (AstraDB)
    ASTRA_DB_ID: str = ""
    ASTRA_DB_REGION: str = "us-east1"
    ASTRA_DB_KEYSPACE: str = "maars"
    ASTRA_DB_TOKEN: str = ""
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Phase 2: DAG and Right-Sizing Configuration
    ENABLE_DAG_MODE: bool = True
    MAX_PARALLEL_TASKS: int = 5
    DEFAULT_MODEL_TIER: str = "mid"  # nano, mid, frontier
    ENABLE_RIGHT_SIZING: bool = True
    
    # Resource limits by tier (can be overridden)
    NANO_MAX_EXECUTION_MS: int = 5000
    NANO_MAX_MEMORY_MB: int = 128
    MID_MAX_EXECUTION_MS: int = 30000
    MID_MAX_MEMORY_MB: int = 512
    FRONTIER_MAX_EXECUTION_MS: int = 120000
    FRONTIER_MAX_MEMORY_MB: int = 2048
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Made with Bob
