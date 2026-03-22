# MAARS Master Implementation Guide: Bridging the Gap from Architecture to Code

**Date:** March 22, 2026
**Author:** Manus AI
**Project:** MAARS (Master Autonomous Agentic Runtime System)

This document serves as the definitive implementation guide for the MAARS development team. It bridges the gap between the high-level *MAARS Technical Architecture and Design Specification* and the low-level code required to build the system. It provides the exact API contracts, database schemas, infrastructure configurations, and AI orchestration specifics needed to commence development.

---

## Part 1: API Contracts & Interface Definitions

The following sections define the exact contracts for the REST APIs, gRPC services, and WebSocket channels.

### 1.1 Public REST API (OpenAPI 3.0 Snippets)

The `vessel-gateway` exposes the public REST API. Below are the core OpenAPI 3.0 schema definitions for the primary endpoints.

```yaml
openapi: 3.0.3
info:
  title: MAARS Public API
  version: 1.0.0
servers:
  - url: https://api.maars.ai/v1
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
  schemas:
    GoalPacket:
      type: object
      properties:
        goal_id:
          type: string
          format: uuid
        tenant_id:
          type: string
          format: uuid
        description:
          type: string
        priority:
          type: string
          enum: [LOW, NORMAL, HIGH, CRITICAL]
        total_budget_usd:
          type: number
          format: float
        status:
          type: string
          enum: [PENDING, PLANNING, EXECUTING, PAUSED, COMPLETED, FAILED]
    AgentProfile:
      type: object
      properties:
        agent_id:
          type: string
          format: uuid
        name:
          type: string
        capabilities:
          type: array
          items:
            type: string
        model_tier:
          type: string
          enum: [NANO, MID, FRONTIER]
        budget_ceiling_usd:
          type: number
          format: float

paths:
  /goals:
    post:
      summary: Submit a new goal
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [description]
              properties:
                description:
                  type: string
                priority:
                  type: string
                  default: NORMAL
                total_budget_usd:
                  type: number
      responses:
        '201':
          description: Goal created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GoalPacket'
```

### 1.2 Internal gRPC Protobuf Definitions

Internal microservices communicate synchronously via gRPC. Below is the `.proto` definition for the `vessel-orchestrator` to `vessel-llm-router` communication.

```protobuf
syntax = "proto3";

package maars.llm;

service LLMRouter {
  rpc RoutePrompt (RouteRequest) returns (RouteResponse) {}
}

message Message {
  string role = 1; // system, user, assistant, tool
  string content = 2;
}

message RouteRequest {
  string task_id = 1;
  string tenant_id = 2;
  repeated Message messages = 3;
  string model_tier = 4; // NANO, MID, FRONTIER
  float max_cost_usd = 5;
  repeated string tool_allowlist = 6;
}

message RouteResponse {
  string completion = 1;
  string model_used = 2;
  int32 prompt_tokens = 3;
  int32 completion_tokens = 4;
  float cost_usd = 5;
  bool cached_hit = 6;
}
```

### 1.3 WebSocket Event Payloads

The Next.js frontend connects to `vessel-gateway` via WebSockets. Below are the exact JSON payloads for the `/swarm` channel.

**Event: `agent.spawned`**
```json
{
  "event": "agent.spawned",
  "timestamp": "2026-03-22T10:00:00Z",
  "payload": {
    "agent_id": "uuid-v4",
    "task_id": "uuid-v4",
    "tier": "MID",
    "capabilities": ["web_search", "data_analysis"]
  }
}
```

**Event: `agent.executing`**
```json
{
  "event": "agent.executing",
  "timestamp": "2026-03-22T10:00:05Z",
  "payload": {
    "agent_id": "uuid-v4",
    "active_tool": "execute_sql_query",
    "token_burn_rate_per_sec": 150
  }
}
```


---

## Part 2: AstraDB Data Layer Implementation

Based on the architectural assessment, MAARS will use DataStax AstraDB to replace PostgreSQL, Neo4j, Qdrant, Redis, and ClickHouse. The following sections provide the exact CQL schemas and configurations required.

### 2.1 Core Relational/Document Schemas (CQL)

The following CQL scripts define the core tables, utilizing AstraDB's wide-column architecture and JSON support for flexible schemas.

```sql
-- Keyspace creation (handled by AstraDB UI/API, shown for context)
-- CREATE KEYSPACE maars WITH replication = {'class': 'NetworkTopologyStrategy', 'us-east1': 3};

USE maars;

-- Tenant & Identity Layer
CREATE TABLE tenants (
    tenant_id UUID PRIMARY KEY,
    name TEXT,
    plan_tier TEXT,
    credit_balance DECIMAL,
    settings_json TEXT,
    created_at TIMESTAMP
);

CREATE TABLE users (
    tenant_id UUID,
    user_id UUID,
    email TEXT,
    role TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, user_id)
);

CREATE TABLE agent_identities (
    tenant_id UUID,
    agent_id UUID,
    identity_id UUID,
    token_hash TEXT,
    scope_json TEXT,
    delegation_chain_json TEXT,
    expires_at TIMESTAMP,
    PRIMARY KEY (tenant_id, agent_id, identity_id)
);

-- Orchestration Layer
CREATE TABLE goal_packets (
    tenant_id UUID,
    goal_id UUID,
    owner_user_id UUID,
    description TEXT,
    priority TEXT,
    total_budget_usd DECIMAL,
    spent_usd DECIMAL,
    status TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    PRIMARY KEY (tenant_id, goal_id)
);

CREATE TABLE task_definitions (
    tenant_id UUID,
    goal_id UUID,
    task_id UUID,
    assigned_agent_id UUID,
    instructions TEXT,
    tool_allowlist list<TEXT>,
    budget_ceiling_usd DECIMAL,
    model_tier TEXT,
    status TEXT,
    PRIMARY KEY ((tenant_id, goal_id), task_id)
);
```

### 2.2 Vector Search Configuration (Replacing Qdrant)

AstraDB natively supports vector embeddings via Storage-Attached Indexing (SAI). The `MemoryNode` table is defined as follows to support semantic search.

```sql
-- Memory Layer (Vector Store)
CREATE TABLE memory_nodes (
    tenant_id UUID,
    agent_id UUID,
    node_id UUID,
    content TEXT,
    embedding VECTOR<FLOAT, 1536>, -- Assuming OpenAI text-embedding-3-small
    memory_type TEXT,
    importance_score FLOAT,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, agent_id, node_id)
);

-- Create the Storage-Attached Index for vector search
CREATE CUSTOM INDEX ON memory_nodes(embedding) USING 'StorageAttachedIndex'
WITH OPTIONS = {'similarity_function': 'cosine'};
```

### 2.3 GraphRAG Implementation (Replacing Neo4j)

To replace Neo4j, we model the knowledge graph using adjacency lists in AstraDB, combined with vector search for the nodes.

```sql
-- Knowledge Graph Nodes
CREATE TABLE kg_nodes (
    tenant_id UUID,
    kg_node_id UUID,
    entity_type TEXT,
    entity_name TEXT,
    properties_json TEXT,
    embedding VECTOR<FLOAT, 1536>,
    PRIMARY KEY (tenant_id, kg_node_id)
);

CREATE CUSTOM INDEX ON kg_nodes(embedding) USING 'StorageAttachedIndex'
WITH OPTIONS = {'similarity_function': 'cosine'};

-- Knowledge Graph Edges (Adjacency List)
CREATE TABLE kg_edges (
    tenant_id UUID,
    source_kg_node_id UUID,
    relationship_type TEXT,
    target_kg_node_id UUID,
    weight FLOAT,
    PRIMARY KEY ((tenant_id, source_kg_node_id), relationship_type, target_kg_node_id)
);
```

*Query Strategy:* To perform GraphRAG, the `vessel-memory` service will first query `kg_nodes` using vector similarity to find the entry point, then query `kg_edges` using the `source_kg_node_id` to traverse the graph.

### 2.4 Event Streaming (Replacing Kafka)

The architecture will use **Astra Streaming** (built on Apache Pulsar) with the "Starlight for Kafka" API. 
*   **Action Required:** No code changes are needed in the microservices. The `KAFKA_BROKERS` environment variable simply needs to be pointed to the Astra Streaming Kafka-compatible endpoint (e.g., `kafka.astra.datastax.com:9092`), and the SASL/JAAS configuration updated with the Astra token.


---

## Part 3: Infrastructure as Code (IaC) & Deployment

The following sections provide the Terraform and Kubernetes configurations required to deploy the MAARS architecture.

### 3.1 Terraform: Core Cloud Infrastructure (AWS EKS)

This Terraform snippet provisions the foundational EKS cluster and the S3 bucket for artifact storage.

```hcl
# main.tf
provider "aws" {
  region = "us-east-1"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"
  name    = "maars-vpc"
  cidr    = "10.0.0.0/16"
  azs     = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  enable_nat_gateway = true
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.0.0"
  cluster_name    = "maars-cluster"
  cluster_version = "1.29"
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets

  eks_managed_node_groups = {
    general = {
      min_size     = 3
      max_size     = 10
      desired_size = 3
      instance_types = ["m6i.xlarge"]
    }
    wasm_compute = {
      min_size     = 2
      max_size     = 20
      desired_size = 2
      instance_types = ["c6i.2xlarge"] # Compute optimized for Wasmtime
      labels = {
        workload = "wasm-sandbox"
      }
    }
  }
}

resource "aws_s3_bucket" "artifacts" {
  bucket = "maars-artifacts-prod"
}

resource "aws_s3_bucket_versioning" "artifacts_versioning" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}
```

### 3.2 Kubernetes Manifests: Microservice Deployment

Below is the standard Kubernetes Deployment and Service manifest template used for the Python-based microservices (e.g., `vessel-orchestrator`).

```yaml
# vessel-orchestrator-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vessel-orchestrator
  namespace: maars-core
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vessel-orchestrator
  template:
    metadata:
      labels:
        app: vessel-orchestrator
      annotations:
        sidecar.istio.io/inject: "true" # Enable Istio mTLS
    spec:
      containers:
      - name: vessel-orchestrator
        image: maars/vessel-orchestrator:latest
        ports:
        - containerPort: 8081
        envFrom:
        - configMapRef:
            name: maars-global-config
        - secretRef:
            name: maars-db-secrets
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "1Gi"
---
apiVersion: v1
kind: Service
metadata:
  name: vessel-orchestrator
  namespace: maars-core
spec:
  selector:
    app: vessel-orchestrator
  ports:
    - protocol: TCP
      port: 8081
      targetPort: 8081
```

### 3.3 CI/CD Pipeline (GitHub Actions)

This GitHub Actions workflow defines the build, test, and deploy process for a microservice.

```yaml
# .github/workflows/deploy-orchestrator.yml
name: Deploy Vessel Orchestrator

on:
  push:
    branches: [ "main" ]
    paths: [ "services/vessel-orchestrator/**" ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
        
    - name: Run Tests
      run: |
        cd services/vessel-orchestrator
        pip install -r requirements.txt
        pytest tests/
        
    - name: Build and Push Docker Image
      uses: docker/build-push-action@v5
      with:
        context: ./services/vessel-orchestrator
        push: true
        tags: maars/vessel-orchestrator:${{ github.sha }}
        
    - name: Update Kubernetes Manifest
      run: |
        sed -i 's/latest/${{ github.sha }}/g' k8s/vessel-orchestrator-deployment.yaml
        
    - name: Deploy to EKS
      uses: bitovi/github-actions-deploy-eks-helm@v1.2.8
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
        cluster-name: maars-cluster
        config-files: k8s/vessel-orchestrator-deployment.yaml
```


---

## Part 4: Security & Cryptography Implementation

This section details the cryptographic implementations for agent identity and the smart contracts for the economic layer.

### 4.1 W3C DID Implementation (`did:key`)

MAARS uses the `did:key` method with Ed25519 keypairs for agent identity, as it requires no blockchain anchoring for the initial phases, ensuring high throughput.

**Python Implementation Snippet (`vessel-identity`):**

```python
import ed25519
import base58
import json

def generate_agent_did():
    # Generate Ed25519 keypair
    signing_key, verifying_key = ed25519.create_keypair()
    
    # Format as did:key (multicodec prefix for ed25519-pub is 0xed01)
    # Note: Simplified for illustration. Actual implementation uses standard multicodec.
    pub_bytes = verifying_key.to_bytes()
    multicodec_pub = b'\xed\x01' + pub_bytes
    did_key = f"did:key:z{base58.b58encode(multicodec_pub).decode('utf-8')}"
    
    return {
        "did": did_key,
        "private_key_hex": signing_key.to_bytes().hex(),
        "public_key_hex": pub_bytes.hex()
    }

def sign_artifact(private_key_hex: str, payload: dict) -> str:
    signing_key = ed25519.SigningKey(bytes.fromhex(private_key_hex))
    payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
    signature = signing_key.sign(payload_bytes)
    return signature.hex()
```

### 4.2 Verifiable Credential (VC) JSON-LD Schema

When an agent engages in cross-org commerce, it presents a Verifiable Credential issued by its tenant.

```json
{
  "@context": [
    "https://www.w3.org/2018/credentials/v1",
    "https://maars.ai/credentials/v1"
  ],
  "id": "urn:uuid:3978344f-8596-4c3a-a978-8fcaba3903c5",
  "type": ["VerifiableCredential", "AgentCapabilityCredential"],
  "issuer": "did:web:tenant-domain.com",
  "issuanceDate": "2026-03-22T10:00:00Z",
  "credentialSubject": {
    "id": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
    "agentName": "ContractAnalyzer-Mid",
    "capabilities": ["contract-analysis", "legal-review"],
    "liabilityCapUSD": 10000.00,
    "insuranceBondAddress": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
  },
  "proof": {
    "type": "Ed25519Signature2020",
    "created": "2026-03-22T10:00:00Z",
    "proofPurpose": "assertionMethod",
    "verificationMethod": "did:web:tenant-domain.com#keys-1",
    "jws": "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..[signature]"
  }
}
```

### 4.3 Smart Contract: Algorithmic Liability Escrow (Solidity)

This Solidity contract (deployed on Ethereum L2 Base) manages the insurance bonds and algorithmic slashing for Phase 4 sovereign agents.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract AgenticLiabilityEscrow {
    struct AgentBond {
        uint256 stakedAmount;
        uint256 liabilityCap;
        bool isActive;
    }

    mapping(address => AgentBond) public agentBonds;
    address public maarsGovernanceDAO;

    event BondStaked(address indexed agent, uint256 amount);
    event BondSlashed(address indexed agent, address indexed victim, uint256 amount);

    modifier onlyGovernance() {
        require(msg.sender == maarsGovernanceDAO, "Only DAO can slash");
        _;
    }

    constructor(address _dao) {
        maarsGovernanceDAO = _dao;
    }

    function stakeBond(uint256 _liabilityCap) external payable {
        require(msg.value > 0, "Must stake ETH");
        agentBonds[msg.sender] = AgentBond({
            stakedAmount: msg.value,
            liabilityCap: _liabilityCap,
            isActive: true
        });
        emit BondStaked(msg.sender, msg.value);
    }

    // Called by the DAO after a verifiable harm event is proven
    function slashBond(address _agent, address payable _victim, uint256 _amount) external onlyGovernance {
        require(agentBonds[_agent].isActive, "Agent not active");
        require(agentBonds[_agent].stakedAmount >= _amount, "Insufficient bond");
        require(_amount <= agentBonds[_agent].liabilityCap, "Exceeds liability cap");

        agentBonds[_agent].stakedAmount -= _amount;
        _victim.transfer(_amount);

        emit BondSlashed(_agent, _victim, _amount);
    }
}
```

### 4.4 Wasmtime Sandbox Configuration (Rust)

The `vessel-sandbox` uses Wasmtime to isolate execution. Below is the Rust configuration enforcing the capability-based permissions.

```rust
use wasmtime::*;
use wasmtime_wasi::{WasiCtxBuilder, WasiCtx};

fn configure_sandbox(task_id: &str, network_policy: &str) -> Result<Store<WasiCtx>> {
    let mut config = Config::new();
    config.consume_fuel(true); // Enable token/fuel metering for cost control
    
    let engine = Engine::new(&config)?;
    
    let mut wasi_builder = WasiCtxBuilder::new()
        .inherit_stdio()
        .inherit_args()?;

    // Capability-based File System Access
    // Agents can ONLY access their specific task directory
    let task_dir = std::fs::File::open(format!("/tmp/maars/tasks/{}", task_id))?;
    let wasi_dir = wasmtime_wasi::Dir::from_std_file(task_dir);
    wasi_builder = wasi_builder.preopened_dir(wasi_dir, "/workspace")?;

    // Capability-based Network Access
    if network_policy == "RESTRICTED" {
        // Only allow connections to specific whitelisted APIs (e.g., Stripe, Salesforce)
        // Note: Wasmtime WASI networking is still evolving; this requires custom host functions
        // or a proxy sidecar in production.
    } else if network_policy == "ISOLATED" {
        // No network access granted
    }

    let wasi = wasi_builder.build();
    let mut store = Store::new(&engine, wasi);
    
    // Set execution limits (e.g., 10 million instructions)
    store.set_fuel(10_000_000)?;

    Ok(store)
}
```


---

## Part 5: AI Orchestration Specifics

This section provides the exact LangGraph implementation, system prompts, and the Right-Sizing Engine logic.

### 5.1 LangGraph DAG Planner (`vessel-orchestrator`)

The orchestrator uses LangGraph to decompose a high-level goal into a Directed Acyclic Graph (DAG) of sub-tasks.

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any

class GoalState(TypedDict):
    goal_id: str
    description: str
    tasks: List[Dict[str, Any]]
    current_task_index: int
    results: Dict[str, Any]
    status: str

def plan_tasks(state: GoalState) -> GoalState:
    # Call LLM (Frontier tier) to decompose state.description into a JSON array of tasks
    # Example output: [{"id": "t1", "desc": "Search web", "depends_on": []}, {"id": "t2", "desc": "Summarize", "depends_on": ["t1"]}]
    tasks = llm_decompose(state["description"])
    state["tasks"] = tasks
    state["status"] = "PLANNING_COMPLETE"
    return state

def execute_task(state: GoalState) -> GoalState:
    task = state["tasks"][state["current_task_index"]]
    # Dispatch to vessel-swarm via Kafka
    dispatch_to_swarm(task)
    # Wait for result (simplified for illustration; actual implementation is async)
    result = wait_for_task_completion(task["id"])
    state["results"][task["id"]] = result
    state["current_task_index"] += 1
    return state

def should_continue(state: GoalState) -> str:
    if state["current_task_index"] >= len(state["tasks"]):
        return "end"
    return "continue"

# Build the Graph
workflow = StateGraph(GoalState)
workflow.add_node("planner", plan_tasks)
workflow.add_node("executor", execute_task)

workflow.set_entry_point("planner")
workflow.add_edge("planner", "executor")
workflow.add_conditional_edges("executor", should_continue, {"continue": "executor", "end": END})

app = workflow.compile()
```

### 5.2 System Prompts

**Master Agent (Planner) Prompt:**
> You are the Master Orchestrator for the MAARS system. Your job is to take a high-level goal from a human operator and decompose it into a strictly ordered Directed Acyclic Graph (DAG) of sub-tasks. You must assign each sub-task a required capability (e.g., 'web_search', 'code_execution') and a maximum budget. Do not attempt to execute the tasks yourself. Output strictly in JSON format matching the TaskGraph schema.

**Inline Guardrail Agent Prompt:**
> You are the Inline Guardrail Agent. You sit between a Sub-Agent and its execution environment. You will be provided with the Sub-Agent's reasoning chain and its proposed tool call. You must evaluate this action against the tenant's safety policies and the agent's liability cap. 
> 
> Output a JSON object with three fields:
> 1. `confidence_score` (0.0 to 1.0)
> 2. `action` (must be exactly "PASS", "BLOCK", or "ESCALATE")
> 3. `reason` (a one-sentence explanation)
> 
> If the action involves spending money, signing a contract, or modifying production data, you MUST output "ESCALATE".

### 5.3 Right-Sizing Engine Logic

The Right-Sizing Engine assigns tasks to the most cost-effective LLM tier based on a deterministic heuristic.

```python
def assign_model_tier(task_description: str, required_capabilities: List[str]) -> str:
    # NANO Tier: Simple text processing, formatting, basic extraction
    nano_keywords = ["format", "extract", "parse", "summarize short"]
    if any(kw in task_description.lower() for kw in nano_keywords) and len(required_capabilities) == 0:
        return "NANO" # e.g., Llama-3-8B
        
    # FRONTIER Tier: Complex reasoning, coding, multi-step planning
    frontier_capabilities = ["code_execution", "contract_analysis", "strategic_planning"]
    if any(cap in required_capabilities for cap in frontier_capabilities):
        return "FRONTIER" # e.g., GPT-4.1, Claude 3.5 Sonnet
        
    # MID Tier: Default for standard agentic tasks (web search, data analysis)
    return "MID" # e.g., Llama-3-70B, GPT-4.1-mini
```

### 5.4 Tool/Skill JSON Schema (WASM Registry)

Tools available in the WASM sandbox are defined using standard JSON Schema, which is passed to the LLM for function calling.

```json
{
  "name": "execute_sql_query",
  "description": "Executes a read-only SQL query against the tenant's analytics database.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The PostgreSQL-compatible SQL query to execute. Must begin with SELECT."
      },
      "max_rows": {
        "type": "integer",
        "description": "Maximum number of rows to return",
        "default": 100
      }
    },
    "required": ["query"]
  }
}
```


---

## Part 6: Frontend Implementation Details

This section details the Next.js 15 frontend architecture, specifically the state management for the real-time canvas and the authentication flow.

### 6.1 State Management (Zustand)

The `Live Canvas` requires high-performance state management to handle rapid WebSocket updates without re-rendering the entire React tree. We use Zustand for this.

```typescript
// store/useSwarmStore.ts
import { create } from 'zustand';
import { Node, Edge } from 'reactflow';

interface AgentState {
  id: string;
  tier: 'NANO' | 'MID' | 'FRONTIER';
  status: 'IDLE' | 'PLANNING' | 'EXECUTING' | 'BLOCKED';
  activeTool?: string;
  tokenBurnRate: number;
}

interface SwarmStore {
  nodes: Node<AgentState>[];
  edges: Edge[];
  updateAgentStatus: (agentId: string, status: AgentState['status']) => void;
  setExecutingTool: (agentId: string, toolName: string, burnRate: number) => void;
  addAgentNode: (agent: AgentState, parentId?: string) => void;
}

export const useSwarmStore = create<SwarmStore>((set) => ({
  nodes: [],
  edges: [],
  
  updateAgentStatus: (agentId, status) => set((state) => ({
    nodes: state.nodes.map(node => 
      node.id === agentId ? { ...node, data: { ...node.data, status } } : node
    )
  })),

  setExecutingTool: (agentId, toolName, burnRate) => set((state) => ({
    nodes: state.nodes.map(node => 
      node.id === agentId ? { 
        ...node, 
        data: { ...node.data, status: 'EXECUTING', activeTool: toolName, tokenBurnRate: burnRate } 
      } : node
    )
  })),

  addAgentNode: (agent, parentId) => set((state) => {
    const newNode: Node<AgentState> = {
      id: agent.id,
      type: 'agentNode', // Custom React Flow node type
      position: { x: Math.random() * 500, y: Math.random() * 500 }, // Auto-layout applied later
      data: agent
    };
    
    const newEdge: Edge | null = parentId ? {
      id: `e-${parentId}-${agent.id}`,
      source: parentId,
      target: agent.id,
      animated: true,
    } : null;

    return {
      nodes: [...state.nodes, newNode],
      edges: newEdge ? [...state.edges, newEdge] : state.edges
    };
  })
}));
```

### 6.2 Authentication Flow (NextAuth.js)

MAARS uses NextAuth.js v5 configured with an OIDC provider (e.g., Auth0, Okta, or a custom Keycloak instance) to manage tenant access.

```typescript
// app/api/auth/[...nextauth]/route.ts
import NextAuth from "next-auth";
import { JWT } from "next-auth/jwt";
import { Session } from "next-auth";

export const authOptions = {
  providers: [
    {
      id: "maars-oidc",
      name: "MAARS Enterprise SSO",
      type: "oauth",
      wellKnown: process.env.OIDC_ISSUER_URL + "/.well-known/openid-configuration",
      authorization: { params: { scope: "openid email profile offline_access" } },
      clientId: process.env.OIDC_CLIENT_ID,
      clientSecret: process.env.OIDC_CLIENT_SECRET,
      profile(profile) {
        return {
          id: profile.sub,
          name: profile.name,
          email: profile.email,
          tenantId: profile.tenant_id, // Custom claim from IDP
          role: profile.role
        };
      },
    }
  ],
  callbacks: {
    async jwt({ token, user, account }) {
      if (account && user) {
        token.accessToken = account.access_token;
        token.tenantId = user.tenantId;
        token.role = user.role;
      }
      return token;
    },
    async session({ session, token }: { session: Session, token: JWT }) {
      session.accessToken = token.accessToken as string;
      session.user.tenantId = token.tenantId as string;
      session.user.role = token.role as string;
      return session;
    }
  }
};

const handler = NextAuth(authOptions);
export { handler as GET, handler as POST };
```

### 6.3 UI Component Specification: `AgentNode`

The custom React Flow node for agents must implement the Uncodixfy design principles (high density, professional, no glassmorphism).

```tsx
// components/canvas/AgentNode.tsx
import { Handle, Position } from 'reactflow';
import { AgentState } from '@/store/useSwarmStore';

export function AgentNode({ data }: { data: AgentState }) {
  const statusColors = {
    IDLE: 'bg-gray-200 border-gray-400',
    PLANNING: 'bg-blue-100 border-blue-500 animate-pulse',
    EXECUTING: 'bg-amber-100 border-amber-500',
    BLOCKED: 'bg-red-100 border-red-500'
  };

  return (
    <div className={`px-4 py-2 shadow-sm border-2 rounded-sm bg-white ${statusColors[data.status]}`}>
      <Handle type="target" position={Position.Top} className="w-2 h-2 rounded-none bg-gray-800" />
      
      <div className="flex flex-col">
        <div className="flex justify-between items-center mb-2">
          <span className="font-mono text-xs font-bold text-gray-800">{data.id.substring(0,8)}</span>
          <span className="text-[10px] px-1 bg-gray-800 text-white uppercase">{data.tier}</span>
        </div>
        
        <div className="text-sm font-medium text-gray-900">
          {data.status === 'EXECUTING' ? `Running: ${data.activeTool}` : data.status}
        </div>
        
        {data.status === 'EXECUTING' && (
          <div className="mt-2 text-xs text-gray-500 font-mono">
            Burn: {data.tokenBurnRate} t/s
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="w-2 h-2 rounded-none bg-gray-800" />
    </div>
  );
}
```

---
*End of Master Implementation Guide. This document, combined with the original Architecture Specification, provides the complete blueprint required for the engineering team to execute the MAARS build.*
