"""
RAG (Retrieval-Augmented Generation) retriever using FAISS.

Loads FAISS indices from MinIO and performs similarity search.
Returns contextual chunks for grounding LLM responses.
"""

import os
import pickle
import re
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

import boto3
import numpy as np
import requests
from botocore.exceptions import ClientError, EndpointConnectionError
from dotenv import load_dotenv

from api.config_loader import load_site_config
from api.llm import get_llm_provider

# Load environment
load_dotenv()

# Configuration
S3_ENDPOINT = os.getenv("AWS_ENDPOINT_URL", "http://localhost:9000")
S3_BUCKET = os.getenv("S3_BUCKET_INDEX", "ness-chatbot-index")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Cache live tool-calling fetches (ATS jobs, news fragments) in-process to avoid hitting providers on every message
_LIVE_FETCH_CACHE_TTL = 600  # seconds
_live_fetch_cache: Dict[str, tuple] = {}  # cache key -> (fetched_at, data)


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
                # deserialize_index expects a numpy uint8 array, not raw bytes
                index_array = np.frombuffer(index_bytes, dtype=np.uint8)
                self.index = faiss.deserialize_index(index_array)
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
        except EndpointConnectionError:
            # MinIO/S3 not reachable (e.g. local infra not started) - degrade gracefully
            print("S3/MinIO endpoint unreachable - RAG retrieval disabled")
            self.index = None
            self.metadata = None
            self.chunks = None

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        min_score: float = 0.5,
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

            # L2-normalize to match the normalized vectors stored in the index (see embedder.py)
            norm = np.linalg.norm(query_vector, axis=1, keepdims=True)
            norm[norm == 0] = 1e-10
            query_vector = query_vector / norm

            # Search FAISS index (IndexFlatIP on normalized vectors returns cosine similarity directly)
            similarities, indices = self.index.search(query_vector, top_k)
            similarities = similarities[0]

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


# Maps a phrase/code found anywhere in a location string to additional country-level search aliases
_COUNTRY_ALIASES = {
    "united states": ["us", "usa", "america"],
    ", ny": ["us", "usa", "united states", "america"],
    ", ca": ["us", "usa", "united states", "america"],
    "united kingdom": ["uk", "britain", "england"],
    ", uk": ["uk", "united kingdom", "britain", "england"],
}


def _location_search_terms(location: str) -> List[str]:
    """Build the set of words/phrases that should match a given location string."""
    location_lower = location.lower()
    parts = [p for p in re.split(r"[,\s]+", location_lower) if len(p) > 2]

    terms = list(parts)
    for marker, aliases in _COUNTRY_ALIASES.items():
        if marker in location_lower:
            terms.extend(aliases)
    return terms


def _filter_by_location(items: List[Dict[str, Any]], message: str) -> List[Dict[str, Any]]:
    """Filter items whose 'location' (city, state/country code, or country alias) is mentioned in the
    user's message; falls back to all items if none match."""
    if not message:
        return items

    msg_lower = message.lower()
    filtered = []
    for item in items:
        terms = _location_search_terms(item.get("location", ""))
        if any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", msg_lower) for term in terms):
            filtered.append(item)
    return filtered if filtered else items


# Cache embeddings for the current job title snapshot, refreshed alongside the job list
_job_embedding_cache: Dict[str, tuple] = {}  # cache_key -> (fetched_at, embeddings ndarray, titles used)


def _job_search_text(position: Dict[str, Any]) -> str:
    return f"{position.get('title', '')} - {position.get('location', '')}"


def _get_job_title_embeddings(cache_key: str, positions: List[Dict[str, Any]]) -> Optional[np.ndarray]:
    """Compute (and cache) embeddings for job titles, recomputed whenever the underlying job list changes."""
    titles = [_job_search_text(p) for p in positions]
    now = time.time()
    cached = _job_embedding_cache.get(cache_key)
    if cached and (now - cached[0]) < _LIVE_FETCH_CACHE_TTL and cached[2] == titles:
        return cached[1]

    try:
        llm_provider = get_llm_provider()
        embeddings = np.array(llm_provider.embed(titles), dtype="float32")
        _job_embedding_cache[cache_key] = (now, embeddings, titles)
        return embeddings
    except Exception as e:
        print(f"Job title embedding failed: {e}")
        return None


def _semantic_rank_positions(
    positions: List[Dict[str, Any]],
    message: str,
    cache_key: str,
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    """
    Re-rank (never drop) open positions by semantic similarity between the user's message and each job
    title/location, so free-text role queries (e.g. "engineering roles") surface the most relevant jobs
    first even when they don't share exact keywords. Skipped for small result sets since there's nothing
    to re-rank once everything already fits on screen.
    """
    if not message or len(positions) <= top_n:
        return positions

    embeddings = _get_job_title_embeddings(cache_key, positions)
    if embeddings is None:
        return positions

    try:
        llm_provider = get_llm_provider()
        query_vec = np.array(llm_provider.embed([message])[0], dtype="float32")

        query_norm = query_vec / (np.linalg.norm(query_vec) or 1e-10)
        title_norms = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-10)
        similarities = title_norms @ query_norm

        ranked_indices = np.argsort(-similarities)
        return [positions[i] for i in ranked_indices]
    except Exception as e:
        print(f"Semantic ranking failed, keeping original order: {e}")
        return positions


def _fetch_greenhouse_jobs(board_token: str) -> Optional[List[Dict[str, Any]]]:
    """Fetch live open positions from Greenhouse's public job board API, with a short-lived cache."""
    cached = _live_fetch_cache.get(board_token)
    if cached and (time.time() - cached[0]) < _LIVE_FETCH_CACHE_TTL:
        return cached[1]

    try:
        resp = requests.get(
            f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs",
            timeout=8,
        )
        resp.raise_for_status()
        jobs = [
            {
                "title": job.get("title", "").strip(),
                "location": job.get("location", {}).get("name", "").strip(),
                "department": "",
                "url": job.get("absolute_url", ""),
            }
            for job in resp.json().get("jobs", [])
        ]
        _live_fetch_cache[board_token] = (time.time(), jobs)
        return jobs
    except Exception as e:
        print(f"Greenhouse jobs fetch failed for board '{board_token}': {e}")
        return None


def _fetch_live_positions(site_id: str) -> Optional[List[Dict[str, Any]]]:
    """Fetch live open positions using the ATS configured for this site (see dynamic_pages.careers.ats)."""
    try:
        config = load_site_config(site_id)
    except Exception:
        return None

    ats = config.get("dynamic_pages", {}).get("careers", {}).get("ats", {})
    if ats.get("provider") == "greenhouse" and ats.get("board_token"):
        return _fetch_greenhouse_jobs(ats["board_token"])
    return None


def _fetch_aem_articles(source_cfg: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Fetch and parse a live AEM insights/news fragment (see dynamic_pages.news.source), with a short-lived cache."""
    url = source_cfg.get("url")
    if not url:
        return None

    cached = _live_fetch_cache.get(url)
    if cached and (time.time() - cached[0]) < _LIVE_FETCH_CACHE_TTL:
        return cached[1]

    try:
        from bs4 import BeautifulSoup

        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        base_url = source_cfg.get("base_url", "")
        articles = []
        for link in soup.select(source_cfg.get("item_selector", "a")):
            title_el = link.select_one(source_cfg.get("title_selector", ""))
            if not title_el:
                continue
            date_el = link.select_one(source_cfg.get("date_selector", ""))
            href = link.get("href", "")
            articles.append({
                "title": title_el.get_text(strip=True),
                "date": date_el.get_text(strip=True) if date_el else "",
                "url": href if href.startswith("http") else f"{base_url}{href}",
            })
        if articles:
            _live_fetch_cache[url] = (time.time(), articles)
        return articles or None
    except Exception as e:
        print(f"AEM news fetch failed for {url}: {e}")
        return None


def _fetch_live_news(site_id: str) -> Optional[List[Dict[str, Any]]]:
    """Fetch live news/insights using the source configured for this site (see dynamic_pages.news.source)."""
    try:
        config = load_site_config(site_id)
    except Exception:
        return None

    source = config.get("dynamic_pages", {}).get("news", {}).get("source", {})
    if source.get("type") == "aem_fragment":
        return _fetch_aem_articles(source)
    return None


# Tool-calling implementations
def get_open_positions(site_id: str = "kkr", message: str = "") -> List[Dict[str, Any]]:
    """
    Fetch live open positions using the site's configured ATS (see dynamic_pages.careers.ats).

    Results are narrowed by any mentioned location (keyword/alias match), then semantically
    re-ranked against the full message so free-text role queries surface the most relevant jobs first.

    Args:
        site_id: The site identifier (kkr, ness, etc.)
        message: Original user message, used to filter/rank results

    Returns:
        List of job listings (empty if no ATS is configured or the live fetch fails)
    """
    positions = _fetch_live_positions(site_id) or []
    positions = _filter_by_location(positions, message)
    positions = _semantic_rank_positions(positions, message, cache_key=f"{site_id}:positions")
    return positions


def get_latest_news(site_id: str = "kkr", message: str = "") -> List[Dict[str, Any]]:
    """
    Fetch live news/articles using the site's configured news source (see dynamic_pages.news.source).

    Args:
        site_id: The site identifier (kkr, ness, etc.)
        message: Original user message (unused for news, kept for a consistent tool signature)

    Returns:
        List of news articles (empty if no source is configured or the live fetch fails)
    """
    return _fetch_live_news(site_id) or []


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
