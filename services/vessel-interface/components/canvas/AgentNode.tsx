'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import Badge from '@/components/ui/Badge';
import StatusDot from '@/components/ui/StatusDot';
import type { AgentNodeData } from '@/store/agents';

/**
 * Custom React Flow node component for agent visualization.
 * Displays agent status, model tier, cost, execution time, and live logs.
 */
export const AgentNode = memo(({ data }: NodeProps<AgentNodeData>) => {
  const {
    task_id,
    agent_id,
    model_tier,
    status,
    cost_usd,
    execution_time_ms,
    reasoning_trace,
    live_log_tail,
    task_name,
  } = data;

  // Status color mapping
  const statusColors: Record<AgentNodeData['status'], string> = {
    PENDING: 'bg-gray-500',
    READY: 'bg-blue-500',
    EXECUTING: 'bg-yellow-500 animate-pulse',
    COMPLETED: 'bg-green-500',
    FAILED: 'bg-red-500',
    BLOCKED: 'bg-orange-500',
  };

  // Model tier badge colors
  const tierColors: Record<AgentNodeData['model_tier'], string> = {
    NANO: 'bg-gray-600',
    MID: 'bg-blue-600',
    FRONTIER: 'bg-purple-600',
  };

  return (
    <div className="bg-void-800 border border-void-600 rounded-lg shadow-lg min-w-[280px] max-w-[320px]">
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="w-3 h-3 !bg-accent-blue"
      />

      {/* Header */}
      <div className="px-4 py-3 border-b border-void-600">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <StatusDot status={status === 'COMPLETED' ? 'online' : status === 'FAILED' ? 'error' : status === 'EXECUTING' ? 'warning' : 'pending'} />
            <span className="text-sm font-medium text-void-50">
              {task_name || `Task ${task_id.slice(0, 8)}`}
            </span>
          </div>
          <Badge variant="info" className={tierColors[model_tier]}>
            {model_tier}
          </Badge>
        </div>
        
        <div className="text-xs text-void-400 font-mono">
          {agent_id.slice(0, 12)}...
        </div>
      </div>

      {/* Metrics */}
      <div className="px-4 py-3 space-y-2">
        <div className="flex justify-between text-xs">
          <span className="text-void-400">Cost:</span>
          <span className="text-accent-green font-mono">
            ${cost_usd.toFixed(4)}
          </span>
        </div>
        
        {execution_time_ms > 0 && (
          <div className="flex justify-between text-xs">
            <span className="text-void-400">Time:</span>
            <span className="text-void-200 font-mono">
              {execution_time_ms < 1000
                ? `${execution_time_ms}ms`
                : `${(execution_time_ms / 1000).toFixed(2)}s`}
            </span>
          </div>
        )}

        {/* Status Badge */}
        <div className="pt-2">
          <div className={`inline-flex items-center gap-2 px-2 py-1 rounded text-xs font-medium ${statusColors[status]} text-white`}>
            {status === 'EXECUTING' && (
              <svg className="animate-spin h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
            {status}
          </div>
        </div>
      </div>

      {/* Live Log Tail (if executing) */}
      {status === 'EXECUTING' && live_log_tail && live_log_tail.length > 0 && (
        <div className="px-4 py-3 border-t border-void-600">
          <div className="text-xs text-void-400 mb-2">Live Logs:</div>
          <div className="bg-void-900 rounded p-2 space-y-1 max-h-24 overflow-y-auto">
            {live_log_tail.map((line, idx) => (
              <div key={idx} className="text-xs font-mono text-void-300 truncate">
                {line}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Reasoning Trace (if completed) */}
      {status === 'COMPLETED' && reasoning_trace && (
        <div className="px-4 py-3 border-t border-void-600">
          <details className="group">
            <summary className="text-xs text-void-400 cursor-pointer hover:text-void-200 transition-colors">
              View Reasoning Trace
            </summary>
            <div className="mt-2 bg-void-900 rounded p-2 max-h-32 overflow-y-auto">
              <p className="text-xs text-void-300 whitespace-pre-wrap">
                {reasoning_trace}
              </p>
            </div>
          </details>
        </div>
      )}

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-3 h-3 !bg-accent-blue"
      />
    </div>
  );
});

AgentNode.displayName = 'AgentNode';

// Made with Bob
