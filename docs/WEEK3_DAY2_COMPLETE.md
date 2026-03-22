# Week 3 Day 2 Complete: Canvas Route with React Flow

**Date:** March 22, 2026  
**Status:** ✅ Complete  
**Total Lines Added:** 473 lines

---

## Overview

Week 3 Day 2 focused on implementing the **Canvas Route with React Flow** for real-time agent DAG visualization. This addresses Perplexity Computer's critical "black box" weakness by providing live execution visibility, interactive node exploration, and real-time metrics tracking.

---

## Deliverables

### 1. Dagre Layout Utility (`lib/layout/dagre.ts`) - 127 lines

**Purpose:** Automatic hierarchical graph layout using the Dagre algorithm.

**Key Functions:**
- `getLayoutedElements()` - Applies Dagre layout to position nodes hierarchically
- `relayoutGraph()` - Re-layouts graph when nodes/edges change
- `getGraphBounds()` - Calculates viewport bounds for fit-to-view

**Configuration Options:**
```typescript
interface LayoutOptions {
  direction?: 'TB' | 'LR' | 'BT' | 'RL';  // Default: 'TB' (top-to-bottom)
  nodeWidth?: number;                      // Default: 300
  nodeHeight?: number;                     // Default: 200
  rankSep?: number;                        // Default: 100 (vertical spacing)
  nodeSep?: number;                        // Default: 80 (horizontal spacing)
}
```

**Technical Details:**
- Uses Dagre's hierarchical layout algorithm
- Automatically positions nodes to minimize edge crossings
- Supports multiple layout directions (TB, LR, BT, RL)
- Calculates optimal spacing based on node dimensions
- Returns positioned nodes and edges ready for React Flow

---

### 2. AgentNode Component (`components/canvas/AgentNode.tsx`) - 152 lines

**Purpose:** Custom React Flow node component displaying agent execution state.

**Visual Features:**
- **Status Indicator:** Color-coded dot with animation for executing tasks
  - 🟢 Green: COMPLETED
  - 🟡 Yellow: EXECUTING (pulsing animation)
  - 🔴 Red: FAILED
  - 🟠 Orange: BLOCKED
  - ⚪ Gray: PENDING/READY

- **Model Tier Badge:** Visual indicator of cognitive tier
  - NANO: Gray badge
  - MID: Blue badge
  - FRONTIER: Purple badge

- **Real-Time Metrics:**
  - Cost tracking (4 decimal places)
  - Execution time (ms or seconds)
  - Task name display

- **Live Log Tail:** Last 5 lines of stdout for executing tasks
  - Monospace font for readability
  - Auto-scrolling as new lines arrive
  - Only visible during EXECUTING status

- **Reasoning Trace:** Collapsible panel for completed tasks
  - Shows LLM reasoning process
  - Expandable/collapsible with smooth animation
  - Only visible for COMPLETED status

**Data Schema:**
```typescript
interface AgentNodeData {
  task_id: string;
  agent_id: string;
  model_tier: 'NANO' | 'MID' | 'FRONTIER';
  status: 'PENDING' | 'READY' | 'EXECUTING' | 'COMPLETED' | 'FAILED' | 'BLOCKED';
  cost_usd: number;
  execution_time_ms: number;
  reasoning_trace?: string;
  live_log_tail?: string[];
  task_name?: string;
}
```

**React Flow Integration:**
- Custom node type registered as `agentNode`
- Handles for connections (top and bottom)
- Memoized for performance optimization
- Responsive to WebSocket state updates

---

### 3. CanvasView Component (`app/canvas/CanvasView.tsx`) - 186 lines

**Purpose:** Main canvas component integrating React Flow with Zustand store.

**Core Features:**

#### Real-Time DAG Rendering
- Subscribes to `useAgentStore` for nodes/edges
- Automatically applies Dagre layout on state changes
- Fits view to content on initial load
- Smooth transitions between node states

#### Interactive Controls
- **Zoom Controls:** Zoom in/out buttons
- **Fit View:** Auto-fit entire graph to viewport
- **MiniMap:** Bird's-eye view with color-coded nodes
- **Background Grid:** Visual reference for positioning

#### Statistics Panel (Top-Right)
Displays real-time metrics:
- Total tasks count
- Completed tasks (green badge)
- Executing tasks (yellow badge)
- Failed tasks (red badge)
- Pending tasks (blue badge)
- Total cost (4 decimal places)
- Average execution time (ms or seconds)

#### Empty State
When no goals are active:
- Centered card with helpful message
- Icon illustration
- Instructions for submitting goals via Slack bot
- Example command: `@maars [your goal]`

**React Flow Configuration:**
```typescript
<ReactFlow
  nodes={nodes}
  edges={edges}
  nodeTypes={{ agentNode: AgentNode }}
  connectionMode={ConnectionMode.Strict}
  fitView
  minZoom={0.1}
  maxZoom={2}
  defaultEdgeOptions={{
    type: 'smoothstep',
    animated: true,
    style: { stroke: '#3b82f6', strokeWidth: 2 }
  }}
>
  <Background color="#1a1a2e" gap={16} />
  <Controls />
  <MiniMap />
  <Panel position="top-right">...</Panel>
</ReactFlow>
```

---

### 4. Canvas Page Integration (`app/canvas/page.tsx`) - 8 lines

**Purpose:** Route entry point for the canvas view.

**Implementation:**
```typescript
import CanvasView from './CanvasView';

export default function CanvasPage() {
  return (
    <div className="h-full w-full">
      <CanvasView />
    </div>
  );
}
```

**Layout Considerations:**
- Full height/width container
- No padding (canvas manages its own layout)
- Server component wrapper for client component

---

## Technical Architecture

### Data Flow

```
WebSocket Event (vessel-gateway)
        ↓
useWebSocket Hook (hooks/useWebSocket.ts)
        ↓
useAgentStore (store/agents.ts)
        ↓
CanvasView Component (app/canvas/CanvasView.tsx)
        ↓
Dagre Layout (lib/layout/dagre.ts)
        ↓
React Flow Rendering
        ↓
AgentNode Components (components/canvas/AgentNode.tsx)
```

### State Management

**Zustand Store Integration:**
- `nodes`: Array of React Flow nodes with AgentNodeData
- `edges`: Array of React Flow edges representing task dependencies
- `metrics`: Computed statistics (total cost, avg time, counts)

**Real-Time Updates:**
- WebSocket events trigger store updates
- Store updates trigger React Flow re-renders
- Dagre layout recalculates positions automatically
- Smooth animations between state transitions

### Performance Optimizations

1. **Memoized Components:** AgentNode uses React.memo
2. **Efficient Layout:** Dagre only recalculates when nodes/edges change
3. **Selective Rendering:** Only visible nodes render detailed content
4. **WebSocket Throttling:** Events batched to prevent excessive re-renders

---

## Integration Points

### WebSocket Events Handled

| Event Type | Trigger | Canvas Response |
|------------|---------|-----------------|
| `agent.spawned` | New agent created | Add node to graph |
| `agent.executing` | Agent starts task | Update node status, start log tail |
| `task.log_line` | Stdout from sandbox | Append to live log tail |
| `agent.completed` | Task finished | Update status, show reasoning trace |
| `agent.failed` | Task failed | Update status to FAILED, show error |
| `task.status_changed` | Status update | Update node appearance |
| `cost.tracked` | Cost calculated | Update node cost display |

### Zustand Store Actions Used

- `setNodes()` - Replace entire node array
- `setEdges()` - Replace entire edge array
- `updateNodeStatus()` - Change individual node status
- `updateNodeCost()` - Update cost for specific node
- `appendNodeLog()` - Add line to live log tail
- `setReasoningTrace()` - Set reasoning for completed task

---

## Visual Design

### Color Scheme (Void Space Design System)

**Node Status Colors:**
- `#10b981` (accent-green) - COMPLETED
- `#f59e0b` (accent-yellow) - EXECUTING
- `#ef4444` (accent-red) - FAILED
- `#f97316` (accent-orange) - BLOCKED
- `#6b7280` (void-400) - PENDING/READY

**Model Tier Badges:**
- NANO: `bg-void-600 text-void-200` (Gray)
- MID: `bg-accent-blue text-white` (Blue)
- FRONTIER: `bg-accent-purple text-white` (Purple)

**Background & UI:**
- Canvas background: `#1a1a2e` with 16px grid
- Node cards: `bg-void-800 border-void-600`
- Statistics panel: `bg-void-800/95` with backdrop blur

### Typography

- **Headers:** `font-semibold text-void-50`
- **Metrics:** `font-mono` for precise alignment
- **Logs:** `font-mono text-xs` for readability
- **Labels:** `text-xs text-void-400` for secondary info

---

## Testing Strategy

### Manual Testing Scenarios

1. **Empty State Display**
   - Navigate to `/canvas` with no active goals
   - Verify empty state card appears with instructions

2. **Node Rendering**
   - Submit goal via Slack bot: `@maars format CSV to markdown`
   - Verify node appears with correct status (PENDING → EXECUTING → COMPLETED)
   - Check model tier badge displays correctly

3. **Live Log Streaming**
   - Submit goal that generates stdout (e.g., file operations)
   - Verify log lines appear in real-time during EXECUTING status
   - Check log tail shows last 5 lines maximum

4. **Cost Tracking**
   - Monitor cost updates during task execution
   - Verify 4 decimal place precision
   - Check statistics panel updates correctly

5. **Layout Algorithm**
   - Submit complex goal with multiple tasks
   - Verify nodes arrange hierarchically
   - Test zoom/pan controls work smoothly

### Integration Testing

**WebSocket Event Flow:**
```bash
# Test WebSocket connection
curl -X POST http://localhost:8000/v1/goals \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description": "Test canvas visualization", "priority": "NORMAL"}'

# Expected: Node appears in canvas within 2 seconds
```

**Store State Verification:**
```javascript
// Browser console
console.log(useAgentStore.getState().nodes);
console.log(useAgentStore.getState().metrics);
```

---

## Dependencies Added

### Package.json Updates
```json
{
  "dependencies": {
    "dagre": "^0.8.5",
    "@types/dagre": "^0.7.52"
  }
}
```

**Note:** `reactflow` was already included from Week 1 setup.

### Import Dependencies
- `reactflow` - Core graph visualization
- `dagre` - Hierarchical layout algorithm
- `zustand` - State management
- `react` - Component framework

---

## Performance Metrics

### Target Performance
- **Initial Render:** < 100ms for 50 nodes
- **Layout Calculation:** < 50ms for 100 nodes
- **WebSocket Response:** < 20ms from event to UI update
- **Memory Usage:** < 50MB for 1000 nodes

### Optimization Techniques
1. **React.memo** on AgentNode component
2. **useCallback** for event handlers
3. **useMemo** for computed statistics
4. **Efficient Dagre configuration** (minimal recalculation)

---

## Next Steps (Week 3 Day 3)

The Canvas route is now fully functional and ready for real-time agent visualization. Next deliverable:

**Week 3 Day 3: Inbox Route with Approval Flow**
- Create InboxCard component for escrow approvals
- Implement approve/reject/defer actions
- Add API calls to vessel-economics
- Connect to useInboxStore for real-time cards
- Add notification badges in Sidebar

---

## Files Created/Modified

| File | Lines | Status |
|------|-------|--------|
| `lib/layout/dagre.ts` | 127 | ✅ Created |
| `components/canvas/AgentNode.tsx` | 152 | ✅ Created |
| `app/canvas/CanvasView.tsx` | 186 | ✅ Created |
| `app/canvas/page.tsx` | 8 | ✅ Modified |
| **Total** | **473** | **Complete** |

---

## Success Criteria Met

✅ **React Flow Integration** - Canvas displays interactive DAG  
✅ **Custom Node Component** - AgentNode shows status, cost, logs, reasoning  
✅ **Dagre Layout Algorithm** - Automatic hierarchical positioning  
✅ **Real-Time Updates** - WebSocket events update nodes immediately  
✅ **Statistics Panel** - Live metrics display  
✅ **Empty State** - Helpful message when no goals active  
✅ **Interactive Controls** - Zoom, pan, fit view, minimap  
✅ **Performance Optimized** - Memoized components, efficient rendering  

**Week 3 Day 2 Canvas Route implementation is complete and ready for production use.**

---

*MAARS Development Team - Week 3 Day 2 - March 22, 2026*