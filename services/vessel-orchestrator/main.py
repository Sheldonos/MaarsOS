"""
Vessel Orchestrator - Master orchestration service for MAARS
Handles goal submission, task planning, and execution coordination
"""
import asyncio
import uuid
from datetime import datetime
from typing import Optional

import structlog
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import settings
from app.kafka_producer import KafkaProducer
from app.planner import GoalPlanner
from app.sandbox_client import SandboxClient

# Initialize structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

# Initialize FastAPI app
app = FastAPI(
    title="Vessel Orchestrator",
    description="Master orchestration service for MAARS with DAG support",
    version="0.2.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
kafka_producer: Optional[KafkaProducer] = None
sandbox_client: Optional[SandboxClient] = None
goal_planner: Optional[GoalPlanner] = None


# Pydantic models
class GoalRequest(BaseModel):
    description: str = Field(..., description="Natural language goal description")
    priority: str = Field(default="MEDIUM", description="Goal priority: LOW, MEDIUM, HIGH, CRITICAL")
    total_budget_usd: Optional[float] = Field(default=None, description="Maximum budget in USD")
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID (extracted from JWT in production)")
    use_dag_mode: Optional[bool] = Field(default=None, description="Enable DAG mode for complex multi-task goals")


class GoalResponse(BaseModel):
    goal_id: str
    tenant_id: str
    description: str
    priority: str
    status: str
    total_budget_usd: Optional[float]
    created_at: str


class TaskStatus(BaseModel):
    task_id: str
    goal_id: str
    status: str
    output: Optional[str]
    error: Optional[str]


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global kafka_producer, sandbox_client, goal_planner
    
    logger.info(
        "Starting vessel-orchestrator",
        version="0.2.0",
        dag_mode=settings.ENABLE_DAG_MODE,
        max_parallel_tasks=settings.MAX_PARALLEL_TASKS,
    )
    
    # Initialize Kafka producer
    kafka_producer = KafkaProducer(
        bootstrap_servers=settings.KAFKA_BROKERS.split(",")
    )
    await kafka_producer.start()
    logger.info("Kafka producer initialized", brokers=settings.KAFKA_BROKERS)
    
    # Initialize sandbox client
    sandbox_client = SandboxClient(base_url=settings.SANDBOX_URL)
    logger.info("Sandbox client initialized", url=settings.SANDBOX_URL)
    
    # Initialize goal planner with Phase 2 features
    goal_planner = GoalPlanner(
        sandbox_client=sandbox_client,
        kafka_producer=kafka_producer,
        llm_router_url=settings.LLM_ROUTER_URL,
        enable_dag_mode=settings.ENABLE_DAG_MODE,
        max_parallel_tasks=settings.MAX_PARALLEL_TASKS,
    )
    logger.info(
        "Goal planner initialized",
        dag_mode=settings.ENABLE_DAG_MODE,
        right_sizing=settings.ENABLE_RIGHT_SIZING,
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global kafka_producer
    
    logger.info("Shutting down vessel-orchestrator")
    
    if kafka_producer:
        await kafka_producer.stop()
        logger.info("Kafka producer stopped")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "vessel-orchestrator",
        "version": "0.2.0",
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "dag_mode": settings.ENABLE_DAG_MODE,
            "right_sizing": settings.ENABLE_RIGHT_SIZING,
            "max_parallel_tasks": settings.MAX_PARALLEL_TASKS,
        },
    }


@app.post("/v1/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(request: GoalRequest):
    """
    Submit a new goal for execution
    
    This endpoint accepts a natural language goal description and initiates
    the planning and execution process.
    """
    # Generate IDs
    goal_id = str(uuid.uuid4())
    tenant_id = request.tenant_id or "default-tenant"  # In production, extract from JWT
    
    logger.info(
        "Goal submitted",
        goal_id=goal_id,
        tenant_id=tenant_id,
        description=request.description,
        priority=request.priority,
    )
    
    # Create goal packet
    goal_packet = {
        "goal_id": goal_id,
        "tenant_id": tenant_id,
        "description": request.description,
        "priority": request.priority,
        "total_budget_usd": request.total_budget_usd,
        "status": "PENDING",
        "created_at": datetime.utcnow().isoformat(),
        "use_dag_mode": request.use_dag_mode if request.use_dag_mode is not None else settings.ENABLE_DAG_MODE,
    }
    
    # Publish goal.created event
    await kafka_producer.send_event(
        topic="maars.goals",
        event_type="goal.created",
        payload=goal_packet,
    )
    
    # Start async planning and execution
    asyncio.create_task(
        goal_planner.process_goal(goal_packet)
    )
    
    return GoalResponse(**goal_packet)


@app.get("/v1/goals/{goal_id}", response_model=GoalResponse)
async def get_goal(goal_id: str):
    """Get goal status by ID"""
    # TODO: Implement database lookup
    # For Phase 1 MVP, return mock data
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Goal retrieval not yet implemented in Phase 1 MVP",
    )


@app.post("/v1/goals/{goal_id}/cancel")
async def cancel_goal(goal_id: str):
    """Cancel a running goal"""
    logger.info("Goal cancellation requested", goal_id=goal_id)
    
    # Publish goal.cancelled event
    await kafka_producer.send_event(
        topic="maars.goals",
        event_type="goal.cancelled",
        payload={"goal_id": goal_id, "cancelled_at": datetime.utcnow().isoformat()},
    )
    
    return {"status": "cancelled", "goal_id": goal_id}


@app.get("/v1/tasks/{task_id}", response_model=TaskStatus)
async def get_task(task_id: str):
    """Get task status by ID"""
    # TODO: Implement database lookup
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Task retrieval not yet implemented in Phase 1 MVP",
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8081,
        reload=True,
        log_level="info",
    )

# Made with Bob
