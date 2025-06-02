"""Base Document Processor with Enterprise Features"""

import hashlib
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger
from pydantic import BaseModel


class DocumentChunk(BaseModel):
    """Represents a processed document chunk"""
    id: str
    document_id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any]
    start_char: int
    end_char: int
    chunk_index: int
    

class ProcessedDocument(BaseModel):
    """Represents a fully processed document"""
    id: str
    source_path: str
    content: str
    chunks: List[DocumentChunk]
    metadata: Dict[str, Any]
    processing_timestamp: datetime
    checksum: str


class BaseDocumentProcessor(ABC):
    """Abstract base class for document processors"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.chunk_size = config.get("chunk_size", 1024)
        self.chunk_overlap = config.get("chunk_overlap", 256)
        
    @abstractmethod
    def extract_content(self, file_path: str) -> str:
        """Extract raw content from document"""
        pass
        
    @abstractmethod
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from document"""
        pass
        
    def process_document(
        self,
        file_path: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> ProcessedDocument:
        """Main processing pipeline"""
        logger.info(f"Processing document: {file_path}")
        
        # Extract content and metadata
        content = self.extract_content(file_path)
        metadata = self.extract_metadata(file_path)
        
        # Add user context to metadata
        if user_context:
            metadata["user_context"] = user_context
            
        # Generate document ID and checksum
        doc_id = self._generate_document_id(file_path)
        checksum = self._calculate_checksum(content)
        
        # Create chunks
        chunks = self._create_chunks(doc_id, content, metadata)
        
        # Build processed document
        processed_doc = ProcessedDocument(
            id=doc_id,
            source_path=file_path,
            content=content,
            chunks=chunks,
            metadata=metadata,
            processing_timestamp=datetime.utcnow(),
            checksum=checksum
        )
        
        logger.info(f"Document processed successfully: {doc_id}")
        return processed_doc
        
    def _generate_document_id(self, file_path: str) -> str:
        """Generate unique document ID"""
        timestamp = datetime.utcnow().isoformat()
        data = f"{file_path}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
        
    def _calculate_checksum(self, content: str) -> str:
        """Calculate content checksum for deduplication"""
        return hashlib.sha256(content.encode()).hexdigest()
        
    def _create_chunks(
        self,
        doc_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Create document chunks (basic implementation)"""
        chunks = []
        
        # Simple sliding window chunking (to be replaced with semantic chunking)
        for i in range(0, len(content), self.chunk_size - self.chunk_overlap):
            start = i
            end = min(i + self.chunk_size, len(content))
            
            chunk_text = content[start:end]
            chunk_id = f"{doc_id}_chunk_{len(chunks)}"
            
            chunk = DocumentChunk(
                id=chunk_id,
                document_id=doc_id,
                content=chunk_text,
                metadata={
                    **metadata,
                    "chunk_index": len(chunks),
                    "total_chunks": -1  # Will be updated after all chunks created
                },
                start_char=start,
                end_char=end,
                chunk_index=len(chunks)
            )
            
            chunks.append(chunk)
            
        # Update total chunks count
        for chunk in chunks:
            chunk.metadata["total_chunks"] = len(chunks)
            
        return chunks
        
    def validate_document(self, file_path: str) -> bool:
        """Validate document before processing"""
        # Override in subclasses for specific validation
        return True