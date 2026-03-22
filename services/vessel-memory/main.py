"""
vessel-memory service - FastAPI application for long-term memory management.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import settings
from app.models import (
    MemoryNodeCreate, MemoryNode, MemorySearchRequest, MemorySearchResponse,
    MemoryNodeUpdate, KnowledgeGraphNodeCreate, KnowledgeGraphNode,
    KnowledgeGraphEdgeCreate, KnowledgeGraphEdge, GraphRAGQuery,
    GraphRAGResponse, ContextRetrievalRequest, ContextWindow,
    HealthStatus, ServiceMetrics
)
from app.database import db_manager
from app.vector_store import vector_store
from app.knowledge_graph import knowledge_graph
from app.kafka_producer import kafka_producer

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown."""
    # Startup
    logger.info(f"Starting {settings.service_name} v{settings.service_version}")
    
    try:
        await db_manager.connect()
        await db_manager.create_tables()
        await vector_store.connect()
        await knowledge_graph.connect()
        await kafka_producer.connect()
        logger.info("All connections established successfully")
    except Exception as e:
        logger.error(f"Failed to initialize connections: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down service")
    await kafka_producer.disconnect()
    await knowledge_graph.disconnect()
    await vector_store.disconnect()
    await db_manager.disconnect()


# Create FastAPI app
app = FastAPI(
    title="vessel-memory",
    description="Long-term memory service with vector search and knowledge graphs",
    version=settings.service_version,
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


# Health check endpoints
@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    checks = {
        "database": db_manager.session is not None or db_manager.pg_pool is not None,
        "vector_store": vector_store.client is not None,
        "knowledge_graph": knowledge_graph.driver is not None,
        "kafka": kafka_producer.producer is not None
    }
    
    status_value = "healthy" if all(checks.values()) else "degraded"
    
    return HealthStatus(
        status=status_value,
        version=settings.service_version,
        checks=checks,
        details={
            "service": settings.service_name,
            "environment": settings.environment
        }
    )


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {"status": "ready"}


# Memory endpoints
@app.post("/v1/memory", response_model=MemoryNode, status_code=status.HTTP_201_CREATED)
async def create_memory(memory: MemoryNodeCreate):
    """Create a new memory node."""
    try:
        # Add to vector store
        memory_node = await vector_store.add_memory(memory)
        
        # Publish event
        await kafka_producer.publish_memory_created(
            tenant_id=memory.tenant_id,
            node_id=memory_node.node_id,
            memory_type=memory.memory_type.value,
            agent_id=memory.agent_id
        )
        
        logger.info(f"Created memory node {memory_node.node_id}")
        return memory_node
        
    except Exception as e:
        logger.error(f"Failed to create memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/v1/memory/search", response_model=MemorySearchResponse)
async def search_memory(request: MemorySearchRequest):
    """Search for similar memories."""
    try:
        start_time = datetime.utcnow()
        
        # Search vector store
        results = await vector_store.search_memory(request)
        
        # Calculate search time
        end_time = datetime.utcnow()
        search_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Publish event
        await kafka_producer.publish_memory_retrieved(
            tenant_id=request.tenant_id,
            query=request.query,
            result_count=len(results),
            agent_id=request.agent_id
        )
        
        return MemorySearchResponse(
            results=results,
            total_count=len(results),
            search_time_ms=search_time_ms
        )
        
    except Exception as e:
        logger.error(f"Failed to search memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.delete("/v1/memory/{tenant_id}/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(tenant_id: str, node_id: str):
    """Delete a memory node."""
    try:
        await vector_store.delete_memory(tenant_id, node_id)
        
        # Publish event
        await kafka_producer.publish_memory_deleted(
            tenant_id=tenant_id,
            node_id=node_id
        )
        
        logger.info(f"Deleted memory node {node_id}")
        
    except Exception as e:
        logger.error(f"Failed to delete memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Knowledge Graph endpoints
@app.post("/v1/graph/nodes", response_model=KnowledgeGraphNode, status_code=status.HTTP_201_CREATED)
async def create_graph_node(node: KnowledgeGraphNodeCreate):
    """Create a knowledge graph node."""
    try:
        kg_node = await knowledge_graph.create_node(node)
        
        # Publish event
        await kafka_producer.publish_graph_updated(
            tenant_id=node.tenant_id,
            update_type="node_created",
            entity_id=kg_node.kg_node_id,
            details={"entity_type": kg_node.entity_type.value, "entity_name": kg_node.entity_name}
        )
        
        logger.info(f"Created knowledge graph node {kg_node.kg_node_id}")
        return kg_node
        
    except Exception as e:
        logger.error(f"Failed to create graph node: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/v1/graph/edges", response_model=KnowledgeGraphEdge, status_code=status.HTTP_201_CREATED)
async def create_graph_edge(edge: KnowledgeGraphEdgeCreate):
    """Create a knowledge graph edge."""
    try:
        kg_edge = await knowledge_graph.create_edge(edge)
        
        # Publish event
        await kafka_producer.publish_graph_updated(
            tenant_id=edge.tenant_id,
            update_type="edge_created",
            entity_id=kg_edge.edge_id,
            details={"relationship_type": kg_edge.relationship_type.value}
        )
        
        logger.info(f"Created knowledge graph edge {kg_edge.edge_id}")
        return kg_edge
        
    except Exception as e:
        logger.error(f"Failed to create graph edge: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# GraphRAG endpoint
@app.post("/v1/graphrag", response_model=GraphRAGResponse)
async def query_graphrag(query: GraphRAGQuery):
    """Execute GraphRAG query combining vector search and graph traversal."""
    try:
        response = await knowledge_graph.query_graphrag(query)
        
        logger.info(
            f"GraphRAG query returned {response.total_nodes} nodes "
            f"and {response.total_edges} edges in {response.query_time_ms:.2f}ms"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to execute GraphRAG query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Context retrieval endpoint
@app.post("/v1/context", response_model=ContextWindow)
async def retrieve_context(request: ContextRetrievalRequest):
    """Retrieve context window for agent."""
    try:
        context = ContextWindow(
            tenant_id=request.tenant_id,
            agent_id=request.agent_id,
            task_id=request.task_id
        )
        
        # Retrieve memories by type
        if request.include_episodic or request.include_semantic or request.include_procedural:
            from app.models import MemoryType
            memory_types = []
            if request.include_episodic:
                memory_types.append(MemoryType.EPISODIC)
            if request.include_semantic:
                memory_types.append(MemoryType.SEMANTIC)
            if request.include_procedural:
                memory_types.append(MemoryType.PROCEDURAL)
            
            search_request = MemorySearchRequest(
                tenant_id=request.tenant_id,
                agent_id=request.agent_id,
                query=request.query,
                memory_types=memory_types,
                top_k=request.max_memories_per_type * len(memory_types)
            )
            
            search_results = await vector_store.search_memory(search_request)
            
            # Organize by type
            for result in search_results:
                if result.node.memory_type == MemoryType.EPISODIC:
                    context.episodic_memories.append(result.node)
                elif result.node.memory_type == MemoryType.SEMANTIC:
                    context.semantic_memories.append(result.node)
                elif result.node.memory_type == MemoryType.PROCEDURAL:
                    context.procedural_memories.append(result.node)
        
        # Retrieve graph context if requested
        if request.include_graph:
            graphrag_query = GraphRAGQuery(
                tenant_id=request.tenant_id,
                agent_id=request.agent_id,
                query=request.query,
                max_depth=request.graph_max_depth,
                max_nodes=50
            )
            
            graphrag_response = await knowledge_graph.query_graphrag(graphrag_query)
            context.graph_nodes = [node.kg_node for node in graphrag_response.nodes]
            context.graph_edges = graphrag_response.edges
        
        logger.info(f"Retrieved context for agent {request.agent_id}")
        return context
        
    except Exception as e:
        logger.error(f"Failed to retrieve context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Metrics endpoint
@app.get("/v1/metrics", response_model=ServiceMetrics)
async def get_metrics():
    """Get service metrics."""
    try:
        # This is a simplified version - in production, collect real metrics
        metrics = ServiceMetrics(
            total_memory_nodes=0,
            total_graph_nodes=0,
            total_graph_edges=0,
            avg_search_time_ms=0.0,
            avg_graphrag_time_ms=0.0,
            cache_hit_rate=0.0,
            vector_store_size_mb=0.0,
            graph_store_size_mb=0.0
        )
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )

# Made with Bob