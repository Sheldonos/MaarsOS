"""Database connection and schema management for vessel-swarm"""
import asyncio
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Integer, Float, DateTime, ARRAY, Enum as SQLEnum, Text
import structlog

from .config import settings
from .models import AgentType, AgentStatus, ModelTier

logger = structlog.get_logger()

Base = declarative_base()


# SQLAlchemy ORM Models
class AgentDB(Base):
    """Agent database table"""
    __tablename__ = "agents"
    
    agent_id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True)
    agent_type = Column(SQLEnum(AgentType), nullable=False)
    capabilities = Column(ARRAY(String), nullable=False)
    model_tier = Column(SQLEnum(ModelTier), nullable=False)
    status = Column(SQLEnum(AgentStatus), nullable=False, default=AgentStatus.IDLE)
    current_task_id = Column(String, nullable=True)
    budget_ceiling_usd = Column(Float, nullable=False)
    spent_usd = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_active_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    parent_agent_id = Column(String, nullable=True)


class AgentPoolDB(Base):
    """Agent pool database table"""
    __tablename__ = "agent_pools"
    
    pool_id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    agent_type = Column(SQLEnum(AgentType), nullable=False)
    min_size = Column(Integer, nullable=False)
    max_size = Column(Integer, nullable=False)
    current_size = Column(Integer, nullable=False, default=0)
    warm_agents = Column(ARRAY(String), nullable=False, default=[])
    capabilities = Column(ARRAY(String), nullable=False)
    model_tier = Column(SQLEnum(ModelTier), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AgentMetricsDB(Base):
    """Agent metrics database table"""
    __tablename__ = "agent_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, nullable=False, index=True)
    agent_id = Column(String, nullable=False, index=True)
    metric_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    tasks_completed = Column(Integer, nullable=False, default=0)
    avg_execution_time_ms = Column(Integer, nullable=False, default=0)
    total_cost_usd = Column(Float, nullable=False, default=0.0)
    error_count = Column(Integer, nullable=False, default=0)


class Database:
    """Database connection manager"""
    
    def __init__(self):
        self.engine = None
        self.session_maker = None
        self._initialized = False
    
    async def connect(self):
        """Connect to database"""
        if self._initialized:
            return
        
        try:
            logger.info("connecting_to_database", url=settings.database_url.split("@")[1])
            
            self.engine = create_async_engine(
                settings.database_url,
                echo=False,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
            )
            
            self.session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            
            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            self._initialized = True
            logger.info("database_connected")
            
        except Exception as e:
            logger.error("database_connection_failed", error=str(e))
            raise
    
    async def disconnect(self):
        """Disconnect from database"""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("database_disconnected")
    
    async def get_session(self) -> AsyncSession:
        """Get database session"""
        if not self._initialized:
            await self.connect()
        return self.session_maker()
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            async with self.get_session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return False


# Global database instance
db = Database()


async def get_db() -> AsyncSession:
    """Dependency for FastAPI to get database session"""
    async with db.get_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Made with Bob