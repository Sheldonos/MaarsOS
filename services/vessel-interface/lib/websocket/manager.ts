import { io, Socket } from 'socket.io-client';

export type ChannelName = 'swarm' | 'guardrails' | 'costs' | 'simulation';

export interface WSEvent {
  event_id: string;
  event_type: string;
  tenant_id: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

export type WSEventHandler = (event: WSEvent) => void;

interface ChannelConnection {
  ws: WebSocket | null;
  handlers: Set<WSEventHandler>;
  reconnectAttempts: number;
  reconnectTimer: NodeJS.Timeout | null;
}

export class WebSocketManager {
  private baseUrl: string;
  private token: string | null = null;
  private channels: Map<ChannelName, ChannelConnection> = new Map();
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000; // 3 seconds

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
  }

  /**
   * Set the JWT token for authentication
   */
  setToken(token: string): void {
    this.token = token;
  }

  /**
   * Connect to a specific channel
   */
  connect(channel: ChannelName, handler: WSEventHandler): void {
    if (!this.token) {
      console.error('[WebSocket] Cannot connect without token');
      return;
    }

    // Initialize channel connection if it doesn't exist
    if (!this.channels.has(channel)) {
      this.channels.set(channel, {
        ws: null,
        handlers: new Set(),
        reconnectAttempts: 0,
        reconnectTimer: null,
      });
    }

    const connection = this.channels.get(channel)!;
    connection.handlers.add(handler);

    // Connect if not already connected
    if (!connection.ws || connection.ws.readyState === WebSocket.CLOSED) {
      this.connectChannel(channel);
    }
  }

  /**
   * Disconnect from a specific channel
   */
  disconnect(channel: ChannelName, handler?: WSEventHandler): void {
    const connection = this.channels.get(channel);
    if (!connection) return;

    if (handler) {
      connection.handlers.delete(handler);
    }

    // If no handlers left, close the connection
    if (connection.handlers.size === 0) {
      this.closeChannel(channel);
    }
  }

  /**
   * Disconnect from all channels
   */
  disconnectAll(): void {
    this.channels.forEach((_, channel) => {
      this.closeChannel(channel);
    });
    this.channels.clear();
  }

  /**
   * Get connection status for a channel
   */
  getStatus(channel: ChannelName): 'connected' | 'connecting' | 'disconnected' {
    const connection = this.channels.get(channel);
    if (!connection || !connection.ws) return 'disconnected';

    switch (connection.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      default:
        return 'disconnected';
    }
  }

  /**
   * Internal: Connect to a channel
   */
  private connectChannel(channel: ChannelName): void {
    const connection = this.channels.get(channel);
    if (!connection) return;

    const url = `${this.baseUrl}/ws/${channel}`;
    console.log(`[WebSocket] Connecting to ${channel}...`);

    try {
      const ws = new WebSocket(url);

      // Set auth header (WebSocket doesn't support custom headers directly,
      // so we'll send it as the first message after connection)
      ws.onopen = () => {
        console.log(`[WebSocket] Connected to ${channel}`);
        connection.reconnectAttempts = 0;

        // Send authentication
        if (this.token) {
          ws.send(JSON.stringify({
            type: 'auth',
            token: this.token,
          }));
        }

        // Send ping to keep connection alive
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          } else {
            clearInterval(pingInterval);
          }
        }, 30000); // 30 seconds
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Handle pong response
          if (data.type === 'pong') {
            return;
          }

          // Parse as WSEvent and notify handlers
          const wsEvent = data as WSEvent;
          connection.handlers.forEach((handler) => {
            try {
              handler(wsEvent);
            } catch (error) {
              console.error(`[WebSocket] Handler error on ${channel}:`, error);
            }
          });
        } catch (error) {
          console.error(`[WebSocket] Parse error on ${channel}:`, error);
        }
      };

      ws.onerror = (error) => {
        console.error(`[WebSocket] Error on ${channel}:`, error);
      };

      ws.onclose = () => {
        console.log(`[WebSocket] Disconnected from ${channel}`);
        connection.ws = null;

        // Attempt reconnection if handlers still exist
        if (connection.handlers.size > 0) {
          this.scheduleReconnect(channel);
        }
      };

      connection.ws = ws;
    } catch (error) {
      console.error(`[WebSocket] Connection error on ${channel}:`, error);
      this.scheduleReconnect(channel);
    }
  }

  /**
   * Internal: Schedule reconnection attempt
   */
  private scheduleReconnect(channel: ChannelName): void {
    const connection = this.channels.get(channel);
    if (!connection) return;

    // Clear existing timer
    if (connection.reconnectTimer) {
      clearTimeout(connection.reconnectTimer);
    }

    // Check if we've exceeded max attempts
    if (connection.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error(`[WebSocket] Max reconnect attempts reached for ${channel}`);
      return;
    }

    connection.reconnectAttempts++;
    const delay = this.reconnectDelay * connection.reconnectAttempts;

    console.log(`[WebSocket] Reconnecting to ${channel} in ${delay}ms (attempt ${connection.reconnectAttempts})`);

    connection.reconnectTimer = setTimeout(() => {
      this.connectChannel(channel);
    }, delay);
  }

  /**
   * Internal: Close a channel connection
   */
  private closeChannel(channel: ChannelName): void {
    const connection = this.channels.get(channel);
    if (!connection) return;

    // Clear reconnect timer
    if (connection.reconnectTimer) {
      clearTimeout(connection.reconnectTimer);
      connection.reconnectTimer = null;
    }

    // Close WebSocket
    if (connection.ws) {
      connection.ws.close();
      connection.ws = null;
    }

    // Clear handlers
    connection.handlers.clear();
  }
}

// Singleton instance
let wsManager: WebSocketManager | null = null;

export function getWebSocketManager(): WebSocketManager {
  if (!wsManager) {
    wsManager = new WebSocketManager();
  }
  return wsManager;
}

// Made with Bob
