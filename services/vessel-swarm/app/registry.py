"""Agent registry management for vessel-swarm"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from .database import AgentDB
from .models import Agent, AgentStatus, AgentType, ModelTier

logger = structlog.get_logger()


class AgentRegistry:
    """Agent registry for managing agent metadata"""
    
    def __init__(self):
        self.logger = logger.bind(component="agent_registry")
    
    async def register_agent(self, session: AsyncSession, agent: Agent) -> Agent:
        """Register a new agent"""
        try:
            db_agent = AgentDB(
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
            
            session.add(db_agent)
            await session.flush()
            
            self.logger.info(
                "agent_registered",
                agent_id=agent.agent_id,
                tenant_id=agent.tenant_id,
                agent_type=agent.agent_type,
            )
            
            return agent
            
        except Exception as e:
            self.logger.error("agent_registration_failed", error=str(e), agent_id=agent.agent_id)
            raise
    
    async def get_agent(self, session: AsyncSession, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        try:
            result = await session.execute(
                select(AgentDB).where(AgentDB.agent_id == agent_id)
            )
            db_agent = result.scalar_one_or_none()
            
            if not db_agent:
                return None
            
            return self._db_to_model(db_agent)
            
        except Exception as e:
            self.logger.error("get_agent_failed", error=str(e), agent_id=agent_id)
            raise
    
    async def list_agents(
        self,
        session: AsyncSession,
        tenant_id: str,
        status: Optional[AgentStatus] = None,
        agent_type: Optional[AgentType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Agent]:
        """List agents with optional filters"""
        try:
            query = select(AgentDB).where(AgentDB.tenant_id == tenant_id)
            
            if status:
                query = query.where(AgentDB.status == status)
            
            if agent_type:
                query = query.where(AgentDB.agent_type == agent_type)
            
            query = query.limit(limit).offset(offset).order_by(AgentDB.created_at.desc())
            
            result = await session.execute(query)
            db_agents = result.scalars().all()
            
            return [self._db_to_model(db_agent) for db_agent in db_agents]
            
        except Exception as e:
            self.logger.error("list_agents_failed", error=str(e), tenant_id=tenant_id)
            raise
    
    async def update_agent(
        self,
        session: AsyncSession,
        agent_id: str,
        status: Optional[AgentStatus] = None,
        current_task_id: Optional[str] = None,
        spent_usd: Optional[float] = None,
        capabilities: Optional[List[str]] = None,
    ) -> Optional[Agent]:
        """Update agent"""
        try:
            update_data = {"last_active_at": datetime.utcnow()}
            
            if status is not None:
                update_data["status"] = status
            
            if current_task_id is not None:
                update_data["current_task_id"] = current_task_id
            
            if spent_usd is not None:
                update_data["spent_usd"] = spent_usd
            
            if capabilities is not None:
                update_data["capabilities"] = capabilities
            
            await session.execute(
                update(AgentDB)
                .where(AgentDB.agent_id == agent_id)
                .values(**update_data)
            )
            
            await session.flush()
            
            self.logger.info("agent_updated", agent_id=agent_id, updates=update_data)
            
            return await self.get_agent(session, agent_id)
            
        except Exception as e:
            self.logger.error("update_agent_failed", error=str(e), agent_id=agent_id)
            raise
    
    async def deregister_agent(self, session: AsyncSession, agent_id: str) -> bool:
        """Deregister (delete) an agent"""
        try:
            result = await session.execute(
                delete(AgentDB).where(AgentDB.agent_id == agent_id)
            )
            
            await session.flush()
            
            deleted = result.rowcount > 0
            
            if deleted:
                self.logger.info("agent_deregistered", agent_id=agent_id)
            else:
                self.logger.warning("agent_not_found_for_deregistration", agent_id=agent_id)
            
            return deleted
            
        except Exception as e:
            self.logger.error("deregister_agent_failed", error=str(e), agent_id=agent_id)
            raise
    
    async def find_available_agents(
        self,
        session: AsyncSession,
        tenant_id: str,
        capabilities: List[str],
        model_tier: Optional[ModelTier] = None,
    ) -> List[Agent]:
        """Find available agents matching capabilities"""
        try:
            query = select(AgentDB).where(
                AgentDB.tenant_id == tenant_id,
                AgentDB.status == AgentStatus.IDLE,
            )
            
            if model_tier:
                query = query.where(AgentDB.model_tier == model_tier)
            
            result = await session.execute(query)
            db_agents = result.scalars().all()
            
            # Filter by capabilities (agent must have all required capabilities)
            matching_agents = []
            required_caps = set(capabilities)
            
            for db_agent in db_agents:
                agent_caps = set(db_agent.capabilities)
                if required_caps.issubset(agent_caps):
                    matching_agents.append(self._db_to_model(db_agent))
            
            self.logger.info(
                "found_available_agents",
                tenant_id=tenant_id,
                count=len(matching_agents),
                required_capabilities=capabilities,
            )
            
            return matching_agents
            
        except Exception as e:
            self.logger.error("find_available_agents_failed", error=str(e), tenant_id=tenant_id)
            raise
    
    async def get_agent_count(
        self,
        session: AsyncSession,
        tenant_id: str,
        status: Optional[AgentStatus] = None,
    ) -> int:
        """Get count of agents"""
        try:
            from sqlalchemy import func
            
            query = select(func.count(AgentDB.agent_id)).where(
                AgentDB.tenant_id == tenant_id
            )
            
            if status:
                query = query.where(AgentDB.status == status)
            
            result = await session.execute(query)
            count = result.scalar_one()
            
            return count
            
        except Exception as e:
            self.logger.error("get_agent_count_failed", error=str(e), tenant_id=tenant_id)
            raise
    
    def _db_to_model(self, db_agent: AgentDB) -> Agent:
        """Convert database model to Pydantic model"""
        return Agent(
            agent_id=db_agent.agent_id,
            tenant_id=db_agent.tenant_id,
            name=db_agent.name,
            agent_type=db_agent.agent_type,
            capabilities=db_agent.capabilities,
            model_tier=db_agent.model_tier,
            status=db_agent.status,
            current_task_id=db_agent.current_task_id,
            budget_ceiling_usd=db_agent.budget_ceiling_usd,
            spent_usd=db_agent.spent_usd,
            created_at=db_agent.created_at,
            last_active_at=db_agent.last_active_at,
            parent_agent_id=db_agent.parent_agent_id,
        )


# Global registry instance
agent_registry = AgentRegistry()


# Made with Bob