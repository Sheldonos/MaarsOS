"""
Data models for vessel-simulation service
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict


class SimulationStatus(str, Enum):
    """Simulation run status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScenarioType(str, Enum):
    """Type of simulation scenario"""
    MONTE_CARLO = "monte_carlo"
    DETERMINISTIC = "deterministic"
    AGENT_BASED = "agent_based"
    WHAT_IF = "what_if"


class OutcomeType(str, Enum):
    """Type of simulation outcome"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class SimulationMetric(BaseModel):
    """Individual simulation metric"""
    model_config = ConfigDict(from_attributes=True)
    
    metric_id: UUID = Field(default_factory=uuid4)
    simulation_id: UUID
    metric_name: str
    metric_value: float
    metric_unit: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScenarioParameter(BaseModel):
    """Parameter for simulation scenario"""
    model_config = ConfigDict(from_attributes=True)
    
    name: str
    value: Any
    value_type: str  # "string", "number", "boolean", "object"
    description: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None


class SimulationOutcome(BaseModel):
    """Individual simulation outcome"""
    model_config = ConfigDict(from_attributes=True)
    
    outcome_id: UUID = Field(default_factory=uuid4)
    simulation_id: UUID
    iteration: int
    outcome_type: OutcomeType
    confidence_score: float = Field(ge=0.0, le=1.0)
    predicted_cost: Optional[float] = None
    predicted_duration: Optional[int] = None  # seconds
    predicted_success_rate: Optional[float] = None
    risk_factors: List[str] = Field(default_factory=list)
    metrics: Dict[str, float] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SimulationRun(BaseModel):
    """Simulation run record"""
    model_config = ConfigDict(from_attributes=True)
    
    simulation_id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    goal_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    
    # Scenario Configuration
    scenario_type: ScenarioType
    scenario_name: str
    scenario_description: Optional[str] = None
    parameters: List[ScenarioParameter] = Field(default_factory=list)
    
    # Execution Configuration
    iterations: int = 100
    time_horizon: int = 86400  # 24 hours
    max_steps: int = 1000
    
    # Status
    status: SimulationStatus = SimulationStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results
    outcomes: List[SimulationOutcome] = Field(default_factory=list)
    aggregate_confidence: Optional[float] = None
    recommendation: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SimulationRequest(BaseModel):
    """Request to create a simulation"""
    tenant_id: UUID
    goal_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    scenario_type: ScenarioType
    scenario_name: str
    scenario_description: Optional[str] = None
    parameters: List[ScenarioParameter] = Field(default_factory=list)
    iterations: int = Field(default=100, ge=1, le=10000)
    time_horizon: int = Field(default=86400, ge=60, le=604800)  # 1 min to 1 week
    max_steps: int = Field(default=1000, ge=1, le=100000)


class SimulationResponse(BaseModel):
    """Response from simulation creation"""
    simulation_id: UUID
    status: SimulationStatus
    message: str
    estimated_completion: Optional[datetime] = None


class SimulationResult(BaseModel):
    """Complete simulation results"""
    simulation_id: UUID
    tenant_id: UUID
    scenario_name: str
    status: SimulationStatus
    
    # Aggregate Results
    total_iterations: int
    successful_outcomes: int
    failed_outcomes: int
    partial_outcomes: int
    
    # Confidence Metrics
    aggregate_confidence: float
    confidence_std_dev: float
    min_confidence: float
    max_confidence: float
    
    # Predictions
    predicted_success_rate: float
    predicted_cost_mean: Optional[float] = None
    predicted_cost_std_dev: Optional[float] = None
    predicted_duration_mean: Optional[int] = None
    predicted_duration_std_dev: Optional[int] = None
    
    # Risk Analysis
    risk_factors: List[str] = Field(default_factory=list)
    risk_score: float = Field(ge=0.0, le=1.0)
    
    # Recommendation
    recommendation: str
    should_proceed: bool
    
    # Timing
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DigitalTwinState(BaseModel):
    """Current state of the digital twin"""
    model_config = ConfigDict(from_attributes=True)
    
    twin_id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    entity_type: str  # "agent", "system", "workflow"
    entity_id: UUID
    
    # State Data
    state_snapshot: Dict[str, Any]
    metrics: Dict[str, float] = Field(default_factory=dict)
    
    # Timing
    snapshot_time: datetime = Field(default_factory=datetime.utcnow)
    valid_until: Optional[datetime] = None
    
    # Metadata
    version: int = 1
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScenarioTemplate(BaseModel):
    """Reusable simulation scenario template"""
    model_config = ConfigDict(from_attributes=True)
    
    template_id: UUID = Field(default_factory=uuid4)
    tenant_id: Optional[UUID] = None  # None for global templates
    
    # Template Info
    name: str
    description: str
    scenario_type: ScenarioType
    category: str  # "financial", "operational", "security", etc.
    
    # Configuration
    default_parameters: List[ScenarioParameter] = Field(default_factory=list)
    default_iterations: int = 100
    default_time_horizon: int = 86400
    
    # Usage Stats
    usage_count: int = 0
    avg_confidence: Optional[float] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    is_public: bool = False
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SimulationEvent(BaseModel):
    """Event emitted during simulation lifecycle"""
    event_id: UUID = Field(default_factory=uuid4)
    simulation_id: UUID
    event_type: str  # "started", "progress", "completed", "failed"
    event_data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: UUID


# Database Models (for SQLAlchemy)
class SimulationRunDB(BaseModel):
    """Database model for simulation runs"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    simulation_id: UUID
    tenant_id: UUID
    goal_id: Optional[UUID]
    task_id: Optional[UUID]
    scenario_type: str
    scenario_name: str
    scenario_description: Optional[str]
    parameters_json: str  # JSON string
    iterations: int
    time_horizon: int
    max_steps: int
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    aggregate_confidence: Optional[float]
    recommendation: Optional[str]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    metadata_json: str  # JSON string


class SimulationOutcomeDB(BaseModel):
    """Database model for simulation outcomes"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    outcome_id: UUID
    simulation_id: UUID
    iteration: int
    outcome_type: str
    confidence_score: float
    predicted_cost: Optional[float]
    predicted_duration: Optional[int]
    predicted_success_rate: Optional[float]
    risk_factors_json: str  # JSON string
    metrics_json: str  # JSON string
    timestamp: datetime
    metadata_json: str  # JSON string

# Made with Bob
