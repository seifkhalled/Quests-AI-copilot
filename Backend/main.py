from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from src.api import documents, ai, ingest, auth
from src.api.routes.chat import router as chat_router
from src.api.routes.conversations import router as conversations_router
from src.core.config import settings
from src.db import supabase as db_module
from src.services.vector import get_vector_service

load_dotenv()

app = FastAPI(
    title="AI Knowledge Operations System",
    description="RAG-based knowledge management for real estate",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/api/ingest", tags=["Ingestion"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(chat_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    settings.validate()
    await db_module.init_db()
    # Ensure collection exists
    vector_service = get_vector_service()
    await vector_service.create_collection()


@app.get("/api/health")
async def health_check():
    vector_service = get_vector_service()
    points_count = await vector_service.get_count()

    return {
        "status": "healthy", 
        "version": "1.0.0",
        "qdrant_collection": {
            "name": vector_service.collection_name,
            "points_count": points_count
        }
    }


@app.get("/")
async def root():
    return {"message": "AI Knowledge Operations System API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)