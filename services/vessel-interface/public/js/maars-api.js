/**
 * MAARS OS API Client
 * Connects frontend UI to backend microservices
 */

class MAARSAPIClient {
  constructor(config = {}) {
    this.baseURL = config.baseURL || 'http://localhost:8000';
    this.orchestratorURL = config.orchestratorURL || 'http://localhost:8000';
    this.swarmURL = config.swarmURL || 'http://localhost:8001';
    this.observabilityURL = config.observabilityURL || 'http://localhost:8002';
    this.economicsURL = config.economicsURL || 'http://localhost:8003';
    this.wsURL = config.wsURL || 'ws://localhost:8000/ws';
    
    this.ws = null;
    this.wsCallbacks = {};
  }

  // ============================================
  // ORCHESTRATOR API
  // ============================================

  /**
   * Create a new workflow from natural language description
   */
  async createWorkflow(description, userId = 'default') {
    try {
      const response = await fetch(`${this.orchestratorURL}/api/v1/workflows`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description,
          user_id: userId,
          auto_start: true
        })
      });
      
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error creating workflow:', error);
      throw error;
    }
  }

  /**
   * Get workflow details
   */
  async getWorkflow(workflowId) {
    try {
      const response = await fetch(`${this.orchestratorURL}/api/v1/workflows/${workflowId}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error fetching workflow:', error);
      throw error;
    }
  }

  /**
   * Execute a workflow
   */
  async executeWorkflow(workflowId) {
    try {
      const response = await fetch(`${this.orchestratorURL}/api/v1/workflows/${workflowId}/execute`, {
        method: 'POST'
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error executing workflow:', error);
      throw error;
    }
  }

  /**
   * Pause a workflow
   */
  async pauseWorkflow(workflowId) {
    try {
      const response = await fetch(`${this.orchestratorURL}/api/v1/workflows/${workflowId}/pause`, {
        method: 'POST'
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error pausing workflow:', error);
      throw error;
    }
  }

  // ============================================
  // SWARM API
  // ============================================

  /**
   * Get all active swarms
   */
  async getSwarms() {
    try {
      const response = await fetch(`${this.swarmURL}/api/v1/swarms`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error fetching swarms:', error);
      throw error;
    }
  }

  /**
   * Get swarm details
   */
  async getSwarm(swarmId) {
    try {
      const response = await fetch(`${this.swarmURL}/api/v1/swarms/${swarmId}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error fetching swarm:', error);
      throw error;
    }
  }

  /**
   * Create a new agent
   */
  async createAgent(name, description, capabilities = []) {
    try {
      const response = await fetch(`${this.swarmURL}/api/v1/agents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          description,
          capabilities,
          auto_start: true
        })
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error creating agent:', error);
      throw error;
    }
  }

  /**
   * Get agent status
   */
  async getAgent(agentId) {
    try {
      const response = await fetch(`${this.swarmURL}/api/v1/agents/${agentId}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error fetching agent:', error);
      throw error;
    }
  }

  // ============================================
  // OBSERVABILITY API
  // ============================================

  /**
   * Get system metrics
   */
  async getMetrics() {
    try {
      const response = await fetch(`${this.observabilityURL}/api/v1/metrics`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error fetching metrics:', error);
      throw error;
    }
  }

  /**
   * Get guardrail events
   */
  async getGuardrailEvents(limit = 10) {
    try {
      const response = await fetch(`${this.observabilityURL}/api/v1/guardrails?limit=${limit}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error fetching guardrail events:', error);
      throw error;
    }
  }

  /**
   * Approve a guardrail action
   */
  async approveGuardrail(eventId) {
    try {
      const response = await fetch(`${this.observabilityURL}/api/v1/guardrails/${eventId}/approve`, {
        method: 'POST'
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error approving guardrail:', error);
      throw error;
    }
  }

  /**
   * Reject a guardrail action
   */
  async rejectGuardrail(eventId) {
    try {
      const response = await fetch(`${this.observabilityURL}/api/v1/guardrails/${eventId}/reject`, {
        method: 'POST'
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error rejecting guardrail:', error);
      throw error;
    }
  }

  /**
   * Get telemetry logs
   */
  async getLogs(filters = {}) {
    try {
      const params = new URLSearchParams(filters);
      const response = await fetch(`${this.observabilityURL}/api/v1/logs?${params}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error fetching logs:', error);
      throw error;
    }
  }

  // ============================================
  // ECONOMICS API
  // ============================================

  /**
   * Get cost summary
   */
  async getCostSummary() {
    try {
      const response = await fetch(`${this.economicsURL}/api/v1/costs/summary`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error fetching cost summary:', error);
      throw error;
    }
  }

  /**
   * Get budget status
   */
  async getBudgetStatus() {
    try {
      const response = await fetch(`${this.economicsURL}/api/v1/budgets/status`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error fetching budget status:', error);
      throw error;
    }
  }

  /**
   * Approve budget increase
   */
  async approveBudgetIncrease(amount, reason) {
    try {
      const response = await fetch(`${this.economicsURL}/api/v1/budgets/increase`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount, reason })
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error approving budget increase:', error);
      throw error;
    }
  }

  // ============================================
  // WEBSOCKET API (Real-time Updates)
  // ============================================

  /**
   * Connect to WebSocket for real-time updates
   */
  connectWebSocket(callbacks = {}) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    this.wsCallbacks = callbacks;
    this.ws = new WebSocket(this.wsURL);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      if (callbacks.onConnect) callbacks.onConnect();
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WebSocket message:', data);

        // Route to appropriate callback
        if (data.type === 'swarm_update' && callbacks.onSwarmUpdate) {
          callbacks.onSwarmUpdate(data.payload);
        } else if (data.type === 'agent_update' && callbacks.onAgentUpdate) {
          callbacks.onAgentUpdate(data.payload);
        } else if (data.type === 'metric_update' && callbacks.onMetricUpdate) {
          callbacks.onMetricUpdate(data.payload);
        } else if (data.type === 'log' && callbacks.onLog) {
          callbacks.onLog(data.payload);
        } else if (data.type === 'guardrail' && callbacks.onGuardrail) {
          callbacks.onGuardrail(data.payload);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (callbacks.onError) callbacks.onError(error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      if (callbacks.onDisconnect) callbacks.onDisconnect();
      
      // Auto-reconnect after 5 seconds
      setTimeout(() => {
        console.log('Attempting to reconnect WebSocket...');
        this.connectWebSocket(callbacks);
      }, 5000);
    };
  }

  /**
   * Disconnect WebSocket
   */
  disconnectWebSocket() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Send message via WebSocket
   */
  sendWebSocketMessage(type, payload) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, payload }));
    } else {
      console.error('WebSocket not connected');
    }
  }

  // ============================================
  // UTILITY METHODS
  // ============================================

  /**
   * Check if backend services are available
   */
  async healthCheck() {
    const services = {
      orchestrator: this.orchestratorURL,
      swarm: this.swarmURL,
      observability: this.observabilityURL,
      economics: this.economicsURL
    };

    const results = {};

    for (const [name, url] of Object.entries(services)) {
      try {
        const response = await fetch(`${url}/health`, { method: 'GET' });
        results[name] = response.ok;
      } catch (error) {
        results[name] = false;
      }
    }

    return results;
  }

  /**
   * Get dashboard data (aggregated)
   */
  async getDashboardData() {
    try {
      const [swarms, metrics, logs, costs] = await Promise.all([
        this.getSwarms().catch(() => []),
        this.getMetrics().catch(() => ({})),
        this.getLogs({ limit: 10 }).catch(() => []),
        this.getCostSummary().catch(() => ({}))
      ]);

      return {
        swarms,
        metrics,
        logs,
        costs,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      throw error;
    }
  }
}

// Export for use in HTML files
if (typeof window !== 'undefined') {
  window.MAARSAPIClient = MAARSAPIClient;
}

// Export for Node.js (if needed)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = MAARSAPIClient;
}

// Made with Bob
