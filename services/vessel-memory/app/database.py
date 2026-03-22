"""
Database connection and management for vessel-memory service.
"""

import logging
from typing import Optional
from contextlib import asynccontextmanager

from cassandra.cluster import Cluster, Session
from cassandra.auth import PlainTextAuthProvider
import psycopg2
from psycopg2.pool import SimpleConnectionPool

from .config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections for AstraDB or PostgreSQL."""
    
    def __init__(self):
        self.db_type = settings.database_type
        self.session: Optional[Session] = None
        self.pg_pool: Optional[SimpleConnectionPool] = None
        
    async def connect(self):
        """Establish database connection."""
        if self.db_type == "astradb":
            await self._connect_astradb()
        else:
            await self._connect_postgresql()
        
        logger.info(f"Connected to {self.db_type} database")
    
    async def _connect_astradb(self):
        """Connect to AstraDB."""
        try:
            if settings.astra_db_secure_bundle_path:
                # Cloud connection with secure bundle
                cloud_config = {
                    'secure_connect_bundle': settings.astra_db_secure_bundle_path
                }
                auth_provider = PlainTextAuthProvider(
                    username='token',
                    password=settings.astra_db_token
                )
                cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider)
            else:
                # Local connection (for development)
                cluster = Cluster(['localhost'])
            
            self.session = cluster.connect(settings.astra_db_keyspace)
            logger.info("Connected to AstraDB")
            
        except Exception as e:
            logger.error(f"Failed to connect to AstraDB: {e}")
            raise
    
    async def _connect_postgresql(self):
        """Connect to PostgreSQL."""
        try:
            self.pg_pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=settings.postgres_host,
                port=settings.postgres_port,
                database=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password
            )
            logger.info("Connected to PostgreSQL")
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    async def disconnect(self):
        """Close database connections."""
        if self.session:
            self.session.shutdown()
            logger.info("Disconnected from AstraDB")
        
        if self.pg_pool:
            self.pg_pool.closeall()
            logger.info("Disconnected from PostgreSQL")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool."""
        if self.db_type == "astradb":
            yield self.session
        else:
            conn = self.pg_pool.getconn()
            try:
                yield conn
            finally:
                self.pg_pool.putconn(conn)
    
    async def execute_query(self, query: str, params: tuple = None):
        """Execute a query and return results."""
        async with self.get_connection() as conn:
            if self.db_type == "astradb":
                if params:
                    result = conn.execute(query, params)
                else:
                    result = conn.execute(query)
                return list(result)
            else:
                cursor = conn.cursor()
                try:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    
                    if cursor.description:
                        return cursor.fetchall()
                    conn.commit()
                    return []
                finally:
                    cursor.close()
    
    async def execute_batch(self, queries: list):
        """Execute multiple queries in a batch."""
        async with self.get_connection() as conn:
            if self.db_type == "astradb":
                from cassandra.query import BatchStatement
                batch = BatchStatement()
                for query, params in queries:
                    batch.add(query, params)
                self.session.execute(batch)
            else:
                cursor = conn.cursor()
                try:
                    for query, params in queries:
                        cursor.execute(query, params)
                    conn.commit()
                finally:
                    cursor.close()
    
    async def create_tables(self):
        """Create necessary tables if they don't exist."""
        if self.db_type == "postgresql":
            await self._create_postgresql_tables()
        # AstraDB tables are created via schema file
    
    async def _create_postgresql_tables(self):
        """Create PostgreSQL tables."""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS memory_metadata (
                node_id UUID PRIMARY KEY,
                tenant_id UUID NOT NULL,
                agent_id UUID,
                memory_type VARCHAR(50) NOT NULL,
                importance_score FLOAT NOT NULL,
                provenance_hash VARCHAR(64),
                source_task_id UUID,
                source_tool VARCHAR(255),
                metadata JSONB,
                tags TEXT[],
                created_at TIMESTAMP NOT NULL,
                accessed_at TIMESTAMP,
                expires_at TIMESTAMP,
                is_private BOOLEAN DEFAULT FALSE,
                shared_with_tenants UUID[]
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_memory_tenant 
            ON memory_metadata(tenant_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_memory_agent 
            ON memory_metadata(agent_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_memory_type 
            ON memory_metadata(memory_type)
            """,
            """
            CREATE TABLE IF NOT EXISTS provenance_records (
                provenance_hash VARCHAR(64) PRIMARY KEY,
                memory_node_id UUID NOT NULL,
                source_type VARCHAR(50) NOT NULL,
                source_id VARCHAR(255) NOT NULL,
                source_timestamp TIMESTAMP NOT NULL,
                created_by_agent_id UUID,
                verified_by VARCHAR(255),
                content_hash VARCHAR(64) NOT NULL,
                signature TEXT,
                created_at TIMESTAMP NOT NULL
            )
            """
        ]
        
        for query in queries:
            await self.execute_query(query)
        
        logger.info("PostgreSQL tables created successfully")


# Global database manager instance
db_manager = DatabaseManager()

# Made with Bob