package providers

import (
	"context"
	"time"
)

// Provider defines the interface that all LLM providers must implement
type Provider interface {
	// Chat sends a chat completion request and returns the full response
	Chat(ctx context.Context, req *ChatRequest) (*ChatResponse, error)

	// StreamChat sends a streaming chat completion request
	StreamChat(ctx context.Context, req *ChatRequest) (<-chan StreamChunk, <-chan error)

	// GetEmbedding generates an embedding for the given text
	GetEmbedding(ctx context.Context, text string) ([]float32, error)

	// Name returns the provider name (e.g., "openai", "anthropic")
	Name() string

	// SupportsStreaming returns true if the provider supports streaming
	SupportsStreaming() bool
}

// ChatRequest represents a chat completion request
type ChatRequest struct {
	Messages    []Message
	ModelTier   string  // NANO, MID, FRONTIER
	MaxTokens   int32
	Temperature float32
	TaskID      string
	TenantID    string
}

// Message represents a single message in a conversation
type Message struct {
	Role    string // system, user, assistant, tool
	Content string
}

// ChatResponse represents a complete chat response
type ChatResponse struct {
	Completion       string
	ModelUsed        string
	PromptTokens     int32
	CompletionTokens int32
	CostUSD          float32
	FinishReason     string
	Latency          time.Duration
}

// StreamChunk represents a single chunk in a streaming response
type StreamChunk struct {
	Delta            string
	ModelUsed        string
	IsFinal          bool
	PromptTokens     int32
	CompletionTokens int32
	CostUSD          float32
}

// ModelTierMapping maps model tiers to actual model names
type ModelTierMapping struct {
	Nano     string
	Mid      string
	Frontier string
}

// CostCalculator calculates the cost of a request based on token usage
type CostCalculator interface {
	CalculateCost(model string, promptTokens, completionTokens int32) float32
}

// DefaultCostCalculator provides default cost calculation
type DefaultCostCalculator struct {
	// Cost per 1M tokens for different models
	costs map[string]struct {
		promptCost     float32
		completionCost float32
	}
}

// NewDefaultCostCalculator creates a new cost calculator with default pricing
func NewDefaultCostCalculator() *DefaultCostCalculator {
	return &DefaultCostCalculator{
		costs: map[string]struct {
			promptCost     float32
			completionCost float32
		}{
			// OpenAI pricing (per 1M tokens)
			"gpt-3.5-turbo": {
				promptCost:     0.50,
				completionCost: 1.50,
			},
			"gpt-4-turbo": {
				promptCost:     10.00,
				completionCost: 30.00,
			},
			"gpt-4": {
				promptCost:     30.00,
				completionCost: 60.00,
			},
			"gpt-4o": {
				promptCost:     5.00,
				completionCost: 15.00,
			},
			"gpt-4o-mini": {
				promptCost:     0.15,
				completionCost: 0.60,
			},
			// Anthropic pricing (per 1M tokens)
			"claude-3-5-sonnet-20241022": {
				promptCost:     3.00,
				completionCost: 15.00,
			},
			"claude-3-opus-20240229": {
				promptCost:     15.00,
				completionCost: 75.00,
			},
			"claude-3-sonnet-20240229": {
				promptCost:     3.00,
				completionCost: 15.00,
			},
			"claude-3-haiku-20240307": {
				promptCost:     0.25,
				completionCost: 1.25,
			},
		},
	}
}

// CalculateCost calculates the cost in USD for the given token usage
func (c *DefaultCostCalculator) CalculateCost(model string, promptTokens, completionTokens int32) float32 {
	costs, ok := c.costs[model]
	if !ok {
		// Default to mid-tier pricing if model not found
		costs = c.costs["gpt-4-turbo"]
	}

	promptCost := (float32(promptTokens) / 1_000_000) * costs.promptCost
	completionCost := (float32(completionTokens) / 1_000_000) * costs.completionCost

	return promptCost + completionCost
}

// ProviderError represents an error from a provider
type ProviderError struct {
	Provider string
	Message  string
	Code     string
	Retryable bool
}

func (e *ProviderError) Error() string {
	return e.Message
}

// NewProviderError creates a new provider error
func NewProviderError(provider, message, code string, retryable bool) *ProviderError {
	return &ProviderError{
		Provider:  provider,
		Message:   message,
		Code:      code,
		Retryable: retryable,
	}
}

// Made with Bob
