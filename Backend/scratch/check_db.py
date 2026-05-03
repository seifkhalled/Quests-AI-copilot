import asyncio
import os
import sys

# Add current directory to path so src can be imported
sys.path.append(os.getcwd())

from src.db.supabase import supabase_client

async def check():
    try:
        await supabase_client.connect()
        tables = await supabase_client.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        print("Tables in 'public' schema:")
        for t in tables:
            print(f"- {t['table_name']}")
        await supabase_client.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
