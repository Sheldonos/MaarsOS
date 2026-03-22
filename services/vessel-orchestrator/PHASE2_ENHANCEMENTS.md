# Phase 2 Enhancements: Multi-Task DAG & Right-Sizing Engine

## Overview

The vessel-orchestrator has been enhanced with advanced features for Phase 2:

1. **Multi-Task DAG (Directed Acyclic Graph) Execution**
2. **Right-Sizing Engine for Optimal Resource Allocation**
3. **Parallel Task Execution**
4. **LLM-Router Integration**
5. **Backward Compatibility with Simple Workflow**

## Architecture

### Enhanced State Structure

The `GoalState` now includes:
- **DAG Fields**: `task_graph`, `task_status`, `ready_tasks`, `executing_tasks`, `completed_tasks`, `failed_tasks`
- **Right-Sizing Fields**: `task_sizing` with complexity scores and resource estimates
- **Metrics**: `total_tasks`, `parallel_executions`, `dag_depth`

### Workflow Modes

#### Simple Mode (Backward Compatible)
```
Plan → Execute → Complete
```
- Single task execution
- Sequential processing
- No dependency management
- Maintains Phase 1 behavior

#### DAG Mode (New)
```
Analyze → Decompose → Build DAG → Right-Size → Execute DAG → Aggregate → Complete
```
- Multi-task decomposition
- Dependency resolution
- Parallel execution
- Resource optimization

## Right-Sizing Engine

### Model Tiers

| Tier | Use Case | Max Time | Max Memory | Cost Factor |
|------|----------|----------|------------|-------------|
| NANO | Simple tasks | 5s | 128MB | 0.01x |
| MID | Moderate complexity | 30s | 512MB | 0.05x |
| FRONTIER | Complex tasks | 120s | 2GB | 0.20x |

### Complexity Analysis

The engine analyzes:
- **Code Lines**: Estimated lines of code
- **Logic Depth**: Nested structures, loops, conditionals
- **Data Processing**: Pandas, NumPy, JSON operations
- **API Calls**: Network requests
- **Computation**: Algorithms, sorting, optimization

### Complexity Scoring

Score ranges (0-100):
- **0-25**: SIMPLE → NANO tier
- **25-50**: MODERATE → MID tier
- **50-70**: COMPLEX → MID tier
- **70-100**: VERY_COMPLEX → FRONTIER tier

Priority can boost tier selection:
- HIGH: +10 points
- CRITICAL: +20 points

## DAG Builder

### Features

1. **Dependency Graph Construction**
   - Parses `depends_on` field in tasks
   - Builds adjacency list representation

2. **Cycle Detection**
   - Detects circular dependencies
   - Prevents infinite loops

3. **Topological Sort**
   - Organizes tasks into execution levels
   - Identifies parallel execution opportunities

4. **Ready Task Identification**
   - Finds tasks with satisfied dependencies
   - Enables parallel execution

## Configuration

### Environment Variables

```bash
# DAG Mode
ENABLE_DAG_MODE=true
MAX_PARALLEL_TASKS=5

# Right-Sizing
ENABLE_RIGHT_SIZING=true
DEFAULT_MODEL_TIER=mid

# Resource Limits (per tier)
NANO_MAX_EXECUTION_MS=5000
NANO_MAX_MEMORY_MB=128
MID_MAX_EXECUTION_MS=30000
MID_MAX_MEMORY_MB=512
FRONTIER_MAX_EXECUTION_MS=120000
FRONTIER_MAX_MEMORY_MB=2048

# LLM Router
LLM_ROUTER_URL=http://localhost:8082
```

### API Request

```json
{
  "description": "Complex multi-step goal",
  "priority": "HIGH",
  "use_dag_mode": true,
  "total_budget_usd": 10.0
}
```

## Usage Examples

### Example 1: Simple Goal (Backward Compatible)

```bash
curl -X POST http://localhost:8081/v1/goals \
  -H "Content-Type: application/json" \
  -d '{
    "description": "print(\"Hello, World!\")",
    "priority": "MEDIUM",
    "use_dag_mode": false
  }'
```

**Behavior**: Single task, direct execution, no DAG overhead.

### Example 2: Complex Multi-Task Goal

```bash
curl -X POST http://localhost:8081/v1/goals \
  -H "Content-Type: application/json" \
  -d '{
    "description": "1. Fetch data from API\n2. Process and clean the data\n3. Generate visualization\n4. Save results to file",
    "priority": "HIGH",
    "use_dag_mode": true
  }'
```

**Behavior**:
1. Decomposes into 4 tasks
2. Builds dependency chain: Task1 → Task2 → Task3 → Task4
3. Right-sizes each task based on complexity
4. Executes sequentially (due to dependencies)

### Example 3: Parallel Execution

```json
{
  "description": "Process multiple independent datasets",
  "tasks": [
    {
      "task_id": "task-1",
      "description": "Process dataset A",
      "depends_on": []
    },
    {
      "task_id": "task-2", 
      "description": "Process dataset B",
      "depends_on": []
    },
    {
      "task_id": "task-3",
      "description": "Merge results",
      "depends_on": ["task-1", "task-2"]
    }
  ]
}
```

**Execution**:
- Level 0: task-1 and task-2 execute in parallel
- Level 1: task-3 executes after both complete

## Kafka Events

### New Events

#### goal.analyzing
```json
{
  "event_type": "goal.analyzing",
  "goal_id": "uuid",
  "timestamp": "2026-03-22T06:30:00Z"
}
```

#### goal.decomposing
```json
{
  "event_type": "goal.decomposing",
  "goal_id": "uuid",
  "task_count": 4
}
```

#### task.executing (Enhanced)
```json
{
  "event_type": "task.executing",
  "task_id": "uuid",
  "goal_id": "uuid",
  "model_tier": "mid",
  "complexity_score": 45
}
```

#### goal.completed (Enhanced)
```json
{
  "event_type": "goal.completed",
  "goal_id": "uuid",
  "status": "COMPLETED",
  "use_dag_mode": true,
  "metrics": {
    "total_tasks": 4,
    "completed_tasks": 4,
    "failed_tasks": 0,
    "dag_depth": 2,
    "max_parallel": 2
  }
}
```

## Performance Characteristics

### Simple Mode
- **Latency**: Low (no DAG overhead)
- **Throughput**: Single task at a time
- **Resource Usage**: Minimal
- **Best For**: Quick, simple tasks

### DAG Mode
- **Latency**: Higher initial overhead (analysis, decomposition)
- **Throughput**: Up to MAX_PARALLEL_TASKS concurrent
- **Resource Usage**: Optimized per task
- **Best For**: Complex, multi-step goals

## Monitoring

### Health Check

```bash
curl http://localhost:8081/health
```

Response includes feature flags:
```json
{
  "status": "healthy",
  "version": "0.2.0",
  "features": {
    "dag_mode": true,
    "right_sizing": true,
    "max_parallel_tasks": 5
  }
}
```

### Metrics to Track

1. **DAG Depth**: Average execution levels
2. **Parallel Efficiency**: Tasks executed concurrently
3. **Right-Sizing Accuracy**: Estimated vs actual resources
4. **Task Success Rate**: By complexity tier
5. **Cost Optimization**: Savings from right-sizing

## Future Enhancements

### Phase 3 Roadmap

1. **LLM-Based Decomposition**
   - Replace heuristic decomposition with LLM
   - Use vessel-llm-router for intelligent task breakdown

2. **Agent Spawning**
   - Integrate vessel-swarm for complex tasks
   - Spawn specialized agents per task type

3. **Dynamic Re-Planning**
   - Adjust DAG based on intermediate results
   - Handle task failures with alternative paths

4. **Cost Prediction**
   - Estimate total goal cost before execution
   - Budget-aware task scheduling

5. **Historical Learning**
   - Track actual vs estimated resources
   - Improve right-sizing accuracy over time

## Testing

### Unit Tests

```bash
cd services/vessel-orchestrator
pytest tests/test_right_sizing.py
pytest tests/test_dag_builder.py
pytest tests/test_planner.py
```

### Integration Tests

```bash
# Test simple mode (backward compatibility)
./test-simple-goal.sh

# Test DAG mode
./test-dag-goal.sh

# Test parallel execution
./test-parallel-tasks.sh
```

## Troubleshooting

### Issue: Tasks not executing in parallel

**Check**:
1. Verify `ENABLE_DAG_MODE=true`
2. Ensure tasks have no dependencies
3. Check `MAX_PARALLEL_TASKS` setting
4. Review task status in logs

### Issue: Right-sizing selecting wrong tier

**Check**:
1. Review complexity scoring in logs
2. Adjust complexity weights if needed
3. Verify priority boost settings
4. Check task description clarity

### Issue: Circular dependency detected

**Solution**:
1. Review task dependencies
2. Remove circular references
3. Restructure task graph
4. Use DAG visualization tools

## Migration Guide

### From Phase 1 to Phase 2

1. **No Breaking Changes**: Existing simple goals work as-is
2. **Opt-In DAG Mode**: Set `use_dag_mode: true` in request
3. **Configuration**: Add new env vars to `.env`
4. **Monitoring**: Update dashboards for new metrics

### Rollback Plan

If issues arise:
1. Set `ENABLE_DAG_MODE=false`
2. System reverts to Phase 1 behavior
3. No data loss or compatibility issues

## Support

For questions or issues:
- Review logs: `docker logs vessel-orchestrator`
- Check Kafka events: `maars.goals`, `maars.tasks`
- Consult main README.md
- Review PHASE_1_COMPLETE.md for baseline

---

**Version**: 0.2.0  
**Last Updated**: 2026-03-22  
**Author**: Bob (AI Assistant)