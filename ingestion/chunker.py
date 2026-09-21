"""
Text chunking utilities for preparing documents for embedding.

Chunks are built from semantic units (paragraphs, falling back to sentences) packed
greedily up to chunk_size words, so embeddings represent coherent ideas instead of
text sliced mid-sentence at a fixed word count. A raw word-count sliding window is
only used as a last resort for a single unit that's still longer than chunk_size.
"""

import re
from typing import List

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> List[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


def _sliding_window(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Fixed-size word-count fallback for a single unit too long to keep intact."""
    words = text.split()
    pieces = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        pieces.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return pieces


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 100,
) -> List[str]:
    """
    Split text into chunks along paragraph/sentence boundaries.

    Args:
        text: The text to chunk
        chunk_size: Target max words per chunk
        overlap: Words of overlap carried into the next chunk

    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []

    if len(text.split()) <= chunk_size:
        return [text]

    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT_RE.split(text) if p.strip()]
    if len(paragraphs) <= 1:
        paragraphs = _split_sentences(text) or [text]

    # Break any paragraph that's still too big on its own into sentences
    units = []
    for para in paragraphs:
        if len(para.split()) > chunk_size:
            units.extend(_split_sentences(para) or [para])
        else:
            units.append(para)

    # Greedily pack units into chunks up to chunk_size words, carrying `overlap`
    # trailing words forward so consecutive chunks retain some shared context.
    chunks: List[str] = []
    current_words: List[str] = []
    for unit in units:
        unit_words = unit.split()

        if len(unit_words) > chunk_size:
            if current_words:
                chunks.append(" ".join(current_words))
                current_words = []
            chunks.extend(_sliding_window(unit, chunk_size, overlap))
            continue

        if current_words and len(current_words) + len(unit_words) > chunk_size:
            chunks.append(" ".join(current_words))
            current_words = current_words[-overlap:] if overlap else []
        current_words.extend(unit_words)

    if current_words:
        chunks.append(" ".join(current_words))

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
