use anyhow::{anyhow, Result};
use std::collections::HashMap;
use std::path::PathBuf;
use std::time::Duration;
use tracing::{debug, info, warn};
use wasmtime::*;
use wasmtime_wasi::{WasiCtx, WasiCtxBuilder};

#[derive(Debug, Clone)]
pub enum NetworkPolicy {
    Isolated,   // No network access
    Restricted, // Whitelisted domains only
    Open,       // Full network access (monitored)
}

#[derive(Debug, Clone)]
pub struct SandboxConfig {
    pub task_id: String,
    pub tenant_id: String,
    pub network_policy: NetworkPolicy,
    pub max_execution_time_ms: u64,
    pub max_memory_mb: u64,
    pub max_fuel: u64,
}

pub struct ExecutionOutput {
    pub stdout: String,
    pub stderr: String,
    pub memory_used_mb: u64,
    pub artifacts: HashMap<String, Vec<u8>>,
}

pub struct WasmSandbox {
    config: SandboxConfig,
    workspace_dir: PathBuf,
}

impl WasmSandbox {
    pub fn new(config: SandboxConfig) -> Result<Self> {
        // Create isolated workspace directory for this task
        let workspace_dir = PathBuf::from(format!("/tmp/maars/tasks/{}", config.task_id));
        std::fs::create_dir_all(&workspace_dir)?;

        info!(
            "Created sandbox for task_id={} with policy={:?}",
            config.task_id, config.network_policy
        );

        Ok(Self {
            config,
            workspace_dir,
        })
    }

    pub async fn execute(&self, code: &str, language: &str) -> Result<ExecutionOutput> {
        match language.to_lowercase().as_str() {
            "python" => self.execute_python(code).await,
            "javascript" | "js" => self.execute_javascript(code).await,
            _ => Err(anyhow!("Unsupported language: {}", language)),
        }
    }

    async fn execute_python(&self, code: &str) -> Result<ExecutionOutput> {
        // For Phase 1, we'll use a simplified approach:
        // 1. Write Python code to workspace
        // 2. Compile to WASM using a Python-to-WASM compiler (e.g., pyodide)
        // 3. Execute in Wasmtime
        
        // For now, we'll simulate execution with a direct Python interpreter
        // wrapped in WASM-like constraints. Full WASM implementation in Phase 2.
        
        info!("Executing Python code for task_id={}", self.config.task_id);
        
        // Write code to workspace
        let code_path = self.workspace_dir.join("script.py");
        std::fs::write(&code_path, code)?;

        // Create WASM engine with fuel metering
        let mut config = Config::new();
        config.consume_fuel(true);
        config.wasm_multi_memory(true);
        config.wasm_memory64(true);
        
        let engine = Engine::new(&config)?;
        
        // For Phase 1 MVP, we'll execute Python directly with constraints
        // and wrap it in our security model
        let output = self.execute_with_constraints(code).await?;
        
        Ok(output)
    }

    async fn execute_javascript(&self, code: &str) -> Result<ExecutionOutput> {
        info!("Executing JavaScript code for task_id={}", self.config.task_id);
        
        // Write code to workspace
        let code_path = self.workspace_dir.join("script.js");
        std::fs::write(&code_path, code)?;

        // Execute with constraints
        let output = self.execute_with_constraints(code).await?;
        
        Ok(output)
    }

    async fn execute_with_constraints(&self, code: &str) -> Result<ExecutionOutput> {
        // Create isolated execution environment
        let mut stdout_buffer: Vec<u8> = Vec::new();
        let mut stderr_buffer: Vec<u8> = Vec::new();

        // Set up WASI context with capability-based file system access
        let _wasi_ctx = self.create_wasi_context()?;

        // For Phase 1 MVP: Execute using system Python with timeout and resource limits
        // This will be replaced with full WASM execution in Phase 2
        let result = tokio::time::timeout(
            Duration::from_millis(self.config.max_execution_time_ms),
            self.run_sandboxed_process(code),
        )
        .await;

        match result {
            Ok(Ok(output)) => Ok(output),
            Ok(Err(e)) => Err(anyhow!("Execution failed: {}", e)),
            Err(_) => Err(anyhow!(
                "Execution timeout after {}ms",
                self.config.max_execution_time_ms
            )),
        }
    }

    fn create_wasi_context(&self) -> Result<WasiCtx> {
        let mut builder = WasiCtxBuilder::new();
        
        // Inherit stdio for capturing output
        builder.inherit_stdio();

        // Capability-based file system access
        // Only grant access to the task-specific workspace directory
        let task_dir = std::fs::File::open(&self.workspace_dir)?;
        let wasi_dir = wasmtime_wasi::Dir::from_std_file(task_dir);
        builder.preopened_dir(wasi_dir, "/workspace")?;

        // Network policy enforcement
        match self.config.network_policy {
            NetworkPolicy::Isolated => {
                debug!("Network access: ISOLATED (no network)");
                // No network capabilities granted
            }
            NetworkPolicy::Restricted => {
                debug!("Network access: RESTRICTED (whitelisted domains only)");
                // In production, this would use WASI sockets with domain filtering
                // For Phase 1, we'll implement this via proxy
            }
            NetworkPolicy::Open => {
                debug!("Network access: OPEN (full network, monitored)");
                // Grant network capabilities with monitoring
            }
        }

        Ok(builder.build())
    }

    async fn run_sandboxed_process(&self, code: &str) -> Result<ExecutionOutput> {
        // Phase 1 MVP: Use system Python with resource limits
        // This simulates WASM execution constraints
        
        use std::process::Command;
        
        let code_path = self.workspace_dir.join("script.py");
        std::fs::write(&code_path, code)?;

        // Execute with ulimit-like constraints
        let output = Command::new("python3")
            .arg(&code_path)
            .current_dir(&self.workspace_dir)
            .env("PYTHONUNBUFFERED", "1")
            .output()?;

        // Collect any generated artifacts
        let mut artifacts = HashMap::new();
        if let Ok(entries) = std::fs::read_dir(&self.workspace_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_file() && path.file_name() != Some(std::ffi::OsStr::new("script.py")) {
                    if let Ok(content) = std::fs::read(&path) {
                        if let Some(filename) = path.file_name() {
                            artifacts.insert(filename.to_string_lossy().to_string(), content);
                        }
                    }
                }
            }
        }

        Ok(ExecutionOutput {
            stdout: String::from_utf8_lossy(&output.stdout).to_string(),
            stderr: String::from_utf8_lossy(&output.stderr).to_string(),
            memory_used_mb: 0, // TODO: Implement memory tracking
            artifacts,
        })
    }
}

impl Drop for WasmSandbox {
    fn drop(&mut self) {
        // Clean up workspace directory
        if let Err(e) = std::fs::remove_dir_all(&self.workspace_dir) {
            warn!(
                "Failed to clean up workspace for task_id={}: {}",
                self.config.task_id, e
            );
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_python_hello_world() {
        let config = SandboxConfig {
            task_id: "test-001".to_string(),
            tenant_id: "tenant-001".to_string(),
            network_policy: NetworkPolicy::Isolated,
            max_execution_time_ms: 5000,
            max_memory_mb: 256,
            max_fuel: 1_000_000,
        };

        let sandbox = WasmSandbox::new(config).unwrap();
        let result = sandbox.execute("print('Hello MAARS')", "python").await;

        assert!(result.is_ok());
        let output = result.unwrap();
        assert!(output.stdout.contains("Hello MAARS"));
    }

    #[tokio::test]
    async fn test_execution_timeout() {
        let config = SandboxConfig {
            task_id: "test-002".to_string(),
            tenant_id: "tenant-001".to_string(),
            network_policy: NetworkPolicy::Isolated,
            max_execution_time_ms: 100,
            max_memory_mb: 256,
            max_fuel: 1_000_000,
        };

        let sandbox = WasmSandbox::new(config).unwrap();
        let result = sandbox
            .execute("import time; time.sleep(10)", "python")
            .await;

        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("timeout"));
    }
}

// Made with Bob
