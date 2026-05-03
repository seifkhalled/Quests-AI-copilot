import streamlit as st
import asyncio
import os
import sys
import io
from datetime import datetime

# Add the current directory to sys.path to allow imports from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.ingestion.pdf_processor import get_pdf_processor
from src.services.ingestion.txt_processor import get_text_processor
from src.services.ingestion.md_processor import get_markdown_processor
from src.services.cleaning import clean_text
import hashlib
import uuid
import json
import psycopg2
from psycopg2.extras import RealDictCursor

# Import supabase module (not supabase_client directly)
from src.db import supabase as supabase_module


def run_async(coro):
    """Helper to run async code in Streamlit without loop conflicts."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # If we are already in a loop, we need to use a thread or a different approach
        # But for Streamlit, this usually shouldn't happen in the main thread
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    else:
        return loop.run_until_complete(coro)

def save_to_database(title: str, content: str, file_type: str, filename: str):
    """Save processed document to Supabase database."""
    # Clean the content
    cleaned_content = clean_text(content, remove_emojis_flag=True)
    
    # Compute hash for deduplication
    content_hash = hashlib.sha256(cleaned_content.encode()).hexdigest()
    
def save_to_database(title: str, content: str, file_type: str, filename: str):
    """Save processed document to Supabase database using synchronous psycopg2."""
    from src.core.config import settings
    
    # Clean the content
    cleaned_content = clean_text(content, remove_emojis_flag=True)
    
    # Compute hash for deduplication
    content_hash = hashlib.sha256(cleaned_content.encode()).hexdigest()
    
    conn = None
    try:
        # Connect using DATABASE_URL from settings
        conn = psycopg2.connect(settings.DATABASE_URL, sslmode='require')
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check for duplicate
        cur.execute("SELECT id FROM documents WHERE content_hash = %s", (content_hash,))
        existing = cur.fetchone()
        
        if existing:
            return {"status": "duplicate", "id": str(existing["id"])}
        
        # Create document record
        doc_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO documents (id, title, source_type, original_filename, mime_type, file_size_bytes, content_hash, status, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                doc_id,
                title,
                file_type,
                filename,
                f"application/{file_type}" if file_type != "slack" else "text/plain",
                len(cleaned_content.encode()),
                content_hash,
                "completed",
                json.dumps({"uploaded_via": "streamlit_test"}),
            )
        )
        
        # Create document version
        version_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO document_versions (id, document_id, version, raw_content, metadata)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                version_id,
                doc_id,
                1,
                cleaned_content,
                json.dumps({"uploaded_via": "streamlit_test"}),
            )
        )
        
        conn.commit()
        return {"status": "created", "id": doc_id}
        
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

# Set page configuration
st.set_page_config(
    page_title="PDF Extraction Tester | Quests AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium look
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #161b22 100%);
        color: #e6edf3;
    }
    .header-container {
        padding: 2rem 0;
        text-align: center;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 15px;
        margin-bottom: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .title-text {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        font-size: 3rem;
        background: linear-gradient(90deg, #4f46e5, #0ea5e9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .subtitle-text {
        color: #8b949e;
        font-size: 1.1rem;
    }
    .result-card {
        background: rgba(255, 255, 255, 0.05);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 1rem;
    }
    .method-tag {
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .tag-text { background-color: #238636; color: white; }
    .tag-ocr { background-color: #d29922; color: black; }
    
    /* Animation */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .animated {
        animation: fadeIn 0.5s ease-out forwards;
    }
</style>
""", unsafe_allow_html=True)

# App Header
st.markdown("""
<div class="header-container animated">
    <div class="title-text">Document Extraction Tester</div>
    <div class="subtitle-text">Validate backend extraction logic for PDF, TXT, and MD files</div>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/pdf-document.png", width=80)
    st.title("Settings")
    st.info("This tool uses the actual backend processor classes to ensure consistency with the production environment.")
    
    st.divider()
    
    st.markdown("### Backend Status")
    
    # Check PDF Processor
    pdf_processor = get_pdf_processor()
    if pdf_processor.groq_client:
        st.success("✅ Groq Vision (OCR) Ready")
    else:
        st.warning("⚠️ Groq API Key missing")
        
    # Check Supabase Connection
    try:
        st.markdown("---")
        from src.core.config import settings
        
        # Quick synchronous check
        conn = psycopg2.connect(settings.DATABASE_URL, sslmode='require', connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        res = cur.fetchone()
        cur.close()
        conn.close()
        
        if res and res[0] == 1:
            st.success("✅ Supabase Connected")
            st.caption("Database: `postgres` | Mode: `Synchronous`")
        else:
            st.error("❌ Supabase Error")
    except Exception as e:
        st.error(f"❌ Supabase Connection Failed")
        st.caption(f"Error: {type(e).__name__}")
    
    st.markdown("---")
    # Initialize other processors
    txt_processor = get_text_processor()
    st.success("✅ TXT Processor Ready")
    
    md_processor = get_markdown_processor()
    st.success("✅ MD Processor Ready")

# Main Content
st.markdown("### 📤 Upload Document")

col_type, col_upload = st.columns([1, 3])

with col_type:
    file_type = st.selectbox("File Type", ["PDF", "TXT", "MD"], help="Select the type of file to test")

with col_upload:
    if file_type == "PDF":
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", help="Upload a PDF to test the backend extraction logic.")
    elif file_type == "TXT":
        uploaded_file = st.file_uploader("Choose a TXT file", type="txt", help="Upload a TXT file to test the backend extraction logic.")
    elif file_type == "MD":
        uploaded_file = st.file_uploader("Choose an MD file", type=["md", "markdown"], help="Upload an MD file to test the backend extraction logic.")

col1, col2 = st.columns([1, 1])

if uploaded_file is not None:
    # Read file bytes
    file_bytes = uploaded_file.read()
    filename = uploaded_file.name
    
    with col2:
        st.markdown("### 📊 File Info")
        st.write(f"**Filename:** `{filename}`")
        st.write(f"**Size:** `{len(file_bytes) / 1024:.2f} KB`")
        st.write(f"**Type:** `{file_type}`")
        
        process_btn = st.button("🚀 Process Document", use_container_width=True, type="primary")

    if process_btn:
        with st.status(f"🔍 Extracting {file_type} text...", expanded=True) as status:
            try:
                start_time = datetime.now()
                
                if file_type == "PDF":
                    st.write("Initializing PDF Processor...")
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    doc_result = loop.run_until_complete(pdf_processor.process_pdf_bytes(file_bytes, filename))
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    status.update(label=f"✅ PDF Extraction complete in {duration:.2f}s", state="complete", expanded=False)
                    
                    # Display Results
                    st.divider()
                    
                    # Summary Stats
                    m_col1, m_col2, m_col3 = st.columns(3)
                    m_col1.metric("Total Pages", doc_result.total_pages)
                    m_col2.metric("Has Images", "Yes" if doc_result.has_images else "No")
                    m_col3.metric("Title", doc_result.title[:20] + "..." if len(doc_result.title) > 20 else doc_result.title)
                    
                    # Tabs for different views
                    tab1, tab2, tab3 = st.tabs(["📄 Page-by-Page", "📝 Full Text", "🛠️ Metadata"])
                    
                    with tab1:
                        for page in doc_result.page_results:
                            tag_class = "tag-text" if page.method == "text" else "tag-ocr"
                            st.markdown(f"""
                            <div class="result-card animated">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                                    <span style="font-weight: bold; font-size: 1.1rem;">Page {page.page_num}</span>
                                    <span class="method-tag {tag_class}">{page.method}</span>
                                </div>
                                <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px; font-family: 'Courier New', monospace; white-space: pre-wrap; font-size: 0.9rem; max-height: 300px; overflow-y: auto;">
                                    {page.text if page.text else '<span style="color: #6e7681; font-style: italic;">No text extracted from this page.</span>'}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    with tab2:
                        full_text = pdf_processor.get_full_text(doc_result)
                        st.text_area("Consolidated Extraction Output", full_text, height=600)
                        
                        col_dl, col_save = st.columns([1, 1])
                        with col_dl:
                            st.download_button(
                                label="📥 Download Extracted Text",
                                data=full_text,
                                file_name=f"{filename}_extracted.txt",
                                mime="text/plain",
                            )
                        with col_save:
                            if st.button("💾 Save to Database", key="save_pdf"):
                                result = save_to_database(
                                    title=doc_result.title,
                                    content=full_text,
                                    file_type="pdf",
                                    filename=filename,
                                )
                                if result["status"] == "created":
                                    st.success(f"✅ Saved! Document ID: {result['id']}")
                                elif result["status"] == "duplicate":
                                    st.warning(f"⚠️ Already exists! Document ID: {result['id']}")
                                else:
                                    st.error("❌ Failed to save")
                    
                    with tab3:
                        st.json({
                            "title": doc_result.title,
                            "total_pages": doc_result.total_pages,
                            "has_images": doc_result.has_images,
                            "processing_time_seconds": duration,
                            "pages": [
                                {"page": p.page_num, "method": p.method, "char_count": len(p.text)}
                                for p in doc_result.page_results
                            ]
                        })
                
                elif file_type == "TXT":
                    st.write("Initializing TXT Processor...")
                    text_content = file_bytes.decode("utf-8", errors="ignore")
                    txt_doc = txt_processor.process_txt(text_content, filename)
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    status.update(label=f"✅ TXT Extraction complete in {duration:.2f}s", state="complete", expanded=False)
                    
                    # Display Results
                    st.divider()
                    
                    # Summary Stats
                    m_col1, m_col2, m_col3 = st.columns(3)
                    m_col1.metric("Line Count", txt_doc.line_count)
                    m_col2.metric("Character Count", len(txt_doc.content))
                    m_col3.metric("Title", txt_doc.title[:20] + "..." if len(txt_doc.title) > 20 else txt_doc.title)
                    
                    # Tabs for different views
                    tab1, tab2, tab3 = st.tabs(["📝 Content", "📄 Raw Text", "🛠️ Metadata"])
                    
                    with tab1:
                        st.markdown(f"""
                        <div class="result-card animated">
                            <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px; font-family: 'Courier New', monospace; white-space: pre-wrap; font-size: 0.9rem; max-height: 600px; overflow-y: auto;">
                                {txt_doc.content}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with tab2:
                        st.text_area("Raw Content", txt_doc.content, height=600)
                        
                        col_dl, col_save = st.columns([1, 1])
                        with col_dl:
                            st.download_button(
                                label="📥 Download Extracted Text",
                                data=txt_doc.content,
                                file_name=f"{filename}_extracted.txt",
                                mime="text/plain",
                            )
                        with col_save:
                            if st.button("💾 Save to Database", key="save_txt"):
                                result = save_to_database(
                                    title=txt_doc.title,
                                    content=txt_doc.content,
                                    file_type="txt",
                                    filename=filename,
                                )
                                if result["status"] == "created":
                                    st.success(f"✅ Saved! Document ID: {result['id']}")
                                elif result["status"] == "duplicate":
                                    st.warning(f"⚠️ Already exists! Document ID: {result['id']}")
                                else:
                                    st.error("❌ Failed to save")
                    
                    with tab3:
                        st.json({
                            "title": txt_doc.title,
                            "line_count": txt_doc.line_count,
                            "char_count": len(txt_doc.content),
                            "processing_time_seconds": duration,
                        })
                
                elif file_type == "MD":
                    st.write("Initializing MD Processor...")
                    md_content = file_bytes.decode("utf-8", errors="ignore")
                    md_doc = md_processor.process_md(md_content, filename)
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    status.update(label=f"✅ MD Extraction complete in {duration:.2f}s", state="complete", expanded=False)
                    
                    # Display Results
                    st.divider()
                    
                    # Summary Stats
                    m_col1, m_col2, m_col3 = st.columns(3)
                    m_col1.metric("Line Count", md_doc.line_count)
                    m_col2.metric("Heading Count", md_doc.heading_count)
                    m_col3.metric("Title", md_doc.title[:20] + "..." if len(md_doc.title) > 20 else md_doc.title)
                    
                    # Tabs for different views
                    tab1, tab2, tab3 = st.tabs(["📝 Content", "📄 Raw Text", "🛠️ Metadata"])
                    
                    with tab1:
                        st.markdown(f"""
                        <div class="result-card animated">
                            <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px; font-family: 'Courier New', monospace; white-space: pre-wrap; font-size: 0.9rem; max-height: 600px; overflow-y: auto;">
                                {md_doc.content}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with tab2:
                        st.text_area("Raw Content", md_doc.content, height=600)
                        
                        col_dl, col_save = st.columns([1, 1])
                        with col_dl:
                            st.download_button(
                                label="📥 Download Extracted Text",
                                data=md_doc.content,
                                file_name=f"{filename}_extracted.txt",
                                mime="text/plain",
                            )
                        with col_save:
                            if st.button("💾 Save to Database", key="save_md"):
                                result = save_to_database(
                                    title=md_doc.title,
                                    content=md_doc.content,
                                    file_type="md",
                                    filename=filename,
                                )
                                if result["status"] == "created":
                                    st.success(f"✅ Saved! Document ID: {result['id']}")
                                elif result["status"] == "duplicate":
                                    st.warning(f"⚠️ Already exists! Document ID: {result['id']}")
                                else:
                                    st.error("❌ Failed to save")
                    
                    with tab3:
                        st.json({
                            "title": md_doc.title,
                            "line_count": md_doc.line_count,
                            "heading_count": md_doc.heading_count,
                            "char_count": len(md_doc.content),
                            "processing_time_seconds": duration,
                        })
                    
            except Exception as e:
                st.error(f"❌ Extraction failed: {str(e)}")
                st.exception(e)

else:
    # Empty state
    st.markdown("""
    <div style="text-align: center; padding: 5rem 0; color: #6e7681;">
        <img src="https://img.icons8.com/ios/100/6e7681/upload-to-cloud--v1.png" style="opacity: 0.5; margin-bottom: 1rem;"><br>
        Upload a file to begin testing
    </div>
    """, unsafe_allow_html=True)
