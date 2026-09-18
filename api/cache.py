"""
Response caching to avoid repeated LLM calls.

Uses DynamoDB with TTL for cost optimization.
"""

import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
DYNAMODB_ENDPOINT = os.getenv("DYNAMODB_ENDPOINT_URL", "http://localhost:8000")
TABLE_NAME = os.getenv("DYNAMODB_TABLE_CACHE", "response_cache")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
CACHE_TTL_SECONDS = 86400  # 24 hours


def get_dynamodb_table():
    """Get DynamoDB table resource."""
    dynamodb = boto3.resource(
        "dynamodb",
        endpoint_url=DYNAMODB_ENDPOINT,
        region_name=AWS_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )
    return dynamodb.Table(TABLE_NAME)


def normalize_query(query: str) -> str:
    """Normalize query for consistent hashing."""
    return query.strip().lower()


def hash_query(query: str) -> str:
    """Generate a hash key for a query."""
    normalized = normalize_query(query)
    return hashlib.sha256(normalized.encode()).hexdigest()


def get_cached(query: str) -> Optional[str]:
    """
    Retrieve cached response for a query.

    Args:
        query: The original query

    Returns:
        Cached response, or None if not found/expired
    """
    query_hash = hash_query(query)
    table = get_dynamodb_table()

    try:
        response = table.get_item(Key={"query_hash": query_hash})
        item = response.get("Item")

        if not item:
            return None

        # Check if TTL has expired (DynamoDB may not auto-delete)
        if "ttl" in item:
            import time
            if int(item["ttl"]) < int(time.time()):
                return None

        return item.get("answer")

    except ClientError as e:
        print(f"Cache retrieval error: {e}")
        return None


def set_cached(query: str, answer: str, ttl_seconds: int = CACHE_TTL_SECONDS) -> None:
    """
    Cache a response for a query.

    Args:
        query: The query
        answer: The LLM-generated answer
        ttl_seconds: Time-to-live in seconds
    """
    query_hash = hash_query(query)
    table = get_dynamodb_table()

    import time
    ttl_timestamp = int(time.time()) + ttl_seconds

    try:
        table.put_item(
            Item={
                "query_hash": query_hash,
                "query": query,
                "answer": answer,
                "ttl": ttl_timestamp,
                "created_at": datetime.utcnow().isoformat() + "Z",
            }
        )
    except ClientError as e:
        print(f"Cache write error: {e}")
        # Don't raise - caching is optional
