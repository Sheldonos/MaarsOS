"""
Budget enforcement for vessel-economics service.
Enforces budget limits, generates alerts, and prevents budget overruns.
"""

import logging
from typing import Optional, Tuple
from datetime import datetime
from decimal import Decimal
import uuid
from contextlib import asynccontextmanager

from .database import db_manager
from .models import (
    BudgetLimit, BudgetCheckRequest, BudgetCheckResponse,
    BudgetEnforceRequest, BudgetStatus, EscrowTransaction,
    TransactionType, TransactionStatus, EscrowReleaseRequest
)
from .config import settings
from .kafka_producer import kafka_producer

logger = logging.getLogger(__name__)


class BudgetEnforcer:
    """Enforces budget limits and generates alerts."""
    
    def __init__(self):
        """Initialize budget enforcer."""
        self.db = db_manager
        self._escrow_manager = None
    
    @property
    def escrow_manager(self):
        """Lazy load escrow manager to avoid circular import."""
        if self._escrow_manager is None:
            from .escrow import escrow_manager
            self._escrow_manager = escrow_manager
        return self._escrow_manager
        
    async def check_budget(
        self,
        request: BudgetCheckRequest
    ) -> BudgetCheckResponse:
        """
        Check if budget is available for a task.
        
        Args:
            request: Budget check request
            
        Returns:
            Budget check response with availability status
        """
        try:
            # Get budget limit
            budget = await self.db.get_budget_limit(request.tenant_id)
            
            if not budget:
                # Create default budget if not exists
                budget = await self._create_default_budget(request.tenant_id)
                
            # Calculate remaining budget
            remaining = budget.remaining_budget
            remaining_after = remaining - request.estimated_cost
            
            # Determine budget status
            usage_percentage = (budget.used_budget / budget.total_budget) if budget.total_budget > 0 else Decimal("0")
            
            if usage_percentage >= budget.critical_threshold:
                status = BudgetStatus.CRITICAL
            elif usage_percentage >= budget.warning_threshold:
                status = BudgetStatus.WARNING
            elif usage_percentage >= Decimal("1.0"):
                status = BudgetStatus.EXHAUSTED
            else:
                status = BudgetStatus.HEALTHY
                
            # Check availability
            available = remaining_after >= Decimal("0")
            
            # Generate message
            message = None
            if not available:
                message = (
                    f"Insufficient budget. Required: ${request.estimated_cost}, "
                    f"Available: ${remaining}"
                )
            elif status == BudgetStatus.CRITICAL:
                message = f"Budget critical: {usage_percentage * 100:.1f}% used"
            elif status == BudgetStatus.WARNING:
                message = f"Budget warning: {usage_percentage * 100:.1f}% used"
                
            response = BudgetCheckResponse(
                tenant_id=request.tenant_id,
                available=available,
                current_balance=remaining,
                estimated_cost=request.estimated_cost,
                remaining_after=remaining_after,
                budget_status=status,
                message=message
            )
            
            logger.info(
                f"Budget check for tenant {request.tenant_id}: "
                f"available={available}, status={status.value}, "
                f"remaining=${remaining}"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to check budget: {e}")
            raise ValueError(f"Budget check failed: {str(e)}")
            
    async def enforce_budget(
        self,
        request: BudgetEnforceRequest
    ) -> Tuple[bool, str]:
        """
        Enforce budget limits before task execution.
        
        Args:
            request: Budget enforcement request
            
        Returns:
            Tuple of (allowed, message)
        """
        try:
            # Get budget limit
            budget = await self.db.get_budget_limit(request.tenant_id)
            
            if not budget:
                budget = await self._create_default_budget(request.tenant_id)
                
            # Check if hard limits are enabled
            if not budget.hard_limit_enabled and not request.force:
                logger.info(
                    f"Hard limits disabled for tenant {request.tenant_id}, "
                    f"allowing task {request.task_id}"
                )
                return True, "Hard limits disabled"
                
            # Check budget availability
            remaining = budget.remaining_budget
            
            if remaining < request.estimated_cost:
                if request.force:
                    logger.warning(
                        f"Budget exceeded but forced execution for task {request.task_id} "
                        f"(tenant: {request.tenant_id})"
                    )
                    return True, "Forced execution despite budget exceeded"
                    
                # Budget exceeded - reject task
                message = (
                    f"Budget exceeded. Required: ${request.estimated_cost}, "
                    f"Available: ${remaining}"
                )
                
                # Publish budget exceeded event
                await kafka_producer.publish_event(
                    "budget.exceeded",
                    {
                        "tenant_id": request.tenant_id,
                        "task_id": request.task_id,
                        "estimated_cost": str(request.estimated_cost),
                        "available_budget": str(remaining),
                        "total_budget": str(budget.total_budget),
                        "used_budget": str(budget.used_budget)
                    }
                )
                
                logger.warning(
                    f"Budget exceeded for tenant {request.tenant_id}, "
                    f"rejecting task {request.task_id}"
                )
                
                return False, message
                
            # Check for alerts
            usage_percentage = (budget.used_budget / budget.total_budget) if budget.total_budget > 0 else Decimal("0")
            
            if usage_percentage >= budget.critical_threshold:
                await self._send_budget_alert(
                    request.tenant_id,
                    BudgetStatus.CRITICAL,
                    usage_percentage,
                    budget
                )
            elif usage_percentage >= budget.warning_threshold:
                await self._send_budget_alert(
                    request.tenant_id,
                    BudgetStatus.WARNING,
                    usage_percentage,
                    budget
                )
                
            return True, "Budget available"
            
        except Exception as e:
            logger.error(f"Failed to enforce budget: {e}")
            raise ValueError(f"Budget enforcement failed: {str(e)}")
            
    async def get_budget_status(self, tenant_id: str) -> BudgetLimit:
        """
        Get budget status for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Budget limit information
        """
        budget = await self.db.get_budget_limit(tenant_id)
        
        if not budget:
            budget = await self._create_default_budget(tenant_id)
            
        return budget
        
    async def set_budget_limit(
        self,
        tenant_id: str,
        total_budget: Decimal,
        warning_threshold: Optional[Decimal] = None,
        critical_threshold: Optional[Decimal] = None,
        hard_limit_enabled: bool = True,
        soft_limit_enabled: bool = True
    ) -> BudgetLimit:
        """
        Set or update budget limit for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            total_budget: Total budget in USD
            warning_threshold: Warning threshold (default from config)
            critical_threshold: Critical threshold (default from config)
            hard_limit_enabled: Enable hard limits
            soft_limit_enabled: Enable soft limits
            
        Returns:
            Updated budget limit
        """
        try:
            # Get existing budget or create new
            existing = await self.db.get_budget_limit(tenant_id)
            
            now = datetime.utcnow()
            
            budget = BudgetLimit(
                tenant_id=tenant_id,
                total_budget=total_budget,
                used_budget=existing.used_budget if existing else Decimal("0"),
                remaining_budget=total_budget - (existing.used_budget if existing else Decimal("0")),
                warning_threshold=warning_threshold or settings.budget_warning_threshold,
                critical_threshold=critical_threshold or settings.budget_critical_threshold,
                hard_limit_enabled=hard_limit_enabled,
                soft_limit_enabled=soft_limit_enabled,
                status=BudgetStatus.HEALTHY,
                last_alert_at=existing.last_alert_at if existing else None,
                created_at=existing.created_at if existing else now,
                updated_at=now
            )
            
            # Update status based on usage
            usage_percentage = (budget.used_budget / budget.total_budget) if budget.total_budget > 0 else Decimal("0")
            
            if usage_percentage >= Decimal("1.0"):
                budget.status = BudgetStatus.EXHAUSTED
            elif usage_percentage >= budget.critical_threshold:
                budget.status = BudgetStatus.CRITICAL
            elif usage_percentage >= budget.warning_threshold:
                budget.status = BudgetStatus.WARNING
            else:
                budget.status = BudgetStatus.HEALTHY
                
            # Save to database
            await self.db.create_budget_limit(budget)
            
            logger.info(
                f"Set budget limit for tenant {tenant_id}: "
                f"total=${total_budget}, status={budget.status.value}"
            )
            
            return budget
            
        except Exception as e:
            logger.error(f"Failed to set budget limit: {e}")
            raise ValueError(f"Budget limit update failed: {str(e)}")
            
    async def reset_budget(self, tenant_id: str) -> BudgetLimit:
        """
        Reset budget usage for a tenant (new billing period).
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Updated budget limit
        """
        try:
            budget = await self.db.get_budget_limit(tenant_id)
            
            if not budget:
                raise ValueError(f"Budget not found for tenant {tenant_id}")
                
            # Reset used budget
            budget.used_budget = Decimal("0")
            budget.remaining_budget = budget.total_budget
            budget.status = BudgetStatus.HEALTHY
            budget.updated_at = datetime.utcnow()
            
            # Save to database
            await self.db.create_budget_limit(budget)
            
            logger.info(f"Reset budget for tenant {tenant_id}")
            
            return budget
            
        except Exception as e:
            logger.error(f"Failed to reset budget: {e}")
            raise ValueError(f"Budget reset failed: {str(e)}")
            
    async def _create_default_budget(self, tenant_id: str) -> BudgetLimit:
        """Create default budget for a tenant."""
        now = datetime.utcnow()
        
        budget = BudgetLimit(
            tenant_id=tenant_id,
            total_budget=settings.default_tenant_budget,
            used_budget=Decimal("0"),
            remaining_budget=settings.default_tenant_budget,
            warning_threshold=settings.budget_warning_threshold,
            critical_threshold=settings.budget_critical_threshold,
            hard_limit_enabled=settings.enable_hard_limits,
            soft_limit_enabled=settings.enable_soft_limits,
            status=BudgetStatus.HEALTHY,
            created_at=now,
            updated_at=now
        )
        
        await self.db.create_budget_limit(budget)
        
        logger.info(
            f"Created default budget for tenant {tenant_id}: "
            f"${settings.default_tenant_budget}"
        )
        
        return budget
        
    async def _send_budget_alert(
        self,
        tenant_id: str,
        status: BudgetStatus,
        usage_percentage: Decimal,
        budget: BudgetLimit
    ):
        """Send budget alert if threshold crossed."""
        try:
            # Check if we should send alert (avoid spam)
            if budget.last_alert_at:
                # Only send alert once per hour
                time_since_last = datetime.utcnow() - budget.last_alert_at
                if time_since_last.total_seconds() < 3600:
                    return
                    
            # Publish alert event
            await kafka_producer.publish_event(
                "budget.alert",
                {
                    "tenant_id": tenant_id,
                    "status": status.value,
                    "usage_percentage": str(usage_percentage * 100),
                    "used_budget": str(budget.used_budget),
                    "total_budget": str(budget.total_budget),
                    "remaining_budget": str(budget.remaining_budget)
                }
            )
            
            # Update last alert time
            budget.last_alert_at = datetime.utcnow()
            await self.db.create_budget_limit(budget)
            
            logger.warning(
                f"Budget alert for tenant {tenant_id}: "
                f"status={status.value}, usage={usage_percentage * 100:.1f}%"
            )
            
        except Exception as e:
            logger.error(f"Failed to send budget alert: {e}")
            
    async def get_budget_utilization(
        self,
        tenant_id: str
    ) -> dict:
        """
        Get detailed budget utilization metrics.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dictionary with utilization metrics
        """
        try:
            budget = await self.db.get_budget_limit(tenant_id)
            
            if not budget:
                budget = await self._create_default_budget(tenant_id)
                
            usage_percentage = (budget.used_budget / budget.total_budget) if budget.total_budget > 0 else Decimal("0")
            
            return {
                "tenant_id": tenant_id,
                "total_budget": str(budget.total_budget),
                "used_budget": str(budget.used_budget),
                "remaining_budget": str(budget.remaining_budget),
                "usage_percentage": str(usage_percentage * 100),
                "status": budget.status.value,
                "warning_threshold": str(budget.warning_threshold * 100),
                "critical_threshold": str(budget.critical_threshold * 100),
                "hard_limit_enabled": budget.hard_limit_enabled,
                "soft_limit_enabled": budget.soft_limit_enabled,
                "last_alert_at": budget.last_alert_at.isoformat() if budget.last_alert_at else None,
                "updated_at": budget.updated_at.isoformat()
            }
    @asynccontextmanager
    async def atomic_task_checkout(
        self,
        tenant_id: str,
        task_id: str,
        estimated_cost: Decimal,
        agent_id: Optional[str] = None
    ):
        """
        Paperclip-style atomic budget checkout.
        Locks funds before execution and commits/rolls back after.
        
        This ensures that:
        1. Funds are reserved before task execution
        2. Funds are automatically released on success
        3. Funds are automatically refunded on failure
        4. No fund leaks occur regardless of exit path
        
        Usage:
            async with budget_enforcer.atomic_task_checkout(
                tenant_id="tenant-123",
                task_id="task-456",
                estimated_cost=Decimal("0.50")
            ) as lock_tx:
                # Execute task here
                # Funds are locked during execution
                result = await execute_task()
                # Funds automatically released on success
        
        Args:
            tenant_id: Tenant identifier
            task_id: Task identifier
            estimated_cost: Estimated cost in USD
            agent_id: Optional agent identifier
            
        Yields:
            EscrowTransaction: The lock transaction
            
        Raises:
            ValueError: If budget check fails or insufficient funds
        """
        lock_tx = None
        
        try:
            # Step 1: Pre-execution budget check
            check_req = BudgetCheckRequest(
                tenant_id=tenant_id,
                estimated_cost=estimated_cost
            )
            check_res = await self.check_budget(check_req)
            
            if not check_res.available:
                raise ValueError(
                    f"Budget exhausted: {check_res.message}. "
                    f"Available: ${check_res.current_balance}, Required: ${estimated_cost}"
                )
            
            # Step 2: Lock funds atomically
            lock_tx = await self.escrow_manager.lock_funds(
                tenant_id=tenant_id,
                amount=estimated_cost,
                task_id=task_id,
                agent_id=agent_id,
                description=f"Atomic checkout for task {task_id}"
            )
            
            logger.info(
                f"Atomic checkout: Locked ${estimated_cost} for task {task_id} "
                f"(tenant: {tenant_id}, tx: {lock_tx.transaction_id})"
            )
            
            # Step 3: Yield control to task execution
            yield lock_tx
            
            # Step 4: Post-execution (Success path) - Release and commit spend
            await self.escrow_manager.release_funds(
                EscrowReleaseRequest(
                    tenant_id=tenant_id,
                    transaction_id=lock_tx.transaction_id,
                    amount=estimated_cost,
                    reason=f"Task {task_id} completed successfully"
                )
            )
            
            # Update budget usage
            budget = await self.db.get_budget_limit(tenant_id)
            if budget:
                budget.used_budget += estimated_cost
                budget.remaining_budget -= estimated_cost
                budget.updated_at = datetime.utcnow()
                await self.db.create_budget_limit(budget)
            
            logger.info(
                f"Atomic checkout: Released ${estimated_cost} for task {task_id} "
                f"(tenant: {tenant_id})"
            )
            
        except Exception as e:
            # Step 5: Post-execution (Failure path) - Rollback the lock
            if lock_tx:
                try:
                    await self.escrow_manager.refund_funds(
                        tenant_id=tenant_id,
                        transaction_id=lock_tx.transaction_id,
                        reason=f"Task {task_id} failed: {str(e)}"
                    )
                    
                    logger.warning(
                        f"Atomic checkout: Refunded ${estimated_cost} for failed task {task_id} "
                        f"(tenant: {tenant_id})"
                    )
                except Exception as refund_error:
                    logger.error(
                        f"Failed to refund locked funds for task {task_id}: {refund_error}. "
                        f"Manual intervention may be required for transaction {lock_tx.transaction_id}"
                    )
            
            # Re-raise the original exception
            raise e

            
        except Exception as e:
            logger.error(f"Failed to get budget utilization: {e}")
            raise ValueError(f"Budget utilization retrieval failed: {str(e)}")


# Global budget enforcer instance
budget_enforcer = BudgetEnforcer()

# Made with Bob
