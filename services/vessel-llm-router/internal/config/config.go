package config

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

// Config holds all configuration for the LLM Router service
type Config struct {
	Service  ServiceConfig
	Providers ProvidersConfig
	Redis    RedisConfig
	Cache    CacheConfig
}

// ServiceConfig contains service-level configuration
type ServiceConfig struct {
	Name        string
	Version     string
	GRPCPort    string
	HTTPPort    string
	Environment string
	LogLevel    string
}

// ProvidersConfig contains configuration for LLM providers
type ProvidersConfig struct {
	OpenAI    OpenAIConfig
	Anthropic AnthropicConfig
	Default   DefaultProviderConfig
}

// OpenAIConfig contains OpenAI-specific configuration
type OpenAIConfig struct {
	APIKey      string
	BaseURL     string
	MaxRetries  int
	Timeout     time.Duration
	EmbedModel  string
}

// AnthropicConfig contains Anthropic-specific configuration
type AnthropicConfig struct {
	APIKey     string
	MaxRetries int
	Timeout    time.Duration
}

// DefaultProviderConfig contains default provider settings
type DefaultProviderConfig struct {
	ModelTier      string
	MaxTokens      int
	Temperature    float32
	TimeoutSeconds int
}

// RedisConfig contains Redis connection configuration
type RedisConfig struct {
	URL      string
	Password string
	DB       int
	PoolSize int
}

// CacheConfig contains caching behavior configuration
type CacheConfig struct {
	Enabled            bool
	TTLSeconds         int
	SimilarityThreshold float64
	MaxCacheSize       int64
}

// Load reads configuration from environment variables
func Load() (*Config, error) {
	cfg := &Config{
		Service: ServiceConfig{
			Name:        getEnv("SERVICE_NAME", "vessel-llm-router"),
			Version:     getEnv("SERVICE_VERSION", "0.1.0"),
			GRPCPort:    getEnv("GRPC_PORT", "8082"),
			HTTPPort:    getEnv("HTTP_PORT", "8083"),
			Environment: getEnv("ENVIRONMENT", "development"),
			LogLevel:    getEnv("LOG_LEVEL", "info"),
		},
		Providers: ProvidersConfig{
			OpenAI: OpenAIConfig{
				APIKey:     getEnv("OPENAI_API_KEY", ""),
				BaseURL:    getEnv("OPENAI_BASE_URL", ""),
				MaxRetries: getEnvInt("OPENAI_MAX_RETRIES", 3),
				Timeout:    time.Duration(getEnvInt("OPENAI_TIMEOUT_SECONDS", 30)) * time.Second,
				EmbedModel: getEnv("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
			},
			Anthropic: AnthropicConfig{
				APIKey:     getEnv("ANTHROPIC_API_KEY", ""),
				MaxRetries: getEnvInt("ANTHROPIC_MAX_RETRIES", 3),
				Timeout:    time.Duration(getEnvInt("ANTHROPIC_TIMEOUT_SECONDS", 30)) * time.Second,
			},
			Default: DefaultProviderConfig{
				ModelTier:      getEnv("DEFAULT_MODEL_TIER", "MID"),
				MaxTokens:      getEnvInt("DEFAULT_MAX_TOKENS", 4096),
				Temperature:    float32(getEnvFloat("DEFAULT_TEMPERATURE", 0.7)),
				TimeoutSeconds: getEnvInt("TIMEOUT_SECONDS", 30),
			},
		},
		Redis: RedisConfig{
			URL:      getEnv("REDIS_URL", "redis://localhost:6379"),
			Password: getEnv("REDIS_PASSWORD", ""),
			DB:       getEnvInt("REDIS_DB", 0),
			PoolSize: getEnvInt("REDIS_POOL_SIZE", 10),
		},
		Cache: CacheConfig{
			Enabled:             getEnvBool("ENABLE_CACHING", true),
			TTLSeconds:          getEnvInt("CACHE_TTL_SECONDS", 3600),
			SimilarityThreshold: getEnvFloat("CACHE_SIMILARITY_THRESHOLD", 0.95),
			MaxCacheSize:        int64(getEnvInt("CACHE_MAX_SIZE_MB", 1024)) * 1024 * 1024,
		},
	}

	// Validate required configuration
	if err := cfg.Validate(); err != nil {
		return nil, fmt.Errorf("invalid configuration: %w", err)
	}

	return cfg, nil
}

// Validate checks if the configuration is valid
func (c *Config) Validate() error {
	if c.Providers.OpenAI.APIKey == "" {
		return fmt.Errorf("OPENAI_API_KEY is required")
	}

	if c.Service.GRPCPort == "" {
		return fmt.Errorf("GRPC_PORT is required")
	}

	if c.Redis.URL == "" {
		return fmt.Errorf("REDIS_URL is required")
	}

	return nil
}

// Helper functions for environment variable parsing

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intVal, err := strconv.Atoi(value); err == nil {
			return intVal
		}
	}
	return defaultValue
}

func getEnvFloat(key string, defaultValue float64) float64 {
	if value := os.Getenv(key); value != "" {
		if floatVal, err := strconv.ParseFloat(value, 64); err == nil {
			return floatVal
		}
	}
	return defaultValue
}

func getEnvBool(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		if boolVal, err := strconv.ParseBool(value); err == nil {
			return boolVal
		}
	}
	return defaultValue
}

// Made with Bob
