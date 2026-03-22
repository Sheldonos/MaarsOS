"""
Cost tracking for vessel-economics service.
Tracks LLM API costs, compute costs, and aggregates by various dimensions.
"""

import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from .database import db_manager
from .models import (
    CostRecord, CostTrackRequest, CostSummary, CostCategory
)
from .config import settings
from .kafka_producer import kafka_producer

logger = logging.getLogger(__name__)


class CostTracker:
    """Tracks and aggregates costs across the platform."""
    
    # Cost models per 1K tokens (loaded from config)
    COST_MODELS = {
        "openai": {
            "gpt-4": {
                "input": settings.openai_gpt4_input_cost,
                "output": settings.openai_gpt4_output_cost
            },
            "gpt-4-turbo": {
                "input": settings.openai_gpt4_turbo_input_cost,
                "output": settings.openai_gpt4_turbo_output_cost
            },
            "gpt-3.5-turbo": {
                "input": settings.openai_gpt35_turbo_input_cost,
                "output": settings.openai_gpt35_turbo_output_cost
            }
        },
        "anthropic": {
            "claude-3-opus": {
                "input": settings.anthropic_claude3_opus_input_cost,
                "output": settings.anthropic_claude3_opus_output_cost
            },
            "claude-3-sonnet": {
                "input": settings.anthropic_claude3_sonnet_input_cost,
                "output": settings.anthropic_claude3_sonnet_output_cost
            },
            "claude-3-haiku": {
                "input": settings.anthropic_claude3_haiku_input_cost,
                "output": settings.anthropic_claude3_haiku_output_cost
            },
            "claude-2": {
                "input": settings.anthropic_claude2_input_cost,
                "output": settings.anthropic_claude2_output_cost
            }
        },
        "google": {
            "palm-2": {
                "input": settings.google_palm2_input_cost,
                "output": settings.google_palm2_output_cost
            }
        }
    }
    
    def __init__(self):
        """Initialize cost tracker."""
        self.db = db_manager
        
    def calculate_llm_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> Decimal:
        """
        Calculate LLM API cost based on token usage.
        
        Args:
            provider: Provider name (openai, anthropic, google)
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Total cost in USD
        """
        try:
            provider_lower = provider.lower()
            model_lower = model.lower()
            
            # Get cost model
            if provider_lower not in self.COST_MODELS:
                logger.warning(f"Unknown provider: {provider}, using default rates")
                input_cost_per_1k = Decimal("0.001")
                output_cost_per_1k = Decimal("0.002")
            else:
                provider_models = self.COST_MODELS[provider_lower]
                
                # Find matching model (exact or partial match)
                model_costs = None
                for model_key, costs in provider_models.items():
                    if model_key in model_lower or model_lower in model_key:
                        model_costs = costs
                        break
                        
                if not model_costs:
                    logger.warning(f"Unknown model: {model} for provider {provider}, using default rates")
                    input_cost_per_1k = Decimal("0.001")
                    output_cost_per_1k = Decimal("0.002")
                else:
                    input_cost_per_1k = model_costs["input"]
                    output_cost_per_1k = model_costs["output"]
                    
            # Calculate cost
            input_cost = (Decimal(input_tokens) / Decimal("1000")) * input_cost_per_1k
            output_cost = (Decimal(output_tokens) / Decimal("1000")) * output_cost_per_1k
            total_cost = input_cost + output_cost
            
            logger.debug(
                f"Calculated cost for {provider}/{model}: "
                f"input={input_tokens} tokens (${input_cost}), "
                f"output={output_tokens} tokens (${output_cost}), "
                f"total=${total_cost}"
            )
            
            return total_cost
            
        except Exception as e:
            logger.error(f"Failed to calculate LLM cost: {e}")
            # Return conservative estimate
            return Decimal("0.01")
            
    async def track_cost(self, request: CostTrackRequest) -> CostRecord:
        """
        Track a cost record.
        
        Args:
            request: Cost tracking request
            
        Returns:
            Created cost record
        """
        try:
            # Calculate cost if not provided (for LLM API calls)
            cost = request.cost
            if (request.category == CostCategory.LLM_API and 
                request.provider and request.model and 
                request.input_tokens is not None and 
                request.output_tokens is not None):
                
                calculated_cost = self.calculate_llm_cost(
                    request.provider,
                    request.model,
                    request.input_tokens,
                    request.output_tokens
                )
                
                # Use calculated cost if not provided or if calculated is higher
                if cost == Decimal("0") or calculated_cost > cost:
                    cost = calculated_cost
                    
            # Create cost record
            cost_record = CostRecord(
                cost_id=str(uuid.uuid4()),
                tenant_id=request.tenant_id,
                task_id=request.task_id,
                agent_id=request.agent_id,
                category=request.category,
                provider=request.provider,
                model=request.model,
                input_tokens=request.input_tokens,
                output_tokens=request.output_tokens,
                cost=cost,
                metadata=request.metadata or {},
                created_at=datetime.utcnow()
            )
            
            # Save to database
            await self.db.create_cost_record(cost_record)
            
            # Update budget usage
            await self.db.update_budget_usage(request.tenant_id, cost)
            
            # Publish event
            await kafka_producer.publish_event(
                "cost.tracked",
                {
                    "cost_id": cost_record.cost_id,
                    "tenant_id": request.tenant_id,
                    "task_id": request.task_id,
                    "category": request.category.value,
                    "cost": str(cost),
                    "provider": request.provider,
                    "model": request.model
                }
            )
            
            logger.info(
                f"Tracked cost ${cost} for task {request.task_id} "
                f"(tenant: {request.tenant_id}, category: {request.category.value})"
            )
            
            return cost_record
            
        except Exception as e:
            logger.error(f"Failed to track cost: {e}")
            raise ValueError(f"Cost tracking failed: {str(e)}")
            
    async def get_cost_summary(
        self,
        tenant_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> CostSummary:
        """
        Get cost summary with aggregations.
        
        Args:
            tenant_id: Optional tenant filter
            agent_id: Optional agent filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Cost summary with aggregations
        """
        try:
            # Get cost records
            if tenant_id:
                costs = await self.db.get_costs_by_tenant(tenant_id, start_date, end_date)
            else:
                # Get all costs (admin view)
                costs = []
                # This would need a separate method in database.py
                # For now, we'll just return empty if no tenant specified
                
            # Filter by agent if specified
            if agent_id:
                costs = [c for c in costs if c.agent_id == agent_id]
                
            # Calculate aggregations
            total_cost = Decimal("0")
            total_tasks = len(set(c.task_id for c in costs))
            cost_by_category: Dict[str, Decimal] = {}
            cost_by_provider: Dict[str, Decimal] = {}
            cost_by_model: Dict[str, Decimal] = {}
            total_input_tokens = 0
            total_output_tokens = 0
            
            for cost in costs:
                total_cost += cost.cost
                
                # By category
                category_key = cost.category.value
                cost_by_category[category_key] = cost_by_category.get(category_key, Decimal("0")) + cost.cost
                
                # By provider
                if cost.provider:
                    cost_by_provider[cost.provider] = cost_by_provider.get(cost.provider, Decimal("0")) + cost.cost
                    
                # By model
                if cost.model:
                    cost_by_model[cost.model] = cost_by_model.get(cost.model, Decimal("0")) + cost.cost
                    
                # Token counts
                if cost.input_tokens:
                    total_input_tokens += cost.input_tokens
                if cost.output_tokens:
                    total_output_tokens += cost.output_tokens
                    
            summary = CostSummary(
                tenant_id=tenant_id,
                agent_id=agent_id,
                total_cost=total_cost,
                total_tasks=total_tasks,
                cost_by_category=cost_by_category,
                cost_by_provider=cost_by_provider,
                cost_by_model=cost_by_model,
                total_input_tokens=total_input_tokens,
                total_output_tokens=total_output_tokens,
                period_start=start_date,
                period_end=end_date
            )
            
            logger.info(
                f"Generated cost summary: tenant={tenant_id}, agent={agent_id}, "
                f"total_cost=${total_cost}, tasks={total_tasks}"
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate cost summary: {e}")
            raise ValueError(f"Cost summary generation failed: {str(e)}")
            
    async def get_costs_by_tenant(
        self,
        tenant_id: str,
        days: int = 30
    ) -> list[CostRecord]:
        """
        Get cost records for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            days: Number of days to look back
            
        Returns:
            List of cost records
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        return await self.db.get_costs_by_tenant(tenant_id, start_date)
        
    async def get_costs_by_agent(
        self,
        agent_id: str,
        days: int = 30
    ) -> list[CostRecord]:
        """
        Get cost records for an agent.
        
        Args:
            agent_id: Agent identifier
            days: Number of days to look back
            
        Returns:
            List of cost records
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        # This would need filtering in the database query
        # For now, we'll get all costs and filter
        costs = await self.db.get_costs_by_tenant("", start_date)
        return [c for c in costs if c.agent_id == agent_id]
        
    async def estimate_task_cost(
        self,
        provider: str,
        model: str,
        estimated_input_tokens: int,
        estimated_output_tokens: int
    ) -> Decimal:
        """
        Estimate cost for a task before execution.
        
        Args:
            provider: Provider name
            model: Model name
            estimated_input_tokens: Estimated input tokens
            estimated_output_tokens: Estimated output tokens
            
        Returns:
            Estimated cost in USD
        """
        return self.calculate_llm_cost(
            provider,
            model,
            estimated_input_tokens,
            estimated_output_tokens
        )
        
    async def get_top_cost_drivers(
        self,
        tenant_id: str,
        limit: int = 10,
        days: int = 30
    ) -> Dict[str, any]:
        """
        Get top cost drivers for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            limit: Number of top items to return
            days: Number of days to analyze
            
        Returns:
            Dictionary with top cost drivers
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            costs = await self.db.get_costs_by_tenant(tenant_id, start_date)
            
            # Aggregate by different dimensions
            by_task: Dict[str, Decimal] = {}
            by_agent: Dict[str, Decimal] = {}
            by_model: Dict[str, Decimal] = {}
            
            for cost in costs:
                # By task
                by_task[cost.task_id] = by_task.get(cost.task_id, Decimal("0")) + cost.cost
                
                # By agent
                if cost.agent_id:
                    by_agent[cost.agent_id] = by_agent.get(cost.agent_id, Decimal("0")) + cost.cost
                    
                # By model
                if cost.model:
                    by_model[cost.model] = by_model.get(cost.model, Decimal("0")) + cost.cost
                    
            # Sort and get top items
            top_tasks = sorted(by_task.items(), key=lambda x: x[1], reverse=True)[:limit]
            top_agents = sorted(by_agent.items(), key=lambda x: x[1], reverse=True)[:limit]
            top_models = sorted(by_model.items(), key=lambda x: x[1], reverse=True)[:limit]
            
            return {
                "top_tasks": [{"task_id": k, "cost": str(v)} for k, v in top_tasks],
                "top_agents": [{"agent_id": k, "cost": str(v)} for k, v in top_agents],
                "top_models": [{"model": k, "cost": str(v)} for k, v in top_models],
                "period_days": days,
                "total_costs_analyzed": len(costs)
            }
            
        except Exception as e:
            logger.error(f"Failed to get top cost drivers: {e}")
            raise ValueError(f"Cost driver analysis failed: {str(e)}")
            
    async def get_cost_trends(
        self,
        tenant_id: str,
        days: int = 30,
        interval: str = "day"
    ) -> Dict[str, any]:
        """
        Get cost trends over time.
        
        Args:
            tenant_id: Tenant identifier
            days: Number of days to analyze
            interval: Aggregation interval (day, week, month)
            
        Returns:
            Dictionary with cost trends
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            costs = await self.db.get_costs_by_tenant(tenant_id, start_date)
            
            # Aggregate by time interval
            trends: Dict[str, Decimal] = {}
            
            for cost in costs:
                if interval == "day":
                    key = cost.created_at.strftime("%Y-%m-%d")
                elif interval == "week":
                    key = cost.created_at.strftime("%Y-W%W")
                elif interval == "month":
                    key = cost.created_at.strftime("%Y-%m")
                else:
                    key = cost.created_at.strftime("%Y-%m-%d")
                    
                trends[key] = trends.get(key, Decimal("0")) + cost.cost
                
            # Sort by date
            sorted_trends = sorted(trends.items())
            
            return {
                "trends": [{"period": k, "cost": str(v)} for k, v in sorted_trends],
                "interval": interval,
                "period_days": days,
                "total_periods": len(sorted_trends)
            }
            
        except Exception as e:
            logger.error(f"Failed to get cost trends: {e}")
            raise ValueError(f"Cost trend analysis failed: {str(e)}")


# Global cost tracker instance
cost_tracker = CostTracker()

# Made with Bob
