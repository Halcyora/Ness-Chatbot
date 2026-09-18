"""
RAG (Retrieval-Augmented Generation) retriever using FAISS.

Loads FAISS indices from MinIO and performs similarity search.
Returns contextual chunks for grounding LLM responses.
"""

import os
import pickle
from typing import List, Dict, Any, Optional
from datetime import datetime

import boto3
import numpy as np
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from api.llm import get_llm_provider

# Load environment
load_dotenv()

# Configuration
S3_ENDPOINT = os.getenv("AWS_ENDPOINT_URL", "http://localhost:9000")
S3_BUCKET = os.getenv("S3_BUCKET_INDEX", "ness-chatbot-index")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


class RAGRetriever:
    """Retrieves relevant chunks from FAISS index."""

    def __init__(self, site_id: str):
        """Initialize retriever for a site."""
        self.site_id = site_id
        self.index = None
        self.metadata = None
        self.chunks = None
        self.llm_provider = None
        self._load_index()

    def _get_s3_client(self):
        """Get S3 client."""
        return boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            region_name=AWS_REGION,
        )

    def _load_index(self) -> None:
        """Load FAISS index and metadata from MinIO."""
        try:
            import faiss

            s3 = self._get_s3_client()

            # Download index file
            index_key = f"{self.site_id}/index.faiss"
            try:
                response = s3.get_object(Bucket=S3_BUCKET, Key=index_key)
                index_bytes = response["Body"].read()
                self.index = faiss.deserialize_index(index_bytes)
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    # Index doesn't exist yet
                    self.index = None
                else:
                    raise

            # Download metadata file
            metadata_key = f"{self.site_id}/metadata.pkl"
            try:
                response = s3.get_object(Bucket=S3_BUCKET, Key=metadata_key)
                metadata_bytes = response["Body"].read()
                self.metadata = pickle.loads(metadata_bytes)
                self.chunks = self.metadata.get("chunks", [])
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    self.metadata = None
                    self.chunks = None
                else:
                    raise

        except ImportError:
            print("FAISS not available - RAG retrieval disabled")
            self.index = None
            self.metadata = None
            self.chunks = None

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        min_score: float = 0.75,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve top-k similar chunks for a query.

        Args:
            query: The search query
            top_k: Number of results to return
            min_score: Minimum similarity score (0-1, higher is more similar)

        Returns:
            List of chunks with scores, or None if no results meet threshold
        """
        if self.index is None or self.chunks is None:
            return None

        try:
            # Get LLM provider for query embedding
            if not self.llm_provider:
                self.llm_provider = get_llm_provider()

            # Embed the query
            query_embedding = self.llm_provider.embed([query])[0]
            query_vector = np.array([query_embedding]).astype("float32")

            # Search FAISS index
            # Note: FAISS returns distances (L2), not similarities
            # We convert: similarity = 1 / (1 + distance)
            distances, indices = self.index.search(query_vector, top_k)

            # Convert distances to similarities (0-1 range)
            similarities = 1.0 / (1.0 + distances[0])

            # Filter by minimum score
            results = []
            for idx, sim_score in zip(indices[0], similarities):
                if sim_score >= min_score:
                    chunk = self.chunks[idx]
                    results.append({
                        "content": chunk.get("content", ""),
                        "url": chunk.get("url", ""),
                        "title": chunk.get("title", ""),
                        "score": float(sim_score),
                        "chunk_index": chunk.get("chunk_index", 0),
                    })

            return results if results else None

        except Exception as e:
            print(f"Retrieval error: {e}")
            return None


# Tool-calling implementations
def get_open_positions(site_id: str = "ness") -> List[Dict[str, Any]]:
    """
    Fetch open positions from Ness careers page (mock implementation).

    In production, this would scrape ness.com/careers dynamically.

    Args:
        site_id: The site identifier

    Returns:
        List of job listings
    """
    # Mock data - in production, would fetch via requests + BeautifulSoup
    return [
        {
            "title": "Senior Software Engineer",
            "location": "Remote",
            "department": "Engineering",
            "url": "https://www.ness.com/careers/senior-engineer",
        },
        {
            "title": "Solutions Architect",
            "location": "New York, NY",
            "department": "Services",
            "url": "https://www.ness.com/careers/architect",
        },
        {
            "title": "Product Manager",
            "location": "San Francisco, CA",
            "department": "Product",
            "url": "https://www.ness.com/careers/product-manager",
        },
    ]


def get_latest_news(site_id: str = "ness") -> List[Dict[str, Any]]:
    """
    Fetch latest news/articles from Ness insights page (mock implementation).

    In production, this would scrape ness.com/insights dynamically.

    Args:
        site_id: The site identifier

    Returns:
        List of news articles
    """
    # Mock data - in production, would fetch via requests + BeautifulSoup
    return [
        {
            "title": "Digital Transformation Trends 2024",
            "date": "2024-09-15",
            "excerpt": "Exploring the latest trends in digital transformation...",
            "url": "https://www.ness.com/insights/digital-transformation-2024",
        },
        {
            "title": "Cloud Migration Best Practices",
            "date": "2024-09-10",
            "excerpt": "Key strategies for successful cloud migration projects...",
            "url": "https://www.ness.com/insights/cloud-migration-best-practices",
        },
    ]


# Registry of available tools
TOOLS = {
    "get_open_positions": get_open_positions,
    "get_latest_news": get_latest_news,
}


def call_tool(tool_name: str, **kwargs) -> Optional[List[Dict[str, Any]]]:
    """
    Call a registered tool by name.

    Args:
        tool_name: Name of the tool (e.g., 'get_open_positions')
        **kwargs: Tool arguments

    Returns:
        Tool result, or None if tool not found
    """
    tool = TOOLS.get(tool_name)
    if not tool:
        return None
    return tool(**kwargs)


if __name__ == "__main__":
    # Test tools
    print("Testing Tools...\n")

    print("1. get_open_positions():")
    positions = get_open_positions()
    for pos in positions:
        print(f"   - {pos['title']} ({pos['location']})")

    print("\n2. get_latest_news():")
    news = get_latest_news()
    for article in news:
        print(f"   - {article['title']}")

    print("\n3. Tool registry:")
    print(f"   Available tools: {list(TOOLS.keys())}")
