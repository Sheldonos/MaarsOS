# MAARS OS UI Deployment Guide

Complete guide for deploying and running the MAARS OS user interface with full backend integration.

## 🎯 Overview

The MAARS OS UI consists of:
- **HOME.html** - Landing page with natural language workflow creation
- **UNIVERSAL_HUB.html** - Canvas workflow editor with visual flow diagram
- **LIVE_DASHBOARD.html** - Real-time monitoring and agent orchestration
- **AGENT_CREATOR.html** - Dedicated agent creation interface
- **VISION_LAYER.html** - Advanced visualization layer

## 📋 Prerequisites

### Required Services
- Docker & Docker Compose
- Python 3.8+ (for HTTP server)
- Backend services (vessel-orchestrator, vessel-swarm, vessel-observability, vessel-economics)

### Optional
- Node.js (for advanced development)
- Redis (for caching)
- Kafka (for event streaming)

## 🚀 Quick Start

### 1. Start Backend Services

```bash
# From project root
cd /Users/sheldonibm/Desktop/maarsOS

# Start all backend services
docker-compose -f infrastructure/docker/docker-compose.yml up -d

# Verify services are running
docker-compose ps
```

Expected services:
- vessel-orchestrator: `http://localhost:8000`
- vessel-swarm: `http://localhost:8001`
- vessel-observability: `http://localhost:8002`
- vessel-economics: `http://localhost:8003`

### 2. Start UI Server

```bash
# Make script executable
chmod +x serve-ui.sh

# Start HTTP server
./serve-ui.sh
```

The UI will be available at: `http://localhost:8080`

### 3. Access the Interface

Open your browser and navigate to:
- **Home**: http://localhost:8080/HOME.html
- **Canvas**: http://localhost:8080/UNIVERSAL_HUB.html
- **Dashboard**: http://localhost:8080/LIVE_DASHBOARD.html
- **Agent Creator**: http://localhost:8080/AGENT_CREATOR.html

## 🔧 Configuration

### API Endpoints

Edit `services/vessel-interface/public/js/integration.js` to configure backend URLs:

```javascript
const maarsAPI = new MAARSAPIClient({
  baseURL: 'http://localhost:8000',
  orchestratorURL: 'http://localhost:8000',
  swarmURL: 'http://localhost:8001',
  observabilityURL: 'http://localhost:8002',
  economicsURL: 'http://localhost:8003',
  wsURL: 'ws://localhost:8000/ws'
});
```

### Environment Variables

Create `.env` file in project root:

```bash
# Backend URLs
ORCHESTRATOR_URL=http://localhost:8000
SWARM_URL=http://localhost:8001
OBSERVABILITY_URL=http://localhost:8002
ECONOMICS_URL=http://localhost:8003

# WebSocket
WS_URL=ws://localhost:8000/ws

# UI Server
UI_PORT=8080
```

## 📊 Features & Integration

### 1. Natural Language Workflow Creation

**Location**: HOME.html

**How it works**:
1. User enters natural language description
2. Frontend calls `maarsAPI.createWorkflow(description)`
3. Backend (vessel-orchestrator) parses and creates workflow
4. User redirected to Canvas with workflow ID

**API Call**:
```javascript
const result = await maarsAPI.createWorkflow("Analyze market trends and generate report");
// Returns: { workflow_id: "wf-123", status: "created" }
```

### 2. Visual Workflow Editor

**Location**: UNIVERSAL_HUB.html

**Features**:
- Drag-and-drop agent nodes
- Visual connections between agents
- Real-time status updates
- Run/Pause/Stop controls

**API Integration**:
```javascript
// Load workflow
const workflow = await maarsAPI.getWorkflow(workflowId);

// Execute workflow
await maarsAPI.executeWorkflow(workflowId);

// Pause workflow
await maarsAPI.pauseWorkflow(workflowId);
```

### 3. Live Dashboard

**Location**: LIVE_DASHBOARD.html

**Real-time Updates**:
- Agent status monitoring
- System metrics (CPU, Memory, Tokens)
- Guardrail events
- Cost tracking

**WebSocket Integration**:
```javascript
maarsAPI.connectWebSocket({
  onAgentUpdate: (data) => {
    // Update agent status in UI
  },
  onMetricUpdate: (data) => {
    // Update system metrics
  },
  onGuardrail: (data) => {
    // Show guardrail alert
  }
});
```

### 4. Guardrail Approval System

**How it works**:
1. Agent triggers guardrail (e.g., high-cost operation)
2. WebSocket pushes event to dashboard
3. User sees approval dialog
4. User approves/rejects action
5. Backend receives decision and proceeds

**API Calls**:
```javascript
// Approve action
await maarsAPI.approveGuardrail(eventId);

// Reject action
await maarsAPI.rejectGuardrail(eventId);
```

## 🔌 Backend Integration Points

### Vessel Orchestrator
**Endpoints**:
- `POST /api/v1/workflows` - Create workflow
- `GET /api/v1/workflows/{id}` - Get workflow details
- `POST /api/v1/workflows/{id}/execute` - Execute workflow
- `POST /api/v1/workflows/{id}/pause` - Pause workflow

### Vessel Swarm
**Endpoints**:
- `GET /api/v1/swarms` - List active swarms
- `GET /api/v1/swarms/{id}` - Get swarm details
- `POST /api/v1/agents` - Create agent
- `GET /api/v1/agents/{id}` - Get agent status

### Vessel Observability
**Endpoints**:
- `GET /api/v1/metrics` - Get system metrics
- `GET /api/v1/guardrails` - Get guardrail events
- `POST /api/v1/guardrails/{id}/approve` - Approve action
- `POST /api/v1/guardrails/{id}/reject` - Reject action
- `GET /api/v1/logs` - Get telemetry logs

### Vessel Economics
**Endpoints**:
- `GET /api/v1/costs/summary` - Get cost summary
- `GET /api/v1/budgets/status` - Get budget status
- `POST /api/v1/budgets/increase` - Request budget increase

## 🧪 Testing

### 1. Test Backend Connection

Open browser console on any page:

```javascript
// Check backend health
const health = await maarsAPI.healthCheck();
console.log(health);
// Expected: { orchestrator: true, swarm: true, ... }
```

### 2. Test Workflow Creation

1. Go to HOME.html
2. Enter: "Create a research agent to analyze AI trends"
3. Click "Generate Workflow"
4. Check console for API calls
5. Verify redirect to Canvas

### 3. Test Real-time Updates

1. Go to LIVE_DASHBOARD.html
2. Open browser console
3. Look for WebSocket connection message
4. Trigger an agent action from another tab
5. Verify dashboard updates automatically

### 4. Test Guardrail System

1. Configure a guardrail in backend (e.g., cost > $10)
2. Trigger action that exceeds threshold
3. Verify approval dialog appears in dashboard
4. Test approve/reject functionality

## 🐛 Troubleshooting

### Issue: "Backend not connected" warning

**Solution**:
1. Verify backend services are running: `docker-compose ps`
2. Check service logs: `docker-compose logs vessel-orchestrator`
3. Test endpoints manually: `curl http://localhost:8000/health`
4. Verify CORS is enabled in backend services

### Issue: WebSocket connection fails

**Solution**:
1. Check WebSocket URL in `integration.js`
2. Verify backend supports WebSocket connections
3. Check browser console for connection errors
4. Test with: `wscat -c ws://localhost:8000/ws`

### Issue: Buttons don't trigger actions

**Solution**:
1. Open browser console and check for JavaScript errors
2. Verify `maars-api.js` and `integration.js` are loaded
3. Check network tab for failed API calls
4. Ensure HTTP server is running (not file:// protocol)

### Issue: CORS errors

**Solution**:
Add CORS headers to backend services:

```python
# Python/FastAPI
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📈 Performance Optimization

### 1. Enable Caching

Configure Redis for API response caching:

```javascript
// In maars-api.js
const cache = new Map();
const CACHE_TTL = 60000; // 1 minute

async function cachedFetch(url) {
  const cached = cache.get(url);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data;
  }
  
  const data = await fetch(url).then(r => r.json());
  cache.set(url, { data, timestamp: Date.now() });
  return data;
}
```

### 2. Optimize WebSocket

Throttle updates to prevent UI overload:

```javascript
let updateQueue = [];
let isProcessing = false;

function throttledUpdate(data) {
  updateQueue.push(data);
  if (!isProcessing) {
    processQueue();
  }
}

async function processQueue() {
  isProcessing = true;
  while (updateQueue.length > 0) {
    const batch = updateQueue.splice(0, 10);
    await updateUI(batch);
    await new Promise(r => setTimeout(r, 100));
  }
  isProcessing = false;
}
```

### 3. Lazy Load Components

Load heavy components only when needed:

```javascript
async function loadDashboard() {
  const module = await import('./dashboard-module.js');
  module.initialize();
}
```

## 🔒 Security

### 1. Authentication

Add JWT token authentication:

```javascript
// In maars-api.js
class MAARSAPIClient {
  constructor(config) {
    this.token = localStorage.getItem('auth_token');
  }
  
  async fetch(url, options = {}) {
    return fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${this.token}`
      }
    });
  }
}
```

### 2. Input Validation

Sanitize user input:

```javascript
function sanitizeInput(input) {
  return input
    .replace(/</g, '<')
    .replace(/>/g, '>')
    .replace(/"/g, '"')
    .trim();
}
```

### 3. Rate Limiting

Implement client-side rate limiting:

```javascript
const rateLimiter = {
  calls: [],
  maxCalls: 10,
  timeWindow: 60000, // 1 minute
  
  canMakeCall() {
    const now = Date.now();
    this.calls = this.calls.filter(t => now - t < this.timeWindow);
    return this.calls.length < this.maxCalls;
  },
  
  recordCall() {
    this.calls.push(Date.now());
  }
};
```

## 📦 Production Deployment

### 1. Build for Production

```bash
# Minify JavaScript
npm install -g terser
terser js/maars-api.js -o js/maars-api.min.js -c -m
terser js/integration.js -o js/integration.min.js -c -m

# Update HTML to use minified versions
sed -i 's/maars-api.js/maars-api.min.js/g' *.html
sed -i 's/integration.js/integration.min.js/g' *.html
```

### 2. Deploy with Nginx

```nginx
server {
    listen 80;
    server_name maars.example.com;
    
    root /var/www/maars-ui/public;
    index HOME.html;
    
    location / {
        try_files $uri $uri/ =404;
    }
    
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
    
    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
}
```

### 3. Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM nginx:alpine

COPY services/vessel-interface/public /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

Build and run:

```bash
docker build -t maars-ui .
docker run -d -p 80:80 maars-ui
```

## 📚 Additional Resources

- [Backend Integration Guide](BACKEND_INTEGRATION_GUIDE.md)
- [API Documentation](../vessel-orchestrator/README.md)
- [WebSocket Protocol](../vessel-observability/README.md)
- [Security Best Practices](../../docs/SECURITY.md)

## 🆘 Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Review browser console for errors
3. Test API endpoints with curl/Postman
4. Consult backend service documentation

## ✅ Checklist

Before going live:

- [ ] All backend services running
- [ ] UI server accessible
- [ ] WebSocket connection established
- [ ] API calls returning data
- [ ] Guardrail system functional
- [ ] Real-time updates working
- [ ] Error handling tested
- [ ] Security measures implemented
- [ ] Performance optimized
- [ ] Documentation complete

---

**Version**: 1.0.0  
**Last Updated**: 2026-03-22  
**Status**: Production Ready