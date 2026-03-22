"""HTTP client for vessel-sandbox service"""
from typing import Dict, Any, Optional

import httpx
import structlog

logger = structlog.get_logger()


class SandboxClient:
    """Client for interacting with vessel-sandbox service"""
    
    def __init__(self, base_url: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        
    async def execute_code(
        self,
        task_id: str,
        tenant_id: str,
        code: str,
        language: str = "python",
        network_policy: str = "ISOLATED",
        max_execution_time_ms: Optional[int] = None,
        max_memory_mb: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute code in the sandbox
        
        Args:
            task_id: Unique task identifier
            tenant_id: Tenant identifier
            code: Code to execute
            language: Programming language (python, javascript)
            network_policy: Network access policy (ISOLATED, RESTRICTED, OPEN)
            max_execution_time_ms: Maximum execution time in milliseconds
            max_memory_mb: Maximum memory in megabytes
            
        Returns:
            Execution result dictionary
        """
        payload = {
            "task_id": task_id,
            "tenant_id": tenant_id,
            "code": code,
            "language": language,
            "network_policy": network_policy,
        }
        
        if max_execution_time_ms:
            payload["max_execution_time_ms"] = max_execution_time_ms
        if max_memory_mb:
            payload["max_memory_mb"] = max_memory_mb
            
        logger.info(
            "Executing code in sandbox",
            task_id=task_id,
            language=language,
            network_policy=network_policy,
        )
        
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/execute",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info(
                "Code execution completed",
                task_id=task_id,
                status=result.get("status"),
                execution_time_ms=result.get("execution_time_ms"),
            )
            
            return result
            
        except httpx.HTTPError as e:
            logger.error(
                "Sandbox execution failed",
                task_id=task_id,
                error=str(e),
            )
            raise
    
    async def health_check(self) -> bool:
        """Check if sandbox service is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

# Made with Bob
