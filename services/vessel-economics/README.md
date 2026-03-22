# Vessel Economics Service

The Vessel Economics Service provides comprehensive cost tracking, budget enforcement, escrow management, and compliance reporting for the MAARS platform. It ensures financial transparency, prevents budget overruns, and maintains detailed audit trails for regulatory compliance.

## Features

### 🏦 Escrow Management
- **Budget Allocation**: Allocate funds to tenant escrow accounts
- **Fund Locking**: Lock funds for task execution with automatic release
- **Transaction Management**: Track all escrow transactions with full audit trail
- **Balance Tracking**: Real-time balance and availability monitoring
- **Multi-tenant Isolation**: Secure separation of tenant funds

### 💰 Cost Tracking
- **Real-time Cost Calculation**: Automatic cost calculation for LLM API calls
- **Provider-specific Pricing**: Support for OpenAI, Anthropic, Google, and more
- **Token-based Billing**: Accurate per-token cost tracking
- **Multi-dimensional Aggregation**: Costs by tenant, agent, task, category, provider, model
- **Historical Analysis**: Cost trends and top cost drivers

### 🚦 Budget Enforcement
- **Pre-execution Checks**: Validate budget availability before task execution
- **Automatic Rejection**: Block tasks when budget is exceeded
- **Threshold Alerts**: Warnings at 80%, 90%, and 100% budget utilization
- **Soft vs Hard Limits**: Configurable warning vs blocking behavior
- **Integration with Orchestrator**: Seamless budget validation in task workflow

### 📊 Compliance Reporting
- **Audit Trail**: Complete transaction history with 7-year retention
- **Compliance Reports**: Multiple report types (audit trail, cost summary, budget analysis, etc.)
- **Data Export**: JSON, CSV, and PDF formats
- **Regulatory Compliance**: SOC 2 and GDPR-ready features
- **Transaction Reconciliation**: Automated reconciliation and verification

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Vessel Economics Service                    │
│                         (Port 8090)                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Escrow     │  │     Cost     │  │    Budget    │      │
│  │  Manager     │  │   Tracker    │  │  Enforcer    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Compliance   │  │    Kafka     │  │   Database   │      │
│  │  Reporter    │  │  Producer    │  │   Manager    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
   PostgreSQL/           Kafka Topics         Prometheus
    AstraDB              (Events)              (Metrics)
```

## API Endpoints

### Escrow Management

#### Allocate Budget
```http
POST /api/v1/escrow/allocate
Content-Type: application/json

{
  "tenant_id": "tenant-123",
  "amount": "1000.00",
  "description": "Monthly budget allocation"
}
```

#### Release Escrow Funds
```http
POST /api/v1/escrow/release
Content-Type: application/json

{
  "tenant_id": "tenant-123",
  "transaction_id": "tx-456",
  "amount": "50.00",
  "reason": "Task completed successfully"
}
```

#### Get Escrow Balance
```http
GET /api/v1/escrow/{tenant_id}
```

### Cost Tracking

#### Track Cost
```http
POST /api/v1/costs/track
Content-Type: application/json

{
  "tenant_id": "tenant-123",
  "task_id": "task-789",
  "agent_id": "agent-001",
  "category": "llm_api",
  "provider": "openai",
  "model": "gpt-4",
  "input_tokens": 1000,
  "output_tokens": 500,
  "cost": "0.00"
}
```

#### Get Cost Summary
```http
GET /api/v1/costs/summary?tenant_id=tenant-123&days=30
```

#### Get Costs by Tenant
```http
GET /api/v1/costs/by-tenant/{tenant_id}?days=30
```

#### Get Costs by Agent
```http
GET /api/v1/costs/by-agent/{agent_id}?days=30
```

### Budget Enforcement

#### Check Budget
```http
POST /api/v1/budget/check
Content-Type: application/json

{
  "tenant_id": "tenant-123",
  "estimated_cost": "25.50",
  "task_id": "task-789"
}
```

#### Enforce Budget
```http
POST /api/v1/budget/enforce
Content-Type: application/json

{
  "tenant_id": "tenant-123",
  "task_id": "task-789",
  "estimated_cost": "25.50",
  "force": false
}
```

#### Get Budget Status
```http
GET /api/v1/budget/{tenant_id}
```

### Compliance

#### Generate Compliance Report
```http
POST /api/v1/compliance/report
Content-Type: application/json

{
  "tenant_id": "tenant-123",
  "report_type": "cost_summary",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-31T23:59:59Z",
  "format": "json",
  "include_metadata": true
}
```

#### Get Audit Trail
```http
GET /api/v1/compliance/audit-trail?tenant_id=tenant-123&days=30&limit=100
```

### Billing

#### Generate Invoice
```http
GET /api/v1/billing/invoice/{tenant_id}?start_date=2024-01-01&end_date=2024-01-31
```

## Cost Calculation

### LLM Provider Pricing (per 1K tokens)

#### OpenAI
- **GPT-4**: Input $0.03, Output $0.06
- **GPT-4 Turbo**: Input $0.01, Output $0.03
- **GPT-3.5-turbo**: Input $0.0015, Output $0.002

#### Anthropic
- **Claude 3 Opus**: Input $0.015, Output $0.075
- **Claude 3 Sonnet**: Input $0.003, Output $0.015
- **Claude 3 Haiku**: Input $0.00025, Output $0.00125
- **Claude 2**: Input $0.008, Output $0.024

#### Google
- **PaLM 2**: Input $0.00025, Output $0.0005

### Cost Calculation Example

```python
# For GPT-4 with 1,500 input tokens and 800 output tokens:
input_cost = (1500 / 1000) * 0.03 = $0.045
output_cost = (800 / 1000) * 0.06 = $0.048
total_cost = $0.093
```

## Budget Enforcement

### Budget Thresholds

- **Warning (80%)**: Soft alert, task continues
- **Critical (90%)**: Strong warning, task continues
- **Exhausted (100%)**: Hard limit, task rejected (if enabled)

### Budget Enforcement Flow

```
1. Task submitted to orchestrator
2. Orchestrator calls /api/v1/budget/enforce
3. Economics service checks budget availability
4. If budget available:
   - Lock estimated funds in escrow
   - Allow task execution
5. If budget exceeded:
   - Reject task (if hard limits enabled)
   - Publish budget.exceeded event
   - Send alert to tenant
6. On task completion:
   - Track actual cost
   - Release locked funds
   - Update budget usage
```

## Configuration

### Environment Variables

```bash
# Service Configuration
SERVICE_NAME=vessel-economics
SERVICE_VERSION=1.0.0
PORT=8090
LOG_LEVEL=INFO

# Database Configuration
DATABASE_TYPE=postgresql  # or astradb
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=vessel_economics
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_PREFIX=vessel.economics

# Budget Configuration
DEFAULT_TENANT_BUDGET=1000.00
BUDGET_WARNING_THRESHOLD=0.80
BUDGET_CRITICAL_THRESHOLD=0.90
ENABLE_HARD_LIMITS=true
ENABLE_SOFT_LIMITS=true

# Compliance Configuration
AUDIT_TRAIL_RETENTION_DAYS=2555  # 7 years
ENABLE_DETAILED_LOGGING=true
ENABLE_TRANSACTION_RECONCILIATION=true

# Integration Endpoints
VESSEL_LLM_ROUTER_URL=http://localhost:8083
VESSEL_ORCHESTRATOR_URL=http://localhost:8081
VESSEL_OBSERVABILITY_URL=http://localhost:8089
```

## Deployment

### Docker

```bash
# Build image
docker build -t vessel-economics:latest .

# Run container
docker run -d \
  --name vessel-economics \
  -p 8090:8090 \
  -e POSTGRES_HOST=postgres \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
  vessel-economics:latest
```

### Docker Compose

```yaml
services:
  vessel-economics:
    build: ./services/vessel-economics
    ports:
      - "8090:8090"
    environment:
      - POSTGRES_HOST=postgres
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
      - LOG_LEVEL=INFO
    depends_on:
      - postgres
      - kafka
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8090/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vessel-economics
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vessel-economics
  template:
    metadata:
      labels:
        app: vessel-economics
    spec:
      containers:
      - name: vessel-economics
        image: vessel-economics:latest
        ports:
        - containerPort: 8090
        env:
        - name: POSTGRES_HOST
          value: "postgres-service"
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: "kafka-service:9092"
        livenessProbe:
          httpGet:
            path: /health
            port: 8090
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8090
          initialDelaySeconds: 10
          periodSeconds: 5
```

## Integration Examples

### Integration with vessel-orchestrator

```python
# In vessel-orchestrator before task execution
import httpx

async def validate_budget(tenant_id: str, estimated_cost: float, task_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://vessel-economics:8090/api/v1/budget/enforce",
            json={
                "tenant_id": tenant_id,
                "task_id": task_id,
                "estimated_cost": str(estimated_cost),
                "force": False
            }
        )
        result = response.json()
        return result["allowed"], result["message"]
```

### Integration with vessel-llm-router

```python
# In vessel-llm-router after LLM API call
import httpx

async def track_llm_cost(
    tenant_id: str,
    task_id: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int
):
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://vessel-economics:8090/api/v1/costs/track",
            json={
                "tenant_id": tenant_id,
                "task_id": task_id,
                "category": "llm_api",
                "provider": provider,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": "0.00"  # Will be calculated automatically
            }
        )
```

## Monitoring

### Prometheus Metrics

```
# Escrow metrics
economics_escrow_allocations_total
economics_escrow_releases_total
economics_escrow_balance_usd{tenant_id}

# Cost metrics
economics_costs_tracked_total{category}
economics_cost_amount_usd

# Budget metrics
economics_budget_checks_total{result}
economics_budget_exceeded_total
economics_budget_utilization_percent{tenant_id}

# Compliance metrics
economics_compliance_reports_total{type}

# Performance metrics
economics_request_duration_seconds{endpoint}
```

### Grafana Dashboard

Import the provided Grafana dashboard for visualization:
- Escrow balances by tenant
- Cost trends over time
- Budget utilization gauges
- Top cost drivers
- Alert history

## Events Published

### Kafka Topics

- `vessel.economics.cost.tracked` - Cost record created
- `vessel.economics.budget.exceeded` - Budget limit exceeded
- `vessel.economics.budget.alert` - Budget threshold alert
- `vessel.economics.escrow.allocated` - Funds allocated to escrow
- `vessel.economics.escrow.released` - Funds released from escrow
- `vessel.economics.escrow.refunded` - Funds refunded
- `vessel.economics.invoice.generated` - Invoice created
- `vessel.economics.compliance.report.created` - Compliance report generated

## Development

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

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

# Integration tests
pytest tests/integration/
```

## Security

- **Non-root User**: Container runs as non-root user
- **Input Validation**: All inputs validated with Pydantic
- **SQL Injection Prevention**: Parameterized queries
- **Decimal Precision**: All monetary values use Decimal type
- **Audit Trail**: Complete transaction history
- **Multi-tenant Isolation**: Secure tenant data separation

## Troubleshooting

### Common Issues

**Issue**: Database connection failed
```bash
# Check database connectivity
psql -h localhost -U postgres -d vessel_economics

# Verify environment variables
echo $POSTGRES_HOST
echo $POSTGRES_PORT
```

**Issue**: Kafka connection failed
```bash
# Check Kafka connectivity
kafka-topics.sh --list --bootstrap-server localhost:9092

# Verify Kafka configuration
echo $KAFKA_BOOTSTRAP_SERVERS
```

**Issue**: Budget not enforcing
```bash
# Check budget configuration
curl http://localhost:8090/api/v1/budget/{tenant_id}

# Verify hard limits enabled
echo $ENABLE_HARD_LIMITS
```

## License

Copyright © 2024 MAARS Platform. All rights reserved.

## Support

For issues and questions:
- GitHub Issues: https://github.com/maars/vessel-economics/issues
- Documentation: https://docs.maars.ai/economics
- Email: support@maars.ai