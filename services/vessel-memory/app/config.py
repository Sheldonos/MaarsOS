"""
Configuration management for vessel-memory service.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Service Configuration
    service_name: str = "vessel-memory"
    service_version: str = "1.0.0"
    environment: str = os.getenv("ENVIRONMENT", "development")
    port: int = int(os.getenv("PORT", "8084"))
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
    postgres_db: str = os.getenv("POSTGRES_DB", "maars_memory")
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    
    # Qdrant Vector Store Configuration
    qdrant_host: str = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", "6333"))
    qdrant_grpc_port: int = int(os.getenv("QDRANT_GRPC_PORT", "6334"))
    qdrant_api_key: Optional[str] = os.getenv("QDRANT_API_KEY")
    qdrant_collection_prefix: str = os.getenv("QDRANT_COLLECTION_PREFIX", "maars")
    
    # Neo4j Knowledge Graph Configuration
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password")
    neo4j_database: str = os.getenv("NEO4J_DATABASE", "neo4j")
    
    # Embedding Configuration
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "3072"))
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "openai")  # openai or local
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Local Embedding Model (if using local)
    local_embedding_model: str = os.getenv("LOCAL_EMBEDDING_MODEL", "nomic-embed-text")
    local_embedding_device: str = os.getenv("LOCAL_EMBEDDING_DEVICE", "cpu")
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_topic_prefix: str = os.getenv("KAFKA_TOPIC_PREFIX", "maars")
    kafka_consumer_group: str = os.getenv("KAFKA_CONSUMER_GROUP", "memory-service")
    
    # Memory Configuration
    memory_ttl_episodic_days: int = int(os.getenv("MEMORY_TTL_EPISODIC_DAYS", "90"))
    memory_ttl_semantic_days: int = int(os.getenv("MEMORY_TTL_SEMANTIC_DAYS", "365"))
    memory_ttl_procedural_days: int = int(os.getenv("MEMORY_TTL_PROCEDURAL_DAYS", "180"))
    
    # Vector Search Configuration
    vector_search_top_k: int = int(os.getenv("VECTOR_SEARCH_TOP_K", "10"))
    vector_search_score_threshold: float = float(os.getenv("VECTOR_SEARCH_SCORE_THRESHOLD", "0.7"))
    vector_search_timeout_seconds: int = int(os.getenv("VECTOR_SEARCH_TIMEOUT_SECONDS", "5"))
    
    # GraphRAG Configuration
    graph_max_depth: int = int(os.getenv("GRAPH_MAX_DEPTH", "3"))
    graph_max_nodes: int = int(os.getenv("GRAPH_MAX_NODES", "100"))
    graph_relationship_types: str = os.getenv("GRAPH_RELATIONSHIP_TYPES", "RELATES_TO,DEPENDS_ON,CAUSED_BY,SIMILAR_TO")
    
    # Memory Provenance Configuration
    provenance_enabled: bool = os.getenv("PROVENANCE_ENABLED", "true").lower() == "true"
    provenance_hash_algorithm: str = os.getenv("PROVENANCE_HASH_ALGORITHM", "sha256")
    
    # Privacy Configuration
    privacy_federation_enabled: bool = os.getenv("PRIVACY_FEDERATION_ENABLED", "false").lower() == "true"
    privacy_mask_pii: bool = os.getenv("PRIVACY_MASK_PII", "true").lower() == "true"
    privacy_anonymize_cross_tenant: bool = os.getenv("PRIVACY_ANONYMIZE_CROSS_TENANT", "true").lower() == "true"
    
    # Performance Configuration
    max_concurrent_embeddings: int = int(os.getenv("MAX_CONCURRENT_EMBEDDINGS", "10"))
    embedding_batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    
    # Integration Endpoints
    orchestrator_url: str = os.getenv("ORCHESTRATOR_URL", "http://localhost:8081")
    identity_url: str = os.getenv("IDENTITY_URL", "http://localhost:8083")
    
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
    def qdrant_url(self) -> str:
        """Get Qdrant connection URL."""
        return f"http://{self.qdrant_host}:{self.qdrant_port}"
    
    @property
    def kafka_topics(self) -> dict:
        """Get Kafka topic names."""
        return {
            "memory_created": f"{self.kafka_topic_prefix}.memory.created",
            "memory_updated": f"{self.kafka_topic_prefix}.memory.updated",
            "memory_deleted": f"{self.kafka_topic_prefix}.memory.deleted",
            "memory_retrieved": f"{self.kafka_topic_prefix}.memory.retrieved",
            "graph_updated": f"{self.kafka_topic_prefix}.graph.updated",
        }
    
    def get_relationship_types(self) -> list[str]:
        """Parse and return graph relationship types."""
        return [rt.strip() for rt in self.graph_relationship_types.split(",")]


# Global settings instance
settings = Settings()

# Made with Bob