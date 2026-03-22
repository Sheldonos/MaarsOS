package config

import (
	"os"
)

// Config holds the application configuration
type Config struct {
	ServiceName     string
	ServiceVersion  string
	Environment     string
	Port            string
	OrchestratorURL string
	JWT             JWTConfig
	Redis           RedisConfig
}

// JWTConfig holds JWT authentication configuration
type JWTConfig struct {
	Secret   string
	Issuer   string
	Audience string
}

// RedisConfig holds Redis configuration
type RedisConfig struct {
	URL string
}

// Load loads configuration from environment variables
func Load() *Config {
	return &Config{
		ServiceName:     getEnv("SERVICE_NAME", "vessel-gateway"),
		ServiceVersion:  getEnv("SERVICE_VERSION", "0.1.0"),
		Environment:     getEnv("ENVIRONMENT", "development"),
		Port:            getEnv("PORT", "8000"),
		OrchestratorURL: getEnv("ORCHESTRATOR_URL", "http://localhost:8081"),
		JWT: JWTConfig{
			Secret:   getEnv("JWT_SECRET", "dev-secret-change-in-production"),
			Issuer:   getEnv("JWT_ISSUER", "maars-auth"),
			Audience: getEnv("JWT_AUDIENCE", "maars-api"),
		},
		Redis: RedisConfig{
			URL: getEnv("REDIS_URL", "redis://localhost:6379"),
		},
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// Made with Bob
