import pytest
import os
from dotenv import load_dotenv

# Load .env for testing
load_dotenv(".env.example")


@pytest.fixture
def env_vars(monkeypatch):
    """Set up environment variables for tests."""
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "amazon.nova-micro-v1:0")
    monkeypatch.setenv("BEDROCK_EMBEDDINGS_MODEL_ID", "amazon.titan-embed-text-v1")
    monkeypatch.setenv("AWS_ENDPOINT_URL", "http://localhost:9000")
    monkeypatch.setenv("DYNAMODB_ENDPOINT_URL", "http://localhost:8000")
    monkeypatch.setenv("DYNAMODB_TABLE_CANDIDATES", "page_candidates")
    monkeypatch.setenv("DYNAMODB_TABLE_CACHE", "response_cache")
    monkeypatch.setenv("S3_BUCKET_INDEX", "ness-chatbot-index")
    monkeypatch.setenv("ADMIN_API_KEY", "dev-secret-key-change-in-prod")
