"""Community Detection for GraphRAG"""

from typing import Any, Dict, List, Optional, Set

import networkx as nx
import numpy as np
from loguru import logger
from sklearn.cluster import SpectralClustering

from ..generation import LLMGenerator


class CommunityDetector:
    """Detect and analyze communities in knowledge graphs"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Community detection parameters
        self.min_community_size = self.config.get("min_community_size", 3)
        self.max_communities = self.config.get("max_communities", 20)
        self.resolution = self.config.get("resolution", 1.0)
        self.algorithm = self.config.get("algorithm", "louvain")  # louvain, label_propagation, spectral
        
        # LLM for community summarization
        self.llm_generator = LLMGenerator()
        
    def detect_communities(self, graph: nx.Graph) -> Dict[str, Any]:
        """Detect communities in the graph"""
        logger.info(f"Detecting communities using {self.algorithm} algorithm")
        
        if graph.number_of_nodes() == 0:
            return {"communities": [], "modularity": 0.0}
            
        # Select algorithm
        if self.algorithm == "louvain":
            communities = self._louvain_communities(graph)
        elif self.algorithm == "label_propagation":
            communities = self._label_propagation_communities(graph)
        elif self.algorithm == "spectral":
            communities = self._spectral_communities(graph)
        else:
            logger.warning(f"Unknown algorithm {self.algorithm}, using louvain")
            communities = self._louvain_communities(graph)
            
        # Filter small communities
        communities = [
            c for c in communities
            if len(c) >= self.min_community_size
        ]
        
        # Limit number of communities
        if len(communities) > self.max_communities:
            # Keep largest communities
            communities = sorted(communities, key=len, reverse=True)[:self.max_communities]
            
        # Calculate modularity
        modularity = self._calculate_modularity(graph, communities)
        
        # Analyze communities
        community_analysis = []
        for i, community in enumerate(communities):
            analysis = self._analyze_community(graph, community, i)
            community_analysis.append(analysis)
            
        return {
            "communities": communities,
            "community_analysis": community_analysis,
            "modularity": modularity,
            "num_communities": len(communities),
            "algorithm": self.algorithm
        }
        
    def _louvain_communities(self, graph: nx.Graph) -> List[Set[str]]:
        """Detect communities using Louvain algorithm"""
        try:
            import community as community_louvain
            
            # Convert to undirected if needed
            if graph.is_directed():
                graph = graph.to_undirected()
                
            # Detect communities
            partition = community_louvain.best_partition(
                graph,
                resolution=self.resolution
            )
            
            # Convert partition to list of sets
            communities = {}
            for node, comm_id in partition.items():
                if comm_id not in communities:
                    communities[comm_id] = set()
                communities[comm_id].add(node)
                
            return list(communities.values())
            
        except ImportError:
            logger.warning("python-louvain not installed, using label propagation")
            return self._label_propagation_communities(graph)
            
    def _label_propagation_communities(self, graph: nx.Graph) -> List[Set[str]]:
        """Detect communities using label propagation"""
        communities = list(nx.community.label_propagation_communities(graph))
        return communities
        
    def _spectral_communities(self, graph: nx.Graph) -> List[Set[str]]:
        """Detect communities using spectral clustering"""
        if graph.number_of_nodes() < 2:
            return [set(graph.nodes())]
            
        try:
            # Get adjacency matrix
            nodes = list(graph.nodes())
            adj_matrix = nx.adjacency_matrix(graph, nodelist=nodes).todense()
            
            # Determine number of clusters
            n_clusters = min(
                self.max_communities,
                max(2, graph.number_of_nodes() // 10)
            )
            
            # Perform spectral clustering
            clustering = SpectralClustering(
                n_clusters=n_clusters,
                affinity='precomputed',
                random_state=42
            )
            labels = clustering.fit_predict(adj_matrix)
            
            # Convert to community sets
            communities = {}
            for i, label in enumerate(labels):
                if label not in communities:
                    communities[label] = set()
                communities[label].add(nodes[i])
                
            return list(communities.values())
            
        except Exception as e:
            logger.error(f"Spectral clustering failed: {e}")
            return self._label_propagation_communities(graph)
            
    def _calculate_modularity(
        self,
        graph: nx.Graph,
        communities: List[Set[str]]
    ) -> float:
        """Calculate modularity of community partition"""
        try:
            return nx.community.modularity(graph, communities)
        except:
            return 0.0
            
    def _analyze_community(
        self,
        graph: nx.Graph,
        community: Set[str],
        community_id: int
    ) -> Dict[str, Any]:
        """Analyze a single community"""
        # Create subgraph for community
        subgraph = graph.subgraph(community)
        
        # Basic statistics
        analysis = {
            "community_id": community_id,
            "size": len(community),
            "density": nx.density(subgraph),
            "num_edges": subgraph.number_of_edges()
        }
        
        # Find central nodes
        if len(community) > 0:
            # Degree centrality
            degree_centrality = nx.degree_centrality(subgraph)
            top_nodes_by_degree = sorted(
                degree_centrality.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            analysis["central_nodes"] = [
                {"node": node, "centrality": score}
                for node, score in top_nodes_by_degree
            ]
            
            # Get node types if available
            node_types = {}
            for node in community:
                node_type = graph.nodes[node].get("label", "unknown")
                if node_type not in node_types:
                    node_types[node_type] = 0
                node_types[node_type] += 1
                
            analysis["node_types"] = node_types
            
            # Extract key entities
            analysis["key_entities"] = list(community)[:10]
            
        return analysis
        
    async def summarize_community(
        self,
        graph: nx.Graph,
        community: Set[str],
        max_summary_length: int = 200
    ) -> str:
        """Generate natural language summary of a community"""
        # Get community subgraph
        subgraph = graph.subgraph(community)
        
        # Prepare information for summarization
        entities = list(community)[:20]  # Limit for prompt
        
        # Get relationships
        relationships = []
        for source, target, data in subgraph.edges(data=True):
            rel_type = data.get("relation_type", "related to")
            relationships.append(f"{source} {rel_type} {target}")
            if len(relationships) >= 10:
                break
                
        # Create prompt
        prompt = f"""Summarize this group of related entities and their relationships:

Entities: {', '.join(entities)}

Key relationships:
{chr(10).join(relationships)}

Provide a brief summary (max {max_summary_length} words) describing what this group represents and how the entities are connected."""

        try:
            response = await self.llm_generator.generate(
                query=prompt,
                context_chunks=[],
                max_tokens=300,
                temperature=0.7
            )
            
            return response["text"][:max_summary_length]
            
        except Exception as e:
            logger.error(f"Failed to generate community summary: {e}")
            # Fallback summary
            return f"Community of {len(community)} entities including {', '.join(entities[:3])}"
            
    def find_bridge_nodes(self, graph: nx.Graph, communities: List[Set[str]]) -> List[Dict[str, Any]]:
        """Find nodes that bridge between communities"""
        bridge_nodes = []
        
        # Create community mapping
        node_to_community = {}
        for i, community in enumerate(communities):
            for node in community:
                node_to_community[node] = i
                
        # Find nodes connected to multiple communities
        for node in graph.nodes():
            if node not in node_to_community:
                continue
                
            # Get neighbors' communities
            neighbor_communities = set()
            for neighbor in graph.neighbors(node):
                if neighbor in node_to_community:
                    neighbor_communities.add(node_to_community[neighbor])
                    
            # Check if connects to other communities
            if len(neighbor_communities) > 1:
                bridge_nodes.append({
                    "node": node,
                    "community": node_to_community[node],
                    "connected_communities": list(neighbor_communities),
                    "num_connections": len(neighbor_communities)
                })
                
        # Sort by number of connections
        bridge_nodes.sort(key=lambda x: x["num_connections"], reverse=True)
        
        return bridge_nodes
        
    def hierarchical_clustering(
        self,
        graph: nx.Graph,
        max_levels: int = 3
    ) -> Dict[str, Any]:
        """Perform hierarchical community detection"""
        hierarchy = []
        current_graph = graph.copy()
        
        for level in range(max_levels):
            # Detect communities at current level
            communities = self.detect_communities(current_graph)
            
            if len(communities["communities"]) <= 1:
                break
                
            hierarchy.append({
                "level": level,
                "communities": communities,
                "num_nodes": current_graph.number_of_nodes()
            })
            
            # Create meta-graph for next level
            meta_graph = self._create_meta_graph(current_graph, communities["communities"])
            
            if meta_graph.number_of_nodes() <= 2:
                break
                
            current_graph = meta_graph
            
        return {
            "hierarchy": hierarchy,
            "num_levels": len(hierarchy)
        }
        
    def _create_meta_graph(
        self,
        graph: nx.Graph,
        communities: List[Set[str]]
    ) -> nx.Graph:
        """Create meta-graph where each node is a community"""
        meta_graph = nx.Graph()
        
        # Add community nodes
        for i, community in enumerate(communities):
            meta_graph.add_node(
                f"community_{i}",
                size=len(community),
                members=list(community)
            )
            
        # Add edges between communities
        for i, comm1 in enumerate(communities):
            for j, comm2 in enumerate(communities):
                if i >= j:
                    continue
                    
                # Count edges between communities
                edge_count = 0
                for node1 in comm1:
                    for node2 in comm2:
                        if graph.has_edge(node1, node2):
                            edge_count += 1
                            
                if edge_count > 0:
                    meta_graph.add_edge(
                        f"community_{i}",
                        f"community_{j}",
                        weight=edge_count
                    )
                    
        return meta_graph