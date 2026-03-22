"""Goal planning and task decomposition using LangGraph"""
import asyncio
import uuid
from collections import defaultdict, deque
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Set, Optional, Tuple

import structlog
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

from app.kafka_producer import KafkaProducer
from app.sandbox_client import SandboxClient

logger = structlog.get_logger()


class ModelTier(str, Enum):
    """LLM model tiers for right-sizing"""
    NANO = "nano"      # Fast, cheap, simple tasks (e.g., gpt-3.5-turbo)
    MID = "mid"        # Balanced, moderate complexity (e.g., gpt-4)
    FRONTIER = "frontier"  # Most capable, complex tasks (e.g., gpt-4-turbo, claude-3-opus)


class TaskComplexity(str, Enum):
    """Task complexity levels"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class GoalState(TypedDict):
    """Enhanced state for goal processing with DAG support"""
    # Basic goal info
    goal_id: str
    tenant_id: str
    description: str
    priority: str
    status: str
    
    # DAG mode flag
    use_dag_mode: bool
    
    # Task management
    tasks: List[Dict[str, Any]]
    current_task_index: int  # For simple mode
    
    # DAG-specific fields
    task_graph: Dict[str, List[str]]  # task_id -> [dependent_task_ids]
    task_status: Dict[str, str]  # task_id -> status
    task_results: Dict[str, Any]  # task_id -> result
    ready_tasks: List[str]  # Tasks ready to execute
    executing_tasks: Set[str]  # Currently executing tasks
    completed_tasks: Set[str]  # Completed task IDs
    failed_tasks: Set[str]  # Failed task IDs
    
    # Right-sizing data
    task_sizing: Dict[str, Dict[str, Any]]  # task_id -> sizing info
    
    # Results and errors
    results: Dict[str, Any]
    error: str | None
    
    # Metrics
    total_tasks: int
    parallel_executions: int
    dag_depth: int


class RightSizingEngine:
    """
    Right-Sizing Engine for optimal resource allocation
    
    Analyzes task complexity and selects appropriate:
    - Model tier (NANO/MID/FRONTIER)
    - Resource limits (CPU, memory, timeout)
    - Execution strategy
    """
    
    # Complexity scoring weights
    WEIGHTS = {
        "code_lines": 0.2,
        "logic_depth": 0.3,
        "data_processing": 0.2,
        "api_calls": 0.15,
        "computation": 0.15,
    }
    
    # Model tier thresholds (complexity score 0-100)
    TIER_THRESHOLDS = {
        ModelTier.NANO: (0, 30),
        ModelTier.MID: (30, 70),
        ModelTier.FRONTIER: (70, 100),
    }
    
    # Resource limits by tier
    RESOURCE_LIMITS = {
        ModelTier.NANO: {
            "max_execution_time_ms": 5000,
            "max_memory_mb": 128,
            "timeout_buffer": 1.2,
        },
        ModelTier.MID: {
            "max_execution_time_ms": 30000,
            "max_memory_mb": 512,
            "timeout_buffer": 1.5,
        },
        ModelTier.FRONTIER: {
            "max_execution_time_ms": 120000,
            "max_memory_mb": 2048,
            "timeout_buffer": 2.0,
        },
    }
    
    @classmethod
    def analyze_task_complexity(cls, task: Dict[str, Any]) -> Tuple[TaskComplexity, int]:
        """
        Analyze task complexity and return complexity level and score
        
        Args:
            task: Task dictionary with description and metadata
            
        Returns:
            Tuple of (complexity_level, complexity_score)
        """
        description = task.get("description", "")
        task_type = task.get("type", "code_execution")
        
        # Calculate complexity score (0-100)
        score = 0
        
        # Code lines estimation
        code_lines = len(description.split("\n"))
        if code_lines > 100:
            score += 20
        elif code_lines > 50:
            score += 15
        elif code_lines > 20:
            score += 10
        else:
            score += 5
        
        # Logic depth (nested structures, loops, conditionals)
        logic_indicators = ["for ", "while ", "if ", "elif ", "def ", "class ", "try:", "with "]
        logic_count = sum(description.count(ind) for ind in logic_indicators)
        score += min(logic_count * 3, 30)
        
        # Data processing complexity
        data_indicators = ["pandas", "numpy", "json", "csv", "dataframe", "array"]
        if any(ind in description.lower() for ind in data_indicators):
            score += 15
        
        # API/Network calls
        api_indicators = ["requests", "http", "api", "fetch", "urllib"]
        if any(ind in description.lower() for ind in api_indicators):
            score += 10
        
        # Computational complexity
        compute_indicators = ["algorithm", "sort", "search", "optimize", "calculate"]
        if any(ind in description.lower() for ind in compute_indicators):
            score += 10
        
        # Task type adjustments
        if task_type == "research":
            score += 15
        elif task_type == "analysis":
            score += 10
        
        # Determine complexity level
        if score >= 70:
            complexity = TaskComplexity.VERY_COMPLEX
        elif score >= 50:
            complexity = TaskComplexity.COMPLEX
        elif score >= 25:
            complexity = TaskComplexity.MODERATE
        else:
            complexity = TaskComplexity.SIMPLE
        
        return complexity, min(score, 100)
    
    @classmethod
    def select_model_tier(cls, complexity_score: int, priority: str = "MEDIUM") -> ModelTier:
        """
        Select appropriate model tier based on complexity and priority
        
        Args:
            complexity_score: Task complexity score (0-100)
            priority: Task priority (LOW/MEDIUM/HIGH/CRITICAL)
            
        Returns:
            Selected model tier
        """
        # Priority can bump up tier
        priority_boost = {
            "LOW": 0,
            "MEDIUM": 0,
            "HIGH": 10,
            "CRITICAL": 20,
        }
        
        adjusted_score = min(complexity_score + priority_boost.get(priority, 0), 100)
        
        for tier, (min_score, max_score) in cls.TIER_THRESHOLDS.items():
            if min_score <= adjusted_score < max_score:
                return tier
        
        return ModelTier.FRONTIER
    
    @classmethod
    def estimate_resources(
        cls,
        task: Dict[str, Any],
        model_tier: ModelTier,
        complexity_score: int,
    ) -> Dict[str, Any]:
        """
        Estimate resource requirements for a task
        
        Args:
            task: Task dictionary
            model_tier: Selected model tier
            complexity_score: Task complexity score
            
        Returns:
            Resource estimation dictionary
        """
        base_limits = cls.RESOURCE_LIMITS[model_tier]
        
        # Adjust based on complexity within tier
        complexity_factor = complexity_score / 100.0
        
        return {
            "model_tier": model_tier.value,
            "max_execution_time_ms": int(
                base_limits["max_execution_time_ms"] * (0.5 + complexity_factor)
            ),
            "max_memory_mb": int(
                base_limits["max_memory_mb"] * (0.5 + complexity_factor)
            ),
            "timeout_buffer": base_limits["timeout_buffer"],
            "estimated_cost": cls._estimate_cost(model_tier, complexity_score),
            "complexity_score": complexity_score,
        }
    
    @classmethod
    def _estimate_cost(cls, model_tier: ModelTier, complexity_score: int) -> float:
        """Estimate execution cost in credits"""
        base_costs = {
            ModelTier.NANO: 0.01,
            ModelTier.MID: 0.05,
            ModelTier.FRONTIER: 0.20,
        }
        
        return base_costs[model_tier] * (1 + complexity_score / 100.0)


class DAGBuilder:
    """
    Builds and manages task dependency graphs (DAGs)
    """
    
    @staticmethod
    def build_dependency_graph(tasks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Build dependency graph from tasks
        
        Args:
            tasks: List of task dictionaries with optional 'depends_on' field
            
        Returns:
            Adjacency list: task_id -> [dependent_task_ids]
        """
        graph = defaultdict(list)
        
        for task in tasks:
            task_id = task["task_id"]
            depends_on = task.get("depends_on", [])
            
            # Add dependencies
            for dep_id in depends_on:
                graph[dep_id].append(task_id)
            
            # Ensure task exists in graph even if no dependencies
            if task_id not in graph:
                graph[task_id] = []
        
        return dict(graph)
    
    @staticmethod
    def topological_sort(
        tasks: List[Dict[str, Any]],
        graph: Dict[str, List[str]],
    ) -> List[List[str]]:
        """
        Perform topological sort to get execution levels
        
        Args:
            tasks: List of tasks
            graph: Dependency graph
            
        Returns:
            List of levels, where each level contains task IDs that can run in parallel
        """
        # Build reverse graph (task -> dependencies)
        in_degree = defaultdict(int)
        reverse_graph = defaultdict(list)
        
        task_ids = {task["task_id"] for task in tasks}
        
        for task in tasks:
            task_id = task["task_id"]
            depends_on = task.get("depends_on", [])
            in_degree[task_id] = len(depends_on)
            
            for dep_id in depends_on:
                reverse_graph[dep_id].append(task_id)
        
        # Find tasks with no dependencies (level 0)
        levels = []
        queue = deque([tid for tid in task_ids if in_degree[tid] == 0])
        
        while queue:
            level_size = len(queue)
            current_level = []
            
            for _ in range(level_size):
                task_id = queue.popleft()
                current_level.append(task_id)
                
                # Reduce in-degree for dependent tasks
                for dependent in reverse_graph[task_id]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
            
            levels.append(current_level)
        
        return levels
    
    @staticmethod
    def detect_cycles(tasks: List[Dict[str, Any]]) -> Optional[List[str]]:
        """
        Detect cycles in task dependencies
        
        Args:
            tasks: List of tasks
            
        Returns:
            List of task IDs in cycle, or None if no cycle
        """
        visited = set()
        rec_stack = set()
        
        def dfs(task_id: str, path: List[str]) -> Optional[List[str]]:
            visited.add(task_id)
            rec_stack.add(task_id)
            path.append(task_id)
            
            # Find task
            task = next((t for t in tasks if t["task_id"] == task_id), None)
            if not task:
                return None
            
            for dep_id in task.get("depends_on", []):
                if dep_id not in visited:
                    cycle = dfs(dep_id, path.copy())
                    if cycle:
                        return cycle
                elif dep_id in rec_stack:
                    # Found cycle
                    cycle_start = path.index(dep_id)
                    return path[cycle_start:] + [dep_id]
            
            rec_stack.remove(task_id)
            return None
        
        for task in tasks:
            task_id = task["task_id"]
            if task_id not in visited:
                cycle = dfs(task_id, [])
                if cycle:
                    return cycle
        
        return None


class GoalPlanner:
    """
    Enhanced Goal planner with multi-task DAG support and Right-Sizing Engine
    
    Features:
    - Multi-task DAG execution with dependency resolution
    - Parallel execution of independent tasks
    - Right-Sizing Engine for optimal resource allocation
    - LLM-based task decomposition (via vessel-llm-router)
    - Backward compatible with simple single-task execution
    """
    
    def __init__(
        self,
        sandbox_client: SandboxClient,
        kafka_producer: KafkaProducer,
        llm_router_url: Optional[str] = None,
        enable_dag_mode: bool = True,
        max_parallel_tasks: int = 5,
    ):
        self.sandbox_client = sandbox_client
        self.kafka_producer = kafka_producer
        self.llm_router_url = llm_router_url
        self.enable_dag_mode = enable_dag_mode
        self.max_parallel_tasks = max_parallel_tasks
        
        # Initialize engines
        self.right_sizing = RightSizingEngine()
        self.dag_builder = DAGBuilder()
        
        # Build LangGraph workflows
        self.simple_workflow = self._build_simple_workflow()
        self.dag_workflow = self._build_dag_workflow()
        
    def _build_simple_workflow(self) -> StateGraph:
        """Build simple workflow for backward compatibility"""
        workflow = StateGraph(GoalState)
        
        # Add nodes
        workflow.add_node("plan", self._plan_tasks_simple)
        workflow.add_node("execute", self._execute_task_simple)
        workflow.add_node("complete", self._complete_goal)
        
        # Set entry point
        workflow.set_entry_point("plan")
        
        # Add edges
        workflow.add_edge("plan", "execute")
        workflow.add_conditional_edges(
            "execute",
            self._should_continue_simple,
            {
                "continue": "execute",
                "complete": "complete",
            }
        )
        workflow.add_edge("complete", END)
        
        return workflow.compile()
    
    def _build_dag_workflow(self) -> StateGraph:
        """Build enhanced DAG workflow"""
        workflow = StateGraph(GoalState)
        
        # Add nodes
        workflow.add_node("analyze", self._analyze_goal)
        workflow.add_node("decompose", self._decompose_into_tasks)
        workflow.add_node("build_dag", self._build_task_dag)
        workflow.add_node("right_size", self._right_size_tasks)
        workflow.add_node("execute_dag", self._execute_dag_level)
        workflow.add_node("aggregate", self._aggregate_results)
        workflow.add_node("complete", self._complete_goal)
        
        # Set entry point
        workflow.set_entry_point("analyze")
        
        # Add edges
        workflow.add_edge("analyze", "decompose")
        workflow.add_edge("decompose", "build_dag")
        workflow.add_edge("build_dag", "right_size")
        workflow.add_edge("right_size", "execute_dag")
        workflow.add_conditional_edges(
            "execute_dag",
            self._should_continue_dag,
            {
                "continue": "execute_dag",
                "aggregate": "aggregate",
                "failed": "complete",
            }
        )
        workflow.add_edge("aggregate", "complete")
        workflow.add_edge("complete", END)
        
        return workflow.compile()
    
    async def process_goal(self, goal_packet: Dict[str, Any]):
        """
        Process a goal through the planning and execution workflow
        
        Args:
            goal_packet: Goal data from the API
        """
        logger.info("Processing goal", goal_id=goal_packet["goal_id"])
        
        # Determine if we should use DAG mode
        use_dag = self.enable_dag_mode and goal_packet.get("use_dag_mode", True)
        
        # Initialize state
        state: GoalState = {
            "goal_id": goal_packet["goal_id"],
            "tenant_id": goal_packet["tenant_id"],
            "description": goal_packet["description"],
            "priority": goal_packet.get("priority", "MEDIUM"),
            "status": "PLANNING",
            "use_dag_mode": use_dag,
            "tasks": [],
            "current_task_index": 0,
            "task_graph": {},
            "task_status": {},
            "task_results": {},
            "ready_tasks": [],
            "executing_tasks": set(),
            "completed_tasks": set(),
            "failed_tasks": set(),
            "task_sizing": {},
            "results": {},
            "error": None,
            "total_tasks": 0,
            "parallel_executions": 0,
            "dag_depth": 0,
        }
        
        try:
            # Select and run appropriate workflow
            workflow = self.dag_workflow if use_dag else self.simple_workflow
            final_state = await workflow.ainvoke(state)
            
            logger.info(
                "Goal processing completed",
                goal_id=goal_packet["goal_id"],
                status=final_state["status"],
                use_dag_mode=use_dag,
                total_tasks=final_state.get("total_tasks", 0),
            )
            
        except Exception as e:
            logger.error(
                "Goal processing failed",
                goal_id=goal_packet["goal_id"],
                error=str(e),
            )
            
            # Publish failure event
            await self.kafka_producer.send_event(
                topic="maars.goals",
                event_type="goal.failed",
                payload={
                    "goal_id": goal_packet["goal_id"],
                    "error": str(e),
                    "failed_at": datetime.utcnow().isoformat(),
                },
            )
    
    # ========== Simple Workflow Methods (Backward Compatible) ==========
    
    async def _plan_tasks_simple(self, state: GoalState) -> GoalState:
        """Simple planning for backward compatibility"""
        logger.info("Planning tasks (simple mode)", goal_id=state["goal_id"])
        
        await self.kafka_producer.send_event(
            topic="maars.goals",
            event_type="goal.planning",
            payload={"goal_id": state["goal_id"]},
        )
        
        # Create single task
        task = {
            "task_id": str(uuid.uuid4()),
            "goal_id": state["goal_id"],
            "description": state["description"],
            "type": "code_execution",
            "language": "python",
            "network_policy": "ISOLATED",
            "status": TaskStatus.PENDING.value,
        }
        
        state["tasks"] = [task]
        state["status"] = "EXECUTING"
        state["total_tasks"] = 1
        
        return state
    
    async def _execute_task_simple(self, state: GoalState) -> GoalState:
        """Execute task in simple mode"""
        task = state["tasks"][state["current_task_index"]]
        task_id = task["task_id"]
        
        logger.info("Executing task (simple mode)", task_id=task_id)
        
        await self.kafka_producer.send_event(
            topic="maars.tasks",
            event_type="task.executing",
            payload={"task_id": task_id, "goal_id": state["goal_id"]},
        )
        
        try:
            code = self._extract_or_generate_code(state["description"])
            
            result = await self.sandbox_client.execute_code(
                task_id=task_id,
                tenant_id=state["tenant_id"],
                code=code,
                language=task["language"],
                network_policy=task["network_policy"],
            )
            
            state["results"][task_id] = result
            
            await self.kafka_producer.send_event(
                topic="maars.tasks",
                event_type="task.completed",
                payload={
                    "task_id": task_id,
                    "goal_id": state["goal_id"],
                    "status": result["status"],
                },
            )
            
        except Exception as e:
            logger.error("Task execution failed", task_id=task_id, error=str(e))
            state["error"] = str(e)
            
            await self.kafka_producer.send_event(
                topic="maars.tasks",
                event_type="task.failed",
                payload={"task_id": task_id, "goal_id": state["goal_id"], "error": str(e)},
            )
        
        state["current_task_index"] += 1
        return state
    
    def _should_continue_simple(self, state: GoalState) -> str:
        """Determine if simple workflow should continue"""
        if state["error"]:
            return "complete"
        if state["current_task_index"] >= len(state["tasks"]):
            return "complete"
        return "continue"
    
    # ========== DAG Workflow Methods ==========
    
    async def _analyze_goal(self, state: GoalState) -> GoalState:
        """Analyze goal complexity and determine execution strategy"""
        logger.info("Analyzing goal", goal_id=state["goal_id"])
        
        state["status"] = "ANALYZING"
        
        await self.kafka_producer.send_event(
            topic="maars.goals",
            event_type="goal.analyzing",
            payload={"goal_id": state["goal_id"]},
        )
        
        # Analyze goal complexity
        description = state["description"]
        
        # Check for multi-task indicators
        multi_task_indicators = [
            "and then", "after that", "first", "second", "finally",
            "step 1", "step 2", "task 1", "task 2",
            "depends on", "requires", "prerequisite"
        ]
        
        is_complex = any(ind in description.lower() for ind in multi_task_indicators)
        
        logger.info(
            "Goal analysis complete",
            goal_id=state["goal_id"],
            is_complex=is_complex,
        )
        
        return state
    
    async def _decompose_into_tasks(self, state: GoalState) -> GoalState:
        """Decompose goal into multiple tasks using LLM"""
        logger.info("Decomposing goal into tasks", goal_id=state["goal_id"])
        
        state["status"] = "DECOMPOSING"
        
        await self.kafka_producer.send_event(
            topic="maars.goals",
            event_type="goal.decomposing",
            payload={"goal_id": state["goal_id"]},
        )
        
        # For Phase 2, this would call vessel-llm-router to decompose the goal
        # For now, use heuristic decomposition
        tasks = self._heuristic_decompose(state["description"], state["goal_id"])
        
        state["tasks"] = tasks
        state["total_tasks"] = len(tasks)
        
        # Initialize task status
        for task in tasks:
            state["task_status"][task["task_id"]] = TaskStatus.PENDING.value
        
        logger.info(
            "Goal decomposed",
            goal_id=state["goal_id"],
            task_count=len(tasks),
        )
        
        return state
    
    async def _build_task_dag(self, state: GoalState) -> GoalState:
        """Build dependency graph for tasks"""
        logger.info("Building task DAG", goal_id=state["goal_id"])
        
        state["status"] = "BUILDING_DAG"
        
        # Build dependency graph
        state["task_graph"] = self.dag_builder.build_dependency_graph(state["tasks"])
        
        # Check for cycles
        cycle = self.dag_builder.detect_cycles(state["tasks"])
        if cycle:
            error_msg = f"Circular dependency detected: {' -> '.join(cycle)}"
            logger.error("DAG has cycle", goal_id=state["goal_id"], cycle=cycle)
            state["error"] = error_msg
            return state
        
        # Perform topological sort to get execution levels
        levels = self.dag_builder.topological_sort(state["tasks"], state["task_graph"])
        state["dag_depth"] = len(levels)
        
        # Identify ready tasks (no dependencies)
        state["ready_tasks"] = levels[0] if levels else []
        
        logger.info(
            "DAG built successfully",
            goal_id=state["goal_id"],
            dag_depth=state["dag_depth"],
            ready_tasks=len(state["ready_tasks"]),
        )
        
        return state
    
    async def _right_size_tasks(self, state: GoalState) -> GoalState:
        """Apply Right-Sizing Engine to all tasks"""
        logger.info("Right-sizing tasks", goal_id=state["goal_id"])
        
        state["status"] = "RIGHT_SIZING"
        
        for task in state["tasks"]:
            task_id = task["task_id"]
            
            # Analyze complexity
            complexity, score = self.right_sizing.analyze_task_complexity(task)
            
            # Select model tier
            model_tier = self.right_sizing.select_model_tier(score, state["priority"])
            
            # Estimate resources
            sizing = self.right_sizing.estimate_resources(task, model_tier, score)
            
            # Store sizing info
            state["task_sizing"][task_id] = {
                "complexity": complexity.value,
                "complexity_score": score,
                "model_tier": model_tier.value,
                **sizing,
            }
            
            logger.info(
                "Task sized",
                task_id=task_id,
                complexity=complexity.value,
                model_tier=model_tier.value,
                score=score,
            )
        
        return state
    
    async def _execute_dag_level(self, state: GoalState) -> GoalState:
        """Execute ready tasks in parallel"""
        if not state["ready_tasks"]:
            return state
        
        logger.info(
            "Executing DAG level",
            goal_id=state["goal_id"],
            ready_tasks=len(state["ready_tasks"]),
        )
        
        state["status"] = "EXECUTING"
        
        # Limit parallel execution
        tasks_to_execute = state["ready_tasks"][:self.max_parallel_tasks]
        state["parallel_executions"] = max(
            state["parallel_executions"],
            len(tasks_to_execute)
        )
        
        # Execute tasks in parallel
        execution_tasks = []
        for task_id in tasks_to_execute:
            task = next(t for t in state["tasks"] if t["task_id"] == task_id)
            state["task_status"][task_id] = TaskStatus.EXECUTING.value
            state["executing_tasks"].add(task_id)
            execution_tasks.append(self._execute_single_task(state, task))
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            task_id = tasks_to_execute[i]
            state["executing_tasks"].discard(task_id)
            
            if isinstance(result, Exception):
                logger.error("Task failed", task_id=task_id, error=str(result))
                state["task_status"][task_id] = TaskStatus.FAILED.value
                state["failed_tasks"].add(task_id)
            else:
                state["task_status"][task_id] = TaskStatus.COMPLETED.value
                state["completed_tasks"].add(task_id)
                state["task_results"][task_id] = result
        
        # Update ready tasks
        state["ready_tasks"] = self._get_next_ready_tasks(state)
        
        return state
    
    async def _execute_single_task(
        self,
        state: GoalState,
        task: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a single task with right-sizing"""
        task_id = task["task_id"]
        sizing = state["task_sizing"].get(task_id, {})
        
        logger.info("Executing task", task_id=task_id, sizing=sizing)
        
        await self.kafka_producer.send_event(
            topic="maars.tasks",
            event_type="task.executing",
            payload={
                "task_id": task_id,
                "goal_id": state["goal_id"],
                "model_tier": sizing.get("model_tier"),
            },
        )
        
        try:
            # Generate or extract code
            code = self._extract_or_generate_code(task["description"])
            
            # Execute with right-sized resources
            result = await self.sandbox_client.execute_code(
                task_id=task_id,
                tenant_id=state["tenant_id"],
                code=code,
                language=task.get("language", "python"),
                network_policy=task.get("network_policy", "ISOLATED"),
                max_execution_time_ms=sizing.get("max_execution_time_ms"),
                max_memory_mb=sizing.get("max_memory_mb"),
            )
            
            await self.kafka_producer.send_event(
                topic="maars.tasks",
                event_type="task.completed",
                payload={
                    "task_id": task_id,
                    "goal_id": state["goal_id"],
                    "status": result["status"],
                    "execution_time_ms": result.get("execution_time_ms"),
                },
            )
            
            return result
            
        except Exception as e:
            logger.error("Task execution failed", task_id=task_id, error=str(e))
            
            await self.kafka_producer.send_event(
                topic="maars.tasks",
                event_type="task.failed",
                payload={
                    "task_id": task_id,
                    "goal_id": state["goal_id"],
                    "error": str(e),
                },
            )
            raise
    
    def _get_next_ready_tasks(self, state: GoalState) -> List[str]:
        """Get tasks that are ready to execute (dependencies satisfied)"""
        ready = []
        
        for task in state["tasks"]:
            task_id = task["task_id"]
            
            # Skip if already completed or failed
            if task_id in state["completed_tasks"] or task_id in state["failed_tasks"]:
                continue
            
            # Skip if already executing
            if task_id in state["executing_tasks"]:
                continue
            
            # Check if all dependencies are satisfied
            depends_on = task.get("depends_on", [])
            if all(dep_id in state["completed_tasks"] for dep_id in depends_on):
                ready.append(task_id)
        
        return ready
    
    def _should_continue_dag(self, state: GoalState) -> str:
        """Determine if DAG execution should continue"""
        # Check for errors
        if state["error"]:
            return "failed"
        
        # Check if any tasks failed
        if state["failed_tasks"]:
            return "failed"
        
        # Check if all tasks completed
        if len(state["completed_tasks"]) == state["total_tasks"]:
            return "aggregate"
        
        # Check if there are ready tasks
        if state["ready_tasks"]:
            return "continue"
        
        # Check if tasks are still executing
        if state["executing_tasks"]:
            return "continue"
        
        # No more tasks to execute
        return "aggregate"
    
    async def _aggregate_results(self, state: GoalState) -> GoalState:
        """Aggregate results from all tasks"""
        logger.info("Aggregating results", goal_id=state["goal_id"])
        
        state["status"] = "AGGREGATING"
        
        # Combine all task results
        state["results"] = {
            "tasks": state["task_results"],
            "summary": {
                "total_tasks": state["total_tasks"],
                "completed_tasks": len(state["completed_tasks"]),
                "failed_tasks": len(state["failed_tasks"]),
                "dag_depth": state["dag_depth"],
                "max_parallel": state["parallel_executions"],
            },
        }
        
        return state
    
    def _heuristic_decompose(
        self,
        description: str,
        goal_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Heuristic-based task decomposition
        
        In Phase 2, this will be replaced with LLM-based decomposition
        """
        # Simple heuristic: split by numbered steps or sentences
        tasks = []
        
        # Try to find numbered steps
        lines = description.split("\n")
        step_lines = [l for l in lines if any(l.strip().startswith(f"{i}.") for i in range(1, 20))]
        
        if step_lines:
            # Found numbered steps
            for i, line in enumerate(step_lines):
                task = {
                    "task_id": str(uuid.uuid4()),
                    "goal_id": goal_id,
                    "description": line.strip(),
                    "type": "code_execution",
                    "language": "python",
                    "network_policy": "ISOLATED",
                    "depends_on": [tasks[i-1]["task_id"]] if i > 0 else [],
                }
                tasks.append(task)
        else:
            # Single task
            task = {
                "task_id": str(uuid.uuid4()),
                "goal_id": goal_id,
                "description": description,
                "type": "code_execution",
                "language": "python",
                "network_policy": "ISOLATED",
                "depends_on": [],
            }
            tasks.append(task)
        
        return tasks
    
    async def _complete_goal(self, state: GoalState) -> GoalState:
        """Complete the goal and publish final event"""
        if state["error"] or state.get("failed_tasks"):
            state["status"] = "FAILED"
        else:
            state["status"] = "COMPLETED"
        
        logger.info(
            "Goal completed",
            goal_id=state["goal_id"],
            status=state["status"],
            use_dag_mode=state.get("use_dag_mode", False),
            total_tasks=state.get("total_tasks", 0),
            completed_tasks=len(state.get("completed_tasks", set())),
        )
        
        # Publish completion event
        await self.kafka_producer.send_event(
            topic="maars.goals",
            event_type="goal.completed",
            payload={
                "goal_id": state["goal_id"],
                "status": state["status"],
                "completed_at": datetime.utcnow().isoformat(),
                "results": state["results"],
                "use_dag_mode": state.get("use_dag_mode", False),
                "metrics": {
                    "total_tasks": state.get("total_tasks", 0),
                    "completed_tasks": len(state.get("completed_tasks", set())),
                    "failed_tasks": len(state.get("failed_tasks", set())),
                    "dag_depth": state.get("dag_depth", 0),
                    "max_parallel": state.get("parallel_executions", 0),
                },
            },
        )
        
        return state
    
    def _extract_or_generate_code(self, description: str) -> str:
        """
        Extract or generate Python code from description
        
        Phase 1 MVP: Simple heuristic extraction
        Phase 2+: LLM-based code generation via vessel-llm-router
        """
        # Check if description contains code blocks
        if "```python" in description:
            # Extract code from markdown code block
            start = description.find("```python") + 9
            end = description.find("```", start)
            return description[start:end].strip()
        
        # Check if description looks like Python code
        if any(keyword in description for keyword in ["print(", "def ", "import ", "="]):
            return description
        
        # Default: wrap description in a print statement
        return f'print("{description}")'
    
    async def _call_llm_router(
        self,
        prompt: str,
        model_tier: ModelTier = ModelTier.MID,
        temperature: float = 0.7,
    ) -> str:
        """
        Call vessel-llm-router for LLM inference
        
        This will be used in Phase 2 for:
        - Task decomposition
        - Code generation
        - Result analysis
        """
        if not self.llm_router_url:
            logger.warning("LLM router URL not configured, skipping LLM call")
            return ""
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.llm_router_url}/v1/chat/completions",
                    json={
                        "model": model_tier.value,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": temperature,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
        except Exception as e:
            logger.error("LLM router call failed", error=str(e))
            return ""


# Made with Bob
