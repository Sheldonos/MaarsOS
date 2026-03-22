# Vessel Gateway

API Gateway for MAARS with JWT authentication, rate limiting, and request proxying.

## Features

- **JWT Authentication**: Validates JWT tokens and extracts user/tenant claims
- **Rate Limiting**: Redis-backed rate limiting (100 req/min per user)
- **Request Proxying**: Forwards authenticated requests to vessel-orchestrator
- **CORS Support**: Configurable CORS headers
- **Structured Logging**: Zap-based structured logging
- **Health Checks**: `/health` endpoint for monitoring
- **Graceful Shutdown**: Proper cleanup on SIGTERM/SIGINT

## Architecture

```
┌─────────────────────────────────────────┐
│      vessel-gateway (Go/Gin)            │
├─────────────────────────────────────────┤
│  ┌───────────────────────────────────┐  │
│  │      HTTP Server (Gin)            │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │      Middleware Stack             │  │
│  │  • Logger                         │  │
│  │  • CORS                           │  │
│  │  • JWT Authentication             │  │
│  │  • Rate Limiter (Redis)           │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │      Reverse Proxy                │  │
│  │  → vessel-orchestrator            │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## API Endpoints

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "vessel-gateway",
  "version": "0.1.0"
}
```

### POST /v1/goals

Submit a new goal (proxied to vessel-orchestrator).

**Headers:**
- `Authorization: Bearer <JWT_TOKEN>` (required)

**Request:**
```json
{
  "description": "print('Hello MAARS')",
  "priority": "NORMAL"
}
```

**Response:** See vessel-orchestrator documentation

### All /v1/* Routes

All routes under `/v1/` are proxied to vessel-orchestrator with:
- JWT validation
- Rate limiting
- User/tenant context injection via headers

## JWT Token Format

Expected JWT claims:
```json
{
  "sub": "user-id",
  "tenant_id": "tenant-id",
  "role": "user|admin",
  "iss": "maars-auth",
  "aud": "maars-api",
  "exp": 1234567890
}
```

## Environment Variables

```bash
# Service
SERVICE_NAME=vessel-gateway
SERVICE_VERSION=0.1.0
ENVIRONMENT=development
PORT=8000

# Backend
ORCHESTRATOR_URL=http://localhost:8081

# JWT
JWT_SECRET=dev-secret-change-in-production
JWT_ISSUER=maars-auth
JWT_AUDIENCE=maars-api

# Redis
REDIS_URL=redis://localhost:6379
```

## Rate Limiting

- **Default Limit:** 100 requests per minute per user
- **Identifier:** User ID from JWT (falls back to IP address)
- **Storage:** Redis with 1-minute TTL
- **Headers:**
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Requests remaining in current window

**Rate Limit Response (429):**
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

## Development

### Prerequisites

- Go 1.22+
- Redis (for rate limiting)

### Install Dependencies

```bash
go mod download
```

### Run Locally

```bash
go run main.go
```

### Build

```bash
go build -o vessel-gateway
```

### Run with Docker

```bash
docker build -t vessel-gateway .
docker run -p 8000:8000 vessel-gateway
```

## Testing

### Generate Test JWT

For development, you can generate a test JWT:

```bash
# Using jwt.io or a JWT library
# Header: {"alg": "HS256", "typ": "JWT"}
# Payload: {
#   "sub": "test-user",
#   "tenant_id": "test-tenant",
#   "role": "user",
#   "iss": "maars-auth",
#   "aud": "maars-api",
#   "exp": 9999999999
# }
# Secret: dev-secret-change-in-production
```

### Test Request

```bash
# Health check (no auth required)
curl http://localhost:8000/health

# Submit goal (requires JWT)
curl -X POST http://localhost:8000/v1/goals \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"description": "print(\"Hello MAARS\")", "priority": "NORMAL"}'
```

## Security Features

### JWT Validation
- Validates signature using HMAC-SHA256
- Checks token expiration
- Validates issuer and audience claims
- Extracts user/tenant context

### Rate Limiting
- Per-user limits prevent abuse
- Redis-backed for distributed deployments
- Fail-open if Redis unavailable

### Request Sanitization
- Strips sensitive headers before proxying
- Injects tenant/user context headers
- Logs all requests for audit trail

## Production Considerations

1. **JWT Secret**: Use a strong, randomly generated secret
2. **CORS**: Configure allowed origins appropriately
3. **Rate Limits**: Adjust based on usage patterns
4. **Redis**: Use Redis Cluster for high availability
5. **TLS**: Terminate TLS at load balancer or use HTTPS
6. **Monitoring**: Integrate with Prometheus/Grafana

## Integration Points

- **vessel-orchestrator**: Backend service (HTTP)
- **Redis**: Rate limiting storage
- **Auth Provider**: JWT token issuer (Auth0, Keycloak, etc.)

## Phase 1 MVP Notes

- JWT validation implemented with HMAC-SHA256
- Rate limiting functional with Redis
- Request proxying to vessel-orchestrator
- Kong integration deferred to Phase 2 (using Gin directly)

## Future Enhancements (Phase 2+)

- [ ] Kong integration for advanced routing
- [ ] API key authentication
- [ ] Request/response transformation
- [ ] Circuit breaker pattern
- [ ] Distributed tracing
- [ ] Metrics export (Prometheus)