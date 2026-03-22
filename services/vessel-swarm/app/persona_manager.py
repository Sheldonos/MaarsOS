"""
Agency Agents Persona Manager for vessel-swarm

Implements declarative persona system inspired by Agency Swarm framework.
Supports uploading persona packages (.zip) containing:
- instructions.md (system prompt)
- tools.py (allowed tools)
- manifesto.md (shared context)
- config.yaml (metadata)
"""

import io
import zipfile
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4

import structlog
import yaml
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    AgentPersona,
    CommunicationFlow,
    AgencyManifesto,
    Agent,
    AgentType,
    ModelTier,
    AgentStatus,
)

logger = structlog.get_logger()


class PersonaPackage:
    """Represents an unpacked persona package"""
    
    def __init__(self):
        self.instructions_md: Optional[str] = None
        self.tools_py: Optional[str] = None
        self.manifesto_md: Optional[str] = None
        self.config_yaml: Optional[Dict[str, Any]] = None
        self.metadata: Dict[str, Any] = {}
    
    @classmethod
    def from_zip(cls, zip_bytes: bytes) -> 'PersonaPackage':
        """Parse persona package from ZIP file"""
        package = cls()
        
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
            # Read instructions.md
            if 'instructions.md' in zf.namelist():
                package.instructions_md = zf.read('instructions.md').decode('utf-8')
            
            # Read tools.py
            if 'tools.py' in zf.namelist():
                package.tools_py = zf.read('tools.py').decode('utf-8')
            
            # Read manifesto.md
            if 'manifesto.md' in zf.namelist():
                package.manifesto_md = zf.read('manifesto.md').decode('utf-8')
            
            # Read config.yaml
            if 'config.yaml' in zf.namelist():
                config_content = zf.read('config.yaml').decode('utf-8')
                package.config_yaml = yaml.safe_load(config_content)
            
            # Read any additional metadata files
            for filename in zf.namelist():
                if filename.endswith('.json'):
                    import json
                    package.metadata[filename] = json.loads(
                        zf.read(filename).decode('utf-8')
                    )
        
        return package
    
    def validate(self) -> List[str]:
        """Validate persona package structure"""
        errors = []
        
        if not self.instructions_md:
            errors.append("Missing required file: instructions.md")
        
        if not self.config_yaml:
            errors.append("Missing required file: config.yaml")
        else:
            # Validate config structure
            required_fields = ['name', 'vibe', 'role']
            for field in required_fields:
                if field not in self.config_yaml:
                    errors.append(f"Missing required config field: {field}")
        
        return errors


class PersonaManager:
    """Manages Agency-style declarative personas"""
    
    def __init__(self):
        self.logger = logger.bind(component="persona_manager")
    
    async def upload_persona_package(
        self,
        session: AsyncSession,
        tenant_id: str,
        persona_zip: bytes,
        created_by: Optional[str] = None,
    ) -> AgentPersona:
        """
        Upload and parse persona package
        
        Args:
            session: Database session
            tenant_id: Tenant ID
            persona_zip: ZIP file bytes containing persona definition
            created_by: User who created the persona
            
        Returns:
            Parsed AgentPersona object
            
        Raises:
            ValueError: If package is invalid
        """
        try:
            # Parse package
            package = PersonaPackage.from_zip(persona_zip)
            
            # Validate
            errors = package.validate()
            if errors:
                raise ValueError(f"Invalid persona package: {', '.join(errors)}")
            
            # Extract metadata from config
            config = package.config_yaml
            
            # Parse allowed tools from tools.py
            allowed_tools = self._parse_tools(package.tools_py) if package.tools_py else []
            
            # Create persona
            persona = AgentPersona(
                name=config['name'],
                vibe=config['vibe'],
                emoji=config.get('emoji', '🤖'),
                color_hex=config.get('color_hex', '#3B82F6'),
                system_prompt_template=package.instructions_md,
                allowed_tools=allowed_tools,
            )
            
            # Store in database
            persona_id = str(uuid4())
            
            # For now, store as JSON in agent_personas table
            # In production, this would use a proper ORM model
            await session.execute(
                """
                INSERT INTO agent_personas (
                    persona_id, tenant_id, name, vibe, emoji, color_hex,
                    instructions_md, tools_definition, manifesto_md,
                    created_at, created_by, version
                ) VALUES (
                    :persona_id, :tenant_id, :name, :vibe, :emoji, :color_hex,
                    :instructions_md, :tools_definition, :manifesto_md,
                    :created_at, :created_by, :version
                )
                """,
                {
                    "persona_id": persona_id,
                    "tenant_id": tenant_id,
                    "name": persona.name,
                    "vibe": persona.vibe,
                    "emoji": persona.emoji,
                    "color_hex": persona.color_hex,
                    "instructions_md": package.instructions_md,
                    "tools_definition": {"tools": allowed_tools},
                    "manifesto_md": package.manifesto_md,
                    "created_at": datetime.utcnow(),
                    "created_by": created_by,
                    "version": 1,
                }
            )
            
            await session.commit()
            
            self.logger.info(
                "persona_uploaded",
                persona_id=persona_id,
                tenant_id=tenant_id,
                name=persona.name,
            )
            
            return persona
            
        except Exception as e:
            self.logger.error("persona_upload_failed", error=str(e), tenant_id=tenant_id)
            raise
    
    async def instantiate_persona(
        self,
        session: AsyncSession,
        persona_id: str,
        tenant_id: str,
        agent_type: AgentType = AgentType.SPECIALIZED,
        model_tier: ModelTier = ModelTier.MID,
        budget_ceiling_usd: float = 10.0,
    ) -> Agent:
        """
        Create agent instance from persona template
        
        Args:
            session: Database session
            persona_id: Persona template ID
            tenant_id: Tenant ID
            agent_type: Type of agent to create
            model_tier: Model tier for agent
            budget_ceiling_usd: Budget ceiling
            
        Returns:
            Agent instance with persona applied
        """
        try:
            # Retrieve persona
            result = await session.execute(
                """
                SELECT * FROM agent_personas
                WHERE persona_id = :persona_id AND tenant_id = :tenant_id
                """,
                {"persona_id": persona_id, "tenant_id": tenant_id}
            )
            persona_row = result.fetchone()
            
            if not persona_row:
                raise ValueError(f"Persona not found: {persona_id}")
            
            # Parse tools from definition
            tools_def = persona_row['tools_definition']
            capabilities = tools_def.get('tools', ['general'])
            
            # Create agent
            agent = Agent(
                agent_id=str(uuid4()),
                tenant_id=tenant_id,
                name=f"{persona_row['name']}-{str(uuid4())[:8]}",
                agent_type=agent_type,
                capabilities=capabilities,
                model_tier=model_tier,
                status=AgentStatus.IDLE,
                budget_ceiling_usd=budget_ceiling_usd,
                spent_usd=0.0,
            )
            
            self.logger.info(
                "persona_instantiated",
                persona_id=persona_id,
                agent_id=agent.agent_id,
                name=agent.name,
            )
            
            return agent
            
        except Exception as e:
            self.logger.error(
                "persona_instantiation_failed",
                error=str(e),
                persona_id=persona_id,
            )
            raise
    
    async def create_agency_manifesto(
        self,
        session: AsyncSession,
        tenant_id: str,
        agency_name: str,
        mission_statement: str,
        shared_instructions: str,
        communication_flows: List[CommunicationFlow],
        world_state_schema: Optional[Dict[str, Any]] = None,
    ) -> AgencyManifesto:
        """
        Create agency manifesto for swarm coordination
        
        Args:
            session: Database session
            tenant_id: Tenant ID
            agency_name: Name of the agency/swarm
            mission_statement: High-level mission
            shared_instructions: Instructions shared by all agents
            communication_flows: Allowed communication patterns
            world_state_schema: Schema for world state (for cinematic use case)
            
        Returns:
            AgencyManifesto object
        """
        try:
            agency_id = str(uuid4())
            
            manifesto = AgencyManifesto(
                agency_id=agency_id,
                tenant_id=tenant_id,
                agency_name=agency_name,
                mission_statement=mission_statement,
                shared_instructions=shared_instructions,
                communication_flows=communication_flows,
                world_state_schema=world_state_schema or {},
            )
            
            # Store in database
            await session.execute(
                """
                INSERT INTO agency_manifestos (
                    agency_id, tenant_id, agency_name, mission_statement,
                    shared_instructions, world_state_schema, created_at, updated_at
                ) VALUES (
                    :agency_id, :tenant_id, :agency_name, :mission_statement,
                    :shared_instructions, :world_state_schema, :created_at, :updated_at
                )
                """,
                {
                    "agency_id": agency_id,
                    "tenant_id": tenant_id,
                    "agency_name": agency_name,
                    "mission_statement": mission_statement,
                    "shared_instructions": shared_instructions,
                    "world_state_schema": world_state_schema or {},
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            )
            
            # Store communication flows
            for flow in communication_flows:
                await session.execute(
                    """
                    INSERT INTO communication_flows (
                        flow_id, agency_id, source_role, target_role,
                        allowed_message_types, bidirectional, created_at
                    ) VALUES (
                        :flow_id, :agency_id, :source_role, :target_role,
                        :allowed_message_types, :bidirectional, :created_at
                    )
                    """,
                    {
                        "flow_id": str(uuid4()),
                        "agency_id": agency_id,
                        "source_role": flow.source_agent_role,
                        "target_role": flow.target_agent_role,
                        "allowed_message_types": flow.allowed_message_types,
                        "bidirectional": flow.bidirectional,
                        "created_at": datetime.utcnow(),
                    }
                )
            
            await session.commit()
            
            self.logger.info(
                "agency_manifesto_created",
                agency_id=agency_id,
                agency_name=agency_name,
                flow_count=len(communication_flows),
            )
            
            return manifesto
            
        except Exception as e:
            self.logger.error(
                "manifesto_creation_failed",
                error=str(e),
                agency_name=agency_name,
            )
            raise
    
    async def validate_communication(
        self,
        session: AsyncSession,
        agency_id: str,
        source_role: str,
        target_role: str,
        message_type: str,
    ) -> bool:
        """
        Validate if communication is allowed per agency manifesto
        
        Args:
            session: Database session
            agency_id: Agency ID
            source_role: Source agent role
            target_role: Target agent role
            message_type: Type of message
            
        Returns:
            True if communication is allowed, False otherwise
        """
        try:
            # Query communication flows
            result = await session.execute(
                """
                SELECT * FROM communication_flows
                WHERE agency_id = :agency_id
                AND (
                    (source_role = :source_role AND target_role = :target_role)
                    OR (bidirectional = true AND source_role = :target_role AND target_role = :source_role)
                )
                """,
                {
                    "agency_id": agency_id,
                    "source_role": source_role,
                    "target_role": target_role,
                }
            )
            
            flows = result.fetchall()
            
            # Check if any flow allows this message type
            for flow in flows:
                allowed_types = flow['allowed_message_types']
                if '*' in allowed_types or message_type in allowed_types:
                    return True
            
            self.logger.warning(
                "communication_blocked",
                agency_id=agency_id,
                source_role=source_role,
                target_role=target_role,
                message_type=message_type,
            )
            
            return False
            
        except Exception as e:
            self.logger.error(
                "communication_validation_failed",
                error=str(e),
                agency_id=agency_id,
            )
            # Fail closed - deny communication on error
            return False
    
    def _parse_tools(self, tools_py: str) -> List[str]:
        """
        Parse tool names from tools.py file
        
        This is a simple heuristic parser. In production, would use AST parsing.
        """
        tools = []
        
        # Look for function definitions
        for line in tools_py.split('\n'):
            line = line.strip()
            if line.startswith('def ') and '(' in line:
                # Extract function name
                func_name = line[4:line.index('(')].strip()
                if not func_name.startswith('_'):  # Skip private functions
                    tools.append(func_name)
        
        return tools


# Global persona manager instance
persona_manager = PersonaManager()


# Made with Bob