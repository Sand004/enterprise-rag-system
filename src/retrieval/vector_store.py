"""Vector Store Manager for Enterprise RAG System"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union

import numpy as np
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    Range,
    SearchParams,
    VectorParams,
)

from ..config import settings


class VectorStoreManager:
    """Manage vector database operations"""
    
    def __init__(self):
        self.config = settings.get_vector_db_config()
        self.client = self._initialize_client()
        self.collection_name = self.config.get("collection_name", "enterprise_docs")
        
    def _initialize_client(self) -> QdrantClient:
        """Initialize vector database client"""
        if self.config["type"] == "qdrant":
            return QdrantClient(
                url=self.config["url"],
                api_key=self.config.get("api_key"),
                https=self.config.get("https", False)
            )
        else:
            raise ValueError(f"Unsupported vector DB type: {self.config['type']}")
            
    async def create_collection(self, collection_name: str, vector_size: int) -> None:
        """Create a new collection"""
        try:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                ),
                optimizers_config={
                    "indexing_threshold": 20000,
                    "memmap_threshold": 50000
                }
            )
            logger.info(f"Created collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise
            
    async def upsert_vectors(
        self,
        vectors: List[np.ndarray],
        payloads: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> None:
        """Insert or update vectors in the collection"""
        try:
            # Generate IDs if not provided
            if ids is None:
                ids = [str(i) for i in range(len(vectors))]
                
            # Convert numpy arrays to lists
            vector_lists = [v.tolist() if isinstance(v, np.ndarray) else v for v in vectors]
            
            # Create point structures
            points = [
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
                for point_id, vector, payload in zip(ids, vector_lists, payloads)
            ]
            
            # Batch upsert
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch
                )
                
            logger.info(f"Upserted {len(points)} vectors")
            
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            raise
            
    async def search(
        self,
        query_vector: Union[List[float], np.ndarray],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        try:
            # Convert numpy array to list if needed
            if isinstance(query_vector, np.ndarray):
                query_vector = query_vector.tolist()
                
            # Build filter conditions
            filter_conditions = None
            if filters:
                filter_conditions = self._build_filter_conditions(filters)
                
            # Perform search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=filter_conditions,
                score_threshold=score_threshold,
                search_params=SearchParams(
                    hnsw_ef=256,
                    exact=False
                )
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload
                })
                
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
            
    async def batch_search(
        self,
        query_vectors: List[Union[List[float], np.ndarray]],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[List[Dict[str, Any]]]:
        """Perform batch search for multiple queries"""
        try:
            # Convert numpy arrays to lists
            query_lists = [
                v.tolist() if isinstance(v, np.ndarray) else v
                for v in query_vectors
            ]
            
            # Build filter
            filter_conditions = None
            if filters:
                filter_conditions = self._build_filter_conditions(filters)
                
            # Perform batch search
            results = self.client.search_batch(
                collection_name=self.collection_name,
                requests=[
                    {
                        "vector": query,
                        "limit": top_k,
                        "filter": filter_conditions
                    }
                    for query in query_lists
                ]
            )
            
            # Format results
            formatted_results = []
            for batch_result in results:
                batch_formatted = []
                for result in batch_result:
                    batch_formatted.append({
                        "id": result.id,
                        "score": result.score,
                        "payload": result.payload
                    })
                formatted_results.append(batch_formatted)
                
            return formatted_results
            
        except Exception as e:
            logger.error(f"Batch search failed: {e}")
            raise
            
    def _build_filter_conditions(self, filters: Dict[str, Any]) -> Filter:
        """Build Qdrant filter conditions from dictionary"""
        conditions = []
        
        for field, value in filters.items():
            if isinstance(value, dict):
                # Range query
                if "gte" in value or "lte" in value:
                    conditions.append(
                        FieldCondition(
                            key=field,
                            range=Range(
                                gte=value.get("gte"),
                                lte=value.get("lte")
                            )
                        )
                    )
            else:
                # Exact match
                conditions.append(
                    FieldCondition(
                        key=field,
                        match=MatchValue(value=value)
                    )
                )
                
        return Filter(must=conditions)
        
    async def delete_vectors(self, ids: List[str]) -> None:
        """Delete vectors by IDs"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=ids
            )
            logger.info(f"Deleted {len(ids)} vectors")
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            raise
            
    async def update_payload(
        self,
        point_id: str,
        payload: Dict[str, Any]
    ) -> None:
        """Update payload for a specific vector"""
        try:
            self.client.set_payload(
                collection_name=self.collection_name,
                payload=payload,
                points=[point_id]
            )
            logger.info(f"Updated payload for point {point_id}")
        except Exception as e:
            logger.error(f"Failed to update payload: {e}")
            raise
            
    async def get_collection_info(self) -> Dict[str, Any]:
        """Get collection information"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "status": info.status,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "config": info.config.dict()
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise
            
    async def optimize_collection(self) -> None:
        """Optimize collection for better performance"""
        try:
            self.client.update_collection(
                collection_name=self.collection_name,
                optimizer_config={
                    "indexing_threshold": 20000,
                    "memmap_threshold": 50000
                }
            )
            logger.info("Collection optimization started")
        except Exception as e:
            logger.error(f"Failed to optimize collection: {e}")
            raise