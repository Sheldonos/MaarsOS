package cache

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"math"
	"time"

	"github.com/maars/vessel-llm-router/internal/providers"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
)

// SemanticCache provides semantic similarity-based caching using Redis
type SemanticCache struct {
	client              *redis.Client
	provider            providers.Provider
	logger              *zap.Logger
	ttl                 time.Duration
	similarityThreshold float64
	enabled             bool
}

// CacheConfig contains configuration for the semantic cache
type CacheConfig struct {
	RedisClient         *redis.Client
	Provider            providers.Provider
	Logger              *zap.Logger
	TTL                 time.Duration
	SimilarityThreshold float64
	Enabled             bool
}

// CachedResponse represents a cached LLM response
type CachedResponse struct {
	Completion       string    `json:"completion"`
	ModelUsed        string    `json:"model_used"`
	PromptTokens     int32     `json:"prompt_tokens"`
	CompletionTokens int32     `json:"completion_tokens"`
	CostUSD          float32   `json:"cost_usd"`
	FinishReason     string    `json:"finish_reason"`
	Embedding        []float32 `json:"embedding"`
	CachedAt         time.Time `json:"cached_at"`
}

// CacheKey represents a cache key with metadata
type CacheKey struct {
	Hash      string
	Embedding []float32
}

// NewSemanticCache creates a new semantic cache
func NewSemanticCache(cfg CacheConfig) (*SemanticCache, error) {
	if cfg.Logger == nil {
		logger, _ := zap.NewProduction()
		cfg.Logger = logger
	}

	if cfg.TTL == 0 {
		cfg.TTL = 1 * time.Hour
	}

	if cfg.SimilarityThreshold == 0 {
		cfg.SimilarityThreshold = 0.95
	}

	return &SemanticCache{
		client:              cfg.RedisClient,
		provider:            cfg.Provider,
		logger:              cfg.Logger,
		ttl:                 cfg.TTL,
		similarityThreshold: cfg.SimilarityThreshold,
		enabled:             cfg.Enabled,
	}, nil
}

// Get retrieves a cached response if a semantically similar prompt exists
func (c *SemanticCache) Get(ctx context.Context, req *providers.ChatRequest) (*providers.ChatResponse, bool, error) {
	if !c.enabled {
		return nil, false, nil
	}

	// Generate cache key from request
	cacheKey, err := c.generateCacheKey(ctx, req)
	if err != nil {
		c.logger.Warn("Failed to generate cache key",
			zap.Error(err),
			zap.String("task_id", req.TaskID),
		)
		return nil, false, nil // Don't fail the request, just skip cache
	}

	// Search for similar cached responses
	cachedResp, similarity, err := c.findSimilarCache(ctx, cacheKey, req)
	if err != nil {
		c.logger.Warn("Failed to search cache",
			zap.Error(err),
			zap.String("task_id", req.TaskID),
		)
		return nil, false, nil
	}

	if cachedResp == nil {
		c.logger.Debug("Cache miss",
			zap.String("task_id", req.TaskID),
		)
		return nil, false, nil
	}

	c.logger.Info("Cache hit",
		zap.String("task_id", req.TaskID),
		zap.Float64("similarity", similarity),
		zap.Time("cached_at", cachedResp.CachedAt),
	)

	// Convert cached response to ChatResponse
	return &providers.ChatResponse{
		Completion:       cachedResp.Completion,
		ModelUsed:        cachedResp.ModelUsed,
		PromptTokens:     cachedResp.PromptTokens,
		CompletionTokens: cachedResp.CompletionTokens,
		CostUSD:          cachedResp.CostUSD,
		FinishReason:     cachedResp.FinishReason,
		Latency:          0, // Cache hit has negligible latency
	}, true, nil
}

// Set stores a response in the cache
func (c *SemanticCache) Set(ctx context.Context, req *providers.ChatRequest, resp *providers.ChatResponse) error {
	if !c.enabled {
		return nil
	}

	// Generate cache key from request
	cacheKey, err := c.generateCacheKey(ctx, req)
	if err != nil {
		c.logger.Warn("Failed to generate cache key for storage",
			zap.Error(err),
			zap.String("task_id", req.TaskID),
		)
		return nil // Don't fail the request
	}

	// Create cached response
	cachedResp := &CachedResponse{
		Completion:       resp.Completion,
		ModelUsed:        resp.ModelUsed,
		PromptTokens:     resp.PromptTokens,
		CompletionTokens: resp.CompletionTokens,
		CostUSD:          resp.CostUSD,
		FinishReason:     resp.FinishReason,
		Embedding:        cacheKey.Embedding,
		CachedAt:         time.Now(),
	}

	// Serialize to JSON
	data, err := json.Marshal(cachedResp)
	if err != nil {
		c.logger.Error("Failed to marshal cached response",
			zap.Error(err),
			zap.String("task_id", req.TaskID),
		)
		return nil
	}

	// Store in Redis with TTL
	key := c.buildRedisKey(cacheKey.Hash)
	err = c.client.Set(ctx, key, data, c.ttl).Err()
	if err != nil {
		c.logger.Error("Failed to store in cache",
			zap.Error(err),
			zap.String("task_id", req.TaskID),
		)
		return nil
	}

	// Add to search index (store hash with embedding for similarity search)
	indexKey := "cache:index"
	err = c.client.ZAdd(ctx, indexKey, redis.Z{
		Score:  float64(time.Now().Unix()),
		Member: cacheKey.Hash,
	}).Err()
	if err != nil {
		c.logger.Warn("Failed to add to cache index",
			zap.Error(err),
		)
	}

	c.logger.Debug("Stored response in cache",
		zap.String("task_id", req.TaskID),
		zap.String("cache_key", cacheKey.Hash),
	)

	return nil
}

// generateCacheKey creates a cache key from the request
func (c *SemanticCache) generateCacheKey(ctx context.Context, req *providers.ChatRequest) (*CacheKey, error) {
	// Combine all messages into a single string for embedding
	var promptText string
	for _, msg := range req.Messages {
		promptText += fmt.Sprintf("%s: %s\n", msg.Role, msg.Content)
	}

	// Add model tier to the prompt for differentiation
	promptText += fmt.Sprintf("tier: %s", req.ModelTier)

	// Generate embedding for semantic similarity
	embedding, err := c.provider.GetEmbedding(ctx, promptText)
	if err != nil {
		return nil, fmt.Errorf("failed to generate embedding: %w", err)
	}

	// Generate hash for exact match lookup
	hash := c.hashPrompt(promptText)

	return &CacheKey{
		Hash:      hash,
		Embedding: embedding,
	}, nil
}

// findSimilarCache searches for a semantically similar cached response
func (c *SemanticCache) findSimilarCache(ctx context.Context, key *CacheKey, req *providers.ChatRequest) (*CachedResponse, float64, error) {
	// First, try exact match
	exactKey := c.buildRedisKey(key.Hash)
	data, err := c.client.Get(ctx, exactKey).Bytes()
	if err == nil {
		var cached CachedResponse
		if err := json.Unmarshal(data, &cached); err == nil {
			return &cached, 1.0, nil // Exact match has similarity of 1.0
		}
	}

	// If no exact match, search for similar embeddings
	// Get all cache keys from index
	indexKey := "cache:index"
	members, err := c.client.ZRange(ctx, indexKey, 0, -1).Result()
	if err != nil {
		return nil, 0, fmt.Errorf("failed to get cache index: %w", err)
	}

	var bestMatch *CachedResponse
	var bestSimilarity float64

	// Search through cached items for semantic similarity
	for _, member := range members {
		cacheKey := c.buildRedisKey(member)
		data, err := c.client.Get(ctx, cacheKey).Bytes()
		if err != nil {
			continue
		}

		var cached CachedResponse
		if err := json.Unmarshal(data, &cached); err != nil {
			continue
		}

		// Calculate cosine similarity
		similarity := c.cosineSimilarity(key.Embedding, cached.Embedding)

		// Check if this is the best match so far
		if similarity > bestSimilarity && similarity >= c.similarityThreshold {
			bestSimilarity = similarity
			bestMatch = &cached
		}
	}

	if bestMatch != nil {
		return bestMatch, bestSimilarity, nil
	}

	return nil, 0, nil
}

// cosineSimilarity calculates the cosine similarity between two embeddings
func (c *SemanticCache) cosineSimilarity(a, b []float32) float64 {
	if len(a) != len(b) {
		return 0
	}

	var dotProduct, normA, normB float64
	for i := range a {
		dotProduct += float64(a[i]) * float64(b[i])
		normA += float64(a[i]) * float64(a[i])
		normB += float64(b[i]) * float64(b[i])
	}

	if normA == 0 || normB == 0 {
		return 0
	}

	return dotProduct / (math.Sqrt(normA) * math.Sqrt(normB))
}

// hashPrompt creates a SHA-256 hash of the prompt
func (c *SemanticCache) hashPrompt(prompt string) string {
	hash := sha256.Sum256([]byte(prompt))
	return fmt.Sprintf("%x", hash)
}

// buildRedisKey creates a Redis key for a cache entry
func (c *SemanticCache) buildRedisKey(hash string) string {
	return fmt.Sprintf("cache:llm:%s", hash)
}

// Clear removes all cached entries
func (c *SemanticCache) Clear(ctx context.Context) error {
	// Delete all cache keys
	pattern := "cache:llm:*"
	iter := c.client.Scan(ctx, 0, pattern, 0).Iterator()
	
	var keys []string
	for iter.Next(ctx) {
		keys = append(keys, iter.Val())
	}
	
	if err := iter.Err(); err != nil {
		return fmt.Errorf("failed to scan cache keys: %w", err)
	}

	if len(keys) > 0 {
		if err := c.client.Del(ctx, keys...).Err(); err != nil {
			return fmt.Errorf("failed to delete cache keys: %w", err)
		}
	}

	// Clear the index
	if err := c.client.Del(ctx, "cache:index").Err(); err != nil {
		return fmt.Errorf("failed to clear cache index: %w", err)
	}

	c.logger.Info("Cache cleared",
		zap.Int("keys_deleted", len(keys)),
	)

	return nil
}

// GetStats returns cache statistics
func (c *SemanticCache) GetStats(ctx context.Context) (map[string]interface{}, error) {
	// Count total cached items
	count, err := c.client.ZCard(ctx, "cache:index").Result()
	if err != nil {
		return nil, fmt.Errorf("failed to get cache count: %w", err)
	}

	stats := map[string]interface{}{
		"enabled":              c.enabled,
		"total_entries":        count,
		"ttl_seconds":          int(c.ttl.Seconds()),
		"similarity_threshold": c.similarityThreshold,
	}

	return stats, nil
}

// Made with Bob
