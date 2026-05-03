import asyncio
import sys
import os
sys.path.insert(0, '/app')

from src.core.config import settings

async def main():
    print(f"DATABASE_URL: {settings.DATABASE_URL[:40]}...")
    print(f"SUPABASE_URL: {settings.SUPABASE_URL}")
    
    # Test 1: asyncpg raw connection
    try:
        import asyncpg
        conn = await asyncpg.connect(settings.DATABASE_URL)
        print("\n[OK] asyncpg connection successful")
        
        tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        print(f"[OK] Tables found: {[t['table_name'] for t in tables]}")
        
        # Test inserting a conversation
        import uuid
        test_id = str(uuid.uuid4())
        
        # First check users table
        users = await conn.fetch('SELECT id FROM "users" LIMIT 1')
        if users:
            user_id = users[0]['id']
            print(f"[OK] Found user: {user_id}")
            
            await conn.execute(
                '''INSERT INTO conversations (id, user_id, title, scope, created_at, last_message_at)
                   VALUES ($1, $2, $3, $4, now(), now())''',
                test_id, user_id, 'Test Conv', 'global'
            )
            print(f"[OK] Inserted test conversation: {test_id}")
            
            # Clean up
            await conn.execute('DELETE FROM conversations WHERE id = $1', test_id)
            print(f"[OK] Cleaned up test conversation")
        else:
            print("[WARN] No users found in users table - user must be registered first")
        
        await conn.close()
    except Exception as e:
        print(f"\n[FAIL] asyncpg error: {type(e).__name__}: {e}")
    
    # Test 2: Supabase client
    try:
        from src.db.supabase_client import get_supabase
        sb = get_supabase()
        result = sb.table("conversations").select("id").limit(1).execute()
        print(f"\n[OK] Supabase REST client works. Conversation count check ok.")
    except Exception as e:
        print(f"\n[FAIL] Supabase REST client error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
