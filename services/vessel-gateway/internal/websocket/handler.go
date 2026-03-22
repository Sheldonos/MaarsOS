package websocket

import (
	"log"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		// In production, validate origin against allowed domains
		return true
	},
}

// Handler manages WebSocket connections
type Handler struct {
	hub *Hub
}

// NewHandler creates a new WebSocket handler
func NewHandler(hub *Hub) *Handler {
	return &Handler{
		hub: hub,
	}
}

// ServeSwarmChannel handles WebSocket connections for the swarm channel
func (h *Handler) ServeSwarmChannel(c *gin.Context) {
	h.serveChannel(c, ChannelSwarm)
}

// ServeGuardrailsChannel handles WebSocket connections for the guardrails channel
func (h *Handler) ServeGuardrailsChannel(c *gin.Context) {
	h.serveChannel(c, ChannelGuardrails)
}

// ServeCostsChannel handles WebSocket connections for the costs channel
func (h *Handler) ServeCostsChannel(c *gin.Context) {
	h.serveChannel(c, ChannelCosts)
}

// ServeSimulationChannel handles WebSocket connections for the simulation channel
func (h *Handler) ServeSimulationChannel(c *gin.Context) {
	h.serveChannel(c, ChannelSimulation)
}

// serveChannel is the generic handler for all WebSocket channels
func (h *Handler) serveChannel(c *gin.Context, channel ChannelName) {
	// Extract tenant_id from JWT claims (set by auth middleware)
	tenantID, exists := c.Get("tenant_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Missing tenant_id"})
		return
	}

	// Upgrade HTTP connection to WebSocket
	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("[WebSocket] Upgrade error: %v", err)
		return
	}

	// Create client
	client := &Client{
		ID:       uuid.New().String(),
		TenantID: tenantID.(string),
		Channel:  channel,
		Conn:     conn,
		Send:     make(chan []byte, 256),
		Hub:      h.hub,
	}

	// Register client with hub
	h.hub.register <- client

	// Start client goroutines
	go client.WritePump()
	go client.ReadPump()

	log.Printf("[WebSocket] Client connected: channel=%s tenant=%s client=%s",
		channel, tenantID, client.ID)
}

// GetStats returns WebSocket statistics
func (h *Handler) GetStats(c *gin.Context) {
	stats := h.hub.GetStats()
	c.JSON(http.StatusOK, gin.H{
		"websocket_stats": stats,
	})
}

// Made with Bob
