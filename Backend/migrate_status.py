import asyncio
from src.db.supabase import supabase_client

async def migrate():
    await supabase_client.execute("""
        ALTER TABLE conversations 
        ADD COLUMN IF NOT EXISTS status text 
        DEFAULT 'active' 
        CHECK (status IN ('active', 'ended'));
    """)
    print('Migration successful')

asyncio.run(migrate())
