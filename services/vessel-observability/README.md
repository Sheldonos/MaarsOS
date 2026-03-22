# Vessel Observability Service

The Vessel Observability Service provides comprehensive observability, guardrail enforcement, and anomaly detection for the MAARS platform. It monitors system behavior, enforces policies, and detects anomalies in real-time.

## Features

### 🛡️ Guardrail Enforcement
- **Content Filtering**: Profanity, PII, and sensitive data detection
- **Rate Limiting**: Per-minute, per-hour, and per-day request limits
- **Cost Thresholds**: Per-task and per-tenant cost limits
- **Resource Limits**: CPU, memory, and execution time constraints
- **Compliance Rules**: Data retention and audit logging

### 🔍 Anomaly Detection
- **Statistical Detection**: Z-score based anomaly detection
- **Latency Monitoring**: P95/P99 latency spike detection
- **Error Rate Tracking**: Sudden error rate increases
- **Cost Anomalies**: Unexpected spending patterns
- **Resource Monitoring**: CPU/memory usage spikes
- **Pattern Analysis**: Unusual request patterns

### 📊 Observability
- **Distributed Tracing**: OpenTelemetry integration
- **Metrics Collection**: Prometheus-compatible metrics
- **Event Streaming**: Kafka event publishing
- **Real-time Monitoring**: Live system health tracking

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Vessel Observability Service                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Guardrail   │  │   Anomaly    │  │  Telemetry   │      │
│  │   Engine     │  │   Detector   │  │   Manager    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
│         ┌──────────────────┴──────────────────┐             │
│         │                                      │             │
│  ┌──────▼──────┐                      ┌───────▼──────┐      │
│  │  Database   │                      │    Kafka     │      │
│  │  (AstraDB/  │                      │   Producer   │      │
│  │  PostgreSQL)│                      └──────────────┘      │
│  └─────────────┘                                             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
         │                                      │
         │                                      │
    ┌────▼────┐                          ┌─────▼─────┐
    │ Storage │                          │   Kafka   │
    └─────────┘                          └───────────┘
```

## API Endpoints

### Health & Metrics
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

### Guardrail Evaluation
- `POST /api/v1/guardrails/evaluate` - Evaluate guardrail policies

### Anomaly Detection
- `POST /api/v1/anomalies/detect` - Detect anomalies in metrics

### Metrics Management
- `GET /api/v1/metrics` - Query metrics
- `POST /api/v1/metrics` - Store metric data

### Trace Management
- `POST /api/v1/traces` - Receive and analyze traces

### Policy Management
- `GET /api/v1/policies` - List policies
- `POST /api/v1/policies` - Create policy
- `GET /api/v1/policies/{policy_id}` - Get policy
- `PUT /api/v1/policies/{policy_id}` - Update policy
- `DELETE /api/v1/policies/{policy_id}` - Delete policy

### Statistics
- `GET /api/v1/stats/violations` - Violation statistics
- `GET /api/v1/stats/anomalies` - Anomaly statistics
- `GET /api/v1/stats/service` - Service metrics

## Configuration

### Environment Variables

```bash
# Service Configuration
SERVICE_NAME=vessel-observability
SERVICE_VERSION=1.0.0
ENVIRONMENT=production
PORT=8087
HOST=0.0.0.0
LOG_LEVEL=INFO

# Database Configuration
DATABASE_TYPE=astradb  # or postgresql

# AstraDB Configuration
ASTRA_DB_ID=your-db-id
ASTRA_DB_REGION=us-east-1
ASTRA_DB_KEYSPACE=maars
ASTRA_DB_TOKEN=your-token
ASTRA_DB_SECURE_BUNDLE_PATH=/path/to/bundle.zip

# PostgreSQL Configuration (fallback)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=maars_observability
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_PREFIX=maars
KAFKA_CONSUMER_GROUP=observability-service

# OpenTelemetry Configuration
OTEL_ENABLED=true
OTEL_EXPORTER_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=vessel-observability

# Guardrail Thresholds
GUARDRAIL_MAX_REQUESTS_PER_MINUTE=100
GUARDRAIL_MAX_REQUESTS_PER_HOUR=1000
GUARDRAIL_MAX_COST_PER_TASK=10.0
GUARDRAIL_MAX_COST_PER_TENANT_DAILY=1000.0
GUARDRAIL_MAX_EXECUTION_TIME_SECONDS=300
GUARDRAIL_MAX_MEMORY_MB=2048
GUARDRAIL_MAX_CPU_PERCENT=80

# Content Filtering
CONTENT_FILTER_ENABLED=true
CONTENT_FILTER_PROFANITY=true
CONTENT_FILTER_PII=true
CONTENT_FILTER_SENSITIVE_DATA=true

# Anomaly Detection
ANOMALY_DETECTION_ENABLED=true
ANOMALY_Z_SCORE_THRESHOLD=3.0
ANOMALY_WINDOW_SIZE=100
ANOMALY_MIN_SAMPLES=30

# Latency Thresholds
LATENCY_P95_THRESHOLD_MS=1000
LATENCY_P99_THRESHOLD_MS=2000

# Error Rate Thresholds
ERROR_RATE_THRESHOLD_PERCENT=5.0
ERROR_RATE_WINDOW_MINUTES=5

# Integration Endpoints
ORCHESTRATOR_URL=http://localhost:8081
LLM_ROUTER_URL=http://localhost:8083
SWARM_URL=http://localhost:8086
ECONOMICS_URL=http://localhost:8088
```

## Guardrail Policy Examples

### Content Policy
```json
{
  "tenant_id": "tenant-123",
  "policy_name": "Content Filter",
  "policy_type": "content",
  "description": "Filter profanity and PII",
  "enabled": true,
  "severity": "high",
  "action": "block",
  "content_config": {
    "check_profanity": true,
    "check_pii": true,
    "check_sensitive_data": true,
    "blocked_patterns": ["password", "secret"],
    "allowed_patterns": []
  }
}
```

### Rate Limit Policy
```json
{
  "tenant_id": "tenant-123",
  "policy_name": "API Rate Limit",
  "policy_type": "rate_limit",
  "description": "Limit API requests",
  "enabled": true,
  "severity": "medium",
  "action": "warn",
  "rate_limit_config": {
    "max_requests_per_minute": 100,
    "max_requests_per_hour": 1000,
    "max_requests_per_day": 10000,
    "burst_size": 10
  }
}
```

### Cost Threshold Policy
```json
{
  "tenant_id": "tenant-123",
  "policy_name": "Cost Control",
  "policy_type": "cost_threshold",
  "description": "Control spending",
  "enabled": true,
  "severity": "critical",
  "action": "block",
  "cost_threshold_config": {
    "max_cost_per_task": 10.0,
    "max_cost_per_tenant_daily": 1000.0,
    "max_cost_per_tenant_monthly": 30000.0,
    "alert_threshold_percent": 80.0
  }
}
```

### Resource Limit Policy
```json
{
  "tenant_id": "tenant-123",
  "policy_name": "Resource Limits",
  "policy_type": "resource_limit",
  "description": "Limit resource usage",
  "enabled": true,
  "severity": "high",
  "action": "block",
  "resource_limit_config": {
    "max_memory_mb": 2048,
    "max_cpu_percent": 80,
    "max_disk_mb": 10240,
    "max_network_mbps": 100
  }
}
```

## Usage Examples

### Evaluate Guardrails
```bash
curl -X POST http://localhost:8087/api/v1/guardrails/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-123",
    "task_id": "task-456",
    "content": "Sample content to evaluate",
    "cost_estimate": 5.0,
    "resource_usage": {
      "memory_mb": 512,
      "cpu_percent": 45
    }
  }'
```

### Detect Anomalies
```bash
curl -X POST http://localhost:8087/api/v1/anomalies/detect \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-123",
    "metric_name": "api.latency",
    "metric_value": 2500.0,
    "metric_type": "histogram"
  }'
```

### Create Policy
```bash
curl -X POST http://localhost:8087/api/v1/policies \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-123",
    "policy_name": "My Policy",
    "policy_type": "rate_limit",
    "description": "Custom rate limit",
    "enabled": true,
    "severity": "medium",
    "action": "warn",
    "rate_limit_config": {
      "max_requests_per_minute": 50
    }
  }'
```

### Query Metrics
```bash
curl -X GET "http://localhost:8087/api/v1/metrics?metric_name=api.latency&tenant_id=tenant-123&aggregation=avg"
```

## Deployment

### Docker
```bash
# Build image
docker build -t vessel-observability:latest .

# Run container
docker run -d \
  --name vessel-observability \
  -p 8087:8087 \
  -e DATABASE_TYPE=astradb \
  -e ASTRA_DB_TOKEN=your-token \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
  vessel-observability:latest
```

### Docker Compose
```yaml
version: '3.8'
services:
  vessel-observability:
    build: .
    ports:
      - "8087:8087"
    environment:
      - DATABASE_TYPE=astradb
      - ASTRA_DB_TOKEN=${ASTRA_DB_TOKEN}
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
      - OTEL_EXPORTER_ENDPOINT=http://otel-collector:4318
    depends_on:
      - kafka
      - otel-collector
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vessel-observability
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vessel-observability
  template:
    metadata:
      labels:
        app: vessel-observability
    spec:
      containers:
      - name: vessel-observability
        image: vessel-observability:latest
        ports:
        - containerPort: 8087
        env:
        - name: DATABASE_TYPE
          value: "astradb"
        - name: ASTRA_DB_TOKEN
          valueFrom:
            secretKeyRef:
              name: astra-credentials
              key: token
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8087
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8087
          initialDelaySeconds: 10
          periodSeconds: 5
```

## Integration Examples

### With Vessel Orchestrator
```python
import httpx

async def check_guardrails(task_data):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://vessel-observability:8087/api/v1/guardrails/evaluate",
            json={
                "tenant_id": task_data["tenant_id"],
                "task_id": task_data["task_id"],
                "content": task_data["content"],
                "cost_estimate": task_data["estimated_cost"]
            }
        )
        result = response.json()
        return result["allowed"]
```

### With Vessel LLM Router
```python
async def monitor_llm_cost(tenant_id, cost):
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://vessel-observability:8087/api/v1/anomalies/detect",
            json={
                "tenant_id": tenant_id,
                "metric_name": "llm.cost",
                "metric_value": cost,
                "metric_type": "counter"
            }
        )
```

## Monitoring

### Prometheus Metrics
- `observability_requests_total` - Total requests by endpoint
- `observability_request_duration_seconds` - Request duration
- `observability_policy_evaluation_duration` - Policy evaluation time
- `observability_policy_violations_total` - Total violations
- `observability_anomaly_detection_duration` - Detection time
- `observability_anomalies_total` - Total anomalies detected

### Grafana Dashboard
Import the provided Grafana dashboard for visualization:
- Policy violation trends
- Anomaly detection rates
- Service performance metrics
- Cost tracking

## Development

### Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py
```

### Testing
```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=app tests/
```

## Troubleshooting

### Common Issues

**Database Connection Failed**
- Verify AstraDB credentials
- Check network connectivity
- Ensure secure bundle path is correct

**Kafka Connection Failed**
- Verify Kafka bootstrap servers
- Check Kafka is running
- Verify topic permissions

**High Memory Usage**
- Reduce `ANOMALY_WINDOW_SIZE`
- Increase `ANOMALY_MIN_SAMPLES`
- Enable metric aggregation

**False Positive Anomalies**
- Increase `ANOMALY_Z_SCORE_THRESHOLD`
- Increase `ANOMALY_MIN_SAMPLES`
- Review baseline data

## Performance Tuning

### Database Optimization
- Use connection pooling
- Enable query caching
- Index frequently queried fields

### Anomaly Detection
- Adjust window size based on traffic
- Use appropriate z-score threshold
- Enable metric sampling for high-volume metrics

### Guardrail Evaluation
- Cache policy definitions
- Use async evaluation
- Batch policy checks

## Security

- All endpoints support authentication (configure via middleware)
- Sensitive data is encrypted at rest
- PII detection prevents data leakage
- Audit logging for all policy changes
- Rate limiting prevents abuse

## License

Copyright © 2026 MAARS Platform. All rights reserved.

## Support

For issues and questions:
- GitHub Issues: [maarsOS/issues](https://github.com/maarsOS/issues)
- Documentation: [docs.maars.io](https://docs.maars.io)
- Email: support@maars.io