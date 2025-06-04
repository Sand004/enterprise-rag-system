# Enterprise RAG System API Documentation

## Overview

The Enterprise RAG System provides a comprehensive REST API for document management, search, and AI-powered responses.

## Base URL

```
https://api.your-domain.com/v1
```

## Authentication

All API requests require authentication using either:
- JWT Bearer tokens
- API keys

### Bearer Token

```http
Authorization: Bearer <your-jwt-token>
```

### API Key

```http
X-API-Key: <your-api-key>
```

## Endpoints

### Authentication

#### POST /auth/login

Authenticate user and receive access token.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 86400,
  "refresh_token": "string"
}
```

#### POST /auth/refresh

Refresh access token.

**Headers:**
```
Authorization: Bearer <refresh-token>
```

**Response:**
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Document Management

#### POST /ingestion/upload

Upload and process a document.

**Request:**
- Method: POST
- Content-Type: multipart/form-data

**Form Data:**
- `file`: Document file (PDF, DOCX)
- `metadata`: JSON string with document metadata (optional)

**Example:**
```bash
curl -X POST \
  https://api.your-domain.com/v1/ingestion/upload \
  -H 'Authorization: Bearer <token>' \
  -F 'file=@document.pdf' \
  -F 'metadata={"title":"Q4 Report","tags":["finance","quarterly"]}'
```

**Response:**
```json
{
  "document_id": "doc_123abc",
  "status": "processing",
  "chunks_created": 42,
  "processing_time": 3.14,
  "message": "Document processed successfully"
}
```

#### GET /ingestion/status/{document_id}

Get document processing status.

**Response:**
```json
{
  "document_id": "doc_123abc",
  "status": "completed",
  "processed_at": "2024-01-15T10:30:00Z",
  "chunks_count": 42,
  "error": null
}
```

#### DELETE /ingestion/document/{document_id}

Delete a document and all associated data.

**Response:**
```json
{
  "message": "Document deleted successfully",
  "chunks_deleted": "42"
}
```

### Search

#### POST /search/search

Search for relevant documents.

**Request Body:**
```json
{
  "query": "string",
  "top_k": 10,
  "filters": {
    "department": "engineering",
    "created_after": "2024-01-01"
  },
  "search_type": "hybrid",
  "include_metadata": true,
  "rerank": true
}
```

**Response:**
```json
{
  "query": "RAG implementation best practices",
  "results": [
    {
      "document_id": "doc_123abc",
      "chunk_id": "chunk_456def",
      "content": "RAG systems combine retrieval and generation...",
      "score": 0.95,
      "metadata": {
        "title": "AI Architecture Guide",
        "page": 15,
        "author": "John Doe"
      },
      "highlights": [
        "<em>RAG systems</em> combine retrieval and generation"
      ]
    }
  ],
  "total_results": 10,
  "search_time_ms": 125.4,
  "search_type": "hybrid"
}
```

#### POST /search/generate

Generate AI response with retrieved context.

**Request Body:**
```json
{
  "query": "How do I implement semantic chunking?",
  "context_ids": ["chunk_123", "chunk_456"],
  "max_tokens": 1024,
  "temperature": 0.7,
  "system_prompt": "You are a helpful technical assistant."
}
```

**Response:**
```json
{
  "query": "How do I implement semantic chunking?",
  "response": "To implement semantic chunking, follow these steps...\n\n1. First, split your text into sentences...\n\n2. Generate embeddings for each sentence...\n\n3. Calculate semantic similarity between adjacent sentences...",
  "sources": [
    {
      "document_id": "doc_123abc",
      "title": "NLP Best Practices",
      "chunk_index": 5
    }
  ],
  "generation_time_ms": 2341.5,
  "tokens_used": 256
}
```

### Integrations

#### GET /integrations/atlassian/sync

Trigger Atlassian content synchronization.

**Query Parameters:**
- `service`: `confluence` | `jira` | `both`
- `space_key`: Confluence space key (optional)
- `project_key`: Jira project key (optional)

**Response:**
```json
{
  "status": "started",
  "sync_id": "sync_789ghi",
  "estimated_items": 150
}
```

### Health & Monitoring

#### GET /health

Basic health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "0.1.0",
  "environment": "production"
}
```

#### GET /health/ready

Detailed readiness check.

**Response:**
```json
{
  "status": "ready",
  "checks": {
    "api": true,
    "vector_db": true,
    "redis": true,
    "postgres": true,
    "llm": true
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Error Responses

All errors follow a consistent format:

```json
{
  "error": "Error message",
  "status_code": 400,
  "path": "/api/v1/search/search",
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123abc"
}
```

### Common Error Codes

- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Too Many Requests
- `500` - Internal Server Error

## Rate Limiting

API requests are rate limited based on your plan:

- **Free**: 60 requests/minute
- **Pro**: 300 requests/minute
- **Enterprise**: Custom limits

Rate limit information is included in response headers:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1642252800
```

## Pagination

List endpoints support pagination:

```
GET /api/v1/documents?limit=20&offset=40
```

Response includes pagination metadata:

```json
{
  "data": [...],
  "pagination": {
    "total": 150,
    "limit": 20,
    "offset": 40,
    "has_next": true,
    "has_prev": true
  }
}
```

## Webhooks

Configure webhooks to receive real-time updates:

```json
{
  "url": "https://your-app.com/webhooks/rag",
  "events": [
    "document.processed",
    "document.failed",
    "search.executed"
  ],
  "secret": "webhook_secret_key"
}
```

## SDKs

Official SDKs available for:
- Python
- JavaScript/TypeScript
- Go
- Java

Example (Python):

```python
from enterprise_rag import RAGClient

client = RAGClient(
    api_key="your-api-key",
    base_url="https://api.your-domain.com/v1"
)

# Upload document
result = client.documents.upload(
    file="report.pdf",
    metadata={"department": "sales"}
)

# Search
results = client.search.query(
    "Q4 sales performance",
    top_k=5
)

# Generate response
response = client.generate.create(
    query="Summarize Q4 performance",
    context_ids=[r.chunk_id for r in results]
)
```