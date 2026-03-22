"""
Compliance reporting for vessel-economics service.
Generates audit trails, compliance reports, and regulatory exports.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import json
import csv
import io

from .database import db_manager
from .models import (
    ComplianceReport, ComplianceReportRequest, ComplianceReportType,
    AuditTrailEntry, AuditTrailQuery
)
from .config import settings

logger = logging.getLogger(__name__)


class ComplianceReporter:
    """Generates compliance reports and manages audit trails."""
    
    def __init__(self):
        """Initialize compliance reporter."""
        self.db = db_manager
        
    async def create_audit_entry(
        self,
        tenant_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditTrailEntry:
        """
        Create an audit trail entry.
        
        Args:
            tenant_id: Tenant identifier
            event_type: Type of event
            event_data: Event data
            user_id: Optional user identifier
            ip_address: Optional IP address
            metadata: Optional metadata
            
        Returns:
            Created audit trail entry
        """
        try:
            entry = AuditTrailEntry(
                entry_id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                event_type=event_type,
                event_data=event_data,
                user_id=user_id,
                ip_address=ip_address,
                timestamp=datetime.utcnow(),
                metadata=metadata or {}
            )
            
            await self.db.create_audit_entry(entry)
            
            logger.debug(
                f"Created audit entry: tenant={tenant_id}, "
                f"event={event_type}, entry_id={entry.entry_id}"
            )
            
            return entry
            
        except Exception as e:
            logger.error(f"Failed to create audit entry: {e}")
            raise ValueError(f"Audit entry creation failed: {str(e)}")
            
    async def get_audit_trail(
        self,
        query: AuditTrailQuery
    ) -> List[AuditTrailEntry]:
        """
        Get audit trail entries based on query.
        
        Args:
            query: Audit trail query parameters
            
        Returns:
            List of audit trail entries
        """
        try:
            entries = await self.db.get_audit_trail(
                tenant_id=query.tenant_id,
                event_type=query.event_type,
                start_date=query.start_date,
                end_date=query.end_date,
                limit=query.limit,
                offset=query.offset
            )
            
            logger.info(
                f"Retrieved {len(entries)} audit trail entries "
                f"(tenant={query.tenant_id}, event_type={query.event_type})"
            )
            
            return entries
            
        except Exception as e:
            logger.error(f"Failed to get audit trail: {e}")
            raise ValueError(f"Audit trail retrieval failed: {str(e)}")
            
    async def generate_compliance_report(
        self,
        request: ComplianceReportRequest
    ) -> ComplianceReport:
        """
        Generate a compliance report.
        
        Args:
            request: Compliance report request
            
        Returns:
            Generated compliance report
        """
        try:
            report_id = str(uuid.uuid4())
            
            # Generate report based on type
            if request.report_type == ComplianceReportType.AUDIT_TRAIL:
                data = await self._generate_audit_trail_report(request)
            elif request.report_type == ComplianceReportType.COST_SUMMARY:
                data = await self._generate_cost_summary_report(request)
            elif request.report_type == ComplianceReportType.BUDGET_ANALYSIS:
                data = await self._generate_budget_analysis_report(request)
            elif request.report_type == ComplianceReportType.TRANSACTION_RECONCILIATION:
                data = await self._generate_transaction_reconciliation_report(request)
            elif request.report_type == ComplianceReportType.REGULATORY_EXPORT:
                data = await self._generate_regulatory_export_report(request)
            else:
                raise ValueError(f"Unknown report type: {request.report_type}")
                
            # Calculate total transactions and cost
            total_transactions = data.get("total_transactions", 0)
            total_cost = Decimal(str(data.get("total_cost", "0")))
            
            # Create report
            report = ComplianceReport(
                report_id=report_id,
                report_type=request.report_type,
                tenant_id=request.tenant_id,
                start_date=request.start_date,
                end_date=request.end_date,
                generated_at=datetime.utcnow(),
                total_transactions=total_transactions,
                total_cost=total_cost,
                data=data,
                format=request.format
            )
            
            # Export to file if requested
            if request.format in ["csv", "pdf"]:
                file_path = await self._export_report(report, request.format)
                report.file_path = file_path
                
            logger.info(
                f"Generated compliance report: type={request.report_type.value}, "
                f"tenant={request.tenant_id}, report_id={report_id}"
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")
            raise ValueError(f"Compliance report generation failed: {str(e)}")
            
    async def _generate_audit_trail_report(
        self,
        request: ComplianceReportRequest
    ) -> Dict[str, Any]:
        """Generate audit trail report."""
        entries = await self.db.get_audit_trail(
            tenant_id=request.tenant_id,
            start_date=request.start_date,
            end_date=request.end_date,
            limit=10000  # Large limit for reports
        )
        
        # Aggregate by event type
        by_event_type: Dict[str, int] = {}
        by_date: Dict[str, int] = {}
        
        for entry in entries:
            # By event type
            by_event_type[entry.event_type] = by_event_type.get(entry.event_type, 0) + 1
            
            # By date
            date_key = entry.timestamp.strftime("%Y-%m-%d")
            by_date[date_key] = by_date.get(date_key, 0) + 1
            
        return {
            "total_transactions": len(entries),
            "total_cost": "0",  # Audit trail doesn't track costs directly
            "entries": [
                {
                    "entry_id": e.entry_id,
                    "tenant_id": e.tenant_id,
                    "event_type": e.event_type,
                    "timestamp": e.timestamp.isoformat(),
                    "user_id": e.user_id,
                    "ip_address": e.ip_address,
                    "event_data": e.event_data if request.include_metadata else {}
                }
                for e in entries
            ],
            "summary": {
                "by_event_type": by_event_type,
                "by_date": by_date
            }
        }
        
    async def _generate_cost_summary_report(
        self,
        request: ComplianceReportRequest
    ) -> Dict[str, Any]:
        """Generate cost summary report."""
        costs = await self.db.get_costs_by_tenant(
            request.tenant_id or "",
            request.start_date,
            request.end_date
        )
        
        # Calculate aggregations
        total_cost = Decimal("0")
        by_category: Dict[str, Decimal] = {}
        by_provider: Dict[str, Decimal] = {}
        by_model: Dict[str, Decimal] = {}
        by_date: Dict[str, Decimal] = {}
        
        for cost in costs:
            total_cost += cost.cost
            
            # By category
            category_key = cost.category.value
            by_category[category_key] = by_category.get(category_key, Decimal("0")) + cost.cost
            
            # By provider
            if cost.provider:
                by_provider[cost.provider] = by_provider.get(cost.provider, Decimal("0")) + cost.cost
                
            # By model
            if cost.model:
                by_model[cost.model] = by_model.get(cost.model, Decimal("0")) + cost.cost
                
            # By date
            date_key = cost.created_at.strftime("%Y-%m-%d")
            by_date[date_key] = by_date.get(date_key, Decimal("0")) + cost.cost
            
        return {
            "total_transactions": len(costs),
            "total_cost": str(total_cost),
            "costs": [
                {
                    "cost_id": c.cost_id,
                    "tenant_id": c.tenant_id,
                    "task_id": c.task_id,
                    "agent_id": c.agent_id,
                    "category": c.category.value,
                    "provider": c.provider,
                    "model": c.model,
                    "cost": str(c.cost),
                    "created_at": c.created_at.isoformat()
                }
                for c in costs
            ],
            "summary": {
                "by_category": {k: str(v) for k, v in by_category.items()},
                "by_provider": {k: str(v) for k, v in by_provider.items()},
                "by_model": {k: str(v) for k, v in by_model.items()},
                "by_date": {k: str(v) for k, v in by_date.items()}
            }
        }
        
    async def _generate_budget_analysis_report(
        self,
        request: ComplianceReportRequest
    ) -> Dict[str, Any]:
        """Generate budget analysis report."""
        if not request.tenant_id:
            raise ValueError("Tenant ID required for budget analysis report")
            
        budget = await self.db.get_budget_limit(request.tenant_id)
        
        if not budget:
            return {
                "total_transactions": 0,
                "total_cost": "0",
                "budget": None,
                "message": "No budget configured"
            }
            
        # Get costs for period
        costs = await self.db.get_costs_by_tenant(
            request.tenant_id,
            request.start_date,
            request.end_date
        )
        
        period_cost = sum(c.cost for c in costs)
        usage_percentage = (budget.used_budget / budget.total_budget) if budget.total_budget > 0 else Decimal("0")
        
        return {
            "total_transactions": len(costs),
            "total_cost": str(period_cost),
            "budget": {
                "tenant_id": budget.tenant_id,
                "total_budget": str(budget.total_budget),
                "used_budget": str(budget.used_budget),
                "remaining_budget": str(budget.remaining_budget),
                "usage_percentage": str(usage_percentage * 100),
                "status": budget.status.value,
                "warning_threshold": str(budget.warning_threshold * 100),
                "critical_threshold": str(budget.critical_threshold * 100)
            },
            "period_analysis": {
                "period_cost": str(period_cost),
                "period_transactions": len(costs),
                "average_cost_per_transaction": str(period_cost / len(costs)) if costs else "0"
            }
        }
        
    async def _generate_transaction_reconciliation_report(
        self,
        request: ComplianceReportRequest
    ) -> Dict[str, Any]:
        """Generate transaction reconciliation report."""
        if not request.tenant_id:
            raise ValueError("Tenant ID required for transaction reconciliation report")
            
        # Get escrow transactions
        transactions = await self.db.get_transactions(request.tenant_id, limit=10000)
        
        # Filter by date range
        if request.start_date or request.end_date:
            transactions = [
                t for t in transactions
                if (not request.start_date or t.created_at >= request.start_date) and
                   (not request.end_date or t.created_at <= request.end_date)
            ]
            
        # Calculate totals by transaction type
        by_type: Dict[str, Decimal] = {}
        
        for tx in transactions:
            tx_type = tx.transaction_type.value
            by_type[tx_type] = by_type.get(tx_type, Decimal("0")) + tx.amount
            
        total_amount = sum(tx.amount for tx in transactions)
        
        return {
            "total_transactions": len(transactions),
            "total_cost": str(total_amount),
            "transactions": [
                {
                    "transaction_id": t.transaction_id,
                    "tenant_id": t.tenant_id,
                    "transaction_type": t.transaction_type.value,
                    "amount": str(t.amount),
                    "status": t.status.value,
                    "task_id": t.task_id,
                    "created_at": t.created_at.isoformat(),
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None
                }
                for t in transactions
            ],
            "summary": {
                "by_type": {k: str(v) for k, v in by_type.items()},
                "total_amount": str(total_amount)
            }
        }
        
    async def _generate_regulatory_export_report(
        self,
        request: ComplianceReportRequest
    ) -> Dict[str, Any]:
        """Generate regulatory export report (comprehensive)."""
        # Combine all data for regulatory compliance
        audit_data = await self._generate_audit_trail_report(request)
        cost_data = await self._generate_cost_summary_report(request)
        
        if request.tenant_id:
            budget_data = await self._generate_budget_analysis_report(request)
            transaction_data = await self._generate_transaction_reconciliation_report(request)
        else:
            budget_data = {"message": "Budget data requires tenant_id"}
            transaction_data = {"message": "Transaction data requires tenant_id"}
            
        return {
            "total_transactions": audit_data["total_transactions"] + cost_data["total_transactions"],
            "total_cost": cost_data["total_cost"],
            "report_metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "tenant_id": request.tenant_id,
                "start_date": request.start_date.isoformat(),
                "end_date": request.end_date.isoformat(),
                "report_type": request.report_type.value
            },
            "audit_trail": audit_data,
            "cost_summary": cost_data,
            "budget_analysis": budget_data,
            "transaction_reconciliation": transaction_data
        }
        
    async def _export_report(
        self,
        report: ComplianceReport,
        format: str
    ) -> str:
        """Export report to file."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"compliance_report_{report.report_id}_{timestamp}.{format}"
            file_path = f"/tmp/{filename}"
            
            if format == "csv":
                await self._export_to_csv(report, file_path)
            elif format == "pdf":
                # PDF export would require additional library (reportlab, weasyprint, etc.)
                # For now, we'll just save as JSON with .pdf extension
                await self._export_to_json(report, file_path)
            else:
                await self._export_to_json(report, file_path)
                
            logger.info(f"Exported report to {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to export report: {e}")
            return ""
            
    async def _export_to_csv(self, report: ComplianceReport, file_path: str):
        """Export report to CSV format."""
        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow([
                "Report ID", report.report_id,
                "Type", report.report_type.value,
                "Generated", report.generated_at.isoformat()
            ])
            writer.writerow([])
            
            # Write summary
            writer.writerow(["Summary"])
            writer.writerow(["Total Transactions", report.total_transactions])
            writer.writerow(["Total Cost", str(report.total_cost)])
            writer.writerow([])
            
            # Write data (simplified)
            writer.writerow(["Data"])
            writer.writerow([json.dumps(report.data, indent=2)])
            
    async def _export_to_json(self, report: ComplianceReport, file_path: str):
        """Export report to JSON format."""
        report_dict = {
            "report_id": report.report_id,
            "report_type": report.report_type.value,
            "tenant_id": report.tenant_id,
            "start_date": report.start_date.isoformat(),
            "end_date": report.end_date.isoformat(),
            "generated_at": report.generated_at.isoformat(),
            "total_transactions": report.total_transactions,
            "total_cost": str(report.total_cost),
            "data": report.data
        }
        
        with open(file_path, 'w') as f:
            json.dump(report_dict, f, indent=2)


# Global compliance reporter instance
compliance_reporter = ComplianceReporter()

# Made with Bob
