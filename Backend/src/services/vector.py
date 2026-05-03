import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, PayloadSchemaType
from src.core.config import settings

class VectorService:
    def __init__(self):
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        self.collection_name = settings.QDRANT_COLLECTION

    async def create_collection(self):
        """Ensure the collection exists and has necessary indexes."""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            
            if not exists:
                print(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=settings.EMBEDDING_DIM,
                        distance=Distance.COSINE
                    ),
                )
            
            # Always ensure indexes exist (idempotent in Qdrant)
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="document_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="chunk_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="chunk_index",
                    field_schema=PayloadSchemaType.INTEGER,
                )
            except Exception as index_err:
                print(f"Index check/creation note: {index_err}")
                
        except Exception as e:
            print(f"Error in create_collection: {e}")
            raise

    async def upsert_chunks(
        self,
        document_id: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Upsert chunks and their embeddings into Qdrant.
        Returns the list of generated point IDs.
        """
        points = []
        point_ids = []
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = chunk.get("id") or str(uuid.uuid4())
            point_ids.append(point_id)
            
            payload = {
                "chunk_id": point_id,
                "document_id": document_id,
                "chunk_index": chunk.get("chunk_index", i),
                "content": chunk.get("content", ""),
                "document_title": metadata.get("title", "") if metadata else "",
                **(metadata or {})
            }
            
            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            ))
            
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
        except Exception as e:
            if "Not found: Collection" in str(e):
                print(f"Collection {self.collection_name} not found. Recreating and retrying...")
                await self.create_collection()
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
            else:
                raise
        
        return point_ids

    async def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks."""
        search_filter = None
        if document_id:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )
            
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=search_filter,
            with_payload=True
        )
        
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "content": hit.payload.get("content", ""),
                "metadata": hit.payload
            }
            for hit in results
        ]

    async def delete_document(self, document_id: str):
        """Delete all points associated with a document."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )
        )

    async def get_count(self) -> int:
        """Get total points in collection."""
        try:
            info = self.client.get_collection(self.collection_name)
            return info.points_count
        except Exception:
            return 0

_vector_service = None

def get_vector_service() -> VectorService:
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService()
    return _vector_service