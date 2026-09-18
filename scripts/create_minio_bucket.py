#!/usr/bin/env python
"""
Create MinIO bucket for local development.

This script creates the S3-compatible bucket in MinIO for storing FAISS indices.
It's safe to run multiple times (idempotent).

Make sure docker-compose is running:
    docker-compose up -d minio
"""

import boto3
import os
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MinIO configuration
minio_endpoint = os.getenv("AWS_ENDPOINT_URL", "http://localhost:9000")
minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
bucket_name = os.getenv("S3_BUCKET_INDEX", "ness-chatbot-index")

# Create S3 client pointing to MinIO
s3_client = boto3.client(
    "s3",
    endpoint_url=minio_endpoint,
    aws_access_key_id=minio_access_key,
    aws_secret_access_key=minio_secret_key,
    region_name="us-east-1",
)


def create_bucket():
    """Create the S3 bucket in MinIO."""
    try:
        s3_client.create_bucket(Bucket=bucket_name)
        print(f"✅ Created bucket: {bucket_name}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "BucketAlreadyExists":
            print(f"ℹ️  Bucket already exists: {bucket_name}")
        elif e.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
            print(f"ℹ️  Bucket already owned: {bucket_name}")
        else:
            raise


if __name__ == "__main__":
    print(f"Connecting to MinIO at {minio_endpoint}...")
    print(f"Bucket: {bucket_name}\n")

    try:
        create_bucket()
        print("\n✅ Bucket ready!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure MinIO is running:")
        print("  docker-compose up -d minio")
        exit(1)
