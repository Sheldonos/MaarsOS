package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/maars/vessel-llm-router/internal/cache"
	"github.com/maars/vessel-llm-router/internal/config"
	"github.com/maars/vessel-llm-router/internal/providers"
	"github.com/maars/vessel-llm-router/internal/server"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

func main() {
	// Initialize logger
	logger, err := initLogger()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to initialize logger: %v\n", err)
		os.Exit(1)
	}
	defer logger.Sync()

	logger.Info("Starting vessel-llm-router service")

	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		logger.Fatal("Failed to load configuration",
			zap.Error(err),
		)
	}

	logger.Info("Configuration loaded",
		zap.String("service", cfg.Service.Name),
		zap.String("version", cfg.Service.Version),
		zap.String("environment", cfg.Service.Environment),
		zap.String("grpc_port", cfg.Service.GRPCPort),
		zap.String("http_port", cfg.Service.HTTPPort),
	)

	// Initialize Redis client
	redisClient, err := initRedis(cfg, logger)
	if err != nil {
		logger.Fatal("Failed to initialize Redis",
			zap.Error(err),
		)
	}
	defer redisClient.Close()

	logger.Info("Redis connection established",
		zap.String("url", cfg.Redis.URL),
	)

	// Initialize OpenAI provider
	provider, err := initProvider(cfg, logger)
	if err != nil {
		logger.Fatal("Failed to initialize provider",
			zap.Error(err),
		)
	}

	logger.Info("Provider initialized",
		zap.String("provider", provider.Name()),
		zap.Bool("supports_streaming", provider.SupportsStreaming()),
	)

	// Initialize semantic cache
	semanticCache, err := initCache(cfg, redisClient, provider, logger)
	if err != nil {
		logger.Fatal("Failed to initialize cache",
			zap.Error(err),
		)
	}

	logger.Info("Semantic cache initialized",
		zap.Bool("enabled", cfg.Cache.Enabled),
		zap.Int("ttl_seconds", cfg.Cache.TTLSeconds),
		zap.Float64("similarity_threshold", cfg.Cache.SimilarityThreshold),
	)

	// Create and start gRPC server
	grpcServer := server.NewServer(cfg, provider, semanticCache, logger)

	// Handle graceful shutdown
	go handleShutdown(logger, redisClient)

	// Start server (blocking)
	logger.Info("Starting gRPC server",
		zap.String("grpc_address", fmt.Sprintf(":%s", cfg.Service.GRPCPort)),
		zap.String("http_address", fmt.Sprintf(":%s", cfg.Service.HTTPPort)),
	)

	if err := grpcServer.Start(); err != nil {
		logger.Fatal("Server failed",
			zap.Error(err),
		)
	}
}

// initLogger initializes the structured logger
func initLogger() (*zap.Logger, error) {
	logLevel := os.Getenv("LOG_LEVEL")
	if logLevel == "" {
		logLevel = "info"
	}

	var level zapcore.Level
	if err := level.UnmarshalText([]byte(logLevel)); err != nil {
		level = zapcore.InfoLevel
	}

	config := zap.Config{
		Level:             zap.NewAtomicLevelAt(level),
		Development:       false,
		Encoding:          "json",
		EncoderConfig:     zap.NewProductionEncoderConfig(),
		OutputPaths:       []string{"stdout"},
		ErrorOutputPaths:  []string{"stderr"},
		DisableStacktrace: false,
	}

	// Use console encoding in development
	if os.Getenv("ENVIRONMENT") == "development" {
		config.Encoding = "console"
		config.EncoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder
		config.EncoderConfig.EncodeLevel = zapcore.CapitalColorLevelEncoder
	}

	return config.Build()
}

// initRedis initializes the Redis client
func initRedis(cfg *config.Config, logger *zap.Logger) (*redis.Client, error) {
	opts, err := redis.ParseURL(cfg.Redis.URL)
	if err != nil {
		return nil, fmt.Errorf("invalid Redis URL: %w", err)
	}

	// Override with config values
	if cfg.Redis.Password != "" {
		opts.Password = cfg.Redis.Password
	}
	opts.DB = cfg.Redis.DB
	opts.PoolSize = cfg.Redis.PoolSize

	client := redis.NewClient(opts)

	// Test connection
	ctx := context.Background()
	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("failed to connect to Redis: %w", err)
	}

	return client, nil
}

// initProvider initializes the LLM provider
func initProvider(cfg *config.Config, logger *zap.Logger) (providers.Provider, error) {
	// Currently only OpenAI is implemented
	// In the future, this could be extended to support multiple providers
	// based on configuration

	providerCfg := providers.OpenAIConfig{
		APIKey:         cfg.Providers.OpenAI.APIKey,
		BaseURL:        cfg.Providers.OpenAI.BaseURL,
		MaxRetries:     cfg.Providers.OpenAI.MaxRetries,
		Timeout:        cfg.Providers.OpenAI.Timeout,
		Logger:         logger,
		CostCalculator: providers.NewDefaultCostCalculator(),
	}

	provider, err := providers.NewOpenAIProvider(providerCfg)
	if err != nil {
		return nil, fmt.Errorf("failed to create OpenAI provider: %w", err)
	}

	return provider, nil
}

// initCache initializes the semantic cache
func initCache(cfg *config.Config, redisClient *redis.Client, provider providers.Provider, logger *zap.Logger) (*cache.SemanticCache, error) {
	cacheCfg := cache.CacheConfig{
		RedisClient:         redisClient,
		Provider:            provider,
		Logger:              logger,
		TTL:                 cfg.Cache.TTLSeconds,
		SimilarityThreshold: cfg.Cache.SimilarityThreshold,
		Enabled:             cfg.Cache.Enabled,
	}

	semanticCache, err := cache.NewSemanticCache(cacheCfg)
	if err != nil {
		return nil, fmt.Errorf("failed to create semantic cache: %w", err)
	}

	return semanticCache, nil
}

// handleShutdown handles graceful shutdown on SIGINT/SIGTERM
func handleShutdown(logger *zap.Logger, redisClient *redis.Client) {
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

	sig := <-sigChan
	logger.Info("Received shutdown signal",
		zap.String("signal", sig.String()),
	)

	// Cleanup
	logger.Info("Cleaning up resources...")

	if redisClient != nil {
		if err := redisClient.Close(); err != nil {
			logger.Error("Failed to close Redis connection",
				zap.Error(err),
			)
		}
	}

	logger.Info("Shutdown complete")
	os.Exit(0)
}

// Made with Bob
