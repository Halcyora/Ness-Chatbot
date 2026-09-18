#!/usr/bin/env python
"""
Create DynamoDB tables for local development.

This script creates the required tables in DynamoDB Local.
It's safe to run multiple times (idempotent).

Make sure docker-compose is running:
    docker-compose up -d
"""

import boto3
import os
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# DynamoDB configuration
dynamodb_endpoint = os.getenv("DYNAMODB_ENDPOINT_URL", "http://localhost:8000")
aws_region = os.getenv("AWS_REGION", "us-east-1")

# Table names
table_candidates = os.getenv("DYNAMODB_TABLE_CANDIDATES", "page_candidates")
table_cache = os.getenv("DYNAMODB_TABLE_CACHE", "response_cache")

# Create DynamoDB resource
dynamodb = boto3.resource(
    "dynamodb",
    endpoint_url=dynamodb_endpoint,
    region_name=aws_region,
    aws_access_key_id="test",
    aws_secret_access_key="test",
)


def create_page_candidates_table():
    """Create page_candidates table for storing discovered pages."""
    try:
        table = dynamodb.create_table(
            TableName=table_candidates,
            KeySchema=[
                {"AttributeName": "site_id", "KeyType": "HASH"},  # Partition key
                {"AttributeName": "url", "KeyType": "RANGE"},  # Sort key
            ],
            AttributeDefinitions=[
                {"AttributeName": "site_id", "AttributeType": "S"},
                {"AttributeName": "url", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        print(f"✅ Created table: {table_candidates}")
        table.wait_until_exists()
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"ℹ️  Table already exists: {table_candidates}")
        else:
            raise


def create_response_cache_table():
    """Create response_cache table for caching LLM responses."""
    try:
        table = dynamodb.create_table(
            TableName=table_cache,
            KeySchema=[
                {"AttributeName": "query_hash", "KeyType": "HASH"},  # Partition key
            ],
            AttributeDefinitions=[
                {"AttributeName": "query_hash", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
            TimeToLiveSpecification={
                "AttributeName": "ttl",
                "Enabled": True,
            },
        )
        print(f"✅ Created table: {table_cache}")
        table.wait_until_exists()
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"ℹ️  Table already exists: {table_cache}")
        else:
            raise


if __name__ == "__main__":
    print(f"Connecting to DynamoDB at {dynamodb_endpoint}...")
    print(f"Region: {aws_region}\n")

    try:
        create_page_candidates_table()
        create_response_cache_table()
        print("\n✅ All tables ready!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure DynamoDB Local is running:")
        print("  docker-compose up -d dynamodb-local")
        exit(1)
