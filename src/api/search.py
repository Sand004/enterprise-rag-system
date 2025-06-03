"""Search API endpoints"""

from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field

from ..api.auth import get_current_user, UserInfo
from ..generation import LLMGenerator
from ..retrieval import HybridSearch
from ..utils.embeddings import EmbeddingManager

router = APIRouter()


class SearchRequest(BaseModel):
    """Search request model"""
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=10, ge=1, le=100)
    filters: Optional[Dict[str, Any]] = None
    search_type: str = Field(default="hybrid", pattern="^(vector|keyword|hybrid)$")
    include_metadata: bool = True
    rerank: bool = True


class SearchResult(BaseModel):
    """Individual search result"""
    document_id: str
    chunk_id: str
    content: str
    score: float
    metadata: Optional[Dict[str, Any]] = None
    highlights: Optional[List[str]] = None


class SearchResponse(BaseModel):
    """Search response model"""
    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: float
    search_type: str


class GenerateRequest(BaseModel):
    """Generation request model"""
    query: str = Field(..., min_length=1, max_length=1000)
    context_ids: Optional[List[str]] = None
    max_tokens: int = Field(default=1024, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0, le=2)
    system_prompt: Optional[str] = None


class GenerateResponse(BaseModel):
    """Generation response model"""
    query: str
    response: str
    sources: List[Dict[str, Any]]
    generation_time_ms: float
    tokens_used: int


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    current_user: UserInfo = Depends(get_current_user)
) -> SearchResponse:
    """Search for documents"""
    import time
    start_time = time.time()
    
    try:
        # Add user context to filters
        if request.filters is None:
            request.filters = {}
            
        # Add access control filters based on user permissions
        if "documents:admin" not in current_user.permissions:
            request.filters["uploaded_by"] = current_user.id
            
        # Initialize search
        hybrid_search = HybridSearch()
        
        # Perform search
        results = await hybrid_search.search(
            query=request.query,
            filters=request.filters,
            top_k=request.top_k,
            search_type=request.search_type,
            rerank=request.rerank
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append(
                SearchResult(
                    document_id=result["payload"]["document_id"],
                    chunk_id=result["id"],
                    content=result["payload"]["content"],
                    score=result["score"],
                    metadata=result["payload"]["metadata"] if request.include_metadata else None,
                    highlights=result.get("highlights")
                )
            )
            
        # Calculate search time
        search_time_ms = (time.time() - start_time) * 1000
        
        return SearchResponse(
            query=request.query,
            results=formatted_results,
            total_results=len(formatted_results),
            search_time_ms=search_time_ms,
            search_type=request.search_type
        )
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/generate", response_model=GenerateResponse)
async def generate_response(
    request: GenerateRequest,
    current_user: UserInfo = Depends(get_current_user)
) -> GenerateResponse:
    """Generate response using RAG"""
    import time
    start_time = time.time()
    
    try:
        # First, search for relevant context
        hybrid_search = HybridSearch()
        
        if request.context_ids:
            # Use provided context IDs
            # TODO: Fetch specific chunks by IDs
            context_chunks = []
        else:
            # Search for context
            search_results = await hybrid_search.search(
                query=request.query,
                filters={"uploaded_by": current_user.id},
                top_k=5,
                rerank=True
            )
            
            context_chunks = [
                {
                    "content": result["payload"]["content"],
                    "metadata": result["payload"]["metadata"]
                }
                for result in search_results
            ]
            
        # Generate response
        llm_generator = LLMGenerator()
        
        response = await llm_generator.generate(
            query=request.query,
            context_chunks=context_chunks,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system_prompt=request.system_prompt
        )
        
        # Extract sources
        sources = [
            {
                "document_id": chunk["metadata"].get("document_id"),
                "title": chunk["metadata"].get("title", "Untitled"),
                "chunk_index": chunk["metadata"].get("chunk_index")
            }
            for chunk in context_chunks
        ]
        
        # Calculate generation time
        generation_time_ms = (time.time() - start_time) * 1000
        
        return GenerateResponse(
            query=request.query,
            response=response["text"],
            sources=sources,
            generation_time_ms=generation_time_ms,
            tokens_used=response["tokens_used"]
        )
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {str(e)}"
        )


@router.get("/suggest")
async def suggest_queries(
    query: str = Query(..., min_length=3),
    limit: int = Query(default=5, ge=1, le=20),
    current_user: UserInfo = Depends(get_current_user)
) -> Dict[str, Any]:
    """Suggest related queries"""
    # TODO: Implement query suggestion using embeddings or LLM
    suggestions = [
        f"{query} best practices",
        f"{query} implementation guide",
        f"{query} troubleshooting",
        f"how to {query}",
        f"{query} examples"
    ]
    
    return {
        "query": query,
        "suggestions": suggestions[:limit]
    }