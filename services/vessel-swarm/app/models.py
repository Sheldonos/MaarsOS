"""Pydantic models for vessel-swarm"""
from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
import yaml


class AgentType(str, Enum):
    """Agent type enumeration"""
    EPHEMERAL = "EPHEMERAL"
    PERSISTENT = "PERSISTENT"
    SPECIALIZED = "SPECIALIZED"


class AgentStatus(str, Enum):
    """Agent status enumeration"""
    IDLE = "IDLE"
    ASSIGNED = "ASSIGNED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    TERMINATED = "TERMINATED"


class ModelTier(str, Enum):
    """Model tier enumeration"""
    NANO = "NANO"
    MID = "MID"
    FRONTIER = "FRONTIER"


# Agency Agents - Declarative Persona Model
class AgentPersona(BaseModel):
    """Agency-Agents style declarative persona"""
    name: str = Field(..., description="Persona name")
    vibe: str = Field(..., description="The personality/tone of the agent")
    emoji: str = Field(default="🤖", description="Emoji representation")
    color_hex: str = Field(default="#3B82F6", description="Color for UI representation")
    system_prompt_template: str = Field(..., description="System prompt template for the agent")
    allowed_tools: List[str] = Field(default_factory=list, description="List of allowed tool names")
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> 'AgentPersona':
        """Parse declarative YAML definition"""
        data = yaml.safe_load(yaml_content)
        return cls(**data)
    
    def to_yaml(self) -> str:
        """Export persona to YAML format"""
        return yaml.dump(self.model_dump(), default_flow_style=False)


class CommunicationFlow(BaseModel):
    """Defines allowed agent-to-agent communication patterns"""
    source_agent_role: str = Field(..., description="Source agent role (e.g., 'Director')")
    target_agent_role: str = Field(..., description="Target agent role (e.g., 'Art_Director')")
    allowed_message_types: List[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed message types (* for all)"
    )
    bidirectional: bool = Field(
        default=False,
        description="Whether communication is bidirectional"
    )
    
    class Config:
        use_enum_values = True


class AgencyManifesto(BaseModel):
    """Shared context and rules for all agents in a swarm/agency"""
    agency_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    agency_name: str = Field(..., description="Name of the agency/swarm")
    mission_statement: str = Field(..., description="High-level mission for the agency")
    shared_instructions: str = Field(..., description="Instructions shared by all agents")
    communication_flows: List[CommunicationFlow] = Field(
        default_factory=list,
        description="Allowed communication patterns"
    )
    world_state_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="Schema for world state (for cinematic use case)"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


# Request/Response Models
class SpawnAgentRequest(BaseModel):
    """Request to spawn a new agent"""
    tenant_id: str = Field(..., description="Tenant ID")
    agent_type: AgentType = Field(default=AgentType.EPHEMERAL, description="Agent type")
    capabilities: List[str] = Field(default=["general"], description="Agent capabilities")
    model_tier: ModelTier = Field(default=ModelTier.MID, description="Model tier")
    budget_ceiling_usd: float = Field(default=10.0, description="Budget ceiling in USD")
    name: Optional[str] = Field(None, description="Agent name")
    parent_agent_id: Optional[str] = Field(None, description="Parent agent ID for hierarchical agents")
    persona_yaml: Optional[str] = Field(None, description="Declarative YAML persona definition (Agency Agents style)")
    persona: Optional[AgentPersona] = Field(None, description="Parsed persona object")


class AgentResponse(BaseModel):
    """Agent response model"""
    agent_id: str
    tenant_id: str
    name: Optional[str]
    agent_type: AgentType
    capabilities: List[str]
    model_tier: ModelTier
    status: AgentStatus
    current_task_id: Optional[str]
    budget_ceiling_usd: float
    spent_usd: float
    created_at: datetime
    last_active_at: datetime
    parent_agent_id: Optional[str] = None


class UpdateAgentRequest(BaseModel):
    """Request to update agent"""
    status: Optional[AgentStatus] = None
    current_task_id: Optional[str] = None
    spent_usd: Optional[float] = None
    capabilities: Optional[List[str]] = None


class AssignTaskRequest(BaseModel):
    """Request to assign task to agent"""
    task_id: str = Field(..., description="Task ID")
    task_definition: dict = Field(..., description="Task definition")


class CreatePoolRequest(BaseModel):
    """Request to create agent pool"""
    tenant_id: str = Field(..., description="Tenant ID")
    agent_type: AgentType = Field(default=AgentType.EPHEMERAL, description="Agent type")
    min_size: int = Field(default=2, ge=1, description="Minimum pool size")
    max_size: int = Field(default=10, ge=1, description="Maximum pool size")
    capabilities: List[str] = Field(default=["general"], description="Agent capabilities")
    model_tier: ModelTier = Field(default=ModelTier.MID, description="Model tier")


class PoolResponse(BaseModel):
    """Pool response model"""
    pool_id: str
    tenant_id: str
    agent_type: AgentType
    min_size: int
    max_size: int
    current_size: int
    warm_agents: List[str]
    capabilities: List[str]
    model_tier: ModelTier
    created_at: datetime


class WarmPoolRequest(BaseModel):
    """Request to warm up pool"""
    target_size: Optional[int] = Field(None, description="Target pool size")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
    timestamp: datetime
    database_connected: bool
    kafka_connected: bool


class AgentMetrics(BaseModel):
    """Agent metrics model"""
    agent_id: str
    tasks_completed: int = 0
    avg_execution_time_ms: int = 0
    total_cost_usd: float = 0.0
    error_count: int = 0
    last_updated: datetime


# Database Models (SQLAlchemy will use these as reference)
class Agent(BaseModel):
    """Agent database model"""
    agent_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    name: Optional[str] = None
    agent_type: AgentType
    capabilities: List[str]
    model_tier: ModelTier
    status: AgentStatus = AgentStatus.IDLE
    current_task_id: Optional[str] = None
    budget_ceiling_usd: float
    spent_usd: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active_at: datetime = Field(default_factory=datetime.utcnow)
    parent_agent_id: Optional[str] = None
    
    class Config:
        use_enum_values = True


class AgentPool(BaseModel):
    """Agent pool database model"""
    pool_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    agent_type: AgentType
    min_size: int
    max_size: int
    current_size: int = 0
    warm_agents: List[str] = Field(default_factory=list)
    capabilities: List[str]
    model_tier: ModelTier
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


# Event Models
class AgentEvent(BaseModel):
    """Agent event for Kafka"""
    event_type: str
    agent_id: str
    tenant_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: dict


# Made with Bob