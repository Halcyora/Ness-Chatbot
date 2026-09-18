"""
Unit tests for ingestion/chunker.py
"""

import pytest
from ingestion.chunker import chunk_text, chunk_documents


def test_chunk_text_basic():
    """Test basic text chunking."""
    text = " ".join(["word"] * 100)
    chunks = chunk_text(text, chunk_size=20, overlap=5)
    assert len(chunks) > 1


def test_chunk_text_empty():
    """Test chunking empty text."""
    chunks = chunk_text("")
    assert chunks == []


def test_chunk_text_short():
    """Test chunking text shorter than chunk size."""
    text = "This is a short text"
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_with_overlap():
    """Test that chunks have overlap."""
    text = " ".join([str(i) for i in range(100)])
    chunks = chunk_text(text, chunk_size=20, overlap=5)

    # Check overlap - last words of chunk should appear in next chunk
    for i in range(len(chunks) - 1):
        current_chunk_words = chunks[i].split()
        next_chunk_words = chunks[i + 1].split()

        # The end of current chunk should have words from overlap
        overlap_words = current_chunk_words[-5:]  # Last 5 words
        should_be_in_next = any(word in next_chunk_words for word in overlap_words)
        assert should_be_in_next


def test_chunk_documents():
    """Test chunking multiple documents."""
    documents = [
        {
            "content": " ".join(["word"] * 100),
            "url": "https://example.com/page1",
            "title": "Page 1",
        },
        {
            "content": " ".join(["word"] * 50),
            "url": "https://example.com/page2",
            "title": "Page 2",
        },
    ]

    chunks = chunk_documents(documents, chunk_size=20, overlap=5)

    # Should have multiple chunks from both documents
    assert len(chunks) > 2

    # Check metadata is preserved
    for chunk in chunks:
        assert "content" in chunk
        assert "url" in chunk
        assert "title" in chunk
        assert "chunk_index" in chunk
        assert "total_chunks" in chunk


def test_chunk_documents_empty_content():
    """Test that documents with empty content are skipped."""
    documents = [
        {"content": "", "url": "https://example.com/empty", "title": "Empty"},
        {"content": "actual content", "url": "https://example.com/valid", "title": "Valid"},
    ]

    chunks = chunk_documents(documents)

    # Should only have chunks from the valid document
    assert len(chunks) == 1
    assert chunks[0]["url"] == "https://example.com/valid"
