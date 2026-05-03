# Quests AI Copilot

RAG-based knowledge management system for real estate with Slack integration.

## Tech Stack

- **Frontend**: Next.js 16 (React 19), TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI, Python 3.12
- **Database**: Supabase (PostgreSQL)
- **Vector Database**: Qdrant
- **LLM**: Groq / OpenRouter
- **External**: Slack API

## Prerequisites

- Node.js 18+
- Python 3.12+
- Supabase account (https://supabase.com)
- Qdrant account (https://qdrant.ai)
- Groq or OpenRouter API key

## Setup

### 1. Clone and Install Dependencies

```bash
# Backend
cd Backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Frontend
cd Frontend
npm install
```

### 2. Environment Variables

Copy the example files and fill in your credentials:

```bash
# Backend
cp .env.example .env
```

Edit `Backend/.env` with your credentials:

| Variable | Description | How to get |
|----------|-------------|------------|
| `SUPABASE_URL` | Supabase project URL | Supabase Dashboard → Settings → API |
| `DATABASE_URL` | PostgreSQL connection string | Supabase Dashboard → Settings → Database |
| `PUBLISHABLE_KEY` | Supabase publishable key | Supabase Dashboard → Settings → API |
| `SECRET_KEY` | Supabase secret key | Supabase Dashboard → Settings → API |
| `QDRANT_URL` | Qdrant cluster URL | Qdrant Dashboard → Clusters |
| `QDRANT_API_KEY` | Qdrant API key | Qdrant Dashboard → API Keys |
| `GROQ_API_KEY` | Groq API key | https://console.groq.com |
| `OPEN_ROUTER_API_KEY` | OpenRouter API key | https://openrouter.ai |

### 3. Database Setup

The database tables are created automatically on first run. Alternatively:

```bash
cd Backend/supabase
python setup_db.py
```

### 4. Slack Integration (Optional)

To enable Slack integration:

1. Create a Slack app at https://api.slack.com/apps
2. Add the following Bot Token Scopes:
   - `channels:history`
   - `channels:read`
   - `chat:write`
   - `users:read`
3. Install the app to your workspace
4. Copy the credentials to `.env`

## Running the Application

### Backend

```bash
cd Backend
python main.py
```

The API runs at `http://localhost:8000`

### Frontend

```bash
cd Frontend
npm run dev
```

The app runs at `http://localhost:3000`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/documents` | GET | List documents |
| `/api/documents/upload` | POST | Upload document |
| `/api/documents/{id}` | DELETE | Delete document |
| `/api/ai/query` | POST | Query AI |
| `/api/ingest/sync` | POST | Sync Slack messages |

## Testing

```bash
# Health check
curl http://localhost:8000/api/health

# Upload document
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@sample.pdf"

# Query AI
curl -X POST http://localhost:8000/api/ai/query \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "question": "What documents do I have?"}'
```

## Project Structure

```
Quests-AI-copilot/
├── Backend/
│   ├── main.py              # FastAPI app entry
│   ├── src/
│   │   ├── api/             # API routes
│   │   ├── core/            # Config & settings
│   │   ├── db/              # Supabase client
│   │   └── services/        # Business logic
│   ├── supabase/            # DB setup scripts
│   └── requirements.txt
│
├── Frontend/
│   ├── app/                 # Next.js App Router
│   ├── components/          # React components
│   └── lib/                 # Utilities
│
└── README.md
```

## Features

- Document upload (PDF, MD, TXT)
- OCR for scanned PDFs
- RAG-based AI chat
- Slack message sync
- Vector search with Qdrant