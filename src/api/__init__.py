"""API routes for Enterprise RAG System"""

from .auth import router as auth_router
from .health import router as health_router
from .ingestion import router as ingestion_router
from .search import router as search_router

__all__ = [
    "auth_router",
    "health_router",
    "ingestion_router",
    "search_router",
]