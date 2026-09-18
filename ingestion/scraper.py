"""
Web scraper for discovering and extracting page content.

Crawls sitemap URLs, extracts title and body text, and stores results in DynamoDB.
"""

import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from api.config_loader import load_site_config

# Load environment
load_dotenv()

# Configuration
DYNAMODB_ENDPOINT = os.getenv("DYNAMODB_ENDPOINT_URL", "http://localhost:8000")
TABLE_NAME = os.getenv("DYNAMODB_TABLE_CANDIDATES", "page_candidates")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Request settings
REQUEST_TIMEOUT = 10
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Markers that indicate the response is an anti-bot/CAPTCHA challenge page,
# not real content - seen on sites fronted by bot-protection (e.g. sgcaptcha, Cloudflare)
_CHALLENGE_MARKERS = ("sgcaptcha", "captcha", "cf-challenge", "checking your browser")

# Fallback to a real headless browser when plain requests gets blocked/JS-rendered content
USE_PLAYWRIGHT_FALLBACK = os.getenv("SCRAPER_USE_PLAYWRIGHT_FALLBACK", "true").lower() == "true"
PLAYWRIGHT_TIMEOUT_MS = 20000


def _get_session() -> requests.Session:
    """Shared session so cookies persist across requests to the same site."""
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)
    return session


def is_challenge_page(html: str) -> bool:
    """Detect anti-bot/CAPTCHA challenge pages so we don't index them as real content."""
    lower = html.lower()
    if any(marker in lower for marker in _CHALLENGE_MARKERS):
        return True
    # Real pages have far more markup than a bare challenge stub
    if len(html.strip()) < 500 and "<title>" not in lower:
        return True
    return False


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


def extract_text(html: str) -> str:
    """
    Extract visible text from HTML.

    Removes scripts, styles, and other non-visible elements.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Get text
    text = soup.get_text()

    # Break into lines and remove leading/trailing space
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = " ".join(chunk for chunk in chunks if chunk)

    return text.strip()


def extract_title(html: str) -> str:
    """Extract page title from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text().strip()
    return ""


def is_valid_url(url: str, base_url: str) -> bool:
    """Check if URL is valid and on the same domain."""
    try:
        parsed = urlparse(url)
        base_parsed = urlparse(base_url)

        # Check domain match
        if parsed.netloc and parsed.netloc != base_parsed.netloc:
            return False

        # Exclude certain file types
        excluded_extensions = [".pdf", ".zip", ".exe", ".jpg", ".png", ".gif", ".css", ".js"]
        if any(url.lower().endswith(ext) for ext in excluded_extensions):
            return False

        return True
    except Exception:
        return False


def get_page_urls(base_url: str, html: str) -> List[str]:
    """Extract all links from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    urls = []

    for link in soup.find_all("a", href=True):
        href = link["href"]
        # Convert relative URLs to absolute
        absolute_url = urljoin(base_url, href)

        # Remove fragment
        absolute_url = absolute_url.split("#")[0]

        if is_valid_url(absolute_url, base_url):
            urls.append(absolute_url)

    return list(set(urls))  # Remove duplicates


def fetch_page_with_playwright(url: str) -> Optional[Dict[str, str]]:
    """
    Fetch a page using a real headless browser (Playwright/Chromium).

    Used as a fallback when plain requests hits a challenge page or JS-only
    content. Not a bypass for IP-level bot blocks - only helps for genuinely
    JS-rendered pages or lightweight browser-fingerprint checks.

    Runs in a dedicated worker thread because Playwright's Sync API refuses
    to run on a thread that already has an asyncio event loop (e.g. FastAPI's
    request-handling thread).
    """
    try:
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(_fetch_with_playwright_sync, url).result()
    except Exception as e:
        print(f"  \u26a0\ufe0f  Playwright fetch failed for {url}: {e}")
        return None


def _fetch_with_playwright_sync(url: str) -> Optional[Dict[str, str]]:
    """Actual Playwright Sync API call - must run on a thread with no asyncio event loop."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  \u26a0\ufe0f  Playwright not installed - skipping browser fallback")
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=REQUEST_HEADERS["User-Agent"])
            page.goto(url, timeout=PLAYWRIGHT_TIMEOUT_MS, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            html = page.content()
            browser.close()

        if is_challenge_page(html):
            print(f"  \U0001F6AB Still blocked after browser render: {url}")
            return None

        return {
            "title": extract_title(html),
            "content": extract_text(html),
            "html": html,
        }
    except Exception as e:
        print(f"  \u26a0\ufe0f  Playwright fetch failed for {url}: {e}")
        return None


def fetch_page(url: str, session: Optional[requests.Session] = None) -> Optional[Dict[str, str]]:
    """Fetch a page and extract title and content."""
    try:
        http = session or requests
        response = http.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers=REQUEST_HEADERS if session is None else None,
        )
        response.raise_for_status()

        if is_challenge_page(response.text):
            print(f"  \U0001F6AB Blocked by anti-bot/CAPTCHA challenge: {url}")
            if USE_PLAYWRIGHT_FALLBACK:
                print("  \U0001F504 Retrying with headless browser (Playwright)...")
                return fetch_page_with_playwright(url)
            return None

        title = extract_title(response.text)
        content = extract_text(response.text)

        return {
            "title": title,
            "content": content,
            "html": response.text,
        }
    except requests.RequestException as e:
        print(f"  ⚠️  Failed to fetch {url}: {e}")
        if USE_PLAYWRIGHT_FALLBACK:
            print("  \U0001F504 Retrying with headless browser (Playwright)...")
            return fetch_page_with_playwright(url)
        return None


def upsert_page_candidate(
    table,
    site_id: str,
    url: str,
    title: str,
    content: str,
) -> None:
    """
    Insert or update a page candidate in DynamoDB.

    If the page already exists and status is 'included' or 'excluded',
    only update the content and last_scraped timestamp.
    """
    try:
        # First, try to get the existing item to check status
        response = table.get_item(
            Key={"site_id": site_id, "url": url}
        )

        existing_item = response.get("Item")

        if existing_item:
            # If status is pending, we keep it (don't override to pending)
            # If status is included/excluded, we preserve it
            status = existing_item.get("status", "pending")
        else:
            status = "pending"

        # Update the item
        table.put_item(
            Item={
                "site_id": site_id,
                "url": url,
                "title": title,
                "content": content,
                "status": status,
                "last_scraped": datetime.utcnow().isoformat() + "Z",
            }
        )
    except ClientError as e:
        print(f"  ❌ DynamoDB error for {url}: {e}")
        raise


def discover_pages(site_id: str) -> List[Dict[str, Any]]:
    """
    Discover pages by crawling sitemap seeds.

    Returns a list of discovered pages with their metadata.
    """
    print(f"\n🔍 Discovering pages for site: {site_id}")
    print("=" * 60)

    # Load site config
    config = load_site_config(site_id)
    base_url = config["base_url"]
    sitemap_seeds = config["sitemap_seeds"]
    dynamic_pages = config["dynamic_pages"]

    # Filter out dynamic page URLs (these should never be embedded)
    dynamic_urls = {page["url"] for page in dynamic_pages.values()}
    filtered_seeds = [
        urljoin(base_url, seed) if seed.startswith("/") else seed
        for seed in sitemap_seeds
        if seed not in dynamic_urls
    ]

    # Get DynamoDB table
    table = get_dynamodb_table()
    discovered = []
    visited = set()
    session = _get_session()

    # BFS crawl from seed URLs
    to_visit = filtered_seeds.copy()
    max_pages = 100  # Safety limit

    while to_visit and len(discovered) < max_pages:
        url = to_visit.pop(0)

        # Avoid duplicates and already visited
        if url in visited:
            continue

        visited.add(url)
        print(f"\n📄 Fetching: {url}")

        # Fetch page
        page_data = fetch_page(url, session=session)
        if not page_data:
            continue

        title = page_data["title"]
        content = page_data["content"]

        # Store in DynamoDB
        try:
            upsert_page_candidate(table, site_id, url, title, content)
            discovered.append({
                "url": url,
                "title": title,
                "content_length": len(content),
            })
            print(f"   ✅ Indexed: {title} ({len(content)} chars)")
        except Exception as e:
            print(f"   ❌ Error storing page: {e}")
            continue

        # Extract links for further crawling (BFS) - reuse the HTML already fetched
        new_urls = get_page_urls(base_url, page_data["html"])
        for new_url in new_urls:
            if new_url not in visited and len(discovered) < max_pages:
                to_visit.append(new_url)

        # Rate limiting
        time.sleep(0.5)

    print(f"\n{'=' * 60}")
    print(f"✅ Discovery complete: {len(discovered)} pages indexed")
    return discovered


if __name__ == "__main__":
    try:
        discover_pages("ness")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
