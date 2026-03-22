'use client';

import { useCallback, useEffect, useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Panel,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  ConnectionMode,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { AgentNode } from '@/components/canvas/AgentNode';
import { useAgentStore } from '@/store/agents';
import { getLayoutedElements } from '@/lib/layout/dagre';
import { Card } from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';

// Define custom node types
const nodeTypes = {
  agentNode: AgentNode,
};

/**
 * Canvas View Component
 * Displays the agent DAG with real-time updates from WebSocket.
 */
export default function CanvasView() {
  const { nodes: storeNodes, edges: storeEdges, metrics } = useAgentStore();
  
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Apply Dagre layout when store nodes/edges change
  useEffect(() => {
    if (storeNodes.length > 0) {
      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
        storeNodes,
        storeEdges,
        {
          direction: 'TB',
          nodeWidth: 320,
          nodeHeight: 250,
          rankSep: 120,
          nodeSep: 100,
        }
      );
      
      setNodes(layoutedNodes);
      setEdges(layoutedEdges);
    }
  }, [storeNodes, storeEdges, setNodes, setEdges]);

  // Fit view when nodes change
  const onInit = useCallback((reactFlowInstance: any) => {
    reactFlowInstance.fitView({ padding: 0.2 });
  }, []);

  // Calculate statistics
  const stats = useMemo(() => {
    const total = storeNodes.length;
    const completed = storeNodes.filter(n => n.data.status === 'COMPLETED').length;
    const executing = storeNodes.filter(n => n.data.status === 'EXECUTING').length;
    const failed = storeNodes.filter(n => n.data.status === 'FAILED').length;
    const pending = storeNodes.filter(n => n.data.status === 'PENDING' || n.data.status === 'READY').length;
    
    return { total, completed, executing, failed, pending };
  }, [storeNodes]);

  return (
    <div className="h-full w-full relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onInit={onInit}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Strict}
        fitView
        minZoom={0.1}
        maxZoom={2}
        defaultEdgeOptions={{
          type: 'smoothstep',
          animated: true,
          style: { stroke: '#3b82f6', strokeWidth: 2 },
        }}
      >
        <Background color="#1a1a2e" gap={16} />
        <Controls className="bg-void-800 border-void-600" />
        <MiniMap
          className="bg-void-800 border-void-600"
          nodeColor={(node) => {
            const status = (node.data as any).status;
            switch (status) {
              case 'COMPLETED': return '#10b981';
              case 'EXECUTING': return '#f59e0b';
              case 'FAILED': return '#ef4444';
              case 'BLOCKED': return '#f97316';
              default: return '#6b7280';
            }
          }}
        />
        
        {/* Stats Panel */}
        <Panel position="top-right" className="space-y-2">
          <Card className="bg-void-800/95 backdrop-blur-sm border-void-600 p-4 min-w-[280px]">
            <h3 className="text-sm font-semibold text-void-50 mb-3">Agent DAG Statistics</h3>
            
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-xs text-void-400">Total Tasks:</span>
                <Badge variant="default">{stats.total}</Badge>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-xs text-void-400">Completed:</span>
                <Badge variant="success">{stats.completed}</Badge>
              </div>
              
              {stats.executing > 0 && (
                <div className="flex justify-between items-center">
                  <span className="text-xs text-void-400">Executing:</span>
                  <Badge variant="warning">{stats.executing}</Badge>
                </div>
              )}
              
              {stats.failed > 0 && (
                <div className="flex justify-between items-center">
                  <span className="text-xs text-void-400">Failed:</span>
                  <Badge variant="danger">{stats.failed}</Badge>
                </div>
              )}
              
              {stats.pending > 0 && (
                <div className="flex justify-between items-center">
                  <span className="text-xs text-void-400">Pending:</span>
                  <Badge variant="info">{stats.pending}</Badge>
                </div>
              )}
            </div>
            
            <div className="mt-4 pt-4 border-t border-void-600 space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-xs text-void-400">Total Cost:</span>
                <span className="text-sm font-mono text-accent-green">
                  ${metrics.total_cost_usd.toFixed(4)}
                </span>
              </div>
              
              {metrics.avg_execution_time_ms > 0 && (
                <div className="flex justify-between items-center">
                  <span className="text-xs text-void-400">Avg Time:</span>
                  <span className="text-sm font-mono text-void-200">
                    {metrics.avg_execution_time_ms < 1000
                      ? `${metrics.avg_execution_time_ms.toFixed(0)}ms`
                      : `${(metrics.avg_execution_time_ms / 1000).toFixed(2)}s`}
                  </span>
                </div>
              )}
            </div>
          </Card>
        </Panel>

        {/* Empty State */}
        {storeNodes.length === 0 && (
          <Panel position="top-center" className="mt-20">
            <Card className="bg-void-800/95 backdrop-blur-sm border-void-600 p-8 text-center max-w-md">
              <div className="text-void-400 mb-4">
                <svg
                  className="w-16 h-16 mx-auto mb-4 opacity-50"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <h3 className="text-lg font-semibold text-void-200 mb-2">
                  No Active Goals
                </h3>
                <p className="text-sm text-void-400">
                  Submit a goal to see the agent DAG visualization here.
                  <br />
                  Try using the Slack bot: <code className="text-accent-blue">@maars [your goal]</code>
                </p>
              </div>
            </Card>
          </Panel>
        )}
      </ReactFlow>
    </div>
  );
}

// Made with Bob
