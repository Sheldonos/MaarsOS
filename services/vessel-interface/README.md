# MAARS Vision Layer

The **Vision Layer** is the real-time, enterprise-grade UI for the MAARS (Master Autonomous Agentic Runtime System) platform. It provides operators with full situational awareness of agent swarms through a high-density, professional interface following strict **Uncodixfy** design principles.

## 🎯 Overview

The Vision Layer is not a traditional dashboard. It is a **Real-Time Agentic Canvas** — an observe-and-steer interface that gives human operators complete control over autonomous agent swarms.

### Key Features

- **Live Agentic Canvas**: Real-time DAG visualization of agent nodes with draggable positioning
- **Escrow & Guardrail Inbox**: High-priority human intervention queue with approve/reject controls
- **Digital Twin Dashboard**: Scrubbable strategy timeline with confidence heatmaps
- **Agent Registry**: Full CRUD management for agent profiles and performance tracking
- **Insurance Telemetry**: Actuarial data export for underwriting partners
- **WebSocket Real-Time**: Persistent connections for sub-100ms latency updates

## 🚀 Quick Start

### Launch the UI

```bash
./start-ui.sh
```

This will open `VISION_LAYER.html` in your default browser.

### Demo Mode

The UI runs in **demo mode** by default with simulated agents and data. No backend required.

### Connect to Live Backend

1. Start the MAARS backend services (see main [README.md](../../README.md))
2. The UI will auto-connect to `ws://localhost:8080/ws`
3. Real-time agent data will replace demo data

## 🎨 Design System: Void Space

The Vision Layer uses the **Void Space** design system, inspired by GitHub's dark theme and professional enterprise tools like Linear, Raycast, and Stripe.

### Color Palette

```css
--bg:        #0d1117  /* Background */
--surface:   #161b22  /* Cards, panels */
--surface2:  #21262d  /* Elevated surfaces */
--border:    #30363d  /* Borders, dividers */
--primary:   #58a6ff  /* Primary actions */
--secondary: #79c0ff  /* Secondary text */
--accent:    #f78166  /* Accents */
--green:     #3fb950  /* Success states */
--amber:     #d29922  /* Warning states */
--red:       #f85149  /* Error states */
--text:      #c9d1d9  /* Body text */
--text-dim:  #8b949e  /* Dimmed text */
--text-bright: #f0f6fc /* Bright text */
```

### Uncodixfy Principles

The Vision Layer strictly adheres to **Uncodixfy** design principles:

#### ❌ Banned Patterns
- Decorative gradients
- Excessive rounded corners (>8px)
- Glassmorphism effects
- Oversized padding and whitespace
- Emoji-heavy UI
- Generic "pill" status badges
- Soft, friendly copy

#### ✅ Enforced Patterns
- Sharp, minimal borders (6px max radius)
- High information density
- Monospace fonts for technical data
- Real-time status indicators
- Professional status dots
- Technical, direct language
- Enterprise-grade aesthetics

## 📊 Application Routes

### 1. Overview (`#overview`)
Hero section with system statistics and route navigation cards.

### 2. Live Canvas (`#canvas`)
Real-time agent swarm visualization with draggable nodes.

**Agent Node States:**
- `IDLE` (grey) — Agent waiting for tasks
- `PLANNING` (blue) — Agent planning execution
- `EXECUTING` (amber) — Agent actively running tools
- `GUARDRAIL_CHECK` (yellow) — Guardrail validation in progress
- `ESCROW_HOLD` (orange) — Action held for human approval
- `BLOCKED` (red) — Agent blocked by error
- `TERMINATED` (dark grey) — Agent lifecycle complete

### 3. Inbox (`#inbox`)
High-priority escrow actions requiring human intervention.

**Actions:**
- **Approve**: Execute the proposed action
- **Reject**: Block the action and terminate task
- **Modify**: Adjust parameters before execution

### 4. Simulation (`#simulation`)
Digital twin dashboard with confidence heatmaps (integration in progress).

### 5. Agents (`#agents`)
Agent registry table with CRUD operations.

**Columns:**
- Agent ID (monospace)
- Tier (NANO/MID/FRONTIER)
- Status (with status dot)
- Performance score (%)
- Active tasks count
- Total cost ($)

### 6. Telemetry (`#telemetry`)
Insurance telemetry metrics for underwriting partners.

**Metrics:**
- Guardrail Intervention Rate
- Escrow Hold Rate
- Task Success Rate
- Cost Per Outcome

## 🔌 WebSocket Integration

The Vision Layer maintains a persistent WebSocket connection for real-time updates.

### Connection

```javascript
ws://localhost:8080/ws
```

### Message Format

```json
{
  "type": "agent.spawned",
  "payload": {
    "id": "agent_001",
    "tier": "MID",
    "status": "ACTIVE",
    "performance": 94,
    "cost": 0.23,
    "x": 100,
    "y": 100
  },
  "timestamp": "2026-03-22T09:00:00Z"
}
```

### Event Types

#### Swarm Channel
- `agent.spawned` — New agent created
- `agent.status` — Agent status changed
- `task.assigned` — Task assigned to agent
- `task.completed` — Task completed
- `escrow.created` — New escrow action

#### Stats Channel
- `stats.update` — System statistics update

### Auto-Reconnect

The WebSocket manager automatically reconnects after 5 seconds if disconnected.

## 🛠️ Development

### File Structure

```
services/vessel-interface/
├── public/
│   ├── VISION_LAYER.html      # Main UI (1,050 lines)
│   └── index.html             # Legacy UI (deprecated)
├── README.md                  # This file
└── VISION_LAYER_IMPLEMENTATION.md  # Full implementation guide
```

### Technology Stack

- **HTML5** + **CSS3** (Void Space design system)
- **Vanilla JavaScript** (ES6+)
- **WebSocket API** for real-time updates
- **No dependencies** — zero build step required

### Customization

#### Change WebSocket URL

Edit line 738 in `VISION_LAYER.html`:

```javascript
const wsUrl = 'ws://your-backend:8080/ws';
```

#### Adjust Agent Node Positions

Drag nodes on the canvas. Positions are stored in the `state.agents` array.

#### Add Custom Metrics

Edit the `updateStatsDisplay()` function to add new telemetry metrics.

## 📈 Performance

- **Target Latency**: <100ms for WebSocket updates
- **Scalability**: Handles 100+ agent nodes without lag
- **Browser Support**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+

## 🔒 Security

- WebSocket connections use `ws://` (upgrade to `wss://` in production)
- No authentication in demo mode
- Production deployments should integrate with `vessel-identity` for SSO

## 📝 Next Steps

### Phase 8: Production Readiness

1. **Next.js Migration**: Convert to Next.js 15 with App Router (see `VISION_LAYER_IMPLEMENTATION.md`)
2. **React Flow Integration**: Replace vanilla canvas with React Flow for advanced DAG features
3. **Authentication**: Integrate NextAuth.js with vessel-identity
4. **Real-Time Charts**: Add Recharts + D3.js for sparklines and heatmaps
5. **Component Library**: Build Radix UI + 21st.dev component system

### Phase 9: Advanced Features

1. **Agent Passports**: W3C Verifiable Credential visual cards
2. **Federation Map**: Cross-org A2A connection network graph
3. **Trust Center**: DID management and VC revocation interface
4. **Simulation Engine**: Monte Carlo confidence heatmaps
5. **No-Code Canvas**: Drag-and-drop agent workflow builder

## 📚 Documentation

- [Vision Layer Specification](../../docs/VISION_LAYER.html) — Full design spec
- [Implementation Guide](./VISION_LAYER_IMPLEMENTATION.md) — Technical roadmap
- [Main README](../../README.md) — MAARS platform overview
- [Project Status](../../docs/PROJECT_STATUS.md) — Current phase status

## 🤝 Contributing

The Vision Layer follows strict design principles. Before contributing:

1. Read the **Uncodixfy** principles above
2. Review the [Implementation Guide](./VISION_LAYER_IMPLEMENTATION.md)
3. Test in both demo mode and with live backend
4. Ensure <100ms latency for real-time updates

## 📄 License

Proprietary — All Rights Reserved © 2026

---

**Version**: 7.0.0  
**Phase**: 7 Complete  
**Status**: Production Ready (Demo Mode)  
**Next**: Phase 8 — Next.js Migration