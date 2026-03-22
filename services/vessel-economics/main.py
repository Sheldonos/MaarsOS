"""
Vessel Economics Service - Main FastAPI application.
Provides cost tracking, budget enforcement, escrow management, and compliance reporting.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import uvicorn

from app.config import settings
from app.database import db_manager
from app.escrow import escrow_manager
from app.cost_tracker import cost_tracker
from app.budget_enforcer import budget_enforcer
from app.compliance import compliance_reporter
from app.kafka_producer import kafka_producer
from app.models import (
    EscrowAllocateRequest, EscrowReleaseRequest, EscrowAccount,
    CostTrackRequest, CostSummary, CostRecord,
    BudgetCheckRequest, BudgetCheckResponse, BudgetEnforceRequest,
    BudgetLimit, ComplianceReportRequest, ComplianceReport,
    AuditTrailQuery, AuditTrailEntry, Invoice,
    HealthResponse, MetricsResponse
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
escrow_allocations = Counter('economics_escrow_allocations_total', 'Total escrow allocations')
escrow_releases = Counter('economics_escrow_releases_total', 'Total escrow releases')
costs_tracked = Counter('economics_costs_tracked_total', 'Total costs tracked', ['category'])
budget_checks = Counter('economics_budget_checks_total', 'Total budget checks', ['result'])
budget_exceeded = Counter('economics_budget_exceeded_total', 'Total budget exceeded events')
compliance_reports = Counter('economics_compliance_reports_total', 'Total compliance reports', ['type'])

cost_amount = Histogram('economics_cost_amount_usd', 'Cost amounts in USD')
escrow_balance = Gauge('economics_escrow_balance_usd', 'Current escrow balance', ['tenant_id'])
budget_utilization = Gauge('economics_budget_utilization_percent', 'Budget utilization percentage', ['tenant_id'])

request_duration = Histogram('economics_request_duration_seconds', 'Request duration', ['endpoint'])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown."""
    # Startup
    logger.info(f"Starting {settings.service_name} v{settings.service_version}")
    
    try:
        await db_manager.connect()
        await kafka_producer.connect()
        logger.info("All connections established")
    except Exception as e:
        logger.error(f"Failed to establish connections: {e}")
        
    yield
    
    # Shutdown
    logger.info("Shutting down service")
    await db_manager.disconnect()
    await kafka_producer.disconnect()


# Create FastAPI app
app = FastAPI(
    title="Vessel Economics Service",
    description="Cost tracking, budget enforcement, escrow management, and compliance reporting",
    version=settings.service_version,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service=settings.service_name,
        version=settings.service_version,
        timestamp=datetime.utcnow(),
        database="connected" if db_manager.conn or db_manager.session else "disconnected",
        kafka="connected" if kafka_producer.producer else "disconnected"
    )


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Escrow endpoints
@app.post("/api/v1/escrow/allocate", response_model=dict)
async def allocate_escrow(request: EscrowAllocateRequest):
    """
    Allocate budget to escrow account.
    
    Args:
        request: Escrow allocation request
        
    Returns:
        Transaction details
    """
    try:
        with request_duration.labels(endpoint='allocate_escrow').time():
            transaction = await escrow_manager.allocate_budget(request)
            escrow_allocations.inc()
            
            return {
                "transaction_id": transaction.transaction_id,
                "tenant_id": transaction.tenant_id,
                "amount": str(transaction.amount),
                "status": transaction.status.value,
                "created_at": transaction.created_at.isoformat()
            }
    except Exception as e:
        logger.error(f"Failed to allocate escrow: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/escrow/release", response_model=dict)
async def release_escrow(request: EscrowReleaseRequest):
    """
    Release escrow funds.
    
    Args:
        request: Escrow release request
        
    Returns:
        Transaction details
    """
    try:
        with request_duration.labels(endpoint='release_escrow').time():
            transaction = await escrow_manager.release_funds(request)
            escrow_releases.inc()
            
            return {
                "transaction_id": transaction.transaction_id,
                "tenant_id": transaction.tenant_id,
                "amount": str(transaction.amount),
                "status": transaction.status.value,
                "created_at": transaction.created_at.isoformat()
            }
    except Exception as e:
        logger.error(f"Failed to release escrow: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/escrow/{tenant_id}", response_model=dict)
async def get_escrow_balance(tenant_id: str):
    """
    Get escrow balance for a tenant.
    
    Args:
        tenant_id: Tenant identifier
        
    Returns:
        Escrow account details
    """
    try:
        with request_duration.labels(endpoint='get_escrow_balance').time():
            account = await escrow_manager.get_account_balance(tenant_id)
            
            # Update Prometheus gauge
            escrow_balance.labels(tenant_id=tenant_id).set(float(account.balance))
            
            return {
                "tenant_id": account.tenant_id,
                "balance": str(account.balance),
                "locked_balance": str(account.locked_balance),
                "available_balance": str(account.available_balance),
                "total_allocated": str(account.total_allocated),
                "total_spent": str(account.total_spent),
                "updated_at": account.updated_at.isoformat()
            }
    except Exception as e:
        logger.error(f"Failed to get escrow balance: {e}")
        raise HTTPException(status_code=404, detail=str(e))


# Cost tracking endpoints
@app.post("/api/v1/costs/track", response_model=dict)
async def track_cost(request: CostTrackRequest):
    """
    Track a cost record.
    
    Args:
        request: Cost tracking request
        
    Returns:
        Cost record details
    """
    try:
        with request_duration.labels(endpoint='track_cost').time():
            cost_record = await cost_tracker.track_cost(request)
            costs_tracked.labels(category=request.category.value).inc()
            cost_amount.observe(float(cost_record.cost))
            
            return {
                "cost_id": cost_record.cost_id,
                "tenant_id": cost_record.tenant_id,
                "task_id": cost_record.task_id,
                "cost": str(cost_record.cost),
                "category": cost_record.category.value,
                "created_at": cost_record.created_at.isoformat()
            }
    except Exception as e:
        logger.error(f"Failed to track cost: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/costs/summary", response_model=dict)
async def get_cost_summary(
    tenant_id: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365)
):
    """
    Get cost summary with aggregations.
    
    Args:
        tenant_id: Optional tenant filter
        agent_id: Optional agent filter
        days: Number of days to look back
        
    Returns:
        Cost summary
    """
    try:
        with request_duration.labels(endpoint='get_cost_summary').time():
            start_date = datetime.utcnow() - timedelta(days=days)
            summary = await cost_tracker.get_cost_summary(
                tenant_id=tenant_id,
                agent_id=agent_id,
                start_date=start_date,
                end_date=datetime.utcnow()
            )
            
            return {
                "tenant_id": summary.tenant_id,
                "agent_id": summary.agent_id,
                "total_cost": str(summary.total_cost),
                "total_tasks": summary.total_tasks,
                "cost_by_category": {k: str(v) for k, v in summary.cost_by_category.items()},
                "cost_by_provider": {k: str(v) for k, v in summary.cost_by_provider.items()},
                "cost_by_model": {k: str(v) for k, v in summary.cost_by_model.items()},
                "total_input_tokens": summary.total_input_tokens,
                "total_output_tokens": summary.total_output_tokens,
                "period_days": days
            }
    except Exception as e:
        logger.error(f"Failed to get cost summary: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/costs/by-tenant/{tenant_id}", response_model=list)
async def get_costs_by_tenant(
    tenant_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """
    Get cost records for a tenant.
    
    Args:
        tenant_id: Tenant identifier
        days: Number of days to look back
        
    Returns:
        List of cost records
    """
    try:
        with request_duration.labels(endpoint='get_costs_by_tenant').time():
            costs = await cost_tracker.get_costs_by_tenant(tenant_id, days)
            
            return [
                {
                    "cost_id": c.cost_id,
                    "task_id": c.task_id,
                    "agent_id": c.agent_id,
                    "category": c.category.value,
                    "provider": c.provider,
                    "model": c.model,
                    "cost": str(c.cost),
                    "created_at": c.created_at.isoformat()
                }
                for c in costs
            ]
    except Exception as e:
        logger.error(f"Failed to get costs by tenant: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/costs/by-agent/{agent_id}", response_model=list)
async def get_costs_by_agent(
    agent_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """
    Get cost records for an agent.
    
    Args:
        agent_id: Agent identifier
        days: Number of days to look back
        
    Returns:
        List of cost records
    """
    try:
        with request_duration.labels(endpoint='get_costs_by_agent').time():
            costs = await cost_tracker.get_costs_by_agent(agent_id, days)
            
            return [
                {
                    "cost_id": c.cost_id,
                    "tenant_id": c.tenant_id,
                    "task_id": c.task_id,
                    "category": c.category.value,
                    "provider": c.provider,
                    "model": c.model,
                    "cost": str(c.cost),
                    "created_at": c.created_at.isoformat()
                }
                for c in costs
            ]
    except Exception as e:
        logger.error(f"Failed to get costs by agent: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Budget enforcement endpoints
@app.post("/api/v1/budget/check", response_model=BudgetCheckResponse)
async def check_budget(request: BudgetCheckRequest):
    """
    Check if budget is available for a task.
    
    Args:
        request: Budget check request
        
    Returns:
        Budget check response
    """
    try:
        with request_duration.labels(endpoint='check_budget').time():
            response = await budget_enforcer.check_budget(request)
            budget_checks.labels(result='available' if response.available else 'unavailable').inc()
            
            if not response.available:
                budget_exceeded.inc()
                
            return response
    except Exception as e:
        logger.error(f"Failed to check budget: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/budget/enforce", response_model=dict)
async def enforce_budget(request: BudgetEnforceRequest):
    """
    Enforce budget limits before task execution.
    
    Args:
        request: Budget enforcement request
        
    Returns:
        Enforcement result
    """
    try:
        with request_duration.labels(endpoint='enforce_budget').time():
            allowed, message = await budget_enforcer.enforce_budget(request)
            
            return {
                "allowed": allowed,
                "message": message,
                "tenant_id": request.tenant_id,
                "task_id": request.task_id
            }
    except Exception as e:
        logger.error(f"Failed to enforce budget: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/budget/{tenant_id}", response_model=dict)
async def get_budget_status(tenant_id: str):
    """
    Get budget status for a tenant.
    
    Args:
        tenant_id: Tenant identifier
        
    Returns:
        Budget status
    """
    try:
        with request_duration.labels(endpoint='get_budget_status').time():
            budget = await budget_enforcer.get_budget_status(tenant_id)
            
            # Update Prometheus gauge
            usage_pct = (float(budget.used_budget) / float(budget.total_budget) * 100) if budget.total_budget > 0 else 0
            budget_utilization.labels(tenant_id=tenant_id).set(usage_pct)
            
            return {
                "tenant_id": budget.tenant_id,
                "total_budget": str(budget.total_budget),
                "used_budget": str(budget.used_budget),
                "remaining_budget": str(budget.remaining_budget),
                "status": budget.status.value,
                "hard_limit_enabled": budget.hard_limit_enabled,
                "soft_limit_enabled": budget.soft_limit_enabled,
                "updated_at": budget.updated_at.isoformat()
            }
    except Exception as e:
        logger.error(f"Failed to get budget status: {e}")
        raise HTTPException(status_code=404, detail=str(e))


# Compliance endpoints
@app.post("/api/v1/compliance/report", response_model=dict)
async def generate_compliance_report(request: ComplianceReportRequest):
    """
    Generate a compliance report.
    
    Args:
        request: Compliance report request
        
    Returns:
        Compliance report
    """
    try:
        with request_duration.labels(endpoint='generate_compliance_report').time():
            report = await compliance_reporter.generate_compliance_report(request)
            compliance_reports.labels(type=request.report_type.value).inc()
            
            return {
                "report_id": report.report_id,
                "report_type": report.report_type.value,
                "tenant_id": report.tenant_id,
                "start_date": report.start_date.isoformat(),
                "end_date": report.end_date.isoformat(),
                "generated_at": report.generated_at.isoformat(),
                "total_transactions": report.total_transactions,
                "total_cost": str(report.total_cost),
                "format": report.format,
                "file_path": report.file_path,
                "data": report.data
            }
    except Exception as e:
        logger.error(f"Failed to generate compliance report: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/compliance/audit-trail", response_model=list)
async def get_audit_trail(
    tenant_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Get audit trail entries.
    
    Args:
        tenant_id: Optional tenant filter
        event_type: Optional event type filter
        days: Number of days to look back
        limit: Maximum number of entries
        offset: Offset for pagination
        
    Returns:
        List of audit trail entries
    """
    try:
        with request_duration.labels(endpoint='get_audit_trail').time():
            start_date = datetime.utcnow() - timedelta(days=days)
            
            query = AuditTrailQuery(
                tenant_id=tenant_id,
                event_type=event_type,
                start_date=start_date,
                end_date=datetime.utcnow(),
                limit=limit,
                offset=offset
            )
            
            entries = await compliance_reporter.get_audit_trail(query)
            
            return [
                {
                    "entry_id": e.entry_id,
                    "tenant_id": e.tenant_id,
                    "event_type": e.event_type,
                    "timestamp": e.timestamp.isoformat(),
                    "user_id": e.user_id,
                    "ip_address": e.ip_address,
                    "event_data": e.event_data
                }
                for e in entries
            ]
    except Exception as e:
        logger.error(f"Failed to get audit trail: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/billing/invoice/{tenant_id}", response_model=dict)
async def generate_invoice(
    tenant_id: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """
    Generate invoice for a tenant.
    
    Args:
        tenant_id: Tenant identifier
        start_date: Optional billing period start (ISO format)
        end_date: Optional billing period end (ISO format)
        
    Returns:
        Invoice details
    """
    try:
        with request_duration.labels(endpoint='generate_invoice').time():
            # Parse dates or use default (last 30 days)
            if start_date:
                period_start = datetime.fromisoformat(start_date)
            else:
                period_start = datetime.utcnow() - timedelta(days=30)
                
            if end_date:
                period_end = datetime.fromisoformat(end_date)
            else:
                period_end = datetime.utcnow()
                
            # Get costs for period
            costs = await db_manager.get_costs_by_tenant(tenant_id, period_start, period_end)
            
            # Calculate totals
            total_cost = sum(c.cost for c in costs)
            tax_amount = total_cost * settings.tax_rate
            total_amount = total_cost + tax_amount
            
            # Create line items
            line_items = [
                {
                    "description": f"{c.category.value} - {c.task_id}",
                    "provider": c.provider,
                    "model": c.model,
                    "cost": str(c.cost),
                    "date": c.created_at.isoformat()
                }
                for c in costs
            ]
            
            # Create invoice
            from app.models import Invoice
            import uuid
            
            invoice = Invoice(
                invoice_id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                billing_period_start=period_start,
                billing_period_end=period_end,
                total_cost=total_cost,
                tax_amount=tax_amount,
                total_amount=total_amount,
                currency=settings.invoice_currency,
                line_items=line_items,
                status="issued",
                issued_at=datetime.utcnow()
            )
            
            # Save invoice
            await db_manager.create_invoice(invoice)
            
            return {
                "invoice_id": invoice.invoice_id,
                "tenant_id": invoice.tenant_id,
                "billing_period_start": invoice.billing_period_start.isoformat(),
                "billing_period_end": invoice.billing_period_end.isoformat(),
                "total_cost": str(invoice.total_cost),
                "tax_amount": str(invoice.tax_amount),
                "total_amount": str(invoice.total_amount),
                "currency": invoice.currency,
                "line_items": invoice.line_items,
                "status": invoice.status,
                "issued_at": invoice.issued_at.isoformat() if invoice.issued_at else None
            }
    except Exception as e:
        logger.error(f"Failed to generate invoice: {e}")
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level=settings.log_level.lower()
    )

# Made with Bob
