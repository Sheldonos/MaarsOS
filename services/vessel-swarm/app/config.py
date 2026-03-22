"""Configuration management for vessel-swarm"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    SERVICE_NAME: str = "vessel-swarm"
    SERVICE_VERSION: str = "0.1.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8083
    
    # PostgreSQL configuration
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "maars"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "maars"
    
    # Kafka configuration
    KAFKA_BROKERS: str = "localhost:19092"
    KAFKA_TOPIC_AGENTS: str = "maars.agents"
    KAFKA_TOPIC_EVENTS: str = "maars.events"
    
    # Pool configuration
    DEFAULT_POOL_MIN_SIZE: int = 2
    DEFAULT_POOL_MAX_SIZE: int = 10
    POOL_WARMUP_ENABLED: bool = True
    AGENT_IDLE_TIMEOUT_SECONDS: int = 300  # 5 minutes
    AGENT_MAX_EXECUTION_TIME_SECONDS: int = 3600  # 1 hour
    
    # Agent configuration
    DEFAULT_AGENT_TYPE: str = "EPHEMERAL"
    DEFAULT_MODEL_TIER: str = "MID"
    DEFAULT_BUDGET_CEILING_USD: float = 10.0
    
    # Monitoring
    HEALTH_CHECK_INTERVAL_SECONDS: int = 10
    METRICS_ENABLED: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def database_url(self) -> str:
        """Get PostgreSQL connection URL"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()

# Made with Bob