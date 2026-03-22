# MAARS MCP & API Integration Layer Specification

**Date:** March 22, 2026
**Project:** MAARS — Master Autonomous Agentic Runtime System
**Service:** `vessel-integrations`

---

## Executive Summary

The original Architecture Specification references `vessel-integrations` exactly once, as the solution to "Token waste (browser scraping)" via "Agent-Native APIs." It provides no further detail. **MCP (Model Context Protocol) is not mentioned anywhere in the spec.** This document fills that gap entirely.

`vessel-integrations` is the **tool and connector layer** of MAARS. It is the service that transforms the WASM sandbox from a general-purpose compute environment into a system that can actually interact with the real world — CRMs, databases, payment systems, calendars, file systems, and any third-party API. Without this layer, agents can reason but cannot act.

The service has two distinct sub-systems that must be built:

1. **The MCP Gateway** — A standards-compliant Model Context Protocol server that exposes all MAARS tools to any MCP-compatible client (including the agents themselves).
2. **The Connector Registry** — A catalog of pre-built, tenant-configurable integrations for common enterprise systems (Salesforce, Stripe, Google Workspace, Slack, etc.).

---

## 1. Why MCP Is the Right Standard

The Model Context Protocol (MCP), introduced by Anthropic in November 2024 and now an open standard, solves the exact problem MAARS faces: how does an LLM-powered agent call external tools in a safe, structured, and vendor-neutral way?

MCP defines a client-server architecture where:
- **MCP Servers** expose tools, resources, and prompts.
- **MCP Clients** (i.e., the LLM-powered agents) discover and invoke those tools.
- **The Transport Layer** is either `stdio` (for local processes) or `HTTP + SSE` (for remote servers).

For MAARS, `vessel-integrations` acts as an **MCP Server** and `vessel-swarm` (the agent execution layer) acts as the **MCP Client**. This is the correct architectural split.

| Component | MCP Role | Protocol |
|---|---|---|
| `vessel-integrations` | MCP Server | HTTP + SSE (remote) |
| `vessel-swarm` (per-agent) | MCP Client | HTTP + SSE |
| Local tools (file, shell) | MCP Server | stdio (in-sandbox) |
| External APIs (Salesforce, Stripe) | Upstream target | REST/GraphQL (proxied) |

---

## 2. `vessel-integrations` Architecture

### 2.1 Service Overview

`vessel-integrations` is a **Python FastAPI** service (consistent with the AI/data services in the stack) that:

1. Exposes a standards-compliant MCP endpoint at `/mcp` (HTTP + SSE transport).
2. Maintains a **Connector Registry** in AstraDB — a catalog of all available integrations and their per-tenant configurations.
3. Proxies tool calls from agents to upstream APIs, injecting the correct tenant credentials at runtime.
4. Enforces the agent's `tool_allowlist` from the `TaskDefinition` before executing any tool.
5. Records every tool call as a `ToolExecution` record (already defined in the ERD) and emits a `tool.executed` Kafka event.

### 2.2 Environment Variables

| Variable | Description | Example |
|---|---|---|
| `PORT` | Service listening port | `8088` |
| `ASTRA_DB_TOKEN` | AstraDB token for connector registry | `AstraCS:...` |
| `ASTRA_DB_ENDPOINT` | AstraDB endpoint URL | `https://...astra.datastax.com` |
| `KAFKA_BROKERS` | Kafka broker addresses | `kafka:9092` |
| `VAULT_URL` | HashiCorp Vault for tenant API key secrets | `http://vault:8200` |
| `VAULT_TOKEN` | Vault root/service token | `hvs.xxx` |
| `SANDBOX_SERVICE_URL` | `vessel-sandbox` gRPC endpoint | `grpc://vessel-sandbox:50057` |
| `IDENTITY_SERVICE_URL` | `vessel-identity` gRPC for JIT token validation | `grpc://vessel-identity:50051` |
| `MCP_SERVER_NAME` | Name advertised in MCP discovery | `maars-integrations` |
| `MCP_SERVER_VERSION` | MCP server version | `1.0.0` |

---

## 3. MCP Server Implementation

### 3.1 MCP Endpoint Structure

The MCP server exposes the following endpoints, conforming to the MCP specification:

```
POST /mcp              — Main JSON-RPC 2.0 endpoint for all MCP messages
GET  /mcp/sse          — Server-Sent Events stream for server-to-client notifications
GET  /mcp/health       — Health check
GET  /.well-known/mcp  — MCP server discovery document
```

### 3.2 MCP Server Discovery Document (`/.well-known/mcp`)

```json
{
  "name": "maars-integrations",
  "version": "1.0.0",
  "description": "MAARS enterprise tool and connector gateway",
  "protocolVersion": "2024-11-05",
  "capabilities": {
    "tools": { "listChanged": true },
    "resources": { "subscribe": true, "listChanged": true },
    "prompts": { "listChanged": false },
    "logging": {}
  },
  "serverInfo": {
    "name": "vessel-integrations",
    "version": "1.0.0"
  }
}
```

### 3.3 Python MCP Server Implementation

```python
# vessel_integrations/mcp_server.py
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent, CallToolResult
from fastapi import FastAPI, Request, Depends
from fastapi.responses import StreamingResponse
import json

app = FastAPI()
mcp_server = Server("maars-integrations")

# -------------------------------------------------------
# Tool Registration
# -------------------------------------------------------

@mcp_server.list_tools()
async def list_tools(context: dict) -> list[Tool]:
    """
    Returns the tools available to this agent based on its task's tool_allowlist.
    The context dict contains the agent's JIT token, from which we extract
    the task_id and look up the tool_allowlist in AstraDB.
    """
    task_id = context.get("task_id")
    allowlist = await get_tool_allowlist(task_id)  # Query AstraDB
    
    all_tools = get_all_registered_tools()
    return [t for t in all_tools if t.name in allowlist]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict, context: dict) -> list[TextContent]:
    """
    Main tool dispatch. Validates the tool call against the agent's allowlist,
    routes to the correct connector, and records the execution.
    """
    task_id = context.get("task_id")
    agent_id = context.get("agent_id")
    tenant_id = context.get("tenant_id")
    
    # 1. Validate against allowlist
    allowlist = await get_tool_allowlist(task_id)
    if name not in allowlist:
        raise PermissionError(f"Tool '{name}' is not in the allowlist for task {task_id}")
    
    # 2. Get tenant credentials from Vault
    credentials = await get_tenant_credentials(tenant_id, name)
    
    # 3. Execute the tool via the appropriate connector
    result = await execute_connector(name, arguments, credentials)
    
    # 4. Record the execution in AstraDB and emit Kafka event
    await record_tool_execution(task_id, agent_id, tenant_id, name, arguments, result)
    
    return [TextContent(type="text", text=json.dumps(result))]


# -------------------------------------------------------
# FastAPI SSE Transport
# -------------------------------------------------------

@app.get("/mcp/sse")
async def sse_endpoint(request: Request):
    transport = SseServerTransport("/mcp/messages")
    async def event_generator():
        async with mcp_server.run_sse_async(transport) as session:
            yield session
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/mcp/messages")
async def handle_message(request: Request):
    body = await request.json()
    transport = SseServerTransport("/mcp/messages")
    return await transport.handle_post_message(body)
```

---

## 4. The Connector Registry

### 4.1 AstraDB Schema for Connector Registry

```sql
-- Connector definitions (platform-level, not per-tenant)
CREATE TABLE connector_definitions (
    connector_id UUID PRIMARY KEY,
    name TEXT,                    -- e.g., "salesforce_query"
    display_name TEXT,            -- e.g., "Salesforce: Query Records"
    category TEXT,                -- e.g., "CRM", "PAYMENTS", "PRODUCTIVITY"
    description TEXT,
    input_schema_json TEXT,       -- JSON Schema for tool arguments
    output_schema_json TEXT,      -- JSON Schema for tool output
    auth_type TEXT,               -- "OAUTH2", "API_KEY", "BASIC"
    required_scopes list<TEXT>,
    is_active BOOLEAN
);

-- Per-tenant connector configurations (credentials stored in Vault, not here)
CREATE TABLE tenant_connectors (
    tenant_id UUID,
    connector_id UUID,
    config_id UUID,
    vault_secret_path TEXT,       -- Path in HashiCorp Vault where credentials live
    is_enabled BOOLEAN,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, connector_id)
);

-- Per-task tool allowlists (derived from TaskDefinition.tool_allowlist)
CREATE TABLE task_tool_allowlists (
    task_id UUID PRIMARY KEY,
    tenant_id UUID,
    allowed_tool_names list<TEXT>,
    created_at TIMESTAMP
);
```

### 4.2 Credential Storage in HashiCorp Vault

Tenant API keys and OAuth tokens are **never stored in AstraDB**. They live in HashiCorp Vault at a path structured as:

```
secret/tenants/{tenant_id}/connectors/{connector_id}
```

Example Vault secret for a Salesforce connector:
```json
{
  "access_token": "00D...",
  "refresh_token": "5Aep...",
  "instance_url": "https://myorg.salesforce.com",
  "token_expires_at": "2026-03-22T11:00:00Z"
}
```

The `vessel-integrations` service fetches credentials from Vault at tool-call time, never caching them in memory beyond the duration of a single request.

---

## 5. Built-In Connector Catalog

The following connectors must be built for the Phase 1–2 launch. Each connector is a Python class that implements the `BaseConnector` interface.

### 5.1 Connector Interface

```python
# vessel_integrations/connectors/base.py
from abc import ABC, abstractmethod
from typing import Any

class BaseConnector(ABC):
    """All connectors must implement this interface."""
    
    name: str           # Unique tool name, e.g., "salesforce_query"
    category: str       # Tool category
    
    @abstractmethod
    async def execute(self, arguments: dict, credentials: dict) -> dict:
        """Execute the tool and return a JSON-serializable result."""
        pass
    
    @abstractmethod
    def get_tool_definition(self) -> dict:
        """Return the MCP Tool definition (name, description, inputSchema)."""
        pass
```

### 5.2 Phase 1 Connector Catalog

| Connector Name | Category | Auth Type | Description |
|---|---|---|---|
| `web_search` | RESEARCH | API Key | Search the web via Brave/Serper API |
| `web_scrape` | RESEARCH | None | Scrape a URL and return clean Markdown |
| `execute_python` | COMPUTE | None | Run Python code in the WASM sandbox |
| `execute_shell` | COMPUTE | None | Run a shell command in the WASM sandbox |
| `read_file` | FILES | None | Read a file from the task's workspace |
| `write_file` | FILES | None | Write a file to the task's workspace |
| `http_request` | HTTP | API Key | Make an arbitrary HTTP request to a whitelisted URL |
| `send_email` | COMMS | OAuth2 | Send an email via Gmail or Outlook |
| `send_slack_message` | COMMS | OAuth2 | Post a message to a Slack channel |
| `calendar_create_event` | PRODUCTIVITY | OAuth2 | Create a Google Calendar event |

### 5.3 Phase 2 Connector Catalog (Enterprise)

| Connector Name | Category | Auth Type | Description |
|---|---|---|---|
| `salesforce_query` | CRM | OAuth2 | Execute a SOQL query against Salesforce |
| `salesforce_create_record` | CRM | OAuth2 | Create a Salesforce record (Lead, Contact, Opportunity) |
| `hubspot_get_contact` | CRM | API Key | Retrieve a HubSpot contact by email |
| `hubspot_create_deal` | CRM | API Key | Create a HubSpot deal |
| `stripe_create_charge` | PAYMENTS | API Key | Create a Stripe payment charge |
| `stripe_get_customer` | PAYMENTS | API Key | Retrieve a Stripe customer record |
| `postgres_query` | DATABASE | Connection String | Execute a read-only SQL query |
| `airtable_query` | DATABASE | API Key | Query an Airtable base |
| `notion_create_page` | PRODUCTIVITY | OAuth2 | Create a Notion page |
| `github_create_issue` | DEVTOOLS | OAuth2 | Create a GitHub issue |
| `github_create_pr` | DEVTOOLS | OAuth2 | Create a GitHub pull request |
| `jira_create_ticket` | DEVTOOLS | OAuth2 | Create a Jira ticket |

---

## 6. Example Connector Implementation: `web_search`

```python
# vessel_integrations/connectors/web_search.py
import httpx
from .base import BaseConnector

class WebSearchConnector(BaseConnector):
    name = "web_search"
    category = "RESEARCH"

    def get_tool_definition(self) -> dict:
        return {
            "name": self.name,
            "description": "Search the web for real-time information. Returns a list of results with titles, URLs, and snippets.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return (max 10)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }

    async def execute(self, arguments: dict, credentials: dict) -> dict:
        query = arguments["query"]
        num_results = min(arguments.get("num_results", 5), 10)
        api_key = credentials["brave_api_key"]

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"Accept": "application/json", "X-Subscription-Token": api_key},
                params={"q": query, "count": num_results}
            )
            response.raise_for_status()
            data = response.json()

        results = [
            {
                "title": r["title"],
                "url": r["url"],
                "snippet": r.get("description", "")
            }
            for r in data.get("web", {}).get("results", [])
        ]
        return {"results": results, "query": query}
```

---

## 7. MCP Client Integration in `vessel-swarm`

The agent execution loop in `vessel-swarm` must be updated to initialize an MCP client session before each task and pass it to the LLM for tool calling.

```python
# vessel_swarm/agent_executor.py
from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import AsyncOpenAI

INTEGRATIONS_MCP_URL = "http://vessel-integrations:8088/mcp/sse"

async def execute_task(task: TaskDefinition, jit_token: str):
    """
    Main agent execution loop. Connects to the MCP server, retrieves
    the available tools, and runs the ReAct loop until the task is complete.
    """
    llm = AsyncOpenAI()
    
    # 1. Open MCP session with the agent's JIT token as auth context
    async with sse_client(INTEGRATIONS_MCP_URL, headers={"Authorization": f"Bearer {jit_token}"}) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 2. Retrieve the tools available to THIS agent (filtered by allowlist)
            tools_response = await session.list_tools()
            openai_tools = [convert_mcp_tool_to_openai(t) for t in tools_response.tools]
            
            # 3. Run the ReAct loop
            messages = [
                {"role": "system", "content": task.system_prompt},
                {"role": "user", "content": task.instructions}
            ]
            
            while True:
                response = await llm.chat.completions.create(
                    model=task.model_id,
                    messages=messages,
                    tools=openai_tools,
                    tool_choice="auto"
                )
                
                message = response.choices[0].message
                
                # If no tool call, the task is complete
                if not message.tool_calls:
                    return message.content
                
                # 4. Execute each tool call via MCP
                messages.append(message)
                for tool_call in message.tool_calls:
                    result = await session.call_tool(
                        tool_call.function.name,
                        arguments=json.loads(tool_call.function.arguments)
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result.content[0].text
                    })


def convert_mcp_tool_to_openai(mcp_tool) -> dict:
    """Converts an MCP Tool object to the OpenAI function-calling format."""
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.name,
            "description": mcp_tool.description,
            "parameters": mcp_tool.inputSchema
        }
    }
```

---

## 8. The A2A Protocol Server as an MCP Resource

The A2A Protocol Server in `vessel-identity` must also expose agent discovery as an **MCP Resource**, allowing agents to discover and hire other agents programmatically using the same MCP client they use for tools.

```python
# In vessel-identity's MCP server registration

@mcp_server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="maars://agents/registry",
            name="Agent Registry",
            description="Browse and discover available MAARS agents by capability",
            mimeType="application/json"
        )
    ]

@mcp_server.read_resource()
async def read_resource(uri: str) -> str:
    if uri == "maars://agents/registry":
        agents = await query_ans_registry()
        return json.dumps(agents)
```

---

## 9. Webhook Outbound System

The spec lists `POST /v1/webhooks` as a public API endpoint but provides no implementation detail. This is the outbound webhook system that notifies external systems when MAARS events occur.

### 9.1 Webhook Registration Schema

```sql
CREATE TABLE webhook_subscriptions (
    webhook_id UUID PRIMARY KEY,
    tenant_id UUID,
    target_url TEXT,
    secret_hash TEXT,           -- HMAC-SHA256 secret for payload signing
    events list<TEXT>,          -- e.g., ["goal.completed", "escrow.escalated"]
    is_active BOOLEAN,
    created_at TIMESTAMP
);
```

### 9.2 Webhook Delivery Service

The webhook delivery service runs as a Kafka consumer, listening to all system events and fanning out to registered webhook endpoints.

```python
# vessel_integrations/webhook_dispatcher.py
import hmac, hashlib, httpx, json
from kafka import KafkaConsumer

WEBHOOK_EVENTS = [
    "goal.completed", "goal.failed",
    "escrow.escalated", "escrow.approved", "escrow.rejected",
    "guardrail.blocked", "agent.spawned", "agent.completed"
]

async def dispatch_webhook(subscription: dict, event: dict):
    """Sign and deliver a webhook payload to a registered endpoint."""
    payload = json.dumps(event).encode("utf-8")
    secret = subscription["secret_hash"].encode("utf-8")
    
    # Sign payload with HMAC-SHA256 (same pattern as Stripe/GitHub webhooks)
    signature = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                subscription["target_url"],
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-MAARS-Signature-256": f"sha256={signature}",
                    "X-MAARS-Event": event["event"],
                    "X-MAARS-Delivery": str(event.get("delivery_id"))
                },
                timeout=10.0
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            # Queue for retry with exponential backoff
            await queue_webhook_retry(subscription["webhook_id"], event, attempt=1)
```

### 9.3 Webhook Retry Policy

| Attempt | Delay | Total Elapsed |
|---|---|---|
| 1 (initial) | Immediate | 0s |
| 2 | 5 seconds | 5s |
| 3 | 30 seconds | 35s |
| 4 | 5 minutes | ~5m |
| 5 | 30 minutes | ~35m |
| Final | 2 hours | ~2.5h |

After 6 failed attempts, the webhook subscription is marked `is_active = false` and the tenant is notified via email.

---

## 10. Kafka Event Schema for `vessel-integrations`

`vessel-integrations` produces the following Kafka events:

| Topic | Event Type | Payload Fields | Description |
|---|---|---|---|
| `tool.events` | `tool.executed` | `task_id`, `agent_id`, `tenant_id`, `tool_name`, `cost_usd`, `duration_ms`, `status` | Every successful tool execution |
| `tool.events` | `tool.failed` | `task_id`, `agent_id`, `tool_name`, `error_code`, `error_message` | Every failed tool execution |
| `tool.events` | `tool.blocked` | `task_id`, `agent_id`, `tool_name`, `reason` | Tool call blocked by allowlist check |
| `webhook.events` | `webhook.delivered` | `webhook_id`, `tenant_id`, `event_type`, `status_code` | Successful webhook delivery |
| `webhook.events` | `webhook.failed` | `webhook_id`, `tenant_id`, `event_type`, `attempt`, `error` | Failed webhook delivery |

---

## 11. Security Considerations for the Integration Layer

The integration layer is the highest-risk surface in the system because it is the bridge between the sandboxed agent world and real external systems. The following controls are mandatory:

**Credential Isolation:** Tenant credentials must never be logged, included in Kafka events, or stored anywhere except HashiCorp Vault. The `ToolExecution` record in AstraDB stores only the tool name and result — never the credentials used.

**SSRF Prevention:** The `http_request` connector must validate all target URLs against a per-tenant allowlist before making any outbound request. Requests to private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.1`) must be unconditionally blocked to prevent Server-Side Request Forgery attacks.

**Rate Limiting per Connector:** Each connector must enforce per-tenant rate limits to prevent a runaway agent from exhausting a tenant's API quota. Rate limits are stored in Redis with the key pattern `ratelimit:{tenant_id}:{connector_name}`.

**OAuth Token Refresh:** The OAuth2 connectors (Salesforce, Google, Slack, etc.) must implement automatic token refresh. When a `401 Unauthorized` response is received, the service must refresh the token via Vault, retry the request once, and update the Vault secret with the new token.

---

*This document, combined with the MAARS Technical Architecture Spec and the Master Implementation Guide, provides the complete specification for the `vessel-integrations` service. The MCP server, Connector Registry, and Webhook system together constitute the full API and tool integration layer of the MAARS platform.*
