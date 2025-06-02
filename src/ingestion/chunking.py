"""Semantic Chunking Implementation"""

import re
from typing import Dict, List, Optional, Tuple

import numpy as np
from loguru import logger
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from .base import DocumentChunk


class SemanticChunker:
    """Advanced semantic chunking with sentence embeddings"""
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        max_chunk_size: int = 1024,
        min_chunk_size: int = 256,
        chunk_overlap: int = 256,
        similarity_threshold: float = 0.7
    ):
        self.model = SentenceTransformer(model_name)
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.chunk_overlap = chunk_overlap
        self.similarity_threshold = similarity_threshold
        
    def chunk_document(
        self,
        doc_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Create semantic chunks from document content"""
        logger.info(f"Starting semantic chunking for document {doc_id}")
        
        # Split into sentences
        sentences = self._split_into_sentences(content)
        
        if not sentences:
            return []
            
        # Generate embeddings for all sentences
        embeddings = self.model.encode(sentences)
        
        # Create semantic chunks
        chunks = self._create_semantic_chunks(
            doc_id,
            sentences,
            embeddings,
            metadata
        )
        
        logger.info(f"Created {len(chunks)} semantic chunks")
        return chunks
        
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Enhanced sentence splitting
        # Handle abbreviations, decimals, etc.
        sentence_endings = re.compile(
            r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s+(?=[A-Z])'
        )
        
        sentences = sentence_endings.split(text)
        
        # Clean and filter sentences
        cleaned_sentences = []
        for sent in sentences:
            sent = sent.strip()
            if len(sent) > 10:  # Minimum sentence length
                cleaned_sentences.append(sent)
                
        return cleaned_sentences
        
    def _create_semantic_chunks(
        self,
        doc_id: str,
        sentences: List[str],
        embeddings: np.ndarray,
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Create chunks based on semantic similarity"""
        chunks = []
        current_chunk_sentences = [sentences[0]]
        current_chunk_embeddings = [embeddings[0]]
        char_position = 0
        
        for i in range(1, len(sentences)):
            # Calculate similarity with current chunk
            chunk_embedding = np.mean(current_chunk_embeddings, axis=0)
            similarity = cosine_similarity(
                [chunk_embedding],
                [embeddings[i]]
            )[0][0]
            
            # Check if we should start a new chunk
            current_chunk_text = " ".join(current_chunk_sentences)
            current_length = len(current_chunk_text)
            
            should_split = (
                similarity < self.similarity_threshold or
                current_length > self.max_chunk_size or
                (current_length > self.min_chunk_size and 
                 current_length + len(sentences[i]) > self.max_chunk_size)
            )
            
            if should_split:
                # Create chunk
                chunk = self._create_chunk(
                    doc_id,
                    current_chunk_text,
                    char_position,
                    char_position + current_length,
                    len(chunks),
                    metadata,
                    np.mean(current_chunk_embeddings, axis=0)
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk_sentences,
                    self.chunk_overlap
                )
                
                current_chunk_sentences = overlap_sentences + [sentences[i]]
                
                # Update embeddings
                overlap_count = len(overlap_sentences)
                if overlap_count > 0:
                    overlap_embeddings = current_chunk_embeddings[-overlap_count:]
                    current_chunk_embeddings = overlap_embeddings + [embeddings[i]]
                else:
                    current_chunk_embeddings = [embeddings[i]]
                    
                char_position += current_length - len(" ".join(overlap_sentences))
            else:
                # Add to current chunk
                current_chunk_sentences.append(sentences[i])
                current_chunk_embeddings.append(embeddings[i])
                
        # Create final chunk
        if current_chunk_sentences:
            final_chunk_text = " ".join(current_chunk_sentences)
            chunk = self._create_chunk(
                doc_id,
                final_chunk_text,
                char_position,
                char_position + len(final_chunk_text),
                len(chunks),
                metadata,
                np.mean(current_chunk_embeddings, axis=0)
            )
            chunks.append(chunk)
            
        # Update total chunks in metadata
        for chunk in chunks:
            chunk.metadata["total_chunks"] = len(chunks)
            
        return chunks
        
    def _get_overlap_sentences(
        self,
        sentences: List[str],
        target_overlap: int
    ) -> List[str]:
        """Get sentences for chunk overlap"""
        overlap_sentences = []
        overlap_length = 0
        
        for sent in reversed(sentences):
            overlap_length += len(sent)
            overlap_sentences.insert(0, sent)
            
            if overlap_length >= target_overlap:
                break
                
        return overlap_sentences
        
    def _create_chunk(
        self,
        doc_id: str,
        content: str,
        start_char: int,
        end_char: int,
        chunk_index: int,
        metadata: Dict[str, Any],
        embedding: Optional[np.ndarray] = None
    ) -> DocumentChunk:
        """Create a document chunk"""
        chunk_id = f"{doc_id}_chunk_{chunk_index}"
        
        chunk_metadata = {
            **metadata,
            "chunk_index": chunk_index,
            "chunk_method": "semantic",
            "chunk_size": len(content)
        }
        
        return DocumentChunk(
            id=chunk_id,
            document_id=doc_id,
            content=content,
            embedding=embedding.tolist() if embedding is not None else None,
            metadata=chunk_metadata,
            start_char=start_char,
            end_char=end_char,
            chunk_index=chunk_index
        )