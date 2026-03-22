# MAARS Implementation Priorities
## Actionable Roadmap to Market Readiness

**Version:** 1.0.0  
**Date:** March 22, 2026  
**Status:** 🔴 CRITICAL - Immediate Action Required  

---

## Executive Summary

Based on the comprehensive gap analysis, MAARS requires **11 weeks of focused work** to reach Minimum Viable Product (MVP) status and compete with Perplexity Computer. This document provides the exact sequence of implementation tasks.

**Current State:** 42% compliant with technical specification  
**Target State:** 100% Tier 1 features (market-ready MVP)  
**Timeline:** 11 weeks (Tier 1) → 20 weeks (full launch)

---

## Priority Matrix

| Priority | Feature | Impact | Effort | Status |
|----------|---------|--------|--------|--------|
| 🔴 P0 | Vision Layer Next.js Migration | CRITICAL | 4 weeks | ⏳ START NOW |
| 🔴 P0 | WebSocket Hub | CRITICAL | 2 weeks | Week 2 |
| 🔴 P0 | Slack Integration | CRITICAL | 3 weeks | Week 3 |
| 🔴 P0 | Inbox UI + Approval Flow | CRITICAL | 2 weeks | Week 5 |
| 🟠 P1 | Custom MCP Framework | HIGH | 2 weeks | Week 7 |
| 🟠 P1 | Simulation Engine | HIGH | 4 weeks | Week 9 |
| 🟠 P1 | Long-Running Context | HIGH | 3 weeks | Week 13 |
| 🟡 P2 | ROI Dashboard | MEDIUM | 1 week | Week 16 |
| 🟡 P2 | Merkle Audit Trail | MEDIUM | 1 week | Week 17 |

---

## Week-by-Week Implementation Plan

### Week 1: Vision Layer Foundation (Days 1-7)

#### Day 1-2: Project Setup
```bash
cd services/vessel-interface

# Initialize Next.js 15 with TypeScript and Tailwind
npx create-next-app@latest . \
  --typescript \
  --tailwind \
  --app \
  --no-src-dir \
  --import-alias "@/*"

# Install dependencies
npm install zustand @tanstack/react-query socket.io-client \
  @radix-ui/react-dialog @radix-ui/react-dropdown-menu \
  @radix-ui/react-select @radix-ui/react-tabs \
  reactflow recharts d3 next-auth date-fns clsx tailwind-merge
```

**Deliverables:**
- ✅ Next.js 15 project initialized
- ✅ Dependencies installed
- ✅ TypeScript configured

#### Day 3-4: Design System
**Files to Create:**
- `src/styles/void-space.css` - Color palette and design tokens
- `tailwind.config.js` - Tailwind configuration
- `src/styles/globals.css` - Global styles

**Deliverables:**
- ✅ Void Space design system implemented
- ✅ Tailwind configured with custom colors
- ✅ Typography and spacing tokens defined

#### Day 5-7: Core Layout
**Files to Create:**
- `src/app/layout.tsx` - Root layout
- `src/components/layout/TopNav.tsx` - Navigation bar
- `src/components/layout/Sidebar.tsx` - Sidebar navigation
- `src/components/layout/Footer.tsx` - Footer

**Deliverables:**
- ✅ Root layout with TopNav
- ✅ Responsive sidebar
- ✅ Route navigation working

---

### Week 2: WebSocket Infrastructure (Days 8-14)

#### Day 8-10: WebSocket Manager
**Files to Create:**
- `src/lib/websocket/manager.ts` - WebSocket connection manager
- `src/lib/websocket/swarm-channel.ts` - Swarm events handler
- `src/lib/websocket/guardrails-channel.ts` - Guardrail events handler
- `src/lib/websocket/costs-channel.ts` - Cost events handler
- `src/lib/websocket/simulation-channel.ts` - Simulation events handler

**Backend Work (vessel-gateway):**
- `internal/websocket/hub.go` - WebSocket hub implementation
- `internal/websocket/channels.go` - Channel handlers

**Deliverables:**
- ✅ WebSocket manager with auto-reconnect
- ✅ 4 persistent channels operational
- ✅ Event multiplexing working

#### Day 11-14: State Management
**Files to Create:**
- `src/store/agents.ts` - Zustand agent state
- `src/store/tasks.ts` - Zustand task state
- `src/store/websocket.ts` - Zustand WebSocket state
- `src/store/ui.ts` - Zustand UI state

**Deliverables:**
- ✅ Zustand stores configured
- ✅ Real-time state updates working
- ✅ WebSocket events updating UI state

---

### Week 3-5: Slack Integration (Days 15-35)

#### Week 3: vessel-integrations Service
**New Service Structure:**
```
services/vessel-integrations/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── database.py
│   ├── slack_handler.py      # Slack Event API handler
│   ├── slack_notifier.py     # Slack message sender
│   ├── mcp_registry.py       # MCP server registry
│   └── kafka_producer.py
├── main.py
├── requirements.txt
├── Dockerfile
└── README.md
```

**Deliverables:**
- ✅ vessel-integrations service scaffolded
- ✅ Slack SDK integrated
- ✅ Event API webhook endpoint

#### Week 4: Slack Bot Logic
**Files to Implement:**
- `app/slack_handler.py` - @maars mention handler
- `app/slack_notifier.py` - Thread update logic
- Kafka subscription for goal events

**Deliverables:**
- ✅ @maars mention creates goals
- ✅ Thread updates on milestones
- ✅ Workspace installation flow

#### Week 5: Inbox UI + Approval Flow
**Files to Create:**
- `src/app/inbox/page.tsx` - Inbox route
- `src/components/inbox/InboxCard.tsx` - Card component
- `src/components/inbox/EscrowAction.tsx` - Approval buttons

**Backend Work (vessel-gateway):**
- `POST /v1/inbox/{card_id}/approve`
- `POST /v1/inbox/{card_id}/reject`
- `POST /v1/inbox/{card_id}/defer`
- `GET /v1/inbox`

**Deliverables:**
- ✅ Inbox UI rendering cards
- ✅ Approve/reject/defer actions working
- ✅ Integration with vessel-orchestrator pause/resume

---

### Week 6: Canvas Route (Days 36-42)

**Files to Create:**
- `src/app/canvas/page.tsx` - Canvas route
- `src/components/canvas/AgentNode.tsx` - Custom React Flow node
- `src/components/canvas/ReasoningTrace.tsx` - Reasoning display
- `src/components/canvas/CanvasControls.tsx` - Canvas controls

**Deliverables:**
- ✅ React Flow canvas rendering
- ✅ Agent nodes updating in real-time
- ✅ Live log streaming in node panels
- ✅ Draggable node positioning

---

### Week 7-8: Custom MCP Framework (Days 43-56)

**Backend Work (vessel-integrations):**
- `app/mcp_registry.py` - MCP server CRUD
- `POST /v1/integrations/mcp/servers`
- `GET /v1/integrations/mcp/servers`
- `DELETE /v1/integrations/mcp/servers/{id}`
- `GET /v1/integrations/mcp/tools`

**Frontend Work:**
- `src/app/integrations/page.tsx` - MCP management UI
- `src/components/integrations/MCPServerForm.tsx`

**Deliverables:**
- ✅ MCP server registration API
- ✅ Tool discovery endpoint
- ✅ UI for managing custom connectors

---

### Week 9-12: Simulation Engine (Days 57-84)

**New Service Structure:**
```
services/vessel-simulation/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── initializer.py        # Initializer Agent
│   ├── abm_engine.py         # Mesa ABM simulation
│   ├── monte_carlo.py        # Monte Carlo runner
│   └── kafka_producer.py
├── main.py
├── requirements.txt
├── Dockerfile
└── README.md
```

**Deliverables:**
- ✅ vessel-simulation service operational
- ✅ ABM simulation with Mesa
- ✅ Monte Carlo cost/time prediction
- ✅ Simulation UI route

---

### Week 13-15: Long-Running Context (Days 85-105)

**Backend Work (vessel-simulation):**
- `app/initializer.py` - Context restoration logic
- GraphRAG query implementation
- Git history parser
- ProgressState save/load

**Deliverables:**
- ✅ Initializer Agent pattern working
- ✅ Context restoration from GraphRAG
- ✅ 6-month project resume capability

---

## Critical Success Factors

### 1. Team Allocation
- **Frontend Engineer:** Vision Layer (Weeks 1-6)
- **Backend Engineer:** WebSocket Hub + Slack (Weeks 2-5)
- **Full-Stack Engineer:** MCP + Simulation (Weeks 7-12)

### 2. Dependencies
- OpenAI API key (for embeddings)
- Slack workspace for testing
- AstraDB account (or local PostgreSQL)

### 3. Testing Strategy
- **Unit Tests:** Each service must have >80% coverage
- **Integration Tests:** End-to-end WebSocket flow
- **Load Tests:** 10,000 concurrent agents
- **User Acceptance:** 5-minute time-to-first-goal

---

## Milestone Checkpoints

### Checkpoint 1: Week 4 (Day 28)
**Criteria:**
- ✅ Vision Layer UI functional
- ✅ WebSocket real-time updates working
- ✅ Slack bot responding to @maars mentions

**Go/No-Go Decision:** If not met, pause and debug before proceeding.

### Checkpoint 2: Week 8 (Day 56)
**Criteria:**
- ✅ Inbox UI with approval flow working
- ✅ Canvas route with live agent nodes
- ✅ Custom MCP registration functional

**Go/No-Go Decision:** If not met, extend timeline by 2 weeks.

### Checkpoint 3: Week 11 (Day 77)
**Criteria:**
- ✅ All Tier 1 features complete
- ✅ MVP ready for beta testing
- ✅ Performance targets met

**Go/No-Go Decision:** Launch beta or continue to Tier 2.

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| WebSocket scaling issues | MEDIUM | HIGH | Load test early, implement connection pooling |
| Slack API rate limits | LOW | MEDIUM | Implement exponential backoff, batch updates |
| React Flow performance | MEDIUM | HIGH | Use WebGL renderer, virtualize large graphs |
| AstraDB migration complexity | LOW | HIGH | Keep PostgreSQL fallback, test schema early |

---

## Success Metrics

### Technical Metrics
- ✅ API latency P50 < 100ms
- ✅ WebSocket event delivery < 50ms
- ✅ Canvas renders 100+ nodes without lag
- ✅ Zero runaway cost events

### Business Metrics
- ✅ Time-to-first-goal < 5 minutes
- ✅ Slack-to-goal conversion > 60%
- ✅ Beta user retention > 80%
- ✅ NPS score > 50

---

## Next Actions (This Week)

### Monday (Day 1)
- [ ] Initialize Next.js 15 project
- [ ] Install all dependencies
- [ ] Set up TypeScript configuration

### Tuesday (Day 2)
- [ ] Create Void Space design system
- [ ] Configure Tailwind with custom colors
- [ ] Set up global styles

### Wednesday (Day 3)
- [ ] Implement root layout
- [ ] Create TopNav component
- [ ] Create Sidebar component

### Thursday (Day 4)
- [ ] Build base component library (Button, Card, Badge)
- [ ] Create StatusDot component
- [ ] Test responsive layout

### Friday (Day 5)
- [ ] Set up routing structure
- [ ] Create placeholder routes
- [ ] Deploy to Vercel for preview

---

## Conclusion

MAARS has the architectural foundation to dominate the enterprise agentic AI market. The gap is purely in user-facing features. By executing this 11-week plan with discipline, MAARS will be market-ready and positioned to outperform Perplexity Computer in every dimension that matters to enterprises.

**The clock starts now.**

---

**Document Version:** 1.0.0  
**Last Updated:** March 22, 2026  
**Owner:** MAARS Engineering Team  
**Status:** 🔴 **ACTIVE - EXECUTION PHASE**