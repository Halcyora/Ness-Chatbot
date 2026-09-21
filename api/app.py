"""
FastAPI application for Ness Chatbot API.

Exposes:
- POST /session/start - Initialize chat session
- POST /message - Send user message
- Admin routes for page management
"""

import os
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Header, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from api.orchestrator import handle_message
from api.config_loader import load_site_config
from api.cache import clear_all_cache
from api.session_memory import clear_session
from api.rate_limiter import check_rate_limit
from api.admin_pages import (
    list_candidates,
    set_page_status,
    trigger_refresh,
    trigger_embed,
)

load_dotenv()

# FastAPI app setup
app = FastAPI(title="Ness Chatbot API", version="0.1.0")

# CORS (for frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "dev-secret-key-change-in-prod")


# Pydantic models
class StartSessionRequest(BaseModel):
    site_id: str = "ness"


class MessageRequest(BaseModel):
    site_id: str = "ness"
    message: str
    session_id: str = ""


class SetPageStatusRequest(BaseModel):
    url: str
    status: str  # "included", "excluded", "pending"


class ClearCacheRequest(BaseModel):
    session_id: str = ""


# Utility functions
def verify_admin_key(x_admin_key: Optional[str] = Header(None)) -> None:
    """Verify admin API key."""
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


# Routes
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/session/start")
async def start_session(request: StartSessionRequest) -> Dict[str, Any]:
    """
    Start a new chat session.

    Returns welcome message and quick-action buttons.
    """
    try:
        config = load_site_config(request.site_id)
        return {
            "welcome_message": config.get("welcome_message", "Hello!"),
            "quick_actions": config.get("quick_actions", []),
            "branding": config.get("branding", {}),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/message")
async def send_message(request: MessageRequest, http_request: Request) -> Dict[str, Any]:
    """
    Send a user message and get a response.

    Handles the full orchestration pipeline. Passing the same session_id across
    calls lets the bot resolve follow-up questions using recent conversation turns.
    """
    client_id = http_request.client.host if http_request.client else "unknown"
    allowed, reason, retry_after = check_rate_limit(client_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=reason,
            headers={"Retry-After": str(retry_after)},
        )

    try:
        response = handle_message(request.site_id, request.message, session_id=request.session_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/clear-cache")
async def clear_cache(request: ClearCacheRequest = ClearCacheRequest()) -> Dict[str, Any]:
    """
    Clear all cached responses and, if provided, the session's conversation memory.

    Exposed to the chat widget so users can force fresh answers / start over.
    """
    try:
        deleted_count = clear_all_cache()
        if request.session_id:
            clear_session(request.session_id)
        return {"cleared": True, "deleted_count": deleted_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Admin routes (require API key)
@app.get("/admin/pages")
async def get_pages(
    site_id: str = "ness",
    x_admin_key: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    List all page candidates for a site.

    Requires X-Admin-Key header.
    """
    verify_admin_key(x_admin_key)

    try:
        candidates = list_candidates(site_id)
        return {
            "site_id": site_id,
            "count": len(candidates),
            "pages": candidates,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/admin/pages/{page_url:path}")
async def update_page_status(
    page_url: str,
    request: SetPageStatusRequest,
    site_id: str = "ness",
    x_admin_key: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    Update the status of a page.

    Requires X-Admin-Key header.
    """
    verify_admin_key(x_admin_key)

    try:
        set_page_status(site_id, page_url, request.status)
        return {
            "site_id": site_id,
            "url": page_url,
            "status": request.status,
            "updated": True,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/admin/refresh")
async def refresh_pages(
    site_id: str = "ness",
    x_admin_key: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    Trigger page discovery (scraping).

    Requires X-Admin-Key header.
    """
    verify_admin_key(x_admin_key)

    try:
        discovered = trigger_refresh(site_id)
        return {
            "site_id": site_id,
            "action": "refresh",
            "discovered_count": len(discovered),
            "discovered_pages": discovered,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/admin/embed")
async def trigger_embedding(
    site_id: str = "ness",
    x_admin_key: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    Trigger embedding of included pages.

    Requires X-Admin-Key header.
    """
    verify_admin_key(x_admin_key)

    try:
        result = trigger_embed(site_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("SERVER_PORT", 8080))
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
