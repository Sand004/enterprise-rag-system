"""Graph Retriever for knowledge graph-enhanced retrieval"""

from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import numpy as np
from loguru import logger

from ..utils.embeddings import EmbeddingManager
from .graph_store import GraphStore


class GraphRetriever:
    """Retrieve information from knowledge graphs for RAG"""
    
    def __init__(self, graph_store: GraphStore, config: Optional[Dict[str, Any]] = None):
        self.graph_store = graph_store
        self.config = config or {}
        
        # Initialize components
        self.embedding_manager = EmbeddingManager()
        
        # Retrieval configuration
        self.max_subgraph_size = self.config.get("max_subgraph_size", 50)
        self.max_path_length = self.config.get("max_path_length", 3)
        self.min_relevance_score = self.config.get("min_relevance_score", 0.5)
        self.use_embeddings = self.config.get("use_embeddings", True)
        
    async def retrieve_subgraph(
        self,
        query: str,
        graph_ids: Optional[List[str]] = None,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """Retrieve relevant subgraph based on query"""
        logger.info(f"Retrieving subgraph for query: {query[:100]}...")
        
        # Get relevant entities from query
        query_entities = await self._extract_query_entities(query)
        
        # Search for matching entities in graphs
        if graph_ids is None:
            graph_ids = self.graph_store.list_graphs()
            
        all_matches = []
        
        for graph_id in graph_ids:
            graph = self.graph_store.load_graph(graph_id)
            if graph is None:
                continue
                
            # Find matching entities
            matches = self._find_matching_entities(
                graph,
                query_entities,
                query
            )
            
            for match in matches:
                match["graph_id"] = graph_id
                all_matches.append(match)
                
        # Sort by relevance score
        all_matches.sort(key=lambda x: x["score"], reverse=True)
        top_matches = all_matches[:top_k]
        
        # Build subgraph from top matches
        subgraph = self._build_subgraph_from_matches(top_matches)
        
        return {
            "query": query,
            "entities": query_entities,
            "matches": top_matches,
            "subgraph": subgraph,
            "stats": {
                "total_matches": len(all_matches),
                "graphs_searched": len(graph_ids),
                "subgraph_nodes": subgraph.number_of_nodes() if subgraph else 0,
                "subgraph_edges": subgraph.number_of_edges() if subgraph else 0
            }
        }
        
    async def _extract_query_entities(self, query: str) -> List[str]:
        """Extract potential entities from query"""
        # Simple approach: extract capitalized words and phrases
        # In production, use NER model
        entities = []
        
        # Split into words
        words = query.split()
        
        # Extract capitalized words (potential entities)
        for word in words:
            if word[0].isupper() and len(word) > 2:
                entities.append(word)
                
        # Extract quoted phrases
        import re
        quoted = re.findall(r'"([^"]*)"', query)
        entities.extend(quoted)
        
        # Remove duplicates
        entities = list(set(entities))
        
        return entities
        
    def _find_matching_entities(
        self,
        graph: nx.Graph,
        query_entities: List[str],
        full_query: str
    ) -> List[Dict[str, Any]]:
        """Find entities in graph matching query"""
        matches = []
        
        for node, attrs in graph.nodes(data=True):
            score = 0.0
            
            # Check direct entity matches
            for query_entity in query_entities:
                if query_entity.lower() in node.lower():
                    score += 1.0
                elif node.lower() in query_entity.lower():
                    score += 0.8
                    
            # Check if node text appears in query
            if node.lower() in full_query.lower():
                score += 0.5
                
            # Consider node importance
            importance = attrs.get("importance", 0.0)
            score += importance * 0.3
            
            # Consider node degree (connectivity)
            degree = graph.degree(node)
            score += min(degree / 10, 1.0) * 0.2
            
            if score >= self.min_relevance_score:
                matches.append({
                    "entity": node,
                    "score": score,
                    "attributes": attrs,
                    "degree": degree
                })
                
        return matches
        
    def _build_subgraph_from_matches(
        self,
        matches: List[Dict[str, Any]]
    ) -> Optional[nx.Graph]:
        """Build subgraph from matched entities"""
        if not matches:
            return None
            
        subgraph = nx.Graph()
        added_nodes = set()
        
        # Group matches by graph
        matches_by_graph = {}
        for match in matches:
            graph_id = match["graph_id"]
            if graph_id not in matches_by_graph:
                matches_by_graph[graph_id] = []
            matches_by_graph[graph_id].append(match)
            
        # Process each graph
        for graph_id, graph_matches in matches_by_graph.items():
            graph = self.graph_store.load_graph(graph_id)
            if graph is None:
                continue
                
            # Add matched entities and their neighborhoods
            for match in graph_matches:
                entity = match["entity"]
                
                # Add entity if not already added
                if entity not in added_nodes:
                    subgraph.add_node(
                        entity,
                        **graph.nodes[entity],
                        match_score=match["score"],
                        source_graph=graph_id
                    )
                    added_nodes.add(entity)
                    
                # Add neighbors up to specified depth
                self._add_entity_neighborhood(
                    graph,
                    subgraph,
                    entity,
                    added_nodes,
                    depth=2
                )
                
        # Limit subgraph size
        if subgraph.number_of_nodes() > self.max_subgraph_size:
            subgraph = self._prune_subgraph(subgraph, self.max_subgraph_size)
            
        return subgraph
        
    def _add_entity_neighborhood(
        self,
        source_graph: nx.Graph,
        target_graph: nx.Graph,
        entity: str,
        added_nodes: Set[str],
        depth: int
    ):
        """Add entity's neighborhood to subgraph"""
        if depth <= 0:
            return
            
        # Get neighbors
        if entity in source_graph:
            for neighbor in source_graph.neighbors(entity):
                # Add neighbor node
                if neighbor not in added_nodes:
                    target_graph.add_node(
                        neighbor,
                        **source_graph.nodes[neighbor]
                    )
                    added_nodes.add(neighbor)
                    
                # Add edge
                if not target_graph.has_edge(entity, neighbor):
                    target_graph.add_edge(
                        entity,
                        neighbor,
                        **source_graph[entity][neighbor]
                    )
                    
                # Recursively add neighbor's neighborhood
                if len(added_nodes) < self.max_subgraph_size:
                    self._add_entity_neighborhood(
                        source_graph,
                        target_graph,
                        neighbor,
                        added_nodes,
                        depth - 1
                    )
                    
    def _prune_subgraph(self, subgraph: nx.Graph, max_size: int) -> nx.Graph:
        """Prune subgraph to maximum size while preserving important nodes"""
        if subgraph.number_of_nodes() <= max_size:
            return subgraph
            
        # Calculate node scores
        node_scores = {}
        
        for node in subgraph.nodes():
            # Consider match score, degree, and importance
            match_score = subgraph.nodes[node].get("match_score", 0)
            importance = subgraph.nodes[node].get("importance", 0)
            degree = subgraph.degree(node)
            
            node_scores[node] = match_score + importance + (degree / 10)
            
        # Keep top nodes
        sorted_nodes = sorted(node_scores.items(), key=lambda x: x[1], reverse=True)
        nodes_to_keep = [node for node, _ in sorted_nodes[:max_size]]
        
        # Create pruned subgraph
        pruned = subgraph.subgraph(nodes_to_keep).copy()
        
        return pruned
        
    async def get_entity_context(
        self,
        entity: str,
        graph_id: str,
        context_size: int = 10
    ) -> Dict[str, Any]:
        """Get context around an entity"""
        graph = self.graph_store.load_graph(graph_id)
        if graph is None or entity not in graph:
            return {}
            
        # Get entity relations
        relations = self.graph_store.get_entity_relations(
            entity,
            graph_id,
            depth=2
        )
        
        # Build context
        context = {
            "entity": entity,
            "attributes": graph.nodes[entity],
            "relations": relations["relations"][:context_size],
            "connected_entities": []
        }
        
        # Get connected entities with their attributes
        seen = set()
        for rel in relations["relations"]:
            for node in [rel["source"], rel["target"]]:
                if node != entity and node not in seen:
                    seen.add(node)
                    context["connected_entities"].append({
                        "entity": node,
                        "attributes": graph.nodes.get(node, {}),
                        "relation": rel["relation_type"]
                    })
                    
        return context
        
    def find_paths(
        self,
        source_entity: str,
        target_entity: str,
        graph_id: str,
        max_paths: int = 5
    ) -> List[List[str]]:
        """Find paths between two entities"""
        graph = self.graph_store.load_graph(graph_id)
        if graph is None:
            return []
            
        if source_entity not in graph or target_entity not in graph:
            return []
            
        paths = []
        
        try:
            # Find all simple paths up to max length
            all_paths = nx.all_simple_paths(
                graph,
                source_entity,
                target_entity,
                cutoff=self.max_path_length
            )
            
            # Convert generator to list and limit
            for i, path in enumerate(all_paths):
                if i >= max_paths:
                    break
                paths.append(path)
                
        except nx.NetworkXNoPath:
            pass
            
        return paths
        
    def get_graph_summary(self, graph_id: str) -> Dict[str, Any]:
        """Get summary statistics for a graph"""
        graph = self.graph_store.load_graph(graph_id)
        if graph is None:
            return {}
            
        # Calculate various graph metrics
        summary = {
            "graph_id": graph_id,
            "num_nodes": graph.number_of_nodes(),
            "num_edges": graph.number_of_edges(),
            "density": nx.density(graph),
            "is_connected": nx.is_connected(graph),
            "num_components": nx.number_connected_components(graph)
        }
        
        # Get top entities by various metrics
        if graph.number_of_nodes() > 0:
            # By degree
            degrees = dict(graph.degree())
            top_by_degree = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:5]
            summary["top_entities_by_degree"] = [
                {"entity": entity, "degree": degree}
                for entity, degree in top_by_degree
            ]
            
            # By importance (if available)
            importance_scores = {}
            for node, attrs in graph.nodes(data=True):
                importance_scores[node] = attrs.get("importance", 0)
                
            top_by_importance = sorted(
                importance_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            summary["top_entities_by_importance"] = [
                {"entity": entity, "importance": score}
                for entity, score in top_by_importance
            ]
            
        return summary