"""
Embedding and indexing for RAG.

Creates FAISS indices from chunked documents and uploads to MinIO/S3.
"""

import os
import sys
import io
import pickle
from typing import List, Dict, Any
from datetime import datetime

# Handle Windows Unicode output issues
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import boto3
import numpy as np
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from api.config_loader import load_site_config
from api.llm import get_llm_provider
from ingestion.chunker import chunk_documents

# Load environment
load_dotenv()

# Configuration
S3_ENDPOINT = os.getenv("AWS_ENDPOINT_URL", "http://localhost:9000")
S3_BUCKET = os.getenv("S3_BUCKET_INDEX", "ness-chatbot-index")
DYNAMODB_ENDPOINT = os.getenv("DYNAMODB_ENDPOINT_URL", "http://localhost:8000")
TABLE_NAME = os.getenv("DYNAMODB_TABLE_CANDIDATES", "page_candidates")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Chunking parameters
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# FAISS index configuration
EMBEDDING_DIMENSION = 1536  # Titan embeddings default


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


def get_s3_client():
    """Get S3 client for MinIO."""
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        region_name=AWS_REGION,
    )


def get_included_pages(site_id: str) -> List[Dict[str, Any]]:
    """Fetch all pages with status='included' from DynamoDB."""
    table = get_dynamodb_table()
    pages = []

    try:
        # Query all items for this site with status=included
        response = table.query(
            KeyConditionExpression="site_id = :site_id",
            FilterExpression="attribute_exists(#status) AND #status = :status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":site_id": site_id,
                ":status": "included",
            }
        )

        pages = response.get("Items", [])

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = table.query(
                KeyConditionExpression="site_id = :site_id",
                FilterExpression="attribute_exists(#status) AND #status = :status",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":site_id": site_id,
                    ":status": "included",
                },
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            pages.extend(response.get("Items", []))

        return pages
    except ClientError as e:
        print(f"❌ DynamoDB query error: {e}")
        raise


def embed_and_index(site_id: str) -> None:
    """
    Embed all included pages and create FAISS index.

    Uploads the index to MinIO.
    """
    print(f"\n[INDEX] Creating index for site: {site_id}")
    print("=" * 60)

    # Get LLM provider for embeddings
    try:
        llm_provider = get_llm_provider()
        print(f"Using provider: {llm_provider.provider_name}")
    except Exception as e:
        print(f"[WARN] LLM provider error (embeddings may fail): {e}")
        llm_provider = None

    # Fetch included pages
    print("\n[1] Fetching included pages...")
    pages = get_included_pages(site_id)
    print(f"   Found {len(pages)} pages to embed")

    if not pages:
        print("   [WARN] No included pages to embed!")
        return

    # Chunk documents
    print("\n[2] Chunking documents...")
    chunks = chunk_documents(pages, CHUNK_SIZE, CHUNK_OVERLAP)
    print(f"   Created {len(chunks)} chunks from {len(pages)} pages")

    if not chunks:
        print("   [WARN] No chunks produced (pages have no content) - skipping embedding")
        return

    # Create embeddings (optional - mock if LLM unavailable)
    print("\n[3] Generating embeddings...")

    if llm_provider:
        try:
            # Extract chunk content for embedding
            chunk_texts = [chunk["content"] for chunk in chunks]

            # Embed in batches (to avoid token limits)
            embeddings = []
            batch_size = 10

            for i in range(0, len(chunk_texts), batch_size):
                batch = chunk_texts[i : i + batch_size]
                try:
                    batch_embeddings = llm_provider.embed(batch)
                    embeddings.extend(batch_embeddings)
                    print(f"   [OK] Embedded batch {i // batch_size + 1}/{(len(chunk_texts) + batch_size - 1) // batch_size}")
                except Exception as e:
                    print(f"   [WARN] Embedding batch error: {e}")
                    # Fall back to dummy embeddings for testing
                    embeddings.extend([[0.0] * EMBEDDING_DIMENSION for _ in batch])

        except Exception as e:
            print(f"   [WARN] Embedding error (using dummy embeddings): {e}")
            embeddings = [[0.0] * EMBEDDING_DIMENSION for _ in chunks]
    else:
        print("   [WARN] No LLM provider, using dummy embeddings")
        embeddings = [[0.0] * EMBEDDING_DIMENSION for _ in chunks]

    # Create FAISS index
    print("\n[4] Creating FAISS index...")
    try:
        import faiss

        # Convert embeddings to numpy array
        embeddings_array = np.array(embeddings).astype("float32")
        print(f"   Embeddings shape: {embeddings_array.shape}")

        # L2-normalize so inner product == cosine similarity (0.75 threshold assumes cosine similarity,
        # not raw L2 distance which is unbounded and makes any fixed threshold meaningless)
        norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        embeddings_array = embeddings_array / norms

        # Create FAISS index (inner product on normalized vectors = cosine similarity)
        dimension = embeddings_array.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings_array)

        print(f"   [OK] FAISS index created with {index.ntotal} vectors")

        # Prepare metadata
        metadata = {
            "site_id": site_id,
            "created_at": datetime.utcnow().isoformat(),
            "chunk_count": len(chunks),
            "page_count": len(pages),
            "chunks": chunks,  # Store chunk metadata
        }

        # Upload to MinIO
        print("\n[5] Uploading to MinIO...")
        s3_client = get_s3_client()

        # Upload FAISS index
        index_key = f"{site_id}/index.faiss"
        # faiss.serialize_index returns a numpy uint8 array in this version - S3 needs raw bytes
        index_bytes = faiss.serialize_index(index).tobytes()
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=index_key,
            Body=index_bytes,
        )
        print(f"   [OK] Uploaded FAISS index to s3://{S3_BUCKET}/{index_key}")

        # Upload metadata/chunk info
        metadata_key = f"{site_id}/metadata.pkl"
        metadata_bytes = pickle.dumps(metadata)
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=metadata_key,
            Body=metadata_bytes,
        )
        print(f"   [OK] Uploaded metadata to s3://{S3_BUCKET}/{metadata_key}")

        print(f"\n{'=' * 60}")
        print(f"[OK] Index creation complete!")
        print(f"   Site: {site_id}")
        print(f"   Pages: {len(pages)}")
        print(f"   Chunks: {len(chunks)}")
        print(f"   Vectors: {index.ntotal}")

    except ImportError:
        print("[ERROR] FAISS not installed. Install with: pip install faiss-cpu")
        raise
    except Exception as e:
        print(f"[ERROR] Error creating index: {e}")
        raise


if __name__ == "__main__":
    import sys
    site_id = sys.argv[1] if len(sys.argv) > 1 else "ness"
    try:
        embed_and_index(site_id)
    except Exception as e:
        print(f"\\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
