"""Health check endpoints"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends
from loguru import logger

from ..config import settings
from ..retrieval.vector_store import VectorStoreManager

router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
        "environment": settings.environment
    }


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check for all services"""
    checks = {
        "api": True,
        "vector_db": False,
        "redis": False,
        "postgres": False,
        "llm": False
    }
    
    # Check vector database
    try:
        vector_store = VectorStoreManager()
        info = await vector_store.get_collection_info()
        checks["vector_db"] = info["status"] == "green"
    except Exception as e:
        logger.error(f"Vector DB check failed: {e}")
        
    # Check Redis
    try:
        import redis
        r = redis.from_url(settings.redis_url)
        r.ping()
        checks["redis"] = True
    except Exception as e:
        logger.error(f"Redis check failed: {e}")
        
    # Check PostgreSQL
    try:
        import psycopg2
        conn = psycopg2.connect(settings.get_database_url())
        conn.close()
        checks["postgres"] = True
    except Exception as e:
        logger.error(f"PostgreSQL check failed: {e}")
        
    # Check LLM endpoint
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.vllm_endpoint}/health")
            checks["llm"] = response.status_code == 200
    except Exception as e:
        logger.error(f"LLM check failed: {e}")
        
    # Overall status
    all_healthy = all(checks.values())
    
    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    """Liveness check for Kubernetes"""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }