"""Graph Builder for constructing knowledge graphs from documents"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import spacy
from loguru import logger

from ..generation import LLMGenerator
from ..utils.text_processing import TextProcessor


class GraphBuilder:
    """Build knowledge graphs from document content"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Load spaCy model for NER and dependency parsing
        self.nlp = self._load_spacy_model()
        
        # Initialize components
        self.text_processor = TextProcessor()
        self.llm_generator = LLMGenerator()
        
        # Graph configuration
        self.min_entity_length = self.config.get("min_entity_length", 2)
        self.max_entities_per_chunk = self.config.get("max_entities_per_chunk", 50)
        self.min_relation_confidence = self.config.get("min_relation_confidence", 0.7)
        
    def _load_spacy_model(self):
        """Load spaCy model for NLP tasks"""
        model_name = self.config.get("spacy_model", "en_core_web_sm")
        try:
            import spacy
            return spacy.load(model_name)
        except OSError:
            logger.warning(f"spaCy model {model_name} not found, downloading...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", model_name])
            return spacy.load(model_name)
            
    def build_graph_from_chunks(
        self,
        chunks: List[Dict[str, Any]],
        document_id: str
    ) -> nx.Graph:
        """Build a knowledge graph from document chunks"""
        logger.info(f"Building graph for document {document_id}")
        
        # Initialize graph
        graph = nx.Graph()
        graph.graph["document_id"] = document_id
        
        # Process each chunk
        all_entities = []
        all_relations = []
        
        for chunk_idx, chunk in enumerate(chunks):
            chunk_text = chunk.get("content", "")
            
            # Extract entities and relations
            entities = self._extract_entities(chunk_text, chunk_idx)
            relations = self._extract_relations(chunk_text, entities, chunk_idx)
            
            all_entities.extend(entities)
            all_relations.extend(relations)
            
        # Add entities as nodes
        for entity in all_entities:
            self._add_entity_node(graph, entity)
            
        # Add relations as edges
        for relation in all_relations:
            self._add_relation_edge(graph, relation)
            
        # Post-process graph
        self._post_process_graph(graph)
        
        logger.info(f"Graph built with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
        return graph
        
    def _extract_entities(self, text: str, chunk_idx: int) -> List[Dict[str, Any]]:
        """Extract entities from text using NER"""
        entities = []
        
        # Process text with spaCy
        doc = self.nlp(text)
        
        # Extract named entities
        for ent in doc.ents:
            if len(ent.text) >= self.min_entity_length:
                entities.append({
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "chunk_idx": chunk_idx
                })
                
        # Extract noun phrases as potential entities
        for chunk in doc.noun_chunks:
            if len(chunk.text) >= self.min_entity_length:
                # Check if not already captured as named entity
                is_duplicate = any(
                    chunk.start_char >= e["start"] and chunk.end_char <= e["end"]
                    for e in entities
                )
                
                if not is_duplicate:
                    entities.append({
                        "text": chunk.text,
                        "label": "NOUN_PHRASE",
                        "start": chunk.start_char,
                        "end": chunk.end_char,
                        "chunk_idx": chunk_idx
                    })
                    
        # Limit entities per chunk
        if len(entities) > self.max_entities_per_chunk:
            # Prioritize named entities over noun phrases
            named_entities = [e for e in entities if e["label"] != "NOUN_PHRASE"]
            noun_phrases = [e for e in entities if e["label"] == "NOUN_PHRASE"]
            
            entities = named_entities[:self.max_entities_per_chunk]
            remaining_slots = self.max_entities_per_chunk - len(entities)
            if remaining_slots > 0:
                entities.extend(noun_phrases[:remaining_slots])
                
        return entities
        
    def _extract_relations(
        self,
        text: str,
        entities: List[Dict[str, Any]],
        chunk_idx: int
    ) -> List[Dict[str, Any]]:
        """Extract relations between entities"""
        relations = []
        
        if len(entities) < 2:
            return relations
            
        # Use dependency parsing for relation extraction
        doc = self.nlp(text)
        
        # Extract relations based on dependency patterns
        for token in doc:
            if token.dep_ in ["nsubj", "dobj", "pobj", "prep"]:
                # Find connected entities
                subject_entity = self._find_entity_for_token(token, entities)
                if token.head:
                    object_entity = self._find_entity_for_token(token.head, entities)
                    
                    if subject_entity and object_entity and subject_entity != object_entity:
                        relations.append({
                            "source": subject_entity["text"],
                            "target": object_entity["text"],
                            "relation": token.dep_,
                            "verb": token.head.text if token.head.pos_ == "VERB" else None,
                            "chunk_idx": chunk_idx,
                            "confidence": 0.8  # Basic confidence score
                        })
                        
        # Use LLM for more sophisticated relation extraction if enabled
        if self.config.get("use_llm_for_relations", False) and len(entities) <= 10:
            llm_relations = self._extract_relations_with_llm(text, entities)
            relations.extend(llm_relations)
            
        # Filter by confidence threshold
        relations = [
            r for r in relations
            if r.get("confidence", 0) >= self.min_relation_confidence
        ]
        
        return relations
        
    def _find_entity_for_token(
        self,
        token,
        entities: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find entity that contains the token"""
        token_start = token.idx
        token_end = token.idx + len(token.text)
        
        for entity in entities:
            if token_start >= entity["start"] and token_end <= entity["end"]:
                return entity
                
        return None
        
    async def _extract_relations_with_llm(
        self,
        text: str,
        entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Use LLM to extract relations between entities"""
        # Prepare prompt
        entity_list = [e["text"] for e in entities]
        prompt = f"""Extract relationships between the following entities from the text:

Entities: {', '.join(entity_list)}

Text: {text}

Return relationships in the format:
- [Entity1] -> [relationship] -> [Entity2]

Only include clear, factual relationships present in the text."""

        try:
            # Generate response
            response = await self.llm_generator.generate(
                query=prompt,
                context_chunks=[],
                max_tokens=500,
                temperature=0.3
            )
            
            # Parse response
            relations = []
            lines = response["text"].split("\n")
            
            for line in lines:
                # Parse relation format: Entity1 -> relationship -> Entity2
                match = re.match(r".*\[(.*?)\].*->\s*\[(.*?)\].*->\s*\[(.*?)\]", line)
                if match:
                    source, relation_type, target = match.groups()
                    
                    # Verify entities exist
                    if any(e["text"] == source for e in entities) and \
                       any(e["text"] == target for e in entities):
                        relations.append({
                            "source": source,
                            "target": target,
                            "relation": relation_type,
                            "confidence": 0.9,  # Higher confidence for LLM extraction
                            "method": "llm"
                        })
                        
            return relations
            
        except Exception as e:
            logger.error(f"LLM relation extraction failed: {e}")
            return []
            
    def _add_entity_node(self, graph: nx.Graph, entity: Dict[str, Any]):
        """Add entity as node to graph"""
        node_id = entity["text"]
        
        # Check if node already exists
        if graph.has_node(node_id):
            # Update node attributes
            graph.nodes[node_id]["occurrences"].append(entity["chunk_idx"])
            graph.nodes[node_id]["count"] += 1
        else:
            # Add new node
            graph.add_node(
                node_id,
                label=entity["label"],
                occurrences=[entity["chunk_idx"]],
                count=1,
                node_type="entity"
            )
            
    def _add_relation_edge(self, graph: nx.Graph, relation: Dict[str, Any]):
        """Add relation as edge to graph"""
        source = relation["source"]
        target = relation["target"]
        
        # Ensure nodes exist
        if not graph.has_node(source):
            graph.add_node(source, node_type="entity", label="UNKNOWN", count=0)
        if not graph.has_node(target):
            graph.add_node(target, node_type="entity", label="UNKNOWN", count=0)
            
        # Add or update edge
        if graph.has_edge(source, target):
            # Update existing edge
            graph[source][target]["count"] += 1
            graph[source][target]["relations"].append(relation["relation"])
            graph[source][target]["confidence"] = max(
                graph[source][target]["confidence"],
                relation.get("confidence", 0.5)
            )
        else:
            # Add new edge
            graph.add_edge(
                source,
                target,
                relation_type=relation["relation"],
                relations=[relation["relation"]],
                count=1,
                confidence=relation.get("confidence", 0.5),
                verb=relation.get("verb"),
                chunk_indices=[relation.get("chunk_idx")]
            )
            
    def _post_process_graph(self, graph: nx.Graph):
        """Post-process graph to improve quality"""
        # Remove isolated nodes (no connections)
        if self.config.get("remove_isolated_nodes", True):
            isolated_nodes = list(nx.isolates(graph))
            graph.remove_nodes_from(isolated_nodes)
            logger.info(f"Removed {len(isolated_nodes)} isolated nodes")
            
        # Merge similar entities
        if self.config.get("merge_similar_entities", True):
            self._merge_similar_entities(graph)
            
        # Calculate node importance scores
        self._calculate_node_importance(graph)
        
    def _merge_similar_entities(self, graph: nx.Graph):
        """Merge entities with similar names"""
        # Group nodes by lowercase text
        node_groups = {}
        for node in graph.nodes():
            key = node.lower().strip()
            if key not in node_groups:
                node_groups[key] = []
            node_groups[key].append(node)
            
        # Merge groups with multiple variants
        for key, nodes in node_groups.items():
            if len(nodes) > 1:
                # Keep the most frequent variant
                primary_node = max(nodes, key=lambda n: graph.nodes[n].get("count", 0))
                
                # Merge others into primary
                for node in nodes:
                    if node != primary_node:
                        # Transfer edges
                        for neighbor in list(graph.neighbors(node)):
                            if not graph.has_edge(primary_node, neighbor):
                                graph.add_edge(
                                    primary_node,
                                    neighbor,
                                    **graph[node][neighbor]
                                )
                                
                        # Remove merged node
                        graph.remove_node(node)
                        
    def _calculate_node_importance(self, graph: nx.Graph):
        """Calculate importance scores for nodes"""
        # Use PageRank for importance
        try:
            pagerank_scores = nx.pagerank(graph)
            for node, score in pagerank_scores.items():
                graph.nodes[node]["importance"] = score
        except:
            # Fallback to degree centrality
            for node in graph.nodes():
                graph.nodes[node]["importance"] = graph.degree(node) / max(1, graph.number_of_nodes())