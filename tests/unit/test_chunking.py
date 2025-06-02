"""Unit tests for semantic chunking"""

import numpy as np
import pytest

from src.ingestion.chunking import SemanticChunker


class TestSemanticChunker:
    """Test semantic chunking functionality"""
    
    @pytest.fixture
    def chunker(self):
        """Create semantic chunker instance"""
        return SemanticChunker(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            max_chunk_size=512,
            min_chunk_size=128,
            chunk_overlap=64,
            similarity_threshold=0.7
        )
        
    def test_sentence_splitting(self, chunker):
        """Test sentence splitting functionality"""
        text = (
            "This is the first sentence. "
            "This is the second sentence! "
            "And here's the third sentence? "
            "Finally, the fourth sentence."
        )
        
        sentences = chunker._split_into_sentences(text)
        
        assert len(sentences) == 4
        assert sentences[0] == "This is the first sentence."
        assert sentences[1] == "This is the second sentence!"
        assert sentences[2] == "And here's the third sentence?"
        assert sentences[3] == "Finally, the fourth sentence."
        
    def test_sentence_splitting_edge_cases(self, chunker):
        """Test sentence splitting with edge cases"""
        # Test with abbreviations
        text1 = "Dr. Smith went to the U.S.A. yesterday. He had a great time."
        sentences1 = chunker._split_into_sentences(text1)
        assert len(sentences1) == 2
        
        # Test with decimals
        text2 = "The price is $19.99 today. That's a 10.5% discount!"
        sentences2 = chunker._split_into_sentences(text2)
        assert len(sentences2) == 2
        
    def test_semantic_chunking(self, chunker, sample_document_content):
        """Test semantic chunking algorithm"""
        doc_id = "test_doc_456"
        metadata = {"source": "unit_test"}
        
        chunks = chunker.chunk_document(
            doc_id,
            sample_document_content,
            metadata
        )
        
        assert len(chunks) > 0
        assert all(chunk.document_id == doc_id for chunk in chunks)
        assert all(chunk.metadata["chunk_method"] == "semantic" for chunk in chunks)
        
        # Check chunk sizes
        for chunk in chunks:
            assert len(chunk.content) >= chunker.min_chunk_size
            assert len(chunk.content) <= chunker.max_chunk_size
            
        # Check embeddings
        for chunk in chunks:
            assert chunk.embedding is not None
            assert len(chunk.embedding) == 384  # MiniLM embedding size
            
    def test_overlap_calculation(self, chunker):
        """Test overlap sentence calculation"""
        sentences = [
            "First sentence.",
            "Second sentence.",
            "Third sentence.",
            "Fourth sentence."
        ]
        
        # Test with different overlap sizes
        overlap1 = chunker._get_overlap_sentences(sentences, 20)
        assert len(overlap1) >= 1
        
        overlap2 = chunker._get_overlap_sentences(sentences, 50)
        assert len(overlap2) >= 2
        
    def test_chunk_metadata(self, chunker):
        """Test chunk metadata generation"""
        doc_id = "test_doc_789"
        content = "This is a test chunk content."
        metadata = {"source": "test", "author": "tester"}
        
        chunk = chunker._create_chunk(
            doc_id,
            content,
            0,
            len(content),
            0,
            metadata,
            np.random.rand(384)  # Mock embedding
        )
        
        assert chunk.id == f"{doc_id}_chunk_0"
        assert chunk.document_id == doc_id
        assert chunk.content == content
        assert chunk.start_char == 0
        assert chunk.end_char == len(content)
        assert chunk.chunk_index == 0
        assert chunk.metadata["source"] == "test"
        assert chunk.metadata["author"] == "tester"
        assert chunk.metadata["chunk_method"] == "semantic"
        assert chunk.metadata["chunk_size"] == len(content)