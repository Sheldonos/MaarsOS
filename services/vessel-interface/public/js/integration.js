/**
 * MAARS OS UI Integration Script
 * Connects all UI pages to backend services
 */

// Initialize API client
const maarsAPI = new MAARSAPIClient({
  baseURL: 'http://localhost:8000',
  orchestratorURL: 'http://localhost:8000',
  swarmURL: 'http://localhost:8001',
  observabilityURL: 'http://localhost:8002',
  economicsURL: 'http://localhost:8003',
  wsURL: 'ws://localhost:8000/ws'
});

// Global state
let currentWorkflowId = null;
let isBackendConnected = false;

// ============================================
// INITIALIZATION
// ============================================

/**
 * Initialize the application
 */
async function initializeApp() {
  console.log('🚀 Initializing MAARS OS...');
  
  // Check backend health
  try {
    const health = await maarsAPI.healthCheck();
    console.log('Backend health:', health);
    
    isBackendConnected = Object.values(health).some(status => status === true);
    
    if (isBackendConnected) {
      console.log('✅ Backend services connected');
      showNotification('✅ Connected to MAARS OS backend', 'success');
      
      // Connect WebSocket for real-time updates
      connectRealTimeUpdates();
    } else {
      console.warn('⚠️ Backend services not available - running in demo mode');
      showNotification('⚠️ Running in demo mode - backend not connected', 'warning');
    }
  } catch (error) {
    console.error('❌ Backend connection failed:', error);
    showNotification('⚠️ Running in demo mode - backend not available', 'warning');
  }
}

/**
 * Connect WebSocket for real-time updates
 */
function connectRealTimeUpdates() {
  maarsAPI.connectWebSocket({
    onConnect: () => {
      console.log('🔌 WebSocket connected');
    },
    onSwarmUpdate: (data) => {
      console.log('Swarm update:', data);
      if (window.handleSwarmUpdate) {
        window.handleSwarmUpdate(data);
      }
    },
    onAgentUpdate: (data) => {
      console.log('Agent update:', data);
      if (window.handleAgentUpdate) {
        window.handleAgentUpdate(data);
      }
    },
    onMetricUpdate: (data) => {
      console.log('Metric update:', data);
      if (window.handleMetricUpdate) {
        window.handleMetricUpdate(data);
      }
    },
    onGuardrail: (data) => {
      console.log('Guardrail event:', data);
      if (window.handleGuardrailEvent) {
        window.handleGuardrailEvent(data);
      }
    },
    onLog: (data) => {
      console.log('Log:', data);
      if (window.handleLogEvent) {
        window.handleLogEvent(data);
      }
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
    },
    onDisconnect: () => {
      console.log('🔌 WebSocket disconnected');
    }
  });
}

// ============================================
// HOME PAGE FUNCTIONS
// ============================================

/**
 * Generate workflow from natural language (HOME.html)
 */
async function generateWorkflow() {
  const input = document.getElementById('buildInput');
  if (!input) return;
  
  const description = input.value.trim();
  if (!description) {
    showNotification('⚠️ Please enter a description', 'warning');
    return;
  }
  
  showNotification('🤖 Creating workflow...', 'info');
  
  if (isBackendConnected) {
    try {
      const result = await maarsAPI.createWorkflow(description);
      console.log('Workflow created:', result);
      
      currentWorkflowId = result.workflow_id;
      showNotification('✅ Workflow created successfully!', 'success');
      
      // Navigate to canvas with workflow ID
      setTimeout(() => {
        window.location.href = `UNIVERSAL_HUB.html?workflow=${result.workflow_id}`;
      }, 1000);
    } catch (error) {
      console.error('Error creating workflow:', error);
      showNotification('❌ Failed to create workflow', 'error');
    }
  } else {
    // Demo mode - simulate workflow creation
    setTimeout(() => {
      showNotification('✅ Demo workflow created!', 'success');
      setTimeout(() => {
        window.location.href = `UNIVERSAL_HUB.html?custom=${encodeURIComponent(description)}`;
      }, 1000);
    }, 1500);
  }
}

/**
 * Navigate to use case template
 */
function navigateToUseCase(useCase) {
  showNotification(`🚀 Loading ${useCase} template...`, 'info');
  setTimeout(() => {
    window.location.href = `UNIVERSAL_HUB.html?template=${encodeURIComponent(useCase)}`;
  }, 500);
}

// ============================================
// CANVAS PAGE FUNCTIONS (UNIVERSAL_HUB.html)
// ============================================

/**
 * Load workflow data for canvas
 */
async function loadWorkflowData(workflowId) {
  if (!isBackendConnected) {
    console.log('Demo mode - using mock workflow data');
    return null;
  }
  
  try {
    const workflow = await maarsAPI.getWorkflow(workflowId);
    console.log('Workflow loaded:', workflow);
    return workflow;
  } catch (error) {
    console.error('Error loading workflow:', error);
    showNotification('❌ Failed to load workflow', 'error');
    return null;
  }
}

/**
 * Execute workflow (Run All button)
 */
async function executeWorkflow(workflowId) {
  if (!workflowId) {
    showNotification('⚠️ No workflow selected', 'warning');
    return;
  }
  
  showNotification('▶️ Executing workflow...', 'info');
  
  if (isBackendConnected) {
    try {
      const result = await maarsAPI.executeWorkflow(workflowId);
      console.log('Workflow execution started:', result);
      showNotification('✅ Workflow execution started!', 'success');
    } catch (error) {
      console.error('Error executing workflow:', error);
      showNotification('❌ Failed to execute workflow', 'error');
    }
  } else {
    // Demo mode
    setTimeout(() => {
      showNotification('✅ Demo execution started!', 'success');
    }, 1000);
  }
}

/**
 * Pause workflow
 */
async function pauseWorkflow(workflowId) {
  if (!workflowId) return;
  
  showNotification('⏸️ Pausing workflow...', 'info');
  
  if (isBackendConnected) {
    try {
      await maarsAPI.pauseWorkflow(workflowId);
      showNotification('✅ Workflow paused', 'success');
    } catch (error) {
      console.error('Error pausing workflow:', error);
      showNotification('❌ Failed to pause workflow', 'error');
    }
  } else {
    setTimeout(() => {
      showNotification('✅ Demo workflow paused', 'success');
    }, 500);
  }
}

// ============================================
// LIVE DASHBOARD FUNCTIONS
// ============================================

/**
 * Load dashboard data
 */
async function loadDashboardData() {
  if (!isBackendConnected) {
    console.log('Demo mode - using mock dashboard data');
    return null;
  }
  
  try {
    const data = await maarsAPI.getDashboardData();
    console.log('Dashboard data loaded:', data);
    return data;
  } catch (error) {
    console.error('Error loading dashboard data:', error);
    return null;
  }
}

/**
 * Approve guardrail action
 */
async function approveGuardrail(eventId) {
  showNotification('✅ Approving action...', 'info');
  
  if (isBackendConnected) {
    try {
      await maarsAPI.approveGuardrail(eventId);
      showNotification('✅ Action approved', 'success');
      
      // Refresh dashboard
      if (window.refreshDashboard) {
        window.refreshDashboard();
      }
    } catch (error) {
      console.error('Error approving guardrail:', error);
      showNotification('❌ Failed to approve action', 'error');
    }
  } else {
    setTimeout(() => {
      showNotification('✅ Demo action approved', 'success');
    }, 500);
  }
}

/**
 * Reject guardrail action
 */
async function rejectGuardrail(eventId) {
  showNotification('❌ Rejecting action...', 'info');
  
  if (isBackendConnected) {
    try {
      await maarsAPI.rejectGuardrail(eventId);
      showNotification('✅ Action rejected', 'success');
      
      // Refresh dashboard
      if (window.refreshDashboard) {
        window.refreshDashboard();
      }
    } catch (error) {
      console.error('Error rejecting guardrail:', error);
      showNotification('❌ Failed to reject action', 'error');
    }
  } else {
    setTimeout(() => {
      showNotification('✅ Demo action rejected', 'success');
    }, 500);
  }
}

/**
 * Update system metrics display
 */
function updateMetricsDisplay(metrics) {
  // Update CPU
  const cpuElement = document.querySelector('.metric-value[data-metric="cpu"]');
  if (cpuElement && metrics.cpu) {
    cpuElement.textContent = `${metrics.cpu}%`;
  }
  
  // Update Memory
  const memoryElement = document.querySelector('.metric-value[data-metric="memory"]');
  if (memoryElement && metrics.memory) {
    memoryElement.textContent = metrics.memory;
  }
  
  // Update Token Usage
  const tokenElement = document.querySelector('.metric-value[data-metric="tokens"]');
  if (tokenElement && metrics.tokens) {
    tokenElement.textContent = metrics.tokens;
  }
}

// ============================================
// AGENT CREATOR FUNCTIONS
// ============================================

/**
 * Create agent from form
 */
async function createAgentFromForm(formData) {
  showNotification('🤖 Creating agent...', 'info');
  
  if (isBackendConnected) {
    try {
      const result = await maarsAPI.createAgent(
        formData.name,
        formData.description,
        formData.capabilities
      );
      console.log('Agent created:', result);
      showNotification('✅ Agent created successfully!', 'success');
      return result;
    } catch (error) {
      console.error('Error creating agent:', error);
      showNotification('❌ Failed to create agent', 'error');
      return null;
    }
  } else {
    // Demo mode
    return new Promise((resolve) => {
      setTimeout(() => {
        showNotification('✅ Demo agent created!', 'success');
        resolve({
          agent_id: 'demo-' + Date.now(),
          name: formData.name,
          status: 'idle'
        });
      }, 1000);
    });
  }
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

/**
 * Show notification to user
 */
function showNotification(message, type = 'info') {
  // Try to use existing notification system
  if (window.showNotification && typeof window.showNotification === 'function') {
    window.showNotification(message, type);
    return;
  }
  
  // Fallback: create simple notification
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  notification.style.cssText = `
    position: fixed;
    top: 80px;
    right: 20px;
    padding: 16px 24px;
    background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#3b82f6'};
    color: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    z-index: 10000;
    animation: slideIn 0.3s ease-out;
  `;
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease-out';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

/**
 * Get URL parameter
 */
function getURLParameter(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

/**
 * Format timestamp
 */
function formatTimestamp(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleString();
}

/**
 * Format currency
 */
function formatCurrency(amount) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(amount);
}

// ============================================
// EXPORT FUNCTIONS
// ============================================

// Make functions available globally
window.maarsAPI = maarsAPI;
window.generateWorkflow = generateWorkflow;
window.navigateToUseCase = navigateToUseCase;
window.loadWorkflowData = loadWorkflowData;
window.executeWorkflow = executeWorkflow;
window.pauseWorkflow = pauseWorkflow;
window.loadDashboardData = loadDashboardData;
window.approveGuardrail = approveGuardrail;
window.rejectGuardrail = rejectGuardrail;
window.updateMetricsDisplay = updateMetricsDisplay;
window.createAgentFromForm = createAgentFromForm;
window.getURLParameter = getURLParameter;
window.formatTimestamp = formatTimestamp;
window.formatCurrency = formatCurrency;

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp);
} else {
  initializeApp();
}

console.log('✅ MAARS OS Integration loaded');

// Made with Bob
