# Vessel Swarm

**Status:** Phase 1 MVP - Specification Complete, Implementation Deferred to Phase 2  
**Priority:** 5 (Week 3-4)

---

## Overview

The Swarm service manages the lifecycle of autonomous agents, including spawning, monitoring, resource allocation, and termination. It acts as the "agent pool manager" for MAARS.

## Phase 1 MVP Decision

**For Phase 1**, agent management is **handled directly by vessel-orchestrator** with a simplified single-agent model. This allows us to:

1. ✅ Prove the core execution loop works
2. ✅ Test task execution without multi-agent complexity
3. ✅ Defer agent lifecycle management to Phase 2
4. ✅ Focus on end-to-end functionality first

**Phase 2** will implement this as a dedicated service for production-scale agent orchestration.

---

## Planned Architecture (Phase 2)

### Features

- **Agent Registry**: AstraDB-backed agent metadata storage
- **Lifecycle Management**: Spawn, monitor, pause, resume, terminate
- **Resource Allocation**: CPU, memory, and cost budgets per agent
- **Pool Pre-warming**: Keep idle agents ready for fast task assignment
- **Health Monitoring**: Detect and recover from agent failures
- **Capability Matching**: Route tasks to agents with required skills
- **Hierarchical Agents**: Master agents can spawn sub-agents

### Agent States

```
IDLE → ASSIGNED → EXECUTING → COMPLETED
  ↓       ↓          ↓           ↓
PAUSED  FAILED    TIMEOUT    TERMINATED
```

### Agent Types

| Type | Purpose | Lifespan | Cost |
|------|---------|----------|------|
| **Ephemeral** | Single task | Task duration | Low |
| **Persistent** | Multiple tasks | Session duration | Medium |
| **Specialized** | Domain expert | Long-lived | High |

---

## Phase 1 Workaround

### Current Implementation

The vessel-orchestrator creates a "virtual agent" for each task:

```python
# services/vessel-orchestrator/app/planner.py

class GoalPlanner:
    async def _execute_task(self, state: GoalState) -> GoalState:
        task = state["tasks"][state["current_task_index"]]
        
        # Virtual agent (no actual agent spawning)
        virtual_agent = {
            "agent_id": str(uuid.uuid4()),
            "task_id": task["task_id"],
            "status": "EXECUTING",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Execute directly in sandbox
        result = await self.sandbox_client.execute_code(...)
        
        return state
```

This is sufficient for Phase 1 because:
- ✅ Single-task execution works
- ✅ No agent pooling needed yet
- ✅ No multi-agent coordination required
- ✅ Simpler debugging and testing

---

## Phase 2 Implementation Plan

### Database Schema (AstraDB)

```sql
-- Agent Registry
CREATE TABLE agents (
    tenant_id UUID,
    agent_id UUID,
    name TEXT,
    agent_type TEXT,  -- EPHEMERAL, PERSISTENT, SPECIALIZED
    capabilities LIST<TEXT>,
    model_tier TEXT,  -- NANO, MID, FRONTIER
    status TEXT,      -- IDLE, ASSIGNED, EXECUTING, etc.
    current_task_id UUID,
    budget_ceiling_usd DECIMAL,
    spent_usd DECIMAL,
    created_at TIMESTAMP,
    last_active_at TIMESTAMP,
    PRIMARY KEY (tenant_id, agent_id)
);

-- Agent Pool
CREATE TABLE agent_pool (
    tenant_id UUID,
    pool_id UUID,
    agent_type TEXT,
    min_size INT,
    max_size INT,
    current_size INT,
    warm_agents LIST<UUID>,
    PRIMARY KEY (tenant_id, pool_id)
);

-- Agent Metrics
CREATE TABLE agent_metrics (
    tenant_id UUID,
    agent_id UUID,
    metric_timestamp TIMESTAMP,
    tasks_completed INT,
    avg_execution_time_ms BIGINT,
    total_cost_usd DECIMAL,
    error_count INT,
    PRIMARY KEY ((tenant_id, agent_id), metric_timestamp)
) WITH CLUSTERING ORDER BY (metric_timestamp DESC);
```

### API Endpoints

```python
# FastAPI routes

@app.post("/v1/agents")
async def spawn_agent(request: SpawnAgentRequest):
    """Spawn a new agent"""
    pass

@app.get("/v1/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent status"""
    pass

@app.post("/v1/agents/{agent_id}/assign")
async def assign_task(agent_id: str, task: TaskDefinition):
    """Assign task to agent"""
    pass

@app.post("/v1/agents/{agent_id}/terminate")
async def terminate_agent(agent_id: str):
    """Terminate agent"""
    pass

@app.get("/v1/pools/{pool_id}")
async def get_pool_status(pool_id: str):
    """Get agent pool status"""
    pass
```

### Agent Lifecycle Manager

```python
class AgentLifecycleManager:
    def __init__(self, db_client, kafka_producer):
        self.db = db_client
        self.kafka = kafka_producer
        self.active_agents = {}
    
    async def spawn_agent(
        self,
        tenant_id: str,
        agent_type: str,
        capabilities: List[str],
        model_tier: str
    ) -> Agent:
        """Spawn a new agent"""
        agent_id = str(uuid.uuid4())
        
        agent = Agent(
            agent_id=agent_id,
            tenant_id=tenant_id,
            agent_type=agent_type,
            capabilities=capabilities,
            model_tier=model_tier,
            status="IDLE"
        )
        
        # Store in database
        await self.db.insert_agent(agent)
        
        # Publish event
        await self.kafka.send_event(
            topic="maars.agents",
            event_type="agent.spawned",
            payload=agent.to_dict()
        )
        
        self.active_agents[agent_id] = agent
        return agent
    
    async def assign_task(self, agent_id: str, task: Task):
        """Assign task to agent"""
        agent = self.active_agents.get(agent_id)
        if not agent:
            raise AgentNotFoundError(agent_id)
        
        if agent.status != "IDLE":
            raise AgentBusyError(agent_id)
        
        agent.status = "ASSIGNED"
        agent.current_task_id = task.task_id
        
        await self.db.update_agent(agent)
        await self.kafka.send_event(
            topic="maars.agents",
            event_type="agent.assigned",
            payload={"agent_id": agent_id, "task_id": task.task_id}
        )
    
    async def monitor_agents(self):
        """Background task to monitor agent health"""
        while True:
            for agent_id, agent in self.active_agents.items():
                # Check if agent is stuck
                if agent.is_stuck():
                    await self.recover_agent(agent_id)
                
                # Check if agent exceeded budget
                if agent.spent_usd > agent.budget_ceiling_usd:
                    await self.terminate_agent(agent_id, reason="budget_exceeded")
            
            await asyncio.sleep(10)
```

### Pool Pre-warming

```python
class AgentPoolManager:
    def __init__(self, lifecycle_manager):
        self.lifecycle = lifecycle_manager
        self.pools = {}
    
    async def create_pool(
        self,
        tenant_id: str,
        agent_type: str,
        min_size: int = 2,
        max_size: int = 10
    ):
        """Create an agent pool with pre-warmed agents"""
        pool_id = str(uuid.uuid4())
        
        # Spawn minimum number of agents
        warm_agents = []
        for _ in range(min_size):
            agent = await self.lifecycle.spawn_agent(
                tenant_id=tenant_id,
                agent_type=agent_type,
                capabilities=["general"],
                model_tier="MID"
            )
            warm_agents.append(agent.agent_id)
        
        pool = AgentPool(
            pool_id=pool_id,
            tenant_id=tenant_id,
            agent_type=agent_type,
            min_size=min_size,
            max_size=max_size,
            warm_agents=warm_agents
        )
        
        self.pools[pool_id] = pool
        return pool
    
    async def get_available_agent(self, pool_id: str) -> Optional[Agent]:
        """Get an available agent from the pool"""
        pool = self.pools.get(pool_id)
        if not pool:
            return None
        
        # Find idle agent
        for agent_id in pool.warm_agents:
            agent = self.lifecycle.active_agents.get(agent_id)
            if agent and agent.status == "IDLE":
                return agent
        
        # Spawn new agent if pool not at max
        if len(pool.warm_agents) < pool.max_size:
            agent = await self.lifecycle.spawn_agent(
                tenant_id=pool.tenant_id,
                agent_type=pool.agent_type,
                capabilities=["general"],
                model_tier="MID"
            )
            pool.warm_agents.append(agent.agent_id)
            return agent
        
        return None
```

---

## Capability Matching

```python
def match_agent_to_task(task: Task, available_agents: List[Agent]) -> Optional[Agent]:
    """Find best agent for task based on capabilities"""
    required_capabilities = set(task.required_capabilities)
    
    # Filter agents with required capabilities
    capable_agents = [
        agent for agent in available_agents
        if required_capabilities.issubset(set(agent.capabilities))
    ]
    
    if not capable_agents:
        return None
    
    # Sort by cost (prefer cheaper agents)
    capable_agents.sort(key=lambda a: MODEL_TIER_COSTS[a.model_tier])
    
    return capable_agents[0]
```

---

## Hierarchical Agents

```python
class MasterAgent:
    def __init__(self, agent_id: str, swarm_client):
        self.agent_id = agent_id
        self.swarm = swarm_client
        self.sub_agents = []
    
    async def spawn_sub_agent(self, capabilities: List[str], model_tier: str):
        """Master agent spawns a sub-agent"""
        sub_agent = await self.swarm.spawn_agent(
            tenant_id=self.tenant_id,
            agent_type="EPHEMERAL",
            capabilities=capabilities,
            model_tier=model_tier,
            parent_agent_id=self.agent_id  # Track hierarchy
        )
        
        self.sub_agents.append(sub_agent.agent_id)
        return sub_agent
    
    async def coordinate_sub_agents(self, tasks: List[Task]):
        """Distribute tasks among sub-agents"""
        results = []
        
        for task in tasks:
            # Spawn specialized sub-agent for each task
            sub_agent = await self.spawn_sub_agent(
                capabilities=task.required_capabilities,
                model_tier=task.model_tier
            )
            
            # Assign task
            await self.swarm.assign_task(sub_agent.agent_id, task)
            
            # Wait for completion (simplified)
            result = await self.wait_for_completion(sub_agent.agent_id)
            results.append(result)
            
            # Terminate sub-agent
            await self.swarm.terminate_agent(sub_agent.agent_id)
        
        return results
```

---

## Monitoring & Metrics

### Prometheus Metrics

```
swarm_agents_total{tenant_id, agent_type, status}
swarm_pool_size{pool_id, agent_type}
swarm_agent_spawn_duration_seconds
swarm_agent_lifetime_seconds
swarm_tasks_per_agent
swarm_cost_per_agent_usd
swarm_agent_errors_total{agent_id, error_type}
```

### Health Checks

```python
async def check_agent_health(agent: Agent) -> bool:
    """Check if agent is healthy"""
    # Check last activity
    if (datetime.utcnow() - agent.last_active_at).seconds > 300:
        return False
    
    # Check if stuck on task
    if agent.status == "EXECUTING":
        task_duration = (datetime.utcnow() - agent.task_started_at).seconds
        if task_duration > agent.max_execution_time:
            return False
    
    # Check budget
    if agent.spent_usd > agent.budget_ceiling_usd:
        return False
    
    return True
```

---

## Phase 1 vs Phase 2 Comparison

| Feature | Phase 1 (Current) | Phase 2 (Planned) |
|---------|-------------------|-------------------|
| Agent Model | Virtual (no actual agents) | Real agent instances |
| Lifecycle | Task-scoped | Configurable lifespan |
| Pooling | None | Pre-warmed pools |
| Capabilities | Implicit | Explicit matching |
| Hierarchy | None | Master/sub-agent support |
| Monitoring | Basic logging | Comprehensive metrics |
| Recovery | None | Automatic failover |

---

## Integration with Other Services

### vessel-orchestrator
- Requests agents for tasks
- Receives agent status updates
- Coordinates multi-agent workflows

### vessel-llm-router
- Agents use LLM router for completions
- Router tracks per-agent costs

### vessel-memory
- Agents store/retrieve memories
- Shared memory for agent collaboration

### vessel-observability
- Tracks agent metrics
- Monitors agent health
- Alerts on anomalies

---

## Cost Optimization

1. **Agent Reuse**: Keep agents alive for multiple tasks
2. **Right-Sizing**: Match agent tier to task complexity
3. **Pool Management**: Terminate idle agents after timeout
4. **Budget Enforcement**: Hard stop at budget ceiling
5. **Capability Matching**: Use cheapest capable agent

---

## Security Considerations

1. **Agent Isolation**: Each agent has isolated workspace
2. **Budget Limits**: Prevent runaway costs
3. **Capability Restrictions**: Agents can only use allowed tools
4. **Audit Trail**: Log all agent actions
5. **Termination**: Force-kill agents on security violations

---

## Conclusion

While vessel-swarm is essential for production-scale multi-agent orchestration, **Phase 1 successfully demonstrates the MAARS architecture** with a simplified single-agent model in vessel-orchestrator.

The current approach is sufficient for:

✅ Proving task execution works  
✅ Testing the core execution loop  
✅ Validating the overall architecture  
✅ Gathering requirements for Phase 2  

**Phase 2 will implement this service for production-grade agent management, pooling, and coordination.**

---

**Status:** Specification Complete, Implementation Deferred  
**Next Steps:** Complete Phase 1 testing, then implement in Phase 2