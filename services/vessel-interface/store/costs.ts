import { create } from 'zustand';

export interface CostEvent {
  event_id: string;
  tenant_id: string;
  goal_id: string;
  task_id: string;
  agent_id: string;
  model_tier: 'NANO' | 'MID' | 'FRONTIER';
  cost_usd: number;
  tokens_used: number;
  timestamp: string;
}

export interface BudgetStatus {
  tenant_id: string;
  total_budget_usd: number;
  spent_usd: number;
  remaining_usd: number;
  locked_usd: number;
  available_usd: number;
  threshold_80_reached: boolean;
  threshold_90_reached: boolean;
  threshold_100_reached: boolean;
}

export interface CostBreakdown {
  nano_cost_usd: number;
  mid_cost_usd: number;
  frontier_cost_usd: number;
  total_cost_usd: number;
  nano_percentage: number;
  mid_percentage: number;
  frontier_percentage: number;
}

interface CostStore {
  // Events
  events: CostEvent[];
  
  // Budget status
  budget: BudgetStatus | null;
  
  // Cost breakdown
  breakdown: CostBreakdown;
  
  // Connection status
  isConnected: boolean;
  lastEventTime: string | null;
  
  // Actions
  addEvent: (event: CostEvent) => void;
  updateBudget: (budget: BudgetStatus) => void;
  setConnectionStatus: (isConnected: boolean) => void;
  reset: () => void;
  
  // Computed getters
  getTotalCost: () => number;
  getCostByGoal: (goal_id: string) => number;
  getCostByAgent: (agent_id: string) => number;
  getCostByModelTier: (model_tier: 'NANO' | 'MID' | 'FRONTIER') => number;
  getRecentEvents: (limit: number) => CostEvent[];
}

const initialBreakdown: CostBreakdown = {
  nano_cost_usd: 0,
  mid_cost_usd: 0,
  frontier_cost_usd: 0,
  total_cost_usd: 0,
  nano_percentage: 0,
  mid_percentage: 0,
  frontier_percentage: 0,
};

const calculateBreakdown = (events: CostEvent[]): CostBreakdown => {
  const nano_cost_usd = events
    .filter((e) => e.model_tier === 'NANO')
    .reduce((sum, e) => sum + e.cost_usd, 0);
  
  const mid_cost_usd = events
    .filter((e) => e.model_tier === 'MID')
    .reduce((sum, e) => sum + e.cost_usd, 0);
  
  const frontier_cost_usd = events
    .filter((e) => e.model_tier === 'FRONTIER')
    .reduce((sum, e) => sum + e.cost_usd, 0);
  
  const total_cost_usd = nano_cost_usd + mid_cost_usd + frontier_cost_usd;
  
  return {
    nano_cost_usd,
    mid_cost_usd,
    frontier_cost_usd,
    total_cost_usd,
    nano_percentage: total_cost_usd > 0 ? (nano_cost_usd / total_cost_usd) * 100 : 0,
    mid_percentage: total_cost_usd > 0 ? (mid_cost_usd / total_cost_usd) * 100 : 0,
    frontier_percentage: total_cost_usd > 0 ? (frontier_cost_usd / total_cost_usd) * 100 : 0,
  };
};

export const useCostStore = create<CostStore>((set, get) => ({
  events: [],
  budget: null,
  breakdown: initialBreakdown,
  isConnected: false,
  lastEventTime: null,

  addEvent: (event) =>
    set((state) => {
      const events = [...state.events, event];
      return {
        events,
        breakdown: calculateBreakdown(events),
        lastEventTime: new Date().toISOString(),
      };
    }),

  updateBudget: (budget) =>
    set({
      budget,
      lastEventTime: new Date().toISOString(),
    }),

  setConnectionStatus: (isConnected) =>
    set({ isConnected }),

  reset: () =>
    set({
      events: [],
      budget: null,
      breakdown: initialBreakdown,
      isConnected: false,
      lastEventTime: null,
    }),

  // Computed getters
  getTotalCost: () => {
    return get().events.reduce((sum, e) => sum + e.cost_usd, 0);
  },

  getCostByGoal: (goal_id) => {
    return get()
      .events.filter((e) => e.goal_id === goal_id)
      .reduce((sum, e) => sum + e.cost_usd, 0);
  },

  getCostByAgent: (agent_id) => {
    return get()
      .events.filter((e) => e.agent_id === agent_id)
      .reduce((sum, e) => sum + e.cost_usd, 0);
  },

  getCostByModelTier: (model_tier) => {
    return get()
      .events.filter((e) => e.model_tier === model_tier)
      .reduce((sum, e) => sum + e.cost_usd, 0);
  },

  getRecentEvents: (limit) => {
    return get()
      .events.slice(-limit)
      .reverse();
  },
}));

// Made with Bob
