"""
Configuration management for vessel-observability service.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Service Configuration
    service_name: str = "vessel-observability"
    service_version: str = "1.0.0"
    environment: str = os.getenv("ENVIRONMENT", "development")
    port: int = int(os.getenv("PORT", "8087"))
    host: str = os.getenv("HOST", "0.0.0.0")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Database Configuration
    database_type: str = os.getenv("DATABASE_TYPE", "astradb")  # astradb or postgresql
    
    # AstraDB Configuration
    astra_db_id: Optional[str] = os.getenv("ASTRA_DB_ID")
    astra_db_region: Optional[str] = os.getenv("ASTRA_DB_REGION")
    astra_db_keyspace: str = os.getenv("ASTRA_DB_KEYSPACE", "maars")
    astra_db_token: Optional[str] = os.getenv("ASTRA_DB_TOKEN")
    astra_db_secure_bundle_path: Optional[str] = os.getenv("ASTRA_DB_SECURE_BUNDLE_PATH")
    
    # PostgreSQL Configuration (fallback)
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "maars_observability")
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_topic_prefix: str = os.getenv("KAFKA_TOPIC_PREFIX", "maars")
    kafka_consumer_group: str = os.getenv("KAFKA_CONSUMER_GROUP", "observability-service")
    
    # OpenTelemetry Configuration
    otel_enabled: bool = os.getenv("OTEL_ENABLED", "true").lower() == "true"
    otel_exporter_endpoint: str = os.getenv("OTEL_EXPORTER_ENDPOINT", "http://localhost:4318")
    otel_service_name: str = os.getenv("OTEL_SERVICE_NAME", "vessel-observability")
    otel_traces_exporter: str = os.getenv("OTEL_TRACES_EXPORTER", "otlp")
    otel_metrics_exporter: str = os.getenv("OTEL_METRICS_EXPORTER", "otlp")
    
    # Prometheus Configuration
    prometheus_enabled: bool = os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true"
    prometheus_port: int = int(os.getenv("PROMETHEUS_PORT", "9090"))
    
    # Guardrail Thresholds
    guardrail_max_requests_per_minute: int = int(os.getenv("GUARDRAIL_MAX_REQUESTS_PER_MINUTE", "100"))
    guardrail_max_requests_per_hour: int = int(os.getenv("GUARDRAIL_MAX_REQUESTS_PER_HOUR", "1000"))
    guardrail_max_cost_per_task: float = float(os.getenv("GUARDRAIL_MAX_COST_PER_TASK", "10.0"))
    guardrail_max_cost_per_tenant_daily: float = float(os.getenv("GUARDRAIL_MAX_COST_PER_TENANT_DAILY", "1000.0"))
    guardrail_max_execution_time_seconds: int = int(os.getenv("GUARDRAIL_MAX_EXECUTION_TIME_SECONDS", "300"))
    guardrail_max_memory_mb: int = int(os.getenv("GUARDRAIL_MAX_MEMORY_MB", "2048"))
    guardrail_max_cpu_percent: int = int(os.getenv("GUARDRAIL_MAX_CPU_PERCENT", "80"))
    
    # Content Policy Configuration
    content_filter_enabled: bool = os.getenv("CONTENT_FILTER_ENABLED", "true").lower() == "true"
    content_filter_profanity: bool = os.getenv("CONTENT_FILTER_PROFANITY", "true").lower() == "true"
    content_filter_pii: bool = os.getenv("CONTENT_FILTER_PII", "true").lower() == "true"
    content_filter_sensitive_data: bool = os.getenv("CONTENT_FILTER_SENSITIVE_DATA", "true").lower() == "true"
    
    # Anomaly Detection Parameters
    anomaly_detection_enabled: bool = os.getenv("ANOMALY_DETECTION_ENABLED", "true").lower() == "true"
    anomaly_z_score_threshold: float = float(os.getenv("ANOMALY_Z_SCORE_THRESHOLD", "3.0"))
    anomaly_window_size: int = int(os.getenv("ANOMALY_WINDOW_SIZE", "100"))
    anomaly_min_samples: int = int(os.getenv("ANOMALY_MIN_SAMPLES", "30"))
    
    # Latency Thresholds (milliseconds)
    latency_p95_threshold_ms: int = int(os.getenv("LATENCY_P95_THRESHOLD_MS", "1000"))
    latency_p99_threshold_ms: int = int(os.getenv("LATENCY_P99_THRESHOLD_MS", "2000"))
    
    # Error Rate Thresholds (percentage)
    error_rate_threshold_percent: float = float(os.getenv("ERROR_RATE_THRESHOLD_PERCENT", "5.0"))
    error_rate_window_minutes: int = int(os.getenv("ERROR_RATE_WINDOW_MINUTES", "5"))
    
    # Cost Anomaly Thresholds
    cost_anomaly_threshold_percent: float = float(os.getenv("COST_ANOMALY_THRESHOLD_PERCENT", "50.0"))
    cost_baseline_window_hours: int = int(os.getenv("COST_BASELINE_WINDOW_HOURS", "24"))
    
    # Resource Usage Thresholds
    cpu_spike_threshold_percent: float = float(os.getenv("CPU_SPIKE_THRESHOLD_PERCENT", "90.0"))
    memory_spike_threshold_percent: float = float(os.getenv("MEMORY_SPIKE_THRESHOLD_PERCENT", "90.0"))
    
    # Integration Endpoints
    orchestrator_url: str = os.getenv("ORCHESTRATOR_URL", "http://localhost:8081")
    llm_router_url: str = os.getenv("LLM_ROUTER_URL", "http://localhost:8083")
    swarm_url: str = os.getenv("SWARM_URL", "http://localhost:8086")
    economics_url: str = os.getenv("ECONOMICS_URL", "http://localhost:8088")
    
    # Alert Configuration
    alert_enabled: bool = os.getenv("ALERT_ENABLED", "true").lower() == "true"
    alert_webhook_url: Optional[str] = os.getenv("ALERT_WEBHOOK_URL")
    alert_email_enabled: bool = os.getenv("ALERT_EMAIL_ENABLED", "false").lower() == "true"
    alert_email_recipients: str = os.getenv("ALERT_EMAIL_RECIPIENTS", "")
    
    # Data Retention
    metrics_retention_days: int = int(os.getenv("METRICS_RETENTION_DAYS", "30"))
    traces_retention_days: int = int(os.getenv("TRACES_RETENTION_DAYS", "7"))
    violations_retention_days: int = int(os.getenv("VIOLATIONS_RETENTION_DAYS", "90"))
    
    # Performance Configuration
    max_concurrent_evaluations: int = int(os.getenv("MAX_CONCURRENT_EVALUATIONS", "100"))
    evaluation_timeout_seconds: int = int(os.getenv("EVALUATION_TIMEOUT_SECONDS", "30"))
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = False
    
    @property
    def database_url(self) -> str:
        """Get database connection URL based on database type."""
        if self.database_type == "postgresql":
            return (
                f"postgresql://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        return ""  # AstraDB uses different connection method
    
    @property
    def kafka_topics(self) -> dict:
        """Get Kafka topic names."""
        return {
            "guardrail_violation": f"{self.kafka_topic_prefix}.guardrail.violation",
            "anomaly_detected": f"{self.kafka_topic_prefix}.anomaly.detected",
            "policy_created": f"{self.kafka_topic_prefix}.policy.created",
            "policy_updated": f"{self.kafka_topic_prefix}.policy.updated",
            "metric_threshold_exceeded": f"{self.kafka_topic_prefix}.metric.threshold.exceeded",
        }
    
    def get_alert_recipients(self) -> list[str]:
        """Parse and return alert email recipients."""
        if not self.alert_email_recipients:
            return []
        return [email.strip() for email in self.alert_email_recipients.split(",")]


# Global settings instance
settings = Settings()

# Made with Bob
