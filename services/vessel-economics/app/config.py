"""
Configuration management for vessel-economics service.
"""

from pydantic_settings import BaseSettings
from typing import Optional
from decimal import Decimal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Service Configuration
    service_name: str = "vessel-economics"
    service_version: str = "1.0.0"
    port: int = 8090
    host: str = "0.0.0.0"
    log_level: str = "INFO"
    
    # Database Configuration
    database_type: str = "postgresql"  # postgresql or astradb
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "vessel_economics"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    
    # AstraDB Configuration (alternative to PostgreSQL)
    astra_db_id: Optional[str] = None
    astra_db_region: Optional[str] = None
    astra_db_keyspace: str = "vessel_economics"
    astra_db_token: Optional[str] = None
    astra_secure_bundle_path: Optional[str] = None
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_prefix: str = "vessel.economics"
    kafka_consumer_group: str = "vessel-economics-group"
    kafka_enable_ssl: bool = False
    kafka_sasl_mechanism: Optional[str] = None
    kafka_sasl_username: Optional[str] = None
    kafka_sasl_password: Optional[str] = None
    
    # Cost Calculation Parameters (per 1K tokens)
    # OpenAI GPT-4
    openai_gpt4_input_cost: Decimal = Decimal("0.03")
    openai_gpt4_output_cost: Decimal = Decimal("0.06")
    
    # OpenAI GPT-4 Turbo
    openai_gpt4_turbo_input_cost: Decimal = Decimal("0.01")
    openai_gpt4_turbo_output_cost: Decimal = Decimal("0.03")
    
    # OpenAI GPT-3.5-turbo
    openai_gpt35_turbo_input_cost: Decimal = Decimal("0.0015")
    openai_gpt35_turbo_output_cost: Decimal = Decimal("0.002")
    
    # Anthropic Claude 3 Opus
    anthropic_claude3_opus_input_cost: Decimal = Decimal("0.015")
    anthropic_claude3_opus_output_cost: Decimal = Decimal("0.075")
    
    # Anthropic Claude 3 Sonnet
    anthropic_claude3_sonnet_input_cost: Decimal = Decimal("0.003")
    anthropic_claude3_sonnet_output_cost: Decimal = Decimal("0.015")
    
    # Anthropic Claude 3 Haiku
    anthropic_claude3_haiku_input_cost: Decimal = Decimal("0.00025")
    anthropic_claude3_haiku_output_cost: Decimal = Decimal("0.00125")
    
    # Anthropic Claude 2
    anthropic_claude2_input_cost: Decimal = Decimal("0.008")
    anthropic_claude2_output_cost: Decimal = Decimal("0.024")
    
    # Google PaLM 2
    google_palm2_input_cost: Decimal = Decimal("0.00025")
    google_palm2_output_cost: Decimal = Decimal("0.0005")
    
    # Budget Thresholds (percentage of total budget)
    budget_warning_threshold: Decimal = Decimal("0.80")  # 80%
    budget_critical_threshold: Decimal = Decimal("0.90")  # 90%
    budget_exhausted_threshold: Decimal = Decimal("1.00")  # 100%
    
    # Budget Enforcement
    enable_hard_limits: bool = True  # Block tasks when budget exceeded
    enable_soft_limits: bool = True  # Warn when approaching limits
    default_tenant_budget: Decimal = Decimal("1000.00")  # Default budget in USD
    
    # Escrow Configuration
    escrow_lock_timeout_seconds: int = 3600  # 1 hour
    escrow_auto_release_on_success: bool = True
    escrow_auto_refund_on_failure: bool = True
    minimum_escrow_balance: Decimal = Decimal("10.00")  # Minimum balance in USD
    
    # Compliance Settings
    audit_trail_retention_days: int = 2555  # 7 years for compliance
    enable_detailed_logging: bool = True
    enable_transaction_reconciliation: bool = True
    compliance_report_formats: list = ["json", "csv", "pdf"]
    
    # Billing Configuration
    billing_cycle_days: int = 30
    invoice_generation_enabled: bool = True
    invoice_currency: str = "USD"
    tax_rate: Decimal = Decimal("0.00")  # Default 0%, configurable per tenant
    
    # Integration Endpoints
    vessel_llm_router_url: str = "http://localhost:8083"
    vessel_orchestrator_url: str = "http://localhost:8081"
    vessel_observability_url: str = "http://localhost:8089"
    
    # Prometheus Metrics
    metrics_enabled: bool = True
    metrics_port: int = 8090
    metrics_path: str = "/metrics"
    
    # Health Check
    health_check_path: str = "/health"
    
    # CORS Configuration
    cors_origins: list = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list = ["*"]
    cors_allow_headers: list = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Made with Bob
