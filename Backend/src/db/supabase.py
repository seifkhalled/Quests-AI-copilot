import os
import asyncio
import asyncpg
from typing import Optional, List
from src.core.config import settings


class SupabaseClient:
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_KEY

    async def connect(self):
        if not self._pool:
            self._pool = await asyncpg.create_pool(
                settings.DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=60,
            )
        return self._pool

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def fetch(self, query: str, *args):
        pool = await self.connect()
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        pool = await self.connect()
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def execute(self, query: str, *args):
        pool = await self.connect()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def execute_many(self, query: str, args_list: list):
        pool = await self.connect()
        async with pool.acquire() as conn:
            await conn.executemany(query, args_list)


supabase_client = SupabaseClient()


async def init_db():
    await supabase_client.connect()


async def close_db():
    await supabase_client.close()