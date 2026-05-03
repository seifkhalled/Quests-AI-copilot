import hashlib
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from src.services.ingestion.pdf_processor import PDFProcessor, PDFDocument, get_pdf_processor
from src.services.ingestion.txt_processor import TextProcessor, TextDocument, get_text_processor
from src.services.ingestion.md_processor import MarkdownProcessor, MarkdownDocument, get_markdown_processor, get_markdown_processor
from src.services.cleaning import clean_text


class FileType(Enum):
    PDF = "pdf"
    TXT = "txt"
    MD = "md"
    UNKNOWN = "unknown"


@dataclass
class IngestedDocument:
    """Document after ingestion."""
    title: str
    content: str
    file_type: FileType
    content_hash: str
    metadata: dict


class IngestionService:
    """Main ingestion service for all file types."""

    def __init__(self):
        self.pdf_processor = get_pdf_processor()
        self.txt_processor = get_text_processor()
        self.md_processor = get_markdown_processor()

    def detect_file_type(self, filename: str, mime_type: str = None) -> FileType:
        """Detect file type from extension or MIME type."""
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        
        if ext == "pdf" or mime_type == "application/pdf":
            return FileType.PDF
        elif ext == "txt" or mime_type == "text/plain":
            return FileType.TXT
        elif ext in ("md", "markdown") or mime_type == "text/markdown":
            return FileType.MD
        else:
            return FileType.UNKNOWN

    def compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()

    async def ingest_file(
        self,
        content: bytes,
        filename: str,
        mime_type: str = None,
    ) -> IngestedDocument:
        """
        Ingest a file based on its type.
        
        Args:
            content: File bytes
            filename: Original filename
            mime_type: MIME type (optional)
        
        Returns:
            IngestedDocument with extracted content
        """
        file_type = self.detect_file_type(filename, mime_type)
        
        if file_type == FileType.PDF:
            pdf_doc = await self.pdf_processor.process_pdf_bytes(content, filename)
            raw_content = self.pdf_processor.get_full_text(pdf_doc)
            title = pdf_doc.title
            metadata = {
                "total_pages": pdf_doc.total_pages,
                "has_images": pdf_doc.has_images,
            }
        
        elif file_type == FileType.TXT:
            text_content = content.decode("utf-8", errors="ignore")
            txt_doc = self.txt_processor.process_txt(text_content, filename)
            raw_content = txt_doc.content
            title = txt_doc.title
            metadata = {"line_count": txt_doc.line_count}
        
        elif file_type == FileType.MD:
            md_content = content.decode("utf-8", errors="ignore")
            md_doc = self.md_processor.process_md(md_content, filename)
            raw_content = md_doc.content
            title = md_doc.title
            metadata = {
                "line_count": md_doc.line_count,
                "heading_count": md_doc.heading_count,
            }
        
        else:
            raise ValueError(f"Unsupported file type: {filename}")
        
        # Clean the content (minimal cleaning)
        cleaned_content = clean_text(raw_content, remove_emojis_flag=True)
        
        # Compute hash
        content_hash = self.compute_hash(cleaned_content)
        
        return IngestedDocument(
            title=title,
            content=cleaned_content,
            file_type=file_type,
            content_hash=content_hash,
            metadata=metadata,
        )


ingestion_service = IngestionService()


async def get_ingestion_service() -> IngestionService:
    return ingestion_service