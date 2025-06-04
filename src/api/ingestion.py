"""Document ingestion API endpoints"""

import os
import tempfile
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from loguru import logger
from pydantic import BaseModel

from ..api.auth import get_current_user, UserInfo
from ..ingestion import PDFProcessor, DOCXProcessor
from ..ingestion.chunking import SemanticChunker
from ..retrieval.vector_store import VectorStoreManager
from ..utils.embeddings import EmbeddingManager

router = APIRouter()


class DocumentMetadata(BaseModel):
    """Document metadata model"""
    title: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[List[str]] = None
    department: Optional[str] = None
    access_level: Optional[str] = "private"


class IngestionResponse(BaseModel):
    """Ingestion response model"""
    document_id: str
    status: str
    chunks_created: int
    processing_time: float
    message: str


@router.post("/upload", response_model=IngestionResponse)
async def upload_document(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
    current_user: UserInfo = Depends(get_current_user)
) -> IngestionResponse:
    """Upload and process a document"""
    import time
    start_time = time.time()
    
    # Validate file type
    allowed_types = [".pdf", ".docx"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_ext} not supported. Allowed types: {allowed_types}"
        )
        
    # Parse metadata if provided
    doc_metadata = {}
    if metadata:
        try:
            import json
            doc_metadata = json.loads(metadata)
        except:
            logger.warning("Failed to parse metadata, using defaults")
            
    # Add user context
    doc_metadata.update({
        "uploaded_by": current_user.id,
        "upload_timestamp": time.time(),
        "original_filename": file.filename
    })
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
            
        # Select appropriate processor
        if file_ext == ".pdf":
            processor = PDFProcessor({"chunk_size": 1024, "chunk_overlap": 256})
        elif file_ext == ".docx":
            processor = DOCXProcessor({"chunk_size": 1024, "chunk_overlap": 256})
        else:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Processor for {file_ext} not yet implemented"
            )
            
        # Process document
        processed_doc = processor.process_document(
            tmp_file_path,
            user_context={"user_id": current_user.id}
        )
        
        # Apply semantic chunking
        chunker = SemanticChunker()
        semantic_chunks = chunker.chunk_document(
            processed_doc.id,
            processed_doc.content,
            doc_metadata
        )
        
        # Generate embeddings
        embedding_manager = EmbeddingManager()
        chunk_texts = [chunk.content for chunk in semantic_chunks]
        embeddings = await embedding_manager.generate_embeddings(chunk_texts)
        
        # Prepare vectors and payloads
        vectors = []
        payloads = []
        ids = []
        
        for i, (chunk, embedding) in enumerate(zip(semantic_chunks, embeddings)):
            vectors.append(embedding)
            ids.append(chunk.id)
            payloads.append({
                "document_id": processed_doc.id,
                "chunk_index": i,
                "content": chunk.content,
                "metadata": chunk.metadata,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char
            })
            
        # Store in vector database
        vector_store = VectorStoreManager()
        await vector_store.upsert_vectors(vectors, payloads, ids)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Clean up temporary file
        os.unlink(tmp_file_path)
        
        return IngestionResponse(
            document_id=processed_doc.id,
            status="success",
            chunks_created=len(semantic_chunks),
            processing_time=processing_time,
            message=f"Document processed successfully in {processing_time:.2f}s"
        )
        
    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        # Clean up on error
        if 'tmp_file_path' in locals():
            try:
                os.unlink(tmp_file_path)
            except:
                pass
                
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}"
        )


@router.get("/status/{document_id}")
async def get_ingestion_status(
    document_id: str,
    current_user: UserInfo = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get document ingestion status"""
    # TODO: Implement status tracking
    return {
        "document_id": document_id,
        "status": "completed",
        "message": "Document processing completed"
    }


@router.delete("/document/{document_id}")
async def delete_document(
    document_id: str,
    current_user: UserInfo = Depends(get_current_user)
) -> Dict[str, str]:
    """Delete a document and its chunks"""
    try:
        # Get all chunk IDs for the document
        vector_store = VectorStoreManager()
        
        # Search for all chunks of this document
        # This is a simplified approach - in production, maintain an index
        results = await vector_store.search(
            query_vector=[0] * 3072,  # Dummy vector
            top_k=10000,
            filters={"document_id": document_id}
        )
        
        # Extract chunk IDs
        chunk_ids = [result["id"] for result in results]
        
        if chunk_ids:
            # Delete all chunks
            await vector_store.delete_vectors(chunk_ids)
            logger.info(f"Deleted {len(chunk_ids)} chunks for document {document_id}")
            
        return {
            "message": f"Document {document_id} deleted successfully",
            "chunks_deleted": str(len(chunk_ids))
        }
        
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )


@router.get("/documents")
async def list_documents(
    limit: int = 50,
    offset: int = 0,
    current_user: UserInfo = Depends(get_current_user)
) -> Dict[str, Any]:
    """List user's documents"""
    # TODO: Implement document listing from metadata store
    return {
        "documents": [],
        "total": 0,
        "limit": limit,
        "offset": offset
    }