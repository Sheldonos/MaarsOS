# vessel-memory

Long-term memory service with vector search and knowledge graphs for the MAARS platform.

## Overview

The vessel-memory service provides persistent memory capabilities for AI agents, combining:
- **Vector Store (Qdrant)**: Semantic memory search using embeddings
- **Knowledge Graph (Neo4j)**: Relationship-based memory with GraphRAG
- **Memory Types**: Episodic, Semantic, and Procedural memory
- **Provenance Tracking**: Cryptographic verification of memory sources

## Features

### Memory Management
- Create, search, and delete memory nodes
- Three memory types with configurable TTL
- Importance scoring for memory prioritization
- Privacy controls and tenant isolation

### Vector Search
- Semantic similarity search using embeddings
- OpenAI or local embedding models
- Configurable score thresholds
- Fast retrieval (<100ms target)

### Knowledge Graph
- Entity and relationship management
- Graph traversal for context discovery
- GraphRAG combining vector + graph search
- Configurable depth and node limits

### Context Retrieval
- Unified context window for agents
- Multi-type memory aggregation
- Graph-enhanced context
- Token budget management

## API Endpoints

### Memory Operations
- `POST /v1/memory` - Create memory node
- `POST /v1/memory/search` - Search memories
- `DELETE /v1/memory/{tenant_id}/{node_id}` - Delete memory

### Knowledge Graph
- `POST /v1/graph/nodes` - Create graph node
- `POST /v1/graph/edges` - Create graph edge
- `POST /v1/graphrag` - GraphRAG query

### Context
- `POST /v1/context` - Retrieve context window

### System
- `GET /health` - Health check
- `GET /ready` - Readiness check
- `GET /v1/metrics` - Service metrics

## Configuration

### Environment Variables

```bash
# Service
PORT=8084
LOG_LEVEL=INFO

# Qdrant Vector Store
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=

# Neo4j Knowledge Graph
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Embeddings
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=

# Memory TTL
MEMORY_TTL_EPISODIC_DAYS=90
MEMORY_TTL_SEMANTIC_DAYS=365
MEMORY_TTL_PROCEDURAL_DAYS=180

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

## Development

### Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
python main.py
```

### Docker

```bash
# Build image
docker build -t vessel-memory:latest .

# Run container
docker run -p 8084:8084 \
  -e QDRANT_HOST=qdrant \
  -e NEO4J_URI=bolt://neo4j:7687 \
  -e OPENAI_API_KEY=your-key \
  vessel-memory:latest
```

## Architecture

### Memory Types

1. **Episodic Memory**: Specific events and interactions
   - "On March 15, user asked about project status"
   - TTL: 90 days (configurable)

2. **Semantic Memory**: General facts and knowledge
   - "User prefers meetings at 10am"
   - TTL: 365 days (configurable)

3. **Procedural Memory**: Task execution patterns
   - "To book a flight, first check calendar"
   - TTL: 180 days (configurable)

### GraphRAG Flow

1. Vector search finds relevant memories
2. Graph traversal discovers connected entities
3. Relationship analysis enriches context
4. Combined results returned with relevance scores

## Performance Targets

- Vector search: <100ms
- GraphRAG query: <500ms
- Memory creation: <50ms
- Context retrieval: <200ms

## Integration

### With vessel-orchestrator
```python
# Retrieve context for task planning
context = await memory_client.retrieve_context(
    tenant_id=tenant_id,
    agent_id=agent_id,
    query="What do I know about this project?"
)
```

### With vessel-swarm
```python
# Store agent execution results
await memory_client.create_memory(
    tenant_id=tenant_id,
    agent_id=agent_id,
    content="Successfully completed data analysis task",
    memory_type="procedural"
)
```

## Monitoring

### Kafka Events
- `memory.created` - New memory node created
- `memory.updated` - Memory node updated
- `memory.deleted` - Memory node deleted
- `memory.retrieved` - Memory search performed
- `graph.updated` - Graph structure changed

### Metrics
- Total memory nodes
- Total graph nodes/edges
- Average search time
- Cache hit rate
- Storage size

## Security

- Tenant isolation via separate Qdrant collections
- Privacy controls for sensitive memories
- Provenance hashing for integrity
- Encrypted storage of sensitive data

## Made with Bob