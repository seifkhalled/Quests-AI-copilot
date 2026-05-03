# Quests AI Copilot

RAG-based knowledge management system for real estate with Slack integration.

## Tech Stack

- **Frontend**: Next.js 16 (React 19), TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI, Python 3.12
- **Database**: Supabase (PostgreSQL)
- **Vector Database**: Qdrant
- **LLM**: Groq (Llama 3)
- **Task Queue**: Celery + Redis
- **External**: Slack API

## Prerequisites

- Node.js 18+
- Python 3.12
- Supabase account
- Qdrant account (or local instance)
- Groq API key
- Slack app (for Slack integration)

## Environment Setup

### 1. Clone and Setup

```bash
# Backend
cd Backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd Frontend
npm install
```

### 2. Environment Variables

Create `.env` files from the examples:

**Backend (`Backend/.env`):**
```env
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
DATABASE_URL=postgresql://...

# Qdrant
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_key

# Groq
GROQ_API_KEY=your_groq_api_key

# Redis
REDIS_URL=redis://localhost:6379/0

# Slack (optional)
SLACK_APP_TOKEN=xapp-xxx
SLACK_BOT_TOKEN=xoxb-xxx
```

**Frontend (`Frontend/.env.local`):**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Database Setup

Run the Supabase setup script:
```bash
cd Backend/supabase
python setup_db.py
```

## Running the Application

### Backend (FastAPI)
```bash
cd Backend
uvicorn main:app --reload --port 8000
```

### Frontend (Next.js)
```bash
cd Frontend
npm run dev
```

The app will be available at `http://localhost:3000`

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `POST /api/documents/upload` | Upload document |
| `GET /api/documents` | List documents |
| `POST /api/ai/query` | Query AI |
| `POST /api/ingest/sync` | Sync Slack messages |

## Project Structure

```
Backend/
├── main.py              # FastAPI app entry
├── src/
│   ├── api/             # API routes
│   ├── core/            # Config & settings
│   ├── db/              # Supabase client
│   ├── services/        # Business logic
│   └── celery_app.py    # Celery config
├── supabase/            # DB setup scripts
└── requirements.txt

Frontend/
├── app/                 # Next.js App Router
├── components/          # React components
├── lib/                 # Utilities
└── package.json
```

## Features

- Document upload (PDF, MD, TXT)
- OCR for scanned PDFs
- RAG-based AI
- Slack message sync
- Vector search with Qdrant