"""
Vessel Observability Service - Main FastAPI Application

Provides observability, guardrail enforcement, and anomaly detection
for the MAARS platform.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import uvicorn

from app.config import settings
from app.models import (
    GuardrailPolicy,
    GuardrailEvaluationRequest,
    GuardrailEvaluationResponse,
    AnomalyDetectionRequest,
    AnomalyDetectionResponse,
    MetricData,
    MetricQuery,
    MetricResponse,
    TraceData,
    TraceQuery,
    HealthStatus,
    ServiceMetrics,
)
from app.database import db_manager
from app.guardrails import guardrail_engine
from app.anomaly_detector import anomaly_detector
from app.telemetry import telemetry_manager
from app.kafka_producer import kafka_producer

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
request_count = Counter(
    'observability_requests_total',
    'Total requests',
    ['endpoint', 'method', 'status']
)
request_duration = Histogram(
    'observability_request_duration_seconds',
    'Request duration',
    ['endpoint', 'method']
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.service_name} v{settings.service_version}")
    
    try:
        # Initialize database
        await db_manager.connect()
        
        # Initialize telemetry
        telemetry_manager.initialize()
        
        # Initialize Kafka
        kafka_producer.connect()
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down services...")
    
    try:
        await db_manager.disconnect()
        telemetry_manager.shutdown()
        kafka_producer.disconnect()
        
        logger.info("Shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="Vessel Observability Service",
    description="Observability, guardrail enforcement, and anomaly detection for MAARS",
    version=settings.service_version,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    checks = {
        "database": db_manager.session is not None or db_manager.pool is not None,
        "kafka": kafka_producer.producer is not None,
        "telemetry": telemetry_manager.tracer is not None,
    }
    
    all_healthy = all(checks.values())
    
    return HealthStatus(
        status="healthy" if all_healthy else "degraded",
        version=settings.service_version,
        checks=checks,
        details={
            "service": settings.service_name,
            "environment": settings.environment,
            "port": settings.port
        }
    )


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# Guardrail endpoints
@app.post("/api/v1/guardrails/evaluate", response_model=GuardrailEvaluationResponse)
async def evaluate_guardrails(request: GuardrailEvaluationRequest):
    """
    Evaluate guardrail policies for a request.
    
    Args:
        request: Evaluation request
        
    Returns:
        Evaluation response with violations and warnings
    """
    start_time = datetime.utcnow()
    
    try:
        with telemetry_manager.trace_operation(
            "evaluate_guardrails",
            {"tenant_id": request.tenant_id}
        ):
            response = await guardrail_engine.evaluate(request)
            
            # Record metrics
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            telemetry_manager.record_policy_evaluation(
                request.tenant_id,
                duration_ms,
                len(response.violations)
            )
            
            # Send violations to Kafka
            for violation in response.violations:
                await kafka_producer.send_guardrail_violation(violation)
            
            request_count.labels(
                endpoint="/api/v1/guardrails/evaluate",
                method="POST",
                status="200"
            ).inc()
            
            return response
            
    except Exception as e:
        logger.error(f"Error evaluating guardrails: {e}")
        request_count.labels(
            endpoint="/api/v1/guardrails/evaluate",
            method="POST",
            status="500"
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Anomaly detection endpoints
@app.post("/api/v1/anomalies/detect", response_model=AnomalyDetectionResponse)
async def detect_anomalies(request: AnomalyDetectionRequest):
    """
    Detect anomalies in metric data.
    
    Args:
        request: Anomaly detection request
        
    Returns:
        Detection response
    """
    start_time = datetime.utcnow()
    
    try:
        with telemetry_manager.trace_operation(
            "detect_anomalies",
            {"tenant_id": request.tenant_id, "metric": request.metric_name}
        ):
            response = await anomaly_detector.detect(request)
            
            # Record metrics
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            telemetry_manager.record_anomaly_detection(
                request.tenant_id,
                duration_ms,
                response.is_anomaly
            )
            
            # Send anomaly to Kafka if detected
            if response.is_anomaly and response.anomaly:
                await kafka_producer.send_anomaly_detected(response.anomaly)
            
            request_count.labels(
                endpoint="/api/v1/anomalies/detect",
                method="POST",
                status="200"
            ).inc()
            
            return response
            
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")
        request_count.labels(
            endpoint="/api/v1/anomalies/detect",
            method="POST",
            status="500"
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Metrics endpoints
@app.get("/api/v1/metrics", response_model=MetricResponse)
async def get_metrics(query: MetricQuery):
    """
    Get metrics data.
    
    Args:
        query: Metric query parameters
        
    Returns:
        Metrics response
    """
    try:
        metrics_data = await db_manager.get_metrics(
            metric_name=query.metric_name,
            tenant_id=query.tenant_id,
            start_time=query.start_time,
            end_time=query.end_time
        )
        
        # Convert to MetricData objects
        metrics = [
            MetricData(
                metric_name=m.get('metric_name'),
                metric_type=m.get('metric_type'),
                value=m.get('value'),
                timestamp=m.get('timestamp'),
                labels=m.get('labels', {}),
                tenant_id=m.get('tenant_id')
            )
            for m in metrics_data
        ]
        
        # Calculate aggregated value if requested
        aggregated_value = None
        if query.aggregation and metrics:
            values = [m.value for m in metrics]
            if query.aggregation == "avg":
                aggregated_value = sum(values) / len(values)
            elif query.aggregation == "sum":
                aggregated_value = sum(values)
            elif query.aggregation == "min":
                aggregated_value = min(values)
            elif query.aggregation == "max":
                aggregated_value = max(values)
            elif query.aggregation == "count":
                aggregated_value = len(values)
        
        return MetricResponse(
            metrics=metrics,
            total_count=len(metrics),
            aggregated_value=aggregated_value
        )
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/api/v1/metrics")
async def store_metric(metric: MetricData):
    """
    Store a metric data point.
    
    Args:
        metric: Metric data
        
    Returns:
        Success response
    """
    try:
        metric_id = await db_manager.store_metric(metric)
        
        return {
            "status": "success",
            "metric_id": metric_id,
            "message": "Metric stored successfully"
        }
        
    except Exception as e:
        logger.error(f"Error storing metric: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Trace endpoints
@app.post("/api/v1/traces")
async def receive_trace(trace: TraceData):
    """
    Receive and process trace data.
    
    Args:
        trace: Trace data
        
    Returns:
        Analysis results
    """
    try:
        analysis = await telemetry_manager.process_trace(trace)
        
        return {
            "status": "success",
            "trace_id": trace.trace_id,
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"Error processing trace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Policy management endpoints
@app.get("/api/v1/policies")
async def list_policies(tenant_id: str, enabled_only: bool = False):
    """
    List guardrail policies for a tenant.
    
    Args:
        tenant_id: Tenant identifier
        enabled_only: Only return enabled policies
        
    Returns:
        List of policies
    """
    try:
        policies = await db_manager.list_policies(tenant_id, enabled_only)
        
        return {
            "status": "success",
            "tenant_id": tenant_id,
            "count": len(policies),
            "policies": policies
        }
        
    except Exception as e:
        logger.error(f"Error listing policies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/api/v1/policies")
async def create_policy(policy: GuardrailPolicy):
    """
    Create a new guardrail policy.
    
    Args:
        policy: Policy definition
        
    Returns:
        Created policy ID
    """
    try:
        policy_id = await db_manager.create_policy(policy)
        
        # Send event to Kafka
        await kafka_producer.send_policy_created(
            policy_id,
            policy.tenant_id,
            policy.policy_name,
            policy.policy_type.value
        )
        
        return {
            "status": "success",
            "policy_id": policy_id,
            "message": "Policy created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/v1/policies/{policy_id}")
async def get_policy(policy_id: str):
    """
    Get a guardrail policy by ID.
    
    Args:
        policy_id: Policy identifier
        
    Returns:
        Policy details
    """
    try:
        policy = await db_manager.get_policy(policy_id)
        
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Policy not found"
            )
        
        return {
            "status": "success",
            "policy": policy
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.put("/api/v1/policies/{policy_id}")
async def update_policy(policy_id: str, updates: Dict[str, Any]):
    """
    Update a guardrail policy.
    
    Args:
        policy_id: Policy identifier
        updates: Fields to update
        
    Returns:
        Success response
    """
    try:
        success = await db_manager.update_policy(policy_id, updates)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Policy not found"
            )
        
        # Get updated policy for event
        policy = await db_manager.get_policy(policy_id)
        if policy:
            await kafka_producer.send_policy_updated(
                policy_id,
                policy.get('tenant_id'),
                policy.get('policy_name'),
                updates
            )
        
        return {
            "status": "success",
            "policy_id": policy_id,
            "message": "Policy updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.delete("/api/v1/policies/{policy_id}")
async def delete_policy(policy_id: str):
    """
    Delete a guardrail policy.
    
    Args:
        policy_id: Policy identifier
        
    Returns:
        Success response
    """
    try:
        success = await db_manager.delete_policy(policy_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Policy not found"
            )
        
        return {
            "status": "success",
            "policy_id": policy_id,
            "message": "Policy deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Statistics endpoints
@app.get("/api/v1/stats/violations")
async def get_violation_stats(tenant_id: str):
    """
    Get policy violation statistics.
    
    Args:
        tenant_id: Tenant identifier
        
    Returns:
        Violation statistics
    """
    try:
        stats = await guardrail_engine.get_policy_stats(tenant_id)
        
        return {
            "status": "success",
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting violation stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/v1/stats/anomalies")
async def get_anomaly_stats(tenant_id: str, hours: int = 24):
    """
    Get anomaly detection statistics.
    
    Args:
        tenant_id: Tenant identifier
        hours: Time window in hours
        
    Returns:
        Anomaly statistics
    """
    try:
        summary = await anomaly_detector.get_anomaly_summary(tenant_id, hours)
        
        return {
            "status": "success",
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error getting anomaly stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/v1/stats/service", response_model=ServiceMetrics)
async def get_service_metrics():
    """
    Get service-level metrics.
    
    Returns:
        Service metrics
    """
    try:
        # This is a simplified version - in production, aggregate from database
        return ServiceMetrics(
            total_policies=0,
            active_policies=0,
            total_violations=0,
            violations_last_hour=0,
            total_anomalies=0,
            anomalies_last_hour=0,
            avg_evaluation_time_ms=0.0,
            avg_detection_time_ms=0.0
        )
        
    except Exception as e:
        logger.error(f"Error getting service metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )

# Made with Bob
