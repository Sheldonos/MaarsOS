"""
Vessel Swarm - Agent Lifecycle Management Service

FastAPI service for managing agent lifecycle, registry, and pool pre-warming.
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import db, get_db
from app.models import (
    SpawnAgentRequest,
    AgentResponse,
    UpdateAgentRequest,
    AssignTaskRequest,
    CreatePoolRequest,
    PoolResponse,
    WarmPoolRequest,
    HealthResponse,
    AgentType,
    AgentStatus,
    ModelTier,
)
from app.registry import agent_registry
from app.lifecycle import lifecycle_manager
from app.pool import pool_manager
from app.kafka_producer import kafka_producer

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    logger.info("starting_vessel_swarm", version=settings.SERVICE_VERSION)
    
    try:
        # Connect to database
        await db.connect()
        logger.info("database_connected")
        
        # Start Kafka producer
        await kafka_producer.start()
        logger.info("kafka_producer_started")
        
        # Set Kafka producer in lifecycle manager
        lifecycle_manager.set_kafka_producer(kafka_producer)
        
        # Start agent monitoring
        await lifecycle_manager.start_monitoring(db.get_session)
        logger.info("agent_monitoring_started")
        
        logger.info("vessel_swarm_started")
        
    except Exception as e:
        logger.error("startup_failed", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("shutting_down_vessel_swarm")
    
    try:
        # Stop monitoring
        await lifecycle_manager.stop_monitoring()
        
        # Stop Kafka producer
        await kafka_producer.stop()
        
        # Disconnect from database
        await db.disconnect()
        
        logger.info("vessel_swarm_shutdown_complete")
        
    except Exception as e:
        logger.error("shutdown_error", error=str(e))


# Create FastAPI app
app = FastAPI(
    title="Vessel Swarm",
    description="Agent Lifecycle Management Service",
    version=settings.SERVICE_VERSION,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    db_healthy = await db.health_check()
    kafka_healthy = await kafka_producer.health_check()
    
    return HealthResponse(
        status="healthy" if db_healthy and kafka_healthy else "degraded",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        timestamp=datetime.utcnow(),
        database_connected=db_healthy,
        kafka_connected=kafka_healthy,
    )


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    db_healthy = await db.health_check()
    
    if not db_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not ready",
        )
    
    return {"status": "ready"}


# Agent endpoints
@app.post("/v1/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def spawn_agent(
    request: SpawnAgentRequest,
    session: AsyncSession = Depends(get_db),
):
    """Spawn a new agent"""
    try:
        agent = await lifecycle_manager.spawn_agent(
            session=session,
            tenant_id=request.tenant_id,
            agent_type=request.agent_type,
            capabilities=request.capabilities,
            model_tier=request.model_tier,
            budget_ceiling_usd=request.budget_ceiling_usd,
            name=request.name,
            parent_agent_id=request.parent_agent_id,
        )
        
        return AgentResponse(
            agent_id=agent.agent_id,
            tenant_id=agent.tenant_id,
            name=agent.name,
            agent_type=agent.agent_type,
            capabilities=agent.capabilities,
            model_tier=agent.model_tier,
            status=agent.status,
            current_task_id=agent.current_task_id,
            budget_ceiling_usd=agent.budget_ceiling_usd,
            spent_usd=agent.spent_usd,
            created_at=agent.created_at,
            last_active_at=agent.last_active_at,
            parent_agent_id=agent.parent_agent_id,
        )
        
    except Exception as e:
        logger.error("spawn_agent_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to spawn agent: {str(e)}",
        )


@app.get("/v1/agents", response_model=List[AgentResponse])
async def list_agents(
    tenant_id: str,
    status_filter: Optional[AgentStatus] = None,
    agent_type: Optional[AgentType] = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
):
    """List agents with optional filters"""
    try:
        agents = await agent_registry.list_agents(
            session=session,
            tenant_id=tenant_id,
            status=status_filter,
            agent_type=agent_type,
            limit=limit,
            offset=offset,
        )
        
        return [
            AgentResponse(
                agent_id=agent.agent_id,
                tenant_id=agent.tenant_id,
                name=agent.name,
                agent_type=agent.agent_type,
                capabilities=agent.capabilities,
                model_tier=agent.model_tier,
                status=agent.status,
                current_task_id=agent.current_task_id,
                budget_ceiling_usd=agent.budget_ceiling_usd,
                spent_usd=agent.spent_usd,
                created_at=agent.created_at,
                last_active_at=agent.last_active_at,
                parent_agent_id=agent.parent_agent_id,
            )
            for agent in agents
        ]
        
    except Exception as e:
        logger.error("list_agents_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agents: {str(e)}",
        )


@app.get("/v1/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Get agent by ID"""
    try:
        agent = await agent_registry.get_agent(session, agent_id)
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found",
            )
        
        return AgentResponse(
            agent_id=agent.agent_id,
            tenant_id=agent.tenant_id,
            name=agent.name,
            agent_type=agent.agent_type,
            capabilities=agent.capabilities,
            model_tier=agent.model_tier,
            status=agent.status,
            current_task_id=agent.current_task_id,
            budget_ceiling_usd=agent.budget_ceiling_usd,
            spent_usd=agent.spent_usd,
            created_at=agent.created_at,
            last_active_at=agent.last_active_at,
            parent_agent_id=agent.parent_agent_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_agent_failed", error=str(e), agent_id=agent_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent: {str(e)}",
        )


@app.put("/v1/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    request: UpdateAgentRequest,
    session: AsyncSession = Depends(get_db),
):
    """Update agent"""
    try:
        agent = await agent_registry.update_agent(
            session=session,
            agent_id=agent_id,
            status=request.status,
            current_task_id=request.current_task_id,
            spent_usd=request.spent_usd,
            capabilities=request.capabilities,
        )
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found",
            )
        
        return AgentResponse(
            agent_id=agent.agent_id,
            tenant_id=agent.tenant_id,
            name=agent.name,
            agent_type=agent.agent_type,
            capabilities=agent.capabilities,
            model_tier=agent.model_tier,
            status=agent.status,
            current_task_id=agent.current_task_id,
            budget_ceiling_usd=agent.budget_ceiling_usd,
            spent_usd=agent.spent_usd,
            created_at=agent.created_at,
            last_active_at=agent.last_active_at,
            parent_agent_id=agent.parent_agent_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_agent_failed", error=str(e), agent_id=agent_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent: {str(e)}",
        )


@app.delete("/v1/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deregister_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Deregister (delete) agent"""
    try:
        deleted = await lifecycle_manager.terminate_agent(session, agent_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found",
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("deregister_agent_failed", error=str(e), agent_id=agent_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deregister agent: {str(e)}",
        )


@app.post("/v1/agents/{agent_id}/start", response_model=AgentResponse)
async def start_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Start agent"""
    try:
        agent = await lifecycle_manager.start_agent(session, agent_id)
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found",
            )
        
        return AgentResponse(
            agent_id=agent.agent_id,
            tenant_id=agent.tenant_id,
            name=agent.name,
            agent_type=agent.agent_type,
            capabilities=agent.capabilities,
            model_tier=agent.model_tier,
            status=agent.status,
            current_task_id=agent.current_task_id,
            budget_ceiling_usd=agent.budget_ceiling_usd,
            spent_usd=agent.spent_usd,
            created_at=agent.created_at,
            last_active_at=agent.last_active_at,
            parent_agent_id=agent.parent_agent_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("start_agent_failed", error=str(e), agent_id=agent_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start agent: {str(e)}",
        )


@app.post("/v1/agents/{agent_id}/stop", response_model=AgentResponse)
async def stop_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Stop agent"""
    try:
        agent = await lifecycle_manager.stop_agent(session, agent_id)
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found",
            )
        
        return AgentResponse(
            agent_id=agent.agent_id,
            tenant_id=agent.tenant_id,
            name=agent.name,
            agent_type=agent.agent_type,
            capabilities=agent.capabilities,
            model_tier=agent.model_tier,
            status=agent.status,
            current_task_id=agent.current_task_id,
            budget_ceiling_usd=agent.budget_ceiling_usd,
            spent_usd=agent.spent_usd,
            created_at=agent.created_at,
            last_active_at=agent.last_active_at,
            parent_agent_id=agent.parent_agent_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("stop_agent_failed", error=str(e), agent_id=agent_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop agent: {str(e)}",
        )


@app.post("/v1/agents/{agent_id}/assign", response_model=AgentResponse)
async def assign_task_to_agent(
    agent_id: str,
    request: AssignTaskRequest,
    session: AsyncSession = Depends(get_db),
):
    """Assign task to agent"""
    try:
        agent = await lifecycle_manager.assign_task(
            session=session,
            agent_id=agent_id,
            task_id=request.task_id,
        )
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found or not available",
            )
        
        return AgentResponse(
            agent_id=agent.agent_id,
            tenant_id=agent.tenant_id,
            name=agent.name,
            agent_type=agent.agent_type,
            capabilities=agent.capabilities,
            model_tier=agent.model_tier,
            status=agent.status,
            current_task_id=agent.current_task_id,
            budget_ceiling_usd=agent.budget_ceiling_usd,
            spent_usd=agent.spent_usd,
            created_at=agent.created_at,
            last_active_at=agent.last_active_at,
            parent_agent_id=agent.parent_agent_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("assign_task_failed", error=str(e), agent_id=agent_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign task: {str(e)}",
        )


# Pool endpoints
@app.post("/v1/pools", response_model=PoolResponse, status_code=status.HTTP_201_CREATED)
async def create_pool(
    request: CreatePoolRequest,
    session: AsyncSession = Depends(get_db),
):
    """Create agent pool"""
    try:
        from app.models import AgentPool
        from uuid import uuid4
        
        pool = AgentPool(
            pool_id=str(uuid4()),
            tenant_id=request.tenant_id,
            agent_type=request.agent_type,
            min_size=request.min_size,
            max_size=request.max_size,
            current_size=0,
            warm_agents=[],
            capabilities=request.capabilities,
            model_tier=request.model_tier,
            created_at=datetime.utcnow(),
        )
        
        pool = await pool_manager.create_pool(session, pool)
        
        # Pre-warm pool if enabled
        if settings.POOL_WARMUP_ENABLED:
            pool = await pool_manager.warm_pool(session, pool.pool_id)
        
        return PoolResponse(
            pool_id=pool.pool_id,
            tenant_id=pool.tenant_id,
            agent_type=pool.agent_type,
            min_size=pool.min_size,
            max_size=pool.max_size,
            current_size=pool.current_size,
            warm_agents=pool.warm_agents,
            capabilities=pool.capabilities,
            model_tier=pool.model_tier,
            created_at=pool.created_at,
        )
        
    except Exception as e:
        logger.error("create_pool_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create pool: {str(e)}",
        )


@app.get("/v1/pools", response_model=List[PoolResponse])
async def list_pools(
    tenant_id: str,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
):
    """List agent pools"""
    try:
        pools = await pool_manager.list_pools(
            session=session,
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
        )
        
        return [
            PoolResponse(
                pool_id=pool.pool_id,
                tenant_id=pool.tenant_id,
                agent_type=pool.agent_type,
                min_size=pool.min_size,
                max_size=pool.max_size,
                current_size=pool.current_size,
                warm_agents=pool.warm_agents,
                capabilities=pool.capabilities,
                model_tier=pool.model_tier,
                created_at=pool.created_at,
            )
            for pool in pools
        ]
        
    except Exception as e:
        logger.error("list_pools_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list pools: {str(e)}",
        )


@app.get("/v1/pools/{pool_id}", response_model=PoolResponse)
async def get_pool(
    pool_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Get pool by ID"""
    try:
        pool = await pool_manager.get_pool(session, pool_id)
        
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pool {pool_id} not found",
            )
        
        return PoolResponse(
            pool_id=pool.pool_id,
            tenant_id=pool.tenant_id,
            agent_type=pool.agent_type,
            min_size=pool.min_size,
            max_size=pool.max_size,
            current_size=pool.current_size,
            warm_agents=pool.warm_agents,
            capabilities=pool.capabilities,
            model_tier=pool.model_tier,
            created_at=pool.created_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_pool_failed", error=str(e), pool_id=pool_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pool: {str(e)}",
        )


@app.post("/v1/pools/{pool_id}/warm", response_model=PoolResponse)
async def warm_pool(
    pool_id: str,
    request: WarmPoolRequest = WarmPoolRequest(),
    session: AsyncSession = Depends(get_db),
):
    """Pre-warm agent pool"""
    try:
        pool = await pool_manager.warm_pool(
            session=session,
            pool_id=pool_id,
            target_size=request.target_size,
        )
        
        return PoolResponse(
            pool_id=pool.pool_id,
            tenant_id=pool.tenant_id,
            agent_type=pool.agent_type,
            min_size=pool.min_size,
            max_size=pool.max_size,
            current_size=pool.current_size,
            warm_agents=pool.warm_agents,
            capabilities=pool.capabilities,
            model_tier=pool.model_tier,
            created_at=pool.created_at,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error("warm_pool_failed", error=str(e), pool_id=pool_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to warm pool: {str(e)}",
        )


@app.delete("/v1/pools/{pool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pool(
    pool_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Delete agent pool"""
    try:
        deleted = await pool_manager.delete_pool(session, pool_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pool {pool_id} not found",
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_pool_failed", error=str(e), pool_id=pool_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete pool: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )


# Made with Bob