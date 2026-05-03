import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Qdrant
    QDRANT_URL: str = os.getenv("QDRANT_END_POINT", os.getenv("QDRANT_URL", ""))
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "quest_chunks")

    # Groq Agent (LangGraph LLM — Llama 70B)
    GROQ_AGENT_API_KEY: str = os.getenv("GROQ_AGENT_API_KEY", "")

    # Groq (LLM + OCR)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Slack
    SLACK_APP_TOKEN: str = os.getenv("SLACK_APP_TOKEN", "")
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")

    # Embedding model
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # Chunk settings
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # RAG settings
    TOP_K_CHUNKS: int = 5
    MIN_CONFIDENCE: float = 0.3

    model_config = {"env_file": ".env", "extra": "ignore"}

    def validate(self):
        required = [
            (self.SUPABASE_URL, "SUPABASE_URL"),
            (self.GROQ_API_KEY, "GROQ_API_KEY"),
            (self.GROQ_AGENT_API_KEY, "GROQ_AGENT_API_KEY"),
        ]
        missing = [name for val, name in required if not val]
        if missing:
            raise ValueError(f"Missing required config: {', '.join(missing)}")
        return True


settings = Settings()