import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import hashlib
import uuid
import asyncio
from datetime import datetime
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from src.core.config import settings
from src.db import supabase
from src.services.ingestion.pdf_processor import get_pdf_processor
from src.services.ingestion.txt_processor import get_text_processor
from src.services.ingestion.md_processor import get_markdown_processor
from src.services.cleaning import clean_text
from src.services.chunking import chunk_text
from src.services.embedding import get_embedding_service
from src.services.vector import get_vector_service

import threading

# Create a background event loop for all async tasks
bg_loop = asyncio.new_event_loop()

def run_bg_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=run_bg_loop, args=(bg_loop,), daemon=True).start()

def run_async(coro):
    """Run a coroutine on the background event loop and wait for the result."""
    future = asyncio.run_coroutine_threadsafe(coro, bg_loop)
    return future.result()


# Initialize Slack App
if not settings.SLACK_BOT_TOKEN or not settings.SLACK_APP_TOKEN:
    raise ValueError("SLACK_BOT_TOKEN and SLACK_APP_TOKEN are required")

app = App(token=settings.SLACK_BOT_TOKEN)

# Cache channel names
channel_names = {}


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash for deduplication."""
    return hashlib.sha256(content.encode()).hexdigest()


async def save_slack_message(
    channel_id: str,
    channel_name: str,
    user_id: str,
    text: str,
    ts: str,
    thread_ts: str = None,
    file_info: dict = None,
    source_type: str = "slack_json",
    title: str = None,
) -> dict:
    """
    Save Slack message to database.
    
    Returns the created document ID or existing ID if duplicate.
    """
    # Clean text (remove emojis)
    cleaned_text = clean_text(text, remove_emojis_flag=True)
    
    if not cleaned_text.strip():
        return None
    
    # Compute hash for deduplication
    content_hash = compute_content_hash(cleaned_text)
    
    # For deduplication, check if a message with the same timestamp and channel exists in metadata
    existing = await supabase.supabase_client.fetchrow(
        "SELECT id FROM documents WHERE metadata->>'ts' = $1 AND metadata->>'channel_id' = $2",
        ts, channel_id
    )
    if existing:
        return {"id": str(existing["id"]), "status": "duplicate"}
    
    # Create document record
    doc_id = str(uuid.uuid4())
    metadata = {
        "source": "slack",
        "channel_id": channel_id,
        "channel_name": channel_name,
        "user_id": user_id,
        "ts": ts,
        "thread_ts": thread_ts,
        "file_info": file_info,
    }
    
    if title is None:
        title = f"Slack #{channel_name}"

    await supabase.supabase_client.execute(
        """
        INSERT INTO documents (id, title, source_type, raw_text, status, metadata)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        doc_id,
        title,
        source_type,
        cleaned_text,
        "processed",
        json.dumps(metadata),
    )
    # Save the chunking/embedding pipeline
    try:
        # Chunking
        chunks = chunk_text(cleaned_text, title)
        
        # Embedding and Qdrant upload only if there are chunks
        if chunks:
            embedding_service = get_embedding_service()
            chunk_docs = [{"content": c["content"]} for c in chunks]
            chunk_docs = embedding_service.embed_documents(chunk_docs)
            
            for i, chunk in enumerate(chunk_docs):
                chunk["chunk_index"] = chunks[i]["chunk_index"]
                chunk["token_count"] = chunks[i]["token_count"]
                chunk["document_title"] = title
                
            # Vector DB
            vector_service = get_vector_service()
            embeddings = [c["embedding"] for c in chunk_docs]
            vector_ids = await vector_service.upsert_chunks(
                document_id=doc_id,
                chunks=chunk_docs,
                embeddings=embeddings,
                metadata={"title": title, "source": "slack"}
            )
            
            # Save chunks to DB
            chunk_records = [
                (
                    str(uuid.uuid4()),
                    doc_id,
                    c["chunk_index"],
                    c["content"],
                    c["token_count"],
                    vector_ids[i]
                )
                for i, c in enumerate(chunk_docs)
            ]
            
            await supabase.supabase_client.execute_many(
                """
                INSERT INTO chunks (id, document_id, chunk_index, content, token_count, qdrant_point_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                chunk_records,
            )
            print(f"[Slack] Pipeline success: {len(chunks)} chunks embedded and saved to Qdrant.")
        else:
            print(f"[Slack] No chunks generated for message {doc_id} (text too short).")
    except Exception as e:
        print(f"[Slack] Pipeline error for message {doc_id}: {e}")
        import traceback
        traceback.print_exc()

    return {"id": doc_id, "status": "created"}


def resolve_channel_name(client, channel_id: str) -> str:
    """Resolve channel name from ID."""
    if channel_id in channel_names:
        return channel_names[channel_id]
    
    try:
        response = client.conversations_info(channel=channel_id)
        name = response["channel"]["name"]
        channel_names[channel_id] = name
        return name
    except Exception:
        return channel_id


async def handle_file_upload(client, file_info: dict, channel_id: str, channel_name: str, user_id: str) -> dict:
    """
    Handle file uploaded to Slack and print its content using specific processors.
    """
    try:
        filename = file_info.get("name", "unknown")
        filetype = file_info.get("filetype", "").lower()
        file_url = file_info.get("url_private_download")
        
        if not file_url:
            return None
        
        # Download file content using SlackOps
        from src.slack_ops import SlackOps
        ops = SlackOps()
        file_content = ops.download_file(file_url)
        
        extracted_text = ""
        
        # 1. Use PDF Processor directly
        if filetype == "pdf" or file_info.get("mimetype") == "application/pdf":
            print(f"\n[Slack] 📄 Reading PDF: {filename}...")
            processor = get_pdf_processor()
            pdf_doc = await processor.process_pdf_bytes(file_content, filename)
            extracted_text = processor.get_full_text(pdf_doc)
            
        # 2. Use TXT Processor directly
        elif filetype in ("txt", "plain") or file_info.get("mimetype") == "text/plain":
            print(f"\n[Slack] 📝 Reading TXT: {filename}...")
            text_str = file_content.decode("utf-8", errors="ignore")
            processor = get_text_processor()
            txt_doc = processor.process_txt(text_str, filename)
            extracted_text = txt_doc.content
            
        # 3. Use MD Processor directly
        elif filetype in ("md", "markdown") or file_info.get("mimetype") == "text/markdown":
            print(f"\n[Slack] 📘 Reading MD: {filename}...")
            md_str = file_content.decode("utf-8", errors="ignore")
            processor = get_markdown_processor()
            md_doc = processor.process_md(md_str, filename)
            extracted_text = md_doc.content
        else:
            print(f"\n[Slack] Skipping unsupported file: {filename} ({filetype})")
            return None
        
        # Determine source_type
        if filetype == "pdf" or file_info.get("mimetype") == "application/pdf":
            source_type = "pdf"
        elif filetype in ("txt", "plain") or file_info.get("mimetype") == "text/plain":
            source_type = "txt"
        elif filetype in ("md", "markdown") or file_info.get("mimetype") == "text/markdown":
            source_type = "md"
        else:
            source_type = "slack_json"
            
        # PRINT TO LOGS
        print("=" * 60)
        print(f"CONTENT FROM: {filename}")
        print("-" * 60)
        print(extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text)
        print("=" * 60)
        
        # Save and process through the pipeline
        file_ts = str(file_info.get("timestamp", datetime.now().timestamp()))
        await save_slack_message(
            channel_id=channel_id,
            channel_name=channel_name,
            user_id=user_id,
            text=extracted_text,
            ts=file_ts,
            file_info=file_info,
            source_type=source_type,
            title=filename
        )
        
        return {"status": "success", "filename": filename}
        
    except Exception as e:
        print(f"\n[Slack] ❌ Error processing file {file_info.get('name')}: {e}")
        import traceback
        traceback.print_exc()
        return None


@app.event("message")
def handle_message(event, client, logger):
    """Handle incoming message events without replying."""
    # Ignore bot messages
    if event.get("bot_id") or event.get("subtype") in ("bot_message", "thread_broadcast"):
        return
    
    # Check for files in the message
    if event.get("subtype") == "file_share":
        files = event.get("files", [])
        if not files:
            return
        
        channel_id = event.get("channel")
        user_id = event.get("user")
        channel_name = resolve_channel_name(client, channel_id)
        
        for file_info in files:
            # Run async file processing on background loop
            run_async(handle_file_upload(
                client=client,
                file_info=file_info,
                channel_id=channel_id,
                channel_name=channel_name,
                user_id=user_id
            ))
        return

    channel_id = event.get("channel")
    user_id = event.get("user")
    text = event.get("text", "")
    ts = event.get("ts")
    
    if not channel_id or not text:
        return
    
    channel_name = resolve_channel_name(client, channel_id)
    
    print(f"\n[Slack] 💬 Message in #{channel_name}: {text[:100]}...")
    
    # Save message metadata silently
    try:
        run_async(save_slack_message(
            channel_id=channel_id,
            channel_name=channel_name,
            user_id=user_id,
            text=text,
            ts=ts
        ))
    except Exception as e:
        print(f"[Database] Warning: {e}")


@app.event("file_shared")
def handle_file_shared(event, client, logger):
    """Handle file shared in a channel."""
    file_id = event.get("file_id")
    channel_id = event.get("channel_id")
    user_id = event.get("user_id")
    
    if not file_id or not channel_id:
        return
    
    try:
        response = client.api_call("files.info", file=file_id)
        file_info = response["file"]
    except Exception as e:
        print(f"[Slack] Error getting file info: {e}")
        return
    
    channel_name = resolve_channel_name(client, channel_id)
    
    # Process asynchronously on background loop
    run_async(handle_file_upload(
        client=client,
        file_info=file_info,
        channel_id=channel_id,
        channel_name=channel_name,
        user_id=user_id
    ))


@app.event("reaction_added")
def handle_reaction(event, client, logger):
    """Handle reaction added to a message."""
    reaction = event.get("reaction")
    user_id = event.get("user")
    item = event.get("item", {})
    ts = item.get("ts")
    channel_id = item.get("channel")
    
    if not ts or not channel_id:
        return
    
    channel_name = resolve_channel_name(client, channel_id)
    
    print("\n[Slack] REACTION ADDED")
    print(f"[Slack] Channel: #{channel_name}")
    print(f"[Slack] User: {user_id}")
    print(f"[Slack] Reaction: {reaction}")
    print(f"[Slack] Message: {ts}")
    print("-" * 40)


@app.event("thread_started")
def handle_thread(event, client, logger):
    """Handle thread started."""
    channel_id = event.get("channel_id")
    user_id = event.get("user")
    ts = event.get("ts")
    
    if not channel_id:
        return
    
    channel_name = resolve_channel_name(client, channel_id)
    
    print("\n[Slack] THREAD STARTED")
    print(f"[Slack] Channel: #{channel_name}")
    print(f"[Slack] User: {user_id}")
    print(f"[Slack] Timestamp: {ts}")
    print("-" * 40)


if __name__ == "__main__":
    print("[Slack] Bot running in Socket Mode...")
    print("[Slack] Listening for messages, files, reactions, and threads...")
    
    handler = SocketModeHandler(app, settings.SLACK_APP_TOKEN)
    handler.start()