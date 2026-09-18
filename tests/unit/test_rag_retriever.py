"""
Unit tests for api/rag_retriever.py
"""

import pytest
from api.rag_retriever import (
    get_open_positions,
    get_latest_news,
    call_tool,
    TOOLS,
)


def test_get_open_positions():
    """Test getting open positions."""
    positions = get_open_positions()
    assert len(positions) > 0
    assert all("title" in pos for pos in positions)
    assert all("location" in pos for pos in positions)


def test_get_latest_news():
    """Test getting latest news."""
    news = get_latest_news()
    assert len(news) > 0
    assert all("title" in article for article in news)
    assert all("date" in article for article in news)


def test_tools_registry():
    """Test that tools are registered."""
    assert "get_open_positions" in TOOLS
    assert "get_latest_news" in TOOLS
    assert len(TOOLS) >= 2


def test_call_tool_positions():
    """Test calling tool via registry."""
    result = call_tool("get_open_positions")
    assert result is not None
    assert len(result) > 0


def test_call_tool_news():
    """Test calling tool via registry."""
    result = call_tool("get_latest_news")
    assert result is not None
    assert len(result) > 0


def test_call_tool_nonexistent():
    """Test calling non-existent tool."""
    result = call_tool("nonexistent_tool")
    assert result is None


class TestRAGRetriever:
    """Tests for RAG retriever (requires FAISS and index files)."""

    def test_retriever_init(self):
        """Test RAG retriever initialization."""
        from api.rag_retriever import RAGRetriever

        retriever = RAGRetriever("ness")
        # Should not raise, even if index doesn't exist
        assert retriever.site_id == "ness"

    def test_retriever_no_index(self):
        """Test retriever when no index exists."""
        from api.rag_retriever import RAGRetriever

        retriever = RAGRetriever("ness")
        # If index doesn't exist, retrieve should return None
        if retriever.index is None:
            result = retriever.retrieve("test query")
            assert result is None
