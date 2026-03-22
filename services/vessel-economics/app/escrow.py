"""
Escrow management for vessel-economics service.
Handles budget allocation, fund locking, and transaction management.
"""

import logging
from typing import Optional
from datetime import datetime
from decimal import Decimal
import uuid

from .database import db_manager
from .models import (
    EscrowAccount, EscrowTransaction, EscrowAllocateRequest,
    EscrowReleaseRequest, TransactionType, TransactionStatus
)
from .kafka_producer import kafka_producer

logger = logging.getLogger(__name__)


class EscrowManager:
    """Manages escrow accounts and transactions."""
    
    def __init__(self):
        """Initialize escrow manager."""
        self.db = db_manager
        
    async def allocate_budget(
        self,
        request: EscrowAllocateRequest
    ) -> EscrowTransaction:
        """
        Allocate budget to escrow account.
        
        Args:
            request: Allocation request
            
        Returns:
            EscrowTransaction: Created transaction
            
        Raises:
            ValueError: If allocation fails
        """
        try:
            # Get or create escrow account
            account = await self.db.get_escrow_account(request.tenant_id)
            if not account:
                account = await self.db.create_escrow_account(request.tenant_id)
                
            # Create transaction
            transaction = EscrowTransaction(
                transaction_id=str(uuid.uuid4()),
                tenant_id=request.tenant_id,
                transaction_type=TransactionType.ALLOCATE,
                amount=request.amount,
                status=TransactionStatus.PENDING,
                description=request.description or f"Budget allocation of ${request.amount}",
                metadata=request.metadata,
                created_at=datetime.utcnow()
            )
            
            # Save transaction
            await self.db.create_transaction(transaction)
            
            # Update account balance
            await self.db.update_escrow_balance(
                request.tenant_id,
                request.amount,
                operation="add"
            )
            
            # Update transaction status
            transaction.status = TransactionStatus.COMPLETED
            transaction.completed_at = datetime.utcnow()
            
            # Publish event
            await kafka_producer.publish_event(
                "escrow.allocated",
                {
                    "transaction_id": transaction.transaction_id,
                    "tenant_id": request.tenant_id,
                    "amount": str(request.amount),
                    "balance": str((await self.db.get_escrow_account(request.tenant_id)).balance)
                }
            )
            
            logger.info(
                f"Allocated ${request.amount} to escrow for tenant {request.tenant_id}. "
                f"Transaction: {transaction.transaction_id}"
            )
            
            return transaction
            
        except Exception as e:
            logger.error(f"Failed to allocate budget: {e}")
            raise ValueError(f"Budget allocation failed: {str(e)}")
            
    async def lock_funds(
        self,
        tenant_id: str,
        amount: Decimal,
        task_id: str,
        agent_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> EscrowTransaction:
        """
        Lock funds for task execution.
        
        Args:
            tenant_id: Tenant identifier
            amount: Amount to lock
            task_id: Task identifier
            agent_id: Optional agent identifier
            description: Optional description
            
        Returns:
            EscrowTransaction: Created transaction
            
        Raises:
            ValueError: If insufficient funds or lock fails
        """
        try:
            # Check available balance
            account = await self.db.get_escrow_account(tenant_id)
            if not account:
                raise ValueError(f"Escrow account not found for tenant {tenant_id}")
                
            if account.available_balance < amount:
                raise ValueError(
                    f"Insufficient funds. Available: ${account.available_balance}, "
                    f"Required: ${amount}"
                )
                
            # Create transaction
            transaction = EscrowTransaction(
                transaction_id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                transaction_type=TransactionType.LOCK,
                amount=amount,
                status=TransactionStatus.PENDING,
                description=description or f"Lock ${amount} for task {task_id}",
                task_id=task_id,
                agent_id=agent_id,
                metadata={"task_id": task_id, "agent_id": agent_id},
                created_at=datetime.utcnow()
            )
            
            # Save transaction
            await self.db.create_transaction(transaction)
            
            # Lock funds
            await self.db.update_escrow_balance(
                tenant_id,
                amount,
                operation="lock"
            )
            
            # Update transaction status
            transaction.status = TransactionStatus.COMPLETED
            transaction.completed_at = datetime.utcnow()
            
            logger.info(
                f"Locked ${amount} for task {task_id} (tenant: {tenant_id}). "
                f"Transaction: {transaction.transaction_id}"
            )
            
            return transaction
            
        except Exception as e:
            logger.error(f"Failed to lock funds: {e}")
            raise ValueError(f"Fund locking failed: {str(e)}")
            
    async def release_funds(
        self,
        request: EscrowReleaseRequest
    ) -> EscrowTransaction:
        """
        Release locked funds (on task completion).
        
        Args:
            request: Release request
            
        Returns:
            EscrowTransaction: Created transaction
            
        Raises:
            ValueError: If release fails
        """
        try:
            # Get original transaction
            transactions = await self.db.get_transactions(request.tenant_id)
            original_tx = next(
                (tx for tx in transactions if tx.transaction_id == request.transaction_id),
                None
            )
            
            if not original_tx:
                raise ValueError(f"Transaction {request.transaction_id} not found")
                
            if original_tx.transaction_type != TransactionType.LOCK:
                raise ValueError(f"Transaction {request.transaction_id} is not a lock transaction")
                
            # Determine amount to release
            release_amount = request.amount or original_tx.amount
            
            if release_amount > original_tx.amount:
                raise ValueError(
                    f"Release amount ${release_amount} exceeds locked amount ${original_tx.amount}"
                )
                
            # Create release transaction
            transaction = EscrowTransaction(
                transaction_id=str(uuid.uuid4()),
                tenant_id=request.tenant_id,
                transaction_type=TransactionType.RELEASE,
                amount=release_amount,
                status=TransactionStatus.PENDING,
                description=request.reason or f"Release ${release_amount} from task {original_tx.task_id}",
                task_id=original_tx.task_id,
                agent_id=original_tx.agent_id,
                metadata={"original_transaction_id": request.transaction_id},
                created_at=datetime.utcnow()
            )
            
            # Save transaction
            await self.db.create_transaction(transaction)
            
            # Unlock funds
            await self.db.update_escrow_balance(
                request.tenant_id,
                release_amount,
                operation="unlock"
            )
            
            # Deduct from balance (funds spent)
            await self.db.update_escrow_balance(
                request.tenant_id,
                release_amount,
                operation="subtract"
            )
            
            # Update transaction status
            transaction.status = TransactionStatus.COMPLETED
            transaction.completed_at = datetime.utcnow()
            
            # Publish event
            await kafka_producer.publish_event(
                "escrow.released",
                {
                    "transaction_id": transaction.transaction_id,
                    "tenant_id": request.tenant_id,
                    "amount": str(release_amount),
                    "task_id": original_tx.task_id,
                    "balance": str((await self.db.get_escrow_account(request.tenant_id)).balance)
                }
            )
            
            logger.info(
                f"Released ${release_amount} for task {original_tx.task_id} "
                f"(tenant: {request.tenant_id}). Transaction: {transaction.transaction_id}"
            )
            
            return transaction
            
        except Exception as e:
            logger.error(f"Failed to release funds: {e}")
            raise ValueError(f"Fund release failed: {str(e)}")
            
    async def refund_funds(
        self,
        tenant_id: str,
        transaction_id: str,
        reason: Optional[str] = None
    ) -> EscrowTransaction:
        """
        Refund locked funds (on task failure).
        
        Args:
            tenant_id: Tenant identifier
            transaction_id: Original lock transaction ID
            reason: Optional refund reason
            
        Returns:
            EscrowTransaction: Created transaction
            
        Raises:
            ValueError: If refund fails
        """
        try:
            # Get original transaction
            transactions = await self.db.get_transactions(tenant_id)
            original_tx = next(
                (tx for tx in transactions if tx.transaction_id == transaction_id),
                None
            )
            
            if not original_tx:
                raise ValueError(f"Transaction {transaction_id} not found")
                
            if original_tx.transaction_type != TransactionType.LOCK:
                raise ValueError(f"Transaction {transaction_id} is not a lock transaction")
                
            # Create refund transaction
            transaction = EscrowTransaction(
                transaction_id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                transaction_type=TransactionType.REFUND,
                amount=original_tx.amount,
                status=TransactionStatus.PENDING,
                description=reason or f"Refund ${original_tx.amount} from failed task {original_tx.task_id}",
                task_id=original_tx.task_id,
                agent_id=original_tx.agent_id,
                metadata={"original_transaction_id": transaction_id},
                created_at=datetime.utcnow()
            )
            
            # Save transaction
            await self.db.create_transaction(transaction)
            
            # Unlock funds (return to available balance)
            await self.db.update_escrow_balance(
                tenant_id,
                original_tx.amount,
                operation="unlock"
            )
            
            # Update transaction status
            transaction.status = TransactionStatus.COMPLETED
            transaction.completed_at = datetime.utcnow()
            
            # Publish event
            await kafka_producer.publish_event(
                "escrow.refunded",
                {
                    "transaction_id": transaction.transaction_id,
                    "tenant_id": tenant_id,
                    "amount": str(original_tx.amount),
                    "task_id": original_tx.task_id,
                    "reason": reason
                }
            )
            
            logger.info(
                f"Refunded ${original_tx.amount} for failed task {original_tx.task_id} "
                f"(tenant: {tenant_id}). Transaction: {transaction.transaction_id}"
            )
            
            return transaction
            
        except Exception as e:
            logger.error(f"Failed to refund funds: {e}")
            raise ValueError(f"Fund refund failed: {str(e)}")
            
    async def get_account_balance(self, tenant_id: str) -> EscrowAccount:
        """
        Get escrow account balance.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            EscrowAccount: Account information
            
        Raises:
            ValueError: If account not found
        """
        account = await self.db.get_escrow_account(tenant_id)
        if not account:
            raise ValueError(f"Escrow account not found for tenant {tenant_id}")
            
        return account
        
    async def get_transaction_history(
        self,
        tenant_id: str,
        limit: int = 100
    ) -> list[EscrowTransaction]:
        """
        Get transaction history for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            limit: Maximum number of transactions to return
            
        Returns:
            List of transactions
        """
        return await self.db.get_transactions(tenant_id, limit)
        
    async def validate_sufficient_funds(
        self,
        tenant_id: str,
        required_amount: Decimal
    ) -> tuple[bool, str]:
        """
        Validate if tenant has sufficient funds.
        
        Args:
            tenant_id: Tenant identifier
            required_amount: Required amount
            
        Returns:
            Tuple of (is_sufficient, message)
        """
        try:
            account = await self.db.get_escrow_account(tenant_id)
            if not account:
                return False, f"Escrow account not found for tenant {tenant_id}"
                
            if account.available_balance < required_amount:
                return False, (
                    f"Insufficient funds. Available: ${account.available_balance}, "
                    f"Required: ${required_amount}"
                )
                
            return True, "Sufficient funds available"
            
        except Exception as e:
            logger.error(f"Failed to validate funds: {e}")
            return False, f"Validation failed: {str(e)}"


# Global escrow manager instance
escrow_manager = EscrowManager()

# Made with Bob
