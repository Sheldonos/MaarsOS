"""
MAARS vessel-integrations Service
Main FastAPI application for external integrations.
"""

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Dict, Any, List
import logging
import uvicorn
from sqlalchemy.orm import Session

from app.config import settings
from app.database import init_db, get_db_session, close_db_session
from app.kafka_producer import kafka_producer
from app.slack_handler import slack_handler
from app.models import SlackIntegration, MCPServer
import uuid

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")
    
    # Initialize database
    init_db()
    
    # Start Kafka producer
    await kafka_producer.start()
    
    logger.info(f"{settings.SERVICE_NAME} started successfully on port {settings.PORT}")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.SERVICE_NAME}")
    await kafka_producer.stop()


# Create FastAPI app
app = FastAPI(
    title="MAARS vessel-integrations",
    description="External integrations service for MAARS",
    version=settings.SERVICE_VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION
    }


# Slack endpoints
@app.post("/v1/integrations/slack/events")
async def slack_events(request: Request):
    """
    Slack Event API webhook endpoint.
    Handles all Slack events including @maars mentions.
    """
    return await slack_handler.handler.handle(request)


@app.post("/v1/integrations/slack/install")
async def install_slack_workspace(
    data: Dict[str, Any],
    db: Session = Depends(get_db_session)
):
    """
    Install Slack workspace integration.
    
    Request body:
    {
        "tenant_id": "uuid",
        "workspace_id": "T1234567890",
        "bot_token_vault_path": "secret/slack/workspace-id/bot-token",
        "signing_secret_vault_path": "secret/slack/workspace-id/signing-secret",
        "default_channel_id": "C1234567890"
    }
    """
    try:
        integration = SlackIntegration(
            tenant_id=uuid.UUID(data["tenant_id"]),
            workspace_id=data["workspace_id"],
            bot_token_vault_path=data["bot_token_vault_path"],
            signing_secret_vault_path=data["signing_secret_vault_path"],
            default_channel_id=data.get("default_channel_id"),
            notify_on_milestone=data.get("notify_on_milestone", True),
            notify_on_completion=data.get("notify_on_completion", True),
            notify_on_inbox_card=data.get("notify_on_inbox_card", True)
        )
        
        db.add(integration)
        db.commit()
        db.refresh(integration)
        
        logger.info(f"Installed Slack workspace {data['workspace_id']} for tenant {data['tenant_id']}")
        
        return {
            "status": "success",
            "workspace_id": data["workspace_id"],
            "tenant_id": data["tenant_id"]
        }
        
    except Exception as e:
        logger.error(f"Failed to install Slack workspace: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        close_db_session(db)


@app.get("/v1/integrations/slack/workspaces")
async def list_slack_workspaces(
    tenant_id: str,
    db: Session = Depends(get_db_session)
):
    """List all Slack workspaces for a tenant."""
    try:
        workspaces = db.query(SlackIntegration).filter(
            SlackIntegration.tenant_id == uuid.UUID(tenant_id)
        ).all()
        
        return {
            "workspaces": [
                {
                    "workspace_id": w.workspace_id,
                    "default_channel_id": w.default_channel_id,
                    "notify_on_milestone": w.notify_on_milestone,
                    "notify_on_completion": w.notify_on_completion,
                    "created_at": w.created_at.isoformat()
                }
                for w in workspaces
            ]
        }
    finally:
        close_db_session(db)


# MCP Server endpoints
@app.post("/v1/integrations/mcp/servers")
async def register_mcp_server(
    data: Dict[str, Any],
    db: Session = Depends(get_db_session)
):
    """
    Register a custom MCP server.
    
    Request body:
    {
        "tenant_id": "uuid",
        "server_name": "internal-crm",
        "server_url": "https://crm.internal.company.com/mcp",
        "auth_type": "bearer",
        "auth_token_vault_path": "secret/crm/mcp-token",
        "allowed_tools": ["get_customer", "update_opportunity"],
        "description": "Internal Salesforce CRM connector"
    }
    """
    try:
        server = MCPServer(
            tenant_id=uuid.UUID(data["tenant_id"]),
            server_name=data["server_name"],
            server_url=data["server_url"],
            auth_type=data["auth_type"],
            auth_token_vault_path=data.get("auth_token_vault_path"),
            allowed_tools=data.get("allowed_tools", []),
            status="ACTIVE"
        )
        
        db.add(server)
        db.commit()
        db.refresh(server)
        
        logger.info(f"Registered MCP server {data['server_name']} for tenant {data['tenant_id']}")
        
        # Publish event
        await kafka_producer.publish_mcp_event(
            event_type="mcp.server_registered",
            payload={
                "server_id": str(server.server_id),
                "server_name": data["server_name"],
                "server_url": data["server_url"]
            },
            tenant_id=data["tenant_id"],
            server_id=str(server.server_id)
        )
        
        return {
            "status": "success",
            "server_id": str(server.server_id),
            "server_name": data["server_name"]
        }
        
    except Exception as e:
        logger.error(f"Failed to register MCP server: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        close_db_session(db)


@app.get("/v1/integrations/mcp/servers")
async def list_mcp_servers(
    tenant_id: str,
    db: Session = Depends(get_db_session)
):
    """List all MCP servers for a tenant."""
    try:
        servers = db.query(MCPServer).filter(
            MCPServer.tenant_id == uuid.UUID(tenant_id),
            MCPServer.status == "ACTIVE"
        ).all()
        
        return {
            "servers": [
                {
                    "server_id": str(s.server_id),
                    "server_name": s.server_name,
                    "server_url": s.server_url,
                    "auth_type": s.auth_type,
                    "allowed_tools": s.allowed_tools,
                    "status": s.status,
                    "last_health_check": s.last_health_check.isoformat() if s.last_health_check else None,
                    "created_at": s.created_at.isoformat()
                }
                for s in servers
            ]
        }
    finally:
        close_db_session(db)


@app.delete("/v1/integrations/mcp/servers/{server_id}")
async def delete_mcp_server(
    server_id: str,
    tenant_id: str,
    db: Session = Depends(get_db_session)
):
    """Delete (deactivate) an MCP server."""
    try:
        server = db.query(MCPServer).filter(
            MCPServer.server_id == uuid.UUID(server_id),
            MCPServer.tenant_id == uuid.UUID(tenant_id)
        ).first()
        
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP server not found"
            )
        
        server.status = "INACTIVE"
        db.commit()
        
        logger.info(f"Deactivated MCP server {server_id}")
        
        return {"status": "success", "server_id": server_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete MCP server: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        close_db_session(db)


@app.get("/v1/integrations/mcp/tools")
async def discover_mcp_tools(
    tenant_id: str,
    db: Session = Depends(get_db_session)
):
    """
    Discover all available MCP tools across registered servers.
    Used by vessel-orchestrator for task planning.
    """
    try:
        servers = db.query(MCPServer).filter(
            MCPServer.tenant_id == uuid.UUID(tenant_id),
            MCPServer.status == "ACTIVE"
        ).all()
        
        tools = []
        for server in servers:
            for tool_name in server.allowed_tools or []:
                tools.append({
                    "tool_name": tool_name,
                    "server_id": str(server.server_id),
                    "server_name": server.server_name,
                    "server_url": server.server_url
                })
        
        return {"tools": tools, "total": len(tools)}
        
    finally:
        close_db_session(db)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.LOG_LEVEL == "DEBUG",
        log_level=settings.LOG_LEVEL.lower()
    )

# Made with Bob
