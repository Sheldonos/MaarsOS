"""
Pydantic models for vessel-economics service.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


class TransactionType(str, Enum):
    """Types of escrow transactions."""
    ALLOCATE = "allocate"
    LOCK = "lock"
    RELEASE = "release"
    REFUND = "refund"
    TRANSFER = "transfer"


class TransactionStatus(str, Enum):
    """Status of escrow transactions."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CostCategory(str, Enum):
    """Categories of costs."""
    LLM_API = "llm_api"
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    OTHER = "other"


class BudgetStatus(str, Enum):
    """Budget status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    EXHAUSTED = "exhausted"


class ComplianceReportType(str, Enum):
    """Types of compliance reports."""
    AUDIT_TRAIL = "audit_trail"
    COST_SUMMARY = "cost_summary"
    BUDGET_ANALYSIS = "budget_analysis"
    TRANSACTION_RECONCILIATION = "transaction_reconciliation"
    REGULATORY_EXPORT = "regulatory_export"


# Request/Response Models

class EscrowAllocateRequest(BaseModel):
    """Request to allocate budget to escrow."""
    tenant_id: str = Field(..., description="Tenant identifier")
    amount: Decimal = Field(..., description="Amount to allocate in USD", gt=0)
    description: Optional[str] = Field(None, description="Allocation description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class EscrowReleaseRequest(BaseModel):
    """Request to release escrow funds."""
    tenant_id: str = Field(..., description="Tenant identifier")
    transaction_id: str = Field(..., description="Transaction to release")
    amount: Optional[Decimal] = Field(None, description="Amount to release (None for full)")
    reason: Optional[str] = Field(None, description="Release reason")


class EscrowAccount(BaseModel):
    """Escrow account information."""
    tenant_id: str
    balance: Decimal = Field(default=Decimal("0.00"))
    locked_balance: Decimal = Field(default=Decimal("0.00"))
    available_balance: Decimal = Field(default=Decimal("0.00"))
    total_allocated: Decimal = Field(default=Decimal("0.00"))
    total_spent: Decimal = Field(default=Decimal("0.00"))
    created_at: datetime
    updated_at: datetime
    
    @validator('available_balance', always=True)
    def calculate_available(cls, v, values):
        """Calculate available balance."""
        if 'balance' in values and 'locked_balance' in values:
            return values['balance'] - values['locked_balance']
        return v


class EscrowTransaction(BaseModel):
    """Escrow transaction record."""
    transaction_id: str
    tenant_id: str
    transaction_type: TransactionType
    amount: Decimal
    status: TransactionStatus
    description: Optional[str] = None
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    completed_at: Optional[datetime] = None


class CostTrackRequest(BaseModel):
    """Request to track a cost."""
    tenant_id: str = Field(..., description="Tenant identifier")
    task_id: str = Field(..., description="Task identifier")
    agent_id: Optional[str] = Field(None, description="Agent identifier")
    category: CostCategory = Field(..., description="Cost category")
    provider: Optional[str] = Field(None, description="Provider (e.g., openai, anthropic)")
    model: Optional[str] = Field(None, description="Model name (e.g., gpt-4)")
    input_tokens: Optional[int] = Field(None, description="Input tokens used")
    output_tokens: Optional[int] = Field(None, description="Output tokens used")
    cost: Decimal = Field(..., description="Cost in USD", ge=0)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CostRecord(BaseModel):
    """Cost record."""
    cost_id: str
    tenant_id: str
    task_id: str
    agent_id: Optional[str] = None
    category: CostCategory
    provider: Optional[str] = None
    model: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost: Decimal
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class CostSummary(BaseModel):
    """Cost summary aggregation."""
    tenant_id: Optional[str] = None
    agent_id: Optional[str] = None
    total_cost: Decimal = Field(default=Decimal("0.00"))
    total_tasks: int = 0
    cost_by_category: Dict[str, Decimal] = Field(default_factory=dict)
    cost_by_provider: Dict[str, Decimal] = Field(default_factory=dict)
    cost_by_model: Dict[str, Decimal] = Field(default_factory=dict)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class BudgetCheckRequest(BaseModel):
    """Request to check budget availability."""
    tenant_id: str = Field(..., description="Tenant identifier")
    estimated_cost: Decimal = Field(..., description="Estimated cost in USD", ge=0)
    task_id: Optional[str] = Field(None, description="Task identifier")


class BudgetCheckResponse(BaseModel):
    """Response for budget check."""
    tenant_id: str
    available: bool
    current_balance: Decimal
    estimated_cost: Decimal
    remaining_after: Decimal
    budget_status: BudgetStatus
    message: Optional[str] = None


class BudgetEnforceRequest(BaseModel):
    """Request to enforce budget limits."""
    tenant_id: str = Field(..., description="Tenant identifier")
    task_id: str = Field(..., description="Task identifier")
    estimated_cost: Decimal = Field(..., description="Estimated cost in USD", ge=0)
    force: bool = Field(default=False, description="Force execution even if budget exceeded")


class BudgetLimit(BaseModel):
    """Budget limit configuration."""
    tenant_id: str
    total_budget: Decimal
    used_budget: Decimal = Field(default=Decimal("0.00"))
    remaining_budget: Decimal
    warning_threshold: Decimal
    critical_threshold: Decimal
    hard_limit_enabled: bool = True
    soft_limit_enabled: bool = True
    status: BudgetStatus
    last_alert_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    @validator('remaining_budget', always=True)
    def calculate_remaining(cls, v, values):
        """Calculate remaining budget."""
        if 'total_budget' in values and 'used_budget' in values:
            return values['total_budget'] - values['used_budget']
        return v


class ComplianceReportRequest(BaseModel):
    """Request to generate compliance report."""
    tenant_id: Optional[str] = Field(None, description="Tenant identifier (None for all)")
    report_type: ComplianceReportType = Field(..., description="Type of report")
    start_date: datetime = Field(..., description="Report start date")
    end_date: datetime = Field(..., description="Report end date")
    format: str = Field(default="json", description="Report format (json, csv, pdf)")
    include_metadata: bool = Field(default=True, description="Include metadata")


class ComplianceReport(BaseModel):
    """Compliance report."""
    report_id: str
    report_type: ComplianceReportType
    tenant_id: Optional[str] = None
    start_date: datetime
    end_date: datetime
    generated_at: datetime
    total_transactions: int
    total_cost: Decimal
    data: Dict[str, Any]
    format: str
    file_path: Optional[str] = None


class AuditTrailEntry(BaseModel):
    """Audit trail entry."""
    entry_id: str
    tenant_id: str
    event_type: str
    event_data: Dict[str, Any]
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditTrailQuery(BaseModel):
    """Query parameters for audit trail."""
    tenant_id: Optional[str] = None
    event_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)


class Invoice(BaseModel):
    """Invoice for billing period."""
    invoice_id: str
    tenant_id: str
    billing_period_start: datetime
    billing_period_end: datetime
    total_cost: Decimal
    tax_amount: Decimal = Field(default=Decimal("0.00"))
    total_amount: Decimal
    currency: str = "USD"
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "draft"  # draft, issued, paid, cancelled
    issued_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('total_amount', always=True)
    def calculate_total(cls, v, values):
        """Calculate total amount including tax."""
        if 'total_cost' in values and 'tax_amount' in values:
            return values['total_cost'] + values['tax_amount']
        return v


class BillingPeriod(BaseModel):
    """Billing period information."""
    tenant_id: str
    period_start: datetime
    period_end: datetime
    total_cost: Decimal
    total_tasks: int
    invoice_id: Optional[str] = None
    invoice_generated: bool = False


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    timestamp: datetime
    database: str
    kafka: str


class MetricsResponse(BaseModel):
    """Metrics response."""
    total_escrow_accounts: int
    total_escrow_balance: Decimal
    total_transactions: int
    total_costs_tracked: Decimal
    active_budgets: int
    budgets_in_warning: int
    budgets_exhausted: int

# Made with Bob
