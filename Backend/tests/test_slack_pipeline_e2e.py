import os
import sys
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Fix shadowing of 'supabase' package by local 'supabase/' directory
current_dir = os.getcwd()
if current_dir in sys.path:
    sys.path.remove(current_dir)

from supabase import create_client

# Restore path for local 'src' imports
sys.path.append(current_dir)

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import numpy as np

# Load environment variables
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "quest_chunks")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Logging Helpers
def log(msg):       
    try:
        print(f"  {msg}")
    except UnicodeEncodeError:
        print(f"  {msg.encode('ascii', 'replace').decode('ascii')}")

def ok(msg):        print(f"  [PASS] {msg}")
def fail(msg, e=""): 
    print(f"  [FAIL] {msg}")
    if e: print(f"         {e}")
    sys.exit(1)
def section(title): print(f"\n{'='*55}\n  {title}\n{'='*55}")

async def step_1_simulate_slack_message():
    section("STEP 1 — Simulate Slack WebSocket Event")
    
    from src.slack_listener import save_slack_message
    from src.db.supabase import init_db
    
    await init_db()
    
    channel_id = "C_TEST_SLACK_E2E"
    channel_name = "test-slack-e2e"
    user_id = "U_TEST_USER"
    ts = str(time.time())
    text = (f"This is a test Slack message for the E2E pipeline testing. Timestamp: {ts}\n"
            "It should be chunked, embedded, and saved to Qdrant.\n"
            "To ensure this message gets properly chunked, it needs to be longer than the minimum chunk tokens.\n"
            "We are repeating some text. We are repeating some text. We are repeating some text. "
            "We are repeating some text. We are repeating some text. We are repeating some text. "
            "This will guarantee it exceeds the 50 token limit. This is very important for the pipeline. "
            "Testing Slack WebSocket ingestion. Testing Slack WebSocket ingestion.")
    
    log(f"Simulating incoming Slack message in #{channel_name}...")
    log(f"Message content: {text}")
    
    try:
        result = await save_slack_message(
            channel_id=channel_id,
            channel_name=channel_name,
            user_id=user_id,
            text=text,
            ts=ts
        )
        
        doc_id = result.get("id")
        if not doc_id:
            fail("Slack message save returned no doc_id")
            
        ok(f"Message processed via pipeline — document_id: {doc_id}")
        return doc_id
    except Exception as e:
        fail("Slack message processing failed", str(e))

def step_2_verify_supabase_doc(sb, doc_id):
    section("STEP 2 — Verify Document Row in Supabase")
    try:
        result = sb.table("documents").select("*").eq("id", doc_id).single().execute()
        doc = result.data
        ok(f"Check passed: source_type is {doc['source_type']}")
        return doc
    except Exception as e:
        fail("Supabase document verification failed", str(e))

def step_3_verify_chunks(sb, doc_id):
    section("STEP 3 — Verify Chunks in Supabase")
    try:
        result = sb.table("chunks").select("*").eq("document_id", doc_id).order("chunk_index").execute()
        chunks = result.data
        if not chunks:
            fail("No chunks found in Supabase! Pipeline might have failed.")
        ok(f"{len(chunks)} chunks found")
        
        log(f"{'IDX':<5} {'TOKENS':<8} {'QDRANT_ID':<38} {'PREVIEW'}")
        log("-" * 85)
        for chunk in chunks:
            preview = chunk["content"][:45].replace("\n", " ")
            qid = chunk.get("qdrant_point_id") or "NOT SET"
            log(f"{chunk['chunk_index']:<5} {chunk['token_count']:<8} {qid:<38} {preview}")
        return chunks
    except Exception as e:
        fail("Supabase chunks verification failed", str(e))

def step_4_verify_qdrant_ids(chunks):
    section("STEP 4 — Verify Qdrant Point IDs in Chunks Table")
    chunks_with_id = [c for c in chunks if c.get("qdrant_point_id")]
    ok(f"{len(chunks_with_id)}/{len(chunks)} chunks have qdrant_point_id")
    if len(chunks_with_id) < len(chunks):
        fail("Some chunks are missing qdrant_point_id")
    return True

def step_5_verify_qdrant_vectors(doc_id, chunks):
    section("STEP 5 — Verify Vectors in Qdrant")
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        results, _ = client.scroll(
            collection_name=QDRANT_COLLECTION,
            scroll_filter=Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=doc_id))]),
            with_vectors=True, with_payload=True, limit=200
        )
        ok(f"{len(results)} vectors found in Qdrant")
        if len(results) != len(chunks):
            fail(f"Vector count mismatch: {len(results)} vs {len(chunks)}")
        
        for point in results:
            norm = float(np.linalg.norm(point.vector))
            if not (0.95 <= norm <= 1.05):
                fail(f"Abnormal vector norm: {norm:.4f}")
        ok("All vector norms are healthy")
        return results
    except Exception as e:
        fail("Qdrant verification failed", str(e))

def step_6_summary(doc_id, chunks_len, results_len):
    section("STEP 6 — Test Summary")
    log("  [PASS] All steps completed successfully.")
    print(f"\n  Slack Document ID: {doc_id}")
    print(f"  Chunks created: {chunks_len}")
    print(f"  Vectors in Qdrant: {results_len}")
    sys.exit(0)

async def async_main():
    doc_id = await step_1_simulate_slack_message()
    
    # Wait a moment for async inserts to settle if needed, though they are awaited
    await asyncio.sleep(1)
    
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    step_2_verify_supabase_doc(sb, doc_id)
    chunks = step_3_verify_chunks(sb, doc_id)
    step_4_verify_qdrant_ids(chunks)
    results = step_5_verify_qdrant_vectors(doc_id, chunks)
    step_6_summary(doc_id, len(chunks), len(results))

if __name__ == "__main__":
    asyncio.run(async_main())
