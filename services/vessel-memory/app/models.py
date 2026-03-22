"""
Pydantic models for vessel-memory service.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Types of memory."""
    EPISODIC = "episodic"  # Specific events and interactions
    SEMANTIC = "semantic"  # General facts and knowledge
    PROCEDURAL = "procedural"  # How to perform tasks


class MemoryImportance(str, Enum):
    """Importance levels for memory prioritization."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EntityType(str, Enum):
    """Types of entities in knowledge graph."""
    PERSON = "person"
    ORGANIZATION = "organization"
    CONCEPT = "concept"
    EVENT = "event"
    TASK = "task"
    DOCUMENT = "document"
    TOOL = "tool"
    AGENT = "agent"
    # MiroFish - Digital Twin entities
    DIGITAL_TWIN = "digital_twin"
    SIMULATION_STATE = "simulation_state"


class RelationshipType(str, Enum):
    """Types of relationships in knowledge graph."""
    RELATES_TO = "relates_to"
    DEPENDS_ON = "depends_on"
    CAUSED_BY = "caused_by"
    SIMILAR_TO = "similar_to"
    PART_OF = "part_of"
    CREATED_BY = "created_by"
    USED_BY = "used_by"
    MENTIONS = "mentions"
    # MiroFish - Digital Twin relationships
    SIMULATES = "simulates"
    INTERACTS_WITH_TWIN = "interacts_with_twin"


# Memory Node Models

class MemoryNode(BaseModel):
    """Individual memory unit stored in vector store."""
    node_id: Optional[str] = None
    tenant_id: str
    agent_id: Optional[str] = None
    
    # Content
    content: str
    embedding: Optional[List[float]] = None
    
    # Classification
    memory_type: MemoryType
    importance_score: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Provenance
    provenance_hash: Optional[str] = None
    source_task_id: Optional[str] = None
    source_tool: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    accessed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Access control
    is_private: bool = False
    shared_with_tenants: List[str] = Field(default_factory=list)


class MemoryNodeCreate(BaseModel):
    """Request to create a memory node."""
    tenant_id: str
    agent_id: Optional[str] = None
    content: str
    memory_type: MemoryType
    importance_score: float = 0.5
    source_task_id: Optional[str] = None
    source_tool: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    is_private: bool = False


class MemoryNodeUpdate(BaseModel):
    """Request to update a memory node."""
    content: Optional[str] = None
    importance_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_private: Optional[bool] = None


class MemorySearchRequest(BaseModel):
    """Request to search memory."""
    tenant_id: str
    agent_id: Optional[str] = None
    query: str
    memory_types: Optional[List[MemoryType]] = None
    top_k: int = Field(default=10, ge=1, le=100)
    score_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    include_shared: bool = False
    filters: Dict[str, Any] = Field(default_factory=dict)


class MemorySearchResult(BaseModel):
    """Result from memory search."""
    node: MemoryNode
    score: float
    distance: float


class MemorySearchResponse(BaseModel):
    """Response from memory search."""
    results: List[MemorySearchResult]
    total_count: int
    search_time_ms: float


# Knowledge Graph Models

class KnowledgeGraphNode(BaseModel):
    """Entity in the knowledge graph."""
    kg_node_id: Optional[str] = None
    tenant_id: str
    
    # Entity information
    entity_type: EntityType
    entity_name: str
    entity_description: Optional[str] = None
    
    # Properties
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    # Linked memory
    memory_node_ids: List[str] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    # Access control
    is_private: bool = False


class KnowledgeGraphEdge(BaseModel):
    """Relationship between entities in knowledge graph."""
    edge_id: Optional[str] = None
    tenant_id: str
    
    # Relationship
    source_kg_node_id: str
    target_kg_node_id: str
    relationship_type: RelationshipType
    
    # Properties
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    # Provenance
    created_from_task_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class KnowledgeGraphNodeCreate(BaseModel):
    """Request to create a knowledge graph node."""
    tenant_id: str
    entity_type: EntityType
    entity_name: str
    entity_description: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    memory_node_ids: List[str] = Field(default_factory=list)
    is_private: bool = False


class KnowledgeGraphEdgeCreate(BaseModel):
    """Request to create a knowledge graph edge."""
    tenant_id: str
    source_kg_node_id: str
    target_kg_node_id: str
    relationship_type: RelationshipType
    weight: float = 1.0
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_from_task_id: Optional[str] = None


# GraphRAG Models

class GraphRAGQuery(BaseModel):
    """Query for GraphRAG retrieval."""
    tenant_id: str
    agent_id: Optional[str] = None
    query: str
    
    # Graph traversal parameters
    max_depth: int = Field(default=3, ge=1, le=5)
    max_nodes: int = Field(default=100, ge=1, le=500)
    relationship_types: Optional[List[RelationshipType]] = None
    
    # Vector search parameters
    vector_top_k: int = Field(default=10, ge=1, le=50)
    vector_score_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    
    # Filters
    entity_types: Optional[List[EntityType]] = None
    include_shared: bool = False


class GraphRAGNode(BaseModel):
    """Node in GraphRAG result."""
    kg_node: KnowledgeGraphNode
    relevance_score: float
    path_from_query: List[str]  # List of node IDs in path
    connected_memories: List[MemoryNode]


class GraphRAGResponse(BaseModel):
    """Response from GraphRAG query."""
    nodes: List[GraphRAGNode]
    edges: List[KnowledgeGraphEdge]
    context_summary: str
    total_nodes: int
    total_edges: int
    query_time_ms: float


# Context Management Models

class ContextWindow(BaseModel):
    """Context window for agent."""
    tenant_id: str
    agent_id: str
    task_id: Optional[str] = None
    
    # Retrieved context
    episodic_memories: List[MemoryNode] = Field(default_factory=list)
    semantic_memories: List[MemoryNode] = Field(default_factory=list)
    procedural_memories: List[MemoryNode] = Field(default_factory=list)
    
    # Graph context
    graph_nodes: List[KnowledgeGraphNode] = Field(default_factory=list)
    graph_edges: List[KnowledgeGraphEdge] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    token_count: Optional[int] = None


class ContextRetrievalRequest(BaseModel):
    """Request to retrieve context for agent."""
    tenant_id: str
    agent_id: str
    task_id: Optional[str] = None
    query: str
    
    # Memory retrieval
    include_episodic: bool = True
    include_semantic: bool = True
    include_procedural: bool = True
    max_memories_per_type: int = Field(default=5, ge=1, le=20)
    
    # Graph retrieval
    include_graph: bool = True
    graph_max_depth: int = Field(default=2, ge=1, le=5)
    
    # Token budget
    max_tokens: Optional[int] = None


# Provenance Models

class ProvenanceRecord(BaseModel):
    """Provenance record for memory."""
    provenance_hash: str
    memory_node_id: str
    
    # Source information
    source_type: str  # task, tool, llm, user
    source_id: str
    source_timestamp: datetime
    
    # Chain of custody
    created_by_agent_id: Optional[str] = None
    verified_by: Optional[str] = None
    
    # Integrity
    content_hash: str
    signature: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)


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
    total_memory_nodes: int
    total_graph_nodes: int
    total_graph_edges: int
    avg_search_time_ms: float
    avg_graphrag_time_ms: float
    cache_hit_rate: float
    vector_store_size_mb: float
    graph_store_size_mb: float


# Made with Bob