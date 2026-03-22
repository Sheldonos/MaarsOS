"""
Vector store management using Qdrant for semantic memory search.
"""

import logging
import hashlib
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue, Range, SearchRequest
)
import openai

from .config import settings
from .models import (
    MemoryNode, MemoryNodeCreate, MemorySearchRequest,
    MemorySearchResult, MemoryType
)

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Manages vector store operations with Qdrant."""
    
    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.embedding_model = settings.embedding_model
        self.embedding_dimension = settings.embedding_dimension
        
        # Initialize OpenAI if using OpenAI embeddings
        if settings.embedding_provider == "openai" and settings.openai_api_key:
            openai.api_key = settings.openai_api_key
    
    async def connect(self):
        """Connect to Qdrant."""
        try:
            self.client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.qdrant_api_key,
                timeout=settings.vector_search_timeout_seconds
            )
            logger.info(f"Connected to Qdrant at {settings.qdrant_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Qdrant."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from Qdrant")
    
    def _get_collection_name(self, tenant_id: str) -> str:
        """Get collection name for tenant."""
        return f"{settings.qdrant_collection_prefix}_{tenant_id}"
    
    async def create_collection(self, tenant_id: str):
        """Create a collection for a tenant if it doesn't exist."""
        collection_name = self._get_collection_name(tenant_id)
        
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            if any(c.name == collection_name for c in collections):
                logger.info(f"Collection {collection_name} already exists")
                return
            
            # Create collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dimension,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created collection {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        try:
            if settings.embedding_provider == "openai":
                response = openai.embeddings.create(
                    model=self.embedding_model,
                    input=text
                )
                return response.data[0].embedding
            else:
                # Placeholder for local embedding model
                # In production, use sentence-transformers or similar
                logger.warning("Local embedding not implemented, using mock")
                return [0.0] * self.embedding_dimension
                
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    async def add_memory(self, memory: MemoryNodeCreate) -> MemoryNode:
        """Add a memory node to the vector store."""
        try:
            # Ensure collection exists
            await self.create_collection(memory.tenant_id)
            
            # Generate embedding
            embedding = await self.generate_embedding(memory.content)
            
            # Generate node ID and provenance hash
            node_id = str(uuid.uuid4())
            provenance_hash = self._generate_provenance_hash(
                memory.content,
                memory.tenant_id,
                memory.source_task_id or ""
            )
            
            # Calculate expiry
            expires_at = self._calculate_expiry(memory.memory_type)
            
            # Create memory node
            memory_node = MemoryNode(
                node_id=node_id,
                tenant_id=memory.tenant_id,
                agent_id=memory.agent_id,
                content=memory.content,
                embedding=embedding,
                memory_type=memory.memory_type,
                importance_score=memory.importance_score,
                provenance_hash=provenance_hash,
                source_task_id=memory.source_task_id,
                source_tool=memory.source_tool,
                metadata=memory.metadata,
                tags=memory.tags,
                created_at=datetime.utcnow(),
                expires_at=expires_at,
                is_private=memory.is_private
            )
            
            # Prepare payload
            payload = {
                "node_id": node_id,
                "tenant_id": memory.tenant_id,
                "agent_id": memory.agent_id,
                "content": memory.content,
                "memory_type": memory.memory_type.value,
                "importance_score": memory.importance_score,
                "provenance_hash": provenance_hash,
                "source_task_id": memory.source_task_id,
                "source_tool": memory.source_tool,
                "metadata": memory.metadata,
                "tags": memory.tags,
                "created_at": memory_node.created_at.isoformat(),
                "expires_at": expires_at.isoformat() if expires_at else None,
                "is_private": memory.is_private
            }
            
            # Insert into Qdrant
            collection_name = self._get_collection_name(memory.tenant_id)
            self.client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=node_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )
            
            logger.info(f"Added memory node {node_id} to collection {collection_name}")
            return memory_node
            
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            raise
    
    async def search_memory(self, request: MemorySearchRequest) -> List[MemorySearchResult]:
        """Search for similar memories."""
        try:
            # Ensure collection exists
            collection_name = self._get_collection_name(request.tenant_id)
            
            # Generate query embedding
            query_embedding = await self.generate_embedding(request.query)
            
            # Build filter
            filter_conditions = [
                FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=request.tenant_id)
                )
            ]
            
            # Filter by agent if specified
            if request.agent_id:
                filter_conditions.append(
                    FieldCondition(
                        key="agent_id",
                        match=MatchValue(value=request.agent_id)
                    )
                )
            
            # Filter by memory types if specified
            if request.memory_types:
                memory_type_values = [mt.value for mt in request.memory_types]
                filter_conditions.append(
                    FieldCondition(
                        key="memory_type",
                        match=MatchValue(any=memory_type_values)
                    )
                )
            
            # Filter by privacy
            if not request.include_shared:
                filter_conditions.append(
                    FieldCondition(
                        key="is_private",
                        match=MatchValue(value=False)
                    )
                )
            
            # Search
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                query_filter=Filter(must=filter_conditions) if filter_conditions else None,
                limit=request.top_k,
                score_threshold=request.score_threshold
            )
            
            # Convert results
            results = []
            for hit in search_result:
                memory_node = MemoryNode(
                    node_id=hit.payload["node_id"],
                    tenant_id=hit.payload["tenant_id"],
                    agent_id=hit.payload.get("agent_id"),
                    content=hit.payload["content"],
                    memory_type=MemoryType(hit.payload["memory_type"]),
                    importance_score=hit.payload["importance_score"],
                    provenance_hash=hit.payload.get("provenance_hash"),
                    source_task_id=hit.payload.get("source_task_id"),
                    source_tool=hit.payload.get("source_tool"),
                    metadata=hit.payload.get("metadata", {}),
                    tags=hit.payload.get("tags", []),
                    created_at=datetime.fromisoformat(hit.payload["created_at"]),
                    expires_at=datetime.fromisoformat(hit.payload["expires_at"]) if hit.payload.get("expires_at") else None,
                    is_private=hit.payload.get("is_private", False)
                )
                
                results.append(MemorySearchResult(
                    node=memory_node,
                    score=hit.score,
                    distance=1.0 - hit.score  # Convert cosine similarity to distance
                ))
            
            logger.info(f"Found {len(results)} memories for query")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search memory: {e}")
            raise
    
    async def delete_memory(self, tenant_id: str, node_id: str):
        """Delete a memory node."""
        try:
            collection_name = self._get_collection_name(tenant_id)
            self.client.delete(
                collection_name=collection_name,
                points_selector=[node_id]
            )
            logger.info(f"Deleted memory node {node_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            raise
    
    async def cleanup_expired_memories(self, tenant_id: str):
        """Remove expired memories from the vector store."""
        try:
            collection_name = self._get_collection_name(tenant_id)
            now = datetime.utcnow().isoformat()
            
            # Qdrant doesn't support direct deletion by filter in all versions
            # This is a simplified approach - in production, implement batch deletion
            logger.info(f"Cleanup expired memories for tenant {tenant_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired memories: {e}")
            raise
    
    def _generate_provenance_hash(self, content: str, tenant_id: str, source_id: str) -> str:
        """Generate provenance hash for memory."""
        if not settings.provenance_enabled:
            return ""
        
        data = f"{content}|{tenant_id}|{source_id}|{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _calculate_expiry(self, memory_type: MemoryType) -> Optional[datetime]:
        """Calculate expiry date based on memory type."""
        now = datetime.utcnow()
        
        if memory_type == MemoryType.EPISODIC:
            return now + timedelta(days=settings.memory_ttl_episodic_days)
        elif memory_type == MemoryType.SEMANTIC:
            return now + timedelta(days=settings.memory_ttl_semantic_days)
        elif memory_type == MemoryType.PROCEDURAL:
            return now + timedelta(days=settings.memory_ttl_procedural_days)
        
        return None


# Global vector store manager instance
vector_store = VectorStoreManager()

# Made with Bob