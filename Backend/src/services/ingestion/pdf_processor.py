import os
import io
import base64
import fitz  # pymupdf
from typing import List, Tuple, Optional
from dataclasses import dataclass

from groq import Groq
from src.core.config import settings


@dataclass
class PageResult:
    """Result of processing a single page."""
    page_num: int
    text: str
    method: str  # "text" or "ocr"


@dataclass
class PDFDocument:
    """Extracted PDF document."""
    title: str
    total_pages: int
    page_results: List[PageResult]
    has_images: bool


class PDFProcessor:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

    def has_images(self, page: fitz.Page) -> bool:
        """Check if page contains images."""
        images = page.get_images()
        return len(images) > 0

    def has_text(self, page: fitz.Page) -> bool:
        """Check if page contains text."""
        text = page.get_text()
        return len(text.strip()) > 10

    def extract_text(self, page: fitz.Page) -> str:
        """Extract text from a page (fast, free)."""
        text = page.get_text("text")
        return text.strip()

    async def ocr_page(self, page: fitz.Page) -> str:
        """Apply OCR to a page using Groq Vision."""
        if not self.groq_client:
            return "[OCR not available - no GROQ_API_KEY]"

        try:
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")

            response = self.groq_client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_b64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": "Extract all text from this document page exactly as it appears. Preserve the structure and layout."
                            }
                        ]
                    }
                ],
                temperature=0,
                max_tokens=4096,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"[OCR failed: {str(e)}]"

    async def process_page(self, page: fitz.Page, page_num: int) -> PageResult:
        """
        Process a single page with smart detection.
        
        Decision logic:
        - Has text only → extract text (free, fast)
        - Has images → apply OCR (costly)
        - Has both → extract text + OCR for images
        """
        has_img = self.has_images(page)
        has_txt = self.has_text(page)

        if not has_txt and has_img:
            # Image-only page: OCR required
            text = await self.ocr_page(page)
            return PageResult(page_num=page_num, text=text, method="ocr")
        
        elif has_txt and not has_img:
            # Text-only page: extract directly
            text = self.extract_text(page)
            return PageResult(page_num=page_num, text=text, method="text")
        
        elif has_txt and has_img:
            # Hybrid: extract text (prefer free over OCR)
            text = self.extract_text(page)
            if len(text) < 50:  # Text extraction returned little
                text = await self.ocr_page(page)
                method = "ocr"
            else:
                method = "text"
            return PageResult(page_num=page_num, text=text, method=method)
        
        else:
            # Empty page
            return PageResult(page_num=page_num, text="", method="text")

    async def process_pdf(self, pdf_path: str) -> PDFDocument:
        """
        Process entire PDF with smart per-page detection.
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            PDFDocument with extracted content
        """
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        # Extract title from first page or filename
        title = doc.metadata.get("title", "")
        if not title:
            title = os.path.splitext(os.path.basename(pdf_path))[0]
        
        page_results = []
        has_images = False

        for page_num in range(total_pages):
            page = doc.load_page(page_num)
            
            if not has_images:
                has_images = self.has_images(page)
            
            result = await self.process_page(page, page_num + 1)
            page_results.append(result)

        doc.close()

        return PDFDocument(
            title=title,
            total_pages=total_pages,
            page_results=page_results,
            has_images=has_images,
        )

    async def process_pdf_bytes(self, pdf_bytes: bytes, filename: str = "document.pdf") -> PDFDocument:
        """Process PDF from bytes."""
        import asyncio
        
        # Write to temp file
        temp_path = f"temp_{filename}"
        with open(temp_path, "wb") as f:
            f.write(pdf_bytes)
        
        try:
            result = await self.process_pdf(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        return result

    def get_full_text(self, pdf_doc: PDFDocument) -> str:
        """Get full text from processed PDF."""
        parts = []
        for r in pdf_doc.page_results:
            if r.text:
                parts.append(f"--- Page {r.page_num} ---\n{r.text}")
        return "\n\n".join(parts)


pdf_processor = PDFProcessor()


def get_pdf_processor() -> PDFProcessor:
    return pdf_processor