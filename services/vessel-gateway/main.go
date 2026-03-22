package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"

	"github.com/maars/vessel-gateway/internal/config"
	"github.com/maars/vessel-gateway/internal/middleware"
	"github.com/maars/vessel-gateway/internal/proxy"
	"github.com/maars/vessel-gateway/internal/websocket"
)

func main() {
	// Initialize logger
	logger, err := zap.NewProduction()
	if err != nil {
		panic(fmt.Sprintf("Failed to initialize logger: %v", err))
	}
	defer logger.Sync()

	// Load configuration
	cfg := config.Load()
	logger.Info("Configuration loaded",
		zap.String("service", cfg.ServiceName),
		zap.String("version", cfg.ServiceVersion),
		zap.String("port", cfg.Port),
	)

	// Set Gin mode
	if cfg.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	// Initialize WebSocket hub
	hub := websocket.NewHub()
	go hub.Run()
	logger.Info("WebSocket hub started")

	// Initialize WebSocket handler
	wsHandler := websocket.NewHandler(hub)

	// Create router
	router := gin.New()

	// Global middleware
	router.Use(gin.Recovery())
	router.Use(middleware.Logger(logger))
	router.Use(middleware.CORS())

	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":  "healthy",
			"service": cfg.ServiceName,
			"version": cfg.ServiceVersion,
		})
	})

	// Initialize rate limiter
	rateLimiter := middleware.NewRateLimiter(cfg.Redis)

	// Initialize JWT middleware
	jwtMiddleware := middleware.NewJWTMiddleware(cfg.JWT)

	// Initialize proxy
	orchestratorProxy := proxy.NewProxy(cfg.OrchestratorURL, logger)

	// WebSocket routes (with authentication, no rate limiting for persistent connections)
	ws := router.Group("/ws")
	ws.Use(jwtMiddleware.Authenticate())
	{
		ws.GET("/swarm", wsHandler.ServeSwarmChannel)
		ws.GET("/guardrails", wsHandler.ServeGuardrailsChannel)
		ws.GET("/costs", wsHandler.ServeCostsChannel)
		ws.GET("/simulation", wsHandler.ServeSimulationChannel)
		ws.GET("/stats", wsHandler.GetStats)
	}

	// API routes with authentication and rate limiting
	v1 := router.Group("/v1")
	v1.Use(jwtMiddleware.Authenticate())
	v1.Use(rateLimiter.Limit())
	{
		// Proxy all /v1/goals requests to vessel-orchestrator
		v1.Any("/goals/*path", orchestratorProxy.Handler())
		v1.Any("/goals", orchestratorProxy.Handler())

		// Proxy task endpoints
		v1.Any("/tasks/*path", orchestratorProxy.Handler())
	}

	// Create HTTP server
	srv := &http.Server{
		Addr:         ":" + cfg.Port,
		Handler:      router,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	// Start server in goroutine
	go func() {
		logger.Info("Starting vessel-gateway",
			zap.String("addr", srv.Addr),
		)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("Failed to start server", zap.Error(err))
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("Shutting down server...")

	// Graceful shutdown with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		logger.Fatal("Server forced to shutdown", zap.Error(err))
	}

	logger.Info("Server exited")
}

// Made with Bob
