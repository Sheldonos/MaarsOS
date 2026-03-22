# MAARS Phase 1 Deployment Guide

**Version:** 1.0.0  
**Date:** March 22, 2026  
**Status:** Production Ready

---

## Quick Start (5 Minutes)

### Prerequisites

- Docker Desktop 4.x+ with 8GB+ RAM
- Ports available: 8000, 8081, 8085, 6379, 9000, 19092

### Step 1: Start Services

```bash
cd infrastructure/docker
docker-compose up --build -d
```

This will build and start all 9 services (takes 5-10 minutes on first run).

### Step 2: Verify Health

```bash
# Wait for all services to be healthy (30-60 seconds)
docker-compose ps

# Check individual services
curl http://localhost:8000/health  # Gateway
curl http://localhost:8081/health  # Orchestrator
curl http://localhost:8085/health  # Sandbox
```

### Step 3: Run Integration Tests

```bash
cd ../..
chmod +x test-integration.sh
./test-integration.sh
```

Expected output: All tests pass ✅

### Step 4: Test Your First Goal

```bash
curl -X POST http://localhost:8081/v1/goals \
  -H "Content-Type: application/json" \
  -d '{
    "description": "print(\"Hello MAARS! The system is working.\")",
    "priority": "NORMAL"
  }'
```

---

## Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| vessel-gateway | http://localhost:8000 | Public API (with auth) |
| vessel-orchestrator | http://localhost:8081 | Internal API |
| vessel-sandbox | http://localhost:8085 | Execution engine |
| Redpanda Console | http://localhost:19644 | Kafka UI |
| MinIO Console | http://localhost:9001 | Storage UI |
| Kong Admin | http://localhost:8001 | Gateway config |
| Vault | http://localhost:8200 | Secrets |

---

## Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker logs -f maars-vessel-gateway
docker logs -f maars-vessel-orchestrator
docker logs -f maars-vessel-sandbox
```

### Check Kafka Events

1. Open http://localhost:19644
2. Navigate to Topics
3. View messages in `maars.goals`, `maars.tasks`, `maars.events`

### Check Artifacts

1. Open http://localhost:9001
2. Login: minioadmin / minioadmin
3. Browse `maars-artifacts` bucket

---

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs [service-name]

# Rebuild specific service
docker-compose up --build [service-name]

# Reset everything
docker-compose down -v
docker-compose up --build -d
```

### Port Conflicts

Edit `infrastructure/docker/docker-compose.yml` to change port mappings.

### Out of Memory

Increase Docker Desktop memory to 8GB+ in Settings → Resources.

---

## Production Deployment (Phase 2)

### Kubernetes

```bash
# Apply manifests
kubectl apply -f infrastructure/kubernetes/

# Verify deployment
kubectl get pods -n maars-core
```

### Environment Variables

See `.env.example` for all configuration options.

Critical variables:
- `OPENAI_API_KEY` - For LLM integration (Phase 2)
- `ASTRA_DB_TOKEN` - For production database
- `JWT_SECRET` - Change from default!

---

## Scaling

### Horizontal Scaling

```bash
# Scale orchestrator
docker-compose up -d --scale vessel-orchestrator=3

# Scale sandbox
docker-compose up -d --scale vessel-sandbox=5
```

### Resource Limits

Edit `docker-compose.yml` to adjust:
- CPU limits
- Memory limits
- Replica counts

---

## Security Checklist

- [ ] Change JWT_SECRET from default
- [ ] Configure CORS origins
- [ ] Set up TLS/HTTPS
- [ ] Rotate API keys
- [ ] Enable Vault in production mode
- [ ] Configure network policies
- [ ] Set up monitoring alerts

---

## Backup & Recovery

### Database Backup

```bash
# PostgreSQL (local dev)
docker exec maars-postgres pg_dump -U maars maars > backup.sql

# Restore
docker exec -i maars-postgres psql -U maars maars < backup.sql
```

### Artifact Backup

```bash
# MinIO
docker exec maars-minio mc mirror /data /backup
```

---

## Performance Tuning

### Recommended Settings

| Component | Setting | Value |
|-----------|---------|-------|
| Orchestrator replicas | 3-5 | Based on load |
| Sandbox replicas | 5-10 | Based on concurrency |
| Redis max memory | 2GB | For rate limiting |
| Redpanda memory | 4GB | For event streaming |

---

## Health Checks

All services expose `/health` endpoints:

```bash
# Automated health check
for service in gateway orchestrator sandbox; do
  curl -f http://localhost:800${service#vessel-}/health || echo "$service unhealthy"
done
```

---

## Shutdown

```bash
# Graceful shutdown
docker-compose down

# Remove volumes (data loss!)
docker-compose down -v
```

---

## Next Steps

1. ✅ Complete integration testing
2. 📋 Set up monitoring (Prometheus/Grafana)
3. 📋 Configure production database (AstraDB)
4. 📋 Implement CI/CD pipeline
5. 📋 Begin Phase 2 development

---

**Support:** See `docs/` for detailed documentation  
**Issues:** GitHub Issues  
**Testing:** `./test-integration.sh`