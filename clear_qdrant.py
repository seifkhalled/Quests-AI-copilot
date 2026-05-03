import asyncio
import os
import sys
from dotenv import load_dotenv

# Load .env from Backend folder
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Backend')
load_dotenv(os.path.join(backend_path, '.env'))

# Add Backend to sys.path so we can import src
sys.path.insert(0, backend_path)

from src.services.vector import get_vector_service
from src.core.config import settings

async def clear_qdrant():
    """
    Deletes the current Qdrant collection specified in .env
    """
    print(f"--- Qdrant Collection Cleaner ---")
    
    # Initialize vector service
    vector_service = get_vector_service()
    collection_name = vector_service.collection_name
    
    print(f"Target URL: {settings.QDRANT_URL}")
    print(f"Target Collection: {collection_name}")
    print("-" * 30)
    
    confirm = input(f"WARNING: This will PERMANENTLY DELETE the collection '{collection_name}'.\nAre you sure you want to continue? (y/n): ")
    
    if confirm.lower() != 'y':
        print("Operation aborted.")
        return

    try:
        print(f"Deleting collection '{collection_name}'...")
        # Note: client.delete_collection is a synchronous call in qdrant-client
        vector_service.client.delete_collection(collection_name=collection_name)
        print(f"Successfully deleted collection '{collection_name}'.")
        print("\nYou can recreate it by running the backend or 'python Backend/setup_qdrant.py'")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(clear_qdrant())
    except KeyboardInterrupt:
        print("\nAborted.")
