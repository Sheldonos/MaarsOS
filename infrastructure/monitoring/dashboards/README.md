# MAARS Grafana Dashboards

This directory contains Grafana dashboard configurations for monitoring the MAARS platform, with a focus on Phase 3 services (vessel-observability and vessel-economics).

## Dashboard Overview

### 1. MAARS System Overview (`maars-overview.json`)
**UID:** `maars-overview`  
**Refresh:** 30 seconds  
**Time Range:** Last 24 hours

System-wide monitoring dashboard providing a high-level view of all MAARS services.

**Key Panels:**
- **Service Health Status**: Real-time health check for all 7 services (Gateway, Orchestrator, Swarm, LLM Router, Sandbox, Observability, Economics)
- **Request Rate by Service**: HTTP requests per second across all services
- **Error Rate by Service**: 5xx error percentage by service
- **Latency (P95/P99)**: Response time percentiles for performance monitoring
- **Active Agents**: Current number of active agents in the swarm
- **Total Cost**: Cost tracking (last hour, 24h, 7 days)
- **Budget Utilization**: Budget usage percentage by tenant
- **Active Guardrail Violations**: Recent policy violations count
- **Recent Anomalies**: Anomaly detections in the last hour

**Use Cases:**
- Quick system health check
- Identifying service outages
- Monitoring overall system performance
- Cost overview at a glance

---

### 2. Vessel Observability Service (`vessel-observability.json`)
**UID:** `vessel-observability`  
**Refresh:** 15 seconds  
**Time Range:** Last 6 hours

Detailed monitoring for the vessel-observability service, focusing on guardrails, policy enforcement, and anomaly detection.

**Key Panels:**

**Service Metrics:**
- Service health and uptime (6h)
- Request rate and P95 latency
- Request/response breakdown by endpoint

**Guardrail Monitoring:**
- Total evaluations (passed/failed)
- Policy violations by type and severity
- Top violated policies table
- Policy enforcement success rate

**Anomaly Detection:**
- Anomalies by type (stacked area chart)
- Anomaly detection rate over time
- Recent anomaly trends

**Telemetry Collection:**
- Trace collection rate
- Metrics collection rate
- OpenTelemetry span processing

**Template Variables:**
- `tenant_id`: Filter by tenant
- `agent_id`: Filter by agent

**Use Cases:**
- Monitoring guardrail effectiveness
- Identifying policy violations
- Tracking anomaly detection performance
- Debugging observability issues

---

### 3. Vessel Economics Service (`vessel-economics.json`)
**UID:** `vessel-economics`  
**Refresh:** 30 seconds  
**Time Range:** Last 24 hours

Comprehensive cost tracking, budget management, and escrow monitoring for the vessel-economics service.

**Key Panels:**

**Service Metrics:**
- Service health and uptime (24h)
- Request rate and P95 latency
- Request/response breakdown by endpoint

**Cost Tracking:**
- Total cost (real-time)
- Cost trends (hourly visualization)
- Cost by tenant (top 10 pie chart)
- Cost by agent (top 10 pie chart)
- Cost by provider (OpenAI, Anthropic, Google)
- Cost by model breakdown

**Budget Management:**
- Budget utilization by tenant (bar gauge)
- Budget exceeded events timeline
- Budget vs actual spending comparison

**Escrow Management:**
- Escrow balance by tenant
- Escrow transactions (allocations/releases)
- Transaction rate over time

**Compliance & Reporting:**
- Invoice generation rate
- Compliance report generation rate

**Template Variables:**
- `tenant_id`: Filter by tenant
- `agent_id`: Filter by agent

**Use Cases:**
- Real-time cost monitoring
- Budget compliance tracking
- Escrow balance management
- Financial reporting and analysis

---

### 4. Guardrails & Compliance (`guardrails-compliance.json`)
**UID:** `guardrails-compliance`  
**Refresh:** 1 minute  
**Time Range:** Last 7 days

Combined dashboard for policy violations, compliance reporting, and audit trail monitoring.

**Key Panels:**

**Violation Overview:**
- Active policy violations (1h)
- Critical/high severity violations
- Policy enforcement rate gauge

**Violation Analysis:**
- Violations by policy type (pie chart)
- Violations by severity (donut chart)
- Violation trends (7-day timeline)

**Top Violators:**
- Top 10 violating tenants (table)
- Top 10 violating agents (table)

**Compliance Reporting:**
- Compliance report status
- Reports generated (7d count)
- Audit trail activity rate
- Active escalations count
- Report generation rate timeline
- Audit trail events by type

**Policy Details:**
- Most violated policies (top 20 table with policy name, type, severity)

**Template Variables:**
- `tenant_id`: Filter by tenant
- `severity`: Filter by severity level (multi-select)

**Use Cases:**
- Compliance monitoring and reporting
- Policy violation tracking
- Audit trail analysis
- Identifying problematic tenants/agents

---

### 5. Cost Analysis (`cost-analysis.json`)
**UID:** `cost-analysis`  
**Refresh:** 5 minutes  
**Time Range:** Last 30 days

Detailed cost analysis with trends, forecasting, and efficiency metrics.

**Key Panels:**

**Cost Overview:**
- Total cost (30d)
- Average daily cost
- Hourly cost rate
- Cost per task average

**Cost Trends:**
- Hourly cost trend (smooth line chart)
- Daily cost trend (bar chart)
- Weekly cost trend (bar chart)

**Cost Breakdown:**
- Cost by category (LLM, compute, storage)
- Cost by provider comparison (stacked area)
- Cost by model comparison (stacked area)

**Cost Efficiency:**
- Most expensive tasks (top 10 table)
- Cost efficiency metrics (cost per task, cost per request)

**Budget Analysis:**
- Budget vs actual spending comparison
- 7-day cost forecast (linear projection)

**Cost Anomalies:**
- Detected cost anomalies (scatter plot)

**Template Variables:**
- `tenant_id`: Filter by tenant
- `provider`: Filter by provider (multi-select)

**Use Cases:**
- Long-term cost analysis
- Cost optimization opportunities
- Budget planning and forecasting
- Identifying cost anomalies

---

## Importing Dashboards

### Method 1: Grafana UI

1. Access Grafana at `http://localhost:3000`
2. Login with default credentials (admin/admin)
3. Navigate to **Dashboards** → **Import**
4. Click **Upload JSON file**
5. Select the dashboard JSON file
6. Click **Import**

### Method 2: Grafana API

```bash
# Import a dashboard using curl
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @infrastructure/monitoring/dashboards/maars-overview.json
```

### Method 3: Provisioning (Recommended for Production)

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

---

## Key Metrics Explained

### Service Health Metrics

- **`up{job="service-name"}`**: Service availability (1 = up, 0 = down)
- **`http_requests_total`**: Total HTTP requests counter
- **`http_request_duration_seconds_bucket`**: Request duration histogram for percentile calculations

### Guardrail Metrics

- **`guardrail_evaluations_total`**: Total guardrail evaluations performed
- **`guardrail_violations_total`**: Policy violations detected
- **`policy_violations_total{severity="critical|high|medium|low"}`**: Violations by severity
- **`anomaly_detected_total`**: Anomalies detected by type

### Cost Metrics

- **`cost_tracked_total`**: Total cost accumulated (counter)
- **`cost_amount`**: Current cost amount (gauge)
- **`budget_limit`**: Budget limit per tenant
- **`budget_used`**: Budget consumed per tenant
- **`escrow_balance`**: Current escrow balance per tenant

### Economics Metrics

- **`escrow_allocations_total`**: Escrow allocation events
- **`escrow_releases_total`**: Escrow release events
- **`invoices_generated_total`**: Invoices generated
- **`compliance_reports_generated_total`**: Compliance reports generated

---

## Alert Thresholds

### Critical Alerts (Immediate Action Required)

- Service down: `up{job="service-name"} == 0`
- Error rate > 5%: `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05`
- P95 latency > 1000ms: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1`
- Critical policy violations: `increase(policy_violations_total{severity="critical"}[5m]) > 0`
- Budget exceeded: `budget_used / budget_limit > 1`

### Warning Alerts (Monitor Closely)

- Error rate > 1%: `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.01`
- P95 latency > 500ms: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5`
- Budget utilization > 85%: `budget_used / budget_limit > 0.85`
- High policy violations: `increase(policy_violations_total{severity="high"}[5m]) > 5`

---

## Troubleshooting

### Dashboard Not Loading

1. **Check Prometheus datasource:**
   ```bash
   curl http://localhost:9090/-/healthy
   ```

2. **Verify Grafana datasource configuration:**
   - Navigate to **Configuration** → **Data Sources**
   - Ensure Prometheus datasource is configured with URL `http://prometheus:9090`

3. **Check if metrics are being collected:**
   ```bash
   curl http://localhost:9090/api/v1/query?query=up
   ```

### No Data in Panels

1. **Verify services are exposing metrics:**
   ```bash
   # Check vessel-observability metrics
   curl http://localhost:8006/metrics
   
   # Check vessel-economics metrics
   curl http://localhost:8007/metrics
   ```

2. **Check Prometheus targets:**
   - Navigate to `http://localhost:9090/targets`
   - Ensure all services are in "UP" state

3. **Verify time range:**
   - Ensure the dashboard time range includes periods when services were running
   - Try changing time range to "Last 5 minutes" for recent data

### Metrics Not Matching Expected Values

1. **Check metric labels:**
   - Ensure services are using consistent label names
   - Verify `service`, `tenant_id`, `agent_id` labels are present

2. **Review PromQL queries:**
   - Test queries directly in Prometheus UI
   - Adjust rate/increase intervals if needed

3. **Check metric types:**
   - Counters: Use `rate()` or `increase()`
   - Gauges: Use directly or with aggregations
   - Histograms: Use `histogram_quantile()` for percentiles

---

## Dashboard Customization

### Adding New Panels

1. Click **Add panel** in dashboard edit mode
2. Select visualization type (Time series, Stat, Gauge, Table, etc.)
3. Configure query using PromQL
4. Set panel options (title, description, units, thresholds)
5. Save dashboard

### Modifying Queries

Example: Change time range for cost calculation
```promql
# Original: Last hour
increase(cost_tracked_total[1h])

# Modified: Last 6 hours
increase(cost_tracked_total[6h])
```

### Adding Template Variables

1. Navigate to **Dashboard settings** → **Variables**
2. Click **Add variable**
3. Configure:
   - **Name**: Variable name (e.g., `service`)
   - **Type**: Query
   - **Data source**: Prometheus
   - **Query**: `label_values(up, job)`
4. Use in queries: `up{job="$service"}`

---

## Best Practices

1. **Use consistent time ranges** across related dashboards
2. **Set appropriate refresh intervals** (balance between freshness and load)
3. **Add panel descriptions** to explain metrics and thresholds
4. **Use template variables** for filtering and reusability
5. **Group related panels** using rows for better organization
6. **Set meaningful alert thresholds** based on SLOs
7. **Link related dashboards** for easy navigation
8. **Document custom queries** in panel descriptions
9. **Use appropriate visualization types** for different metrics
10. **Test dashboards** with real data before production deployment

---

## Maintenance

### Regular Tasks

- **Weekly**: Review dashboard performance and adjust refresh rates
- **Monthly**: Update alert thresholds based on observed patterns
- **Quarterly**: Review and optimize PromQL queries for efficiency
- **As needed**: Add new panels for new metrics or services

### Version Control

All dashboard JSON files are version controlled in this repository. When making changes:

1. Export dashboard JSON from Grafana
2. Update the file in `infrastructure/monitoring/dashboards/`
3. Commit changes with descriptive message
4. Document changes in this README

---

## Support

For issues or questions:
- Check Grafana documentation: https://grafana.com/docs/
- Review Prometheus query documentation: https://prometheus.io/docs/prometheus/latest/querying/basics/
- Consult MAARS monitoring documentation: `infrastructure/monitoring/README.md`

---

## Dashboard Schema Version

All dashboards use Grafana schema version 38 (compatible with Grafana 10.0+).