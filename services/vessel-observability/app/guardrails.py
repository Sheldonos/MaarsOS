"""
Guardrail engine for policy evaluation and enforcement.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

from .config import settings
from .models import (
    GuardrailPolicy,
    GuardrailEvaluationRequest,
    GuardrailEvaluationResponse,
    PolicyViolation,
    PolicyType,
    PolicyAction,
    PolicySeverity,
)
from .database import db_manager

logger = logging.getLogger(__name__)


class GuardrailEngine:
    """Engine for evaluating and enforcing guardrail policies."""
    
    def __init__(self):
        """Initialize guardrail engine."""
        self.request_counts = defaultdict(lambda: defaultdict(int))
        self.cost_tracking = defaultdict(lambda: defaultdict(float))
        
        # Profanity patterns (simplified - use a proper library in production)
        self.profanity_patterns = [
            r'\b(damn|hell|crap)\b',
        ]
        
        # PII patterns
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        }
        
        # Sensitive data patterns
        self.sensitive_patterns = {
            'api_key': r'\b[A-Za-z0-9]{32,}\b',
            'password': r'password\s*[:=]\s*[^\s]+',
            'token': r'token\s*[:=]\s*[^\s]+',
        }
    
    async def evaluate(
        self,
        request: GuardrailEvaluationRequest
    ) -> GuardrailEvaluationResponse:
        """
        Evaluate guardrail policies for a request.
        
        Args:
            request: Evaluation request
            
        Returns:
            Evaluation response with violations and warnings
        """
        start_time = datetime.utcnow()
        violations = []
        warnings = []
        
        try:
            # Get active policies for tenant
            policies = await db_manager.list_policies(request.tenant_id, enabled_only=True)
            
            # Evaluate each policy
            for policy_data in policies:
                policy = self._parse_policy(policy_data)
                
                if policy.policy_type == PolicyType.CONTENT:
                    violation = await self._evaluate_content_policy(policy, request)
                elif policy.policy_type == PolicyType.RATE_LIMIT:
                    violation = await self._evaluate_rate_limit_policy(policy, request)
                elif policy.policy_type == PolicyType.COST_THRESHOLD:
                    violation = await self._evaluate_cost_policy(policy, request)
                elif policy.policy_type == PolicyType.RESOURCE_LIMIT:
                    violation = await self._evaluate_resource_policy(policy, request)
                elif policy.policy_type == PolicyType.EXECUTION_TIME:
                    violation = await self._evaluate_execution_time_policy(policy, request)
                else:
                    continue
                
                if violation:
                    violations.append(violation)
                    
                    # Record violation in database
                    await db_manager.record_violation(violation)
                    
                    # Add warning if action is WARN
                    if violation.action_taken == PolicyAction.WARN:
                        warnings.append(
                            f"Policy '{policy.policy_name}' warning: {violation.violation_details.get('message', 'Violation detected')}"
                        )
            
            # Determine if request is allowed
            allowed = not any(v.action_taken == PolicyAction.BLOCK for v in violations)
            
            # Calculate evaluation time
            evaluation_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return GuardrailEvaluationResponse(
                allowed=allowed,
                violations=violations,
                warnings=warnings,
                evaluation_time_ms=evaluation_time_ms,
                policies_evaluated=len(policies)
            )
            
        except Exception as e:
            logger.error(f"Error evaluating guardrails: {e}")
            # Fail open - allow request but log error
            return GuardrailEvaluationResponse(
                allowed=True,
                violations=[],
                warnings=[f"Guardrail evaluation error: {str(e)}"],
                evaluation_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                policies_evaluated=0
            )
    
    def _parse_policy(self, policy_data: Dict[str, Any]) -> GuardrailPolicy:
        """Parse policy data from database."""
        # This is a simplified parser - in production, properly deserialize JSON config
        return GuardrailPolicy(
            policy_id=str(policy_data.get('policy_id')),
            tenant_id=policy_data.get('tenant_id'),
            policy_name=policy_data.get('policy_name'),
            policy_type=PolicyType(policy_data.get('policy_type')),
            description=policy_data.get('description'),
            enabled=policy_data.get('enabled', True),
            severity=PolicySeverity(policy_data.get('severity', 'medium')),
            action=PolicyAction(policy_data.get('action', 'warn')),
        )
    
    async def _evaluate_content_policy(
        self,
        policy: GuardrailPolicy,
        request: GuardrailEvaluationRequest
    ) -> Optional[PolicyViolation]:
        """Evaluate content filtering policy."""
        if not request.content:
            return None
        
        content = request.content.lower()
        violations_found = []
        
        # Check profanity
        if settings.content_filter_profanity:
            for pattern in self.profanity_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    violations_found.append("Profanity detected")
                    break
        
        # Check PII
        if settings.content_filter_pii:
            for pii_type, pattern in self.pii_patterns.items():
                if re.search(pattern, request.content):
                    violations_found.append(f"PII detected: {pii_type}")
        
        # Check sensitive data
        if settings.content_filter_sensitive_data:
            for data_type, pattern in self.sensitive_patterns.items():
                if re.search(pattern, content, re.IGNORECASE):
                    violations_found.append(f"Sensitive data detected: {data_type}")
        
        if violations_found:
            return PolicyViolation(
                policy_id=policy.policy_id,
                policy_name=policy.policy_name,
                policy_type=policy.policy_type,
                tenant_id=request.tenant_id,
                task_id=request.task_id,
                agent_id=request.agent_id,
                severity=policy.severity,
                action_taken=policy.action,
                violation_details={
                    "message": "Content policy violation",
                    "violations": violations_found,
                    "content_length": len(request.content)
                }
            )
        
        return None
    
    async def _evaluate_rate_limit_policy(
        self,
        policy: GuardrailPolicy,
        request: GuardrailEvaluationRequest
    ) -> Optional[PolicyViolation]:
        """Evaluate rate limiting policy."""
        tenant_id = request.tenant_id
        now = datetime.utcnow()
        
        # Track request counts
        minute_key = now.strftime("%Y-%m-%d-%H-%M")
        hour_key = now.strftime("%Y-%m-%d-%H")
        
        self.request_counts[tenant_id][minute_key] += 1
        self.request_counts[tenant_id][hour_key] += 1
        
        # Check limits
        if self.request_counts[tenant_id][minute_key] > settings.guardrail_max_requests_per_minute:
            return PolicyViolation(
                policy_id=policy.policy_id,
                policy_name=policy.policy_name,
                policy_type=policy.policy_type,
                tenant_id=tenant_id,
                task_id=request.task_id,
                agent_id=request.agent_id,
                severity=policy.severity,
                action_taken=policy.action,
                violation_details={
                    "message": "Rate limit exceeded (per minute)",
                    "limit": settings.guardrail_max_requests_per_minute,
                    "current": self.request_counts[tenant_id][minute_key]
                }
            )
        
        if self.request_counts[tenant_id][hour_key] > settings.guardrail_max_requests_per_hour:
            return PolicyViolation(
                policy_id=policy.policy_id,
                policy_name=policy.policy_name,
                policy_type=policy.policy_type,
                tenant_id=tenant_id,
                task_id=request.task_id,
                agent_id=request.agent_id,
                severity=policy.severity,
                action_taken=policy.action,
                violation_details={
                    "message": "Rate limit exceeded (per hour)",
                    "limit": settings.guardrail_max_requests_per_hour,
                    "current": self.request_counts[tenant_id][hour_key]
                }
            )
        
        # Clean up old entries
        self._cleanup_rate_limits(tenant_id, now)
        
        return None
    
    async def _evaluate_cost_policy(
        self,
        policy: GuardrailPolicy,
        request: GuardrailEvaluationRequest
    ) -> Optional[PolicyViolation]:
        """Evaluate cost threshold policy."""
        if not request.cost_estimate:
            return None
        
        tenant_id = request.tenant_id
        
        # Check per-task cost
        if request.cost_estimate > settings.guardrail_max_cost_per_task:
            return PolicyViolation(
                policy_id=policy.policy_id,
                policy_name=policy.policy_name,
                policy_type=policy.policy_type,
                tenant_id=tenant_id,
                task_id=request.task_id,
                agent_id=request.agent_id,
                severity=policy.severity,
                action_taken=policy.action,
                violation_details={
                    "message": "Task cost exceeds threshold",
                    "limit": settings.guardrail_max_cost_per_task,
                    "estimated_cost": request.cost_estimate
                }
            )
        
        # Track daily costs
        day_key = datetime.utcnow().strftime("%Y-%m-%d")
        self.cost_tracking[tenant_id][day_key] += request.cost_estimate
        
        # Check daily tenant cost
        if self.cost_tracking[tenant_id][day_key] > settings.guardrail_max_cost_per_tenant_daily:
            return PolicyViolation(
                policy_id=policy.policy_id,
                policy_name=policy.policy_name,
                policy_type=policy.policy_type,
                tenant_id=tenant_id,
                task_id=request.task_id,
                agent_id=request.agent_id,
                severity=policy.severity,
                action_taken=policy.action,
                violation_details={
                    "message": "Daily tenant cost exceeds threshold",
                    "limit": settings.guardrail_max_cost_per_tenant_daily,
                    "current_cost": self.cost_tracking[tenant_id][day_key]
                }
            )
        
        return None
    
    async def _evaluate_resource_policy(
        self,
        policy: GuardrailPolicy,
        request: GuardrailEvaluationRequest
    ) -> Optional[PolicyViolation]:
        """Evaluate resource limit policy."""
        if not request.resource_usage:
            return None
        
        violations = []
        
        # Check memory
        memory_mb = request.resource_usage.get('memory_mb', 0)
        if memory_mb > settings.guardrail_max_memory_mb:
            violations.append(f"Memory usage ({memory_mb}MB) exceeds limit ({settings.guardrail_max_memory_mb}MB)")
        
        # Check CPU
        cpu_percent = request.resource_usage.get('cpu_percent', 0)
        if cpu_percent > settings.guardrail_max_cpu_percent:
            violations.append(f"CPU usage ({cpu_percent}%) exceeds limit ({settings.guardrail_max_cpu_percent}%)")
        
        if violations:
            return PolicyViolation(
                policy_id=policy.policy_id,
                policy_name=policy.policy_name,
                policy_type=policy.policy_type,
                tenant_id=request.tenant_id,
                task_id=request.task_id,
                agent_id=request.agent_id,
                severity=policy.severity,
                action_taken=policy.action,
                violation_details={
                    "message": "Resource limits exceeded",
                    "violations": violations,
                    "resource_usage": request.resource_usage
                }
            )
        
        return None
    
    async def _evaluate_execution_time_policy(
        self,
        policy: GuardrailPolicy,
        request: GuardrailEvaluationRequest
    ) -> Optional[PolicyViolation]:
        """Evaluate execution time policy."""
        if not request.execution_time:
            return None
        
        if request.execution_time > settings.guardrail_max_execution_time_seconds:
            return PolicyViolation(
                policy_id=policy.policy_id,
                policy_name=policy.policy_name,
                policy_type=policy.policy_type,
                tenant_id=request.tenant_id,
                task_id=request.task_id,
                agent_id=request.agent_id,
                severity=policy.severity,
                action_taken=policy.action,
                violation_details={
                    "message": "Execution time exceeds threshold",
                    "limit_seconds": settings.guardrail_max_execution_time_seconds,
                    "actual_seconds": request.execution_time
                }
            )
        
        return None
    
    def _cleanup_rate_limits(self, tenant_id: str, now: datetime):
        """Clean up old rate limit entries."""
        # Keep only last 2 hours of data
        cutoff = now - timedelta(hours=2)
        cutoff_minute = cutoff.strftime("%Y-%m-%d-%H-%M")
        cutoff_hour = cutoff.strftime("%Y-%m-%d-%H")
        
        # Remove old entries
        keys_to_remove = [
            k for k in self.request_counts[tenant_id].keys()
            if k < cutoff_minute or k < cutoff_hour
        ]
        for key in keys_to_remove:
            del self.request_counts[tenant_id][key]
    
    async def notify_orchestrator(self, violation: PolicyViolation):
        """
        Notify orchestrator service about policy violation.
        Used to block tasks when action is BLOCK.
        """
        if violation.action_taken != PolicyAction.BLOCK:
            return
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.orchestrator_url}/api/v1/tasks/{violation.task_id}/block",
                    json={
                        "reason": "guardrail_violation",
                        "policy_id": violation.policy_id,
                        "policy_name": violation.policy_name,
                        "violation_details": violation.violation_details
                    },
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Notified orchestrator about violation for task {violation.task_id}")
                else:
                    logger.warning(f"Failed to notify orchestrator: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error notifying orchestrator: {e}")
    
    async def get_policy_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get statistics about policy evaluations and violations."""
        # Get violations from last 24 hours
        start_time = datetime.utcnow() - timedelta(hours=24)
        violations = await db_manager.get_violations(tenant_id, start_time=start_time)
        
        # Calculate statistics
        total_violations = len(violations)
        violations_by_type = defaultdict(int)
        violations_by_severity = defaultdict(int)
        
        for violation in violations:
            violations_by_type[violation.get('policy_type')] += 1
            violations_by_severity[violation.get('severity')] += 1
        
        return {
            "tenant_id": tenant_id,
            "period_hours": 24,
            "total_violations": total_violations,
            "violations_by_type": dict(violations_by_type),
            "violations_by_severity": dict(violations_by_severity),
            "current_rate_limits": dict(self.request_counts.get(tenant_id, {})),
            "current_costs": dict(self.cost_tracking.get(tenant_id, {}))
        }


# Global guardrail engine instance
guardrail_engine = GuardrailEngine()

# Made with Bob
