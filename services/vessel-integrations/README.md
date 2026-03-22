# vessel-integrations

External integrations service for MAARS, handling Slack bot, MCP servers, and OAuth providers.

## Overview

The `vessel-integrations` service is the **Device Drivers** layer of the MAARS operating system, providing:

- **Slack Bot Integration**: Natural language goal creation via `@maars` mentions
- **Custom MCP Server Registry**: Bring-your-own-tool framework
- **OAuth Token Management**: Secure credential storage in Vault
- **Integration Event Logging**: Full audit trail of external interactions

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    vessel-integrations                       │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Slack Bot    │  │ MCP Registry │  │ OAuth Manager│     │
│  │ Handler      │  │              │  │              │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
│                    ┌───────▼────────┐                       │
│                    │  Kafka Producer │                       │
│                    └────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
   vessel-gateway      vessel-orchestrator    HashiCorp Vault
```

## Features

### 1. Slack Bot MVP

**The Enterprise Trojan Horse**: Perplexity Computer achieved viral adoption through Slack. MAARS replicates and extends this pattern.

**Capabilities:**
- `@maars [goal description]` → Instant goal creation
- Real-time task updates in thread
- Goal completion notifications with artifacts
- Cost tracking per goal
- Multi-workspace support

**Example:**
```
User: @maars Research the top 10 AI frameworks and create a comparison table

MAARS: ✅ Goal created: `a1b2c3d4-...`
       > Research the top 10 AI frameworks and create a comparison table
       I'll update you as tasks complete.

[5 minutes later]
MAARS: ✅ Task Complete: Web research
       > Model: `MID` | Cost: `$0.12` | Time: `3200ms`

[10 minutes later]
MAARS: 🏆 Goal Complete: Research the top 10 AI frameworks...
       > Total Cost: `$0.45` | Agents Used: `3` | Duration: `8m 32s`
       
       Artifacts:
       • https://maars.ai/artifacts/comparison-table.md
```

### 2. Custom MCP Server Registry

**The Ultimate Differentiator**: Unlike Perplexity's closed ecosystem, MAARS allows enterprises to register proprietary internal tools.

**Registration:**
```bash
POST /v1/integrations/mcp/servers
{
  "tenant_id": "uuid",
  "server_name": "internal-crm",
  "server_url": "https://crm.internal.company.com/mcp",
  "auth_type": "bearer",
  "auth_token_vault_path": "secret/crm/mcp-token",
  "allowed_tools": ["get_customer", "update_opportunity", "list_accounts"]
}
```

**Tool Discovery:**
```bash
GET /v1/integrations/mcp/tools?tenant_id=uuid

Response:
{
  "tools": [
    {
      "tool_name": "get_customer",
      "server_id": "uuid",
      "server_name": "internal-crm",
      "server_url": "https://crm.internal.company.com/mcp"
    }
  ],
  "total": 1
}
```

### 3. OAuth Token Management

**Secure Credential Storage**: All OAuth tokens are stored in HashiCorp Vault, with only metadata in PostgreSQL.

**Flow:**
1. User authorizes OAuth provider (Slack, Google, GitHub, etc.)
2. Access token stored in Vault at `secret/oauth/{tenant_id}/{provider}`
3. Metadata (expiry, scope) stored in PostgreSQL
4. JIT token retrieval for agent actions

## API Endpoints

### Slack Integration

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/integrations/slack/events` | Slack Event API webhook |
| `POST` | `/v1/integrations/slack/install` | Install workspace |
| `GET` | `/v1/integrations/slack/workspaces` | List workspaces |

### MCP Servers

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/integrations/mcp/servers` | Register MCP server |
| `GET` | `/v1/integrations/mcp/servers` | List MCP servers |
| `DELETE` | `/v1/integrations/mcp/servers/{id}` | Deactivate server |
| `GET` | `/v1/integrations/mcp/tools` | Discover all tools |

## Database Schema

### slack_integrations
```sql
CREATE TABLE slack_integrations (
    tenant_id UUID,
    workspace_id TEXT,
    bot_token_vault_path TEXT,
    signing_secret_vault_path TEXT,
    default_channel_id TEXT,
    notify_on_milestone BOOLEAN DEFAULT TRUE,
    notify_on_completion BOOLEAN DEFAULT TRUE,
    notify_on_inbox_card BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, workspace_id)
);
```

### goal_slack_threads
```sql
CREATE TABLE goal_slack_threads (
    goal_id UUID PRIMARY KEY,
    tenant_id UUID,
    workspace_id TEXT,
    channel_id TEXT,
    thread_ts TEXT,
    created_at TIMESTAMP
);
```

### mcp_servers
```sql
CREATE TABLE mcp_servers (
    server_id UUID PRIMARY KEY,
    tenant_id UUID,
    server_name TEXT,
    server_url TEXT,
    auth_type TEXT,
    auth_token_vault_path TEXT,
    allowed_tools JSON,
    status TEXT DEFAULT 'ACTIVE',
    last_health_check TIMESTAMP,
    created_at TIMESTAMP
);
```

## Configuration

### Environment Variables

```bash
# Service Configuration
SERVICE_NAME=vessel-integrations
SERVICE_VERSION=1.0.0
PORT=8091
HOST=0.0.0.0
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://maars:maars@localhost:5432/maars

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:19092
KAFKA_TOPIC_PREFIX=maars

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
SLACK_APP_TOKEN=xapp-...  # For Socket Mode

# Vault
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=dev-root-token
VAULT_MOUNT_POINT=secret

# Gateway
GATEWAY_URL=http://localhost:8000
INTERNAL_SERVICE_TOKEN=...
```

## Local Development

### 1. Start Infrastructure

```bash
cd infrastructure/docker
docker-compose up -d postgres kafka vault
```

### 2. Install Dependencies

```bash
cd services/vessel-integrations
pip install -r requirements.txt
```

### 3. Initialize Database

```bash
psql -h localhost -U maars -d maars -f ../../config/astradb-schema.cql
```

### 4. Run Service

```bash
python main.py
```

Service will start on `http://localhost:8091`

### 5. Test Slack Bot (Local)

For local development, use Slack's Socket Mode:

1. Create Slack app at https://api.slack.com/apps
2. Enable Socket Mode
3. Add Bot Token Scopes: `app_mentions:read`, `chat:write`, `im:history`
4. Install app to workspace
5. Set environment variables:
   ```bash
   export SLACK_BOT_TOKEN=xoxb-...
   export SLACK_SIGNING_SECRET=...
   export SLACK_APP_TOKEN=xapp-...
   ```
6. Restart service
7. Mention `@maars` in any channel

## Docker Deployment

### Build Image

```bash
docker build -t maars/vessel-integrations:latest .
```

### Run Container

```bash
docker run -d \
  --name vessel-integrations \
  -p 8091:8091 \
  -e DATABASE_URL=postgresql://maars:maars@postgres:5432/maars \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
  -e SLACK_BOT_TOKEN=xoxb-... \
  -e SLACK_SIGNING_SECRET=... \
  -e VAULT_ADDR=http://vault:8200 \
  -e VAULT_TOKEN=... \
  -e GATEWAY_URL=http://vessel-gateway:8000 \
  maars/vessel-integrations:latest
```

## Kafka Events

### Published Events

**Slack Events:**
```json
{
  "event_id": "uuid",
  "event_type": "goal.created_from_slack",
  "tenant_id": "uuid",
  "timestamp": "2026-03-22T14:30:00Z",
  "payload": {
    "goal_id": "uuid",
    "workspace_id": "T1234567890",
    "channel_id": "C1234567890",
    "thread_ts": "1234567890.123456",
    "description": "Research AI frameworks"
  }
}
```

**MCP Events:**
```json
{
  "event_id": "uuid",
  "event_type": "mcp.server_registered",
  "tenant_id": "uuid",
  "timestamp": "2026-03-22T14:30:00Z",
  "payload": {
    "server_id": "uuid",
    "server_name": "internal-crm",
    "server_url": "https://crm.internal.company.com/mcp"
  }
}
```

### Consumed Events

The service consumes goal lifecycle events to post updates to Slack threads:

- `goal.task_completed` → Post task update
- `goal.completed` → Post completion message
- `goal.failed` → Post failure notification

## Testing

### Unit Tests

```bash
pytest tests/unit/
```

### Integration Tests

```bash
pytest tests/integration/
```

### Slack Bot Testing

Use the `/test` endpoint to simulate Slack events:

```bash
curl -X POST http://localhost:8091/test/slack/mention \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "C1234567890",
    "user": "U1234567890",
    "text": "@maars Research AI frameworks"
  }'
```

## Monitoring

### Metrics

Prometheus metrics exposed on `/metrics`:

- `slack_events_total{event_type}` - Total Slack events processed
- `slack_goals_created_total` - Goals created from Slack
- `mcp_servers_registered_total` - MCP servers registered
- `integration_errors_total{integration_type}` - Integration errors

### Health Check

```bash
curl http://localhost:8091/health

Response:
{
  "status": "healthy",
  "service": "vessel-integrations",
  "version": "1.0.0"
}
```

## Security

### Slack Request Verification

All Slack requests are verified using HMAC-SHA256 signature validation:

```python
def verify_slack_signature(request: Request) -> bool:
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    signature = request.headers.get("X-Slack-Signature")
    body = await request.body()
    
    basestring = f"v0:{timestamp}:{body.decode()}"
    expected = "v0=" + hmac.new(
        signing_secret.encode(),
        basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)
```

### Vault Integration

OAuth tokens are never stored in PostgreSQL. Only Vault paths are stored:

```python
# Store token in Vault
vault_client.secrets.kv.v2.create_or_update_secret(
    path=f"oauth/{tenant_id}/slack",
    secret={"access_token": token, "refresh_token": refresh}
)

# Store metadata in PostgreSQL
oauth_token = OAuthToken(
    tenant_id=tenant_id,
    provider="slack",
    vault_path=f"oauth/{tenant_id}/slack",
    expires_at=expires_at
)
```

## Troubleshooting

### Slack Events Not Received

1. Check Slack app Event Subscriptions URL: `https://your-domain.com/v1/integrations/slack/events`
2. Verify signing secret matches environment variable
3. Check Slack app has required scopes
4. Review logs: `docker logs vessel-integrations`

### MCP Server Registration Fails

1. Verify server URL is accessible from MAARS network
2. Check auth token is valid in Vault
3. Test MCP server health: `curl https://mcp-server.com/health`
4. Review integration_events table for error details

### Goal Not Created from Slack

1. Check workspace is registered in `slack_integrations` table
2. Verify tenant_id mapping is correct
3. Check vessel-gateway is accessible
4. Review Kafka events for `goal.created_from_slack`

## Roadmap

### Phase 1 (Current)
- ✅ Slack bot MVP with @maars mentions
- ✅ MCP server registry
- ✅ OAuth token management

### Phase 2 (Week 3 Day 2-3)
- [ ] Microsoft Teams integration
- [ ] Google Chat integration
- [ ] Slack slash commands (`/maars status [goal_id]`)

### Phase 3 (Week 4)
- [ ] MCP server health checks
- [ ] OAuth token auto-refresh
- [ ] Integration marketplace UI

## Contributing

See main MAARS [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

Proprietary - All Rights Reserved

---

**Built with ❤️ by the MAARS Team**

*Empowering the next generation of autonomous intelligence*