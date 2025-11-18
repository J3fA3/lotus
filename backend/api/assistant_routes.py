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

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
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
        user_id=request.user_id,
        pdf_bytes=None
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
            if op.get("task_id") is not None  # Filter out operations with None task_id
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


@router.post("/process-with-file", response_model=ProcessMessageResponse)
async def process_message_with_file(
    content: str = Form(default=""),
    source_type: str = Form(default="pdf"),
    session_id: Optional[str] = Form(default=None),
    source_identifier: Optional[str] = Form(default=None),
    user_id: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db)
):
    """Process a user message with an uploaded file (PDF, transcript, etc.).

    This endpoint:
    1. Accepts file uploads via multipart/form-data
    2. Reads PDF bytes and passes to orchestrator
    3. Runs the full processing pipeline with PDF parsing
    4. Returns proposed/created tasks

    Args:
        content: User message content
        source_type: Source type (pdf, transcript, etc.)
        session_id: Chat session ID (auto-generated if not provided)
        source_identifier: Optional source identifier
        user_id: Optional user ID
        file: Uploaded file (PDF, DOC, TXT, etc.)
        db: Database session

    Returns:
        ProcessMessageResponse with proposed/created tasks and recommendations
    """
    # Generate session ID if not provided
    session_id = session_id or str(uuid.uuid4())

    # Read file bytes if uploaded
    pdf_bytes = None
    if file:
        pdf_bytes = await file.read()
        # Store user message with filename
        content_with_file = f"[Uploaded: {file.filename}]\n{content}" if content else f"[Uploaded: {file.filename}]"
    else:
        content_with_file = content

    # Store user message
    await store_chat_message(
        db=db,
        session_id=session_id,
        role="user",
        content=content_with_file,
        metadata={"source_type": source_type, "filename": file.filename if file else None}
    )

    # Process message through orchestrator with PDF bytes
    result = await process_assistant_message(
        content=content or "",
        source_type=source_type,
        session_id=session_id,
        db=db,
        source_identifier=source_identifier,
        user_id=user_id,
        pdf_bytes=pdf_bytes
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
            if op.get("task_id") is not None  # Filter out operations with None task_id
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


@router.post("/process-pdf-fast")
async def process_pdf_fast(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db)
):
    """Fast PDF processing endpoint - bypasses orchestrator for speed.

    This endpoint:
    1. Processes PDF with AdvancedPDFProcessor
    2. Runs Phase 1 agents (cognitive nexus)
    3. Auto-creates all tasks without confidence scoring
    4. Returns results immediately

    Use this for large PDFs or when speed is critical.
    """
    from agents.advanced_pdf_processor import AdvancedPDFProcessor
    from agents.cognitive_nexus_graph import process_context
    from services.assistant_db_operations import create_tasks_from_proposals, store_context_item
    from sqlalchemy import select
    from db.models import Task

    # Generate session ID
    session_id = session_id or str(uuid.uuid4())

    try:
        # Read PDF bytes
        pdf_bytes = await file.read()

        # Process PDF
        processed_doc = await AdvancedPDFProcessor.process_document(pdf_bytes)
        context_text = processed_doc.raw_text

        # Add table data
        if processed_doc.tables:
            context_text += "\n\n### Tables Found:\n"
            for i, table in enumerate(processed_doc.tables, 1):
                context_text += f"\nTable {i}:\n{table.get('text', '')}\n"

        # Get existing tasks
        tasks_query = select(Task).order_by(Task.created_at.desc()).limit(20)
        result = await db.execute(tasks_query)
        task_models = result.scalars().all()
        existing_tasks = [
            {
                "id": t.id,
                "title": t.title,
                "assignee": t.assignee,
                "value_stream": t.value_stream,
                "description": t.description,
                "status": t.status,
                "due_date": t.due_date
            }
            for t in task_models
        ]

        # Run Phase 1 agents
        phase1_result = await process_context(
            text=context_text,
            source_type="pdf",
            source_identifier=file.filename,
            existing_tasks=existing_tasks
        )

        # Store context
        context_item_id = await store_context_item(
            db=db,
            content=context_text,
            source_type="pdf",
            entities=phase1_result["extracted_entities"],
            relationships=phase1_result["inferred_relationships"],
            quality_metrics={
                "extraction_strategy": "fast",
                "context_complexity": phase1_result.get("context_complexity", 0.0),
                "entity_quality": phase1_result.get("entity_quality", 0.0),
                "relationship_quality": phase1_result.get("relationship_quality", 0.0),
                "task_quality": phase1_result.get("task_quality", 0.0)
            },
            reasoning_trace=phase1_result.get("reasoning_steps", []),
            source_identifier=file.filename
        )

        # Convert task operations to proposals
        proposed_tasks = []
        for operation in phase1_result["task_operations"]:
            if operation.get("operation") == "CREATE":
                data = operation.get("data", {})
                proposed_tasks.append({
                    "id": f"temp_{uuid.uuid4().hex[:8]}",
                    "title": data.get("title", "Untitled Task"),
                    "description": data.get("description", ""),
                    "assignee": data.get("assignee", "Unassigned"),
                    "due_date": data.get("due_date"),
                    "priority": data.get("priority", "medium"),
                    "value_stream": data.get("project") or data.get("value_stream"),
                    "tags": [],
                    "status": "todo",
                    "operation": "CREATE",
                    "reasoning": operation.get("reasoning", "")
                })

        # Auto-create all tasks
        created_tasks = await create_tasks_from_proposals(
            db=db,
            proposed_tasks=proposed_tasks,
            context_item_id=context_item_id,
            auto_created=True
        )

        return {
            "message": f"Successfully processed PDF and created {len(created_tasks)} tasks",
            "session_id": session_id,
            "created_tasks": created_tasks,
            "entities_found": len(phase1_result["extracted_entities"]),
            "relationships_found": len(phase1_result["inferred_relationships"]),
            "context_item_id": context_item_id,
            "filename": file.filename
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")


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
