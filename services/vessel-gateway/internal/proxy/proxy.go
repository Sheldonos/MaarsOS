package proxy

import (
	"bytes"
	"io"
	"net/http"
	"net/url"
	"time"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
)

// Proxy handles proxying requests to backend services
type Proxy struct {
	targetURL *url.URL
	client    *http.Client
	logger    *zap.Logger
}

// NewProxy creates a new proxy instance
func NewProxy(targetURL string, logger *zap.Logger) *Proxy {
	parsedURL, err := url.Parse(targetURL)
	if err != nil {
		panic("Invalid target URL: " + targetURL)
	}

	return &Proxy{
		targetURL: parsedURL,
		client: &http.Client{
			Timeout: 60 * time.Second,
			Transport: &http.Transport{
				MaxIdleConns:        100,
				MaxIdleConnsPerHost: 10,
				IdleConnTimeout:     90 * time.Second,
			},
		},
		logger: logger,
	}
}

// Handler returns a Gin handler function that proxies requests
func (p *Proxy) Handler() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Build target URL
		targetURL := *p.targetURL
		targetURL.Path = c.Request.URL.Path
		targetURL.RawQuery = c.Request.URL.RawQuery

		p.logger.Debug("Proxying request",
			zap.String("method", c.Request.Method),
			zap.String("path", c.Request.URL.Path),
			zap.String("target", targetURL.String()),
		)

		// Read request body
		var bodyBytes []byte
		if c.Request.Body != nil {
			bodyBytes, _ = io.ReadAll(c.Request.Body)
			c.Request.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))
		}

		// Create proxy request
		proxyReq, err := http.NewRequest(c.Request.Method, targetURL.String(), bytes.NewBuffer(bodyBytes))
		if err != nil {
			p.logger.Error("Failed to create proxy request", zap.Error(err))
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to proxy request"})
			return
		}

		// Copy headers (except Host)
		for key, values := range c.Request.Header {
			if key == "Host" {
				continue
			}
			for _, value := range values {
				proxyReq.Header.Add(key, value)
			}
		}

		// Add tenant_id from JWT claims if available
		if tenantID, exists := c.Get("tenant_id"); exists {
			proxyReq.Header.Set("X-Tenant-ID", tenantID.(string))
		}

		// Add user_id from JWT claims if available
		if userID, exists := c.Get("user_id"); exists {
			proxyReq.Header.Set("X-User-ID", userID.(string))
		}

		// Execute proxy request
		start := time.Now()
		resp, err := p.client.Do(proxyReq)
		if err != nil {
			p.logger.Error("Proxy request failed",
				zap.Error(err),
				zap.String("target", targetURL.String()),
			)
			c.JSON(http.StatusBadGateway, gin.H{"error": "Backend service unavailable"})
			return
		}
		defer resp.Body.Close()

		latency := time.Since(start)
		p.logger.Debug("Proxy request completed",
			zap.Int("status", resp.StatusCode),
			zap.Duration("latency", latency),
		)

		// Copy response headers
		for key, values := range resp.Header {
			for _, value := range values {
				c.Writer.Header().Add(key, value)
			}
		}

		// Copy response body
		c.Status(resp.StatusCode)
		io.Copy(c.Writer, resp.Body)
	}
}

// Made with Bob
