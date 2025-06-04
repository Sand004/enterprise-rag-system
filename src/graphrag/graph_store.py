"""Graph Store for persisting and managing knowledge graphs"""

import json
import pickle
from typing import Any, Dict, List, Optional, Set

import networkx as nx
from loguru import logger
from neo4j import GraphDatabase

from ..config import settings


class GraphStore:
    """Store and manage knowledge graphs"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Storage backend
        self.backend = self.config.get("backend", "networkx")  # networkx, neo4j
        
        if self.backend == "neo4j":
            self._init_neo4j()
        else:
            # In-memory storage for networkx
            self.graphs: Dict[str, nx.Graph] = {}
            
    def _init_neo4j(self):
        """Initialize Neo4j connection"""
        uri = self.config.get("neo4j_uri", "bolt://localhost:7687")
        user = self.config.get("neo4j_user", "neo4j")
        password = self.config.get("neo4j_password", "password")
        
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("Connected to Neo4j successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            logger.warning("Falling back to in-memory storage")
            self.backend = "networkx"
            self.graphs = {}
            
    def save_graph(self, graph_id: str, graph: nx.Graph) -> bool:
        """Save a graph to storage"""
        try:
            if self.backend == "neo4j":
                return self._save_to_neo4j(graph_id, graph)
            else:
                return self._save_to_memory(graph_id, graph)
        except Exception as e:
            logger.error(f"Failed to save graph {graph_id}: {e}")
            return False
            
    def load_graph(self, graph_id: str) -> Optional[nx.Graph]:
        """Load a graph from storage"""
        try:
            if self.backend == "neo4j":
                return self._load_from_neo4j(graph_id)
            else:
                return self._load_from_memory(graph_id)
        except Exception as e:
            logger.error(f"Failed to load graph {graph_id}: {e}")
            return None
            
    def delete_graph(self, graph_id: str) -> bool:
        """Delete a graph from storage"""
        try:
            if self.backend == "neo4j":
                return self._delete_from_neo4j(graph_id)
            else:
                return self._delete_from_memory(graph_id)
        except Exception as e:
            logger.error(f"Failed to delete graph {graph_id}: {e}")
            return False
            
    def list_graphs(self) -> List[str]:
        """List all stored graph IDs"""
        try:
            if self.backend == "neo4j":
                return self._list_neo4j_graphs()
            else:
                return list(self.graphs.keys())
        except Exception as e:
            logger.error(f"Failed to list graphs: {e}")
            return []
            
    def search_entities(
        self,
        entity_name: str,
        graph_ids: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for entities across graphs"""
        results = []
        
        # Get graphs to search
        if graph_ids is None:
            graph_ids = self.list_graphs()
            
        for graph_id in graph_ids:
            graph = self.load_graph(graph_id)
            if graph is None:
                continue
                
            # Search for matching entities
            for node, attrs in graph.nodes(data=True):
                if entity_name.lower() in node.lower():
                    results.append({
                        "graph_id": graph_id,
                        "entity": node,
                        "attributes": attrs,
                        "degree": graph.degree(node),
                        "importance": attrs.get("importance", 0)
                    })
                    
        # Sort by importance and limit
        results.sort(key=lambda x: x["importance"], reverse=True)
        return results[:limit]
        
    def get_entity_relations(
        self,
        entity: str,
        graph_id: str,
        depth: int = 1
    ) -> Dict[str, Any]:
        """Get relations for an entity up to specified depth"""
        graph = self.load_graph(graph_id)
        if graph is None or entity not in graph:
            return {}
            
        # BFS to get relations up to depth
        visited = set()
        relations = {"entity": entity, "relations": []}
        queue = [(entity, 0)]
        
        while queue:
            current, current_depth = queue.pop(0)
            
            if current in visited or current_depth > depth:
                continue
                
            visited.add(current)
            
            # Get neighbors
            for neighbor in graph.neighbors(current):
                edge_data = graph[current][neighbor]
                
                relations["relations"].append({
                    "source": current,
                    "target": neighbor,
                    "relation_type": edge_data.get("relation_type", "related"),
                    "confidence": edge_data.get("confidence", 0.5),
                    "depth": current_depth
                })
                
                if current_depth < depth:
                    queue.append((neighbor, current_depth + 1))
                    
        return relations
        
    # NetworkX backend methods
    def _save_to_memory(self, graph_id: str, graph: nx.Graph) -> bool:
        """Save graph to in-memory storage"""
        self.graphs[graph_id] = graph.copy()
        return True
        
    def _load_from_memory(self, graph_id: str) -> Optional[nx.Graph]:
        """Load graph from in-memory storage"""
        return self.graphs.get(graph_id)
        
    def _delete_from_memory(self, graph_id: str) -> bool:
        """Delete graph from in-memory storage"""
        if graph_id in self.graphs:
            del self.graphs[graph_id]
            return True
        return False
        
    # Neo4j backend methods
    def _save_to_neo4j(self, graph_id: str, graph: nx.Graph) -> bool:
        """Save graph to Neo4j"""
        with self.driver.session() as session:
            # Clear existing graph
            session.run(
                "MATCH (n {graph_id: $graph_id})-[r]-() DELETE r",
                graph_id=graph_id
            )
            session.run(
                "MATCH (n {graph_id: $graph_id}) DELETE n",
                graph_id=graph_id
            )
            
            # Add nodes
            for node, attrs in graph.nodes(data=True):
                properties = {
                    "graph_id": graph_id,
                    "name": node,
                    **attrs
                }
                session.run(
                    """
                    CREATE (n:Entity $props)
                    """,
                    props=properties
                )
                
            # Add edges
            for source, target, attrs in graph.edges(data=True):
                session.run(
                    """
                    MATCH (a:Entity {graph_id: $graph_id, name: $source})
                    MATCH (b:Entity {graph_id: $graph_id, name: $target})
                    CREATE (a)-[r:RELATED $props]->(b)
                    """,
                    graph_id=graph_id,
                    source=source,
                    target=target,
                    props=attrs
                )
                
        return True
        
    def _load_from_neo4j(self, graph_id: str) -> Optional[nx.Graph]:
        """Load graph from Neo4j"""
        graph = nx.Graph()
        graph.graph["graph_id"] = graph_id
        
        with self.driver.session() as session:
            # Load nodes
            result = session.run(
                """
                MATCH (n:Entity {graph_id: $graph_id})
                RETURN n
                """,
                graph_id=graph_id
            )
            
            for record in result:
                node = record["n"]
                properties = dict(node)
                name = properties.pop("name")
                properties.pop("graph_id", None)
                graph.add_node(name, **properties)
                
            # Load edges
            result = session.run(
                """
                MATCH (a:Entity {graph_id: $graph_id})-[r:RELATED]->(b:Entity {graph_id: $graph_id})
                RETURN a.name as source, b.name as target, r
                """,
                graph_id=graph_id
            )
            
            for record in result:
                source = record["source"]
                target = record["target"]
                properties = dict(record["r"])
                graph.add_edge(source, target, **properties)
                
        return graph
        
    def _delete_from_neo4j(self, graph_id: str) -> bool:
        """Delete graph from Neo4j"""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (n:Entity {graph_id: $graph_id})-[r]-()
                DELETE r, n
                """,
                graph_id=graph_id
            )
        return True
        
    def _list_neo4j_graphs(self) -> List[str]:
        """List all graph IDs in Neo4j"""
        graph_ids = set()
        
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (n:Entity)
                RETURN DISTINCT n.graph_id as graph_id
                """
            )
            
            for record in result:
                graph_ids.add(record["graph_id"])
                
        return list(graph_ids)
        
    def merge_graphs(self, graph_ids: List[str], merged_id: str) -> Optional[nx.Graph]:
        """Merge multiple graphs into one"""
        if not graph_ids:
            return None
            
        # Start with first graph
        merged_graph = self.load_graph(graph_ids[0])
        if merged_graph is None:
            return None
            
        merged_graph = merged_graph.copy()
        
        # Merge remaining graphs
        for graph_id in graph_ids[1:]:
            graph = self.load_graph(graph_id)
            if graph is None:
                continue
                
            # Merge nodes and edges
            for node, attrs in graph.nodes(data=True):
                if node in merged_graph:
                    # Update attributes
                    merged_graph.nodes[node].update(attrs)
                else:
                    merged_graph.add_node(node, **attrs)
                    
            for source, target, attrs in graph.edges(data=True):
                if merged_graph.has_edge(source, target):
                    # Update edge attributes
                    merged_graph[source][target].update(attrs)
                else:
                    merged_graph.add_edge(source, target, **attrs)
                    
        # Save merged graph
        self.save_graph(merged_id, merged_graph)
        
        return merged_graph
        
    def export_graph(self, graph_id: str, format: str = "json") -> Optional[str]:
        """Export graph in specified format"""
        graph = self.load_graph(graph_id)
        if graph is None:
            return None
            
        if format == "json":
            # Convert to node-link format
            data = nx.node_link_data(graph)
            return json.dumps(data, indent=2)
            
        elif format == "gexf":
            # Export as GEXF (Graph Exchange XML Format)
            import io
            buffer = io.StringIO()
            nx.write_gexf(graph, buffer)
            return buffer.getvalue()
            
        elif format == "graphml":
            # Export as GraphML
            import io
            buffer = io.StringIO()
            nx.write_graphml(graph, buffer)
            return buffer.getvalue()
            
        else:
            logger.error(f"Unsupported export format: {format}")
            return None
            
    def close(self):
        """Close connections"""
        if self.backend == "neo4j" and hasattr(self, "driver"):
            self.driver.close()