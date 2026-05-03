import asyncio
from src.db import supabase

async def test():
    await supabase.init_db()
    doc_id = '0a55777e-c7ad-4a44-a52f-186a8e579025'
    query = "SELECT id, title, source_type, status, created_at FROM documents WHERE id = $1"
    row = await supabase.supabase_client.fetchrow(query, doc_id)
    print('Row type:', type(row))
    print('Row:', row)
    if row:
        d = dict(row)
        print('Dict:', d)
    
asyncio.run(test())