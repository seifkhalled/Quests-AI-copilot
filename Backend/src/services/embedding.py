import os
import numpy as np
from typing import List, Optional
from src.core.config import settings


class EmbeddingService:
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIM
        self._model = None
        self._device = None

    @property
    def model(self):
        """Lazy load the model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            device = "cuda" if os.environ.get("CUDA_VISIBLE_DEVICES") else "cpu"
            self._model = SentenceTransformer(self.model_name, device=device)
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = self.model.encode(texts, batch_size=batch_size, convert_to_numpy=True)
        return [emb.tolist() for emb in embeddings]

    def embed_documents(self, documents: List[dict]) -> List[dict]:
        """
        Embed documents with metadata.
        
        Args:
            documents: List of dicts with 'content' key
        
        Returns:
            List of dicts with added 'embedding' key
        """
        texts = [doc["content"] for doc in documents]
        embeddings = self.embed_texts(texts)
        
        for doc, emb in zip(documents, embeddings):
            doc["embedding"] = emb
        
        return documents

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self.dimension


embedding_service = EmbeddingService()


def get_embedding_service() -> EmbeddingService:
    return embedding_service