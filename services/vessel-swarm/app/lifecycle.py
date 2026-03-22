"""Agent lifecycle management for vessel-swarm"""
import asyncio
from typing import Optional
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import httpx

from .models import (
    Agent,
    AgentType,
    AgentStatus,
    ModelTier,
    AgentEvent,
)
from .registry import agent_registry
from .config import settings

logger = structlog.get_logger()


class LifecycleManager:
    """Agent lifecycle manager"""
    
    def __init__(self):
        self.logger = logger.bind(component="lifecycle_manager")
        self._monitoring_task = None
        self._kafka_producer = None
        self._economics_client = None
    
    def set_kafka_producer(self, producer):
        """Set Kafka producer for events"""
        self._kafka_producer = producer
    
    def set_economics_client(self, base_url: str):
        """Set economics service client for ROI tracking"""
        self._economics_client = httpx.AsyncClient(base_url=base_url)
    
    async def spawn_agent(
        self,
        session: AsyncSession,
        tenant_id: str,
        agent_type: AgentType,
        capabilities: list[str],
        model_tier: ModelTier,
        budget_ceiling_usd: float = None,
        name: Optional[str] = None,
        parent_agent_id: Optional[str] = None,
    ) -> Agent:
        """Spawn a new agent"""
        try:
            if budget_ceiling_usd is None:
                budget_ceiling_usd = settings.DEFAULT_BUDGET_CEILING_USD
            
            agent = Agent(
                agent_id=str(uuid4()),
                tenant_id=tenant_id,
                name=name,
                agent_type=agent_type,
                capabilities=capabilities,
                model_tier=model_tier,
                status=AgentStatus.IDLE,
                budget_ceiling_usd=budget_ceiling_usd,
                spent_usd=0.0,
                created_at=datetime.utcnow(),
                last_active_at=datetime.utcnow(),
                parent_agent_id=parent_agent_id,
            )
            
            # Register agent
            agent = await agent_registry.register_agent(session, agent)
            
            # Publish event
            await self._publish_event(
                event_type="agent.spawned",
                agent_id=agent.agent_id,
                tenant_id=tenant_id,
                payload={
                    "agent_type": agent_type.value,
                    "capabilities": capabilities,
                    "model_tier": model_tier.value,
                },
            )
            
            self.logger.info(
                "agent_spawned",
                agent_id=agent.agent_id,
                tenant_id=tenant_id,
                agent_type=agent_type,
            )
            
            return agent
            
        except Exception as e:
            self.logger.error("spawn_agent_failed", error=str(e), tenant_id=tenant_id)
            raise
    
    async def start_agent(
        self,
        session: AsyncSession,
        agent_id: str,
    ) -> Optional[Agent]:
        """Start an agent (transition to ACTIVE)"""
        try:
            agent = await agent_registry.get_agent(session, agent_id)
            if not agent:
                return None
            
            if agent.status != AgentStatus.IDLE:
                self.logger.warning(
                    "agent_not_idle_for_start",
                    agent_id=agent_id,
                    current_status=agent.status,
                )
                return agent
            
            # Update status
            agent = await agent_registry.update_agent(
                session,
                agent_id,
                status=AgentStatus.ASSIGNED,
            )
            
            await self._publish_event(
                event_type="agent.started",
                agent_id=agent_id,
                tenant_id=agent.tenant_id,
                payload={"status": AgentStatus.ASSIGNED.value},
            )
            
            self.logger.info("agent_started", agent_id=agent_id)
            
            return agent
            
        except Exception as e:
            self.logger.error("start_agent_failed", error=str(e), agent_id=agent_id)
            raise
    
    async def assign_task(
        self,
        session: AsyncSession,
        agent_id: str,
        task_id: str,
    ) -> Optional[Agent]:
        """Assign task to agent"""
        try:
            agent = await agent_registry.get_agent(session, agent_id)
            if not agent:
                return None
            
            if agent.status not in [AgentStatus.IDLE, AgentStatus.ASSIGNED]:
                self.logger.warning(
                    "agent_not_available_for_task",
                    agent_id=agent_id,
                    current_status=agent.status,
                )
                return None
            
            # Update agent with task
            agent = await agent_registry.update_agent(
                session,
                agent_id,
                status=AgentStatus.EXECUTING,
                current_task_id=task_id,
            )
            
            await self._publish_event(
                event_type="agent.task_assigned",
                agent_id=agent_id,
                tenant_id=agent.tenant_id,
                payload={
                    "task_id": task_id,
                    "status": AgentStatus.EXECUTING.value,
                },
            )
            
            self.logger.info(
                "task_assigned_to_agent",
                agent_id=agent_id,
                task_id=task_id,
            )
            
            return agent
            
        except Exception as e:
            self.logger.error(
                "assign_task_failed",
                error=str(e),
                agent_id=agent_id,
                task_id=task_id,
            )
            raise
    
    async def complete_task(
        self,
        session: AsyncSession,
        agent_id: str,
        cost_usd: float = 0.0,
    ) -> Optional[Agent]:
        """Mark task as completed and return agent to IDLE"""
        try:
            agent = await agent_registry.get_agent(session, agent_id)
            if not agent:
                return None
            
            # Update spent amount
            new_spent = agent.spent_usd + cost_usd
            
            # Return to IDLE
            agent = await agent_registry.update_agent(
                session,
                agent_id,
                status=AgentStatus.IDLE,
                current_task_id=None,
                spent_usd=new_spent,
            )
            
            await self._publish_event(
                event_type="agent.task_completed",
                agent_id=agent_id,
                tenant_id=agent.tenant_id,
                payload={
                    "cost_usd": cost_usd,
                    "total_spent_usd": new_spent,
                },
            )
            
            self.logger.info(
                "task_completed",
                agent_id=agent_id,
                cost_usd=cost_usd,
                total_spent=new_spent,
            )
            
            return agent
            
        except Exception as e:
            self.logger.error("complete_task_failed", error=str(e), agent_id=agent_id)
            raise
    
    async def stop_agent(
        self,
        session: AsyncSession,
        agent_id: str,
    ) -> Optional[Agent]:
        """Stop an agent (transition to PAUSED)"""
        try:
            agent = await agent_registry.update_agent(
                session,
                agent_id,
                status=AgentStatus.PAUSED,
            )
            
            if agent:
                await self._publish_event(
                    event_type="agent.stopped",
                    agent_id=agent_id,
                    tenant_id=agent.tenant_id,
                    payload={"status": AgentStatus.PAUSED.value},
                )
                
                self.logger.info("agent_stopped", agent_id=agent_id)
            
            return agent
            
        except Exception as e:
            self.logger.error("stop_agent_failed", error=str(e), agent_id=agent_id)
            raise
    
    async def terminate_agent(
        self,
        session: AsyncSession,
        agent_id: str,
        reason: str = "manual",
    ) -> bool:
        """Terminate an agent"""
        try:
            agent = await agent_registry.get_agent(session, agent_id)
            if not agent:
                return False
            
            # Update to TERMINATED status first
            await agent_registry.update_agent(
                session,
                agent_id,
                status=AgentStatus.TERMINATED,
            )
            
            # Publish event
            await self._publish_event(
                event_type="agent.terminated",
                agent_id=agent_id,
                tenant_id=agent.tenant_id,
                payload={
                    "reason": reason,
                    "total_spent_usd": agent.spent_usd,
                },
            )
            
            # Deregister agent
            deleted = await agent_registry.deregister_agent(session, agent_id)
            
            self.logger.info(
                "agent_terminated",
                agent_id=agent_id,
                reason=reason,
                deleted=deleted,
            )
            
            return deleted
            
        except Exception as e:
            self.logger.error("terminate_agent_failed", error=str(e), agent_id=agent_id)
            raise
    
    async def check_agent_health(
        self,
        session: AsyncSession,
        agent_id: str,
    ) -> bool:
        """Check if agent is healthy"""
        try:
            agent = await agent_registry.get_agent(session, agent_id)
            if not agent:
                return False
            
            # Check last activity
            idle_time = (datetime.utcnow() - agent.last_active_at).total_seconds()
            if idle_time > settings.AGENT_IDLE_TIMEOUT_SECONDS:
                self.logger.warning(
                    "agent_idle_timeout",
                    agent_id=agent_id,
                    idle_seconds=idle_time,
                )
                return False
            
            # Check budget
            if agent.spent_usd > agent.budget_ceiling_usd:
                self.logger.warning(
                    "agent_budget_exceeded",
                    agent_id=agent_id,
                    spent=agent.spent_usd,
                    ceiling=agent.budget_ceiling_usd,
                )
                return False
            
            return True
            
        except Exception as e:
            self.logger.error("check_agent_health_failed", error=str(e), agent_id=agent_id)
            return False
    
    async def evaluate_survival_pressure(
        self,
        session: AsyncSession,
        agent_id: str,
    ) -> bool:
        """
        Automaton-style economic survival pressure evaluation.
        Returns True if agent passes survival check, False if it should be terminated.
        """
        try:
            agent = await agent_registry.get_agent(session, agent_id)
            if not agent:
                return False
            
            # Skip survival pressure for agents that haven't spent much yet
            if agent.spent_usd < agent.budget_ceiling_usd * 0.1:
                return True
            
            # Calculate ROI: Value generated vs Cost spent
            value_generated = await self._get_agent_revenue(agent.tenant_id, agent_id)
            
            # Calculate ROI
            roi = value_generated / agent.spent_usd if agent.spent_usd > 0 else 0
            
            # Survival threshold: Agent must generate at least 80% of what it costs
            # when it has spent 80% or more of its budget
            survival_threshold = 0.8
            budget_usage_ratio = agent.spent_usd / agent.budget_ceiling_usd
            
            if budget_usage_ratio >= 0.8 and roi < survival_threshold:
                self.logger.warning(
                    "agent_failed_survival_pressure",
                    agent_id=agent_id,
                    roi=roi,
                    value_generated=value_generated,
                    spent=agent.spent_usd,
                    budget_usage_ratio=budget_usage_ratio,
                    survival_threshold=survival_threshold,
                )
                return False
            
            self.logger.info(
                "agent_survival_check_passed",
                agent_id=agent_id,
                roi=roi,
                value_generated=value_generated,
                spent=agent.spent_usd,
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "evaluate_survival_pressure_failed",
                error=str(e),
                agent_id=agent_id,
            )
            # Fail open: don't terminate on evaluation errors
            return True
    
    async def _get_agent_revenue(self, tenant_id: str, agent_id: str) -> float:
        """
        Get the revenue/value generated by an agent from the economics service.
        This is a placeholder that queries the economics service for agent-specific metrics.
        """
        if not self._economics_client:
            # If economics client not configured, return 0 (conservative)
            return 0.0
        
        try:
            response = await self._economics_client.get(
                f"/api/v1/economics/agent-revenue/{tenant_id}/{agent_id}"
            )
            if response.status_code == 200:
                data = response.json()
                return float(data.get("total_revenue_usd", 0.0))
            else:
                self.logger.warning(
                    "failed_to_fetch_agent_revenue",
                    status_code=response.status_code,
                    agent_id=agent_id,
                )
                return 0.0
        except Exception as e:
            self.logger.error(
                "get_agent_revenue_error",
                error=str(e),
                agent_id=agent_id,
            )
            return 0.0
    
    async def start_monitoring(self, session_factory):
        """Start background monitoring task"""
        if self._monitoring_task is not None:
            return
        
        self._monitoring_task = asyncio.create_task(
            self._monitor_agents(session_factory)
        )
        self.logger.info("agent_monitoring_started")
    
    async def stop_monitoring(self):
        """Stop background monitoring task"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            self.logger.info("agent_monitoring_stopped")
    
    async def _monitor_agents(self, session_factory):
        """Background task to monitor agent health and survival pressure"""
        while True:
            try:
                async with session_factory() as session:
                    # Get all active agents
                    agents = await agent_registry.list_agents(
                        session,
                        tenant_id="*",  # Monitor all tenants
                        limit=1000,
                    )
                    
                    for agent in agents:
                        if agent.status in [AgentStatus.TERMINATED]:
                            continue
                        
                        # Check health
                        is_healthy = await self.check_agent_health(session, agent.agent_id)
                        
                        if not is_healthy:
                            # Terminate unhealthy agent
                            self.logger.warning(
                                "terminating_unhealthy_agent",
                                agent_id=agent.agent_id,
                            )
                            await self.terminate_agent(
                                session,
                                agent.agent_id,
                                reason="health_check_failed",
                            )
                            continue
                        
                        # Automaton-style survival pressure check
                        survives = await self.evaluate_survival_pressure(session, agent.agent_id)
                        
                        if not survives:
                            # Terminate agent that failed economic survival pressure
                            self.logger.warning(
                                "terminating_agent_economic_failure",
                                agent_id=agent.agent_id,
                            )
                            await self.terminate_agent(
                                session,
                                agent.agent_id,
                                reason="economic_survival_failure",
                            )
                    
                    await session.commit()
                
            except Exception as e:
                self.logger.error("monitoring_error", error=str(e))
            
            await asyncio.sleep(settings.HEALTH_CHECK_INTERVAL_SECONDS)
    
    async def _publish_event(
        self,
        event_type: str,
        agent_id: str,
        tenant_id: str,
        payload: dict,
    ):
        """Publish agent event to Kafka"""
        if not self._kafka_producer:
            return
        
        try:
            event = AgentEvent(
                event_type=event_type,
                agent_id=agent_id,
                tenant_id=tenant_id,
                timestamp=datetime.utcnow(),
                payload=payload,
            )
            
            await self._kafka_producer.send_event(
                topic=settings.KAFKA_TOPIC_AGENTS,
                event_type=event_type,
                payload=event.dict(),
            )
            
        except Exception as e:
            self.logger.error(
                "publish_event_failed",
                error=str(e),
                event_type=event_type,
                agent_id=agent_id,
            )


# Global lifecycle manager instance
lifecycle_manager = LifecycleManager()


# Made with Bob