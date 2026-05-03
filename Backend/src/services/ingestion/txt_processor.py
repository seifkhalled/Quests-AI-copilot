from typing import Optional
from dataclasses import dataclass


@dataclass
class TextDocument:
    """Extracted text document."""
    title: str
    content: str
    line_count: int


class TextProcessor:
    """Process plain text files."""

    def process_txt(self, content: str, filename: str = "document.txt") -> TextDocument:
        """
        Process plain text file.
        
        Args:
            content: Raw text content
            filename: Original filename
        
        Returns:
            TextDocument with extracted content
        """
        title = filename.replace(".txt", "")
        lines = content.split("\n")
        line_count = len(lines)

        return TextDocument(
            title=title,
            content=content.strip(),
            line_count=line_count,
        )


text_processor = TextProcessor()


def get_text_processor() -> TextProcessor:
    return text_processor