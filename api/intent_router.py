"""
Intent classification for routing user messages.

Classifies messages into:
- greeting: Friendly opening messages
- stable: Questions about stable content (use RAG)
- dynamic: Questions about dynamic content (use tool-calling)
- off_topic: Messages unrelated to Ness
"""

import re
from typing import Dict, Any, Literal, List
from api.config_loader import load_site_config


def _keyword_matches(keyword: str, message_lower: str) -> bool:
    """Match keyword as whole word(s) (allowing a trailing plural 's'), not as a substring of another word."""
    pattern = r"(?<!\w)" + re.escape(keyword.lower()) + r"s?(?!\w)"
    return re.search(pattern, message_lower) is not None


def classify(message: str, site_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify user intent using heuristics (no LLM calls for cost efficiency).

    Classification order:
    1. Check greeting keywords → greeting
    2. Check dynamic page trigger keywords → dynamic
    3. Default → stable

    Args:
        message: User message to classify
        site_config: Site configuration (loaded via config_loader)

    Returns:
        Dict with 'type' and optional category info
        Example: {"type": "dynamic", "category": "careers"}
    """
    if not message or not message.strip():
        return {"type": "stable"}

    message_lower = message.lower()

    # Step 1: Check greeting keywords
    greeting_keywords = site_config.get("greeting_keywords", [])
    for keyword in greeting_keywords:
        if _keyword_matches(keyword, message_lower):
            return {"type": "greeting"}

    # Step 2: Check dynamic page trigger keywords
    dynamic_pages = site_config.get("dynamic_pages", {})
    for category, page_config in dynamic_pages.items():
        trigger_keywords = page_config.get("trigger_keywords", [])
        for keyword in trigger_keywords:
            if _keyword_matches(keyword, message_lower):
                return {
                    "type": "dynamic",
                    "category": category,
                    "url": page_config.get("url", ""),
                    "selector": page_config.get("selector", ""),
                }

    # Step 3: Default to stable (RAG query)
    return {"type": "stable"}


def _is_follow_up_refinement(message: str) -> bool:
    """
    Detect if a message is a contextual follow-up/refinement of previous results.
    
    True follow-ups have multiple context-dependent indicators:
    - "Tell me more about the first one"
    - "Which of those is the best?"
    - "What about that?" (referential)
    - "Only show Flash Macro articles"
    
    NOT follow-ups (should go to tool):
    - "Show job openings"
    - "Tell me about careers"
    
    The key: follow-ups reference previous results with words like "that", "those", "first",
    or explicitly ask for refinements with "more", "only", "filter", etc.
    """
    message_lower = message.lower()
    
    # Strong follow-up indicators (contextual references + refinement keywords)
    strong_patterns = [
        r"\b(more|tell me more|what about|which|filter|narrow|specific)\b.*\b(that|those|these|first|second|last|one|ones|it|them)\b",
        r"\bonly\b",
        r"\b(what about that|what about those|tell me more about the|which one)\b",
    ]
    
    for pattern in strong_patterns:
        if re.search(pattern, message_lower):
            return True
    
    return False


def route_message(
    message: str,
    classification: Dict[str, Any],
    site_config: Dict[str, Any],
    history: List[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Route a message to the appropriate handler based on classification.

    Special handling: If a message is a contextual follow-up (e.g., "tell me more
    about the first one", "only show flash macro news"), route to RAG instead of
    re-running the tool. RAG will use conversation history for context.

    Args:
        message: Original user message
        classification: Classification result from classify()
        site_config: Site configuration
        history: Conversation history (to detect if this is truly a follow-up)

    Returns:
        Routing instruction with handler and parameters
    """
    msg_type = classification.get("type", "stable")
    
    # If this is classified as dynamic but looks like a contextual follow-up
    # (with conversation history), route to RAG instead so it can use context
    if msg_type == "dynamic" and history and _is_follow_up_refinement(message):
        return {
            "handler": "rag",
            "query": message,
        }

    if msg_type == "greeting":
        return {
            "handler": "canned",
            "reply": site_config.get("welcome_message", "Hello! How can I help?"),
        }

    elif msg_type == "dynamic":
        category = classification.get("category")
        # Maps a dynamic_pages category (from site config) to its registered tool name
        category_to_tool = {
            "careers": "get_open_positions",
            "news": "get_latest_news",
        }
        return {
            "handler": "tool",
            "tool_name": category_to_tool.get(category, f"get_{category}"),
            "tool_config": {
                "url": classification.get("url", ""),
                "selector": classification.get("selector", ""),
                "category": category,
            },
        }

    else:  # stable (default)
        return {
            "handler": "rag",
            "query": message,  # Use the user's message as the RAG query
        }


# Test/example usage
if __name__ == "__main__":
    from api.config_loader import load_site_config

    print("Testing Intent Router...\n")

    config = load_site_config("ness")

    test_messages = [
        "Hello!",
        "Hi there",
        "What are your services?",
        "Are there any open positions?",
        "Tell me about careers",
        "What's the latest news?",
        "Are you hiring?",
    ]

    for msg in test_messages:
        classification = classify(msg, config)
        routing = route_message(msg, classification, config, history=None)
        print(f"Message: {msg}")
        print(f"  Classification: {classification}")
        print(f"  Routing: {routing['handler']}")
        print()
