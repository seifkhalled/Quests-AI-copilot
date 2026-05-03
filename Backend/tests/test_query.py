import asyncio
from src.db import supabase

async def test():
    await supabase.init_db()
    doc_id = '949b92f3-8985-4f23-952e-54c53c9df2a2'
    result = await supabase.supabase_client.fetchrow(
        "SELECT id, title, source_type, status, created_at FROM documents WHERE id = $1",
        doc_id
    )
    print('Result:', dict(result) if result else None)

asyncio.run(test())