"""
Unit tests for ingestion/scraper.py
"""

import pytest
from ingestion.scraper import (
    extract_text,
    extract_title,
    is_valid_url,
    get_page_urls,
)


def test_extract_text_basic():
    """Test basic text extraction from HTML."""
    html = "<html><body><p>Hello World</p></body></html>"
    text = extract_text(html)
    assert "Hello World" in text


def test_extract_text_removes_scripts():
    """Test that scripts are removed from extracted text."""
    html = "<html><body><script>alert('test')</script><p>Hello</p></body></html>"
    text = extract_text(html)
    assert "alert" not in text
    assert "Hello" in text


def test_extract_text_removes_styles():
    """Test that styles are removed from extracted text."""
    html = "<html><body><style>.class { color: red; }</style><p>Hello</p></body></html>"
    text = extract_text(html)
    assert ".class" not in text
    assert "Hello" in text


def test_extract_title():
    """Test title extraction from HTML."""
    html = "<html><head><title>Page Title</title></head><body></body></html>"
    title = extract_title(html)
    assert title == "Page Title"


def test_extract_title_empty():
    """Test title extraction when no title tag exists."""
    html = "<html><body><p>No title</p></body></html>"
    title = extract_title(html)
    assert title == ""


def test_is_valid_url_same_domain():
    """Test that URLs on same domain are valid."""
    base = "https://example.com/page"
    assert is_valid_url("https://example.com/about", base) is True


def test_is_valid_url_different_domain():
    """Test that URLs on different domains are invalid."""
    base = "https://example.com/page"
    assert is_valid_url("https://other.com/page", base) is False


def test_is_valid_url_excludes_files():
    """Test that certain file types are excluded."""
    base = "https://example.com/page"
    assert is_valid_url("https://example.com/image.jpg", base) is False
    assert is_valid_url("https://example.com/style.css", base) is False
    assert is_valid_url("https://example.com/script.js", base) is False


def test_get_page_urls():
    """Test extracting URLs from HTML."""
    html = """
    <html>
    <body>
        <a href="/about">About</a>
        <a href="/services">Services</a>
    </body>
    </html>
    """
    base = "https://example.com/"
    urls = get_page_urls(base, html)
    assert "https://example.com/about" in urls
    assert "https://example.com/services" in urls
