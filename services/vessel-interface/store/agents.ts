import { create } from 'zustand';
import { Node, Edge } from 'reactflow';

export type AgentStatus = 'PENDING' | 'READY' | 'EXECUTING' | 'COMPLETED' | 'FAILED' | 'BLOCKED';
export type ModelTier = 'NANO' | 'MID' | 'FRONTIER';

export interface AgentNodeData {
  task_id: string;
  agent_id: string;
  model_tier: ModelTier;
  status: AgentStatus;
  cost_usd: number;
  execution_time_ms: number;
  reasoning_trace?: string;
  live_log_tail?: string[];
  task_name?: string;
  created_at?: string;
  updated_at?: string;
}

export interface AgentMetrics {
  total_agents: number;
  active_agents: number;
  completed_tasks: number;
  failed_tasks: number;
  total_cost_usd: number;
  avg_execution_time_ms: number;
}

interface AgentStore {
  // DAG state
  nodes: Node<AgentNodeData>[];
  edges: Edge[];
  
  // Metrics
  metrics: AgentMetrics;
  
  // Connection status
  isConnected: boolean;
  lastEventTime: string | null;
  
  // Actions
  setNodes: (nodes: Node<AgentNodeData>[]) => void;
  setEdges: (edges: Edge[]) => void;
  addNode: (node: Node<AgentNodeData>) => void;
  addEdge: (edge: Edge) => void;
  updateNodeStatus: (task_id: string, status: AgentStatus) => void;
  updateNodeCost: (task_id: string, cost_usd: number) => void;
  updateNodeExecutionTime: (task_id: string, execution_time_ms: number) => void;
  appendNodeLog: (task_id: string, line: string) => void;
  setReasoningTrace: (task_id: string, trace: string) => void;
  updateMetrics: (metrics: Partial<AgentMetrics>) => void;
  setConnectionStatus: (isConnected: boolean) => void;
  reset: () => void;
}

const initialMetrics: AgentMetrics = {
  total_agents: 0,
  active_agents: 0,
  completed_tasks: 0,
  failed_tasks: 0,
  total_cost_usd: 0,
  avg_execution_time_ms: 0,
};

export const useAgentStore = create<AgentStore>((set, get) => ({
  nodes: [],
  edges: [],
  metrics: initialMetrics,
  isConnected: false,
  lastEventTime: null,

  setNodes: (nodes) => set({ nodes }),
  
  setEdges: (edges) => set({ edges }),
  
  addNode: (node) =>
    set((state) => ({
      nodes: [...state.nodes, node],
      metrics: {
        ...state.metrics,
        total_agents: state.metrics.total_agents + 1,
      },
    })),
  
  addEdge: (edge) =>
    set((state) => ({
      edges: [...state.edges, edge],
    })),
  
  updateNodeStatus: (task_id, status) =>
    set((state) => {
      const nodes = state.nodes.map((n) =>
        n.id === task_id
          ? {
              ...n,
              data: {
                ...n.data,
                status,
                updated_at: new Date().toISOString(),
              },
            }
          : n
      );

      // Update metrics based on status change
      const metrics = { ...state.metrics };
      if (status === 'EXECUTING') {
        metrics.active_agents = state.nodes.filter(
          (n) => n.data.status === 'EXECUTING'
        ).length + 1;
      } else if (status === 'COMPLETED') {
        metrics.completed_tasks = state.metrics.completed_tasks + 1;
        metrics.active_agents = Math.max(0, state.metrics.active_agents - 1);
      } else if (status === 'FAILED') {
        metrics.failed_tasks = state.metrics.failed_tasks + 1;
        metrics.active_agents = Math.max(0, state.metrics.active_agents - 1);
      }

      return {
        nodes,
        metrics,
        lastEventTime: new Date().toISOString(),
      };
    }),
  
  updateNodeCost: (task_id, cost_usd) =>
    set((state) => {
      const nodes = state.nodes.map((n) =>
        n.id === task_id
          ? {
              ...n,
              data: {
                ...n.data,
                cost_usd,
                updated_at: new Date().toISOString(),
              },
            }
          : n
      );

      // Recalculate total cost
      const total_cost_usd = nodes.reduce((sum, n) => sum + n.data.cost_usd, 0);

      return {
        nodes,
        metrics: {
          ...state.metrics,
          total_cost_usd,
        },
        lastEventTime: new Date().toISOString(),
      };
    }),
  
  updateNodeExecutionTime: (task_id, execution_time_ms) =>
    set((state) => {
      const nodes = state.nodes.map((n) =>
        n.id === task_id
          ? {
              ...n,
              data: {
                ...n.data,
                execution_time_ms,
                updated_at: new Date().toISOString(),
              },
            }
          : n
      );

      // Recalculate average execution time
      const completedNodes = nodes.filter((n) => n.data.status === 'COMPLETED');
      const avg_execution_time_ms =
        completedNodes.length > 0
          ? completedNodes.reduce((sum, n) => sum + n.data.execution_time_ms, 0) /
            completedNodes.length
          : 0;

      return {
        nodes,
        metrics: {
          ...state.metrics,
          avg_execution_time_ms,
        },
        lastEventTime: new Date().toISOString(),
      };
    }),
  
  appendNodeLog: (task_id, line) =>
    set((state) => ({
      nodes: state.nodes.map((n) =>
        n.id === task_id
          ? {
              ...n,
              data: {
                ...n.data,
                live_log_tail: [
                  ...(n.data.live_log_tail ?? []).slice(-4),
                  line,
                ],
                updated_at: new Date().toISOString(),
              },
            }
          : n
      ),
      lastEventTime: new Date().toISOString(),
    })),
  
  setReasoningTrace: (task_id, trace) =>
    set((state) => ({
      nodes: state.nodes.map((n) =>
        n.id === task_id
          ? {
              ...n,
              data: {
                ...n.data,
                reasoning_trace: trace,
                updated_at: new Date().toISOString(),
              },
            }
          : n
      ),
      lastEventTime: new Date().toISOString(),
    })),
  
  updateMetrics: (metrics) =>
    set((state) => ({
      metrics: {
        ...state.metrics,
        ...metrics,
      },
    })),
  
  setConnectionStatus: (isConnected) =>
    set({ isConnected }),
  
  reset: () =>
    set({
      nodes: [],
      edges: [],
      metrics: initialMetrics,
      isConnected: false,
      lastEventTime: null,
    }),
}));

// Made with Bob
