"""
Unit tests for api/intent_router.py
"""

import pytest
from api.intent_router import classify, route_message
from api.config_loader import load_site_config


@pytest.fixture
def ness_config():
    """Load Ness site config for testing."""
    return load_site_config("ness")


class TestClassify:
    """Tests for intent classification."""

    def test_classify_greeting_hello(self, ness_config):
        """Test greeting classification."""
        result = classify("Hello", ness_config)
        assert result["type"] == "greeting"

    def test_classify_greeting_hi(self, ness_config):
        """Test greeting classification."""
        result = classify("Hi there", ness_config)
        assert result["type"] == "greeting"

    def test_classify_greeting_good_morning(self, ness_config):
        """Test greeting classification."""
        result = classify("Good morning", ness_config)
        assert result["type"] == "greeting"

    def test_classify_dynamic_careers(self, ness_config):
        """Test dynamic classification - careers."""
        result = classify("Are there any open positions?", ness_config)
        assert result["type"] == "dynamic"
        assert result["category"] == "careers"

    def test_classify_dynamic_jobs(self, ness_config):
        """Test dynamic classification - jobs."""
        result = classify("Are you hiring?", ness_config)
        assert result["type"] == "dynamic"
        assert result["category"] == "careers"

    def test_classify_dynamic_news(self, ness_config):
        """Test dynamic classification - news."""
        result = classify("What's the latest news?", ness_config)
        assert result["type"] == "dynamic"
        assert result["category"] == "news"

    def test_classify_stable_default(self, ness_config):
        """Test stable classification (default)."""
        result = classify("What services does Ness offer?", ness_config)
        assert result["type"] == "stable"

    def test_classify_empty_message(self, ness_config):
        """Test empty message classification."""
        result = classify("", ness_config)
        assert result["type"] == "stable"

    def test_classify_case_insensitive(self, ness_config):
        """Test case-insensitive classification."""
        result = classify("HELLO", ness_config)
        assert result["type"] == "greeting"


class TestRouteMessage:
    """Tests for message routing."""

    def test_route_greeting(self, ness_config):
        """Test routing for greeting."""
        classification = {"type": "greeting"}
        routing = route_message("Hello", classification, ness_config)
        assert routing["handler"] == "canned"
        assert "reply" in routing

    def test_route_dynamic(self, ness_config):
        """Test routing for dynamic message."""
        classification = {
            "type": "dynamic",
            "category": "careers",
            "url": "/careers",
            "selector": ".job-listing",
        }
        routing = route_message("Are you hiring?", classification, ness_config)
        assert routing["handler"] == "tool"
        assert routing["tool_name"] == "get_careers"
        assert "tool_config" in routing

    def test_route_stable(self, ness_config):
        """Test routing for stable message."""
        classification = {"type": "stable"}
        routing = route_message("What services?", classification, ness_config)
        assert routing["handler"] == "rag"
        assert routing["query"] == "What services?"

    def test_route_preserves_dynamic_config(self, ness_config):
        """Test that routing preserves dynamic page config."""
        classification = {
            "type": "dynamic",
            "category": "news",
            "url": "/insights",
            "selector": ".article-card",
        }
        routing = route_message("News?", classification, ness_config)
        tool_config = routing["tool_config"]
        assert tool_config["url"] == "/insights"
        assert tool_config["selector"] == ".article-card"
        assert tool_config["category"] == "news"
