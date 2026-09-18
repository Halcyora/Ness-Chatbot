"""
Unit tests for LLM provider abstraction.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from api.llm import get_llm_provider, LLMProvider
from api.llm.base_provider import LLMProvider as BaseLLMProvider
from api.llm.local_provider import LocalProvider


def test_llm_provider_is_abstract():
    """Test that LLMProvider cannot be instantiated directly."""
    with pytest.raises(TypeError):
        LLMProvider()


def test_get_llm_provider_default_bedrock(monkeypatch):
    """Test that default provider is Bedrock."""
    # Unset LLM_PROVIDER to use default
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    # Mock boto3 to avoid needing real AWS credentials
    with patch("api.llm.bedrock_provider.boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        # Mock the invoke_model response for connection test
        mock_client.invoke_model.return_value = {
            "body": MagicMock(read=lambda: b'{"results": [{"outputText": ""}]}')
        }

        provider = get_llm_provider()
        assert provider.provider_name == "bedrock"


def test_get_llm_provider_explicit_bedrock(monkeypatch):
    """Test explicitly setting Bedrock as provider."""
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")

    with patch("api.llm.bedrock_provider.boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.invoke_model.return_value = {
            "body": MagicMock(read=lambda: b'{"results": [{"outputText": ""}]}')
        }

        provider = get_llm_provider()
        assert provider.provider_name == "bedrock"


def test_get_llm_provider_local_not_implemented(monkeypatch):
    """Test that LocalProvider raises NotImplementedError."""
    monkeypatch.setenv("LLM_PROVIDER", "local")

    with pytest.raises(NotImplementedError, match="not yet implemented"):
        get_llm_provider()


def test_get_llm_provider_unknown_provider(monkeypatch):
    """Test that unknown provider raises ValueError."""
    monkeypatch.setenv("LLM_PROVIDER", "unknown_provider")

    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        get_llm_provider()


def test_provider_name_case_insensitive(monkeypatch):
    """Test that provider name is case-insensitive."""
    monkeypatch.setenv("LLM_PROVIDER", "BEDROCK")

    with patch("api.llm.bedrock_provider.boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.invoke_model.return_value = {
            "body": MagicMock(read=lambda: b'{"results": [{"outputText": ""}]}')
        }

        provider = get_llm_provider()
        assert provider.provider_name == "bedrock"


def test_bedrock_provider_attributes(monkeypatch):
    """Test BedrockProvider attributes."""
    monkeypatch.setenv("BEDROCK_MODEL_ID", "custom.model:1")
    monkeypatch.setenv("BEDROCK_EMBEDDINGS_MODEL_ID", "custom.embeddings:1")
    monkeypatch.setenv("AWS_REGION", "eu-west-1")

    with patch("api.llm.bedrock_provider.boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.invoke_model.return_value = {
            "body": MagicMock(read=lambda: b'{"results": [{"outputText": ""}]}')
        }

        provider = get_llm_provider()
        assert provider.model_id == "custom.model:1"
        assert provider.embeddings_model_id == "custom.embeddings:1"
        assert provider.region == "eu-west-1"
