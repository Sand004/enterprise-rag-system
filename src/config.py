"""Configuration Management for Enterprise RAG System"""

import os
from typing import Any, Dict, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # General Settings
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API Configuration
    api_port: int = Field(default=8080, env="API_PORT")
    worker_count: int = Field(default=4, env="WORKER_COUNT")
    request_timeout: int = Field(default=300, env="REQUEST_TIMEOUT_SECONDS")
    max_concurrent_requests: int = Field(default=100, env="MAX_CONCURRENT_REQUESTS")
    
    # API Keys
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    cohere_api_key: Optional[str] = Field(default=None, env="COHERE_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    
    # Atlassian Integration
    atlassian_base_url: Optional[str] = Field(default=None, env="ATLASSIAN_BASE_URL")
    atlassian_email: Optional[str] = Field(default=None, env="ATLASSIAN_EMAIL")
    atlassian_api_token: Optional[str] = Field(default=None, env="ATLASSIAN_API_TOKEN")
    
    # Vector Database
    vector_db_type: str = Field(default="qdrant", env="VECTOR_DB_TYPE")
    qdrant_url: str = Field(default="http://localhost:6333", env="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(default=None, env="QDRANT_API_KEY")
    
    # PostgreSQL (for pgvector)
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(default="rag_vectors", env="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", env="POSTGRES_USER")
    postgres_password: Optional[str] = Field(default=None, env="POSTGRES_PASSWORD")
    
    # Redis Cache
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    
    # LLM Configuration
    llm_provider: str = Field(default="vllm", env="LLM_PROVIDER")
    vllm_endpoint: str = Field(default="http://localhost:8000", env="VLLM_ENDPOINT")
    vllm_model: str = Field(
        default="meta-llama/Llama-3.3-70B-Instruct",
        env="VLLM_MODEL"
    )
    vllm_quantization: str = Field(default="awq", env="VLLM_QUANTIZATION")
    
    # Security
    master_key: Optional[str] = Field(default=None, env="MASTER_KEY")
    jwt_secret: Optional[str] = Field(default=None, env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # Storage
    s3_endpoint: str = Field(default="http://localhost:9000", env="S3_ENDPOINT")
    s3_access_key: str = Field(default="minioadmin", env="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="minioadmin", env="S3_SECRET_KEY")
    s3_bucket_name: str = Field(default="rag-documents", env="S3_BUCKET_NAME")
    
    # Document Processing
    max_chunk_size: int = Field(default=1024, env="MAX_CHUNK_SIZE")
    chunk_overlap: int = Field(default=256, env="CHUNK_OVERLAP")
    embedding_model: str = Field(
        default="text-embedding-3-large",
        env="EMBEDDING_MODEL"
    )
    embedding_dimension: int = Field(default=3072, env="EMBEDDING_DIMENSION")
    
    # Feature Flags
    enable_graphrag: bool = Field(default=True, env="ENABLE_GRAPHRAG")
    enable_multi_agent: bool = Field(default=True, env="ENABLE_MULTI_AGENT")
    enable_caching: bool = Field(default=True, env="ENABLE_CACHING")
    enable_audit_logging: bool = Field(default=True, env="ENABLE_AUDIT_LOGGING")
    enable_encryption: bool = Field(default=True, env="ENABLE_ENCRYPTION")
    
    # Search Configuration
    vector_search_top_k: int = Field(default=10, env="VECTOR_SEARCH_TOP_K")
    reranking_top_k: int = Field(default=5, env="RERANKING_TOP_K")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        
    @validator("master_key")
    def validate_master_key(cls, v):
        if v and len(v) != 32:
            raise ValueError("Master key must be exactly 32 characters")
        return v
        
    @validator("environment")
    def validate_environment(cls, v):
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v
        
    def get_database_url(self) -> str:
        """Get PostgreSQL database URL"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
        
    def get_vector_db_config(self) -> Dict[str, Any]:
        """Get vector database configuration"""
        if self.vector_db_type == "qdrant":
            return {
                "type": "qdrant",
                "url": self.qdrant_url,
                "api_key": self.qdrant_api_key,
                "collection_name": "enterprise_docs"
            }
        elif self.vector_db_type == "pgvector":
            return {
                "type": "pgvector",
                "connection_string": self.get_database_url(),
                "table_name": "document_vectors"
            }
        else:
            raise ValueError(f"Unknown vector DB type: {self.vector_db_type}")
            
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration"""
        if self.llm_provider == "vllm":
            return {
                "provider": "vllm",
                "endpoint": self.vllm_endpoint,
                "model": self.vllm_model,
                "quantization": self.vllm_quantization,
                "max_tokens": 4096,
                "temperature": 0.7
            }
        elif self.llm_provider == "openai":
            return {
                "provider": "openai",
                "api_key": self.openai_api_key,
                "model": "gpt-4-turbo-preview",
                "max_tokens": 4096,
                "temperature": 0.7
            }
        else:
            raise ValueError(f"Unknown LLM provider: {self.llm_provider}")


# Global settings instance
settings = Settings()