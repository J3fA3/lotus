"""
AI Assistant API Routes

This module provides FastAPI endpoints for the Phase 2 AI Assistant:
- POST /assistant/process: Process user messages through orchestrator
- POST /assistant/approve: Approve proposed tasks
- POST /assistant/reject: Reject proposed tasks
- POST /assistant/feedback: Track user feedback on tasks
- GET /assistant/history: Get chat history for a session

All endpoints integrate with the orchestrator agent and database operations.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from db.database import get_db
from agents.orchestrator import process_assistant_message
from services.assistant_db_operations import (
    create_tasks_from_proposals,
    enrich_existing_tasks,
    store_chat_message,
    record_feedback_event,
    get_chat_history
)


router = APIRouter(prefix="/assistant", tags=["AI Assistant"])


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class ProcessMessageRequest(BaseModel):
    """Request to process a user message."""
    content: str = Field(..., description="User message content")
    source_type: str = Field(default="manual", description="Source type: slack, transcript, manual, question")
    session_id: Optional[str] = Field(default=None, description="Chat session ID (auto-generated if not provided)")
    source_identifier: Optional[str] = Field(default=None, description="Optional source identifier")
    user_id: Optional[str] = Field(default=None, description="Optional user ID")


class TaskProposal(BaseModel):
    """A proposed task from the AI."""
    id: str
    title: str
    description: Optional[str]
    assignee: str
    due_date: Optional[str]
    priority: Optional[str]
    value_stream: Optional[str]
    tags: List[str]
    status: str
    confidence: float
    confidence_factors: Dict[str, float]
    operation: str
    reasoning: str


class EnrichmentOperation(BaseModel):
    """An operation to enrich an existing task."""
    operation: str
    task_id: str
    data: Dict
    reasoning: str


class ProcessMessageResponse(BaseModel):
    """Response from processing a user message."""
    message: str
    session_id: str
    recommended_action: str  # 'auto', 'ask', 'clarify', 'store_only', 'answer_question'
    needs_approval: bool
    answer_text: Optional[str]  # For question responses
    proposed_tasks: List[TaskProposal]
    enrichment_operations: List[EnrichmentOperation]
    created_tasks: List[Dict]  # If auto-approved
    enriched_tasks: List[Dict]  # If auto-approved
    clarifying_questions: List[str]
    overall_confidence: float
    reasoning_trace: List[str]
    context_item_id: Optional[int]


class ApproveTasksRequest(BaseModel):
    """Request to approve proposed tasks."""
    session_id: str
    task_proposals: List[Dict]  # Task proposals to create
    enrichment_operations: Optional[List[Dict]] = []
    context_item_id: Optional[int] = None


class ApproveTasksResponse(BaseModel):
    """Response from approving tasks."""
    created_tasks: List[Dict]
    enriched_tasks: List[Dict]
    message: str


class RejectTasksRequest(BaseModel):
    """Request to reject proposed tasks."""
    session_id: str
    task_ids: List[str]  # Temporary IDs of proposed tasks
    reason: Optional[str] = None
    context_item_id: Optional[int] = None


class FeedbackRequest(BaseModel):
    """Request to record user feedback on a task."""
    task_id: str
    event_type: str  # 'approved', 'edited', 'rejected', 'deleted'
    original_data: Optional[Dict] = None
    modified_data: Optional[Dict] = None
    context_item_id: Optional[int] = None


class ChatHistoryResponse(BaseModel):
    """Response with chat history."""
    session_id: str
    messages: List[Dict]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/process", response_model=ProcessMessageResponse)
async def process_message(
    request: ProcessMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    """Process a user message through the AI Assistant orchestrator.

    This endpoint:
    1. Runs the orchestrator pipeline (Phase 1 agents + confidence scoring)
    2. Returns proposed tasks for approval OR auto-created tasks
    3. Stores chat message in history
    4. Returns reasoning trace for transparency

    Args:
        request: ProcessMessageRequest with user message
        db: Database session

    Returns:
        ProcessMessageResponse with proposed/created tasks and recommendations
    """
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())

    # Store user message
    await store_chat_message(
        db=db,
        session_id=session_id,
        role="user",
        content=request.content,
        metadata={"source_type": request.source_type}
    )

    # Process message through orchestrator
    result = await process_assistant_message(
        content=request.content,
        source_type=request.source_type,
        session_id=session_id,
        db=db,
        source_identifier=request.source_identifier,
        user_id=request.user_id
    )

    # Build response message
    if result["recommended_action"] == "auto":
        message = f"I found {len(result['proposed_tasks'])} task(s) and auto-created them with high confidence."
    elif result["recommended_action"] == "ask":
        message = f"I found {len(result['proposed_tasks'])} task(s). Please review and approve."
    elif result["recommended_action"] == "clarify":
        message = "I need some clarification to create tasks effectively."
    elif result["recommended_action"] == "answer_question":
        message = "I'll help answer your question based on the knowledge graph."
    else:
        message = "I've stored this context in the knowledge graph."

    # Prepare response
    response_data = {
        "message": message,
        "session_id": session_id,
        "recommended_action": result["recommended_action"],
        "needs_approval": result["needs_approval"],
        "answer_text": result.get("answer_text"),
        "proposed_tasks": [
            TaskProposal(**task) for task in result["proposed_tasks"]
        ],
        "enrichment_operations": [
            EnrichmentOperation(**op) for op in result["enrichment_operations"]
        ],
        "created_tasks": result["created_tasks"],
        "enriched_tasks": result["enriched_tasks"],
        "clarifying_questions": result["clarifying_questions"],
        "overall_confidence": result["overall_confidence"],
        "reasoning_trace": result["reasoning_trace"],
        "context_item_id": result["context_item_id"]
    }

    # Store assistant message
    await store_chat_message(
        db=db,
        session_id=session_id,
        role="assistant",
        content=message,
        metadata={
            "task_ids": [t["id"] for t in result["created_tasks"]],
            "proposed_tasks": result["proposed_tasks"],
            "enriched_tasks": result["enriched_tasks"],
            "confidence": result["overall_confidence"],
            "context_item_id": result["context_item_id"]
        }
    )

    return ProcessMessageResponse(**response_data)


@router.post("/approve", response_model=ApproveTasksResponse)
async def approve_tasks(
    request: ApproveTasksRequest,
    db: AsyncSession = Depends(get_db)
):
    """Approve and create proposed tasks.

    This endpoint creates tasks that were proposed by the AI but needed
    user approval (confidence 50-80%).

    Args:
        request: ApproveTasksRequest with task proposals
        db: Database session

    Returns:
        ApproveTasksResponse with created tasks
    """
    # Create tasks from proposals
    created_tasks = await create_tasks_from_proposals(
        db=db,
        proposed_tasks=request.task_proposals,
        context_item_id=request.context_item_id,
        auto_created=False  # User-approved
    )

    # Enrich existing tasks if needed
    enriched_tasks = []
    if request.enrichment_operations:
        enriched_tasks = await enrich_existing_tasks(
            db=db,
            enrichment_operations=request.enrichment_operations,
            context_item_id=request.context_item_id
        )

    # Record approval feedback
    for task in created_tasks:
        await record_feedback_event(
            db=db,
            event_type="approved",
            task_id=task["id"],
            original_data=None,  # TODO: Track original proposal
            modified_data=None,
            context_item_id=request.context_item_id
        )

    # Store assistant message about approval
    await store_chat_message(
        db=db,
        session_id=request.session_id,
        role="assistant",
        content=f"Created {len(created_tasks)} task(s) as approved.",
        metadata={
            "task_ids": [t["id"] for t in created_tasks],
            "event": "tasks_approved"
        }
    )

    return ApproveTasksResponse(
        created_tasks=created_tasks,
        enriched_tasks=enriched_tasks,
        message=f"Successfully created {len(created_tasks)} task(s)"
    )


@router.post("/reject")
async def reject_tasks(
    request: RejectTasksRequest,
    db: AsyncSession = Depends(get_db)
):
    """Reject proposed tasks.

    This endpoint records that the user rejected AI-proposed tasks,
    which helps improve confidence scoring in Phase 3.

    Args:
        request: RejectTasksRequest with rejected task IDs
        db: Database session

    Returns:
        Success message
    """
    # Record rejection feedback for each task
    for task_id in request.task_ids:
        await record_feedback_event(
            db=db,
            event_type="rejected",
            task_id=None,  # No actual task created
            original_data={"temp_id": task_id, "reason": request.reason},
            modified_data=None,
            context_item_id=request.context_item_id
        )

    # Store assistant message about rejection
    await store_chat_message(
        db=db,
        session_id=request.session_id,
        role="assistant",
        content=f"Understood. I won't create those {len(request.task_ids)} task(s).",
        metadata={
            "event": "tasks_rejected",
            "reason": request.reason
        }
    )

    return {"message": f"Rejected {len(request.task_ids)} task(s)", "status": "success"}


@router.post("/feedback")
async def record_task_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """Record user feedback on a task.

    This endpoint tracks when users:
    - Edit AI-created tasks
    - Delete AI-created tasks
    - Approve tasks without changes

    This data is used for improving confidence scoring in Phase 3.

    Args:
        request: FeedbackRequest with feedback data
        db: Database session

    Returns:
        Success message
    """
    feedback_id = await record_feedback_event(
        db=db,
        event_type=request.event_type,
        task_id=request.task_id,
        original_data=request.original_data,
        modified_data=request.modified_data,
        context_item_id=request.context_item_id
    )

    return {
        "message": "Feedback recorded",
        "feedback_id": feedback_id,
        "status": "success"
    }


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history_endpoint(
    session_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get chat history for a session.

    Args:
        session_id: Chat session ID
        limit: Maximum messages to return
        db: Database session

    Returns:
        ChatHistoryResponse with messages
    """
    messages = await get_chat_history(
        db=db,
        session_id=session_id,
        limit=limit
    )

    return ChatHistoryResponse(
        session_id=session_id,
        messages=messages
    )
