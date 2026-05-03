import logging
import tiktoken
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Constants for fixed-size chunking
TOKENIZER = tiktoken.get_encoding("cl100k_base")
CHUNK_SIZE = 400
CHUNK_OVERLAP = 80
MIN_CHUNK_TOKENS = 50

def count_tokens(text: str) -> int:
    """Count the number of tokens in a string."""
    return len(TOKENIZER.encode(text))

def chunk_text(text: str, document_title: str) -> List[Dict[str, Any]]:
    """
    Split text into fixed-size chunks with overlap.
    Every chunk is prefixed with the document title.
    """
    if not text:
        return []

    # 1. Tokenize the entire text
    tokens = TOKENIZER.encode(text)
    total_tokens = len(tokens)
    
    chunks = []
    chunk_index = 0
    
    # 2. Slide a window of CHUNK_SIZE with CHUNK_OVERLAP
    # Step size is (CHUNK_SIZE - CHUNK_OVERLAP)
    step = CHUNK_SIZE - CHUNK_OVERLAP
    
    # Prefix to be added to every chunk
    prefix = f"[Document: {document_title}]\n\n"
    prefix_tokens = TOKENIZER.encode(prefix)
    prefix_token_count = len(prefix_tokens)

    for start_idx in range(0, total_tokens, step):
        end_idx = min(start_idx + CHUNK_SIZE, total_tokens)
        
        # Get the window of tokens
        chunk_tokens = tokens[start_idx:end_idx]
        
        # 3. Discard if too small (before decoding)
        if len(chunk_tokens) < MIN_CHUNK_TOKENS:
            continue
            
        # 4. Decode window back to string
        chunk_content = TOKENIZER.decode(chunk_tokens)
        
        # 5. Prepend document title
        full_content = prefix + chunk_content.strip()
        
        # 6. Final token count (including prefix)
        final_token_count = prefix_token_count + len(chunk_tokens)
        
        chunks.append({
            "content": full_content,
            "token_count": final_token_count,
            "chunk_index": chunk_index
        })
        
        chunk_index += 1
        
        # If we reached the end of the document, stop
        if end_idx == total_tokens:
            break
            
    logger.info(f"Created {len(chunks)} fixed-size chunks for document: {document_title}")
    return chunks