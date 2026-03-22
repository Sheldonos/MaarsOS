package middleware

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"

	"github.com/maars/vessel-gateway/internal/config"
)

// Logger returns a Gin middleware for structured logging
func Logger(logger *zap.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path
		query := c.Request.URL.RawQuery

		c.Next()

		latency := time.Since(start)
		statusCode := c.Writer.Status()

		logger.Info("HTTP request",
			zap.String("method", c.Request.Method),
			zap.String("path", path),
			zap.String("query", query),
			zap.Int("status", statusCode),
			zap.Duration("latency", latency),
			zap.String("client_ip", c.ClientIP()),
		)
	}
}

// CORS returns a Gin middleware for CORS handling
func CORS() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, accept, origin, Cache-Control, X-Requested-With")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT, DELETE, PATCH")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	}
}

// JWTMiddleware handles JWT authentication
type JWTMiddleware struct {
	config config.JWTConfig
}

// NewJWTMiddleware creates a new JWT middleware
func NewJWTMiddleware(cfg config.JWTConfig) *JWTMiddleware {
	return &JWTMiddleware{config: cfg}
}

// Authenticate validates JWT tokens
func (m *JWTMiddleware) Authenticate() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Get token from Authorization header
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Authorization header required"})
			c.Abort()
			return
		}

		// Extract token from "Bearer <token>"
		parts := strings.Split(authHeader, " ")
		if len(parts) != 2 || parts[0] != "Bearer" {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid authorization header format"})
			c.Abort()
			return
		}

		tokenString := parts[1]

		// Parse and validate token
		token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
			// Validate signing method
			if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
			}
			return []byte(m.config.Secret), nil
		})

		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid token"})
			c.Abort()
			return
		}

		if !token.Valid {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Token is not valid"})
			c.Abort()
			return
		}

		// Extract claims
		if claims, ok := token.Claims.(jwt.MapClaims); ok {
			// Store claims in context
			c.Set("user_id", claims["sub"])
			c.Set("tenant_id", claims["tenant_id"])
			c.Set("role", claims["role"])
		}

		c.Next()
	}
}

// RateLimiter implements rate limiting using Redis
type RateLimiter struct {
	client *redis.Client
}

// NewRateLimiter creates a new rate limiter
func NewRateLimiter(cfg config.RedisConfig) *RateLimiter {
	opt, err := redis.ParseURL(cfg.URL)
	if err != nil {
		panic(fmt.Sprintf("Failed to parse Redis URL: %v", err))
	}

	client := redis.NewClient(opt)

	// Test connection
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := client.Ping(ctx).Err(); err != nil {
		panic(fmt.Sprintf("Failed to connect to Redis: %v", err))
	}

	return &RateLimiter{client: client}
}

// Limit applies rate limiting
func (rl *RateLimiter) Limit() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Get user identifier (IP or user_id from JWT)
		identifier := c.ClientIP()
		if userID, exists := c.Get("user_id"); exists {
			identifier = fmt.Sprintf("user:%v", userID)
		}

		// Rate limit key
		key := fmt.Sprintf("ratelimit:%s", identifier)

		ctx := context.Background()

		// Increment counter
		count, err := rl.client.Incr(ctx, key).Result()
		if err != nil {
			// If Redis fails, allow the request (fail open)
			c.Next()
			return
		}

		// Set expiry on first request
		if count == 1 {
			rl.client.Expire(ctx, key, time.Minute)
		}

		// Rate limit: 100 requests per minute
		limit := int64(100)
		if count > limit {
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error": "Rate limit exceeded",
				"retry_after": 60,
			})
			c.Abort()
			return
		}

		// Add rate limit headers
		c.Header("X-RateLimit-Limit", fmt.Sprintf("%d", limit))
		c.Header("X-RateLimit-Remaining", fmt.Sprintf("%d", limit-count))

		c.Next()
	}
}

// AgentPairingMiddleware enforces OpenClaw-style agent-to-agent allowlist
type AgentPairingMiddleware struct {
	client *redis.Client
	logger *zap.Logger
}

// NewAgentPairingMiddleware creates a new agent pairing middleware
func NewAgentPairingMiddleware(cfg config.RedisConfig, logger *zap.Logger) *AgentPairingMiddleware {
	opt, err := redis.ParseURL(cfg.URL)
	if err != nil {
		panic(fmt.Sprintf("Failed to parse Redis URL for pairing: %v", err))
	}

	client := redis.NewClient(opt)

	// Test connection
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := client.Ping(ctx).Err(); err != nil {
		panic(fmt.Sprintf("Failed to connect to Redis for pairing: %v", err))
	}

	return &AgentPairingMiddleware{
		client: client,
		logger: logger,
	}
}

// EnforcePairing checks if agent-to-agent communication is authorized
func (apm *AgentPairingMiddleware) EnforcePairing() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Get source and target agent IDs from headers/params
		sourceAgent := c.GetHeader("X-Source-Agent-ID")
		targetAgent := c.Param("agent_id") // For routes like /agents/:agent_id/message
		
		// If no agent-to-agent communication, skip check
		if sourceAgent == "" || targetAgent == "" {
			c.Next()
			return
		}

		// Check if pairing exists in Redis
		pairingKey := fmt.Sprintf("agent_pairing:%s:%s", sourceAgent, targetAgent)
		ctx := context.Background()
		
		exists, err := apm.client.Exists(ctx, pairingKey).Result()
		if err != nil {
			apm.logger.Error("Failed to check agent pairing",
				zap.Error(err),
				zap.String("source_agent", sourceAgent),
				zap.String("target_agent", targetAgent),
			)
			// Fail closed - deny access on error
			c.JSON(http.StatusForbidden, gin.H{
				"error": "Agent pairing verification failed",
			})
			c.Abort()
			return
		}

		if exists == 0 {
			apm.logger.Warn("Agent pairing not authorized",
				zap.String("source_agent", sourceAgent),
				zap.String("target_agent", targetAgent),
			)
			c.JSON(http.StatusForbidden, gin.H{
				"error": "Agent pairing not authorized. Strict allowlist enforced (OpenClaw-style).",
			})
			c.Abort()
			return
		}

		apm.logger.Debug("Agent pairing authorized",
			zap.String("source_agent", sourceAgent),
			zap.String("target_agent", targetAgent),
		)
		
		c.Next()
	}
}

// Made with Bob
