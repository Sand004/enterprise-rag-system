"""Pytest configuration and fixtures"""

import asyncio
import os
import tempfile
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import Settings
from src.main import app


# Override settings for testing
@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Test settings with overrides"""
    return Settings(
        environment="testing",
        debug=True,
        log_level="DEBUG",
        # Use test database
        postgres_db="rag_test",
        # Disable external services
        enable_graphrag=False,
        enable_multi_agent=False,
        # Use smaller chunks for testing
        max_chunk_size=256,
        chunk_overlap=64
    )


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client(test_settings) -> Generator[TestClient, None, None]:
    """Create test client"""
    # Override settings
    os.environ["ENVIRONMENT"] = "testing"
    
    with TestClient(app) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def async_client(test_settings) -> AsyncGenerator[TestClient, None]:
    """Create async test client"""
    os.environ["ENVIRONMENT"] = "testing"
    
    async with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def temp_pdf_file() -> Generator[str, None, None]:
    """Create temporary PDF file for testing"""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        # Write minimal PDF content
        f.write(b"%PDF-1.4\n")
        f.write(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        f.write(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
        f.write(b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n")
        f.write(b"%%EOF")
        temp_path = f.name
        
    yield temp_path
    
    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def sample_document_content() -> str:
    """Sample document content for testing"""
    return """
    # Introduction to Enterprise RAG Systems
    
    A Retrieval-Augmented Generation (RAG) system combines the power of 
    large language models with the ability to retrieve relevant information 
    from a knowledge base. This approach significantly improves the accuracy 
    and relevance of generated responses.
    
    ## Key Components
    
    1. Document Processing: Ingests and processes various document formats
    2. Vector Database: Stores document embeddings for efficient retrieval
    3. LLM Integration: Generates responses based on retrieved context
    4. Security Layer: Ensures data protection and access control
    
    ## Benefits
    
    - Improved accuracy through grounding in factual data
    - Reduced hallucinations compared to pure LLM approaches
    - Ability to incorporate private or domain-specific knowledge
    - Cost-effective scaling through efficient retrieval
    
    This system is designed for enterprise use with features like:
    - Multi-tenancy support
    - Advanced security and encryption
    - Integration with popular enterprise tools
    - Comprehensive monitoring and analytics
    """


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "This is a mock response from the LLM."
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }


@pytest.fixture
def auth_headers() -> dict:
    """Authentication headers for testing"""
    return {
        "Authorization": "Bearer test-token-123",
        "X-API-Key": "test-api-key"
    }