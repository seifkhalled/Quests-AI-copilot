import asyncio
import os
import sys

# Add current directory to path so src can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.db.supabase import supabase_client

async def quick_test():
    try:
        # Use fetchrow instead of fetchval (fetchval is not in our SupabaseClient)
        result = await supabase_client.fetchrow("SELECT 1 as val")
        if result and result['val'] == 1:
            print("✅ Connection Status: Connected Successfully")
        else:
            print("❌ Connection Status: Failed to retrieve expected result")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(quick_test())
