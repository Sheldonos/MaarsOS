"""
Database management for vessel-observability service.
Supports both PostgreSQL and AstraDB.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import SimpleStatement
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

from .config import settings
from .models import (
    GuardrailPolicy,
    PolicyViolation,
    AnomalyDetection,
    MetricData,
    TraceData,
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        """Initialize database manager."""
        self.db_type = settings.database_type
        self.session = None
        self.pool = None
        
    async def connect(self):
        """Establish database connection."""
        try:
            if self.db_type == "astradb":
                await self._connect_astradb()
            else:
                await self._connect_postgresql()
            logger.info(f"Connected to {self.db_type} database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    async def _connect_astradb(self):
        """Connect to AstraDB."""
        if not settings.astra_db_token or not settings.astra_db_secure_bundle_path:
            raise ValueError("AstraDB credentials not configured")
        
        cloud_config = {
            'secure_connect_bundle': settings.astra_db_secure_bundle_path
        }
        auth_provider = PlainTextAuthProvider(
            'token',
            settings.astra_db_token
        )
        
        cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider)
        self.session = cluster.connect(settings.astra_db_keyspace)
        
        # Create tables if they don't exist
        await self._create_astradb_tables()
    
    async def _connect_postgresql(self):
        """Connect to PostgreSQL."""
        self.pool = SimpleConnectionPool(
            1, 20,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password
        )
        
        # Create tables if they don't exist
        await self._create_postgresql_tables()
    
    async def _create_astradb_tables(self):
        """Create AstraDB tables."""
        # Guardrail policies table
        self.session.execute("""
            CREATE TABLE IF NOT EXISTS guardrail_policies (
                policy_id UUID PRIMARY KEY,
                tenant_id TEXT,
                policy_name TEXT,
                policy_type TEXT,
                description TEXT,
                enabled BOOLEAN,
                severity TEXT,
                action TEXT,
                config TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                created_by TEXT,
                tags MAP<TEXT, TEXT>
            )
        """)
        
        # Policy violations table
        self.session.execute("""
            CREATE TABLE IF NOT EXISTS policy_violations (
                violation_id UUID PRIMARY KEY,
                policy_id UUID,
                policy_name TEXT,
                policy_type TEXT,
                tenant_id TEXT,
                task_id TEXT,
                agent_id TEXT,
                severity TEXT,
                action_taken TEXT,
                violation_details TEXT,
                timestamp TIMESTAMP,
                resolved BOOLEAN,
                resolved_at TIMESTAMP,
                resolved_by TEXT
            )
        """)
        
        # Anomaly detections table
        self.session.execute("""
            CREATE TABLE IF NOT EXISTS anomaly_detections (
                anomaly_id UUID PRIMARY KEY,
                tenant_id TEXT,
                anomaly_type TEXT,
                metric_name TEXT,
                observed_value DOUBLE,
                expected_value DOUBLE,
                deviation DOUBLE,
                z_score DOUBLE,
                confidence DOUBLE,
                timestamp TIMESTAMP,
                metadata TEXT,
                acknowledged BOOLEAN,
                acknowledged_at TIMESTAMP,
                acknowledged_by TEXT
            )
        """)
        
        # Metrics history table
        self.session.execute("""
            CREATE TABLE IF NOT EXISTS metrics_history (
                metric_id UUID PRIMARY KEY,
                metric_name TEXT,
                metric_type TEXT,
                value DOUBLE,
                timestamp TIMESTAMP,
                labels MAP<TEXT, TEXT>,
                tenant_id TEXT
            )
        """)
        
        logger.info("AstraDB tables created/verified")
    
    async def _create_postgresql_tables(self):
        """Create PostgreSQL tables."""
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                # Guardrail policies table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS guardrail_policies (
                        policy_id UUID PRIMARY KEY,
                        tenant_id VARCHAR(255) NOT NULL,
                        policy_name VARCHAR(255) NOT NULL,
                        policy_type VARCHAR(50) NOT NULL,
                        description TEXT,
                        enabled BOOLEAN DEFAULT TRUE,
                        severity VARCHAR(20) NOT NULL,
                        action VARCHAR(20) NOT NULL,
                        config JSONB,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        created_by VARCHAR(255),
                        tags JSONB
                    )
                """)
                
                # Policy violations table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS policy_violations (
                        violation_id UUID PRIMARY KEY,
                        policy_id UUID NOT NULL,
                        policy_name VARCHAR(255) NOT NULL,
                        policy_type VARCHAR(50) NOT NULL,
                        tenant_id VARCHAR(255) NOT NULL,
                        task_id VARCHAR(255),
                        agent_id VARCHAR(255),
                        severity VARCHAR(20) NOT NULL,
                        action_taken VARCHAR(20) NOT NULL,
                        violation_details JSONB,
                        timestamp TIMESTAMP DEFAULT NOW(),
                        resolved BOOLEAN DEFAULT FALSE,
                        resolved_at TIMESTAMP,
                        resolved_by VARCHAR(255)
                    )
                """)
                
                # Anomaly detections table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS anomaly_detections (
                        anomaly_id UUID PRIMARY KEY,
                        tenant_id VARCHAR(255) NOT NULL,
                        anomaly_type VARCHAR(50) NOT NULL,
                        metric_name VARCHAR(255) NOT NULL,
                        observed_value DOUBLE PRECISION,
                        expected_value DOUBLE PRECISION,
                        deviation DOUBLE PRECISION,
                        z_score DOUBLE PRECISION,
                        confidence DOUBLE PRECISION,
                        timestamp TIMESTAMP DEFAULT NOW(),
                        metadata JSONB,
                        acknowledged BOOLEAN DEFAULT FALSE,
                        acknowledged_at TIMESTAMP,
                        acknowledged_by VARCHAR(255)
                    )
                """)
                
                # Metrics history table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS metrics_history (
                        metric_id UUID PRIMARY KEY,
                        metric_name VARCHAR(255) NOT NULL,
                        metric_type VARCHAR(50) NOT NULL,
                        value DOUBLE PRECISION,
                        timestamp TIMESTAMP DEFAULT NOW(),
                        labels JSONB,
                        tenant_id VARCHAR(255)
                    )
                """)
                
                # Create indexes
                cur.execute("CREATE INDEX IF NOT EXISTS idx_policies_tenant ON guardrail_policies(tenant_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_violations_tenant ON policy_violations(tenant_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_violations_timestamp ON policy_violations(timestamp)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_tenant ON anomaly_detections(tenant_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_timestamp ON anomaly_detections(timestamp)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics_history(metric_name)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics_history(timestamp)")
                
                conn.commit()
                logger.info("PostgreSQL tables created/verified")
        finally:
            self.pool.putconn(conn)
    
    async def disconnect(self):
        """Close database connection."""
        if self.db_type == "astradb" and self.session:
            self.session.cluster.shutdown()
        elif self.pool:
            self.pool.closeall()
        logger.info("Database connection closed")
    
    # Guardrail Policy Operations
    
    async def create_policy(self, policy: GuardrailPolicy) -> str:
        """Create a new guardrail policy."""
        policy_id = str(uuid.uuid4())
        
        if self.db_type == "astradb":
            query = """
                INSERT INTO guardrail_policies 
                (policy_id, tenant_id, policy_name, policy_type, description, enabled, 
                 severity, action, config, created_at, updated_at, created_by, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.session.execute(query, (
                uuid.UUID(policy_id),
                policy.tenant_id,
                policy.policy_name,
                policy.policy_type.value,
                policy.description,
                policy.enabled,
                policy.severity.value,
                policy.action.value,
                policy.model_dump_json(),
                datetime.utcnow(),
                datetime.utcnow(),
                policy.created_by,
                policy.tags
            ))
        else:
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO guardrail_policies 
                        (policy_id, tenant_id, policy_name, policy_type, description, enabled,
                         severity, action, config, created_by, tags)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        policy_id,
                        policy.tenant_id,
                        policy.policy_name,
                        policy.policy_type.value,
                        policy.description,
                        policy.enabled,
                        policy.severity.value,
                        policy.action.value,
                        policy.model_dump_json(),
                        policy.created_by,
                        policy.model_dump_json()
                    ))
                    conn.commit()
            finally:
                self.pool.putconn(conn)
        
        return policy_id
    
    async def get_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Get a guardrail policy by ID."""
        if self.db_type == "astradb":
            query = "SELECT * FROM guardrail_policies WHERE policy_id = ?"
            result = self.session.execute(query, (uuid.UUID(policy_id),))
            row = result.one()
            return dict(row._asdict()) if row else None
        else:
            conn = self.pool.getconn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM guardrail_policies WHERE policy_id = %s", (policy_id,))
                    return cur.fetchone()
            finally:
                self.pool.putconn(conn)
    
    async def list_policies(self, tenant_id: str, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """List guardrail policies for a tenant."""
        if self.db_type == "astradb":
            query = "SELECT * FROM guardrail_policies WHERE tenant_id = ?"
            if enabled_only:
                query += " AND enabled = true ALLOW FILTERING"
            result = self.session.execute(query, (tenant_id,))
            return [dict(row._asdict()) for row in result]
        else:
            conn = self.pool.getconn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if enabled_only:
                        cur.execute(
                            "SELECT * FROM guardrail_policies WHERE tenant_id = %s AND enabled = TRUE",
                            (tenant_id,)
                        )
                    else:
                        cur.execute("SELECT * FROM guardrail_policies WHERE tenant_id = %s", (tenant_id,))
                    return cur.fetchall()
            finally:
                self.pool.putconn(conn)
    
    async def update_policy(self, policy_id: str, updates: Dict[str, Any]) -> bool:
        """Update a guardrail policy."""
        updates['updated_at'] = datetime.utcnow()
        
        if self.db_type == "astradb":
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            query = f"UPDATE guardrail_policies SET {set_clause} WHERE policy_id = ?"
            values = list(updates.values()) + [uuid.UUID(policy_id)]
            self.session.execute(query, values)
            return True
        else:
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cur:
                    set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
                    query = f"UPDATE guardrail_policies SET {set_clause} WHERE policy_id = %s"
                    values = list(updates.values()) + [policy_id]
                    cur.execute(query, values)
                    conn.commit()
                    return cur.rowcount > 0
            finally:
                self.pool.putconn(conn)
    
    async def delete_policy(self, policy_id: str) -> bool:
        """Delete a guardrail policy."""
        if self.db_type == "astradb":
            query = "DELETE FROM guardrail_policies WHERE policy_id = ?"
            self.session.execute(query, (uuid.UUID(policy_id),))
            return True
        else:
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM guardrail_policies WHERE policy_id = %s", (policy_id,))
                    conn.commit()
                    return cur.rowcount > 0
            finally:
                self.pool.putconn(conn)
    
    # Policy Violation Operations
    
    async def record_violation(self, violation: PolicyViolation) -> str:
        """Record a policy violation."""
        violation_id = str(uuid.uuid4())
        
        if self.db_type == "astradb":
            query = """
                INSERT INTO policy_violations
                (violation_id, policy_id, policy_name, policy_type, tenant_id, task_id,
                 agent_id, severity, action_taken, violation_details, timestamp, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.session.execute(query, (
                uuid.UUID(violation_id),
                uuid.UUID(violation.policy_id),
                violation.policy_name,
                violation.policy_type.value,
                violation.tenant_id,
                violation.task_id,
                violation.agent_id,
                violation.severity.value,
                violation.action_taken.value,
                str(violation.violation_details),
                violation.timestamp,
                violation.resolved
            ))
        else:
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO policy_violations
                        (violation_id, policy_id, policy_name, policy_type, tenant_id, task_id,
                         agent_id, severity, action_taken, violation_details, resolved)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        violation_id,
                        violation.policy_id,
                        violation.policy_name,
                        violation.policy_type.value,
                        violation.tenant_id,
                        violation.task_id,
                        violation.agent_id,
                        violation.severity.value,
                        violation.action_taken.value,
                        violation.model_dump_json(),
                        violation.resolved
                    ))
                    conn.commit()
            finally:
                self.pool.putconn(conn)
        
        return violation_id
    
    async def get_violations(
        self,
        tenant_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get policy violations for a tenant."""
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=7)
        if not end_time:
            end_time = datetime.utcnow()
        
        if self.db_type == "astradb":
            query = """
                SELECT * FROM policy_violations 
                WHERE tenant_id = ? AND timestamp >= ? AND timestamp <= ?
                LIMIT ?
                ALLOW FILTERING
            """
            result = self.session.execute(query, (tenant_id, start_time, end_time, limit))
            return [dict(row._asdict()) for row in result]
        else:
            conn = self.pool.getconn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM policy_violations
                        WHERE tenant_id = %s AND timestamp >= %s AND timestamp <= %s
                        ORDER BY timestamp DESC
                        LIMIT %s
                    """, (tenant_id, start_time, end_time, limit))
                    return cur.fetchall()
            finally:
                self.pool.putconn(conn)
    
    # Anomaly Detection Operations
    
    async def record_anomaly(self, anomaly: AnomalyDetection) -> str:
        """Record an anomaly detection."""
        anomaly_id = str(uuid.uuid4())
        
        if self.db_type == "astradb":
            query = """
                INSERT INTO anomaly_detections
                (anomaly_id, tenant_id, anomaly_type, metric_name, observed_value,
                 expected_value, deviation, z_score, confidence, timestamp, metadata, acknowledged)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.session.execute(query, (
                uuid.UUID(anomaly_id),
                anomaly.tenant_id,
                anomaly.anomaly_type.value,
                anomaly.metric_name,
                anomaly.observed_value,
                anomaly.expected_value,
                anomaly.deviation,
                anomaly.z_score,
                anomaly.confidence,
                anomaly.timestamp,
                str(anomaly.metadata),
                anomaly.acknowledged
            ))
        else:
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO anomaly_detections
                        (anomaly_id, tenant_id, anomaly_type, metric_name, observed_value,
                         expected_value, deviation, z_score, confidence, metadata, acknowledged)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        anomaly_id,
                        anomaly.tenant_id,
                        anomaly.anomaly_type.value,
                        anomaly.metric_name,
                        anomaly.observed_value,
                        anomaly.expected_value,
                        anomaly.deviation,
                        anomaly.z_score,
                        anomaly.confidence,
                        anomaly.model_dump_json(),
                        anomaly.acknowledged
                    ))
                    conn.commit()
            finally:
                self.pool.putconn(conn)
        
        return anomaly_id
    
    async def get_anomalies(
        self,
        tenant_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get anomaly detections for a tenant."""
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=7)
        if not end_time:
            end_time = datetime.utcnow()
        
        if self.db_type == "astradb":
            query = """
                SELECT * FROM anomaly_detections
                WHERE tenant_id = ? AND timestamp >= ? AND timestamp <= ?
                LIMIT ?
                ALLOW FILTERING
            """
            result = self.session.execute(query, (tenant_id, start_time, end_time, limit))
            return [dict(row._asdict()) for row in result]
        else:
            conn = self.pool.getconn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM anomaly_detections
                        WHERE tenant_id = %s AND timestamp >= %s AND timestamp <= %s
                        ORDER BY timestamp DESC
                        LIMIT %s
                    """, (tenant_id, start_time, end_time, limit))
                    return cur.fetchall()
            finally:
                self.pool.putconn(conn)
    
    # Metrics Operations
    
    async def store_metric(self, metric: MetricData) -> str:
        """Store a metric data point."""
        metric_id = str(uuid.uuid4())
        
        if self.db_type == "astradb":
            query = """
                INSERT INTO metrics_history
                (metric_id, metric_name, metric_type, value, timestamp, labels, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            self.session.execute(query, (
                uuid.UUID(metric_id),
                metric.metric_name,
                metric.metric_type.value,
                metric.value,
                metric.timestamp,
                metric.labels,
                metric.tenant_id
            ))
        else:
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO metrics_history
                        (metric_id, metric_name, metric_type, value, labels, tenant_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        metric_id,
                        metric.metric_name,
                        metric.metric_type.value,
                        metric.value,
                        metric.model_dump_json(),
                        metric.tenant_id
                    ))
                    conn.commit()
            finally:
                self.pool.putconn(conn)
        
        return metric_id
    
    async def get_metrics(
        self,
        metric_name: str,
        tenant_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get metric data points."""
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.utcnow()
        
        if self.db_type == "astradb":
            if tenant_id:
                query = """
                    SELECT * FROM metrics_history
                    WHERE metric_name = ? AND tenant_id = ? 
                    AND timestamp >= ? AND timestamp <= ?
                    LIMIT ?
                    ALLOW FILTERING
                """
                result = self.session.execute(query, (metric_name, tenant_id, start_time, end_time, limit))
            else:
                query = """
                    SELECT * FROM metrics_history
                    WHERE metric_name = ? AND timestamp >= ? AND timestamp <= ?
                    LIMIT ?
                    ALLOW FILTERING
                """
                result = self.session.execute(query, (metric_name, start_time, end_time, limit))
            return [dict(row._asdict()) for row in result]
        else:
            conn = self.pool.getconn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if tenant_id:
                        cur.execute("""
                            SELECT * FROM metrics_history
                            WHERE metric_name = %s AND tenant_id = %s
                            AND timestamp >= %s AND timestamp <= %s
                            ORDER BY timestamp DESC
                            LIMIT %s
                        """, (metric_name, tenant_id, start_time, end_time, limit))
                    else:
                        cur.execute("""
                            SELECT * FROM metrics_history
                            WHERE metric_name = %s AND timestamp >= %s AND timestamp <= %s
                            ORDER BY timestamp DESC
                            LIMIT %s
                        """, (metric_name, start_time, end_time, limit))
                    return cur.fetchall()
            finally:
                self.pool.putconn(conn)


# Global database manager instance
db_manager = DatabaseManager()

# Made with Bob
