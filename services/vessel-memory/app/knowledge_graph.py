"""
Knowledge graph management using Neo4j for GraphRAG.
"""

import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable

from .config import settings
from .models import (
    KnowledgeGraphNode, KnowledgeGraphEdge,
    KnowledgeGraphNodeCreate, KnowledgeGraphEdgeCreate,
    GraphRAGQuery, GraphRAGNode, GraphRAGResponse,
    EntityType, RelationshipType, MemoryNode
)
from .vector_store import vector_store

logger = logging.getLogger(__name__)


class KnowledgeGraphManager:
    """Manages knowledge graph operations with Neo4j."""
    
    def __init__(self):
        self.driver: Optional[Driver] = None
    
    async def connect(self):
        """Connect to Neo4j."""
        try:
            self.driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            
            # Verify connectivity
            self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {settings.neo4j_uri}")
            
        except ServiceUnavailable as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Neo4j."""
        if self.driver:
            self.driver.close()
            logger.info("Disconnected from Neo4j")
    
    async def create_node(self, node_create: KnowledgeGraphNodeCreate) -> KnowledgeGraphNode:
        """Create a knowledge graph node."""
        try:
            kg_node_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            with self.driver.session(database=settings.neo4j_database) as session:
                query = """
                CREATE (n:Entity {
                    kg_node_id: $kg_node_id,
                    tenant_id: $tenant_id,
                    entity_type: $entity_type,
                    entity_name: $entity_name,
                    entity_description: $entity_description,
                    properties: $properties,
                    memory_node_ids: $memory_node_ids,
                    created_at: $created_at,
                    is_private: $is_private
                })
                RETURN n
                """
                
                result = session.run(
                    query,
                    kg_node_id=kg_node_id,
                    tenant_id=node_create.tenant_id,
                    entity_type=node_create.entity_type.value,
                    entity_name=node_create.entity_name,
                    entity_description=node_create.entity_description,
                    properties=node_create.properties,
                    memory_node_ids=node_create.memory_node_ids,
                    created_at=now.isoformat(),
                    is_private=node_create.is_private
                )
                
                record = result.single()
                if not record:
                    raise Exception("Failed to create node")
                
                node = KnowledgeGraphNode(
                    kg_node_id=kg_node_id,
                    tenant_id=node_create.tenant_id,
                    entity_type=node_create.entity_type,
                    entity_name=node_create.entity_name,
                    entity_description=node_create.entity_description,
                    properties=node_create.properties,
                    memory_node_ids=node_create.memory_node_ids,
                    created_at=now,
                    is_private=node_create.is_private
                )
                
                logger.info(f"Created knowledge graph node {kg_node_id}")
                return node
                
        except Exception as e:
            logger.error(f"Failed to create knowledge graph node: {e}")
            raise
    
    async def create_edge(self, edge_create: KnowledgeGraphEdgeCreate) -> KnowledgeGraphEdge:
        """Create a knowledge graph edge (relationship)."""
        try:
            edge_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            with self.driver.session(database=settings.neo4j_database) as session:
                query = """
                MATCH (source:Entity {kg_node_id: $source_id, tenant_id: $tenant_id})
                MATCH (target:Entity {kg_node_id: $target_id, tenant_id: $tenant_id})
                CREATE (source)-[r:RELATIONSHIP {
                    edge_id: $edge_id,
                    tenant_id: $tenant_id,
                    relationship_type: $relationship_type,
                    weight: $weight,
                    properties: $properties,
                    created_from_task_id: $created_from_task_id,
                    created_at: $created_at
                }]->(target)
                RETURN r
                """
                
                result = session.run(
                    query,
                    edge_id=edge_id,
                    tenant_id=edge_create.tenant_id,
                    source_id=edge_create.source_kg_node_id,
                    target_id=edge_create.target_kg_node_id,
                    relationship_type=edge_create.relationship_type.value,
                    weight=edge_create.weight,
                    properties=edge_create.properties,
                    created_from_task_id=edge_create.created_from_task_id,
                    created_at=now.isoformat()
                )
                
                record = result.single()
                if not record:
                    raise Exception("Failed to create edge")
                
                edge = KnowledgeGraphEdge(
                    edge_id=edge_id,
                    tenant_id=edge_create.tenant_id,
                    source_kg_node_id=edge_create.source_kg_node_id,
                    target_kg_node_id=edge_create.target_kg_node_id,
                    relationship_type=edge_create.relationship_type,
                    weight=edge_create.weight,
                    properties=edge_create.properties,
                    created_from_task_id=edge_create.created_from_task_id,
                    created_at=now
                )
                
                logger.info(f"Created knowledge graph edge {edge_id}")
                return edge
                
        except Exception as e:
            logger.error(f"Failed to create knowledge graph edge: {e}")
            raise
    
    async def query_graphrag(self, query: GraphRAGQuery) -> GraphRAGResponse:
        """Execute GraphRAG query combining vector search and graph traversal."""
        try:
            start_time = datetime.utcnow()
            
            # Step 1: Vector search to find relevant starting nodes
            from .models import MemorySearchRequest
            vector_results = await vector_store.search_memory(
                MemorySearchRequest(
                    tenant_id=query.tenant_id,
                    agent_id=query.agent_id,
                    query=query.query,
                    top_k=query.vector_top_k,
                    score_threshold=query.vector_score_threshold,
                    include_shared=query.include_shared
                )
            )
            
            # Extract memory node IDs
            memory_node_ids = [result.node.node_id for result in vector_results]
            
            if not memory_node_ids:
                return GraphRAGResponse(
                    nodes=[],
                    edges=[],
                    context_summary="No relevant memories found",
                    total_nodes=0,
                    total_edges=0,
                    query_time_ms=0
                )
            
            # Step 2: Find graph nodes linked to these memories
            with self.driver.session(database=settings.neo4j_database) as session:
                # Build relationship type filter
                rel_types = query.relationship_types or settings.get_relationship_types()
                rel_type_str = "|".join([rt.value for rt in rel_types])
                
                # Build entity type filter
                entity_filter = ""
                if query.entity_types:
                    entity_types_str = "', '".join([et.value for et in query.entity_types])
                    entity_filter = f"AND n.entity_type IN ['{entity_types_str}']"
                
                # Query for connected nodes
                cypher_query = f"""
                MATCH (n:Entity)
                WHERE n.tenant_id = $tenant_id
                AND ANY(mem_id IN n.memory_node_ids WHERE mem_id IN $memory_node_ids)
                {entity_filter}
                OPTIONAL MATCH path = (n)-[r:{rel_type_str}*1..{query.max_depth}]-(connected:Entity)
                WHERE connected.tenant_id = $tenant_id
                WITH n, collect(DISTINCT connected) as connected_nodes, 
                     collect(DISTINCT r) as relationships
                RETURN n, connected_nodes, relationships
                LIMIT $max_nodes
                """
                
                result = session.run(
                    cypher_query,
                    tenant_id=query.tenant_id,
                    memory_node_ids=memory_node_ids,
                    max_nodes=query.max_nodes
                )
                
                # Process results
                graph_nodes = []
                graph_edges = []
                seen_node_ids = set()
                seen_edge_ids = set()
                
                for record in result:
                    # Process main node
                    node_data = record["n"]
                    if node_data["kg_node_id"] not in seen_node_ids:
                        kg_node = self._parse_node(node_data)
                        
                        # Get connected memories
                        connected_memories = [
                            result.node for result in vector_results
                            if result.node.node_id in kg_node.memory_node_ids
                        ]
                        
                        graph_nodes.append(GraphRAGNode(
                            kg_node=kg_node,
                            relevance_score=1.0,  # Could be calculated based on vector scores
                            path_from_query=[kg_node.kg_node_id],
                            connected_memories=connected_memories
                        ))
                        seen_node_ids.add(node_data["kg_node_id"])
                    
                    # Process connected nodes
                    for connected_node in record["connected_nodes"]:
                        if connected_node and connected_node["kg_node_id"] not in seen_node_ids:
                            kg_node = self._parse_node(connected_node)
                            graph_nodes.append(GraphRAGNode(
                                kg_node=kg_node,
                                relevance_score=0.5,  # Lower score for connected nodes
                                path_from_query=[],
                                connected_memories=[]
                            ))
                            seen_node_ids.add(connected_node["kg_node_id"])
                    
                    # Process relationships
                    for rel in record["relationships"]:
                        if rel and rel["edge_id"] not in seen_edge_ids:
                            edge = self._parse_edge(rel)
                            graph_edges.append(edge)
                            seen_edge_ids.add(rel["edge_id"])
                
                # Generate context summary
                context_summary = self._generate_context_summary(graph_nodes, graph_edges)
                
                # Calculate query time
                end_time = datetime.utcnow()
                query_time_ms = (end_time - start_time).total_seconds() * 1000
                
                response = GraphRAGResponse(
                    nodes=graph_nodes[:query.max_nodes],
                    edges=graph_edges,
                    context_summary=context_summary,
                    total_nodes=len(graph_nodes),
                    total_edges=len(graph_edges),
                    query_time_ms=query_time_ms
                )
                
                logger.info(f"GraphRAG query returned {len(graph_nodes)} nodes and {len(graph_edges)} edges")
                return response
                
        except Exception as e:
            logger.error(f"Failed to execute GraphRAG query: {e}")
            raise
    
    def _parse_node(self, node_data: Dict[str, Any]) -> KnowledgeGraphNode:
        """Parse Neo4j node data into KnowledgeGraphNode."""
        return KnowledgeGraphNode(
            kg_node_id=node_data["kg_node_id"],
            tenant_id=node_data["tenant_id"],
            entity_type=EntityType(node_data["entity_type"]),
            entity_name=node_data["entity_name"],
            entity_description=node_data.get("entity_description"),
            properties=node_data.get("properties", {}),
            memory_node_ids=node_data.get("memory_node_ids", []),
            created_at=datetime.fromisoformat(node_data["created_at"]),
            updated_at=datetime.fromisoformat(node_data["updated_at"]) if node_data.get("updated_at") else None,
            is_private=node_data.get("is_private", False)
        )
    
    def _parse_edge(self, edge_data: Dict[str, Any]) -> KnowledgeGraphEdge:
        """Parse Neo4j relationship data into KnowledgeGraphEdge."""
        return KnowledgeGraphEdge(
            edge_id=edge_data["edge_id"],
            tenant_id=edge_data["tenant_id"],
            source_kg_node_id=edge_data.get("source_kg_node_id", ""),
            target_kg_node_id=edge_data.get("target_kg_node_id", ""),
            relationship_type=RelationshipType(edge_data["relationship_type"]),
            weight=edge_data.get("weight", 1.0),
            properties=edge_data.get("properties", {}),
            created_from_task_id=edge_data.get("created_from_task_id"),
            created_at=datetime.fromisoformat(edge_data["created_at"])
        )
    
    def _generate_context_summary(self, nodes: List[GraphRAGNode], edges: List[KnowledgeGraphEdge]) -> str:
        """Generate a text summary of the graph context."""
        if not nodes:
            return "No relevant context found."
        
        summary_parts = []
        
        # Summarize entities
        entity_counts = {}
        for node in nodes:
            entity_type = node.kg_node.entity_type.value
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
        
        entity_summary = ", ".join([f"{count} {etype}(s)" for etype, count in entity_counts.items()])
        summary_parts.append(f"Found {entity_summary}")
        
        # Summarize relationships
        if edges:
            rel_counts = {}
            for edge in edges:
                rel_type = edge.relationship_type.value
                rel_counts[rel_type] = rel_counts.get(rel_type, 0) + 1
            
            rel_summary = ", ".join([f"{count} {rtype}" for rtype, count in rel_counts.items()])
            summary_parts.append(f"with {rel_summary} relationships")
        
        return ". ".join(summary_parts) + "."
    
    async def record_twin_interaction(self, agent_id: str, twin_id: str, tenant_id: str, interaction_data: dict):
        """
        MiroFish-style digital twin memory recording.
        Records agent interactions with digital twins in the knowledge graph.
        """
        try:
            with self.driver.session(database=settings.neo4j_database) as session:
                query = """
                MATCH (a:Entity {entity_type: 'agent', kg_node_id: $agent_id, tenant_id: $tenant_id})
                MATCH (t:Entity {entity_type: 'digital_twin', kg_node_id: $twin_id, tenant_id: $tenant_id})
                MERGE (a)-[r:RELATIONSHIP {relationship_type: 'interacts_with_twin'}]->(t)
                SET r.last_interaction = datetime(),
                    r.interaction_count = coalesce(r.interaction_count, 0) + 1,
                    r.interaction_history = coalesce(r.interaction_history, []) + [$interaction_data]
                RETURN r
                """
                
                result = session.run(
                    query,
                    agent_id=agent_id,
                    twin_id=twin_id,
                    tenant_id=tenant_id,
                    interaction_data=str(interaction_data)
                )
                
                record = result.single()
                if record:
                    logger.info(f"Recorded twin interaction: agent={agent_id}, twin={twin_id}")
                else:
                    logger.warning(f"Failed to record twin interaction: agent or twin not found")
                    
        except Exception as e:
            logger.error(f"Failed to record twin interaction: {e}")
            raise
    
    async def execute_query(self, query: str, parameters: dict = None):
        """
        Execute a custom Cypher query.
        Useful for advanced GraphRAG operations.
        """
        try:
            with self.driver.session(database=settings.neo4j_database) as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Failed to execute custom query: {e}")
            raise


# Global knowledge graph manager instance
knowledge_graph = KnowledgeGraphManager()

# Made with Bob