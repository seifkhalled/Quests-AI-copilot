import sys
import os
import asyncio

# Add backend to path
sys.path.insert(0, r"E:\Quests-AI-copilot\Backend")

from src.services.ingestion.pdf_processor import PDFProcessor, PDFDocument
from src.services.ingestion.base import FileType


async def test_pdf_extraction(pdf_path: str):
    """Test PDF text extraction and print results."""
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        return
    
    print(f"\n{'='*60}")
    print(f"Testing PDF: {os.path.basename(pdf_path)}")
    print(f"{'='*60}\n")
    
    # Read PDF bytes
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    print(f"File size: {len(pdf_bytes)} bytes\n")
    
    # Create processor
    processor = PDFProcessor()
    
    # Process PDF
    try:
        pdf_doc = await processor.process_pdf_bytes(pdf_bytes, os.path.basename(pdf_path))
        
        print(f"Title: {pdf_doc.title}")
        print(f"Total pages: {pdf_doc.total_pages}")
        print(f"Has images: {pdf_doc.has_images}")
        print(f"\n{'-'*60}")
        print("EXTRACTED TEXT:")
        print(f"{'-'*60}\n")
        
        full_text = processor.get_full_text(pdf_doc)
        print(full_text)
        
        print(f"\n{'-'*60}")
        print(f"Total characters extracted: {len(full_text)}")
        print(f"{'-'*60}\n")
        
        # Show per-page breakdown
        print("PAGE BREAKDOWN:")
        print(f"{'-'*60}")
        for page_result in pdf_doc.page_results:
            print(f"Page {page_result.page_num}: {len(page_result.text)} chars (method: {page_result.method})")
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # Default test PDF
        pdf_path = r"E:\Quests-AI-copilot\Backend\data\quest-70-details.pdf"
        print(f"No PDF path provided. Using default: {pdf_path}")
    
    asyncio.run(test_pdf_extraction(pdf_path))
