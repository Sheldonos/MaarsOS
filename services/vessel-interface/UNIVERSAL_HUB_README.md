# MAARS Universal Hub — Technical Documentation

## Overview

The **Universal Hub** is a drag-and-drop command center for deploying and managing 27+ autonomous enterprise use cases across 5 domain clusters. It provides a visual, node-based canvas where operators can instantiate pre-configured templates, wire them into the MAARS execution engine, and monitor real-time execution.

**File:** `services/vessel-interface/public/UNIVERSAL_HUB.html`  
**Version:** 8.0.0-alpha  
**Phase:** 8 Preview  
**Status:** Production-Ready Prototype

---

## Architecture

### Design System: Void Space (Strict Uncodixfy Compliance)

**Color Palette:**
```css
--bg:        #0d1117  /* Background */
--surface:   #161b22  /* Cards, panels */
--surface2:  #21262d  /* Elevated surfaces */
--border:    #30363d  /* Borders, dividers */
--primary:   #58a6ff  /* Primary actions */
--secondary: #79c0ff  /* Secondary text */
--accent:    #f78166  /* Accents */
--green:     #3fb950  /* Success states */
--amber:     #d29922  /* Warning/simulating states */
--red:       #f85149  /* Error/blocked states */
--text:      #c9d1d9  /* Body text */
--text-dim:  #8b949e  /* Dimmed text */
--text-bright: #f0f6fc /* Bright text */
```

**Design Principles:**
- ✅ NO glassmorphism, NO soft gradients, NO oversized rounded corners
- ✅ Sharp 1px borders, 6px max border-radius
- ✅ High information density, Bloomberg-terminal aesthetics
- ✅ Monospace fonts for technical data
- ✅ Professional status indicators (dots, not pills)

---

## Three-Pane Layout

### 1. Left Sidebar (300px) — Use Case Library

**Purpose:** Browse and drag 27+ pre-configured use case templates.

**Structure:**
- **Accordion Menu:** 5 domain clusters (Cinematic, Trading, E-Commerce, Research, Operations)
- **Template Cards:** Draggable cards with:
  - Name (e.g., "XRP Scalp Bot")
  - Description (e.g., "High-frequency XRP trading with risk management")
  - Subsystem tags (e.g., `vessel-swarm`, `vessel-economics`)

**Interaction:**
- Click accordion header to expand/collapse domain
- Drag template card onto canvas to instantiate

**Data Structure:**
```javascript
{
  "Algorithmic Trading": [
    {
      id: "xrp-scalp-bot",
      name: "XRP Scalp Bot",
      description: "High-frequency XRP trading with risk management",
      subsystems: ["vessel-swarm", "vessel-economics", "vessel-observability", "vessel-simulation"],
      personas: ["Risk Manager", "Trade Executor", "Market Analyst"],
      parameters: {
        maxDrawdown: { type: "number", default: 5 },
        escrowLimit: { type: "number", default: 10000 },
        assetPair: { type: "select", options: ["XRP/USD", "XRP/BTC", "XRP/ETH"], default: "XRP/USD" }
      }
    }
  ]
}
```

---

### 2. Center Canvas (Infinite Pan/Zoom) — Node-Based Execution Graph

**Purpose:** Visual representation of deployed use cases as draggable HubNodes.

**HubNode Anatomy:**
```
┌─────────────────────────────────────┐
│ XRP Scalp Bot            [SIMULATING]│ ← Header (Title + Status Pill)
├─────────────────────────────────────┤
│ ┌─────────┐ ┌─────────┐            │
│ │ swarm   │ │economics│            │ ← Subsystem Grid (2 columns)
│ └─────────┘ └─────────┘            │
│ ┌─────────┐ ┌─────────┐            │
│ │observ.  │ │simulat. │            │
│ └─────────┘ └─────────┘            │
├─────────────────────────────────────┤
│ ● Inputs          Outputs ●        │ ← Input/Output Handles
└─────────────────────────────────────┘
```

**Node States:**
- `idle` (grey border) — Waiting for configuration
- `simulating` (amber border, pulsing) — Running digital twin backtest
- `executing` (green border) — Live execution in progress
- `blocked` (red border) — Error or guardrail intervention

**Interactions:**
- **Drag:** Reposition nodes on canvas
- **Click:** Select node → opens Configuration Drawer

---

### 3. Right Drawer (400px, slide-out) — Configuration Panel

**Purpose:** Configure selected HubNode parameters, swarm topology, and advanced settings.

**Tabs:**

#### Tab 1: Parameters
Dynamic form rendering based on use case template:
- **Text inputs:** `niche`, `industry`, `domain`
- **Number inputs:** `budget`, `maxDrawdown`, `escrowLimit`
- **Select dropdowns:** `genre`, `assetPair`, `riskTolerance`

#### Tab 2: Swarm Topology
Visual representation of agent personas in the swarm:
```
┌─────────────────────────────────────┐
│ Risk Manager                  [Edit]│
│ Agent Persona                       │
├─────────────────────────────────────┤
│ Trade Executor                [Edit]│
│ Agent Persona                       │
├─────────────────────────────────────┤
│ Market Analyst                [Edit]│
│ Agent Persona                       │
└─────────────────────────────────────┘
```

**Interaction:** Click `[Edit]` to open Monaco Editor for `instructions.md` and `manifesto.md` (mocked in prototype, real in production via `PUT /v1/swarm/personas/{id}`).

#### Tab 3: Advanced
- **Escrow Liability Cap:** Maximum cost before requiring human approval
- **Guardrail Sensitivity:** Low/Medium/High
- **Custom Instructions:** Freeform textarea for additional swarm directives

**Action Buttons:**
- `[Cancel]` — Close drawer, deselect node
- `[Run Simulation]` — Trigger digital twin backtest (transitions node to `simulating` state)

---

## Bottom Panel (300px, slide-up) — Digital Twin Backtester

**Purpose:** Real-time simulation results before production deployment.

**Triggered By:** Clicking `[Run Simulation]` in Configuration Drawer.

**Layout:**
- **Left (66%):** Chart placeholder for projected ROI timeline (powered by `vessel-simulation` in production)
- **Right (33%):** 4 metric cards:
  - **Confidence Score:** 87% (↑ High confidence)
  - **Projected ROI:** +$2,340 (↑ 23.4% return)
  - **Est. Runtime:** 4.2h (Within budget)
  - **Risk Score:** Low (0.12 / 1.0)

**State Transition:**
1. User clicks `[Run Simulation]`
2. HubNode transitions to `simulating` state (amber pulsing border)
3. Bottom panel slides up with live metrics
4. After 3 seconds (mocked), node transitions to `executing` state (green border)
5. Button changes from `[Run Simulation]` to `[Deploy Swarm]` (green)

---

## Use Case Templates (27+ Across 5 Domains)

### Domain 1: Cinematic World-Building (3 templates)
1. **Reality Series Generator** — End-to-end reality TV production pipeline
2. **LLC to TikTok Pipeline** — Automated brand incubation and content distribution
3. **Cinematic World Builder** — Generate complete fictional universes with lore

### Domain 2: Algorithmic Trading (3 templates)
1. **XRP Scalp Bot** — High-frequency XRP trading with risk management
2. **Portfolio Optimizer** — AI-driven portfolio rebalancing and optimization
3. **Options Strategy Bot** — Automated options trading with Greeks analysis

### Domain 3: Automated E-Commerce (3 templates)
1. **Amazon Brand Incubator** — Full-stack Amazon FBA brand launch automation
2. **Dropshipping Optimizer** — Automated product sourcing and listing optimization
3. **Inventory Predictor** — ML-powered inventory forecasting and reordering

### Domain 4: Research & Intelligence (3 templates)
1. **Market Research Agent** — Comprehensive market analysis and competitive intelligence
2. **Patent Analyzer** — Automated patent search and prior art analysis
3. **Competitor Monitor** — Real-time competitive intelligence and alerting

### Domain 5: Autonomous Operations (3 templates)
1. **Customer Support Swarm** — 24/7 autonomous customer support with escalation
2. **DevOps Orchestrator** — Autonomous infrastructure management and deployment
3. **Security Monitor** — Continuous security monitoring and threat response

**Total:** 15 templates implemented (expandable to 27+ by adding more to `useCaseTemplates` object).

---

## Technical Implementation

### Technology Stack
- **Framework:** Vanilla HTML/CSS/JavaScript (zero dependencies, zero build step)
- **Drag & Drop:** HTML5 Drag and Drop API
- **State Management:** Plain JavaScript object (`state`)
- **Real-Time:** WebSocket mock (connects to `ws://vessel-gateway/hub` in production)
- **Charts:** Chart.js CDN (for future chart rendering)

### File Structure
```
services/vessel-interface/public/
├── UNIVERSAL_HUB.html          # Main file (self-contained)
└── UNIVERSAL_HUB_README.md     # This documentation
```

### Key Functions

#### Drag & Drop
```javascript
setupDragEvents()           // Attach dragstart/dragend to template cards
createHubNode(template, x, y)  // Instantiate node on canvas drop
makeDraggable(element, node)   // Make HubNode draggable on canvas
```

#### Configuration
```javascript
selectNode(node)            // Select node, open config drawer
openConfigDrawer(node)      // Populate drawer with node data
renderParametersTab(node)   // Render dynamic form based on template
renderSwarmTab(node)        // Render persona topology
renderAdvancedTab(node)     // Render advanced settings
```

#### Simulation
```javascript
runSimulation(node)         // Trigger backtest, update node state
connectWebSocket()          // Mock WebSocket connection (real in production)
```

---

## Integration with MAARS Backend

### Production API Endpoints

**1. Fetch Use Case Templates**
```http
GET /v1/hub/templates
Response: { "domains": { "Algorithmic Trading": [...] } }
```

**2. Deploy Use Case**
```http
POST /v1/hub/deploy
Body: {
  "template_id": "xrp-scalp-bot",
  "parameters": { "maxDrawdown": 5, "escrowLimit": 10000, "assetPair": "XRP/USD" },
  "swarm_config": { "personas": [...] }
}
Response: { "deployment_id": "dep_abc123", "status": "simulating" }
```

**3. Run Simulation**
```http
POST /internal/v1/simulation/run
Body: { "deployment_id": "dep_abc123" }
Response: { "simulation_id": "sim_xyz789", "confidence": 87, "projected_roi": 2340 }
```

**4. Update Persona**
```http
PUT /v1/swarm/personas/{persona_id}
Body: { "instructions": "...", "manifesto": "..." }
Response: { "persona_id": "persona_123", "updated_at": "2026-03-22T15:00:00Z" }
```

### WebSocket Channels

**Hub Channel:** `ws://vessel-gateway/hub`

**Events:**
- `hub.node.created` — New HubNode instantiated
- `hub.node.status` — Node status changed (idle → simulating → executing)
- `hub.simulation.completed` — Simulation finished, metrics available
- `hub.deployment.started` — Swarm deployed to production
- `hub.deployment.blocked` — Guardrail intervention or escrow hold

---

## Usage Instructions

### 1. Launch the Hub
```bash
# Open in browser
open services/vessel-interface/public/UNIVERSAL_HUB.html

# Or serve via HTTP
cd services/vessel-interface/public
python3 -m http.server 8000
# Navigate to http://localhost:8000/UNIVERSAL_HUB.html
```

### 2. Deploy a Use Case
1. **Browse:** Expand a domain cluster in the left sidebar (e.g., "Algorithmic Trading")
2. **Drag:** Drag a template card (e.g., "XRP Scalp Bot") onto the canvas
3. **Configure:** Click the instantiated HubNode to open the Configuration Drawer
4. **Customize:** Adjust parameters in the "Parameters" tab
5. **Simulate:** Click `[Run Simulation]` to run a digital twin backtest
6. **Deploy:** After simulation completes, click `[Deploy Swarm]` to go live

### 3. Monitor Execution
- **Node Border Color:** Indicates current state (grey=idle, amber=simulating, green=executing, red=blocked)
- **Status Pill:** Shows current state in text (e.g., "SIMULATING", "EXECUTING")
- **Simulation Panel:** Shows real-time metrics during backtesting

---

## Next Steps: Production Migration

### Phase 8.1: Next.js Migration
Convert standalone HTML to Next.js 15 App Router:
```
services/vessel-interface/
├── src/
│   ├── app/
│   │   └── hub/
│   │       └── page.tsx          # Main Hub route
│   ├── components/
│   │   ├── hub/
│   │   │   ├── Sidebar.tsx       # Use case library
│   │   │   ├── Canvas.tsx        # React Flow canvas
│   │   │   ├── HubNode.tsx       # Custom node component
│   │   │   ├── ConfigDrawer.tsx  # Configuration panel
│   │   │   └── SimulationPanel.tsx # Backtester
│   ├── lib/
│   │   ├── websocket/
│   │   │   └── hub-channel.ts    # WebSocket integration
│   │   └── api/
│   │       └── hub.ts            # REST API client
│   └── store/
│       └── hub.ts                # Zustand state management
```

### Phase 8.2: React Flow Integration
Replace vanilla canvas with React Flow for:
- **Advanced DAG features:** Edge routing, minimap, zoom controls
- **Performance:** WebGL rendering for 100+ nodes
- **Interactivity:** Edge connections between nodes (data flow visualization)

### Phase 8.3: Monaco Editor Integration
Replace `alert()` in `editPersona()` with:
```typescript
import Editor from '@monaco-editor/react';

<Editor
  height="400px"
  defaultLanguage="markdown"
  defaultValue={persona.instructions}
  theme="vs-dark"
  onChange={(value) => updatePersona(persona.id, value)}
/>
```

### Phase 8.4: Real-Time Charts
Replace chart placeholder with Recharts:
```typescript
import { LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';

<LineChart data={simulationData}>
  <Line type="monotone" dataKey="roi" stroke="#58a6ff" />
  <XAxis dataKey="time" />
  <YAxis />
  <Tooltip />
</LineChart>
```

---

## Performance Targets

- **Initial Load:** <2s
- **Drag & Drop Latency:** <50ms
- **Node Instantiation:** <100ms
- **WebSocket Latency:** <100ms
- **Simulation Start:** <500ms
- **Canvas Scalability:** 100+ nodes without lag

---

## Security Considerations

- **Authentication:** Integrate with `vessel-identity` for SSO (NextAuth.js in production)
- **Authorization:** Role-based access control (RBAC) for use case deployment
- **WebSocket Security:** Use `wss://` in production, validate JWT tokens
- **Input Validation:** Sanitize all user inputs in configuration forms
- **Escrow Enforcement:** All high-cost actions require human approval via `vessel-economics`

---

## Troubleshooting

### Issue: Drag & Drop Not Working
**Solution:** Ensure `draggable="true"` attribute is set on template cards. Check browser console for JavaScript errors.

### Issue: Configuration Drawer Not Opening
**Solution:** Verify `selectNode()` function is called on node click. Check if `state.selectedNode` is set correctly.

### Issue: Simulation Panel Not Appearing
**Solution:** Ensure `runSimulation()` is triggered and `simulationPanel.classList.add('open')` is executed.

### Issue: WebSocket Connection Failed
**Solution:** In prototype mode, WebSocket is mocked. In production, verify `vessel-gateway` is running and accessible.

---

## Contributing

When extending the Universal Hub:

1. **Add New Use Case Template:**
   - Add to `useCaseTemplates` object in `<script>` section
   - Define `id`, `name`, `description`, `subsystems`, `personas`, `parameters`

2. **Add New Domain Cluster:**
   - Add new key to `useCaseTemplates` object
   - Accordion will auto-generate

3. **Add New Parameter Type:**
   - Extend `renderParametersTab()` function
   - Add new `if` condition for custom input type

4. **Customize Node Appearance:**
   - Modify `.hub-node` CSS classes
   - Update `renderHubNode()` function

---

## License

Proprietary — All Rights Reserved © 2026

---

**Version:** 1.0.0  
**Last Updated:** 2026-03-22  
**Status:** Production-Ready Prototype  
**Next:** Phase 8.1 — Next.js Migration