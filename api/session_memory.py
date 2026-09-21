"""
Short-term conversation memory so the chatbot can resolve follow-up questions.

Uses DynamoDB with TTL: each session_id stores a rolling window of the most
recent user/bot turns. This is separate from response_cache (which caches
identical queries) and is scoped per browser session, not per query.
"""

import os
import time
from typing import Any, Dict, List

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

DYNAMODB_ENDPOINT = os.getenv("DYNAMODB_ENDPOINT_URL", "http://localhost:8000")
TABLE_NAME = os.getenv("DYNAMODB_TABLE_SESSIONS", "session_history")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SESSION_TTL_SECONDS = 4 * 3600  # session context expires after 4 hours of inactivity
MAX_TURNS = 6  # last 6 entries (3 user/bot exchanges) kept for context


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


def get_history(session_id: str) -> List[Dict[str, str]]:
    """Retrieve recent conversation turns for a session, oldest first."""
    if not session_id:
        return []

    table = get_dynamodb_table()
    try:
        response = table.get_item(Key={"session_id": session_id})
        item = response.get("Item")
        if not item:
            return []

        if "ttl" in item and int(item["ttl"]) < int(time.time()):
            return []

        return list(item.get("turns", []))
    except ClientError as e:
        print(f"Session history retrieval error: {e}")
        return []


def append_turn(session_id: str, user_message: str, bot_reply: str) -> None:
    """Append a user/bot exchange to the session, trimming to the last MAX_TURNS entries."""
    if not session_id:
        return

    history = get_history(session_id)
    history.append({"role": "user", "content": user_message})
    history.append({"role": "bot", "content": bot_reply})
    history = history[-MAX_TURNS:]

    table = get_dynamodb_table()
    ttl_timestamp = int(time.time()) + SESSION_TTL_SECONDS
    try:
        table.put_item(
            Item={
                "session_id": session_id,
                "turns": history,
                "ttl": ttl_timestamp,
            }
        )
    except ClientError as e:
        print(f"Session history write error: {e}")


def clear_session(session_id: str) -> None:
    """Delete a session's stored history."""
    if not session_id:
        return
    table = get_dynamodb_table()
    try:
        table.delete_item(Key={"session_id": session_id})
    except ClientError as e:
        print(f"Session history clear error: {e}")
