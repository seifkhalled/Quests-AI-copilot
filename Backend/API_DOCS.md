# Quest Copilot API Documentation

Base URL: `http://localhost:8000`

---

## Authentication

All protected endpoints require Bearer token in header:
```
Authorization: Bearer <token>
```

Get token via `/api/auth/login` or `/api/auth/register`.

---

## Auth Endpoints

### Register User
```
POST /api/auth/register
```

**Body:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "full_name": "John Doe",
  "role": "user"
}
```

**Response:**
```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "user",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

---

### Login User
```
POST /api/auth/login
```

**Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:** Same as register.

---

### Get Current User
```
GET /api/auth/me
```

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### Logout
```
POST /api/auth/logout
```

**Response:** `{"message": "Logged out successfully"}`

---

### Create Admin User
```
POST /api/auth/create-admin?email=admin@example.com&password=admin123&full_name=Admin
```

**Note:** Requires `ADMIN_CREATE_SECRET` in `.env`

---

## Document Endpoints

### List Documents
```
GET /api/documents?skip=0&limit=50&status=completed
```

**Query Params:**
- `skip` (int, default 0)
- `limit` (int, default 50)
- `status` (str, optional: pending, processing, completed, failed)

**Response:**
```json
[
  {
    "id": "uuid",
    "title": "Document Title",
    "source_type": "pdf",
    "original_filename": "file.pdf",
    "mime_type": "application/pdf",
    "file_size_bytes": 1024,
    "status": "completed",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

### Get Document
```
GET /api/documents/{doc_id}
```

**Response:** Single document object.

---

### Get Document Chunks
```
GET /api/documents/{doc_id}/chunks
```

**Response:**
```json
[
  {
    "id": "uuid",
    "chunk_index": 0,
    "content": "Chunk text...",
    "token_count": 100,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

### Get Document Content
```
GET /api/documents/{doc_id}/content
```

**Response:**
```json
{
  "content": "Full raw document text..."
}
```

---

### Delete Document
```
DELETE /api/documents/{doc_id}
```

**Response:** `{"deleted": "uuid"}`

---

## Ingestion Endpoints

### Upload File
```
POST /api/ingest/file
```

**Content-Type:** `multipart/form-data`

**Form Data:**
- `file`: File (PDF, TXT, MD)

**Response:**
```json
{
  "document_id": "uuid",
  "title": "filename",
  "chunks_created": 10,
  "status": "completed"
}
```

---

### Ingest Source
```
POST /api/ingest/source
```

**Body:**
```json
{
  "source_type": "notion",
  "content": "Raw text content...",
  "title": "My Notion Page",
  "metadata": {"key": "value"}
}
```

**Response:** Same as file upload.

---

### Ingestion Health
```
GET /api/ingest/health
```

**Response:** `{"status": "healthy"}`

---

## AI Endpoints

### Query Knowledge Base
```
POST /api/ai/query
```

**Body:**
```json
{
  "question": "What is in my documents?",
  "document_id": "optional-uuid",
  "top_k": 5,
  "model": "meta-llama/llama-4-scout-17b-16e-instruct"
}
```

**Response:**
```json
{
  "answer": "Based on your documents...",
  "sources": [
    {
      "title": "Document Title",
      "content": "Relevant chunk...",
      "score": 0.95
    }
  ],
  "confidence": 0.85,
  "model": "meta-llama/llama-4-scout-17b-16e-instruct"
}
```

---

### Get Insights
```
GET /api/ai/insights
```

**Response:**
```json
{
  "insights": [
    {
      "type": "pattern",
      "title": "Insight Title",
      "description": "Insight description"
    }
  ]
}
```

---

### AI Health
```
GET /api/ai/health
```

**Response:** `{"status": "healthy"}`

---

## Health Check

### Root
```
GET /
```

**Response:** `{"message": "AI Knowledge Operations System API"}`

---

### API Health
```
GET /api/health
```

**Response:** `{"status": "healthy", "version": "1.0.0"}`

---

## Example Usage

### 1. Register/Login
```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123", "full_name": "Admin"}'

# Login (get token)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}'
```

### 2. Upload Document
```bash
curl -X POST http://localhost:8000/api/ingest/file \
  -F "file=@document.pdf"
```

### 3. Query AI
```bash
curl -X POST http://localhost:8000/api/ai/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Summarize my documents"}'
```

### 4. List Documents
```bash
curl http://localhost:8000/api/documents
```

---

## Error Responses

```json
{
  "detail": "Error message"
}
```

Common status codes:
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error