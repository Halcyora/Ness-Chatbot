"""
Admin API for managing page selection and ingestion.

Provides routes for:
- Listing discovered pages
- Updating page status (included/excluded/pending)
- Triggering page discovery (scraping)
- Triggering embedding
"""

import os
from typing import List, Dict, Any, Literal
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from api.config_loader import load_site_config
from ingestion.scraper import discover_pages as scraper_discover
from ingestion.embedder import embed_and_index

# Load environment
load_dotenv()

# Configuration
DYNAMODB_ENDPOINT = os.getenv("DYNAMODB_ENDPOINT_URL", "http://localhost:8000")
TABLE_NAME = os.getenv("DYNAMODB_TABLE_CANDIDATES", "page_candidates")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


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


def list_candidates(site_id: str) -> List[Dict[str, Any]]:
    """
    List all page candidates for a site.

    Args:
        site_id: The site identifier

    Returns:
        List of page candidates with their metadata

    Raises:
        ValueError: If site_id is invalid
    """
    # Validate site_id
    try:
        load_site_config(site_id)
    except Exception as e:
        raise ValueError(f"Invalid site_id '{site_id}': {e}")

    table = get_dynamodb_table()
    candidates = []

    try:
        response = table.query(
            KeyConditionExpression="site_id = :site_id",
            ExpressionAttributeValues={
                ":site_id": site_id,
            }
        )

        candidates = response.get("Items", [])

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = table.query(
                KeyConditionExpression="site_id = :site_id",
                ExpressionAttributeValues={
                    ":site_id": site_id,
                },
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            candidates.extend(response.get("Items", []))

        return candidates
    except ClientError as e:
        raise RuntimeError(f"DynamoDB error: {e}")


def set_page_status(
    site_id: str,
    url: str,
    status: Literal["included", "excluded", "pending"],
) -> None:
    """
    Update the status of a page.

    Args:
        site_id: The site identifier
        url: The page URL
        status: The new status (included, excluded, or pending)

    Raises:
        ValueError: If site_id or status is invalid
        RuntimeError: If DynamoDB operation fails
    """
    # Validate site_id
    try:
        load_site_config(site_id)
    except Exception as e:
        raise ValueError(f"Invalid site_id '{site_id}': {e}")

    # Validate status
    if status not in ["included", "excluded", "pending"]:
        raise ValueError(f"Invalid status '{status}'. Must be 'included', 'excluded', or 'pending'")

    table = get_dynamodb_table()

    try:
        table.update_item(
            Key={"site_id": site_id, "url": url},
            UpdateExpression="SET #status = :status, #updated = :updated",
            ExpressionAttributeNames={
                "#status": "status",
                "#updated": "updated_at",
            },
            ExpressionAttributeValues={
                ":status": status,
                ":updated": datetime.utcnow().isoformat() + "Z",
            }
        )
    except ClientError as e:
        raise RuntimeError(f"Failed to update page status: {e}")


def trigger_refresh(site_id: str) -> List[Dict[str, Any]]:
    """
    Trigger page discovery (scraping).

    Crawls sitemap URLs and discovers new pages, storing them as 'pending'.
    Existing pages keep their status.

    Args:
        site_id: The site identifier

    Returns:
        List of discovered pages

    Raises:
        ValueError: If site_id is invalid
    """
    # Validate site_id
    try:
        load_site_config(site_id)
    except Exception as e:
        raise ValueError(f"Invalid site_id '{site_id}': {e}")

    try:
        discovered = scraper_discover(site_id)
        return discovered
    except Exception as e:
        raise RuntimeError(f"Discovery failed: {e}")


def trigger_embed(site_id: str) -> Dict[str, Any]:
    """
    Trigger embedding of all 'included' pages.

    Creates a FAISS index and uploads it to MinIO.

    Args:
        site_id: The site identifier

    Returns:
        Status information about the embedding job

    Raises:
        ValueError: If site_id is invalid
    """
    # Validate site_id
    try:
        load_site_config(site_id)
    except Exception as e:
        raise ValueError(f"Invalid site_id '{site_id}': {e}")

    try:
        start_time = datetime.utcnow()
        embed_and_index(site_id)
        end_time = datetime.utcnow()

        return {
            "status": "success",
            "site_id": site_id,
            "started_at": start_time.isoformat() + "Z",
            "completed_at": end_time.isoformat() + "Z",
            "duration_seconds": (end_time - start_time).total_seconds(),
        }
    except Exception as e:
        raise RuntimeError(f"Embedding failed: {e}")


# Example usage for testing
if __name__ == "__main__":
    try:
        site_id = "ness"

        # List candidates
        print(f"\n📋 Listing candidates for {site_id}...")
        candidates = list_candidates(site_id)
        print(f"Found {len(candidates)} candidates")

        # Trigger refresh
        print(f"\n🔄 Triggering refresh for {site_id}...")
        # discovered = trigger_refresh(site_id)
        # print(f"Discovered {len(discovered)} pages")

        # Trigger embed
        print(f"\n📚 Triggering embed for {site_id}...")
        # result = trigger_embed(site_id)
        # print(f"Embedding {result}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
