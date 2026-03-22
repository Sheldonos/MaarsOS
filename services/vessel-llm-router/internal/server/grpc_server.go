package server

import (
	"context"
	"fmt"
	"net"
	"net/http"

	"github.com/maars/vessel-llm-router/internal/cache"
	"github.com/maars/vessel-llm-router/internal/config"
	"github.com/maars/vessel-llm-router/internal/providers"
	pb "github.com/maars/vessel-llm-router/proto"
	"go.uber.org/zap"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/health"
	"google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/reflection"
	"google.golang.org/grpc/status"
)

// Server implements the LLM Router gRPC server
type Server struct {
	pb.UnimplementedLLMRouterServer
	config    *config.Config
	provider  providers.Provider
	providers map[string]providers.Provider // MiniMax-01: Multiple providers for MoE routing
	cache     *cache.SemanticCache
	logger    *zap.Logger
}

// NewServer creates a new gRPC server instance
func NewServer(cfg *config.Config, provider providers.Provider, cache *cache.SemanticCache, logger *zap.Logger) *Server {
	return &Server{
		config:   cfg,
		provider: provider,
		cache:    cache,
		logger:   logger,
	}
}

// RoutePrompt handles synchronous LLM completion requests
func (s *Server) RoutePrompt(ctx context.Context, req *pb.RouteRequest) (*pb.RouteResponse, error) {
	s.logger.Info("Received RoutePrompt request",
		zap.String("task_id", req.TaskId),
		zap.String("tenant_id", req.TenantId),
		zap.String("model_tier", req.ModelTier),
		zap.Int("message_count", len(req.Messages)),
	)

	// Validate request
	if err := s.validateRequest(req); err != nil {
		s.logger.Warn("Invalid request",
			zap.Error(err),
			zap.String("task_id", req.TaskId),
		)
		return nil, status.Errorf(codes.InvalidArgument, "invalid request: %v", err)
	}

	// Convert proto request to provider request
	providerReq := s.convertToProviderRequest(req)

	// Check cache first
	cachedResp, cacheHit, err := s.cache.Get(ctx, providerReq)
	if err != nil {
		s.logger.Warn("Cache lookup failed",
			zap.Error(err),
			zap.String("task_id", req.TaskId),
		)
	}

	if cacheHit && cachedResp != nil {
		s.logger.Info("Cache hit",
			zap.String("task_id", req.TaskId),
			zap.String("model_used", cachedResp.ModelUsed),
		)

		return &pb.RouteResponse{
			Completion:       cachedResp.Completion,
			ModelUsed:        cachedResp.ModelUsed,
			PromptTokens:     cachedResp.PromptTokens,
			CompletionTokens: cachedResp.CompletionTokens,
			CostUsd:          cachedResp.CostUSD,
			CachedHit:        true,
			FinishReason:     cachedResp.FinishReason,
		}, nil
	}

	// Cache miss - call provider
	s.logger.Debug("Cache miss, calling provider",
		zap.String("task_id", req.TaskId),
		zap.String("provider", s.provider.Name()),
	)

	resp, err := s.provider.Chat(ctx, providerReq)
	if err != nil {
		s.logger.Error("Provider request failed",
			zap.Error(err),
			zap.String("task_id", req.TaskId),
			zap.String("provider", s.provider.Name()),
		)

		// Check if it's a provider error with specific code
		if provErr, ok := err.(*providers.ProviderError); ok {
			if provErr.Retryable {
				return nil, status.Errorf(codes.Unavailable, "provider temporarily unavailable: %v", err)
			}
			return nil, status.Errorf(codes.Internal, "provider error: %v", err)
		}

		return nil, status.Errorf(codes.Internal, "failed to complete request: %v", err)
	}

	// Check cost limit
	if req.MaxCostUsd > 0 && resp.CostUSD > req.MaxCostUsd {
		s.logger.Warn("Cost limit exceeded",
			zap.Float32("cost", resp.CostUSD),
			zap.Float32("limit", req.MaxCostUsd),
			zap.String("task_id", req.TaskId),
		)
		return nil, status.Errorf(codes.ResourceExhausted, "cost limit exceeded: %.4f > %.4f", resp.CostUSD, req.MaxCostUsd)
	}

	// Store in cache for future requests
	if err := s.cache.Set(ctx, providerReq, resp); err != nil {
		s.logger.Warn("Failed to cache response",
			zap.Error(err),
			zap.String("task_id", req.TaskId),
		)
	}

	s.logger.Info("Request completed successfully",
		zap.String("task_id", req.TaskId),
		zap.String("model_used", resp.ModelUsed),
		zap.Int32("prompt_tokens", resp.PromptTokens),
		zap.Int32("completion_tokens", resp.CompletionTokens),
		zap.Float32("cost_usd", resp.CostUSD),
		zap.Duration("latency", resp.Latency),
	)

	return &pb.RouteResponse{
		Completion:       resp.Completion,
		ModelUsed:        resp.ModelUsed,
		PromptTokens:     resp.PromptTokens,
		CompletionTokens: resp.CompletionTokens,
		CostUsd:          resp.CostUSD,
		CachedHit:        false,
		FinishReason:     resp.FinishReason,
	}, nil
}

// StreamPrompt handles streaming LLM completion requests
func (s *Server) StreamPrompt(req *pb.RouteRequest, stream pb.LLMRouter_StreamPromptServer) error {
	s.logger.Info("Received StreamPrompt request",
		zap.String("task_id", req.TaskId),
		zap.String("tenant_id", req.TenantId),
		zap.String("model_tier", req.ModelTier),
	)

	// Validate request
	if err := s.validateRequest(req); err != nil {
		s.logger.Warn("Invalid streaming request",
			zap.Error(err),
			zap.String("task_id", req.TaskId),
		)
		return status.Errorf(codes.InvalidArgument, "invalid request: %v", err)
	}

	// Check if provider supports streaming
	if !s.provider.SupportsStreaming() {
		return status.Errorf(codes.Unimplemented, "provider %s does not support streaming", s.provider.Name())
	}

	// Convert proto request to provider request
	providerReq := s.convertToProviderRequest(req)

	// Start streaming from provider
	chunkChan, errChan := s.provider.StreamChat(stream.Context(), providerReq)

	// Stream chunks to client
	for {
		select {
		case chunk, ok := <-chunkChan:
			if !ok {
				// Channel closed, streaming complete
				return nil
			}

			// Send chunk to client
			streamResp := &pb.StreamResponse{
				Delta:            chunk.Delta,
				ModelUsed:        chunk.ModelUsed,
				IsFinal:          chunk.IsFinal,
				PromptTokens:     chunk.PromptTokens,
				CompletionTokens: chunk.CompletionTokens,
				CostUsd:          chunk.CostUSD,
			}

			if err := stream.Send(streamResp); err != nil {
				s.logger.Error("Failed to send stream chunk",
					zap.Error(err),
					zap.String("task_id", req.TaskId),
				)
				return status.Errorf(codes.Internal, "failed to send stream: %v", err)
			}

			// Log final chunk
			if chunk.IsFinal {
				s.logger.Info("Streaming completed",
					zap.String("task_id", req.TaskId),
					zap.String("model_used", chunk.ModelUsed),
					zap.Int32("prompt_tokens", chunk.PromptTokens),
					zap.Int32("completion_tokens", chunk.CompletionTokens),
					zap.Float32("cost_usd", chunk.CostUSD),
				)
			}

		case err := <-errChan:
			if err != nil {
				s.logger.Error("Streaming error",
					zap.Error(err),
					zap.String("task_id", req.TaskId),
				)
				return status.Errorf(codes.Internal, "streaming failed: %v", err)
			}
			return nil

		case <-stream.Context().Done():
			s.logger.Info("Stream cancelled by client",
				zap.String("task_id", req.TaskId),
			)
			return status.Errorf(codes.Canceled, "stream cancelled")
		}
	}
}

// validateRequest validates the incoming request
func (s *Server) validateRequest(req *pb.RouteRequest) error {
	if req.TaskId == "" {
		return fmt.Errorf("task_id is required")
	}

	if req.TenantId == "" {
		return fmt.Errorf("tenant_id is required")
	}

	if len(req.Messages) == 0 {
		return fmt.Errorf("at least one message is required")
	}

	if req.ModelTier == "" {
		return fmt.Errorf("model_tier is required")
	}

	// Validate model tier
	validTiers := map[string]bool{"NANO": true, "MID": true, "FRONTIER": true}
	if !validTiers[req.ModelTier] {
		return fmt.Errorf("invalid model_tier: %s (must be NANO, MID, or FRONTIER)", req.ModelTier)
	}

	return nil
}

// convertToProviderRequest converts proto request to provider request
func (s *Server) convertToProviderRequest(req *pb.RouteRequest) *providers.ChatRequest {
	messages := make([]providers.Message, len(req.Messages))
	for i, msg := range req.Messages {
		messages[i] = providers.Message{
			Role:    msg.Role,
			Content: msg.Content,
		}
	}

	// Use defaults if not specified
	maxTokens := req.MaxTokens
	if maxTokens == 0 {
		maxTokens = int32(s.config.Providers.Default.MaxTokens)
	}

	temperature := req.Temperature
	if temperature == 0 {
		temperature = s.config.Providers.Default.Temperature
	}

	return &providers.ChatRequest{
		Messages:    messages,
		ModelTier:   req.ModelTier,
		MaxTokens:   maxTokens,
		Temperature: temperature,
		TaskID:      req.TaskId,
		TenantID:    req.TenantId,
// routeToExpert implements MiniMax-01 style MoE routing
// Routes requests to different providers based on context length and model tier
func (s *Server) routeToExpert(req *providers.ChatRequest) providers.Provider {
	// Calculate context length
	contextLength := 0
	for _, msg := range req.Messages {
		contextLength += len(msg.Content)
	}
	
	s.logger.Debug("MoE routing decision",
		zap.Int("context_length", contextLength),
		zap.String("model_tier", req.ModelTier),
		zap.String("task_id", req.TaskID),
	)
	
	// MoE Routing Logic (MiniMax-01 style)
	// If multiple providers are configured, route intelligently
	if s.providers != nil && len(s.providers) > 0 {
		// Long context expert (>100k characters)
		if contextLength > 100000 {
			if provider, ok := s.providers["anthropic-claude-3-opus"]; ok {
				s.logger.Info("Routing to long-context expert", zap.String("provider", "anthropic-claude-3-opus"))
				return provider
			}
		}
		
		// Fast/Cheap expert for NANO tier
		if req.ModelTier == "NANO" {
			if provider, ok := s.providers["openai-gpt-4o-mini"]; ok {
				s.logger.Info("Routing to fast expert", zap.String("provider", "openai-gpt-4o-mini"))
				return provider
			}
		}
		
		// Reasoning expert for FRONTIER tier
		if req.ModelTier == "FRONTIER" {
			if provider, ok := s.providers["openai-gpt-4-turbo"]; ok {
				s.logger.Info("Routing to reasoning expert", zap.String("provider", "openai-gpt-4-turbo"))
				return provider
			}
		}
	}
	
	// Default: use the primary provider
	s.logger.Debug("Using default provider", zap.String("provider", s.provider.Name()))
	return s.provider
}

	}
}

// Start starts the gRPC server
func (s *Server) Start() error {
	// Create gRPC server with options
	grpcServer := grpc.NewServer(
		grpc.MaxRecvMsgSize(10*1024*1024), // 10MB
		grpc.MaxSendMsgSize(10*1024*1024), // 10MB
	)

	// Register LLM Router service
	pb.RegisterLLMRouterServer(grpcServer, s)

	// Register health check service
	healthServer := health.NewServer()
	healthServer.SetServingStatus("", grpc_health_v1.HealthCheckResponse_SERVING)
	grpc_health_v1.RegisterHealthServer(grpcServer, healthServer)

	// Register reflection service for debugging
	reflection.Register(grpcServer)

	// Start gRPC server
	grpcAddr := fmt.Sprintf(":%s", s.config.Service.GRPCPort)
	listener, err := net.Listen("tcp", grpcAddr)
	if err != nil {
		return fmt.Errorf("failed to listen on %s: %w", grpcAddr, err)
	}

	s.logger.Info("Starting gRPC server",
		zap.String("address", grpcAddr),
		zap.String("service", s.config.Service.Name),
		zap.String("version", s.config.Service.Version),
	)

	// Start HTTP health check endpoint in a goroutine
	go s.startHTTPHealthCheck()

	// Start serving (blocking)
	if err := grpcServer.Serve(listener); err != nil {
		return fmt.Errorf("failed to serve: %w", err)
	}

	return nil
}

// startHTTPHealthCheck starts an HTTP server for health checks
func (s *Server) startHTTPHealthCheck() {
	httpAddr := fmt.Sprintf(":%s", s.config.Service.HTTPPort)

	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `{"status":"healthy","service":"%s","version":"%s"}`,
			s.config.Service.Name, s.config.Service.Version)
	})

	http.HandleFunc("/ready", func(w http.ResponseWriter, r *http.Request) {
		// Check if provider is available
		ctx := context.Background()
		_, err := s.provider.GetEmbedding(ctx, "test")
		if err != nil {
			w.WriteHeader(http.StatusServiceUnavailable)
			fmt.Fprintf(w, `{"status":"not ready","error":"%s"}`, err.Error())
			return
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `{"status":"ready"}`)
	})

	s.logger.Info("Starting HTTP health check server",
		zap.String("address", httpAddr),
	)

	if err := http.ListenAndServe(httpAddr, nil); err != nil {
		s.logger.Error("HTTP health check server failed",
			zap.Error(err),
		)
	}
}

// Made with Bob
