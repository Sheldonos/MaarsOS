> **Phase 2 Enhancements**: This service now includes multi-task DAG execution and Right-Sizing Engine. See [PHASE2_ENHANCEMENTS.md](./PHASE2_ENHANCEMENTS.md) for detailed documentation.

# Vessel Orchestrator

Master orchestration service for MAARS. Handles goal submission, task planning with LangGraph, and execution coordination.

## Features

- **Goal Management**: REST API for submitting and tracking goals
- **LangGraph Planning**: Task decomposition using LangGraph workflows
- **Sandbox Integration**: Coordinates code execution via vessel-sandbox
- **Event Streaming**: Publishes all events to Kafka for observability
- **Async Processing**: Non-blocking goal processing with asyncio

## API Endpoints

### POST /v1/goals

Submit a new goal for execution.

**Request:**
```json
{
  "description": "print('Hello MAARS')",
  "priority": "NORMAL",
  "total_budget_usd": 10.0,
  "tenant_id": "tenant-123"
}
```

**Response:**
```json
{
  "goal_id": "uuid-v4",
  "tenant_id": "tenant-123",
  "description": "print('Hello MAARS')",
  "priority": "NORMAL",
  "status": "PENDING",
  "total_budget_usd": 10.0,
  "created_at": "2026-03-22T05:00:00Z"
}
```

### GET /v1/goals/{goal_id}

Get goal status (Phase 2).

### POST /v1/goals/{goal_id}/cancel

Cancel a running goal.

### GET /health

Health check endpoint.

## Architecture

```
┌─────────────────────────────────────────┐
│    vessel-orchestrator (Python)         │
├─────────────────────────────────────────┤
│  ┌───────────────────────────────────┐  │
│  │      FastAPI REST API             │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │    LangGraph Goal Planner         │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │  Plan → Execute → Complete  │  │  │
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │    Sandbox Client (HTTP)          │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │    Kafka Producer (Events)        │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## Event Schema

All events published to Kafka follow this structure:

```json
{
  "event": "goal.created",
  "timestamp": "2026-03-22T05:00:00Z",
  "payload": {
    "goal_id": "uuid-v4",
    "tenant_id": "tenant-123",
    ...
  }
}
```

### Event Types

**Goals:**
- `goal.created` - New goal submitted
- `goal.planning` - Planning started
- `goal.executing` - Execution started
- `goal.completed` - Goal completed successfully
- `goal.failed` - Goal failed
- `goal.cancelled` - Goal cancelled by user

**Tasks:**
- `task.executing` - Task execution started
- `task.completed` - Task completed successfully
- `task.failed` - Task failed

## Environment Variables

```bash
# Service
SERVICE_NAME=vessel-orchestrator
SERVICE_VERSION=0.1.0
HOST=0.0.0.0
PORT=8081

# Kafka
KAFKA_BROKERS=localhost:19092
KAFKA_TOPIC_GOALS=maars.goals
KAFKA_TOPIC_TASKS=maars.tasks
KAFKA_TOPIC_EVENTS=maars.events

# Sandbox
SANDBOX_URL=http://localhost:8085

# LLM Router (Phase 2)
LLM_ROUTER_URL=http://localhost:8082

# Database (Phase 2)
ASTRA_DB_ID=
ASTRA_DB_REGION=us-east1
ASTRA_DB_KEYSPACE=maars
ASTRA_DB_TOKEN=

# Redis (Phase 2)
REDIS_URL=redis://localhost:6379

# Logging
LOG_LEVEL=INFO
```

## Development

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Locally

```bash
python main.py
```

### Run with Docker

```bash
docker build -t vessel-orchestrator .
docker run -p 8081:8081 vessel-orchestrator
```

### Test

```bash
pytest tests/
```

## LangGraph Workflow

The goal planner uses LangGraph to orchestrate task execution:

```python
plan_tasks → execute_task → complete_goal
              ↑           ↓
              └───────────┘
              (loop until done)
```

### Phase 1 MVP Workflow

1. **Plan**: Create a single task from the goal description
2. **Execute**: Send task to vessel-sandbox for execution
3. **Complete**: Publish completion event with results

### Phase 2+ Enhancements

- [ ] LLM-based task decomposition
- [ ] Multi-task DAG execution
- [ ] Dependency resolution
- [ ] Right-Sizing Engine integration
- [ ] Agent spawning via vessel-swarm
- [ ] Memory integration for context

## Integration Points

- **vessel-sandbox**: Code execution (HTTP)
- **vessel-llm-router**: LLM routing (gRPC, Phase 2)
- **vessel-swarm**: Agent management (HTTP, Phase 2)
- **Kafka**: Event streaming
- **AstraDB**: State persistence (Phase 2)
- **Redis**: Caching (Phase 2)

## Phase 1 Limitations

- Single-task execution only (no DAG)
- No LLM-based decomposition
- No database persistence
- Simple code extraction (no generation)
- No agent spawning

These will be addressed in Phase 2+.