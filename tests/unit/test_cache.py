"""
Unit tests for api/orchestrator.py and api/cache.py
"""

import pytest
from unittest.mock import patch, MagicMock
from api.cache import hash_query, normalize_query


def test_normalize_query():
    """Test query normalization."""
    result = normalize_query("  Hello World  ")
    assert result == "hello world"


def test_hash_query():
    """Test query hashing."""
    hash1 = hash_query("Hello World")
    hash2 = hash_query("hello world")
    # Different inputs should still hash consistently
    assert len(hash1) == 64  # SHA256
    assert isinstance(hash1, str)


def test_hash_query_consistent():
    """Test that hashing is consistent."""
    query = "What services does Ness offer?"
    hash1 = hash_query(query)
    hash2 = hash_query(query)
    assert hash1 == hash2


def test_cache_key_normalization():
    """Test that cache works with normalized queries."""
    query1 = "  What services?  "
    query2 = "what services?"
    hash1 = hash_query(query1)
    hash2 = hash_query(query2)
    assert hash1 == hash2
