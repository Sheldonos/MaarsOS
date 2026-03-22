# MAARS Phase 8: Agency Agents & Simulation Integration

**Status:** Planning Complete - Implementation Ready  
**Target Release:** Q2 2026  
**Primary Use Case:** Cinematic World-Building & Long-Running Agent Swarms

---

## Executive Summary

Phase 8 introduces two critical architectural enhancements to MAARS:

1. **Agency Agents Pattern** - Structured persona-based swarm orchestration with directional communication flows
2. **Digital Twin Simulation** - Long-running agent harnesses and Agent-Based Modeling (ABM) for predictive backtesting

These enhancements enable MAARS to maintain persistent world states across months-long production cycles, making it ideal for complex media production, interactive storytelling, and enterprise-scale agent deployments.

---

## 1. The Cinematic World-Building Use Case

### Problem Statement
When developing complex media properties (films, games, interactive worlds), maintaining stylistic and narrative consistency over months or years is extremely difficult. Traditional production pipelines lose context, style guides become outdated, and creative continuity breaks down.

### MAARS Solution
By integrating Agency Agents and robust simulation layers, MAARS acts as a **Digital Showrunner**:

- **Persistent World State**: GraphRAG-based storage of character bibles, architectural styles, color grading rules, narrative timelines
- **Specialized Personas**: Director Agent, Cinematography Agent, Continuity Agent, Art Direction Agent
- **Long-Running Harness**: When creators return after months, the system perfectly re-establishes context
- **Style Consistency**: Art Direction Agent ensures new assets match established aesthetics

### Example Workflow
```
Day 1: Creator defines cinematic universe parameters
  → MAARS spawns specialized agent swarm
  → Agents generate initial assets (scenes, characters, style guides)
  → World state saved to vessel-memory GraphRAG

Day 180: Creator returns to project
  → Initializer Agent reads world-state.json + git history
  → Swarm resumes with perfect contextual fidelity
  → New assets automatically match 6-month-old style guidelines
```

---

## 2. Agency Agents Integration (`vessel-swarm`)

### 2.1 Core Concepts from Agency Swarm

**Declarative Personas**
- Move from generic system prompts to structured Markdown-based personas
- Each agent has: `instructions.md`, `tools.py`, `manifesto.md`
- Personas define personality, capabilities, and communication style

**Directional Communication Flows**
- Replace chaotic any-to-any communication with strict topologies
- Example: `Director > Art_Director` (but not reverse)
- Enforced at the LangGraph orchestration layer

**Pydantic Tool Boundaries**
- Type-safe tool definitions for inter-agent communication
- Prevents unauthorized tool access
- Enables capability-based routing

### 2.2 Implementation in vessel-swarm

#### Persona Registry Enhancement
```python
# services/vessel-swarm/app/persona_manager.py

class PersonaManager:
    """Manages Agency-style declarative personas"""
    
    async def upload_persona_package(
        self,
        tenant_id: str,
        persona_zip: bytes,
    ) -> AgentPersona:
        """
        Upload .zip containing:
        - instructions.md (system prompt)
        - tools.py (allowed tools)
        - manifesto.md (shared context)
        - config.yaml (metadata)
        """
        
    async def instantiate_persona(
        self,
        persona_id: str,
        agent_id: str,
    ) -> Agent:
        """Create agent instance from persona template"""
```

#### Communication Flow Enforcement
```python
# services/vessel-swarm/app/models.py

class CommunicationFlow(BaseModel):
    """Defines allowed agent-to-agent communication"""
    source_agent_role: str
    target_agent_role: str
    allowed_message_types: List[str]
    bidirectional: bool = False

class AgencyManifesto(BaseModel):
    """Shared context for all agents in a swarm"""
    agency_name: str
    mission_statement: str
    shared_instructions: str
    communication_flows: List[CommunicationFlow]
    world_state_schema: Dict[str, Any]
```

### 2.3 Database Schema Updates

```sql
-- Agency Personas
CREATE TABLE agent_personas (
    persona_id UUID PRIMARY KEY,
    tenant_id UUID,
    name TEXT,
    vibe TEXT,
    emoji TEXT,
    color_hex TEXT,
    instructions_md TEXT,
    tools_definition JSONB,
    manifesto_md TEXT,
    created_at TIMESTAMP,
    version INT
);

-- Communication Flows
CREATE TABLE communication_flows (
    flow_id UUID PRIMARY KEY,
    agency_id UUID,
    source_role TEXT,
    target_role TEXT,
    allowed_message_types TEXT[],
    bidirectional BOOLEAN,
    created_at TIMESTAMP
);

-- Agency Manifesto
CREATE TABLE agency_manifestos (
    agency_id UUID PRIMARY KEY,
    tenant_id UUID,
    agency_name TEXT,
    mission_statement TEXT,
    shared_instructions TEXT,
    world_state_schema JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## 3. Long-Running Harness (`vessel-simulation`)

### 3.1 The Initializer Agent Pattern

Inspired by Anthropic's research on effective harnesses for long-running agents, MAARS implements a two-stage execution model:

**Stage 1: Initialization**
```python
# services/vessel-simulation/app/initializer.py

class InitializerAgent:
    """Reconstructs context for long-running tasks"""
    
    async def initialize_session(
        self,
        project_id: str,
        last_checkpoint: datetime,
    ) -> SessionContext:
        """
        1. Read GraphRAG memory for project
        2. Parse git history since last checkpoint
        3. Generate maars-progress.json state file
        4. Establish exact project state
        """
        
        # Query vessel-memory for project context
        context = await self.memory_client.get_project_context(
            project_id=project_id,
            since=last_checkpoint,
        )
        
        # Parse git history
        git_state = await self.parse_git_history(
            repo_path=context.repo_path,
            since=last_checkpoint,
        )
        
        # Generate state file
        progress = ProgressState(
            project_id=project_id,
            last_checkpoint=last_checkpoint,
            current_phase=git_state.current_phase,
            completed_tasks=git_state.completed_tasks,
            pending_tasks=context.pending_tasks,
            world_state=context.world_state,
            style_guidelines=context.style_guidelines,
        )
        
        await self.save_progress_state(progress)
        return SessionContext(progress=progress, context=context)
```

**Stage 2: Execution**
```python
# services/vessel-simulation/app/executor.py

class ExecutionAgent:
    """Executes tasks with state persistence"""
    
    async def execute_with_checkpointing(
        self,
        task: Task,
        session: SessionContext,
    ) -> TaskResult:
        """
        1. Read maars-progress.json
        2. Execute task incrementally
        3. Commit progress before context window expires
        4. Update state file
        """
        
        progress = await self.load_progress_state(session.project_id)
        
        # Execute with periodic checkpointing
        result = await self.execute_task(
            task=task,
            context=session,
            checkpoint_callback=self.checkpoint_progress,
        )
        
        # Update progress state
        progress.completed_tasks.append(task.task_id)
        progress.last_checkpoint = datetime.utcnow()
        await self.save_progress_state(progress)
        
        return result
```

### 3.2 Progress State Schema

```python
# services/vessel-simulation/app/models.py

class ProgressState(BaseModel):
    """Persistent state for long-running projects"""
    project_id: UUID
    tenant_id: UUID
    
    # Checkpoint metadata
    last_checkpoint: datetime
    checkpoint_count: int
    
    # Project state
    current_phase: str
    completed_tasks: List[UUID]
    pending_tasks: List[UUID]
    blocked_tasks: List[UUID]
    
    # World state (for cinematic use case)
    world_state: Dict[str, Any]
    style_guidelines: Dict[str, Any]
    character_bibles: Dict[str, Any]
    narrative_timeline: List[Dict[str, Any]]
    
    # Resource tracking
    total_cost_usd: float
    estimated_remaining_cost: float
    
    # Git integration
    git_commit_hash: Optional[str]
    git_branch: str
    
    # Metadata
    created_at: datetime
    updated_at: datetime
```

---

## 4. Agent-Based Modeling (ABM) Integration

### 4.1 Mesa Framework Integration

```python
# services/vessel-simulation/app/abm_engine.py

from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector

class MAARSAgent(Agent):
    """Shadow agent for simulation"""
    
    def __init__(self, unique_id, model, agent_config):
        super().__init__(unique_id, model)
        self.agent_type = agent_config.agent_type
        self.capabilities = agent_config.capabilities
        self.cost_per_task = agent_config.cost_per_task
        self.success_rate = agent_config.success_rate
        self.tasks_completed = 0
        
    def step(self):
        """Execute one simulation step"""
        # Simulate task execution
        if self.random.random() < self.success_rate:
            self.tasks_completed += 1
            self.model.total_cost += self.cost_per_task

class MAARSSimulationModel(Model):
    """ABM model for MAARS swarm simulation"""
    
    def __init__(self, num_agents, task_count, time_horizon):
        self.num_agents = num_agents
        self.task_count = task_count
        self.time_horizon = time_horizon
        self.schedule = RandomActivation(self)
        self.total_cost = 0.0
        
        # Create shadow agents
        for i in range(num_agents):
            agent = MAARSAgent(i, self, agent_config)
            self.schedule.add(agent)
        
        # Data collection
        self.datacollector = DataCollector(
            model_reporters={
                "TotalCost": lambda m: m.total_cost,
                "TasksCompleted": lambda m: sum(a.tasks_completed for a in m.schedule.agents),
            },
            agent_reporters={
                "TasksCompleted": "tasks_completed",
            }
        )
    
    def step(self):
        """Execute one time step"""
        self.datacollector.collect(self)
        self.schedule.step()
```

### 4.2 Backtesting Engine

```python
# services/vessel-simulation/app/backtest.py

class BacktestEngine:
    """Run predictive simulations"""
    
    async def run_monte_carlo(
        self,
        scenario: SimulationScenario,
        iterations: int = 1000,
    ) -> SimulationResult:
        """
        Run Monte Carlo simulation to predict outcomes
        
        Returns:
        - Confidence intervals for cost, duration, success rate
        - Risk factors and bottlenecks
        - Recommended strategy adjustments
        """
        
        results = []
        
        for i in range(iterations):
            # Create model with randomized parameters
            model = MAARSSimulationModel(
                num_agents=scenario.num_agents,
                task_count=scenario.task_count,
                time_horizon=scenario.time_horizon,
            )
            
            # Run simulation
            for _ in range(scenario.max_steps):
                model.step()
            
            # Collect results
            results.append({
                "total_cost": model.total_cost,
                "tasks_completed": sum(a.tasks_completed for a in model.schedule.agents),
                "success_rate": sum(a.tasks_completed for a in model.schedule.agents) / scenario.task_count,
            })
        
        # Analyze results
        return self.analyze_monte_carlo_results(results, scenario)
```

---

## 5. World State Persistence (`vessel-memory`)

### 5.1 GraphRAG Extensions for Digital Twins

```python
# services/vessel-memory/app/digital_twin.py

class DigitalTwinManager:
    """Manages persistent world states for long-running projects"""
    
    async def create_world_state(
        self,
        project_id: UUID,
        world_definition: Dict[str, Any],
    ) -> DigitalTwinState:
        """
        Create persistent world state with:
        - Character bibles
        - Style guidelines
        - Architectural rules
        - Narrative timelines
        """
        
        # Create knowledge graph nodes for world entities
        entities = await self.extract_world_entities(world_definition)
        
        for entity in entities:
            kg_node = await self.kg_client.create_node(
                entity_type=EntityType.DIGITAL_TWIN,
                entity_name=entity.name,
                properties=entity.properties,
            )
            
            # Create relationships
            for relation in entity.relationships:
                await self.kg_client.create_edge(
                    source_id=kg_node.kg_node_id,
                    target_id=relation.target_id,
                    relationship_type=RelationshipType.SIMULATES,
                )
        
        # Store world state snapshot
        twin_state = DigitalTwinState(
            twin_id=uuid4(),
            tenant_id=project_id,
            entity_type="world",
            entity_id=project_id,
            state_snapshot=world_definition,
        )
        
        await self.store_twin_state(twin_state)
        return twin_state
    
    async def restore_world_state(
        self,
        project_id: UUID,
        checkpoint: Optional[datetime] = None,
    ) -> DigitalTwinState:
        """Restore world state from checkpoint"""
        
        # Query GraphRAG for world state
        query = GraphRAGQuery(
            tenant_id=project_id,
            query="Retrieve complete world state",
            entity_types=[EntityType.DIGITAL_TWIN],
            max_depth=5,
        )
        
        graph_context = await self.kg_client.query_graphrag(query)
        
        # Reconstruct world state
        world_state = await self.reconstruct_from_graph(
            graph_context=graph_context,
            checkpoint=checkpoint,
        )
        
        return world_state
```

### 5.2 Style Consistency Engine

```python
# services/vessel-memory/app/style_engine.py

class StyleConsistencyEngine:
    """Ensures stylistic consistency across long time horizons"""
    
    async def validate_asset_style(
        self,
        asset: Asset,
        project_id: UUID,
    ) -> StyleValidationResult:
        """
        Validate new asset against established style guidelines
        
        Returns:
        - Consistency score (0-1)
        - Specific violations
        - Recommended adjustments
        """
        
        # Retrieve style guidelines from world state
        world_state = await self.twin_manager.restore_world_state(project_id)
        style_guide = world_state.state_snapshot["style_guidelines"]
        
        # Compare asset against guidelines
        violations = []
        
        # Color palette check
        if "color_palette" in style_guide:
            color_score = self.check_color_consistency(
                asset.colors,
                style_guide["color_palette"],
            )
            if color_score < 0.8:
                violations.append({
                    "type": "color_palette",
                    "score": color_score,
                    "expected": style_guide["color_palette"],
                    "actual": asset.colors,
                })
        
        # Architectural style check
        if "architecture" in style_guide:
            arch_score = self.check_architectural_consistency(
                asset.architecture,
                style_guide["architecture"],
            )
            if arch_score < 0.8:
                violations.append({
                    "type": "architecture",
                    "score": arch_score,
                })
        
        # Calculate overall consistency
        consistency_score = 1.0 - (len(violations) / len(style_guide))
        
        return StyleValidationResult(
            asset_id=asset.asset_id,
            consistency_score=consistency_score,
            violations=violations,
            recommendations=self.generate_recommendations(violations),
        )
```

---

## 6. Vision Layer Integration

### 6.1 Simulation Dashboard

```html
<!-- services/vessel-interface/public/simulation.html -->

<div class="simulation-dashboard">
    <!-- Real-time ABM Visualization -->
    <div class="abm-canvas">
        <canvas id="abm-visualization"></canvas>
    </div>
    
    <!-- Confidence Heatmap -->
    <div class="confidence-heatmap">
        <h3>Outcome Confidence</h3>
        <div id="heatmap-container"></div>
    </div>
    
    <!-- Predictive Timeline -->
    <div class="predictive-timeline">
        <h3>Predicted Execution Timeline</h3>
        <div id="timeline-chart"></div>
    </div>
    
    <!-- World State Viewer -->
    <div class="world-state-viewer">
        <h3>Digital Twin State</h3>
        <div id="world-state-tree"></div>
    </div>
</div>
```

### 6.2 WebSocket Integration

```javascript
// services/vessel-interface/src/simulation-client.js

class SimulationClient {
    constructor() {
        this.ws = new WebSocket('ws://localhost:8000/ws/simulation');
        this.setupHandlers();
    }
    
    setupHandlers() {
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            switch(data.event_type) {
                case 'simulation.progress':
                    this.updateABMVisualization(data.payload);
                    break;
                case 'simulation.completed':
                    this.displayResults(data.payload);
                    break;
                case 'world_state.updated':
                    this.refreshWorldStateViewer(data.payload);
                    break;
            }
        };
    }
    
    updateABMVisualization(payload) {
        // Update canvas with agent positions and states
        const canvas = document.getElementById('abm-visualization');
        const ctx = canvas.getContext('2d');
        
        // Draw agents
        payload.agents.forEach(agent => {
            ctx.fillStyle = agent.status === 'active' ? '#10b981' : '#6b7280';
            ctx.fillRect(agent.x, agent.y, 10, 10);
        });
    }
}
```

---

## 7. Implementation Roadmap

### Milestone 8.4: Agency Agents Foundation (Week 1-2)
- [ ] Implement `PersonaManager` in vessel-swarm
- [ ] Add persona upload API endpoint
- [ ] Create database schema for personas and flows
- [ ] Build persona parsing from YAML/ZIP
- [ ] Add unit tests for persona system

### Milestone 8.5: Communication Flow Enforcement (Week 3-4)
- [ ] Update LangGraph orchestrator with flow validation
- [ ] Implement `CommunicationFlowEnforcer` middleware
- [ ] Add flow violation logging and alerts
- [ ] Create flow visualization in Vision Layer
- [ ] Integration tests for flow enforcement

### Milestone 8.6: Long-Running Harness (Week 5-6)
- [ ] Implement `InitializerAgent` in vessel-simulation
- [ ] Build `ProgressState` persistence layer
- [ ] Add git history parsing
- [ ] Create checkpoint management system
- [ ] Add resume-from-checkpoint functionality

### Milestone 8.7: ABM Integration (Week 7-8)
- [ ] Integrate Mesa framework
- [ ] Implement `MAARSSimulationModel`
- [ ] Build `BacktestEngine` with Monte Carlo
- [ ] Add scenario template system
- [ ] Create simulation result analysis

### Milestone 8.8: World State & Vision Layer (Week 9-10)
- [ ] Implement `DigitalTwinManager` in vessel-memory
- [ ] Build `StyleConsistencyEngine`
- [ ] Create simulation dashboard UI
- [ ] Add WebSocket streaming for live updates
- [ ] Implement world state visualization

---

## 8. Success Metrics

### Technical Metrics
- **Context Restoration Accuracy**: >95% fidelity when resuming after 6+ months
- **Style Consistency Score**: >90% for assets generated months apart
- **Simulation Prediction Accuracy**: Within 15% of actual outcomes
- **Communication Flow Violations**: <1% of inter-agent messages

### Business Metrics
- **Production Continuity**: Enable 6+ month project pauses without context loss
- **Cost Predictability**: ±10% accuracy in cost forecasting via ABM
- **Time to Resume**: <5 minutes to fully restore project context
- **Multi-Agent Efficiency**: 3x improvement in swarm coordination

---

## 9. Risk Mitigation

### Technical Risks
1. **GraphRAG Scalability**: World states may grow very large
   - Mitigation: Implement state compression and archival
   
2. **ABM Performance**: Simulations may be computationally expensive
   - Mitigation: Use headless execution and result caching
   
3. **Context Window Limits**: Long-running projects may exceed LLM context
   - Mitigation: Hierarchical summarization and progressive loading

### Operational Risks
1. **Persona Complexity**: Users may create overly complex communication flows
   - Mitigation: Provide templates and flow validation
   
2. **State Corruption**: Progress states may become inconsistent
   - Mitigation: Implement state versioning and rollback

---

## 10. Future Enhancements (Phase 9+)

- **Multi-Modal World States**: Support for 3D assets, audio, video
- **Collaborative Editing**: Multiple users editing world state simultaneously
- **Temporal Queries**: "Show me the world state as it was 3 months ago"
- **Predictive Alerts**: "Your current trajectory will exceed budget by 20%"
- **Cross-Project Learning**: Personas learn from multiple projects

---

**Document Version**: 1.0  
**Last Updated**: 2026-03-22  
**Authors**: MAARS Architecture Team  
**Status**: Ready for Implementation

---

*Made with Bob*