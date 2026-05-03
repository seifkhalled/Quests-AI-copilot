import requests
import time
import json
import os
import sys
from pathlib import Path

# Fix shadowing of 'supabase' package by local 'supabase/' directory
current_dir = os.getcwd()
if current_dir in sys.path:
    sys.path.remove(current_dir)

from dotenv import load_dotenv
from supabase import create_client

# Restore path for local 'src' imports
sys.path.append(current_dir)

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import numpy as np

# Load environment variables
load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "quest_chunks")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# CUSTOM TEST FILE
TEST_FILE_PATH = r"C:\Users\DELL\Downloads\💼 Hiring Quest – Core Software Eng.txt"

# Logging Helpers
def log(msg):
    try:
        print(f"  {msg}")
    except UnicodeEncodeError:
        # Fallback for environments with restricted encoding (like some Windows shells)
        print(f"  {msg.encode('ascii', 'replace').decode('ascii')}")

def ok(msg):        print(f"  [PASS] {msg}")
def fail(msg, e=""): 
    print(f"  [FAIL] {msg}")
    if e: print(f"         {e}")
    sys.exit(1)
def section(title): print(f"\n{'='*55}\n  {title}\n{'='*55}")

def get_test_file():
    path = Path(TEST_FILE_PATH)
    if path.exists():
        log(f"Using external test file: {TEST_FILE_PATH}")
        return path
    
    # Fallback to creating a test file
    log(f"External test file not found. Creating a sample .md file...")
    content = """# Test Quest – Backend Engineer
## Who We're Looking For
We are looking for a backend engineer with 2+ years of experience.
## Tech Stack
Backend: FastAPI
Database: PostgreSQL
Vector DB: Qdrant
"""
    tmp_path = Path("./tmp")
    tmp_path.mkdir(exist_ok=True)
    test_file = tmp_path / "test_quest.md"
    test_file.write_text(content, encoding="utf-8")
    return test_file

def step_1_health_check():
    section("STEP 1 — Health Check")
    health_url = f"{API_BASE_URL}/api/health"
    log(f"Checking health at {health_url}...")
    try:
        response = requests.get(health_url)
        if response.status_code != 200:
            fail(f"API is not reachable at {health_url}. Status: {response.status_code}", response.text)
        
        data = response.json()
        if "qdrant_collection" not in data:
            health_url = f"{API_BASE_URL}/health"
            response = requests.get(health_url)
            data = response.json()
            if "qdrant_collection" not in data:
                fail("API health response missing 'qdrant_collection' data", str(data))

        ok(f"API reachable — Qdrant collection: {data['qdrant_collection']['name']}")
        ok(f"Points in collection before test: {data['qdrant_collection']['points_count']}")
        return data["qdrant_collection"]["points_count"]
    except Exception as e:
        fail("API health check failed", str(e))

def step_2_upload_file(test_file_path):
    section("STEP 2 — Upload File to Ingest Endpoint")
    url = f"{API_BASE_URL}/api/ingest/files"
    
    ext = test_file_path.suffix.lower()
    mime_type = "application/pdf" if ext == ".pdf" else "text/markdown" if ext == ".md" else "text/plain"
    
    log(f"Uploading {test_file_path.name} ({mime_type}) to {url}...")
    try:
        with open(test_file_path, "rb") as f:
            file_bytes = f.read()
        
        files = [("files", (test_file_path.name, file_bytes, mime_type))]
        response = requests.post(url, files=files)
        
        if response.status_code != 200:
            fail("Upload failed", f"Status: {response.status_code}\nBody: {response.text}")
        
        data = response.json()
        doc_data = data[0] if isinstance(data, list) else data
        doc_id = doc_data.get("id") or doc_data.get("document_id")
        
        if not doc_id:
            fail("Upload response missing document_id", str(data))
            
        ok(f"File uploaded — document_id: {doc_id}")
        ok(f"Initial status: {doc_data.get('status')}")
        return doc_id
    except Exception as e:
        fail("File upload failed", str(e))

def step_3_poll_status(doc_id):
    section("STEP 3 — Polling Pipeline Status")
    url = f"{API_BASE_URL}/api/documents/{doc_id}"
    log(f"Polling status at {url}...")
    start_time = time.time()
    
    for i in range(40):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                elapsed = time.time() - start_time
                log(f"Attempt {i+1}/40 — status: {status}")
                
                if status in ["processed", "completed"]:
                    ok(f"Pipeline completed in ~{elapsed:.1f}s")
                    return True
                if status == "failed":
                    fail("Pipeline failed for this document")
            else:
                log(f"Attempt {i+1}/40 — status: {response.status_code}")
                if response.status_code == 500:
                    log(f"  [ERROR 500] {response.text}")
        except Exception as e:
            log(f"Attempt {i+1}/40 — Error: {str(e)}")
        time.sleep(3)
    fail("Pipeline timed out after 120 seconds")

def step_4_verify_supabase_doc(sb, doc_id):
    section("STEP 4 — Verify Document Row in Supabase")
    try:
        result = sb.table("documents").select("*").eq("id", doc_id).single().execute()
        doc = result.data
        ok(f"Check passed: status is {doc['status']}")
        if doc.get("raw_text"):
            ok(f"raw_text length: {len(doc['raw_text'])} chars")
        else:
            fail("raw_text is empty")
        return doc
    except Exception as e:
        fail("Supabase document verification failed", str(e))

def step_5_verify_chunks(sb, doc_id):
    section("STEP 5 — Verify Chunks in Supabase")
    try:
        result = sb.table("chunks").select("*").eq("document_id", doc_id).order("chunk_index").execute()
        chunks = result.data
        if not chunks:
            fail("No chunks found")
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

def step_6_verify_qdrant_ids(chunks):
    section("STEP 6 — Verify Qdrant Point IDs in Chunks Table")
    chunks_with_id = [c for c in chunks if c.get("qdrant_point_id")]
    ok(f"{len(chunks_with_id)}/{len(chunks)} chunks have qdrant_point_id")
    if len(chunks_with_id) < len(chunks):
        fail("Some chunks are missing qdrant_point_id")
    return True

def step_7_verify_qdrant_vectors(doc_id, chunks, points_before):
    section("STEP 7 — Verify Vectors in Qdrant")
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
        
        info = client.get_collection(QDRANT_COLLECTION)
        ok(f"Collection grew from {points_before} to {info.points_count}")
        return results
    except Exception as e:
        fail("Qdrant verification failed", str(e))

def step_8_summary(doc_id, chunks_len, results_len):
    section("STEP 8 — Test Summary")
    log("  [PASS] All steps completed successfully.")
    print(f"\n  Document ID: {doc_id}")
    print(f"  Chunks created: {chunks_len}")
    print(f"  Vectors in Qdrant: {results_len}")
    sys.exit(0)

def main():
    test_file = get_test_file()
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    points_before = step_1_health_check()
    doc_id = step_2_upload_file(test_file)
    step_3_poll_status(doc_id)
    step_4_verify_supabase_doc(sb, doc_id)
    chunks = step_5_verify_chunks(sb, doc_id)
    step_6_verify_qdrant_ids(chunks)
    results = step_7_verify_qdrant_vectors(doc_id, chunks, points_before)
    step_8_summary(doc_id, len(chunks), len(results))

if __name__ == "__main__":
    main()
