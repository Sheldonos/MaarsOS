# MAARS Critical Gap Remediation: Part 1

## Remedy 1.1: The Universal Meta-Language for Prompts
**Target Service:** `vessel-llm-router`
**Status:** CRITICAL (Phase 1 Blocker)

To enable true model-agnostic routing and fallback chains, `vessel-llm-router` must accept a standardized Abstract Syntax Tree (AST) for prompts and compile it down to provider-specific formats at runtime.

### 1. The Universal Prompt AST (JSON Schema)

All internal services (`vessel-swarm`, `vessel-observability`) must send prompts to the router using this exact schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MAARS Universal Prompt AST",
  "type": "object",
  "required": ["messages"],
  "properties": {
    "messages": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["role", "content"],
        "properties": {
          "role": {
            "type": "string",
            "enum": ["system", "user", "assistant", "tool_call", "tool_result"]
          },
          "content": {
            "type": ["string", "array"],
            "description": "String for text, Array for multimodal (images)"
          },
          "tool_call_id": {
            "type": "string",
            "description": "Required if role is tool_call or tool_result"
          },
          "tool_name": {
            "type": "string",
            "description": "Required if role is tool_call"
          },
          "tool_arguments": {
            "type": "object",
            "description": "Required if role is tool_call"
          }
        }
      }
    },
    "tools": {
      "type": "array",
      "description": "Array of JSON Schema tool definitions (MCP format)",
      "items": {
        "type": "object",
        "required": ["name", "description", "input_schema"],
        "properties": {
          "name": { "type": "string" },
          "description": { "type": "string" },
          "input_schema": { "type": "object" }
        }
      }
    },
    "routing_hints": {
      "type": "object",
      "properties": {
        "tier": { "enum": ["nano", "mid", "frontier"] },
        "max_cost_usd": { "type": "number" },
        "latency_sensitive": { "type": "boolean" }
      }
    }
  }
}
```

### 2. The Compiler Logic (Go Implementation)

The `vessel-llm-router` implements compiler interfaces for each provider. Here is the Anthropic (Claude) compiler implementation, which handles Anthropic's strict requirement that `system` prompts be separated from the `messages` array:

```go
// vessel-llm-router/compilers/anthropic.go
package compilers

import (
	"encoding/json"
	"errors"
)

type AnthropicCompiler struct{}

func (c *AnthropicCompiler) Compile(ast UniversalPromptAST) (map[string]interface{}, error) {
	payload := make(map[string]interface{})
	var messages []map[string]interface{}
	var systemPrompt string

	// 1. Extract System Prompt (Anthropic requires this at the top level)
	for _, msg := range ast.Messages {
		if msg.Role == "system" {
			systemPrompt += msg.Content.(string) + "\n"
		}
	}
	if systemPrompt != "" {
		payload["system"] = systemPrompt
	}

	// 2. Compile Messages
	for _, msg := range ast.Messages {
		if msg.Role == "system" {
			continue // Already handled
		}

		anthropicMsg := map[string]interface{}{
			"role": msg.Role,
		}

		switch msg.Role {
		case "user", "assistant":
			anthropicMsg["content"] = msg.Content
		case "tool_call":
			anthropicMsg["role"] = "assistant"
			anthropicMsg["content"] = []map[string]interface{}{
				{
					"type":  "tool_use",
					"id":    msg.ToolCallID,
					"name":  msg.ToolName,
					"input": msg.ToolArguments,
				},
			}
		case "tool_result":
			anthropicMsg["role"] = "user"
			anthropicMsg["content"] = []map[string]interface{}{
				{
					"type":     "tool_result",
					"tool_use_id": msg.ToolCallID,
					"content":  msg.Content,
				},
			}
		}
		messages = append(messages, anthropicMsg)
	}
	payload["messages"] = messages

	// 3. Compile Tools
	if len(ast.Tools) > 0 {
		var anthropicTools []map[string]interface{}
		for _, t := range ast.Tools {
			anthropicTools = append(anthropicTools, map[string]interface{}{
				"name":        t.Name,
				"description": t.Description,
				"input_schema": t.InputSchema,
			})
		}
		payload["tools"] = anthropicTools
	}

	return payload, nil
}
```

---

## Remedy 2.1: The Right-Sizing Engine Algorithm
**Target Service:** `vessel-orchestrator`
**Status:** CRITICAL (Phase 1 Blocker)

The Right-Sizing Engine must be a fast, deterministic heuristic, *not* an LLM call. Using an LLM to route LLM calls introduces unacceptable latency and cost overhead.

### 1. The Heuristic Scoring Algorithm

The engine calculates a `ComplexityScore` (0 to 100) for each `TaskDefinition` based on three deterministic vectors: Instruction Complexity, Tool Complexity, and Output Complexity.

```python
# vessel_orchestrator/right_sizing.py
import json

def calculate_task_complexity(task_def: dict) -> int:
    score = 0
    
    # Vector 1: Instruction Complexity (Max 30 points)
    # Proxy: Word count and presence of conditional logic words
    word_count = len(task_def["instructions"].split())
    if word_count < 50:
        score += 5
    elif word_count < 200:
        score += 15
    else:
        score += 30
        
    conditionals = ["if", "then", "else", "unless", "analyze", "synthesize", "compare"]
    condition_count = sum(1 for word in conditionals if word in task_def["instructions"].lower())
    score += min(condition_count * 2, 10) # Cap at 10 extra points
    
    # Vector 2: Tool Complexity (Max 40 points)
    # Proxy: Number of tools and type of tools
    tool_count = len(task_def.get("tool_allowlist", []))
    if tool_count == 0:
        score += 0
    elif tool_count <= 2:
        score += 10
    elif tool_count <= 5:
        score += 25
    else:
        score += 40
        
    # High-stakes tools automatically bump complexity
    high_stakes_tools = ["execute_python", "execute_shell", "stripe_create_charge", "salesforce_create_record"]
    if any(tool in high_stakes_tools for tool in task_def.get("tool_allowlist", [])):
        score += 15
        
    # Vector 3: Output Complexity (Max 30 points)
    # Proxy: Depth of the required JSON schema
    output_schema = task_def.get("expected_output_schema", {})
    if not output_schema:
        score += 5 # Simple text output
    else:
        schema_str = json.dumps(output_schema)
        nesting_depth = schema_str.count("{") - schema_str.count("}") # Rough proxy for depth
        if nesting_depth <= 1:
            score += 10
        elif nesting_depth <= 3:
            score += 20
        else:
            score += 30
            
    return min(score, 100)
```

### 2. The Tier Assignment Logic

Once the `ComplexityScore` is calculated, the engine assigns the tier and sets the budget ceiling.

```python
def assign_tier(task_def: dict) -> dict:
    complexity = calculate_task_complexity(task_def)
    
    if complexity <= 35:
        return {
            "tier": "nano",
            "model_id": "llama-3-8b-instruct",
            "budget_ceiling_usd": 0.05,
            "reasoning": f"Score {complexity}: Simple task, low tool count."
        }
    elif complexity <= 75:
        return {
            "tier": "mid",
            "model_id": "llama-3-70b-instruct",
            "budget_ceiling_usd": 0.50,
            "reasoning": f"Score {complexity}: Moderate complexity, standard tools."
        }
    else:
        return {
            "tier": "frontier",
            "model_id": "gpt-4.1",
            "budget_ceiling_usd": 5.00,
            "reasoning": f"Score {complexity}: High complexity, deep reasoning required."
        }
```
## Remedy 1.2: The A2A JSON-RPC 2.0 Payload Schemas
**Target Service:** `vessel-identity` (A2A Protocol Server)
**Status:** HIGH (Phase 3 Blocker)

To enable cross-organizational agent commerce, the A2A Protocol Server must implement strict JSON-RPC 2.0 schemas. Below are the exact payload definitions for the four core methods.

### 1. HTTP Headers for A2A Requests

All A2A requests must be sent over HTTPS and include the following headers:
- `Content-Type: application/json`
- `X-A2A-DID`: The decentralized identifier of the calling agent (e.g., `did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK`)
- `X-A2A-Signature`: An Ed25519 signature of the request body, signed by the calling agent's private key.

### 2. Method: `message/send` (Task Delegation)

This method is used by an external agent to hire a MAARS agent.

**Request Payload:**
```json
{
  "jsonrpc": "2.0",
  "method": "message/send",
  "id": "req-12345",
  "params": {
    "task": {
      "instructions": "Analyze the attached Q3 financial report and extract all risk factors.",
      "expected_output_schema": {
        "type": "object",
        "properties": {
          "risk_factors": { "type": "array", "items": { "type": "string" } }
        }
      },
      "budget_ceiling_usd": 5.00,
      "deadline_iso": "2026-03-23T12:00:00Z"
    },
    "attachments": [
      {
        "filename": "q3_report.pdf",
        "mime_type": "application/pdf",
        "content_base64": "JVBERi0xLjQKJcOkw7zDtsOfCjIgMCBvYmoKPDwvTGVuZ3RoIDMgMCBSL0ZpbHRlci9GbGF0ZURlY29kZT4+..."
      }
    ],
    "verifiable_credential": {
      "@context": ["https://www.w3.org/2018/credentials/v1"],
      "type": ["VerifiableCredential", "AgentDelegationCredential"],
      "issuer": "did:web:org-b.com",
      "issuanceDate": "2026-03-22T00:00:00Z",
      "credentialSubject": {
        "id": "did:key:z6MkhaXg...",
        "liability_cap_usd": 10000
      },
      "proof": {
        "type": "Ed25519Signature2020",
        "created": "2026-03-22T00:00:00Z",
        "proofPurpose": "assertionMethod",
        "verificationMethod": "did:web:org-b.com#key-1",
        "jws": "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..signature_bytes"
      }
    }
  }
}
```

**Response Payload:**
```json
{
  "jsonrpc": "2.0",
  "id": "req-12345",
  "result": {
    "task_id": "task-98765",
    "status": "accepted",
    "estimated_cost_usd": 1.50,
    "payment_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
  }
}
```

### 3. Method: `tasks/get` (Status Polling)

**Request Payload:**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks/get",
  "id": "req-12346",
  "params": {
    "task_id": "task-98765"
  }
}
```

**Response Payload (Completed):**
```json
{
  "jsonrpc": "2.0",
  "id": "req-12346",
  "result": {
    "task_id": "task-98765",
    "status": "completed",
    "actual_cost_usd": 1.42,
    "output": {
      "risk_factors": [
        "Supply chain disruption in APAC region",
        "Increased regulatory scrutiny in EU market"
      ]
    },
    "output_signature": "Ed25519_signature_of_output_object"
  }
}
```

---

## Remedy 2.2: The Context Graph Engine (Arize Phoenix) Integration
**Target Service:** `vessel-observability`
**Status:** HIGH (Phase 3 Blocker)

The spec claims the Guardrail Agent feeds decisions into Arize Phoenix to build a `FailurePattern` database, but provides no pipeline. This requires a two-part implementation: OpenTelemetry attribute mapping and a background extraction worker.

### 1. OpenTelemetry Span Attribute Mapping

When the Inline Guardrail Agent evaluates a reasoning chain, it must emit a span with specific attributes that Arize Phoenix's LLM evaluation engine can parse.

```python
# vessel_observability/guardrail.py
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def record_guardrail_decision(task_id: str, agent_id: str, prompt: str, completion: str, decision: str, reason: str):
    with tracer.start_as_current_span("guardrail_evaluation") as span:
        # Standard OpenLLMetry attributes
        span.set_attribute("llm.prompt_template.template", prompt)
        span.set_attribute("llm.completions.content", completion)
        
        # Custom MAARS Guardrail attributes required for Arize Phoenix
        span.set_attribute("maars.guardrail.decision", decision) # PASS, BLOCK, ESCALATE
        span.set_attribute("maars.guardrail.reason", reason)
        span.set_attribute("maars.agent.id", agent_id)
        span.set_attribute("maars.task.id", task_id)
        
        # If blocked, mark the span as an error so Arize flags it
        if decision in ["BLOCK", "ESCALATE"]:
            span.set_status(trace.Status(trace.StatusCode.ERROR, reason))
```

### 2. The Failure Pattern Extraction Worker

Arize Phoenix clusters similar errors using UMAP and HDBSCAN. MAARS needs a background worker to query Arize's GraphQL API, extract these clusters, and write them to the `FailurePattern` table in PostgreSQL so the `vessel-self-improvement` module can use them.

```python
# vessel_observability/workers/arize_extractor.py
import httpx
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

ARIZE_GRAPHQL_URL = "https://app.arize.com/graphql"
ARIZE_API_KEY = "..." # Loaded from Vault

async def extract_failure_patterns(db_session: AsyncSession):
    """Runs hourly to extract error clusters from Arize Phoenix."""
    
    query = """
    query GetErrorClusters($spaceId: ID!) {
      space(id: $spaceId) {
        errorClusters(timeRange: "LAST_24_HOURS") {
          id
          name
          description
          spanCount
          commonAttributes {
            key
            value
          }
          representativeSpans(limit: 5) {
            attributes
          }
        }
      }
    }
    """
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            ARIZE_GRAPHQL_URL,
            headers={"Authorization": f"Bearer {ARIZE_API_KEY}"},
            json={"query": query, "variables": {"spaceId": "maars_prod"}}
        )
        data = response.json()
        
    clusters = data["data"]["space"]["errorClusters"]
    
    for cluster in clusters:
        # Extract the affected agent types from the common attributes
        affected_agents = [
            attr["value"] for attr in cluster["commonAttributes"] 
            if attr["key"] == "maars.agent.id"
        ]
        
        # Generate a recommended fix using an LLM call based on the representative spans
        recommended_fix = await generate_fix_recommendation(cluster["representativeSpans"])
        
        # Upsert into MAARS PostgreSQL
        await db_session.execute(
            """
            INSERT INTO failure_patterns 
            (pattern_id, pattern_type, frequency, affected_agent_types, recommended_fix)
            VALUES (:id, :name, :count, :agents, :fix)
            ON CONFLICT (pattern_id) DO UPDATE SET
            frequency = EXCLUDED.frequency,
            recommended_fix = EXCLUDED.recommended_fix
            """,
            {
                "id": cluster["id"],
                "name": cluster["name"],
                "count": cluster["spanCount"],
                "agents": affected_agents,
                "fix": recommended_fix
            }
        )
    await db_session.commit()
```
## Remedy 3.1: The Materialize CDC Ingestion Pipeline
**Target Service:** `vessel-simulation`
**Status:** HIGH (Phase 4 Blocker)

The Digital Twin requires live enterprise data, not just internal agent state. This is achieved by deploying Debezium as a Kafka Connect source to stream Change Data Capture (CDC) events from external databases into the MAARS Kafka cluster, where Materialize can consume them.

### 1. Debezium Connector Configuration (PostgreSQL Example)

This configuration streams a tenant's external CRM database into the MAARS Kafka cluster.

```json
// debezium-postgres-connector.json
{
  "name": "tenant-123-crm-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "tasks.max": "1",
    "database.hostname": "crm-db.tenant123.internal",
    "database.port": "5432",
    "database.user": "maars_cdc_user",
    "database.password": "${vault:secret/data/tenant-123/crm-db:password}",
    "database.dbname": "crm_production",
    "database.server.name": "tenant_123_crm",
    "table.include.list": "public.customers,public.opportunities,public.contracts",
    "plugin.name": "pgoutput",
    "publication.name": "maars_cdc_pub",
    "slot.name": "maars_cdc_slot",
    "transforms": "unwrap",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.unwrap.drop.tombstones": "false"
  }
}
```

### 2. Materialize Source Definition

Materialize ingests this Kafka stream and creates a continuously updated materialized view that the `vessel-simulation` engine can query.

```sql
-- vessel_simulation/materialize/setup.sql

-- 1. Create the Kafka Source
CREATE SOURCE tenant_123_opportunities_source
FROM KAFKA BROKER 'kafka.maars.internal:9092' TOPIC 'tenant_123_crm.public.opportunities'
FORMAT JSON ENVELOPE DEBEZIUM;

-- 2. Create the Materialized View for the Digital Twin
CREATE MATERIALIZED VIEW active_pipeline_value AS
SELECT 
    customer_id,
    SUM(expected_value_usd) as total_pipeline,
    COUNT(*) as open_opportunities
FROM tenant_123_opportunities_source
WHERE stage NOT IN ('Closed Won', 'Closed Lost')
GROUP BY customer_id;
```

---

## Remedy 3.2: The Memory Provenance Cryptography
**Target Service:** `vessel-memory`
**Status:** MEDIUM (Phase 2 Blocker)

To prevent memory poisoning, every `MemoryNode` must have a deterministic `provenance_hash` that cryptographically links it to its source.

### 1. The Hashing Algorithm

The hash is a SHA-256 digest of a specific, ordered concatenation of fields.

```python
# vessel_memory/provenance.py
import hashlib
import json

def generate_provenance_hash(
    tenant_id: str, 
    agent_id: str, 
    task_id: str, 
    source_type: str, # e.g., "tool_execution", "llm_generation", "user_input"
    source_id: str,   # e.g., exec_id, span_id, message_id
    content: str
) -> str:
    """
    Generates a deterministic SHA-256 hash for a MemoryNode.
    """
    # 1. Create a strictly ordered dictionary
    payload = {
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "task_id": task_id,
        "source_type": source_type,
        "source_id": source_id,
        "content": content
    }
    
    # 2. Serialize to JSON with sorted keys and no whitespace to ensure determinism
    canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    
    # 3. Generate SHA-256 hash
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
```

---

## Remedy 4.1: The No-Code Agent Builder
**Target Service:** `vessel-interface` & `vessel-orchestrator`
**Status:** HIGH (GTM Blocker)

The No-Code Canvas allows non-technical users to build agents. It requires a specific React component architecture and a compiler to translate the visual graph into a `TaskGraph`.

### 1. The `AgentTemplate` Schema

```sql
CREATE TABLE agent_templates (
    template_id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL, -- e.g., "Sales", "Legal", "Research"
    description TEXT,
    visual_graph_json JSONB NOT NULL, -- The React Flow state
    compiled_task_graph_json JSONB NOT NULL, -- The executable DAG
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. The Visual DAG Compiler (TypeScript)

This function runs in the Next.js BFF (Backend-for-Frontend) and translates the React Flow nodes/edges into the `TaskGraph` format required by `vessel-orchestrator`.

```typescript
// vessel-interface/lib/compiler.ts

interface ReactFlowNode {
  id: string;
  type: 'trigger' | 'agent' | 'tool' | 'condition';
  data: any;
}

interface ReactFlowEdge {
  source: string;
  target: string;
}

export function compileVisualGraphToTaskGraph(nodes: ReactFlowNode[], edges: ReactFlowEdge[]) {
  const taskGraph: any = {
    tasks: {},
    dependencies: {}
  };

  // 1. Map dependencies
  edges.forEach(edge => {
    if (!taskGraph.dependencies[edge.target]) {
      taskGraph.dependencies[edge.target] = [];
    }
    taskGraph.dependencies[edge.target].push(edge.source);
  });

  // 2. Compile nodes into TaskDefinitions
  nodes.forEach(node => {
    if (node.type === 'agent') {
      taskGraph.tasks[node.id] = {
        task_id: node.id,
        instructions: node.data.systemPrompt,
        tool_allowlist: node.data.selectedTools,
        model_tier: node.data.tierOverride || 'auto' // Let Right-Sizing Engine decide if 'auto'
      };
    }
  });

  return taskGraph;
}
```
