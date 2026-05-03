from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from groq import Groq

from src.core.config import settings
from src.services.embedding import get_embedding_service
from src.services.vector import get_vector_service


@dataclass
class QueryResult:
    """Result of an AI query."""
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    model: str


class AIQueryService:
    """RAG-based AI query service using Groq."""

    def __init__(self):
        self.groq_client = None
        self.embedding_service = get_embedding_service()
        self.vector_service = get_vector_service()

    def _get_groq_client(self) -> Groq:
        if self.groq_client is None:
            self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
        return self.groq_client

    def build_prompt(self, query: str, contexts: List[str]) -> str:
        """Build RAG prompt with contexts."""
        context_text = "\n\n---\n\n".join(
            f"[Source {i+1}]\n{ctx}" for i, ctx in enumerate(contexts)
        )
        
        prompt = f"""You are an AI assistant helping to answer questions based on the provided document knowledge.

Instructions:
- Use only the provided context to answer the question
- If the context doesn't contain relevant information, say "I don't have enough information to answer this question"
- Be precise and cite the sources when possible
- Keep answers concise and helpful

Context:
{context_text}

Question: {query}

Answer:"""
        return prompt

    async def query(
        self,
        question: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        model: str = "meta-llama/llama-4-scout-17b-16e-instruct",
    ) -> QueryResult:
        """
        Query the knowledge base.
        
        Args:
            question: User question
            top_k: Number of chunks to retrieve
            document_id: Optional limit to specific document
            model: Groq model to use
        
        Returns:
            QueryResult with answer, sources, confidence
        """
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(question)
        
        # Search vector DB
        results = await self.vector_service.search(
            query_vector=query_embedding,
            limit=top_k,
            document_id=document_id,
        )
        
        if not results:
            return QueryResult(
                answer="I don't have any relevant information to answer your question.",
                sources=[],
                confidence=0.0,
                model=model,
            )
        
        # Extract contexts
        contexts = [r["content"] for r in results]
        
        # Build prompt
        prompt = self.build_prompt(question, contexts)
        
        # Call Groq
        client = self._get_groq_client()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1024,
        )
        
        answer = response.choices[0].message.content.strip()
        
        # Calculate confidence (based on vector similarity scores)
        avg_score = sum(r["score"] for r in results) / len(results) if results else 0.0
        confidence = min(avg_score * 2, 1.0)  # Scale up a bit
        
        # Format sources
        sources = [
            {
                "document_id": r["document_id"],
                "chunk_index": r["chunk_index"],
                "preview": r["content"][:200] + "..." if len(r["content"]) > 200 else r["content"],
                "score": r["score"],
            }
            for r in results
        ]
        
        return QueryResult(
            answer=answer,
            sources=sources,
            confidence=confidence,
            model=model,
        )


ai_query_service = AIQueryService()


async def get_ai_query_service() -> AIQueryService:
    return ai_query_service