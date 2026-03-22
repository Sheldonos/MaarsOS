"""Agent pool management for vessel-swarm"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import httpx
from pydantic import BaseModel
from enum import Enum

from .database import AgentPoolDB
from .models import AgentPool, AgentType, ModelTier, AgentStatus, Agent
from .registry import agent_registry
from .lifecycle import lifecycle_manager

logger = structlog.get_logger()


class InfrastructureTarget(str, Enum):
    """DeerFlow-style infrastructure deployment targets"""
    LOCAL = "local"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"


class SuperAgentHarness(BaseModel):
    """
    DeerFlow-style unified deployment harness.
    Binds agent, memory partition, and sandbox into a single deployable unit.
    """
    agent_id: str
    tenant_id: str
    sandbox_endpoint: str
    memory_partition_id: str
    infrastructure_target: InfrastructureTarget = InfrastructureTarget.KUBERNETES
    created_at: datetime = datetime.utcnow()
    
    class Config:
        use_enum_values = True


class PoolManager:
    """Agent pool manager for pre-warming and allocation"""
    
    def __init__(self):
        self.logger = logger.bind(component="pool_manager")
    
    async def create_pool(
        self,
        session: AsyncSession,
        pool: AgentPool,
    ) -> AgentPool:
        """Create a new agent pool"""
        try:
            db_pool = AgentPoolDB(
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
            
            session.add(db_pool)
            await session.flush()
            
            self.logger.info(
                "pool_created",
                pool_id=pool.pool_id,
                tenant_id=pool.tenant_id,
                min_size=pool.min_size,
                max_size=pool.max_size,
            )
            
            return pool
            
        except Exception as e:
            self.logger.error("pool_creation_failed", error=str(e), pool_id=pool.pool_id)
            raise
    
    async def get_pool(self, session: AsyncSession, pool_id: str) -> Optional[AgentPool]:
        """Get pool by ID"""
        try:
            result = await session.execute(
                select(AgentPoolDB).where(AgentPoolDB.pool_id == pool_id)
            )
            db_pool = result.scalar_one_or_none()
            
            if not db_pool:
                return None
            
            return self._db_to_model(db_pool)
            
        except Exception as e:
            self.logger.error("get_pool_failed", error=str(e), pool_id=pool_id)
            raise
    
    async def list_pools(
        self,
        session: AsyncSession,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AgentPool]:
        """List pools for tenant"""
        try:
            query = (
                select(AgentPoolDB)
                .where(AgentPoolDB.tenant_id == tenant_id)
                .limit(limit)
                .offset(offset)
                .order_by(AgentPoolDB.created_at.desc())
            )
            
            result = await session.execute(query)
            db_pools = result.scalars().all()
            
            return [self._db_to_model(db_pool) for db_pool in db_pools]
            
        except Exception as e:
            self.logger.error("list_pools_failed", error=str(e), tenant_id=tenant_id)
            raise
    
    async def warm_pool(
        self,
        session: AsyncSession,
        pool_id: str,
        target_size: Optional[int] = None,
    ) -> AgentPool:
        """Pre-warm pool by spawning agents"""
        try:
            pool = await self.get_pool(session, pool_id)
            if not pool:
                raise ValueError(f"Pool {pool_id} not found")
            
            # Determine target size
            if target_size is None:
                target_size = pool.min_size
            else:
                target_size = min(target_size, pool.max_size)
            
            # Calculate how many agents to spawn
            agents_to_spawn = target_size - pool.current_size
            
            if agents_to_spawn <= 0:
                self.logger.info(
                    "pool_already_warm",
                    pool_id=pool_id,
                    current_size=pool.current_size,
                    target_size=target_size,
                )
                return pool
            
            # Spawn agents
            spawned_agents = []
            for i in range(agents_to_spawn):
                try:
                    agent = await lifecycle_manager.spawn_agent(
                        session=session,
                        tenant_id=pool.tenant_id,
                        agent_type=pool.agent_type,
                        capabilities=pool.capabilities,
                        model_tier=pool.model_tier,
                        name=f"pool-{pool_id}-agent-{i}",
                    )
                    spawned_agents.append(agent.agent_id)
                except Exception as e:
                    self.logger.error(
                        "failed_to_spawn_pool_agent",
                        error=str(e),
                        pool_id=pool_id,
                        index=i,
                    )
            
            # Update pool with new agents
            if spawned_agents:
                new_warm_agents = pool.warm_agents + spawned_agents
                new_current_size = len(new_warm_agents)
                
                await session.execute(
                    update(AgentPoolDB)
                    .where(AgentPoolDB.pool_id == pool_id)
                    .values(
                        warm_agents=new_warm_agents,
                        current_size=new_current_size,
                    )
                )
                
                await session.flush()
                
                self.logger.info(
                    "pool_warmed",
                    pool_id=pool_id,
                    spawned_count=len(spawned_agents),
                    new_size=new_current_size,
                )
            
            return await self.get_pool(session, pool_id)
            
        except Exception as e:
            self.logger.error("warm_pool_failed", error=str(e), pool_id=pool_id)
            raise
    
    async def get_available_agent(
        self,
        session: AsyncSession,
        pool_id: str,
    ) -> Optional[str]:
        """Get an available agent from the pool"""
        try:
            pool = await self.get_pool(session, pool_id)
            if not pool:
                return None
            
            # Find idle agent in pool
            for agent_id in pool.warm_agents:
                agent = await agent_registry.get_agent(session, agent_id)
                if agent and agent.status == AgentStatus.IDLE:
                    self.logger.info(
                        "allocated_agent_from_pool",
                        pool_id=pool_id,
                        agent_id=agent_id,
                    )
                    return agent_id
            
            # No idle agents, try to spawn new one if pool not at max
            if pool.current_size < pool.max_size:
                self.logger.info(
                    "spawning_new_agent_for_pool",
                    pool_id=pool_id,
                    current_size=pool.current_size,
                    max_size=pool.max_size,
                )
                
                agent = await lifecycle_manager.spawn_agent(
                    session=session,
                    tenant_id=pool.tenant_id,
                    agent_type=pool.agent_type,
                    capabilities=pool.capabilities,
                    model_tier=pool.model_tier,
                    name=f"pool-{pool_id}-dynamic",
                )
                
                # Add to pool
                new_warm_agents = pool.warm_agents + [agent.agent_id]
                await session.execute(
                    update(AgentPoolDB)
                    .where(AgentPoolDB.pool_id == pool_id)
                    .values(
                        warm_agents=new_warm_agents,
                        current_size=len(new_warm_agents),
                    )
                )
                
                await session.flush()
                
                return agent.agent_id
            
            self.logger.warning(
                "no_available_agents_in_pool",
                pool_id=pool_id,
                current_size=pool.current_size,
            )
            return None
            
        except Exception as e:
            self.logger.error("get_available_agent_failed", error=str(e), pool_id=pool_id)
            raise
    
    async def remove_agent_from_pool(
        self,
        session: AsyncSession,
        pool_id: str,
        agent_id: str,
    ) -> bool:
        """Remove agent from pool"""
        try:
            pool = await self.get_pool(session, pool_id)
            if not pool:
                return False
            
            if agent_id not in pool.warm_agents:
                return False
            
            new_warm_agents = [aid for aid in pool.warm_agents if aid != agent_id]
            
            await session.execute(
                update(AgentPoolDB)
                .where(AgentPoolDB.pool_id == pool_id)
                .values(
                    warm_agents=new_warm_agents,
                    current_size=len(new_warm_agents),
                )
            )
            
            await session.flush()
            
            self.logger.info(
                "agent_removed_from_pool",
                pool_id=pool_id,
                agent_id=agent_id,
                new_size=len(new_warm_agents),
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "remove_agent_from_pool_failed",
                error=str(e),
                pool_id=pool_id,
                agent_id=agent_id,
            )
            raise
    
    async def delete_pool(self, session: AsyncSession, pool_id: str) -> bool:
        """Delete pool and optionally terminate agents"""
        try:
            pool = await self.get_pool(session, pool_id)
            if not pool:
                return False
            
            # Terminate all agents in pool
            for agent_id in pool.warm_agents:
                try:
                    await lifecycle_manager.terminate_agent(session, agent_id)
                except Exception as e:
                    self.logger.error(
                        "failed_to_terminate_pool_agent",
                        error=str(e),
                        pool_id=pool_id,
                        agent_id=agent_id,
                    )
            
            # Delete pool
            result = await session.execute(
                delete(AgentPoolDB).where(AgentPoolDB.pool_id == pool_id)
            )
            
            await session.flush()
            
            deleted = result.rowcount > 0
            
            if deleted:
                self.logger.info("pool_deleted", pool_id=pool_id)
            
            return deleted
            
        except Exception as e:
            self.logger.error("delete_pool_failed", error=str(e), pool_id=pool_id)
            raise
    
    def _db_to_model(self, db_pool: AgentPoolDB) -> AgentPool:
        """Convert database model to Pydantic model"""
        return AgentPool(
            pool_id=db_pool.pool_id,
            tenant_id=db_pool.tenant_id,
            agent_type=db_pool.agent_type,
            min_size=db_pool.min_size,
            max_size=db_pool.max_size,
            current_size=db_pool.current_size,
            warm_agents=db_pool.warm_agents,
            capabilities=db_pool.capabilities,
            model_tier=db_pool.model_tier,
            created_at=db_pool.created_at,
        )


class HarnessManager:
    """
    DeerFlow-style harness manager for unified agent deployment.
    Provisions agent, memory, and sandbox together as a single unit.
    """
    
    def __init__(self):
        self.logger = logger.bind(component="harness_manager")
        self._sandbox_client = None
        self._memory_client = None
    
    def set_service_clients(self, sandbox_base_url: str, memory_base_url: str):
        """Configure service clients for cross-service orchestration"""
        self._sandbox_client = httpx.AsyncClient(base_url=sandbox_base_url)
        self._memory_client = httpx.AsyncClient(base_url=memory_base_url)
    
    async def deploy_harness(
        self,
        session: AsyncSession,
        agent: Agent,
        infrastructure_target: InfrastructureTarget = InfrastructureTarget.KUBERNETES,
    ) -> SuperAgentHarness:
        """
        Provisions a complete Super Agent Harness.
        Orchestrates agent, memory partition, and sandbox provisioning.
        """
        try:
            self.logger.info(
                "deploying_super_agent_harness",
                agent_id=agent.agent_id,
                tenant_id=agent.tenant_id,
                infrastructure=infrastructure_target,
            )
            
            # 1. Provision dedicated sandbox environment
            sandbox_url = await self._provision_sandbox(agent.agent_id, infrastructure_target)
            
            # 2. Create isolated memory partition
            memory_partition_id = await self._create_memory_partition(
                agent.tenant_id,
                agent.agent_id
            )
            
            # 3. Create harness binding
            harness = SuperAgentHarness(
                agent_id=agent.agent_id,
                tenant_id=agent.tenant_id,
                sandbox_endpoint=sandbox_url,
                memory_partition_id=memory_partition_id,
                infrastructure_target=infrastructure_target,
            )
            
            self.logger.info(
                "super_agent_harness_deployed",
                agent_id=agent.agent_id,
                sandbox_endpoint=sandbox_url,
                memory_partition=memory_partition_id,
            )
            
            return harness
            
        except Exception as e:
            self.logger.error(
                "deploy_harness_failed",
                error=str(e),
                agent_id=agent.agent_id,
            )
            raise
    
    async def _provision_sandbox(
        self,
        agent_id: str,
        infrastructure_target: InfrastructureTarget,
    ) -> str:
        """Provision isolated sandbox environment for agent"""
        if not self._sandbox_client:
            # Fallback to default sandbox endpoint
            return f"http://vessel-sandbox:8080/sandbox/{agent_id}"
        
        try:
            response = await self._sandbox_client.post(
                "/api/v1/sandbox/provision",
                json={
                    "agent_id": agent_id,
                    "infrastructure": infrastructure_target.value,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("sandbox_url", f"http://vessel-sandbox:8080/sandbox/{agent_id}")
            else:
                self.logger.warning(
                    "sandbox_provision_failed",
                    status_code=response.status_code,
                    agent_id=agent_id,
                )
                return f"http://vessel-sandbox:8080/sandbox/{agent_id}"
                
        except Exception as e:
            self.logger.error(
                "sandbox_provision_error",
                error=str(e),
                agent_id=agent_id,
            )
            return f"http://vessel-sandbox:8080/sandbox/{agent_id}"
    
    async def _create_memory_partition(
        self,
        tenant_id: str,
        agent_id: str,
    ) -> str:
        """Create isolated memory partition for agent"""
        partition_id = f"{tenant_id}_{agent_id}"
        
        if not self._memory_client:
            return partition_id
        
        try:
            response = await self._memory_client.post(
                "/api/v1/memory/partition",
                json={
                    "tenant_id": tenant_id,
                    "agent_id": agent_id,
                    "partition_id": partition_id,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("partition_id", partition_id)
            else:
                self.logger.warning(
                    "memory_partition_creation_failed",
                    status_code=response.status_code,
                    agent_id=agent_id,
                )
                return partition_id
                
        except Exception as e:
            self.logger.error(
                "memory_partition_error",
                error=str(e),
                agent_id=agent_id,
            )
            return partition_id
    
    async def teardown_harness(
        self,
        harness: SuperAgentHarness,
    ) -> bool:
        """Teardown a Super Agent Harness and clean up resources"""
        try:
            self.logger.info(
                "tearing_down_harness",
                agent_id=harness.agent_id,
            )
            
            # 1. Deprovision sandbox
            if self._sandbox_client:
                try:
                    await self._sandbox_client.delete(
                        f"/api/v1/sandbox/{harness.agent_id}"
                    )
                except Exception as e:
                    self.logger.error(
                        "sandbox_teardown_error",
                        error=str(e),
                        agent_id=harness.agent_id,
                    )
            
            # 2. Delete memory partition
            if self._memory_client:
                try:
                    await self._memory_client.delete(
                        f"/api/v1/memory/partition/{harness.memory_partition_id}"
                    )
                except Exception as e:
                    self.logger.error(
                        "memory_partition_teardown_error",
                        error=str(e),
                        agent_id=harness.agent_id,
                    )
            
            self.logger.info(
                "harness_teardown_complete",
                agent_id=harness.agent_id,
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "teardown_harness_failed",
                error=str(e),
                agent_id=harness.agent_id,
            )
            return False


# Global manager instances
pool_manager = PoolManager()
harness_manager = HarnessManager()


# Made with Bob