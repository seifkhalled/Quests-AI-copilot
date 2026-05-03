import os
from supabase import create_client, Client
from src.core.config import settings

_supabase_client = None

def get_supabase() -> Client:
    global _supabase_client
    if not _supabase_client:
        url = settings.SUPABASE_URL
        key = settings.SUPABASE_KEY
        if not url or not key:
            raise ValueError("Supabase URL and Key must be set in environment")
        _supabase_client = create_client(url, key)
    return _supabase_client
