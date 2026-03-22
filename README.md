# MAARS - Master Autonomous Agentic Runtime System

**Version:** 1.0.0  
**Status:** Phase 1 - Foundation Build  
**Last Updated:** March 22, 2026

---

## 🎯 Project Overview

MAARS is an enterprise-grade autonomous agent runtime system built on WASM, Kafka, and AstraDB. It provides secure, scalable, multi-agent orchestration with deterministic guardrails, economic autonomy, and cross-organizational trust.

### Key Differentiators
- **WASM-First Sandboxing**: Millisecond startup, memory-safe execution
- **Deterministic Guardrails**: Policy-based escrow, not LLM-based security
- **Hierarchical Multi-Agent**: Master orchestrator with specialized sub-agents
- **Zero Trust NHI**: Just-in-time identity provisioning with CAEP
- **Model-Agnostic**: Bring your own LLM keys, automatic fallback chains

---

## 📚 Documentation Hierarchy

**Read these documents in order before writing code:**

1. `MAARS_Technical_Architecture_Design_Spec.md` - The Vision & Data Model
2. `Assessment_Replacing_Architecture_Data_Stores_with_AstraDB.pdf` - Database Strategy
3. `MAARS_Master_Implementation_Guide.md` - API Contracts & IaC
4. `MAARS Build Clarity Supplement_ Execution & Alignment` - Critical Path & Local Dev
5. `MAARS_MCP_API_Integration_Spec.md` - Tooling Protocol
6. `MAARS_Critical_Gap_Remediation_Master.md` - Algorithms & Schemas
7. `MAARS_Content_Layer_Deep_Analysis.md` - Prompts, Rules, & Design Tokens

---

## 🏗️ Architecture

### The 12 Core Microservices

| Service | Language | Purpose | Port |
|---------|----------|---------|------|
| `vessel-gateway` | Go | API Gateway (Kong) | 8000 |
| `vessel-orchestrator` | Python | LangGraph DAG Planner | 8081 |
| `vessel-identity` | Python | JIT Identity + A2A Protocol | 8083 |
| `vessel-memory` | Python | Vector Store + GraphRAG | 8084 |
| `vessel-llm-router` | Go | Multi-Provider LLM Gateway | 8082 |
| `vessel-sandbox` | Rust | WASM Execution Engine | 8085 |
| `vessel-swarm` | Python | Agent Lifecycle Manager | 8086 |
| `vessel-observability` | Python | OpenTelemetry + Guardrails | 8087 |
| `vessel-simulation` | Python | Digital Twin Engine | 8088 |
| `vessel-research` | Python | Autonomous Research Pipeline | 8089 |
| `vessel-economics` | Python | Escrow + Compliance | 8090 |
| `vessel-integrations` | Python | MCP Server + Connectors | 8091 |
| `vessel-interface` | TypeScript | Next.js 15 Frontend | 3000 |

### Data Layer (AstraDB)
- **Replaces**: PostgreSQL, Neo4j, Qdrant, Redis, ClickHouse, Kafka
- **Provides**: Multi-tenant CQL tables, Vector search, GraphRAG, Event streaming

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop 4.x+
- Node.js 20+
- Python 3.11+
- Rust 1.75+
- Go 1.22+

### 1. Start Local Infrastructure

```bash
cd infrastructure/docker
docker-compose up -d
```

This starts:
- PostgreSQL (local dev mock for AstraDB)
- Redpanda (Kafka-compatible event bus)
- Redis (caching)
- Kong (API gateway)
- Vault (secrets management)
- MinIO (S3-compatible artifact storage)

### 2. Verify Services

```bash
# Check all containers are healthy
docker-compose ps

# Expected output: All services should show "healthy" status
```

### 3. Initialize Database Schema

```bash
# For local dev (PostgreSQL)
psql -h localhost -U maars -d maars -f ../../config/astradb-schema.cql

# For production (AstraDB)
# Upload config/astradb-schema.cql via AstraDB UI or CLI
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

---

## 🛠️ Development Workflow

### The Critical Path (Build in this order)

#### Step 1: The Execution Loop (Week 1-2)
**Goal**: A hardcoded prompt executes a Python script in WASM sandbox

```bash
# Build vessel-sandbox
cd services/vessel-sandbox
cargo build --release

# Build vessel-orchestrator
cd ../vessel-orchestrator
pip install -r requirements.txt
python main.py
```

**Test**: `POST /v1/goals` with a simple Python execution task

#### Step 2: The Intelligence Loop (Week 3-4)
**Goal**: LangGraph decomposes goal and routes to sandbox

```bash
# Build vessel-llm-router
cd services/vessel-llm-router
go build -o bin/llm-router

# Build vessel-swarm
cd ../vessel-swarm
pip install -r requirements.txt
python main.py
```

**Test**: Multi-step task with tool calls

#### Step 3: The State Loop (Week 5-6)
**Goal**: Every action emits Kafka event, persisted in AstraDB

```bash
# Connect to Redpanda/Astra Streaming
# Update KAFKA_BROKERS in .env
```

**Test**: Verify events in Redpanda console

#### Step 4: The Visual Loop (Week 7-8)
**Goal**: Frontend renders live agent state via WebSocket

```bash
cd services/vessel-interface
npm install
npm run dev
```

**Test**: Open http://localhost:3000/app/canvas

---

## 🧪 Testing Strategy

### Golden Path Scenarios

#### Scenario A: Nano-Tier Formatting Task
```bash
curl -X POST http://localhost:8000/v1/goals \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Take this raw CSV text and format it into a Markdown table.",
    "priority": "NORMAL"
  }'
```

**Expected**: Nano-tier model, cost < $0.01, no network access

#### Scenario B: Mid-Tier Research Task
```bash
curl -X POST http://localhost:8000/v1/goals \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Research the latest SEC filings for Apple and summarize their AI strategy.",
    "priority": "HIGH"
  }'
```

**Expected**: LangGraph DAG with web_search + summarization, memory write

#### Scenario C: High-Stakes Escalation
```bash
curl -X POST http://localhost:8000/v1/goals \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Email this drafted contract to vendor@example.com and sign it on my behalf.",
    "priority": "CRITICAL"
  }'
```

**Expected**: Guardrail escalation, Inbox card appears, no execution until approved

---

## 🔒 Security

### WASM Sandbox Policies
- `ISOLATED`: No network, file system access only to `/workspace`
- `RESTRICTED`: Whitelisted domains only
- `OPEN`: Full network (monitored by guardrails)

### Liability Matrix
| Tier | Max Transaction | Max Data Export | Approval Required For |
|------|----------------|-----------------|----------------------|
| Nano | $0 | 100 rows | Any external API call |
| Mid | $50 | 5,000 rows | Transactions > $50 |
| Frontier | $5,000 | Unlimited | Transactions > $5,000, contracts |

---

## 📊 Monitoring

### Local Development
- Kong Admin UI: http://localhost:8002
- Redpanda Console: http://localhost:19644
- MinIO Console: http://localhost:9001
- Vault UI: http://localhost:8200

### Production (Phase 2+)
- Arize Phoenix: AI observability
- Grafana: System metrics
- Loki: Log aggregation

---

## 🤝 Contributing

### Branch Strategy
- `main`: Production-ready code
- `develop`: Integration branch
- `feature/*`: Feature branches
- `hotfix/*`: Emergency fixes

### Commit Convention
```
type(scope): subject

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

---

## 📝 License

Proprietary - All Rights Reserved

---

## 🆘 Support

- **Documentation**: `/docs`
- **Issues**: GitHub Issues
- **Slack**: #maars-dev

---

## 🗺️ Roadmap

- [x] Phase 0: Documentation & Setup (Week 0)
- [ ] Phase 1: Core Execution Loop (Week 1-4)
- [ ] Phase 2: Memory & Identity (Week 5-8)
- [ ] Phase 3: Guardrails & Economics (Week 9-12)
- [ ] Phase 4: Frontend (Week 13-14)
- [ ] Phase 5: Testing & Launch (Week 15-16)

---

**Built with ❤️ by the MAARS Team**