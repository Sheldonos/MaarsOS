"""
Slack bot event handler for MAARS integration.
Handles @maars mentions and creates goals via vessel-gateway.
"""

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from slack_sdk.errors import SlackApiError
from typing import Dict, Any, Optional
import httpx
import logging
import re
from datetime import datetime

from app.config import settings
from app.kafka_producer import kafka_producer
from app.database import get_db
from app.models import SlackIntegration, GoalSlackThread, IntegrationEvent
from sqlalchemy.orm import Session
import uuid

logger = logging.getLogger(__name__)


class SlackBotHandler:
    """Handles Slack bot events and interactions."""
    
    def __init__(self):
        """Initialize Slack bot with Bolt framework."""
        self.app = AsyncApp(
            token=settings.SLACK_BOT_TOKEN,
            signing_secret=settings.SLACK_SIGNING_SECRET
        )
        self.handler = AsyncSlackRequestHandler(self.app)
        self.gateway_url = settings.GATEWAY_URL
        self.internal_token = settings.INTERNAL_SERVICE_TOKEN
        
        # Register event handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register Slack event handlers."""
        
        @self.app.event("app_mention")
        async def handle_mention(event, say, client):
            """Handle @maars mentions in Slack channels."""
            await self._handle_maars_mention(event, say, client)
        
        @self.app.event("message")
        async def handle_message(event, say):
            """Handle direct messages to the bot."""
            if event.get("channel_type") == "im":
                await self._handle_direct_message(event, say)
    
    async def _handle_maars_mention(
        self,
        event: Dict[str, Any],
        say,
        client
    ) -> None:
        """
        Handle @maars mention and create a MAARS goal.
        
        Flow:
        1. Extract goal description from message
        2. Post acknowledgment in thread
        3. Create goal via vessel-gateway
        4. Store thread mapping in database
        5. Subscribe to goal events and relay to Slack
        """
        try:
            # Extract message details
            channel_id = event["channel"]
            thread_ts = event.get("thread_ts", event["ts"])
            user_id = event["user"]
            text = event["text"]
            
            # Get bot user ID to remove mention
            bot_info = await client.auth_test()
            bot_user_id = bot_info["user_id"]
            
            # Remove @maars mention and clean up text
            goal_description = re.sub(
                f"<@{bot_user_id}>",
                "",
                text
            ).strip()
            
            if not goal_description:
                await say(
                    text="⚠️ Please provide a goal description after mentioning me.",
                    thread_ts=thread_ts
                )
                return
            
            # Post acknowledgment
            ack_message = await say(
                text=f":gear: Received your request. Decomposing into tasks...\n\n> {goal_description}",
                thread_ts=thread_ts
            )
            
            # Get workspace and tenant info
            workspace_id = event.get("team")
            tenant_id = await self._get_tenant_id_for_workspace(workspace_id)
            
            if not tenant_id:
                await say(
                    text="❌ Workspace not configured. Please contact your administrator.",
                    thread_ts=thread_ts
                )
                return
            
            # Create goal via vessel-gateway
            goal = await self._create_goal(
                description=goal_description,
                tenant_id=tenant_id,
                metadata={
                    "source": "slack",
                    "channel_id": channel_id,
                    "thread_ts": thread_ts,
                    "user_id": user_id,
                    "workspace_id": workspace_id
                }
            )
            
            if not goal:
                await say(
                    text="❌ Failed to create goal. Please try again.",
                    thread_ts=thread_ts
                )
                return
            
            goal_id = goal["goal_id"]
            
            # Store thread mapping
            await self._store_thread_mapping(
                goal_id=goal_id,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                channel_id=channel_id,
                thread_ts=thread_ts
            )
            
            # Update acknowledgment with goal ID
            await client.chat_update(
                channel=channel_id,
                ts=ack_message["ts"],
                text=f":white_check_mark: Goal created: `{goal_id}`\n\n> {goal_description}\n\nI'll update you as tasks complete."
            )
            
            # Log event
            await self._log_integration_event(
                tenant_id=tenant_id,
                integration_type="slack",
                event_type="goal_created_from_mention",
                event_data={
                    "goal_id": goal_id,
                    "channel_id": channel_id,
                    "thread_ts": thread_ts,
                    "user_id": user_id
                },
                status="SUCCESS"
            )
            
            # Publish Kafka event
            await kafka_producer.publish_slack_event(
                event_type="goal.created_from_slack",
                payload={
                    "goal_id": goal_id,
                    "channel_id": channel_id,
                    "thread_ts": thread_ts,
                    "description": goal_description
                },
                tenant_id=tenant_id,
                workspace_id=workspace_id
            )
            
        except Exception as e:
            logger.error(f"Error handling Slack mention: {e}")
            await say(
                text=f"❌ An error occurred: {str(e)}",
                thread_ts=thread_ts
            )
    
    async def _handle_direct_message(
        self,
        event: Dict[str, Any],
        say
    ) -> None:
        """Handle direct messages to the bot."""
        text = event.get("text", "").strip()
        
        if text.lower() in ["help", "?"]:
            await say(
                text=self._get_help_message()
            )
        else:
            await say(
                text="👋 Hi! Mention me in a channel with `@maars [your goal]` to create a task.\n\nType `help` for more information."
            )
    
    async def _create_goal(
        self,
        description: str,
        tenant_id: str,
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a goal via vessel-gateway API."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.gateway_url}/v1/goals",
                    json={
                        "description": description,
                        "priority": "NORMAL",
                        "metadata": metadata
                    },
                    headers={
                        "Authorization": f"Bearer {self.internal_token}",
                        "X-Tenant-ID": tenant_id
                    }
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to create goal: {e}")
            return None
    
    async def _get_tenant_id_for_workspace(
        self,
        workspace_id: str
    ) -> Optional[str]:
        """Get tenant ID for a Slack workspace."""
        try:
            with get_db() as db:
                integration = db.query(SlackIntegration).filter(
                    SlackIntegration.workspace_id == workspace_id
                ).first()
                
                if integration:
                    return str(integration.tenant_id)
                return None
        except Exception as e:
            logger.error(f"Failed to get tenant ID: {e}")
            return None
    
    async def _store_thread_mapping(
        self,
        goal_id: str,
        tenant_id: str,
        workspace_id: str,
        channel_id: str,
        thread_ts: str
    ) -> None:
        """Store mapping between goal and Slack thread."""
        try:
            with get_db() as db:
                thread = GoalSlackThread(
                    goal_id=uuid.UUID(goal_id),
                    tenant_id=uuid.UUID(tenant_id),
                    workspace_id=workspace_id,
                    channel_id=channel_id,
                    thread_ts=thread_ts,
                    created_at=datetime.utcnow()
                )
                db.add(thread)
                db.commit()
        except Exception as e:
            logger.error(f"Failed to store thread mapping: {e}")
    
    async def _log_integration_event(
        self,
        tenant_id: str,
        integration_type: str,
        event_type: str,
        event_data: Dict[str, Any],
        status: str
    ) -> None:
        """Log integration event to database."""
        try:
            with get_db() as db:
                event = IntegrationEvent(
                    tenant_id=uuid.UUID(tenant_id),
                    integration_type=integration_type,
                    event_type=event_type,
                    event_data=event_data,
                    status=status,
                    created_at=datetime.utcnow()
                )
                db.add(event)
                db.commit()
        except Exception as e:
            logger.error(f"Failed to log integration event: {e}")
    
    def _get_help_message(self) -> str:
        """Get help message for users."""
        return """
🤖 *MAARS Bot Help*

*Creating Goals:*
Mention me in any channel with your goal:
`@maars Research the top 10 AI frameworks and create a comparison table`

*Features:*
• Real-time task updates in thread
• Cost tracking per goal
• Artifact links when complete
• Multi-agent orchestration

*Commands:*
• `help` - Show this message
• `status [goal_id]` - Check goal status

*Need help?* Contact your MAARS administrator.
        """.strip()
    
    async def post_task_update(
        self,
        goal_id: str,
        task_name: str,
        model_tier: str,
        cost_usd: float,
        execution_time_ms: int,
        artifact_link: Optional[str] = None
    ) -> None:
        """
        Post task completion update to Slack thread.
        Called by Kafka consumer when task completes.
        """
        try:
            # Get thread mapping
            with get_db() as db:
                thread = db.query(GoalSlackThread).filter(
                    GoalSlackThread.goal_id == uuid.UUID(goal_id)
                ).first()
                
                if not thread:
                    logger.warning(f"No Slack thread found for goal {goal_id}")
                    return
                
                # Get Slack integration
                integration = db.query(SlackIntegration).filter(
                    SlackIntegration.tenant_id == thread.tenant_id,
                    SlackIntegration.workspace_id == thread.workspace_id
                ).first()
                
                if not integration or not integration.notify_on_milestone:
                    return
            
            # Format message
            message = f":white_check_mark: *Task Complete:* {task_name}\n"
            message += f"> Model: `{model_tier}` | Cost: `${cost_usd:.4f}` | Time: `{execution_time_ms}ms`"
            
            if artifact_link:
                message += f"\n> :link: {artifact_link}"
            
            # Post to thread
            await self.app.client.chat_postMessage(
                channel=thread.channel_id,
                thread_ts=thread.thread_ts,
                text=message
            )
            
        except Exception as e:
            logger.error(f"Failed to post task update: {e}")
    
    async def post_goal_completion(
        self,
        goal_id: str,
        goal_description: str,
        total_cost_usd: float,
        agent_count: int,
        duration_seconds: int,
        artifacts: list
    ) -> None:
        """Post goal completion message to Slack thread."""
        try:
            # Get thread mapping
            with get_db() as db:
                thread = db.query(GoalSlackThread).filter(
                    GoalSlackThread.goal_id == uuid.UUID(goal_id)
                ).first()
                
                if not thread:
                    return
                
                # Get Slack integration
                integration = db.query(SlackIntegration).filter(
                    SlackIntegration.tenant_id == thread.tenant_id,
                    SlackIntegration.workspace_id == thread.workspace_id
                ).first()
                
                if not integration or not integration.notify_on_completion:
                    return
            
            # Format duration
            duration_str = f"{duration_seconds // 60}m {duration_seconds % 60}s"
            
            # Format message
            message = f":trophy: *Goal Complete:* {goal_description}\n"
            message += f"> Total Cost: `${total_cost_usd:.4f}` | Agents Used: `{agent_count}` | Duration: `{duration_str}`\n\n"
            
            if artifacts:
                message += "*Artifacts:*\n"
                for artifact in artifacts:
                    message += f"• {artifact}\n"
            
            # Post to thread
            await self.app.client.chat_postMessage(
                channel=thread.channel_id,
                thread_ts=thread.thread_ts,
                text=message
            )
            
        except Exception as e:
            logger.error(f"Failed to post goal completion: {e}")


# Global handler instance
slack_handler = SlackBotHandler()

# Made with Bob
