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
from api.session_memory import get_history, append_turn

load_dotenv()

# Configure LangSmith for observability (optional, via environment variables)
# Set LANGSMITH_API_KEY and LANGSMITH_PROJECT to enable
# LangChain/LangSmith read tracing config from env vars directly - no explicit configure() call needed
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "ness-chatbot")
if LANGSMITH_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT


def handle_message(site_id: str, message: str, session_id: str = "") -> Dict[str, Any]:
    """
    Handle a user message end-to-end.

    Request flow:
    1. Load config
    2. Input guardrails (block injection/PII)
    3. Check cache
    4. Intent classification
    5. Route to handler (canned/RAG/tool), using recent session history for follow-ups
    6. Generate answer (if needed)
    7. Output guardrails
    8. Cache, persist turn to session history & return

    Args:
        site_id: Site identifier (e.g., 'ness')
        message: User message
        session_id: Client-generated id used to look up recent conversation turns

    Returns:
        Dict with 'reply' and 'quick_replies'
    """
    start_time = datetime.utcnow()
    history = get_history(session_id) if session_id else []

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
    is_safe, unsafe_reply = check_input(message, site_id=site_id)
    if not is_safe:
        return {
            "reply": unsafe_reply or config.get("error_reply", "Unable to process message."),
            "quick_replies": config.get("quick_actions", [])[:3],
            "trace": {"handler": "blocked", "reason": "input_guardrail"},
        }

    # Step 2: Check cache
    # Note: Caching works for all message types. If a user asks the same question
    # multiple times (even in the same session), they should get the cached answer.
    # Contextual follow-ups are handled through conversation history anyway.
    cached_reply = get_cached(message)
    if cached_reply:
        return {
            "reply": cached_reply,
            "quick_replies": config.get("quick_actions", [])[:3],
            "cached": True,
            "trace": {"handler": "cache", "cached": True},
        }

    # Step 3: Intent classification
    classification = classify(message, config)
    route = route_message(message, classification, config, history=history)

    # Step 4: Route to handler
    handler_type = route.get("handler")
    answer = None
    trace: Dict[str, Any] = {
        "cached": False,
        "classification": classification,
        "handler": handler_type,
    }

    if handler_type == "canned":
        # Canned reply (no LLM call)
        answer = route.get("reply", config.get("welcome_message", ""))
        trace["llm_used"] = False

    elif handler_type == "rag":
        # RAG retrieval - augment with the last user turn so follow-up questions
        # (e.g. "what about that?") retrieve relevant chunks too
        query = route.get("query", message)
        last_user_turn = next((t["content"] for t in reversed(history) if t.get("role") == "user"), "")
        retrieval_query = f"{last_user_turn} {query}".strip() if last_user_turn else query

        retriever = RAGRetriever(site_id)
        chunks = retriever.retrieve(retrieval_query, top_k=4, min_score=0.5)

        trace["rag"] = {
            "query": query,
            "chunks_found": len(chunks) if chunks else 0,
            "scores": [round(chunk["score"], 3) for chunk in chunks] if chunks else [],
            "sources": [chunk["url"] for chunk in chunks] if chunks else [],
        }

        if chunks:
            # Chunks found - generate answer
            try:
                llm_provider = get_llm_provider()
                trace["llm_used"] = True
                trace["llm_model"] = getattr(llm_provider, "model_id", "unknown")
                source_text = "\n".join([chunk["content"] for chunk in chunks])
                # Determine company name from config
                company_name = config.get("branding", {}).get("name", "the company")

                conversation_context = ""
                if history:
                    recent = "\n".join(
                        f"{'User' if t['role'] == 'user' else 'Assistant'}: {t['content']}"
                        for t in history[-4:]
                    )
                    conversation_context = f"\nPrevious conversation (for context only):\n{recent}\n"

                prompt = f"""Based on the following information about {company_name}, answer the user's question concisely:
{conversation_context}
{source_text}

User question: {query}

Answer:"""

                answer = llm_provider.generate(prompt, temperature=0.7, max_tokens=512)

                # Output guardrails - check grounding
                source_chunks = [chunk["content"] for chunk in chunks]
                grounded = check_output_grounded(answer, source_chunks)
                trace["grounded"] = grounded
                if not grounded:
                    answer = config.get(
                        "fallback_reply",
                        "I found some relevant information but couldn't formulate a confident answer. "
                        "Here's what I found: " + chunks[0]["url"]
                    )
                    trace["grounding_fallback_used"] = True

            except Exception as e:
                answer = f"Error generating response: {e}"
                trace["error"] = str(e)
        else:
            # No chunks found
            trace["llm_used"] = False
            company_name = config.get("branding", {}).get("name", "us")
            fallback_email = f"info@{config.get('site_id', 'ness')}.com"
            default_fallback = (
                f"I couldn't find specific information about that. "
                f"You can contact us at {fallback_email} for more details."
            )
            answer = config.get("fallback_reply", default_fallback)

    elif handler_type == "tool":
        # Tool-calling
        tool_name = route.get("tool_name", "")
        trace["llm_used"] = False
        trace["tool"] = {"name": tool_name}
        try:
            tool_result = call_tool(tool_name, site_id=site_id, message=message)
            trace["tool"]["result_count"] = len(tool_result) if tool_result else 0
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
            trace["error"] = str(e)

    # Fallback if no answer was set
    if not answer:
        answer = config.get("error_reply", "Unable to process your request.")

    # Step 5: Cache the answer
    set_cached(message, answer)

    # Step 6: Persist this turn so follow-up questions have context
    if session_id:
        append_turn(session_id, message, answer)
        trace["history_turns_used"] = len(history)

    # Step 7: Prepare quick replies
    quick_replies = []
    for action in config.get("quick_actions", [])[:5]:
        quick_replies.append({
            "label": action.get("label", ""),
            "id": action.get("id", ""),
        })

    end_time = datetime.utcnow()
    duration_ms = (end_time - start_time).total_seconds() * 1000
    trace["duration_ms"] = round(duration_ms, 2)

    return {
        "reply": answer,
        "quick_replies": quick_replies,
        "handler": handler_type,
        "duration_ms": duration_ms,
        "trace": trace,
    }
