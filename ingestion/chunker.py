"""
Text chunking utilities for preparing documents for embedding.

Implements simple sliding-window text chunking with overlap.
"""

from typing import List


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 100,
) -> List[str]:
    """
    Split text into overlapping chunks.

    Uses word-based chunking to avoid breaking mid-word.

    Args:
        text: The text to chunk
        chunk_size: Target words per chunk
        overlap: Words of overlap between chunks

    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []

    # Split into words
    words = text.split()

    if len(words) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(words):
        # End of current chunk
        end = min(start + chunk_size, len(words))

        # Extract chunk
        chunk_words = words[start:end]
        chunk = " ".join(chunk_words)
        chunks.append(chunk)

        # Move start position by (chunk_size - overlap)
        start += chunk_size - overlap

    return chunks


def chunk_documents(
    documents: List[dict],
    chunk_size: int = 800,
    overlap: int = 100,
) -> List[dict]:
    """
    Chunk a list of documents.

    Each document should have 'content' and 'url'/'title' fields.

    Args:
        documents: List of documents with 'content', 'url', 'title'
        chunk_size: Target words per chunk
        overlap: Words of overlap between chunks

    Returns:
        List of chunks with metadata (content, url, title, chunk_index)
    """
    chunks = []

    for doc in documents:
        content = doc.get("content", "")
        url = doc.get("url", "")
        title = doc.get("title", "")

        if not content:
            continue

        # Chunk the document
        text_chunks = chunk_text(content, chunk_size, overlap)

        for idx, chunk_text_str in enumerate(text_chunks):
            chunks.append({
                "content": chunk_text_str,
                "url": url,
                "title": title,
                "chunk_index": idx,
                "total_chunks": len(text_chunks),
            })

    return chunks
