"""
Data models for vessel-integrations service.
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class SlackIntegration(Base):
    """Slack workspace integration configuration."""
    __tablename__ = "slack_integrations"
    
    tenant_id = Column(UUID(as_uuid=True), primary_key=True)
    workspace_id = Column(String(255), primary_key=True)
    bot_token_vault_path = Column(String(500), nullable=False)
    signing_secret_vault_path = Column(String(500), nullable=False)
    default_channel_id = Column(String(255))
    notify_on_milestone = Column(Boolean, default=True)
    notify_on_completion = Column(Boolean, default=True)
    notify_on_inbox_card = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GoalSlackThread(Base):
    """Mapping between MAARS goals and Slack threads."""
    __tablename__ = "goal_slack_threads"
    
    goal_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    workspace_id = Column(String(255), nullable=False)
    channel_id = Column(String(255), nullable=False)
    thread_ts = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class MCPServer(Base):
    """Custom MCP server registration."""
    __tablename__ = "mcp_servers"
    
    server_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    server_name = Column(String(255), nullable=False)
    server_url = Column(String(500), nullable=False)
    auth_type = Column(String(50), nullable=False)  # bearer, oauth2, api_key
    auth_token_vault_path = Column(String(500))
    allowed_tools = Column(JSON)  # List of tool names
    status = Column(String(50), default="ACTIVE")  # ACTIVE, INACTIVE, ERROR
    last_health_check = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class OAuthToken(Base):
    """OAuth token storage (encrypted in Vault, metadata here)."""
    __tablename__ = "oauth_tokens"
    
    token_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    provider = Column(String(100), nullable=False)  # slack, google, github, etc.
    vault_path = Column(String(500), nullable=False)
    scope = Column(Text)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IntegrationEvent(Base):
    """Audit log for integration events."""
    __tablename__ = "integration_events"
    
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    integration_type = Column(String(100), nullable=False)  # slack, mcp, oauth
    event_type = Column(String(100), nullable=False)  # message_received, goal_created, etc.
    event_data = Column(JSON)
    status = Column(String(50), default="SUCCESS")  # SUCCESS, FAILED, PENDING
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# Made with Bob
