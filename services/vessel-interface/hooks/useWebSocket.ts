import { useEffect, useRef } from 'react';
import { getWebSocketManager, WSEvent, ChannelName } from '@/lib/websocket/manager';
import {
  useAgentStore,
  useInboxStore,
  useCostStore,
  useSimulationStore,
} from '@/store';

/**
 * Custom hook to connect WebSocket channels to Zustand stores
 * Automatically handles connection lifecycle and event routing
 */
export function useWebSocket(token: string | null) {
  const wsManager = useRef(getWebSocketManager());
  const isInitialized = useRef(false);

  // Store actions
  const agentStore = useAgentStore();
  const inboxStore = useInboxStore();
  const costStore = useCostStore();
  const simulationStore = useSimulationStore();

  useEffect(() => {
    if (!token || isInitialized.current) return;

    // Set token
    wsManager.current.setToken(token);
    isInitialized.current = true;

    // Connect to swarm channel
    wsManager.current.connect('swarm', (event: WSEvent) => {
      handleSwarmEvent(event);
    });

    // Connect to guardrails channel
    wsManager.current.connect('guardrails', (event: WSEvent) => {
      handleGuardrailsEvent(event);
    });

    // Connect to costs channel
    wsManager.current.connect('costs', (event: WSEvent) => {
      handleCostsEvent(event);
    });

    // Connect to simulation channel
    wsManager.current.connect('simulation', (event: WSEvent) => {
      handleSimulationEvent(event);
    });

    // Update connection status
    const statusInterval = setInterval(() => {
      agentStore.setConnectionStatus(
        wsManager.current.getStatus('swarm') === 'connected'
      );
      inboxStore.setConnectionStatus(
        wsManager.current.getStatus('guardrails') === 'connected'
      );
      costStore.setConnectionStatus(
        wsManager.current.getStatus('costs') === 'connected'
      );
      simulationStore.setConnectionStatus(
        wsManager.current.getStatus('simulation') === 'connected'
      );
    }, 1000);

    // Cleanup on unmount
    return () => {
      clearInterval(statusInterval);
      wsManager.current.disconnectAll();
      isInitialized.current = false;
    };
  }, [token]);

  // Event handlers
  function handleSwarmEvent(event: WSEvent) {
    const { event_type, payload } = event;

    switch (event_type) {
      case 'agent.spawned':
        agentStore.addNode({
          id: payload.task_id as string,
          type: 'agent',
          position: { x: 0, y: 0 }, // Will be calculated by layout algorithm
          data: {
            task_id: payload.task_id as string,
            agent_id: payload.agent_id as string,
            model_tier: payload.model_tier as 'NANO' | 'MID' | 'FRONTIER',
            status: 'PENDING',
            cost_usd: 0,
            execution_time_ms: 0,
            task_name: payload.task_name as string,
            created_at: event.timestamp,
          },
        });
        break;

      case 'agent.assigned':
      case 'agent.executing':
        agentStore.updateNodeStatus(
          payload.task_id as string,
          event_type === 'agent.assigned' ? 'READY' : 'EXECUTING'
        );
        break;

      case 'agent.completed':
        agentStore.updateNodeStatus(payload.task_id as string, 'COMPLETED');
        if (payload.execution_time_ms) {
          agentStore.updateNodeExecutionTime(
            payload.task_id as string,
            payload.execution_time_ms as number
          );
        }
        break;

      case 'agent.failed':
        agentStore.updateNodeStatus(payload.task_id as string, 'FAILED');
        break;

      case 'task.status_changed':
        agentStore.updateNodeStatus(
          payload.task_id as string,
          payload.new_status as any
        );
        if (payload.reasoning_trace) {
          agentStore.setReasoningTrace(
            payload.task_id as string,
            payload.reasoning_trace as string
          );
        }
        break;

      case 'task.log_line':
        agentStore.appendNodeLog(
          payload.task_id as string,
          payload.line as string
        );
        break;

      case 'goal.completed':
        // Update metrics
        agentStore.updateMetrics({
          completed_tasks: (payload.completed_tasks as number) || 0,
          total_cost_usd: (payload.total_cost_usd as number) || 0,
        });
        break;

      default:
        console.log('[WebSocket] Unhandled swarm event:', event_type);
    }
  }

  function handleGuardrailsEvent(event: WSEvent) {
    const { event_type, payload } = event;

    switch (event_type) {
      case 'guardrail.violation':
      case 'inbox.card_created':
        inboxStore.addCard({
          card_id: payload.card_id as string,
          goal_id: payload.goal_id as string,
          task_id: payload.task_id as string,
          agent_id: payload.agent_id as string,
          trigger_type: payload.trigger_type as any,
          severity: payload.severity as any,
          title: payload.title as string,
          description: payload.description as string,
          proposed_action: payload.proposed_action as string,
          estimated_cost_usd: payload.estimated_cost_usd as number,
          status: 'PENDING',
          created_at: event.timestamp,
          expires_at: payload.expires_at as string,
        });

        // Also update agent node status to BLOCKED
        if (payload.task_id) {
          agentStore.updateNodeStatus(payload.task_id as string, 'BLOCKED');
        }
        break;

      case 'inbox.card_resolved':
        inboxStore.updateCardStatus(
          payload.card_id as string,
          payload.status as any
        );

        // Resume agent if approved
        if (payload.status === 'APPROVED' && payload.task_id) {
          agentStore.updateNodeStatus(payload.task_id as string, 'READY');
        }
        break;

      default:
        console.log('[WebSocket] Unhandled guardrails event:', event_type);
    }
  }

  function handleCostsEvent(event: WSEvent) {
    const { event_type, payload } = event;

    switch (event_type) {
      case 'cost.tracked':
        costStore.addEvent({
          event_id: event.event_id,
          tenant_id: event.tenant_id,
          goal_id: payload.goal_id as string,
          task_id: payload.task_id as string,
          agent_id: payload.agent_id as string,
          model_tier: payload.model_tier as any,
          cost_usd: payload.cost_usd as number,
          tokens_used: payload.tokens_used as number,
          timestamp: event.timestamp,
        });

        // Update agent node cost
        agentStore.updateNodeCost(
          payload.task_id as string,
          payload.cost_usd as number
        );
        break;

      case 'budget.threshold_warning':
      case 'budget.updated':
        costStore.updateBudget({
          tenant_id: event.tenant_id,
          total_budget_usd: payload.total_budget_usd as number,
          spent_usd: payload.spent_usd as number,
          remaining_usd: payload.remaining_usd as number,
          locked_usd: payload.locked_usd as number,
          available_usd: payload.available_usd as number,
          threshold_80_reached: payload.threshold_80_reached as boolean,
          threshold_90_reached: payload.threshold_90_reached as boolean,
          threshold_100_reached: payload.threshold_100_reached as boolean,
        });
        break;

      case 'escrow.locked':
      case 'escrow.released':
        // Update budget status
        if (payload.budget_status) {
          costStore.updateBudget(payload.budget_status as any);
        }
        break;

      default:
        console.log('[WebSocket] Unhandled costs event:', event_type);
    }
  }

  function handleSimulationEvent(event: WSEvent) {
    const { event_type, payload } = event;

    switch (event_type) {
      case 'simulation.progress':
        simulationStore.updateProgress({
          simulation_id: payload.simulation_id as string,
          current_run: payload.current_run as number,
          total_runs: payload.total_runs as number,
          progress_percentage: payload.progress_percentage as number,
          estimated_time_remaining_seconds: payload.estimated_time_remaining_seconds as number,
          current_phase: payload.current_phase as string,
        });
        break;

      case 'simulation.completed':
        simulationStore.completeSimulation(
          payload.simulation_id as string,
          {
            confidence_score: payload.confidence_score as number,
            predicted_cost_p50: payload.predicted_cost_p50 as number,
            predicted_cost_p90: payload.predicted_cost_p90 as number,
            predicted_cost_p99: payload.predicted_cost_p99 as number,
            predicted_duration_p50_minutes: payload.predicted_duration_p50_minutes as number,
            predicted_duration_p90_minutes: payload.predicted_duration_p90_minutes as number,
            predicted_duration_p99_minutes: payload.predicted_duration_p99_minutes as number,
            predicted_success_rate: payload.predicted_success_rate as number,
            risk_factors: payload.risk_factors as any,
            recommended_config: payload.recommended_config as any,
          }
        );
        break;

      case 'world_state.updated':
        // Handle world state updates for long-running projects
        console.log('[WebSocket] World state updated:', payload);
        break;

      default:
        console.log('[WebSocket] Unhandled simulation event:', event_type);
    }
  }

  return {
    isConnected: {
      swarm: wsManager.current.getStatus('swarm') === 'connected',
      guardrails: wsManager.current.getStatus('guardrails') === 'connected',
      costs: wsManager.current.getStatus('costs') === 'connected',
      simulation: wsManager.current.getStatus('simulation') === 'connected',
    },
  };
}

// Made with Bob
