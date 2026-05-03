# Quest Copilot — Data Flow Diagram

This document shows how **data moves** through the system, from the moment a user types a message to when the response is saved and displayed.

---

## High-Level System Data Flow

```mermaid
flowchart LR
    subgraph Client["🌐 Browser (Next.js)"]
        UI["Chat UI\napp/chat/page.tsx"]
        Auth["Auth Store\nlib/auth.ts"]
    end

    subgraph API["⚙️ FastAPI Backend"]
        AuthRoute["/api/auth\nJWT Register/Login"]
        ChatStream["/api/chat/stream\nSSE Streaming"]
        ConvRoute["/api/conversations\nCRUD"]
        IngestRoute["/api/ingest\nFile Upload"]
        DocRoute["/api/documents\nList / Get"]
    end

    subgraph Agent["🤖 LangGraph Agent\n(src/agent/)"]
        Graph["StateGraph\ngraph.py"]
    end

    subgraph External["☁️ External Services"]
        Qdrant[("Qdrant\nVector DB")]
        Supabase[("Supabase\nPostgreSQL")]
        Groq["Groq\nLLM API"]
        SentenceT["Sentence\nTransformers\n(local)"]
    end

    UI -- "JWT Bearer token\n+ message payload" --> ChatStream
    UI -- "credentials" --> AuthRoute
    AuthRoute -- "JWT + user object" --> Auth
    Auth -- "stores token in\nlocalStorage" --> UI

    ChatStream -- "SSE chunks\n{type: content|sources|status}" --> UI
    ChatStream --> Graph
    Graph -- "embed query" --> SentenceT
    SentenceT -- "vector [float32]" --> Graph
    Graph -- "search top-k chunks" --> Qdrant
    Qdrant -- "scored chunks\n+ metadata" --> Graph
    Graph -- "prompt + context" --> Groq
    Groq -- "streamed tokens" --> Graph
    Graph -- "save message\n+ sources" --> Supabase
    Supabase -- "conversation history" --> Graph

    UI -- "create conversation" --> ConvRoute
    ConvRoute -- "conversation_id" --> UI
    ConvRoute --> Supabase

    UI -- "PDF / TXT / MD" --> IngestRoute
    IngestRoute -- "extract + chunk\n+ embed + index" --> Qdrant
    IngestRoute -- "document metadata\n+ chunks" --> Supabase

    UI -- "list documents" --> DocRoute
    DocRoute -- "document list" --> Supabase
```

---

## Chat Message Data Flow (Detailed)

This zooms into the full lifecycle of a single user message through the streaming pipeline.

```mermaid
sequenceDiagram
    actor User
    participant UI as Next.js UI
    participant API as FastAPI /api/chat/stream
    participant Embed as Sentence Transformers
    participant Qdrant as Qdrant Cloud
    participant Groq as Groq LLM
    participant DB as Supabase

    User->>UI: Types message, clicks Send
    UI->>DB: POST /api/conversations (if new chat)
    DB-->>UI: { conversation_id }

    UI->>API: POST /api/chat/stream\n{ message, conversation_id, user_id }
    API-->>UI: SSE event: { type: "start" }

    API->>DB: get_context_window(conversation_id)
    DB-->>API: Last 10 messages (5 turns)

    API-->>UI: SSE event: { type: "status", content: "Searching..." }

    API->>Embed: embed_text(user_message)
    Embed-->>API: [float32 vector, dim=384]

    API->>Qdrant: search(vector, limit=5)
    Qdrant-->>API: Top-5 chunks with score + metadata\n{ document_title, chunk_index, content }

    API->>API: build_context_string(chunks)
    API-->>UI: SSE event: { type: "status", content: "Generating..." }

    API->>Groq: astream(STREAMING_CHAT_PROMPT\n+ context + history + message)

    loop Token streaming
        Groq-->>API: next token chunk
        API-->>UI: SSE event: { type: "content", content: "token" }
    end

    UI->>UI: Append tokens to message bubble in real-time

    API->>DB: save_user_message(conversation_id, message)
    API->>DB: save_assistant_message(conversation_id,\nfull_content, formatted_sources, confidence)

    API-->>UI: SSE event: { type: "sources",\nsources: [{ document_title, chunk_index, snippet, score }] }

    UI->>UI: Show "N sources →" button under message

    User->>UI: Clicks "sources" button
    UI->>UI: Opens Source Panel with cards
```

---

## Document Ingestion Data Flow

Shows what happens when a file is uploaded to the knowledge base.

```mermaid
flowchart TD
    subgraph Input["📥 Input"]
        Upload["File Upload\n.pdf / .txt / .md"]
    end

    subgraph Processing["⚙️ Processing Pipeline\n(src/api/ingest.py)"]
        Extract["Text Extraction\npdf2image + pytesseract\nor raw text read"]
        Chunk["Chunking\nFixed-size with overlap\n~512 tokens"]
        Embed["Embedding\nSentenceTransformers\nall-MiniLM-L6-v2 384-dim"]
    end

    subgraph Storage["💾 Storage"]
        Qdrant[("Qdrant\nVectors + Metadata\nquests_chunks collection")]
        Supabase[("Supabase\ndocuments table\nchunks table")]
    end

    subgraph Background["🔄 Background Task"]
        Insight["generate_post_ingestion_insights()\nGroq LLM summarizes document\nSaves 1-3 insights to insights table"]
    end

    Upload --> Extract
    Extract --> Chunk
    Chunk --> Embed

    Embed -->|"vector point\n{ id, vector, payload }"|Qdrant
    Embed -->|"chunk record\n{ content, chunk_index, doc_id }"|Supabase
    Upload -->|"document record\n{ title, source_type, status }"|Supabase

    Supabase -.->|"document_id"|Insight
    Insight -.->|"insight rows"|Supabase
```

---

## Authentication Data Flow

```mermaid
sequenceDiagram
    actor User
    participant UI as Next.js UI
    participant API as FastAPI /api/auth
    participant DB as Supabase

    User->>UI: Fill Register form\n(email, password, role,\nfull_name, phone if candidate)
    UI->>API: POST /api/auth/register\n{ email, password, role, full_name, phone }
    API->>DB: Check if email exists
    DB-->>API: Not found (OK)
    API->>DB: INSERT into users table
    API->>DB: INSERT into candidate_profiles\n(if role = candidate)\n{ user_id, full_name, phone }
    DB-->>API: Created user row
    API->>API: create_jwt_token(user_id, email, role)\nExpires in 7 days
    API-->>UI: { access_token, user: { id, email, role } }
    UI->>UI: saveAuth(token, user)\nStored in localStorage
    UI->>UI: Redirect to /chat or /dashboard

    Note over User,DB: Login follows the same pattern\nbut skips the INSERT steps
```

---

## Candidate Profile Update Flow

Shows how the AI silently keeps the candidate profile up to date during conversations.

```mermaid
flowchart TD
    A["User sends a message\ne.g. 'I have 3 years in React and Node.js'"] --> B

    B["Streaming endpoint\n/api/chat/stream"] --> C & D

    C["Main path:\nSearch Qdrant → Stream Answer to User"]

    D["Background asyncio.create_task\nrun_extraction()"]

    D --> E["PREFERENCE_EXTRACTION_PROMPT\nsent to Groq LLM"]
    E --> F{{"LLM extracts JSON"}}

    F -->|"tech_stack: React, Node.js\npreferred_roles: Frontend Dev\nsummary: 3yr fullstack dev..."| G

    G["extract_and_save_preferences(user_id, data)"]

    G --> H{{"Profile exists\nin candidate_profiles?"}}
    H -->|No| I["INSERT new profile row"]
    H -->|Yes| J["MERGE fields\ntech_stack = UNION of old + new\npreferred_roles = UNION\nsummary = OVERWRITE with latest"]

    I --> K[("Supabase\ncandidate_profiles table")]
    J --> K
```

---

## Data Store Summary

| Store | Technology | What It Holds |
|---|---|---|
| **Qdrant** | Vector Database (Cloud) | Document chunk embeddings + metadata (title, chunk_index, source) |
| **Supabase - `users`** | PostgreSQL | Email, password hash, role, full_name |
| **Supabase - `candidate_profiles`** | PostgreSQL | full_name, phone, summary, tech_stack[], preferred_roles[], experience_years |
| **Supabase - `conversations`** | PostgreSQL | conversation_id, user_id, status, last_message_at |
| **Supabase - `messages`** | PostgreSQL | role, content, sources (JSONB), confidence, reasoning |
| **Supabase - `documents`** | PostgreSQL | title, source_type, status, raw_text |
| **Supabase - `chunks`** | PostgreSQL | content, chunk_index, qdrant_point_id |
| **Supabase - `insights`** | PostgreSQL | title, body, category, relevance_score |
| **localStorage** | Browser | JWT token + user object (session persistence) |
