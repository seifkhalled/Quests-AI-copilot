import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class MarkdownDocument:
    """Extracted markdown document."""
    title: str
    content: str
    line_count: int
    heading_count: int


class MarkdownProcessor:
    """Process Markdown files."""

    def process_md(self, content: str, filename: str = "document.md") -> MarkdownDocument:
        """
        Process Markdown file.
        
        Args:
            content: Raw markdown content
            filename: Original filename
        
        Returns:
            MarkdownDocument with extracted content
        """
        title = filename.replace(".md", "")
        
        # Count headings
        heading_pattern = r"^#{1,6}\s+"
        headings = re.findall(heading_pattern, content, re.MULTILINE)
        heading_count = len(headings)
        
        lines = content.split("\n")
        line_count = len(lines)

        return MarkdownDocument(
            title=title,
            content=content.strip(),
            line_count=line_count,
            heading_count=heading_count,
        )

    def to_plain_text(self, content: str) -> str:
        """Convert markdown to plain text."""
        # Remove markdown syntax
        text = re.sub(r"^#{1,6}\s+", "", content, flags=re.MULTILINE)  # Headers
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # Links
        text = re.sub(r"[*_]+", "", text)  # Bold/italic
        text = re.sub(r"```[\s\S]*?```", "", text)  # Code blocks
        text = re.sub(r"`[^`]+`", "", text)  # Inline code
        text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)  # Lists
        text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)  # Numbered lists
        text = re.sub(r"^\s*>", "", text, flags=re.MULTILINE)  # Blockquotes
        
        return text.strip()


markdown_processor = MarkdownProcessor()


def get_markdown_processor() -> MarkdownProcessor:
    return markdown_processor