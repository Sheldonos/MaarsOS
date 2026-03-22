# Vessel Sandbox

WASM-based code execution sandbox for MAARS with capability-based security.

## Features

- **WASM Runtime**: Wasmtime-based execution engine
- **Capability-Based Security**: Fine-grained file system and network access control
- **Network Policies**: ISOLATED, RESTRICTED, and OPEN modes
- **Resource Limits**: CPU, memory, and execution time constraints
- **Artifact Storage**: MinIO integration for generated files
- **Multi-Language Support**: Python, JavaScript (extensible)

## API Endpoints

### POST /v1/execute

Execute code in a sandboxed environment.

**Request:**
```json
{
  "task_id": "uuid-v4",
  "tenant_id": "uuid-v4",
  "code": "print('Hello MAARS')",
  "language": "python",
  "network_policy": "ISOLATED",
  "max_execution_time_ms": 30000,
  "max_memory_mb": 512
}
```

**Response:**
```json
{
  "task_id": "uuid-v4",
  "status": "SUCCESS",
  "output": "Hello MAARS\n",
  "error": null,
  "execution_time_ms": 125,
  "memory_used_mb": 45,
  "artifact_urls": []
}
```

### GET /health

Health check endpoint.

## Network Policies

- **ISOLATED**: No network access (default for untrusted code)
- **RESTRICTED**: Whitelisted domains only (for API integrations)
- **OPEN**: Full network access with monitoring (requires approval)

## Environment Variables

```bash
RUST_LOG=info
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=maars-artifacts
MINIO_PUBLIC_URL=http://localhost:9000
```

## Development

### Build

```bash
cargo build --release
```

### Run

```bash
cargo run
```

### Test

```bash
cargo test
```

### Docker

```bash
docker build -t vessel-sandbox .
docker run -p 8085:8085 vessel-sandbox
```

## Architecture

```
┌─────────────────────────────────────────┐
│         vessel-sandbox (Rust)           │
├─────────────────────────────────────────┤
│  ┌───────────────────────────────────┐  │
│  │      Axum HTTP Server             │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │    Wasmtime WASM Runtime          │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │  Capability-Based Security  │  │  │
│  │  │  - File System Isolation    │  │  │
│  │  │  - Network Policy Engine    │  │  │
│  │  │  - Resource Limits          │  │  │
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │    Artifact Storage (MinIO)       │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## Security Model

1. **Workspace Isolation**: Each task gets a unique `/tmp/maars/tasks/{task_id}` directory
2. **Fuel Metering**: Execution limited by instruction count (default: 10M instructions)
3. **Time Limits**: Configurable timeout (default: 30 seconds)
4. **Memory Limits**: Configurable memory cap (default: 512MB)
5. **Network Isolation**: Default deny with explicit allow policies

## Phase 1 MVP Notes

For Phase 1, the sandbox uses system Python with WASM-like constraints. Full WASM compilation (via Pyodide/QuickJS) will be implemented in Phase 2.

Current approach:
- ✅ Isolated workspace per task
- ✅ Execution timeouts
- ✅ Network policy enforcement (via environment)
- ✅ Artifact collection and storage
- 🔄 Memory limits (OS-level, not WASM-level yet)
- 🔄 Fuel metering (simulated, not WASM-level yet)

## Future Enhancements (Phase 2+)

- [ ] Full WASM compilation for Python (Pyodide)
- [ ] Full WASM compilation for JavaScript (QuickJS)
- [ ] WASI sockets for network policy enforcement
- [ ] GPU access for ML workloads
- [ ] Streaming execution output
- [ ] Checkpoint/resume for long-running tasks