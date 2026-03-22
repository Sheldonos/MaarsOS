use axum::{
    extract::{Json, State},
    http::StatusCode,
    response::IntoResponse,
    routing::post,
    Router,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tracing::{info, warn};

mod sandbox;
mod storage;

use sandbox::{NetworkPolicy, SandboxConfig, WasmSandbox};
use storage::ArtifactStorage;

#[derive(Clone)]
struct AppState {
    storage: Arc<ArtifactStorage>,
}

#[derive(Debug, Deserialize)]
struct ExecuteRequest {
    task_id: String,
    tenant_id: String,
    code: String,
    language: String,
    network_policy: String,
    max_execution_time_ms: Option<u64>,
    max_memory_mb: Option<u64>,
}

#[derive(Debug, Serialize)]
struct ExecuteResponse {
    task_id: String,
    status: String,
    output: Option<String>,
    error: Option<String>,
    execution_time_ms: u64,
    memory_used_mb: u64,
    artifact_urls: Vec<String>,
}

#[tokio::main]
async fn main() {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "vessel_sandbox=debug,tower_http=debug".into()),
        )
        .init();

    info!("Starting vessel-sandbox service");

    // Initialize artifact storage
    let storage = Arc::new(ArtifactStorage::new().await);

    let state = AppState { storage };

    // Build router
    let app = Router::new()
        .route("/health", axum::routing::get(health_check))
        .route("/v1/execute", post(execute_code))
        .layer(
            tower_http::trace::TraceLayer::new_for_http()
                .make_span_with(tower_http::trace::DefaultMakeSpan::new().level(tracing::Level::INFO))
                .on_response(tower_http::trace::DefaultOnResponse::new().level(tracing::Level::INFO)),
        )
        .layer(tower_http::cors::CorsLayer::permissive())
        .with_state(state);

    let addr = "0.0.0.0:8085";
    info!("vessel-sandbox listening on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn health_check() -> impl IntoResponse {
    Json(serde_json::json!({
        "status": "healthy",
        "service": "vessel-sandbox",
        "version": "0.1.0"
    }))
}

async fn execute_code(
    State(state): State<AppState>,
    Json(req): Json<ExecuteRequest>,
) -> Result<Json<ExecuteResponse>, (StatusCode, String)> {
    info!(
        "Executing code for task_id={}, tenant_id={}, language={}",
        req.task_id, req.tenant_id, req.language
    );

    // Parse network policy
    let network_policy = match req.network_policy.to_uppercase().as_str() {
        "ISOLATED" => NetworkPolicy::Isolated,
        "RESTRICTED" => NetworkPolicy::Restricted,
        "OPEN" => NetworkPolicy::Open,
        _ => {
            warn!("Invalid network policy: {}, defaulting to ISOLATED", req.network_policy);
            NetworkPolicy::Isolated
        }
    };

    // Create sandbox configuration
    let config = SandboxConfig {
        task_id: req.task_id.clone(),
        tenant_id: req.tenant_id.clone(),
        network_policy,
        max_execution_time_ms: req.max_execution_time_ms.unwrap_or(30000),
        max_memory_mb: req.max_memory_mb.unwrap_or(512),
        max_fuel: 10_000_000, // ~10M instructions
    };

    // Create sandbox instance
    let sandbox = WasmSandbox::new(config).map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            format!("Failed to create sandbox: {}", e),
        )
    })?;

    // Execute code
    let start = std::time::Instant::now();
    let result = sandbox.execute(&req.code, &req.language).await;
    let execution_time_ms = start.elapsed().as_millis() as u64;

    match result {
        Ok(output) => {
            // Store artifacts if any were generated
            let artifact_urls = if !output.artifacts.is_empty() {
                let mut urls = Vec::new();
                for (filename, content) in output.artifacts {
                    match state
                        .storage
                        .upload_artifact(&req.task_id, &filename, content)
                        .await
                    {
                        Ok(url) => urls.push(url),
                        Err(e) => warn!("Failed to upload artifact {}: {}", filename, e),
                    }
                }
                urls
            } else {
                Vec::new()
            };

            Ok(Json(ExecuteResponse {
                task_id: req.task_id,
                status: "SUCCESS".to_string(),
                output: Some(output.stdout),
                error: output.stderr.is_empty().then(|| output.stderr),
                execution_time_ms,
                memory_used_mb: output.memory_used_mb,
                artifact_urls,
            }))
        }
        Err(e) => Ok(Json(ExecuteResponse {
            task_id: req.task_id,
            status: "FAILED".to_string(),
            output: None,
            error: Some(e.to_string()),
            execution_time_ms,
            memory_used_mb: 0,
            artifact_urls: Vec::new(),
        })),
    }
}

// Made with Bob
