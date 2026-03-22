# MAARS Assistant — Embedded Copilot

## Overview

The **MAARS Assistant** is a context-aware LLM copilot embedded directly into the Vision Layer UI. It helps enterprise operators, engineers, and stakeholders navigate the complex MAARS architecture, understand the 13 microservices, and interpret Phase 8 framework integrations.

## Design Philosophy

The assistant adheres to MAARS core principles:

| Principle | Implementation |
|-----------|----------------|
| **User-Configurable LLM** | Routes through `vessel-llm-router` for BYOK (Bring Your Own Key) |
| **Zero Trust (NHI)** | Read-only entity, cannot execute actions on swarm or economics layers |
| **Uncodixfy Design** | No glassmorphism, no soft gradients — Bloomberg-terminal style |
| **Event-Driven Context** | Future: Subscribe to `vessel-observability` Kafka topics for real-time context |

## UI/UX Specification

### Component Hierarchy

1. **AssistantTrigger** — Fixed FAB at bottom-right (`bottom: 28px`, `right: 28px`)
   - Primary blue (`#58a6ff`) with green notification dot
   - Displays `?` icon
   - Click to toggle panel

2. **AssistantPanel** — Floating chat window (`420px × 620px`)
   - Void Space dark palette (`#0d1117` bg, `#161b22` surface)
   - Animates in via scale + translate transform
   - Collapsible with close button

3. **MessageBubble** — Individual chat messages
   - Bot messages: `surface2` color (`#21262d`)
   - User messages: primary blue
   - Markdown parsing for code blocks and links

### Interaction Flow

1. **Initialization**: Panel hidden by default
2. **Toggle**: Click trigger to open/close
3. **Suggestions**: Quick-action chips guide users
4. **Typing Indicator**: Three-dot bounce animation during inference
5. **Anchor Navigation**: Links scroll to Vision Layer sections

## Architecture

### Current Implementation (Demo Mode)

The assistant currently uses a **pattern-matching response system** for demo purposes:

```javascript
const assistant = {
  systemContext: `...comprehensive MAARS architecture context...`,
  
  async getResponse(userMessage) {
    // Pattern matching for common queries
    if (lower.includes('vessel-swarm')) {
      return `**vessel-swarm** is the agent lifecycle management service...`;
    }
    // ... more patterns
  }
};
```

### Production Architecture (Phase 8)

In production, the assistant will integrate with the full MAARS backend:

```
┌─────────────────┐
│ Vision Layer UI │
│  (Assistant)    │
└────────┬────────┘
         │ POST /v1/assistant/chat
         ▼
┌─────────────────┐
│ vessel-gateway  │
│  (API Gateway)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│vessel-llm-router│ ◄─── User's API Key (OpenAI, Anthropic, etc.)
│  (LLM Routing)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ vessel-memory   │ ◄─── GraphRAG context from Cognee
│ (Context Store) │
└─────────────────┘
```

## API Contract

### Request

**Endpoint:** `POST /v1/assistant/chat`

```json
{
  "messages": [
    {
      "role": "user",
      "content": "What is the difference between the Escrow Inbox and the Action Intercept Layer?"
    }
  ],
  "context": {
    "current_route": "/app/inbox",
    "selected_node_id": null
  }
}
```

### Response

```json
{
  "reply": "The **Escrow Inbox** (`/app/inbox`) is for post-proposal approval gating, backed by `vessel-economics`. The **Action Intercept Layer** is a real-time overlay on the `/app/canvas` for immediate intervention before execution. See [#phase8-inbox](#phase8-inbox) for details.",
  "latency_ms": 845
}
```

## System Context

The assistant is primed with comprehensive MAARS knowledge:

### Architecture Overview
- 13 microservices (vessel-gateway, vessel-llm-router, vessel-swarm, etc.)
- 4 evolutionary phases (OpenClaw → ApexClaw → Machine Economy → MAARS)
- 6 Vision Layer routes (/app/canvas, /app/inbox, etc.)

### Key Services
- **vessel-swarm**: Agent lifecycle, registry, pool orchestration
- **vessel-economics**: Cost tracking, escrow, compliance
- **vessel-observability**: Guardrails, anomaly detection, telemetry
- **vessel-llm-router**: Multi-provider LLM routing with caching
- **vessel-memory**: Cognee hybrid memory, knowledge graphs

### Phase 8 Integrations
- Heretic, DeerFlow, Paperclip, AutoRA, Agency Agents
- MiroFish, Cognee, Materialize, x402, W3C DIDs, Wyoming DAO LLCs

## Demo Mode Capabilities

The current implementation can answer questions about:

### Microservices
- "What is vessel-swarm?"
- "Explain vessel-economics"
- "How does vessel-observability work?"

### Vision Layer
- "What is the Live Canvas?"
- "How does the Escrow Inbox work?"
- "Explain the Agent Registry"

### Architecture
- "What are the 4 evolutionary phases?"
- "Explain Phase 8"
- "How do WebSockets work in MAARS?"

### Example Responses

**Q: "What is vessel-swarm?"**

> **vessel-swarm** is the agent lifecycle management service. It handles:
> 
> - Agent registry and metadata storage
> - Agent pool orchestration (NANO, MID, FRONTIER tiers)
> - Lifecycle events (spawn, idle, terminate)
> - Task assignment and routing
> 
> Key endpoints:
> - `POST /v1/agents` — Register new agent
> - `GET /v1/agents/{id}` — Get agent details
> - `POST /v1/agents/{id}/terminate` — Terminate agent
> 
> See the [Agent Registry](#agents) for the full list of active agents.

## Phase 8 Integration Roadmap

### 1. GraphRAG Context Awareness (vessel-memory)

Currently uses static system prompt. In Phase 8:

- Query **Cognee hybrid memory** via `POST /v1/memory/graph/query`
- Pull agent temporal relationships from Neo4j (MiroFish pattern)
- Provide highly contextual answers based on live agent state

### 2. Real-Time Telemetry (vessel-observability)

Subscribe to WebSocket channels:

- Monitor `safety` and `guardrails` channels
- Proactive notifications when Heretic `activation_risk_score` > 70
- Pulse notification dot and offer anomaly explanations

### 3. Persona Editor Integration (vessel-swarm)

When user asks to modify agent behavior:

- Generate YAML for **Agency Agents** declarative persona
- Provide one-click "Apply to Persona Editor" button
- Validate persona against guardrail constraints

### 4. Action Execution (vessel-economics)

**Read-only scope** in current design, but future iterations may allow:

- Approve escrow actions via assistant chat
- Modify agent configurations
- Trigger simulations

**Security**: JIT token from `vessel-identity` with strict `read:docs` and `read:telemetry` scope.

## Security & Compliance

### Stateless Execution
- No persistent chat history storage
- History maintained in browser session (React state)
- Cleared on page refresh

### Read-Only Scope
- JIT token: `read:docs`, `read:telemetry`
- Cannot invoke `POST /v1/escrow/{id}/approve`
- Cannot modify agent configurations

### Data Isolation
- Multi-tenant deployments: context scoped to tenant namespace
- No cross-contamination of proprietary architecture details
- Audit logs for all assistant queries (Phase 8)

## Usage Examples

### Quick Start

1. Click the blue `?` button at bottom-right
2. Try a suggestion chip: "What is vessel-swarm?"
3. Type your own question: "Explain Phase 8"
4. Click links to navigate to relevant sections

### Advanced Queries

**Multi-Service Questions:**
> "How do vessel-swarm and vessel-economics interact during escrow?"

**Architecture Deep-Dives:**
> "Explain the difference between the 4 evolutionary phases"

**Phase 8 Integrations:**
> "What is Heretic and how does it score activation risk?"

**Troubleshooting:**
> "Why is my agent stuck in GUARDRAIL_CHECK state?"

## Styling Reference

### Colors (Void Space Palette)

```css
--bg:        #0d1117  /* Background */
--surface:   #161b22  /* Panel background */
--surface2:  #21262d  /* Message bubbles */
--border:    #30363d  /* Borders */
--primary:   #58a6ff  /* Trigger button, user messages */
--text:      #c9d1d9  /* Body text */
--text-dim:  #8b949e  /* Dimmed text */
--text-bright: #f0f6fc /* Bright text */
```

### Animations

```css
/* Panel entrance */
transform: translateY(12px) scale(0.97) → translateY(0) scale(1)
transition: 200ms

/* Typing indicator */
@keyframes ast-bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}
```

## Future Enhancements

### Phase 8
- [ ] GraphRAG integration with vessel-memory
- [ ] Real-time telemetry subscriptions
- [ ] Persona editor YAML generation
- [ ] Multi-language support (i18n)

### Phase 9
- [ ] Voice input/output
- [ ] Agent-to-agent communication explanations
- [ ] Simulation scenario recommendations
- [ ] Automated troubleshooting workflows

## Development

### Testing

```bash
# Open Vision Layer UI
./start-ui.sh

# Click assistant trigger (bottom-right)
# Test queries:
# - "What is vessel-swarm?"
# - "Explain Phase 8"
# - "How does the Escrow Inbox work?"
```

### Customization

Edit `VISION_LAYER.html` line 1249+ to modify:

- System context prompt
- Pattern matching responses
- Suggestion chips
- Styling (CSS at line 337+)

### Production Integration

To connect to live backend:

1. Update `getResponse()` to call `POST /v1/assistant/chat`
2. Configure `vessel-gateway` to route assistant requests
3. Set up `vessel-llm-router` with user API keys
4. Enable GraphRAG context from `vessel-memory`

## Troubleshooting

### Assistant not opening
- Check browser console for JavaScript errors
- Verify `assistantTrigger` element exists in DOM

### Responses not appearing
- Check `getResponse()` pattern matching logic
- Verify message bubbles are being appended to container

### Styling issues
- Ensure Void Space CSS variables are defined
- Check z-index conflicts with other UI elements

---

**Version**: 1.0.0  
**Status**: Demo Mode (Pattern Matching)  
**Next**: Phase 8 — GraphRAG Integration  
**License**: Proprietary — All Rights Reserved © 2026