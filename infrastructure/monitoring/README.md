# MAARS Monitoring Infrastructure

Phase 3 monitoring infrastructure for observability, metrics, logs, and alerting.

## Overview

This monitoring stack provides comprehensive observability for the MAARS platform using industry-standard tools:

- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **Loki**: Log aggregation and querying
- **Promtail**: Log shipping to Loki
- **Exporters**: Redis and PostgreSQL metrics exporters

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MAARS Services                          │
│  (Gateway, Orchestrator, Sandbox, LLM Router, Swarm, etc.) │
└────────────┬────────────────────────────┬──────────────────┘
             │                            │
             │ Metrics (/metrics)         │ Logs (stdout/stderr)
             │                            │
             ▼                            ▼
      ┌─────────────┐            ┌──────────────┐
      │ Prometheus  │            │  Promtail    │
      │  :9090      │            │              │
      └──────┬──────┘            └──────┬───────┘
             │                          │
             │                          ▼
             │                   ┌──────────────┐
             │                   │    Loki      │
             │                   │   :3100      │
             │                   └──────┬───────┘
             │                          │
             └──────────┬───────────────┘
                        │
                        ▼
                 ┌─────────────┐
                 │   Grafana   │
                 │    :3000    │
                 └─────────────┘
```

## Components

### Prometheus (Port 9090)

Metrics collection and alerting engine.

**Features:**
- 15-second scrape interval
- 15-day retention period
- Comprehensive alert rules
- Service discovery for all MAARS services

**Access:**
- UI: http://localhost:9090
- API: http://localhost:9090/api/v1

**Configuration:**
- `prometheus.yml`: Main configuration
- `alert-rules.yml`: Alert definitions

### Grafana (Port 3000)

Visualization and dashboard platform.

**Features:**
- Pre-configured Prometheus and Loki datasources
- Default admin credentials: admin/admin (change in production!)
- Support for custom dashboards
- Alerting integration

**Access:**
- UI: http://localhost:3000
- Default credentials: admin/admin

**Configuration:**
- `grafana-datasources.yml`: Datasource provisioning

### Loki (Port 3100)

Log aggregation system.

**Features:**
- 15-day log retention
- Efficient log storage and querying
- Label-based log filtering
- Integration with Grafana

**Access:**
- API: http://localhost:3100
- Query via Grafana

**Configuration:**
- `loki-config.yml`: Main configuration

### Promtail

Log shipping agent for Loki.

**Features:**
- Docker container log collection
- Automatic service labeling
- Log parsing and enrichment
- Trace ID extraction

**Configuration:**
- `promtail-config.yml`: Scrape configurations

### Exporters

**Redis Exporter (Port 9121):**
- Exports Redis metrics to Prometheus
- Monitors cache performance

**PostgreSQL Exporter (Port 9187):**
- Exports PostgreSQL metrics to Prometheus
- Monitors database performance

## Monitored Services

All MAARS services expose metrics on their `/metrics` endpoint:

| Service | Port | Metrics Endpoint |
|---------|------|------------------|
| vessel-gateway | 8080 | http://vessel-gateway:8080/metrics |
| vessel-orchestrator | 8081 | http://vessel-orchestrator:8081/metrics |
| vessel-sandbox | 8082 | http://vessel-sandbox:8082/metrics |
| vessel-llm-router | 8083 | http://vessel-llm-router:8083/metrics |
| vessel-swarm | 8084 | http://vessel-swarm:8084/metrics |
| vessel-observability | 8087 | http://vessel-observability:8087/metrics |
| vessel-economics | 8090 | http://vessel-economics:8090/metrics |

## Alert Rules

Comprehensive alerting for:

### Service Health
- ServiceDown: Service unavailable for >1 minute
- ServiceHighRestartRate: Frequent service restarts

### Error Rates
- HighErrorRate: >5% error rate (5xx responses)
- ElevatedErrorRate: >1% error rate
- HighClientErrorRate: >10% client errors (4xx)

### Performance
- HighLatencyP95: P95 latency >1s
- HighLatencyP99: P99 latency >2s
- LatencySpike: 2x increase in latency

### Resources
- HighMemoryUsage: >80% memory usage
- CriticalMemoryUsage: >90% memory usage
- HighCPUUsage: >80% CPU usage
- CriticalCPUUsage: >95% CPU usage

### Economics (Phase 3)
- BudgetThresholdExceeded: >80% budget used
- BudgetCritical: >95% budget used
- HighLLMCostRate: High cost increase rate
- UnexpectedCostSpike: 3x cost increase

### Guardrails (Phase 3)
- GuardrailViolation: Any guardrail violation
- HighGuardrailViolationRate: >0.1/s violation rate
- ContentPolicyViolation: Content policy violations

### Infrastructure
- RedisDown: Redis unavailable
- PostgresDown: PostgreSQL unavailable
- KafkaDown: Kafka unavailable
- HighKafkaLag: >1000 message lag

### Agent Pool (Phase 2)
- LowAgentPoolCapacity: <20% pool capacity
- AgentPoolExhausted: No available agents
- HighAgentFailureRate: >10% agent failures

### Sandbox (Phase 1)
- HighSandboxExecutionFailureRate: >5% execution failures
- LongRunningSandboxExecution: Execution >300s

## Usage

### Starting the Monitoring Stack

```bash
cd infrastructure/docker
docker-compose up -d prometheus grafana loki promtail redis-exporter postgres-exporter
```

### Accessing Services

**Prometheus:**
```bash
open http://localhost:9090
```

**Grafana:**
```bash
open http://localhost:3000
# Login: admin/admin
```

**Loki (via Grafana):**
1. Open Grafana
2. Go to Explore
3. Select "Loki" datasource
4. Query logs using LogQL

### Querying Metrics

**PromQL Examples:**

```promql
# Request rate by service
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Memory usage
process_resident_memory_bytes / 1024 / 1024

# LLM costs
rate(llm_cost_total[1h])
```

### Querying Logs

**LogQL Examples:**

```logql
# All logs from vessel-gateway
{service="vessel-gateway"}

# Error logs
{service="vessel-gateway"} |= "ERROR"

# Logs with trace ID
{service="vessel-gateway"} | json | trace_id="abc123"

# High latency requests
{service="vessel-gateway"} | json | duration > 1000

# Guardrail violations
{service="vessel-observability"} |= "guardrail_violation"
```

### Creating Dashboards

1. Open Grafana (http://localhost:3000)
2. Click "+" → "Dashboard"
3. Add panels with PromQL queries
4. Save dashboard

**Recommended Dashboards:**
- Service Overview (request rate, error rate, latency)
- Resource Usage (CPU, memory, disk)
- Economics Dashboard (costs, budget usage)
- Guardrails Dashboard (violations, trends)

## Grafana Dashboards

MAARS includes 5 comprehensive pre-built Grafana dashboards for monitoring Phase 3 services and system-wide metrics. All dashboards are located in `infrastructure/monitoring/dashboards/`.

### Available Dashboards

**1. MAARS System Overview** (`maars-overview.json`)
- **UID:** `maars-overview`
- **Purpose:** System-wide monitoring of all 7 MAARS services
- **Key Metrics:** Service health, request rates, error rates, latency, active agents, costs, budget utilization, guardrail violations, anomalies
- **Refresh:** 30 seconds
- **Time Range:** Last 24 hours

**2. Vessel Observability Service** (`vessel-observability.json`)
- **UID:** `vessel-observability`
- **Purpose:** Detailed monitoring of guardrails, policies, and anomaly detection
- **Key Metrics:** Guardrail evaluations, policy violations by type/severity, anomaly detection, telemetry collection, OpenTelemetry spans
- **Refresh:** 15 seconds
- **Time Range:** Last 6 hours
- **Variables:** tenant_id, agent_id

**3. Vessel Economics Service** (`vessel-economics.json`)
- **UID:** `vessel-economics`
- **Purpose:** Cost tracking, budget management, and escrow monitoring
- **Key Metrics:** Real-time costs, cost by tenant/agent/provider/model, budget utilization, escrow balances, invoice generation, compliance reports
- **Refresh:** 30 seconds
- **Time Range:** Last 24 hours
- **Variables:** tenant_id, agent_id

**4. Guardrails & Compliance** (`guardrails-compliance.json`)
- **UID:** `guardrails-compliance`
- **Purpose:** Policy violations, compliance reporting, and audit trails
- **Key Metrics:** Active violations, violations by type/severity, top violators, compliance reports, audit trail events, escalation workflows
- **Refresh:** 1 minute
- **Time Range:** Last 7 days
- **Variables:** tenant_id, severity

**5. Cost Analysis** (`cost-analysis.json`)
- **UID:** `cost-analysis`
- **Purpose:** Detailed cost analysis with trends and forecasting
- **Key Metrics:** Cost trends (hourly/daily/weekly), cost breakdown by category/provider/model, cost efficiency, budget analysis, cost forecasting, anomaly detection
- **Refresh:** 5 minutes
- **Time Range:** Last 30 days
- **Variables:** tenant_id, provider

### Importing Dashboards

**Method 1: Grafana UI (Quick Start)**
```bash
# 1. Access Grafana
open http://localhost:3000

# 2. Login with default credentials
# Username: admin
# Password: admin

# 3. Navigate to Dashboards → Import
# 4. Upload JSON file or paste JSON content
# 5. Select Prometheus datasource
# 6. Click Import
```

**Method 2: Grafana API (Automated)**
```bash
# Import all dashboards at once
for dashboard in infrastructure/monitoring/dashboards/*.json; do
  curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
    -H "Content-Type: application/json" \
    -d @"$dashboard"
done
```

**Method 3: Dashboard Provisioning (Recommended for Production)**

Add to `docker-compose.yml`:
```yaml
grafana:
  volumes:
    - ./infrastructure/monitoring/dashboards:/etc/grafana/provisioning/dashboards/maars:ro
    - ./infrastructure/monitoring/grafana-dashboard-provider.yml:/etc/grafana/provisioning/dashboards/provider.yml:ro
```

Create `infrastructure/monitoring/grafana-dashboard-provider.yml`:
```yaml
apiVersion: 1

providers:
  - name: 'MAARS Dashboards'
    orgId: 1
    folder: 'MAARS'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards/maars
      foldersFromFilesStructure: true
```

### Dashboard Features

**Template Variables:**
- Filter data by tenant, agent, service, provider, or severity
- Multi-select support for flexible filtering
- Auto-populated from Prometheus metrics

**Panel Types:**
- Time series graphs for trends
- Stat panels for current values
- Gauge panels for thresholds
- Pie/donut charts for distributions
- Tables for detailed breakdowns
- Bar gauges for comparisons

**Navigation:**
- Dashboard links for easy navigation between related dashboards
- Drill-down capabilities from overview to detailed views
- Consistent color schemes and layouts

**Auto-refresh:**
- Configurable refresh intervals (15s to 5m)
- Real-time monitoring for critical metrics
- Optimized query performance

For detailed dashboard documentation, see [dashboards/README.md](./dashboards/README.md).

- Agent Pool Dashboard (capacity, failures)

### Setting Up Alerts

Alerts are automatically loaded from `alert-rules.yml`. To add custom alerts:

1. Edit `alert-rules.yml`
2. Add new alert rule
3. Restart Prometheus:
   ```bash
   docker-compose restart prometheus
   ```

### Troubleshooting

**Prometheus not scraping metrics:**
- Check service health: `docker-compose ps`
- Verify metrics endpoint: `curl http://localhost:8080/metrics`
- Check Prometheus targets: http://localhost:9090/targets

**Loki not receiving logs:**
- Check Promtail status: `docker-compose logs promtail`
- Verify Loki is running: `curl http://localhost:3100/ready`
- Check Promtail positions: `docker exec maars-promtail cat /tmp/positions.yaml`

**Grafana datasource not working:**
- Verify datasource configuration in Grafana UI
- Check network connectivity: `docker-compose exec grafana ping prometheus`
- Restart Grafana: `docker-compose restart grafana`

## Production Considerations

### Security
- Change default Grafana admin password
- Enable authentication for Prometheus
- Use TLS for all connections
- Implement network policies

### Scalability
- Use remote write for Prometheus
- Deploy Loki in distributed mode
- Use object storage for long-term retention
- Implement metric federation

### High Availability
- Run multiple Prometheus instances
- Use Thanos or Cortex for HA
- Deploy Loki with replication
- Use load balancers

### Cost Optimization
- Adjust retention periods
- Use recording rules for expensive queries
- Implement metric relabeling
- Archive old data to object storage

## Integration with Phase 3 Services

### vessel-observability
- Exposes metrics on port 8087
- Provides guardrail violation metrics
- Tracks compliance metrics

### vessel-economics
- Exposes metrics on port 8090
- Provides cost tracking metrics
- Monitors budget usage

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)
- [LogQL Documentation](https://grafana.com/docs/loki/latest/logql/)

## Made with Bob