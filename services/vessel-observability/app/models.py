"""
Pydantic models for vessel-observability service.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator


class PolicyType(str, Enum):
    """Types of guardrail policies."""
    CONTENT = "content"
    RATE_LIMIT = "rate_limit"
    COST_THRESHOLD = "cost_threshold"
    RESOURCE_LIMIT = "resource_limit"
    EXECUTION_TIME = "execution_time"
    COMPLIANCE = "compliance"


class PolicySeverity(str, Enum):
    """Severity levels for policy violations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyAction(str, Enum):
    """Actions to take on policy violation."""
    LOG = "log"
    WARN = "warn"
    BLOCK = "block"
    ESCALATE = "escalate"


class AnomalyType(str, Enum):
    """Types of anomalies."""
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    COST = "cost"
    RESOURCE_USAGE = "resource_usage"
    PATTERN = "pattern"


class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


# Guardrail Policy Models

class ContentPolicyConfig(BaseModel):
    """Configuration for content filtering policy."""
    check_profanity: bool = True
    check_pii: bool = True
    check_sensitive_data: bool = True
    blocked_patterns: List[str] = Field(default_factory=list)
    allowed_patterns: List[str] = Field(default_factory=list)


class RateLimitPolicyConfig(BaseModel):
    """Configuration for rate limiting policy."""
    max_requests_per_minute: int = 100
    max_requests_per_hour: int = 1000
    max_requests_per_day: int = 10000
    burst_size: int = 10


class CostThresholdPolicyConfig(BaseModel):
    """Configuration for cost threshold policy."""
    max_cost_per_task: float = 10.0
    max_cost_per_tenant_daily: float = 1000.0
    max_cost_per_tenant_monthly: float = 30000.0
    alert_threshold_percent: float = 80.0


class ResourceLimitPolicyConfig(BaseModel):
    """Configuration for resource limit policy."""
    max_memory_mb: int = 2048
    max_cpu_percent: int = 80
    max_disk_mb: int = 10240
    max_network_mbps: int = 100


class ExecutionTimePolicyConfig(BaseModel):
    """Configuration for execution time policy."""
    max_execution_time_seconds: int = 300
    warning_threshold_seconds: int = 240
    timeout_action: PolicyAction = PolicyAction.BLOCK


class GuardrailPolicy(BaseModel):
    """Guardrail policy definition."""
    policy_id: Optional[str] = None
    tenant_id: str
    policy_name: str
    policy_type: PolicyType
    description: Optional[str] = None
    enabled: bool = True
    severity: PolicySeverity = PolicySeverity.MEDIUM
    action: PolicyAction = PolicyAction.WARN
    
    # Type-specific configuration
    content_config: Optional[ContentPolicyConfig] = None
    rate_limit_config: Optional[RateLimitPolicyConfig] = None
    cost_threshold_config: Optional[CostThresholdPolicyConfig] = None
    resource_limit_config: Optional[ResourceLimitPolicyConfig] = None
    execution_time_config: Optional[ExecutionTimePolicyConfig] = None
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)
    
    @validator('policy_type')
    def validate_config(cls, v, values):
        """Ensure appropriate config is provided for policy type."""
        # This is a simplified validation - in production, ensure matching config exists
        return v


class GuardrailEvaluationRequest(BaseModel):
    """Request to evaluate guardrail policies."""
    tenant_id: str
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Context for evaluation
    request_count: Optional[int] = None
    cost_estimate: Optional[float] = None
    resource_usage: Optional[Dict[str, float]] = None
    execution_time: Optional[float] = None


class PolicyViolation(BaseModel):
    """Policy violation record."""
    violation_id: Optional[str] = None
    policy_id: str
    policy_name: str
    policy_type: PolicyType
    tenant_id: str
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    
    severity: PolicySeverity
    action_taken: PolicyAction
    violation_details: Dict[str, Any]
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None


class GuardrailEvaluationResponse(BaseModel):
    """Response from guardrail evaluation."""
    allowed: bool
    violations: List[PolicyViolation] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    evaluation_time_ms: float
    policies_evaluated: int


# Anomaly Detection Models

class AnomalyDetectionRequest(BaseModel):
    """Request to detect anomalies."""
    tenant_id: str
    metric_name: str
    metric_value: float
    metric_type: MetricType = MetricType.GAUGE
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnomalyDetection(BaseModel):
    """Anomaly detection record."""
    anomaly_id: Optional[str] = None
    tenant_id: str
    anomaly_type: AnomalyType
    metric_name: str
    
    # Anomaly details
    observed_value: float
    expected_value: float
    deviation: float
    z_score: float
    confidence: float
    
    # Context
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Resolution
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


class AnomalyDetectionResponse(BaseModel):
    """Response from anomaly detection."""
    is_anomaly: bool
    anomaly: Optional[AnomalyDetection] = None
    baseline_stats: Dict[str, float]
    detection_time_ms: float


# Metrics Models

class MetricData(BaseModel):
    """Metric data point."""
    metric_name: str
    metric_type: MetricType
    value: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = Field(default_factory=dict)
    tenant_id: Optional[str] = None


class MetricQuery(BaseModel):
    """Query for metrics."""
    metric_name: str
    tenant_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    labels: Dict[str, str] = Field(default_factory=dict)
    aggregation: Optional[str] = "avg"  # avg, sum, min, max, count


class MetricResponse(BaseModel):
    """Response containing metrics."""
    metrics: List[MetricData]
    total_count: int
    aggregated_value: Optional[float] = None


# Trace Models

class SpanData(BaseModel):
    """Trace span data."""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str] = None
    operation_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    status: str = "ok"  # ok, error
    tags: Dict[str, str] = Field(default_factory=dict)
    logs: List[Dict[str, Any]] = Field(default_factory=list)


class TraceData(BaseModel):
    """Trace data."""
    trace_id: str
    tenant_id: Optional[str] = None
    service_name: str
    spans: List[SpanData]
    start_time: datetime
    end_time: datetime
    duration_ms: float
    status: str = "ok"


class TraceQuery(BaseModel):
    """Query for traces."""
    trace_id: Optional[str] = None
    tenant_id: Optional[str] = None
    service_name: Optional[str] = None
    operation_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    min_duration_ms: Optional[float] = None
    max_duration_ms: Optional[float] = None
    status: Optional[str] = None
    limit: int = 100


# Health and Status Models

class HealthStatus(BaseModel):
    """Health check status."""
    status: str = "healthy"
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    checks: Dict[str, bool] = Field(default_factory=dict)
    details: Dict[str, Any] = Field(default_factory=dict)


class ServiceMetrics(BaseModel):
    """Service-level metrics."""
    total_policies: int
    active_policies: int
    total_violations: int
    violations_last_hour: int
    total_anomalies: int
    anomalies_last_hour: int
    avg_evaluation_time_ms: float
    avg_detection_time_ms: float

# Made with Bob
