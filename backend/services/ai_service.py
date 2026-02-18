"""
AI Assist Service — Intelligence Flywheel

Combines semantic search over past case studies with Gemini generation
to provide contextual AI assistance for tasks.

Flow:
  1. Build search query from task title + description
  2. Search past case studies via semantic_rag
  3. Build prompt with task context + similar cases
  4. Call Gemini for a response
  5. Return response + metadata

Graceful fallback: if Gemini fails, returns similar cases without AI text.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def assist_with_task(task_data: dict, prompt: Optional[str] = None) -> dict:
    """Get AI assistance for a task using case memory context.

    Args:
        task_data: Dict with keys: id, title, status, description, notes,
                   assignee, value_stream
        prompt: Optional custom prompt from the user

    Returns:
        {"response": str, "similar_cases": int, "model": str}
    """
    title = task_data.get("title", "")
    description = task_data.get("description") or ""
    notes = task_data.get("notes") or ""
    status = task_data.get("status", "")

    # Build search query from task content
    search_query = f"{title} {description}".strip()

    # Search for similar past case studies
    similar_cases = []
    try:
        from services.semantic_rag import get_rag_service
        rag = get_rag_service()
        results = rag.search(search_query, top_k=5)
        similar_cases = [
            (entry["metadata"], score)
            for entry, score in results
            if score > 0.3  # Only include meaningfully similar cases
        ]
    except Exception as e:
        logger.warning(f"RAG search failed: {e}")

    # Build context from similar cases
    case_context = ""
    if similar_cases:
        case_context = "\n\n## Similar Past Tasks\n"
        for i, (meta, score) in enumerate(similar_cases, 1):
            case_context += f"\n### {i}. {meta.get('title', 'Untitled')} (similarity: {score:.2f})\n"
            if meta.get("description"):
                case_context += f"Description: {meta['description']}\n"
            if meta.get("notes"):
                case_context += f"Notes: {meta['notes']}\n"
            if meta.get("assignee"):
                case_context += f"Assignee: {meta['assignee']}\n"
            if meta.get("completed_at"):
                case_context += f"Completed: {meta['completed_at']}\n"

    # Build the Gemini prompt
    user_prompt = prompt or "Help me work on this task effectively."

    full_prompt = f"""You are Lotus, an AI assistant for a task management board.
A user is asking for help with the following task:

**Title:** {title}
**Status:** {status}
**Description:** {description or 'No description provided'}
**Notes:** {notes or 'No notes yet'}
{case_context}

**User's request:** {user_prompt}

Provide concise, actionable advice. If similar past tasks are provided above,
reference relevant patterns or lessons learned from them. Keep your response
focused and practical (2-4 paragraphs max)."""

    # Try Gemini generation
    try:
        from services.gemini_client import get_gemini_client
        client = get_gemini_client()

        if client.available:
            response_text = await client.generate(full_prompt, temperature=0.4, max_tokens=1024)
            return {
                "response": response_text,
                "similar_cases": len(similar_cases),
                "model": client.model_name,
            }
    except Exception as e:
        logger.error(f"Gemini generation failed: {e}")

    # Fallback: return case summary without AI generation
    if similar_cases:
        fallback = f"Found {len(similar_cases)} similar past task(s):\n\n"
        for meta, score in similar_cases:
            fallback += f"- **{meta.get('title', 'Untitled')}** (similarity: {score:.0%})\n"
            if meta.get("description"):
                fallback += f"  {meta['description'][:200]}\n"
        fallback += "\n*AI generation unavailable — showing case matches only.*"
    else:
        fallback = (
            "No similar past tasks found and AI generation is unavailable. "
            "Complete more tasks to build up the case memory, or configure "
            "a GOOGLE_API_KEY for AI-powered assistance."
        )

    return {
        "response": fallback,
        "similar_cases": len(similar_cases),
        "model": "fallback",
    }
