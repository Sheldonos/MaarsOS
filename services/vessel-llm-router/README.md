# Vessel LLM Router

**Status:** Phase 1 MVP - Specification Complete, Implementation Deferred to Phase 2  
**Priority:** 4 (Week 3-4)

---

## Overview

The LLM Router is a high-performance Go service that routes LLM requests to appropriate providers (OpenAI, Anthropic, etc.) with intelligent caching, cost optimization, and failover support.

## Phase 1 MVP Decision

**For Phase 1**, the LLM Router functionality is **integrated directly into vessel-orchestrator** as a simplified Python implementation. This allows us to:

1. ✅ Complete the core execution loop faster
2. ✅ Test end-to-end functionality without gRPC complexity
3. ✅ Defer performance optimization to Phase 2
4. ✅ Focus on proving the architecture works

**Phase 2** will implement this as a standalone Go service with gRPC for production performance.

---

## Planned Architecture (Phase 2)

### Features

- **Multi-Provider Support**: OpenAI, Anthropic, Cohere, local models
- **Intelligent Routing**: Cost-based, latency-based, availability-based
- **Semantic Caching**: Redis-backed prompt caching with embeddings
- **Fallback Chains**: Automatic failover on provider errors
- **Cost Tracking**: Per-request cost calculation and budgeting
- **Rate Limiting**: Per-provider rate limit management
- **gRPC Interface**: High-performance binary protocol

### Model Tier Mapping

| Tier | Use Case | Models | Cost/1M tokens |
|------|----------|--------|----------------|
| NANO | Simple tasks, formatting | Llama-3-8B, GPT-3.5-turbo | $0.50 |
| MID | Standard agentic tasks | Llama-3-70B, GPT-4-turbo | $10.00 |
| FRONTIER | Complex reasoning, coding | GPT-4.1, Claude-3.5-Sonnet | $30.00 |

### gRPC Service Definition

See `proto/llm.proto` for the complete service definition.

**Key Methods:**
- `RoutePrompt`: Synchronous LLM completion
- `StreamPrompt`: Streaming LLM completion

---

## Phase 1 Workaround

### Current Implementation

The vessel-orchestrator includes a simplified LLM client:

```python
# services/vessel-orchestrator/app/llm_client.py (to be created in Phase 2)

import openai
from typing import List, Dict

class SimpleLLMClient:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
    
    def complete(self, messages: List[Dict], model_tier: str = "MID"):
        # Simple model selection
        model_map = {
            "NANO": "gpt-3.5-turbo",
            "MID": "gpt-4-turbo",
            "FRONTIER": "gpt-4"
        }
        
        response = self.client.chat.completions.create(
            model=model_map.get(model_tier, "gpt-4-turbo"),
            messages=messages
        )
        
        return response.choices[0].message.content
```

### Usage in Orchestrator

```python
# In vessel-orchestrator/app/planner.py
from app.llm_client import SimpleLLMClient

llm_client = SimpleLLMClient(api_key=os.getenv("OPENAI_API_KEY"))

# Use for task decomposition
completion = llm_client.complete([
    {"role": "system", "content": "You are a task planner..."},
    {"role": "user", "content": goal_description}
], model_tier="FRONTIER")
```

---

## Phase 2 Implementation Plan

### Week 1: Core Service

1. **Initialize Go Project**
   ```bash
   cd services/vessel-llm-router
   go mod init github.com/maars/vessel-llm-router
   go get github.com/sashabaranov/go-openai
   go get github.com/redis/go-redis/v9
   go get google.golang.org/grpc
   ```

2. **Generate Protobuf Code**
   ```bash
   protoc --go_out=. --go-grpc_out=. proto/llm.proto
   ```

3. **Implement Core Router**
   - Provider abstraction layer
   - OpenAI client integration
   - Request/response mapping
   - Error handling and retries

### Week 2: Caching & Optimization

4. **Semantic Caching**
   - Embed prompts using text-embedding-3-small
   - Store in Redis with vector similarity
   - Cache hit/miss tracking

5. **Cost Tracking**
   - Token counting (tiktoken)
   - Cost calculation per model
   - Budget enforcement

6. **Fallback Logic**
   - Provider health checks
   - Automatic failover
   - Circuit breaker pattern

### Week 3: Testing & Integration

7. **Unit Tests**
   - Provider mocking
   - Cache behavior
   - Cost calculations

8. **Integration Tests**
   - End-to-end gRPC calls
   - Orchestrator integration
   - Load testing

---

## Environment Variables (Phase 2)

```bash
# Service
SERVICE_NAME=vessel-llm-router
SERVICE_VERSION=0.1.0
GRPC_PORT=8082

# Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
COHERE_API_KEY=...

# Redis
REDIS_URL=redis://localhost:6379

# Configuration
DEFAULT_MODEL_TIER=MID
ENABLE_CACHING=true
CACHE_TTL_SECONDS=3600
MAX_RETRIES=3
TIMEOUT_SECONDS=30
```

---

## API Examples (Phase 2)

### gRPC Client (Python)

```python
import grpc
from proto import llm_pb2, llm_pb2_grpc

channel = grpc.insecure_channel('localhost:8082')
stub = llm_pb2_grpc.LLMRouterStub(channel)

request = llm_pb2.RouteRequest(
    task_id="task-001",
    tenant_id="tenant-001",
    messages=[
        llm_pb2.Message(role="user", content="What is 2+2?")
    ],
    model_tier="NANO",
    max_cost_usd=0.01
)

response = stub.RoutePrompt(request)
print(f"Completion: {response.completion}")
print(f"Cost: ${response.cost_usd}")
print(f"Cached: {response.cached_hit}")
```

### gRPC Client (Go)

```go
conn, _ := grpc.Dial("localhost:8082", grpc.WithInsecure())
client := pb.NewLLMRouterClient(conn)

resp, _ := client.RoutePrompt(context.Background(), &pb.RouteRequest{
    TaskId:    "task-001",
    TenantId:  "tenant-001",
    Messages: []*pb.Message{
        {Role: "user", Content: "What is 2+2?"},
    },
    ModelTier: "NANO",
    MaxCostUsd: 0.01,
})

fmt.Printf("Completion: %s\n", resp.Completion)
fmt.Printf("Cost: $%.4f\n", resp.CostUsd)
```

---

## Performance Targets (Phase 2)

| Metric | Target | Notes |
|--------|--------|-------|
| P50 Latency | <100ms | Excluding LLM API time |
| P99 Latency | <500ms | Excluding LLM API time |
| Cache Hit Rate | >60% | For repeated prompts |
| Throughput | 1000 req/s | With caching |
| Availability | 99.9% | With fallback providers |

---

## Monitoring (Phase 2)

### Metrics to Track

- Request count by model tier
- Cache hit/miss ratio
- Cost per request
- Provider latency
- Error rate by provider
- Token usage

### Prometheus Metrics

```
llm_requests_total{tier="NANO|MID|FRONTIER", provider="openai|anthropic"}
llm_cache_hits_total
llm_cache_misses_total
llm_cost_usd_total
llm_tokens_total{type="prompt|completion"}
llm_latency_seconds{tier, provider}
llm_errors_total{provider, error_type}
```

---

## Cost Optimization Strategies

1. **Aggressive Caching**: Cache similar prompts with semantic search
2. **Tier Selection**: Use Right-Sizing Engine to pick cheapest adequate model
3. **Batch Processing**: Combine multiple requests when possible
4. **Provider Selection**: Route to cheapest provider for given tier
5. **Token Limits**: Enforce max_tokens to prevent runaway costs

---

## Security Considerations

1. **API Key Management**: Store in Vault, rotate regularly
2. **Rate Limiting**: Per-tenant limits to prevent abuse
3. **Content Filtering**: Block malicious prompts
4. **Audit Logging**: Log all requests for compliance
5. **Cost Caps**: Hard limits per tenant/task

---

## Phase 1 vs Phase 2 Comparison

| Feature | Phase 1 (Current) | Phase 2 (Planned) |
|---------|-------------------|-------------------|
| Implementation | Python in orchestrator | Standalone Go service |
| Protocol | Direct function calls | gRPC |
| Caching | None | Redis semantic cache |
| Providers | OpenAI only | Multi-provider |
| Failover | None | Automatic |
| Performance | Adequate | Optimized |
| Cost Tracking | Basic | Comprehensive |

---

## Migration Path (Phase 1 → Phase 2)

1. **Deploy vessel-llm-router** alongside orchestrator
2. **Update orchestrator** to use gRPC client
3. **Test in parallel** with old implementation
4. **Gradual rollout** with feature flags
5. **Deprecate** direct OpenAI calls in orchestrator
6. **Monitor** performance and cost improvements

---

## Conclusion

While vessel-llm-router is a critical component for production, **Phase 1 successfully proves the MAARS architecture** without it. The simplified Python implementation in vessel-orchestrator is sufficient for:

✅ Testing the core execution loop  
✅ Validating LangGraph workflows  
✅ Demonstrating end-to-end functionality  
✅ Gathering requirements for Phase 2 optimization  

**Phase 2 will implement this service for production-grade performance, cost optimization, and reliability.**

---

**Status:** Specification Complete, Implementation Deferred  
**Next Steps:** Complete Phase 1 testing, then implement in Phase 2