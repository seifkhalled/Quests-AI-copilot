import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import hashlib
import json
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from src.config import Config
from src.db import supabase
from src.services.ingestion import get_ingestion_service
from src.services.cleaning import clean_text


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


async def save_slack_message(
    channel_id: str,
    channel_name: str,
    user_id: str,
    text: str,
    ts: str,
    thread_ts: str = None,
    file_info: dict = None,
):
    """Save Slack message to database."""
    cleaned = clean_text(text, remove_emojis_flag=True)
    if not cleaned.strip():
        return None
    
    content_hash = compute_hash(cleaned)
    
    existing = await supabase.supabase_client.fetchrow(
        "SELECT id FROM documents WHERE content_hash = $1",
        content_hash,
    )
    if existing:
        return str(existing["id"])
    
    doc_id = str(hashlib.uuid4().hex)
    metadata = {
        "source": "slack",
        "channel_id": channel_id,
        "channel_name": channel_name,
        "user_id": user_id,
        "ts": ts,
        "thread_ts": thread_ts,
        "file_info": file_info,
    }
    
    await supabase.supabase_client.execute(
        """
        INSERT INTO documents (id, title, source_type, original_filename, mime_type, file_size_bytes, content_hash, status)
        VALUES ($1, $2, 'slack', $3, 'text/plain', $4, $5, 'completed')
        """,
        doc_id,
        f"Slack #{channel_name}",
        f"{channel_name}/{ts}",
        len(cleaned.encode()),
        content_hash,
    )
    
    version_id = str(hashlib.uuid4().hex)
    await supabase.supabase_client.execute(
        """
        INSERT INTO document_versions (id, document_id, version, raw_content, metadata)
        VALUES ($1, $2, 1, $3, $4)
        """,
        version_id,
        doc_id,
        cleaned,
        json.dumps({"source": "slack"}),
    )
    
    return doc_id


async def fetch_and_save_channel(client, channel_id: str, channel_name: str, limit: int = 100):
    """Fetch and save all messages from a channel."""
    print(f"  📌 Fetching #{channel_name}...")
    
    try:
        client.conversations_join(channel=channel_id)
    except SlackApiError:
        pass
    
    messages = []
    cursor = None
    
    while len(messages) < limit:
        try:
            result = client.conversations_history(
                channel=channel_id,
                limit=min(200, limit - len(messages)),
                cursor=cursor,
            )
        except SlackApiError as e:
            print(f"    ❌ Error: {e.response['error']}")
            break
        
        msgs = result.get("messages", [])
        if not msgs:
            break
        
        messages.extend(msgs)
        cursor = result.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    
    print(f"  💬 Found {len(messages)} messages")
    
    saved = 0
    for msg in messages:
        if msg.get("bot_id"):
            continue
        
        user_id = msg.get("user", "unknown")
        text = msg.get("text", "")
        ts = msg.get("ts")
        thread_ts = msg.get("thread_ts")
        
        if not text:
            continue
        
        doc_id = await save_slack_message(
            channel_id=channel_id,
            channel_name=channel_name,
            user_id=user_id,
            text=text,
            ts=ts,
            thread_ts=thread_ts if thread_ts != ts else None,
        )
        
        if doc_id and doc_id != "duplicate":
            saved += 1
    
    print(f"  ✅ Saved {saved} new messages")
    return saved


async def sync_all_channels(limit_per_channel: int = 100):
    """Fetch and save messages from all channels."""
    Config.validate_slack_tokens()
    client = WebClient(token=Config.SLACK_BOT_TOKEN)
    
    await supabase.init_db()
    
    print("🔍 Fetching channels...")
    
    result = client.conversations_list(types="public_channel,private_channel", limit=100)
    channels = result.get("channels", [])
    print(f"Found {len(channels)} channels\n")
    
    total_saved = 0
    for channel in channels:
        channel_id = channel["id"]
        channel_name = channel["name"]
        
        print(f"📍 Processing #{channel_name}")
        saved = await fetch_and_save_channel(client, channel_id, channel_name, limit_per_channel)
        total_saved += saved
    
    print(f"\n✅ Total new messages saved: {total_saved}")


async def sync_channel_by_name(channel_name: str, limit: int = 100):
    """Sync a specific channel by name."""
    Config.validate_slack_tokens()
    client = WebClient(token=Config.SLACK_BOT_TOKEN)
    
    await supabase.init_db()
    
    # Find channel
    result = client.conversations_list(types="public_channel,private_channel", limit=100)
    channels = result.get("channels", [])
    
    channel = None
    for c in channels:
        if c["name"] == channel_name:
            channel = c
            break
    
    if not channel:
        print(f"❌ Channel #{channel_name} not found")
        return
    
    channel_id = channel["id"]
    print(f"📍 Syncing #{channel_name}")
    
    saved = await fetch_and_save_channel(client, channel_id, channel_name, limit)
    print(f"✅ Saved {saved} messages")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync Slack messages")
    parser.add_argument("--channel", type=str, help="Specific channel name")
    parser.add_argument("--limit", type=int, default=100, help="Messages per channel")
    args = parser.parse_args()
    
    if args.channel:
        asyncio.run(sync_channel_by_name(args.channel, args.limit))
    else:
        asyncio.run(sync_all_channels(args.limit))