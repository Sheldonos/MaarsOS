package websocket

import (
	"encoding/json"
	"log"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// ChannelName represents the WebSocket channel type
type ChannelName string

const (
	ChannelSwarm       ChannelName = "swarm"
	ChannelGuardrails  ChannelName = "guardrails"
	ChannelCosts       ChannelName = "costs"
	ChannelSimulation  ChannelName = "simulation"
)

// Client represents a WebSocket client connection
type Client struct {
	ID        string
	TenantID  string
	Channel   ChannelName
	Conn      *websocket.Conn
	Send      chan []byte
	Hub       *Hub
	mu        sync.Mutex
}

// Hub maintains the set of active clients and broadcasts messages
type Hub struct {
	// Registered clients by channel and tenant
	clients map[ChannelName]map[string]map[*Client]bool // channel -> tenant_id -> clients

	// Register requests from clients
	register chan *Client

	// Unregister requests from clients
	unregister chan *Client

	// Broadcast messages to clients
	broadcast chan *BroadcastMessage

	// Mutex for thread-safe operations
	mu sync.RWMutex
}

// BroadcastMessage represents a message to broadcast
type BroadcastMessage struct {
	Channel  ChannelName
	TenantID string
	Payload  []byte
}

// WSEvent represents the unified WebSocket event envelope
type WSEvent struct {
	EventID   string                 `json:"event_id"`
	EventType string                 `json:"event_type"`
	TenantID  string                 `json:"tenant_id"`
	Timestamp string                 `json:"timestamp"`
	Payload   map[string]interface{} `json:"payload"`
}

// NewHub creates a new Hub instance
func NewHub() *Hub {
	return &Hub{
		clients:    make(map[ChannelName]map[string]map[*Client]bool),
		register:   make(chan *Client),
		unregister: make(chan *Client),
		broadcast:  make(chan *BroadcastMessage, 256),
	}
}

// Run starts the hub's main loop
func (h *Hub) Run() {
	for {
		select {
		case client := <-h.register:
			h.registerClient(client)

		case client := <-h.unregister:
			h.unregisterClient(client)

		case message := <-h.broadcast:
			h.broadcastToChannel(message)
		}
	}
}

// registerClient adds a client to the hub
func (h *Hub) registerClient(client *Client) {
	h.mu.Lock()
	defer h.mu.Unlock()

	// Initialize channel map if needed
	if h.clients[client.Channel] == nil {
		h.clients[client.Channel] = make(map[string]map[*Client]bool)
	}

	// Initialize tenant map if needed
	if h.clients[client.Channel][client.TenantID] == nil {
		h.clients[client.Channel][client.TenantID] = make(map[*Client]bool)
	}

	// Add client
	h.clients[client.Channel][client.TenantID][client] = true

	log.Printf("[WebSocket] Client registered: channel=%s tenant=%s client=%s",
		client.Channel, client.TenantID, client.ID)
}

// unregisterClient removes a client from the hub
func (h *Hub) unregisterClient(client *Client) {
	h.mu.Lock()
	defer h.mu.Unlock()

	if tenants, ok := h.clients[client.Channel]; ok {
		if clients, ok := tenants[client.TenantID]; ok {
			if _, ok := clients[client]; ok {
				delete(clients, client)
				close(client.Send)

				// Clean up empty maps
				if len(clients) == 0 {
					delete(tenants, client.TenantID)
				}
				if len(tenants) == 0 {
					delete(h.clients, client.Channel)
				}

				log.Printf("[WebSocket] Client unregistered: channel=%s tenant=%s client=%s",
					client.Channel, client.TenantID, client.ID)
			}
		}
	}
}

// broadcastToChannel sends a message to all clients in a channel for a specific tenant
func (h *Hub) broadcastToChannel(message *BroadcastMessage) {
	h.mu.RLock()
	defer h.mu.RUnlock()

	if tenants, ok := h.clients[message.Channel]; ok {
		if clients, ok := tenants[message.TenantID]; ok {
			for client := range clients {
				select {
				case client.Send <- message.Payload:
					// Message sent successfully
				default:
					// Client's send buffer is full, close the connection
					go func(c *Client) {
						h.unregister <- c
					}(client)
				}
			}
		}
	}
}

// Broadcast sends a message to a specific channel and tenant
func (h *Hub) Broadcast(channel ChannelName, tenantID string, payload []byte) {
	h.broadcast <- &BroadcastMessage{
		Channel:  channel,
		TenantID: tenantID,
		Payload:  payload,
	}
}

// GetStats returns statistics about connected clients
func (h *Hub) GetStats() map[string]interface{} {
	h.mu.RLock()
	defer h.mu.RUnlock()

	stats := make(map[string]interface{})
	totalClients := 0

	for channel, tenants := range h.clients {
		channelStats := make(map[string]int)
		for tenantID, clients := range tenants {
			count := len(clients)
			channelStats[tenantID] = count
			totalClients += count
		}
		stats[string(channel)] = channelStats
	}

	stats["total_clients"] = totalClients
	return stats
}

// ReadPump pumps messages from the WebSocket connection to the hub
func (c *Client) ReadPump() {
	defer func() {
		c.Hub.unregister <- c
		c.Conn.Close()
	}()

	c.Conn.SetReadDeadline(time.Now().Add(60 * time.Second))
	c.Conn.SetPongHandler(func(string) error {
		c.Conn.SetReadDeadline(time.Now().Add(60 * time.Second))
		return nil
	})

	for {
		_, message, err := c.Conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("[WebSocket] Read error: %v", err)
			}
			break
		}

		// Handle incoming messages (e.g., ping/pong, subscriptions)
		var msg map[string]interface{}
		if err := json.Unmarshal(message, &msg); err == nil {
			if msgType, ok := msg["type"].(string); ok && msgType == "ping" {
				c.Send <- []byte(`{"type":"pong"}`)
			}
		}
	}
}

// WritePump pumps messages from the hub to the WebSocket connection
func (c *Client) WritePump() {
	ticker := time.NewTicker(54 * time.Second)
	defer func() {
		ticker.Stop()
		c.Conn.Close()
	}()

	for {
		select {
		case message, ok := <-c.Send:
			c.Conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if !ok {
				// Hub closed the channel
				c.Conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			w, err := c.Conn.NextWriter(websocket.TextMessage)
			if err != nil {
				return
			}
			w.Write(message)

			// Add queued messages to the current WebSocket message
			n := len(c.Send)
			for i := 0; i < n; i++ {
				w.Write([]byte{'\n'})
				w.Write(<-c.Send)
			}

			if err := w.Close(); err != nil {
				return
			}

		case <-ticker.C:
			c.Conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if err := c.Conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

// Made with Bob
