"""
Email Classification Agent - Phase 5

LangGraph agent for intelligent email classification using Gemini.

Classifies emails into actionable/FYI/automated categories with confidence scoring.
Uses structured output for reliable parsing.
"""

import logging
from typing import TypedDict, Dict, Any, Optional
from datetime import datetime

from langgraph.graph import StateGraph, END

from services.gemini_client import get_gemini_client
from config.email_prompts import (
    EMAIL_CLASSIFICATION_SYSTEM_PROMPT,
    get_email_classification_prompt,
    EmailClassification
)

logger = logging.getLogger(__name__)


# ==============================================================================
# State Definition
# ==============================================================================


class EmailClassificationState(TypedDict):
    """State for email classification agent.

    Tracks email data, classification result, and routing decisions.
    """
    # Input
    email_id: str
    email_subject: str
    email_sender: str
    email_sender_name: str
    email_sender_email: str
    email_body: str
    email_snippet: str
    action_phrases: list
    is_meeting_invite: bool
    thread_context: Optional[str]
    user_profile: Optional[dict]

    # Processing
    classification_raw: Optional[str]

    # Output
    classification: Optional[EmailClassification]
    confidence: float
    should_process: bool

    # Metadata
    processing_time_ms: Optional[int]
    error: Optional[str]


# ==============================================================================
# Agent Nodes
# ==============================================================================


async def classify_email(state: EmailClassificationState) -> EmailClassificationState:
    """Classify email using Gemini with structured output.

    Args:
        state: Current agent state

    Returns:
        Updated state with classification result
    """
    start_time = datetime.utcnow()

    try:
        # Build classification prompt
        prompt = get_email_classification_prompt(
            email_subject=state["email_subject"],
            email_sender=state["email_sender"],
            email_body=state["email_body"],
            email_snippet=state["email_snippet"],
            action_phrases=state["action_phrases"],
            is_meeting_invite=state["is_meeting_invite"],
            thread_context=state.get("thread_context")
        )

        # Get Gemini client
        gemini = get_gemini_client()

        # Add system prompt to the user prompt
        full_prompt = f"{EMAIL_CLASSIFICATION_SYSTEM_PROMPT}\n\n{prompt}"

        # Call Gemini with structured output
        classification = await gemini.generate_structured(
            prompt=full_prompt,
            schema=EmailClassification,
            temperature=0.3,  # Lower temperature for consistent classification
            fallback_to_qwen=True
        )

        # Calculate processing time
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        logger.info(
            f"Email {state['email_id']} classified: "
            f"actionable={classification.is_actionable}, "
            f"confidence={classification.confidence:.2f}, "
            f"type={classification.action_type}"
        )

        return {
            **state,
            "classification_raw": classification.model_dump_json(),
            "classification": classification,
            "confidence": classification.confidence,
            "processing_time_ms": processing_time,
            "error": None
        }

    except Exception as e:
        logger.error(f"Email classification failed for {state['email_id']}: {e}")

        # Return error state
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return {
            **state,
            "classification": None,
            "confidence": 0.0,
            "processing_time_ms": processing_time,
            "error": str(e)
        }


async def validate_classification(state: EmailClassificationState) -> EmailClassificationState:
    """Validate classification result and adjust confidence if needed.

    Args:
        state: Current agent state

    Returns:
        Updated state with validated classification
    """
    classification = state.get("classification")

    if not classification:
        # No classification - keep as-is
        return state

    # Apply validation rules
    adjusted_confidence = classification.confidence

    # Rule 1: Emails from Maran should be FYI with low confidence
    if state.get("email_sender_name", "").lower() == "maran":
        logger.info(f"Email {state['email_id']} from Maran - forcing FYI classification")
        classification.is_actionable = False
        classification.action_type = "fyi"
        adjusted_confidence = min(adjusted_confidence, 0.2)

    # Rule 2: Meeting invites without explicit prep needs should be medium confidence
    if state.get("is_meeting_invite") and classification.action_type == "meeting_prep":
        if not classification.key_action_items:
            adjusted_confidence = min(adjusted_confidence, 0.75)

    # Rule 3: Automated emails (no-reply, notifications) should be low confidence
    sender_email = state.get("email_sender_email", "").lower()
    if any(keyword in sender_email for keyword in ["no-reply", "noreply", "notification", "automated"]):
        classification.is_actionable = False
        classification.action_type = "automated"
        adjusted_confidence = min(adjusted_confidence, 0.3)

    # Rule 4: Boost confidence for Spain/Alberto (Jef's market)
    if "alberto" in state.get("email_sender_name", "").lower():
        if classification.is_actionable:
            adjusted_confidence = min(adjusted_confidence * 1.1, 1.0)  # 10% boost

    # Rule 5: Boost confidence if project detected
    if classification.detected_project in ["CRESCO", "RF16", "Just Deals"]:
        adjusted_confidence = min(adjusted_confidence * 1.05, 1.0)  # 5% boost

    # Update confidence
    classification.confidence = round(adjusted_confidence, 3)

    logger.debug(
        f"Validation complete for {state['email_id']}: "
        f"confidence adjusted to {classification.confidence:.2f}"
    )

    return {
        **state,
        "classification": classification,
        "confidence": classification.confidence
    }


async def decide_processing(state: EmailClassificationState) -> EmailClassificationState:
    """Decide if email should be processed based on confidence threshold.

    Routing logic:
    - confidence >= 0.8: Auto-process (create task)
    - confidence 0.5-0.8: Ask user for approval
    - confidence < 0.5: Skip (just store email)

    Args:
        state: Current agent state

    Returns:
        Updated state with processing decision
    """
    classification = state.get("classification")
    confidence = state.get("confidence", 0.0)

    # Default: don't process
    should_process = False

    if classification and classification.is_actionable:
        # Actionable emails
        if confidence >= 0.8:
            should_process = True  # Auto-process
            logger.info(f"Email {state['email_id']} will be auto-processed (confidence={confidence:.2f})")
        elif confidence >= 0.5:
            should_process = False  # Ask user
            logger.info(f"Email {state['email_id']} requires user approval (confidence={confidence:.2f})")
        else:
            should_process = False  # Skip
            logger.info(f"Email {state['email_id']} skipped (low confidence={confidence:.2f})")
    else:
        # Non-actionable emails
        should_process = False
        logger.info(f"Email {state['email_id']} marked as non-actionable")

    return {
        **state,
        "should_process": should_process
    }


# ==============================================================================
# Agent Graph Construction
# ==============================================================================


def create_email_classification_agent() -> StateGraph:
    """Create LangGraph agent for email classification.

    Returns:
        Compiled StateGraph agent
    """
    # Create graph
    workflow = StateGraph(EmailClassificationState)

    # Add nodes
    workflow.add_node("classify_email", classify_email)
    workflow.add_node("validate_classification", validate_classification)
    workflow.add_node("decide_processing", decide_processing)

    # Define edges (linear flow)
    workflow.set_entry_point("classify_email")
    workflow.add_edge("classify_email", "validate_classification")
    workflow.add_edge("validate_classification", "decide_processing")
    workflow.add_edge("decide_processing", END)

    # Compile graph
    app = workflow.compile()

    return app


# ==============================================================================
# Agent Runner
# ==============================================================================


async def classify_email_content(
    email_id: str,
    email_subject: str,
    email_sender: str,
    email_sender_name: str,
    email_sender_email: str,
    email_body: str,
    email_snippet: str,
    action_phrases: list,
    is_meeting_invite: bool,
    thread_context: Optional[str] = None,
    user_profile: Optional[dict] = None
) -> Dict[str, Any]:
    """Run email classification agent.

    Args:
        email_id: Email ID
        email_subject: Email subject
        email_sender: Full sender string
        email_sender_name: Sender name
        email_sender_email: Sender email
        email_body: Email body text
        email_snippet: Email snippet
        action_phrases: Detected action phrases
        is_meeting_invite: Whether email is meeting invite
        thread_context: Optional thread context
        user_profile: Optional user profile dict

    Returns:
        Dict with classification result and metadata
    """
    # Create agent
    agent = create_email_classification_agent()

    # Initial state
    initial_state: EmailClassificationState = {
        "email_id": email_id,
        "email_subject": email_subject,
        "email_sender": email_sender,
        "email_sender_name": email_sender_name,
        "email_sender_email": email_sender_email,
        "email_body": email_body,
        "email_snippet": email_snippet,
        "action_phrases": action_phrases,
        "is_meeting_invite": is_meeting_invite,
        "thread_context": thread_context,
        "user_profile": user_profile,
        "classification_raw": None,
        "classification": None,
        "confidence": 0.0,
        "should_process": False,
        "processing_time_ms": None,
        "error": None
    }

    # Run agent
    final_state = await agent.ainvoke(initial_state)

    # Build result
    result = {
        "email_id": email_id,
        "classification": final_state.get("classification"),
        "confidence": final_state.get("confidence", 0.0),
        "should_process": final_state.get("should_process", False),
        "processing_time_ms": final_state.get("processing_time_ms"),
        "error": final_state.get("error")
    }

    return result
