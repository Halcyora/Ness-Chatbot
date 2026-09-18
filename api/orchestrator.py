"""
Main orchestrator for the chatbot.

Coordinates between:
- Config loading
- Input guardrails
- Intent classification
- RAG retrieval
- Tool-calling
- LLM generation
- Output guardrails
- Caching
"""

import os
from typing import Dict, Any, Tuple, List
from datetime import datetime

from dotenv import load_dotenv

from api.config_loader import load_site_config
from api.guardrails import check_input, check_output_grounded
from api.intent_router import classify, route_message
from api.rag_retriever import RAGRetriever, call_tool
from api.llm import get_llm_provider
from api.cache import get_cached, set_cached

load_dotenv()

# Configure LangSmith for observability (optional, via environment variables)
# Set LANGSMITH_API_KEY and LANGSMITH_PROJECT to enable
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "ness-chatbot")
if LANGSMITH_API_KEY:
    os.environ["LANGSMITH_TRACING_V2"] = "true"
    import langsmith
    langsmith.configure(api_key=LANGSMITH_API_KEY, project=LANGSMITH_PROJECT)


def handle_message(site_id: str, message: str) -> Dict[str, Any]:
    """
    Handle a user message end-to-end.

    Request flow:
    1. Load config
    2. Input guardrails (block injection/PII)
    3. Check cache
    4. Intent classification
    5. Route to handler (canned/RAG/tool)
    6. Generate answer (if needed)
    7. Output guardrails
    8. Cache & return

    Args:
        site_id: Site identifier (e.g., 'ness')
        message: User message

    Returns:
        Dict with 'reply' and 'quick_replies'
    """
    start_time = datetime.utcnow()

    # Step 0: Load config
    try:
        config = load_site_config(site_id)
    except Exception as e:
        return {
            "reply": f"Configuration error: {e}",
            "quick_replies": [],
            "error": True,
        }

    # Step 1: Input guardrails
    is_safe, unsafe_reply = check_input(message)
    if not is_safe:
        return {
            "reply": unsafe_reply or config.get("error_reply", "Unable to process message."),
            "quick_replies": config.get("quick_actions", [])[:3],
        }

    # Step 2: Check cache
    cached_reply = get_cached(message)
    if cached_reply:
        return {
            "reply": cached_reply,
            "quick_replies": config.get("quick_actions", [])[:3],
            "cached": True,
        }

    # Step 3: Intent classification
    classification = classify(message, config)
    route = route_message(message, classification, config)

    # Step 4: Route to handler
    handler_type = route.get("handler")
    answer = None

    if handler_type == "canned":
        # Canned reply (no LLM call)
        answer = route.get("reply", config.get("welcome_message", ""))

    elif handler_type == "rag":
        # RAG retrieval
        query = route.get("query", message)
        retriever = RAGRetriever(site_id)
        chunks = retriever.retrieve(query, top_k=4, min_score=0.7)

        if chunks:
            # Chunks found - generate answer
            try:
                llm_provider = get_llm_provider()
                source_text = "\n".join([chunk["content"] for chunk in chunks])
                prompt = f"""Based on the following information about Ness, answer the user's question concisely:

{source_text}

User question: {query}

Answer:"""

                answer = llm_provider.generate(prompt, temperature=0.7, max_tokens=512)

                # Output guardrails - check grounding
                source_chunks = [chunk["content"] for chunk in chunks]
                if not check_output_grounded(answer, source_chunks):
                    answer = config.get(
                        "fallback_reply",
                        "I found some relevant information but couldn't formulate a confident answer. "
                        "Here's what I found: " + chunks[0]["url"]
                    )

            except Exception as e:
                answer = f"Error generating response: {e}"
        else:
            # No chunks found
            answer = config.get(
                "fallback_reply",
                "I couldn't find specific information about that. "
                "You can contact us at contact@ness.com for more details."
            )

    elif handler_type == "tool":
        # Tool-calling
        tool_name = route.get("tool_name", "")
        try:
            tool_result = call_tool(tool_name)
            if tool_result:
                # Format tool result for display
                lines = [f"Found {len(tool_result)} results:\n"]
                for item in tool_result[:5]:  # Show top 5
                    if "title" in item:
                        lines.append(f"• {item['title']}")
                        if "location" in item:
                            lines.append(f"  Location: {item['location']}")
                        elif "date" in item:
                            lines.append(f"  Date: {item['date']}")
                    if "url" in item:
                        lines.append(f"  More: {item['url']}")
                    lines.append("")

                answer = "\n".join(lines)
            else:
                answer = "No results found for that search."

        except Exception as e:
            answer = f"Error retrieving information: {e}"

    # Fallback if no answer was set
    if not answer:
        answer = config.get("error_reply", "Unable to process your request.")

    # Step 5: Cache the answer
    set_cached(message, answer)

    # Step 6: Prepare quick replies
    quick_replies = []
    for action in config.get("quick_actions", [])[:5]:
        quick_replies.append({
            "label": action.get("label", ""),
            "id": action.get("id", ""),
        })

    end_time = datetime.utcnow()

    return {
        "reply": answer,
        "quick_replies": quick_replies,
        "handler": handler_type,
        "duration_ms": (end_time - start_time).total_seconds() * 1000,
    }
