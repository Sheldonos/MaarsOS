"""
Cognee-style hybrid memory retrieval combining vector search and graph traversal.
Provides cognitive, personalized agent memory by fusing semantic similarity with relational context.
"""

import logging
from typing import List, Dict, Any
from .knowledge_graph import knowledge_graph
from .vector_store import vector_store
from .models import MemorySearchRequest

logger = logging.getLogger(__name__)


class CogneeHybridMemory:
    """
    Cognee-style hybrid memory system that combines:
    1. Vector search for semantic similarity
    2. Graph traversal for relational context
    """
    
    async def retrieve_cognitive_context(
        self,
        tenant_id: str,
        agent_id: str,
        query: str,
        top_k: int = 5,
        include_shared: bool = False
    ) -> Dict[str, Any]:
        """
        Cognee-style hybrid retrieval that merges vector similarity with graph traversal.
        
        Args:
            tenant_id: Tenant identifier
            agent_id: Agent identifier
            query: Search query
            top_k: Number of top results to return
            include_shared: Whether to include shared memories
            
        Returns:
            Dictionary containing semantic matches and relational context
        """
        try:
            # Step 1: Vector Search for semantic similarity
            logger.info(f"Performing vector search for query: {query[:50]}...")
            vector_results = await vector_store.search_memory(
                MemorySearchRequest(
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    query=query,
                    top_k=top_k,
                    score_threshold=0.7,
                    include_shared=include_shared
                )
            )
            
            if not vector_results:
                logger.info("No semantic matches found")
                return {
                    "semantic_matches": [],
                    "relational_context": [],
                    "cognitive_summary": "No relevant memories found"
                }
            
            # Step 2: Extract node IDs from vector results
            node_ids = []
            for result in vector_results:
                # Check if the memory node has associated knowledge graph nodes
                if hasattr(result.node, 'metadata') and 'kg_node_id' in result.node.metadata:
                    node_ids.append(result.node.metadata['kg_node_id'])
            
            # Step 3: Graph Traversal for relational context
            graph_context = []
            if node_ids:
                logger.info(f"Performing graph traversal for {len(node_ids)} nodes")
                for node_id in node_ids:
                    try:
                        # Get 1-hop neighbors for the semantically relevant nodes
                        neighbors = await knowledge_graph.execute_query(
                            """
                            MATCH (n {kg_node_id: $node_id, tenant_id: $tenant_id})-[r]-(neighbor)
                            WHERE neighbor.tenant_id = $tenant_id
                            RETURN type(r) as relationship_type, 
                                   neighbor.entity_name as entity_name,
                                   neighbor.entity_type as entity_type,
                                   neighbor.entity_description as description
                            LIMIT 10
                            """,
                            {"node_id": node_id, "tenant_id": tenant_id}
                        )
                        
                        if neighbors:
                            graph_context.extend(neighbors)
                            
                    except Exception as e:
                        logger.warning(f"Failed to get neighbors for node {node_id}: {e}")
                        continue
            
            # Step 4: Generate cognitive summary
            cognitive_summary = self._generate_cognitive_summary(
                vector_results, 
                graph_context
            )
            
            logger.info(
                f"Hybrid retrieval complete: {len(vector_results)} semantic matches, "
                f"{len(graph_context)} relational connections"
            )
            
            return {
                "semantic_matches": [
                    {
                        "content": result.node.content,
                        "score": result.score,
                        "memory_type": result.node.memory_type.value,
                        "created_at": result.node.created_at.isoformat(),
                        "metadata": result.node.metadata
                    }
                    for result in vector_results
                ],
                "relational_context": graph_context,
                "cognitive_summary": cognitive_summary
            }
            
        except Exception as e:
            logger.error(f"Hybrid retrieval failed: {e}")
            raise
    
    def _generate_cognitive_summary(
        self,
        vector_results: List[Any],
        graph_context: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a natural language summary of the cognitive context.
        
        Args:
            vector_results: Results from vector search
            graph_context: Results from graph traversal
            
        Returns:
            Natural language summary
        """
        summary_parts = []
        
        # Summarize semantic matches
        if vector_results:
            memory_types = {}
            for result in vector_results:
                mem_type = result.node.memory_type.value
                memory_types[mem_type] = memory_types.get(mem_type, 0) + 1
            
            type_summary = ", ".join([
                f"{count} {mtype}" for mtype, count in memory_types.items()
            ])
            summary_parts.append(f"Found {len(vector_results)} relevant memories ({type_summary})")
        
        # Summarize relational context
        if graph_context:
            entity_types = {}
            relationship_types = {}
            
            for ctx in graph_context:
                if 'entity_type' in ctx:
                    etype = ctx['entity_type']
                    entity_types[etype] = entity_types.get(etype, 0) + 1
                
                if 'relationship_type' in ctx:
                    rtype = ctx['relationship_type']
                    relationship_types[rtype] = relationship_types.get(rtype, 0) + 1
            
            if entity_types:
                entity_summary = ", ".join([
                    f"{count} {etype}" for etype, count in entity_types.items()
                ])
                summary_parts.append(f"with connections to {entity_summary}")
            
            if relationship_types:
                rel_summary = ", ".join([
                    f"{count} {rtype}" for rtype, count in relationship_types.items()
                ])
                summary_parts.append(f"through {rel_summary} relationships")
        
        if not summary_parts:
            return "No cognitive context available"
        
        return ". ".join(summary_parts) + "."


# Global instance
cognee_hybrid = CogneeHybridMemory()

# Made with Bob