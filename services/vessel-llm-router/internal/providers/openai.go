package providers

import (
	"context"
	"errors"
	"fmt"
	"io"
	"time"

	"github.com/sashabaranov/go-openai"
	"go.uber.org/zap"
)

// OpenAIProvider implements the Provider interface for OpenAI
type OpenAIProvider struct {
	client         *openai.Client
	logger         *zap.Logger
	costCalculator CostCalculator
	modelMapping   ModelTierMapping
	maxRetries     int
	timeout        time.Duration
}

// OpenAIConfig contains configuration for the OpenAI provider
type OpenAIConfig struct {
	APIKey         string
	BaseURL        string
	MaxRetries     int
	Timeout        time.Duration
	Logger         *zap.Logger
	CostCalculator CostCalculator
}

// NewOpenAIProvider creates a new OpenAI provider
func NewOpenAIProvider(cfg OpenAIConfig) (*OpenAIProvider, error) {
	if cfg.APIKey == "" {
		return nil, errors.New("OpenAI API key is required")
	}

	if cfg.Logger == nil {
		logger, _ := zap.NewProduction()
		cfg.Logger = logger
	}

	if cfg.CostCalculator == nil {
		cfg.CostCalculator = NewDefaultCostCalculator()
	}

	// Create OpenAI client configuration
	clientConfig := openai.DefaultConfig(cfg.APIKey)
	if cfg.BaseURL != "" {
		clientConfig.BaseURL = cfg.BaseURL
	}

	client := openai.NewClientWithConfig(clientConfig)

	return &OpenAIProvider{
		client:         client,
		logger:         cfg.Logger,
		costCalculator: cfg.CostCalculator,
		modelMapping: ModelTierMapping{
			Nano:     "gpt-4o-mini",
			Mid:      "gpt-4-turbo",
			Frontier: "gpt-4o",
		},
		maxRetries: cfg.MaxRetries,
		timeout:    cfg.Timeout,
	}, nil
}

// Name returns the provider name
func (p *OpenAIProvider) Name() string {
	return "openai"
}

// SupportsStreaming returns true as OpenAI supports streaming
func (p *OpenAIProvider) SupportsStreaming() bool {
	return true
}

// Chat sends a chat completion request and returns the full response
func (p *OpenAIProvider) Chat(ctx context.Context, req *ChatRequest) (*ChatResponse, error) {
	startTime := time.Now()

	// Select model based on tier
	model := p.selectModel(req.ModelTier)

	// Convert messages to OpenAI format
	messages := p.convertMessages(req.Messages)

	// Create chat completion request
	chatReq := openai.ChatCompletionRequest{
		Model:       model,
		Messages:    messages,
		MaxTokens:   int(req.MaxTokens),
		Temperature: req.Temperature,
	}

	p.logger.Info("Sending chat request to OpenAI",
		zap.String("model", model),
		zap.String("task_id", req.TaskID),
		zap.String("tenant_id", req.TenantID),
	)

	// Execute request with retries
	var resp openai.ChatCompletionResponse
	var err error

	for attempt := 0; attempt <= p.maxRetries; attempt++ {
		if attempt > 0 {
			p.logger.Warn("Retrying OpenAI request",
				zap.Int("attempt", attempt),
				zap.String("task_id", req.TaskID),
			)
			time.Sleep(time.Duration(attempt) * time.Second)
		}

		resp, err = p.client.CreateChatCompletion(ctx, chatReq)
		if err == nil {
			break
		}

		// Check if error is retryable
		if !p.isRetryableError(err) {
			break
		}
	}

	if err != nil {
		p.logger.Error("OpenAI request failed",
			zap.Error(err),
			zap.String("task_id", req.TaskID),
		)
		return nil, NewProviderError(p.Name(), err.Error(), "api_error", p.isRetryableError(err))
	}

	// Calculate cost
	cost := p.costCalculator.CalculateCost(
		model,
		int32(resp.Usage.PromptTokens),
		int32(resp.Usage.CompletionTokens),
	)

	latency := time.Since(startTime)

	p.logger.Info("OpenAI request completed",
		zap.String("model", model),
		zap.Int("prompt_tokens", resp.Usage.PromptTokens),
		zap.Int("completion_tokens", resp.Usage.CompletionTokens),
		zap.Float32("cost_usd", cost),
		zap.Duration("latency", latency),
		zap.String("task_id", req.TaskID),
	)

	return &ChatResponse{
		Completion:       resp.Choices[0].Message.Content,
		ModelUsed:        model,
		PromptTokens:     int32(resp.Usage.PromptTokens),
		CompletionTokens: int32(resp.Usage.CompletionTokens),
		CostUSD:          cost,
		FinishReason:     string(resp.Choices[0].FinishReason),
		Latency:          latency,
	}, nil
}

// StreamChat sends a streaming chat completion request
func (p *OpenAIProvider) StreamChat(ctx context.Context, req *ChatRequest) (<-chan StreamChunk, <-chan error) {
	chunkChan := make(chan StreamChunk, 10)
	errChan := make(chan error, 1)

	go func() {
		defer close(chunkChan)
		defer close(errChan)

		// Select model based on tier
		model := p.selectModel(req.ModelTier)

		// Convert messages to OpenAI format
		messages := p.convertMessages(req.Messages)

		// Create streaming chat completion request
		chatReq := openai.ChatCompletionRequest{
			Model:       model,
			Messages:    messages,
			MaxTokens:   int(req.MaxTokens),
			Temperature: req.Temperature,
			Stream:      true,
		}

		p.logger.Info("Starting streaming chat request to OpenAI",
			zap.String("model", model),
			zap.String("task_id", req.TaskID),
		)

		// Create stream
		stream, err := p.client.CreateChatCompletionStream(ctx, chatReq)
		if err != nil {
			p.logger.Error("Failed to create OpenAI stream",
				zap.Error(err),
				zap.String("task_id", req.TaskID),
			)
			errChan <- NewProviderError(p.Name(), err.Error(), "stream_error", p.isRetryableError(err))
			return
		}
		defer stream.Close()

		var promptTokens, completionTokens int32
		var fullCompletion string

		// Read stream chunks
		for {
			response, err := stream.Recv()
			if errors.Is(err, io.EOF) {
				// Stream finished - send final chunk with token counts
				cost := p.costCalculator.CalculateCost(model, promptTokens, completionTokens)

				chunkChan <- StreamChunk{
					Delta:            "",
					ModelUsed:        model,
					IsFinal:          true,
					PromptTokens:     promptTokens,
					CompletionTokens: completionTokens,
					CostUSD:          cost,
				}

				p.logger.Info("OpenAI stream completed",
					zap.String("model", model),
					zap.Int32("prompt_tokens", promptTokens),
					zap.Int32("completion_tokens", completionTokens),
					zap.Float32("cost_usd", cost),
					zap.String("task_id", req.TaskID),
				)
				return
			}

			if err != nil {
				p.logger.Error("Error reading from OpenAI stream",
					zap.Error(err),
					zap.String("task_id", req.TaskID),
				)
				errChan <- NewProviderError(p.Name(), err.Error(), "stream_read_error", false)
				return
			}

			// Extract delta content
			if len(response.Choices) > 0 {
				delta := response.Choices[0].Delta.Content
				fullCompletion += delta

				// Send chunk
				chunkChan <- StreamChunk{
					Delta:     delta,
					ModelUsed: model,
					IsFinal:   false,
				}
			}

			// Update token counts if available (usually in final chunk)
			if response.Usage != nil {
				promptTokens = int32(response.Usage.PromptTokens)
				completionTokens = int32(response.Usage.CompletionTokens)
			}
		}
	}()

	return chunkChan, errChan
}

// GetEmbedding generates an embedding for the given text
func (p *OpenAIProvider) GetEmbedding(ctx context.Context, text string) ([]float32, error) {
	req := openai.EmbeddingRequest{
		Input: []string{text},
		Model: openai.SmallEmbedding3,
	}

	resp, err := p.client.CreateEmbeddings(ctx, req)
	if err != nil {
		p.logger.Error("Failed to create embedding",
			zap.Error(err),
		)
		return nil, NewProviderError(p.Name(), err.Error(), "embedding_error", p.isRetryableError(err))
	}

	if len(resp.Data) == 0 {
		return nil, NewProviderError(p.Name(), "no embedding returned", "empty_response", false)
	}

	return resp.Data[0].Embedding, nil
}

// selectModel selects the appropriate model based on the tier
func (p *OpenAIProvider) selectModel(tier string) string {
	switch tier {
	case "NANO":
		return p.modelMapping.Nano
	case "MID":
		return p.modelMapping.Mid
	case "FRONTIER":
		return p.modelMapping.Frontier
	default:
		p.logger.Warn("Unknown model tier, using MID",
			zap.String("tier", tier),
		)
		return p.modelMapping.Mid
	}
}

// convertMessages converts internal messages to OpenAI format
func (p *OpenAIProvider) convertMessages(messages []Message) []openai.ChatCompletionMessage {
	result := make([]openai.ChatCompletionMessage, len(messages))
	for i, msg := range messages {
		result[i] = openai.ChatCompletionMessage{
			Role:    msg.Role,
			Content: msg.Content,
		}
	}
	return result
}

// isRetryableError determines if an error is retryable
func (p *OpenAIProvider) isRetryableError(err error) bool {
	if err == nil {
		return false
	}

	// Check for specific OpenAI error types
	var apiErr *openai.APIError
	if errors.As(err, &apiErr) {
		// Retry on rate limits and server errors
		return apiErr.HTTPStatusCode == 429 || apiErr.HTTPStatusCode >= 500
	}

	// Retry on context deadline exceeded (timeout)
	if errors.Is(err, context.DeadlineExceeded) {
		return true
	}

	// Default to not retryable
	return false
}

// SetModelMapping allows customizing the model tier mapping
func (p *OpenAIProvider) SetModelMapping(mapping ModelTierMapping) {
	p.modelMapping = mapping
	p.logger.Info("Updated model tier mapping",
		zap.String("nano", mapping.Nano),
		zap.String("mid", mapping.Mid),
		zap.String("frontier", mapping.Frontier),
	)
}

// GetModelMapping returns the current model tier mapping
func (p *OpenAIProvider) GetModelMapping() ModelTierMapping {
	return p.modelMapping
}

// Made with Bob
