import { create } from 'zustand';

export interface SimulationRun {
  simulation_id: string;
  goal_description: string;
  tenant_id: string;
  simulation_runs: number;
  time_horizon_hours: number;
  confidence_score: number;
  predicted_cost_p50: number;
  predicted_cost_p90: number;
  predicted_cost_p99: number;
  predicted_duration_p50_minutes: number;
  predicted_duration_p90_minutes: number;
  predicted_duration_p99_minutes: number;
  predicted_success_rate: number;
  risk_factors: RiskFactor[];
  recommended_config: RecommendedConfig;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  progress_percentage: number;
  created_at: string;
  completed_at?: string;
}

export interface RiskFactor {
  factor: string;
  probability: number;
  impact: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  mitigation?: string;
}

export interface RecommendedConfig {
  liability_cap_usd: number;
  timeout_minutes: number;
  max_retries: number;
  suggested_model_tier: 'NANO' | 'MID' | 'FRONTIER';
}

export interface SimulationProgress {
  simulation_id: string;
  current_run: number;
  total_runs: number;
  progress_percentage: number;
  estimated_time_remaining_seconds: number;
  current_phase: string;
}

interface SimulationStore {
  // Simulations
  simulations: SimulationRun[];
  currentSimulation: SimulationRun | null;
  
  // Progress tracking
  progress: SimulationProgress | null;
  
  // Connection status
  isConnected: boolean;
  lastEventTime: string | null;
  
  // Actions
  addSimulation: (simulation: SimulationRun) => void;
  updateSimulation: (simulation_id: string, updates: Partial<SimulationRun>) => void;
  setCurrentSimulation: (simulation: SimulationRun | null) => void;
  updateProgress: (progress: SimulationProgress) => void;
  completeSimulation: (simulation_id: string, results: Partial<SimulationRun>) => void;
  setConnectionStatus: (isConnected: boolean) => void;
  reset: () => void;
  
  // Computed getters
  getSimulationById: (simulation_id: string) => SimulationRun | undefined;
  getRecentSimulations: (limit: number) => SimulationRun[];
  getCompletedSimulations: () => SimulationRun[];
  getRunningSimulations: () => SimulationRun[];
}

export const useSimulationStore = create<SimulationStore>((set, get) => ({
  simulations: [],
  currentSimulation: null,
  progress: null,
  isConnected: false,
  lastEventTime: null,

  addSimulation: (simulation) =>
    set((state) => ({
      simulations: [...state.simulations, simulation],
      currentSimulation: simulation,
      lastEventTime: new Date().toISOString(),
    })),

  updateSimulation: (simulation_id, updates) =>
    set((state) => {
      const simulations = state.simulations.map((s) =>
        s.simulation_id === simulation_id
          ? { ...s, ...updates }
          : s
      );
      
      const currentSimulation =
        state.currentSimulation?.simulation_id === simulation_id
          ? { ...state.currentSimulation, ...updates }
          : state.currentSimulation;

      return {
        simulations,
        currentSimulation,
        lastEventTime: new Date().toISOString(),
      };
    }),

  setCurrentSimulation: (simulation) =>
    set({
      currentSimulation: simulation,
    }),

  updateProgress: (progress) =>
    set((state) => {
      // Update the simulation's progress percentage
      const simulations = state.simulations.map((s) =>
        s.simulation_id === progress.simulation_id
          ? { ...s, progress_percentage: progress.progress_percentage }
          : s
      );

      const currentSimulation =
        state.currentSimulation?.simulation_id === progress.simulation_id
          ? { ...state.currentSimulation, progress_percentage: progress.progress_percentage }
          : state.currentSimulation;

      return {
        simulations,
        currentSimulation,
        progress,
        lastEventTime: new Date().toISOString(),
      };
    }),

  completeSimulation: (simulation_id, results) =>
    set((state) => {
      const simulations = state.simulations.map((s) =>
        s.simulation_id === simulation_id
          ? {
              ...s,
              ...results,
              status: 'COMPLETED' as const,
              progress_percentage: 100,
              completed_at: new Date().toISOString(),
            }
          : s
      );

      const currentSimulation =
        state.currentSimulation?.simulation_id === simulation_id
          ? {
              ...state.currentSimulation,
              ...results,
              status: 'COMPLETED' as const,
              progress_percentage: 100,
              completed_at: new Date().toISOString(),
            }
          : state.currentSimulation;

      return {
        simulations,
        currentSimulation,
        progress: null,
        lastEventTime: new Date().toISOString(),
      };
    }),

  setConnectionStatus: (isConnected) =>
    set({ isConnected }),

  reset: () =>
    set({
      simulations: [],
      currentSimulation: null,
      progress: null,
      isConnected: false,
      lastEventTime: null,
    }),

  // Computed getters
  getSimulationById: (simulation_id) => {
    return get().simulations.find((s) => s.simulation_id === simulation_id);
  },

  getRecentSimulations: (limit) => {
    return get()
      .simulations.slice(-limit)
      .reverse();
  },

  getCompletedSimulations: () => {
    return get().simulations.filter((s) => s.status === 'COMPLETED');
  },

  getRunningSimulations: () => {
    return get().simulations.filter((s) => s.status === 'RUNNING');
  },
}));

// Made with Bob
