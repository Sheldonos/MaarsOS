"""
Database management for vessel-economics service.
Supports both PostgreSQL and AstraDB.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import SimpleStatement

from .config import settings
from .models import (
    EscrowAccount, EscrowTransaction, CostRecord, BudgetLimit,
    AuditTrailEntry, Invoice, TransactionType, TransactionStatus,
    CostCategory, BudgetStatus
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        """Initialize database manager."""
        self.db_type = settings.database_type
        self.conn = None
        self.session = None
        
    async def connect(self):
        """Connect to database."""
        if self.db_type == "postgresql":
            await self._connect_postgres()
        elif self.db_type == "astradb":
            await self._connect_astradb()
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
            
        logger.info(f"Connected to {self.db_type} database")
        
    async def _connect_postgres(self):
        """Connect to PostgreSQL."""
        try:
            self.conn = psycopg2.connect(
                host=settings.postgres_host,
                port=settings.postgres_port,
                database=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password
            )
            await self._init_postgres_schema()
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
            
    async def _connect_astradb(self):
        """Connect to AstraDB."""
        try:
            cloud_config = {
                'secure_connect_bundle': settings.astra_secure_bundle_path
            }
            auth_provider = PlainTextAuthProvider(
                username='token',
                password=settings.astra_db_token
            )
            cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider)
            self.session = cluster.connect(settings.astra_db_keyspace)
            await self._init_astradb_schema()
        except Exception as e:
            logger.error(f"Failed to connect to AstraDB: {e}")
            raise
            
    async def _init_postgres_schema(self):
        """Initialize PostgreSQL schema."""
        with self.conn.cursor() as cur:
            # Escrow accounts table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS escrow_accounts (
                    tenant_id VARCHAR(255) PRIMARY KEY,
                    balance DECIMAL(20, 8) NOT NULL DEFAULT 0,
                    locked_balance DECIMAL(20, 8) NOT NULL DEFAULT 0,
                    total_allocated DECIMAL(20, 8) NOT NULL DEFAULT 0,
                    total_spent DECIMAL(20, 8) NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """)
            
            # Escrow transactions table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS escrow_transactions (
                    transaction_id VARCHAR(255) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    transaction_type VARCHAR(50) NOT NULL,
                    amount DECIMAL(20, 8) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    description TEXT,
                    task_id VARCHAR(255),
                    agent_id VARCHAR(255),
                    metadata JSONB,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    completed_at TIMESTAMP,
                    FOREIGN KEY (tenant_id) REFERENCES escrow_accounts(tenant_id)
                )
            """)
            
            # Cost records table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cost_records (
                    cost_id VARCHAR(255) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    task_id VARCHAR(255) NOT NULL,
                    agent_id VARCHAR(255),
                    category VARCHAR(50) NOT NULL,
                    provider VARCHAR(100),
                    model VARCHAR(100),
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cost DECIMAL(20, 8) NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """)
            
            # Budget limits table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS budget_limits (
                    tenant_id VARCHAR(255) PRIMARY KEY,
                    total_budget DECIMAL(20, 8) NOT NULL,
                    used_budget DECIMAL(20, 8) NOT NULL DEFAULT 0,
                    warning_threshold DECIMAL(5, 4) NOT NULL,
                    critical_threshold DECIMAL(5, 4) NOT NULL,
                    hard_limit_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    soft_limit_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    status VARCHAR(50) NOT NULL DEFAULT 'healthy',
                    last_alert_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """)
            
            # Audit trail table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS audit_trail (
                    entry_id VARCHAR(255) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    event_type VARCHAR(100) NOT NULL,
                    event_data JSONB NOT NULL,
                    user_id VARCHAR(255),
                    ip_address VARCHAR(50),
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                    metadata JSONB
                )
            """)
            
            # Invoices table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    invoice_id VARCHAR(255) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    billing_period_start TIMESTAMP NOT NULL,
                    billing_period_end TIMESTAMP NOT NULL,
                    total_cost DECIMAL(20, 8) NOT NULL,
                    tax_amount DECIMAL(20, 8) NOT NULL DEFAULT 0,
                    total_amount DECIMAL(20, 8) NOT NULL,
                    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
                    line_items JSONB,
                    status VARCHAR(50) NOT NULL DEFAULT 'draft',
                    issued_at TIMESTAMP,
                    due_date TIMESTAMP,
                    paid_at TIMESTAMP,
                    metadata JSONB,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """)
            
            # Create indexes
            cur.execute("CREATE INDEX IF NOT EXISTS idx_escrow_transactions_tenant ON escrow_transactions(tenant_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_escrow_transactions_task ON escrow_transactions(task_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_cost_records_tenant ON cost_records(tenant_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_cost_records_task ON cost_records(task_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_cost_records_agent ON cost_records(agent_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_cost_records_created ON cost_records(created_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_trail_tenant ON audit_trail(tenant_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_trail_event ON audit_trail(event_type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_trail_timestamp ON audit_trail(timestamp)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_invoices_tenant ON invoices(tenant_id)")
            
            self.conn.commit()
            
    async def _init_astradb_schema(self):
        """Initialize AstraDB schema."""
        # Create tables using CQL
        tables = [
            """
            CREATE TABLE IF NOT EXISTS escrow_accounts (
                tenant_id text PRIMARY KEY,
                balance decimal,
                locked_balance decimal,
                total_allocated decimal,
                total_spent decimal,
                created_at timestamp,
                updated_at timestamp
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS escrow_transactions (
                transaction_id text PRIMARY KEY,
                tenant_id text,
                transaction_type text,
                amount decimal,
                status text,
                description text,
                task_id text,
                agent_id text,
                metadata map<text, text>,
                created_at timestamp,
                completed_at timestamp
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS cost_records (
                cost_id text PRIMARY KEY,
                tenant_id text,
                task_id text,
                agent_id text,
                category text,
                provider text,
                model text,
                input_tokens int,
                output_tokens int,
                cost decimal,
                metadata map<text, text>,
                created_at timestamp
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS budget_limits (
                tenant_id text PRIMARY KEY,
                total_budget decimal,
                used_budget decimal,
                warning_threshold decimal,
                critical_threshold decimal,
                hard_limit_enabled boolean,
                soft_limit_enabled boolean,
                status text,
                last_alert_at timestamp,
                created_at timestamp,
                updated_at timestamp
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS audit_trail (
                entry_id text PRIMARY KEY,
                tenant_id text,
                event_type text,
                event_data map<text, text>,
                user_id text,
                ip_address text,
                timestamp timestamp,
                metadata map<text, text>
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_id text PRIMARY KEY,
                tenant_id text,
                billing_period_start timestamp,
                billing_period_end timestamp,
                total_cost decimal,
                tax_amount decimal,
                total_amount decimal,
                currency text,
                line_items list<text>,
                status text,
                issued_at timestamp,
                due_date timestamp,
                paid_at timestamp,
                metadata map<text, text>,
                created_at timestamp
            )
            """
        ]
        
        for table_cql in tables:
            self.session.execute(table_cql)
            
    async def disconnect(self):
        """Disconnect from database."""
        if self.conn:
            self.conn.close()
        if self.session:
            self.session.shutdown()
            
    # Escrow Account Operations
    
    async def create_escrow_account(self, tenant_id: str) -> EscrowAccount:
        """Create a new escrow account."""
        now = datetime.utcnow()
        
        if self.db_type == "postgresql":
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO escrow_accounts (tenant_id, created_at, updated_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (tenant_id) DO NOTHING
                    RETURNING *
                """, (tenant_id, now, now))
                result = cur.fetchone()
                self.conn.commit()
                
                if result:
                    return EscrowAccount(
                        tenant_id=result['tenant_id'],
                        balance=Decimal(str(result['balance'])),
                        locked_balance=Decimal(str(result['locked_balance'])),
                        available_balance=Decimal(str(result['balance'])) - Decimal(str(result['locked_balance'])),
                        total_allocated=Decimal(str(result['total_allocated'])),
                        total_spent=Decimal(str(result['total_spent'])),
                        created_at=result['created_at'],
                        updated_at=result['updated_at']
                    )
                    
        return await self.get_escrow_account(tenant_id)
        
    async def get_escrow_account(self, tenant_id: str) -> Optional[EscrowAccount]:
        """Get escrow account by tenant ID."""
        if self.db_type == "postgresql":
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM escrow_accounts WHERE tenant_id = %s", (tenant_id,))
                result = cur.fetchone()
                
                if result:
                    return EscrowAccount(
                        tenant_id=result['tenant_id'],
                        balance=Decimal(str(result['balance'])),
                        locked_balance=Decimal(str(result['locked_balance'])),
                        available_balance=Decimal(str(result['balance'])) - Decimal(str(result['locked_balance'])),
                        total_allocated=Decimal(str(result['total_allocated'])),
                        total_spent=Decimal(str(result['total_spent'])),
                        created_at=result['created_at'],
                        updated_at=result['updated_at']
                    )
                    
        return None
        
    async def update_escrow_balance(self, tenant_id: str, amount: Decimal, operation: str = "add"):
        """Update escrow account balance."""
        if self.db_type == "postgresql":
            with self.conn.cursor() as cur:
                if operation == "add":
                    cur.execute("""
                        UPDATE escrow_accounts 
                        SET balance = balance + %s,
                            total_allocated = total_allocated + %s,
                            updated_at = NOW()
                        WHERE tenant_id = %s
                    """, (amount, amount, tenant_id))
                elif operation == "subtract":
                    cur.execute("""
                        UPDATE escrow_accounts 
                        SET balance = balance - %s,
                            total_spent = total_spent + %s,
                            updated_at = NOW()
                        WHERE tenant_id = %s
                    """, (amount, amount, tenant_id))
                elif operation == "lock":
                    cur.execute("""
                        UPDATE escrow_accounts 
                        SET locked_balance = locked_balance + %s,
                            updated_at = NOW()
                        WHERE tenant_id = %s
                    """, (amount, tenant_id))
                elif operation == "unlock":
                    cur.execute("""
                        UPDATE escrow_accounts 
                        SET locked_balance = locked_balance - %s,
                            updated_at = NOW()
                        WHERE tenant_id = %s
                    """, (amount, tenant_id))
                    
                self.conn.commit()
                
    # Transaction Operations
    
    async def create_transaction(self, transaction: EscrowTransaction) -> EscrowTransaction:
        """Create a new escrow transaction."""
        if self.db_type == "postgresql":
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO escrow_transactions 
                    (transaction_id, tenant_id, transaction_type, amount, status, 
                     description, task_id, agent_id, metadata, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    transaction.transaction_id,
                    transaction.tenant_id,
                    transaction.transaction_type.value,
                    transaction.amount,
                    transaction.status.value,
                    transaction.description,
                    transaction.task_id,
                    transaction.agent_id,
                    Json(transaction.metadata),
                    transaction.created_at
                ))
                self.conn.commit()
                
        return transaction
        
    async def get_transactions(self, tenant_id: str, limit: int = 100) -> List[EscrowTransaction]:
        """Get transactions for a tenant."""
        transactions = []
        
        if self.db_type == "postgresql":
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM escrow_transactions 
                    WHERE tenant_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (tenant_id, limit))
                
                for row in cur.fetchall():
                    transactions.append(EscrowTransaction(
                        transaction_id=row['transaction_id'],
                        tenant_id=row['tenant_id'],
                        transaction_type=TransactionType(row['transaction_type']),
                        amount=Decimal(str(row['amount'])),
                        status=TransactionStatus(row['status']),
                        description=row['description'],
                        task_id=row['task_id'],
                        agent_id=row['agent_id'],
                        metadata=row['metadata'] or {},
                        created_at=row['created_at'],
                        completed_at=row['completed_at']
                    ))
                    
        return transactions
        
    # Cost Record Operations
    
    async def create_cost_record(self, cost: CostRecord) -> CostRecord:
        """Create a new cost record."""
        if self.db_type == "postgresql":
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO cost_records 
                    (cost_id, tenant_id, task_id, agent_id, category, provider, 
                     model, input_tokens, output_tokens, cost, metadata, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    cost.cost_id,
                    cost.tenant_id,
                    cost.task_id,
                    cost.agent_id,
                    cost.category.value,
                    cost.provider,
                    cost.model,
                    cost.input_tokens,
                    cost.output_tokens,
                    cost.cost,
                    Json(cost.metadata),
                    cost.created_at
                ))
                self.conn.commit()
                
        return cost
        
    async def get_costs_by_tenant(
        self, 
        tenant_id: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CostRecord]:
        """Get cost records for a tenant."""
        costs = []
        
        if self.db_type == "postgresql":
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = "SELECT * FROM cost_records WHERE tenant_id = %s"
                params = [tenant_id]
                
                if start_date:
                    query += " AND created_at >= %s"
                    params.append(start_date)
                if end_date:
                    query += " AND created_at <= %s"
                    params.append(end_date)
                    
                query += " ORDER BY created_at DESC"
                
                cur.execute(query, params)
                
                for row in cur.fetchall():
                    costs.append(CostRecord(
                        cost_id=row['cost_id'],
                        tenant_id=row['tenant_id'],
                        task_id=row['task_id'],
                        agent_id=row['agent_id'],
                        category=CostCategory(row['category']),
                        provider=row['provider'],
                        model=row['model'],
                        input_tokens=row['input_tokens'],
                        output_tokens=row['output_tokens'],
                        cost=Decimal(str(row['cost'])),
                        metadata=row['metadata'] or {},
                        created_at=row['created_at']
                    ))
                    
        return costs
        
    # Budget Operations
    
    async def create_budget_limit(self, budget: BudgetLimit) -> BudgetLimit:
        """Create or update budget limit."""
        if self.db_type == "postgresql":
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO budget_limits 
                    (tenant_id, total_budget, used_budget, warning_threshold, 
                     critical_threshold, hard_limit_enabled, soft_limit_enabled, 
                     status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tenant_id) DO UPDATE SET
                        total_budget = EXCLUDED.total_budget,
                        warning_threshold = EXCLUDED.warning_threshold,
                        critical_threshold = EXCLUDED.critical_threshold,
                        hard_limit_enabled = EXCLUDED.hard_limit_enabled,
                        soft_limit_enabled = EXCLUDED.soft_limit_enabled,
                        updated_at = NOW()
                """, (
                    budget.tenant_id,
                    budget.total_budget,
                    budget.used_budget,
                    budget.warning_threshold,
                    budget.critical_threshold,
                    budget.hard_limit_enabled,
                    budget.soft_limit_enabled,
                    budget.status.value,
                    budget.created_at,
                    budget.updated_at
                ))
                self.conn.commit()
                
        return budget
        
    async def get_budget_limit(self, tenant_id: str) -> Optional[BudgetLimit]:
        """Get budget limit for a tenant."""
        if self.db_type == "postgresql":
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM budget_limits WHERE tenant_id = %s", (tenant_id,))
                result = cur.fetchone()
                
                if result:
                    return BudgetLimit(
                        tenant_id=result['tenant_id'],
                        total_budget=Decimal(str(result['total_budget'])),
                        used_budget=Decimal(str(result['used_budget'])),
                        remaining_budget=Decimal(str(result['total_budget'])) - Decimal(str(result['used_budget'])),
                        warning_threshold=Decimal(str(result['warning_threshold'])),
                        critical_threshold=Decimal(str(result['critical_threshold'])),
                        hard_limit_enabled=result['hard_limit_enabled'],
                        soft_limit_enabled=result['soft_limit_enabled'],
                        status=BudgetStatus(result['status']),
                        last_alert_at=result['last_alert_at'],
                        created_at=result['created_at'],
                        updated_at=result['updated_at']
                    )
                    
        return None
        
    async def update_budget_usage(self, tenant_id: str, amount: Decimal):
        """Update budget usage."""
        if self.db_type == "postgresql":
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE budget_limits 
                    SET used_budget = used_budget + %s,
                        updated_at = NOW()
                    WHERE tenant_id = %s
                """, (amount, tenant_id))
                self.conn.commit()
                
    # Audit Trail Operations
    
    async def create_audit_entry(self, entry: AuditTrailEntry) -> AuditTrailEntry:
        """Create audit trail entry."""
        if self.db_type == "postgresql":
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO audit_trail 
                    (entry_id, tenant_id, event_type, event_data, user_id, 
                     ip_address, timestamp, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    entry.entry_id,
                    entry.tenant_id,
                    entry.event_type,
                    Json(entry.event_data),
                    entry.user_id,
                    entry.ip_address,
                    entry.timestamp,
                    Json(entry.metadata)
                ))
                self.conn.commit()
                
        return entry
        
    async def get_audit_trail(
        self,
        tenant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditTrailEntry]:
        """Get audit trail entries."""
        entries = []
        
        if self.db_type == "postgresql":
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = "SELECT * FROM audit_trail WHERE 1=1"
                params = []
                
                if tenant_id:
                    query += " AND tenant_id = %s"
                    params.append(tenant_id)
                if event_type:
                    query += " AND event_type = %s"
                    params.append(event_type)
                if start_date:
                    query += " AND timestamp >= %s"
                    params.append(start_date)
                if end_date:
                    query += " AND timestamp <= %s"
                    params.append(end_date)
                    
                query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cur.execute(query, params)
                
                for row in cur.fetchall():
                    entries.append(AuditTrailEntry(
                        entry_id=row['entry_id'],
                        tenant_id=row['tenant_id'],
                        event_type=row['event_type'],
                        event_data=row['event_data'],
                        user_id=row['user_id'],
                        ip_address=row['ip_address'],
                        timestamp=row['timestamp'],
                        metadata=row['metadata'] or {}
                    ))
                    
        return entries
        
    # Invoice Operations
    
    async def create_invoice(self, invoice: Invoice) -> Invoice:
        """Create a new invoice."""
        if self.db_type == "postgresql":
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO invoices 
                    (invoice_id, tenant_id, billing_period_start, billing_period_end,
                     total_cost, tax_amount, total_amount, currency, line_items,
                     status, issued_at, due_date, paid_at, metadata, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    invoice.invoice_id,
                    invoice.tenant_id,
                    invoice.billing_period_start,
                    invoice.billing_period_end,
                    invoice.total_cost,
                    invoice.tax_amount,
                    invoice.total_amount,
                    invoice.currency,
                    Json(invoice.line_items),
                    invoice.status,
                    invoice.issued_at,
                    invoice.due_date,
                    invoice.paid_at,
                    Json(invoice.metadata)
                ))
                self.conn.commit()
                
        return invoice
        
    async def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID."""
        if self.db_type == "postgresql":
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM invoices WHERE invoice_id = %s", (invoice_id,))
                result = cur.fetchone()
                
                if result:
                    return Invoice(
                        invoice_id=result['invoice_id'],
                        tenant_id=result['tenant_id'],
                        billing_period_start=result['billing_period_start'],
                        billing_period_end=result['billing_period_end'],
                        total_cost=Decimal(str(result['total_cost'])),
                        tax_amount=Decimal(str(result['tax_amount'])),
                        total_amount=Decimal(str(result['total_amount'])),
                        currency=result['currency'],
                        line_items=result['line_items'] or [],
                        status=result['status'],
                        issued_at=result['issued_at'],
                        due_date=result['due_date'],
                        paid_at=result['paid_at'],
                        metadata=result['metadata'] or {}
                    )
                    
        return None


# Global database manager instance
db_manager = DatabaseManager()

# Made with Bob
