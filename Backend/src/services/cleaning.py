import re
import codecs


def remove_emojis(text: str) -> str:
    """Remove emojis from text."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2640-\u2642"
        "\u2600-\u2B55"
        "\u200d"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"
        "\u3030"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub(r"", text)


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace (remove extra spaces, tabs, newlines)."""
    text = re.sub(r"[ \t]+", " ", text)  # multiple spaces/tabs to single space
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)  # multiple newlines to double
    return text.strip()


def remove_control_chars(text: str) -> str:
    """Remove control characters except newlines and tabs."""
    return "".join(char for char in text if ord(char) >= 32 or char in "\n\t\r")


def clean_text(text: str, remove_emojis_flag: bool = True) -> str:
    """
    Minimal text cleaning.
    
    Steps:
    1. Remove emojis (if enabled)
    2. Normalize whitespace
    3. Remove control characters
    """
    if remove_emojis_flag:
        text = remove_emojis(text)
    
    text = normalize_whitespace(text)
    text = remove_control_chars(text)
    
    return text


def detect_language_hint(text: str) -> str:
    """Detect if text is mostly English or other language."""
    english_chars = sum(1 for c in text if c.isascii())
    total_chars = sum(1 for c in text if c.isalnum() or c.isspace())
    
    if total_chars == 0:
        return "en"
    
    return "en" if english_chars / total_chars > 0.7 else "other"


def truncate_text(text: str, max_length: int = 100000) -> str:
    """Truncate text to max length."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "\n\n[Content truncated...]"