import asyncio
from src.db.supabase import supabase_client

async def check():
    res = await supabase_client.fetch("SELECT column_name FROM information_schema.columns WHERE table_name='conversations';")
    print([r['column_name'] for r in res])

asyncio.run(check())
