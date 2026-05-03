import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import supabase


async def test_supabase_connection():
    print("Testing Supabase connection...")
    
    # Test 1: Connect
    print("\n1. Testing connection...")
    try:
        await supabase.supabase_client.connect()
        print("   [OK] Connected to database")
    except Exception as e:
        print(f"   [FAIL] {e}")
        return
    
    # Test 2: Fetch data
    print("\n2. Testing fetch...")
    try:
        rows = await supabase.supabase_client.fetch("SELECT 1 as test")
        print(f"   [OK] Fetch works: {rows}")
    except Exception as e:
        print(f"   [FAIL] {e}")
    
    # Test 3: Query documents
    print("\n3. Testing documents table...")
    try:
        rows = await supabase.supabase_client.fetch(
            "SELECT COUNT(*) as count FROM documents"
        )
        print(f"   [OK] Documents count: {rows[0]['count']}")
    except Exception as e:
        print(f"   [FAIL] {e}")
    
    # Test 4: List recent documents
    print("\n4. Listing recent documents...")
    try:
        rows = await supabase.supabase_client.fetch(
            "SELECT id, title, source_type, status FROM documents ORDER BY created_at DESC LIMIT 5"
        )
        for doc in rows:
            print(f"   - {doc['title']} ({doc['source_type']}) - {doc['status']}")
    except Exception as e:
        print(f"   [FAIL] {e}")
    
    print("\n[Done] Supabase connection test complete")


if __name__ == "__main__":
    asyncio.run(test_supabase_connection())