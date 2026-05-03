# Quest Copilot Backend

FastAPI-based backend for AI Knowledge Operations System with RAG (Retrieval-Augmented Generation).

## Overview

Backend stack:
- **FastAPI** - REST API framework
- **Supabase** - PostgreSQL database (cloud)
- **Qdrant** - Vector database for embeddings
- **Redis + Celery** - Async task queue
- **Groq** - LLM inference (free tier)
- **HuggingFace** - Sentence transformers for embeddings

API Routes:
- `POST /api/ingest/upload` - Upload documents (PDF/TXT/MD)
- `GET /api/documents` - List documents
- `DELETE /api/documents/{id}` - Delete document
- `POST /api/ai/query` - RAG-powered AI chat

## Prerequisites

- Python 3.12+
- Redis server (for Celery)
- Supabase account (cloud PostgreSQL)
- Qdrant account (cloud vector DB)
- Groq API key (free: https://console.groq.com)
- HuggingFace account (free)

## Installation

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Install Tesseract OCR (optional, for PDF pages with images)
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# Mac: brew install tesseract
# Linux: sudo apt install tesseract-ocr
```

## Environment Variables

Create `.env` file in `Backend/` directory:

```env
# Supabase (get from https://supabase.com -> your project -> settings)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# Qdrant (get from https://qdrant.cloud)
QDRANT_URL=https://your-cluster.qdrant.cloud
QDRANT_API_KEY=your-api-key

# Groq (free API: https://console.groq.com)
GROQ_API_KEY=your-groq-key

# JWT (for auth tokens)
JWT_SECRET=your-super-secret-jwt-key-change-this

# Admin creation secret (for creating admin users)
ADMIN_CREATE_SECRET=your-admin-create-secret

# Redis (local or cloud)
REDIS_URL=redis://localhost:6379/0

# Slack (optional, for Slack integration)
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-secret
SLACK_APP_TOKEN=xapp-your-token
```

## Database Setup

The database schema is created automatically on startup via Supabase client. Manual setup:

```bash
python supabase/setup_db.py
```

This creates tables:
- `documents` - Document metadata
- `document_chunks` - Text chunks for embedding

## Running the Project

### Option 1: Direct

```bash
cd Backend
python main.py
```

Server runs at `http://localhost:8000`

### Option 2: With Celery (async tasks)

Terminal 1 - Start Redis (if local):
```bash
redis-server
```

Terminal 2 - Start Celery worker:
```bash
cd Backend
celery -A src.celery_app worker --loglevel=info
```

Terminal 3 - Start API:
```bash
cd Backend
python main.py
```

## Testing

```bash
# Health check
curl http://localhost:8000/api/health

# Register user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123", "full_name": "John Doe"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Upload document (with token)
curl -X POST http://localhost:8000/api/ingest/file \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@docs/sample.pdf"

# Query AI
curl -X POST http://localhost:8000/api/ai/query \
  -H "Content-Type: application/json" \
  -d '{"message": "What is in my documents?"}'
```

## Project Structure

```
Backend/
├── main.py                 # FastAPI entry point
├── requirements.txt       # Python dependencies
├── src/
│   ├── api/            # API routes
│   │   ├── documents.py
│   │   ├── ingest.py
│   │   └── ai.py
│   ├── core/
│   │   └── config.py   # Settings class
│   ├── db/
│   │   └── supabase.py
│   ├── services/
│   │   ├── cleaning.py      # Text cleaning (emoji removal)
│   │   ├── chunking.py     # Text chunking
│   │   ├── embedding.py  # HuggingFace embeddings
│   │   ├── vector.py    # Qdrant vector ops
���   │   ├── ai/
│   │   │   └── query.py # RAG pipeline
│   │   └── ingestion/
│   │       ├── pdf_processor.py  # Smart OCR detection
│   │       ├── txt_processor.py
│   │       └── md_processor.py
│   └── celery_app.py    # Celery config
└── supabase/
    └── setup_db.py      # DB schema script
```

## Features

- **Smart PDF OCR** - Only OCRs pages with images (saves API costs)
- **Text Cleaning** - Removes emojis and special characters
- **Recursive Chunking** - Semantic text splitting
- **HuggingFace Embeddings** - Free local embeddings
- **Groq LLM** - Fast inference with free tier