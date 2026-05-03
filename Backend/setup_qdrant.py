import asyncio
import sys
import os

# Add the current directory to sys.path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.vector import get_vector_service
from src.core.config import settings

async def init_qdrant():
    print(f"Initializing Qdrant at {settings.QDRANT_URL}...")
    
    # Get the vector service
    vector_service = get_vector_service()
    
    try:
        # Create the collection
        # This uses the parameters defined in your src/services/vector.py
        created = await vector_service.create_collection()
        
        if created:
            print(f"Collection '{vector_service.collection_name}' created successfully!")
            print(f"   - Vector Size: {settings.EMBEDDING_DIM}")
            print(f"   - Distance Metric: Cosine")
        else:
            print(f"Collection '{vector_service.collection_name}' already exists.")
            
    except Exception as e:
        print(f"Failed to initialize Qdrant: {e}")
        print("\nMake sure Qdrant is running. If you are using Docker, run:")
        print("docker run -p 6333:6333 qdrant/qdrant")

if __name__ == "__main__":
    asyncio.run(init_qdrant())
