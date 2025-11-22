"""
Assistant Database Operations

This module handles database persistence for the AI Assistant orchestrator:
- Creating tasks from proposals
- Enriching existing tasks (adding comments, updating fields)
- Storing context items
- Tracking feedback events

All operations use transactions to ensure data consistency.
"""

from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid
import json

from db.models import (
    Task,
    Comment,
    ChatMessage,
    ContextItem,
    Entity,
    Relationship,
    FeedbackEvent
)


async def create_tasks_from_proposals(
    db: AsyncSession,
    proposed_tasks: List[Dict],
    context_item_id: Optional[int],
    auto_created: bool = True
) -> List[Dict]:
    """Create tasks from orchestrator proposals with AI agent comments.

    Args:
        db: Database session
        proposed_tasks: List of proposed task dictionaries
        context_item_id: ID of the ContextItem that generated these tasks
        auto_created: Whether tasks were auto-created (vs user-approved)

    Returns:
        List of created task dictionaries with IDs
    """
    created_tasks = []

    for proposal in proposed_tasks:
        # Generate new task ID
        task_id = f"task-{uuid.uuid4().hex[:12]}"

        # Create Task model
        task = Task(
            id=task_id,
            title=proposal.get("title", "Untitled Task"),
            description=proposal.get("description", ""),
            status=proposal.get("status", "todo"),
            assignee=proposal.get("assignee", "Unassigned"),
            due_date=proposal.get("due_date"),
            value_stream=proposal.get("value_stream"),
            notes=f"Created by AI Assistant. Confidence: {proposal.get('confidence', 0):.0f}%",
            confidence_score=proposal.get("confidence", 0.0) / 100.0,  # Store as 0-1
            source_context_id=context_item_id,
            auto_created=auto_created
        )

        db.add(task)
        await db.flush()  # Get task ID before creating comment

        # Add AI Agent comment with reasoning and details
        agent_comment_text = _build_agent_comment(proposal, context_item_id, auto_created)
        agent_comment = Comment(
            id=f"comment-{uuid.uuid4().hex[:12]}",
            task_id=task.id,
            text=agent_comment_text,
            author="Lotus",
            created_at=datetime.utcnow()
        )
        db.add(agent_comment)

        # Convert to dict for return
        created_task = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "assignee": task.assignee,
            "due_date": task.due_date,
            "value_stream": task.value_stream,
            "notes": task.notes,
            "confidence_score": task.confidence_score,
            "auto_created": task.auto_created,
            "created_at": task.created_at.isoformat() if task.created_at else None
        }

        created_tasks.append(created_task)

    await db.commit()
    return created_tasks


def _build_agent_comment(
    proposal: Dict,
    context_item_id: Optional[int],
    auto_created: bool
) -> str:
    """Build detailed agent comment with reasoning and metadata.

    Args:
        proposal: Task proposal dictionary
        context_item_id: Context item ID
        auto_created: Whether auto-created

    Returns:
        Formatted comment text
    """
    lines = ["🤖 **Lotus Analysis**\n"]

    # Confidence and decision
    confidence = proposal.get("confidence", 0)
    lines.append(f"**Confidence:** {confidence:.0f}%")

    if auto_created:
        lines.append(f"**Decision:** Auto-created (high confidence)")
    else:
        lines.append(f"**Decision:** User-approved")

    # Reasoning
    reasoning = proposal.get("reasoning", "")
    if reasoning:
        lines.append(f"\n**Reasoning:**")
        lines.append(f"{reasoning}")

    # Confidence factors
    confidence_factors = proposal.get("confidence_factors", {})
    if confidence_factors:
        lines.append(f"\n**Confidence Breakdown:**")
        for factor, score in confidence_factors.items():
            lines.append(f"- {factor}: {score:.0f}%")

    # Extracted entities (if available)
    tags = proposal.get("tags", [])
    if tags:
        lines.append(f"\n**Related Entities:** {', '.join(tags)}")

    # Source context link
    if context_item_id:
        lines.append(f"\n**Source Context:** #context-{context_item_id}")

    # Priority and due date highlights
    priority = proposal.get("priority")
    due_date = proposal.get("due_date")
    if priority or due_date:
        lines.append(f"\n**Key Details:**")
        if priority:
            lines.append(f"- Priority: {priority}")
        if due_date:
            lines.append(f"- Due Date: {due_date}")

    return "\n".join(lines)


async def enrich_existing_tasks(
    db: AsyncSession,
    enrichment_operations: List[Dict],
    context_item_id: Optional[int]
) -> List[Dict]:
    """Enrich existing tasks based on orchestrator operations.

    Handles:
    - UPDATE: Modify task fields
    - COMMENT: Add comments to tasks
    - ENRICH: Add notes/context to tasks

    Args:
        db: Database session
        enrichment_operations: List of enrichment operation dictionaries
        context_item_id: ID of the ContextItem triggering enrichment

    Returns:
        List of enriched task dictionaries
    """
    enriched_tasks = []

    for operation in enrichment_operations:
        op_type = operation.get("operation")
        task_id = operation.get("task_id")
        op_data = operation.get("data", {})

        if not task_id:
            continue

        # Get existing task
        task_query = select(Task).where(Task.id == task_id)
        result = await db.execute(task_query)
        task = result.scalar_one_or_none()

        if not task:
            continue

        if op_type == "UPDATE":
            # Update task fields
            for field, value in op_data.items():
                if field in ["due_date", "status", "assignee", "priority", "description"]:
                    setattr(task, field, value)

            # Add note about update
            update_note = f"\n[AI Update {datetime.now().strftime('%Y-%m-%d')}]: {operation.get('reasoning', 'Updated by AI')}"
            task.notes = (task.notes or "") + update_note

        elif op_type == "COMMENT":
            # Add comment to task
            comment = Comment(
                id=f"comment-{uuid.uuid4().hex[:12]}",
                task_id=task.id,
                text=op_data.get("text", ""),
                author=op_data.get("author", "Lotus")
            )
            db.add(comment)

        elif op_type == "ENRICH":
            # Add contextual note to task
            enrich_note = f"\n[AI Context {datetime.now().strftime('%Y-%m-%d')}]: {operation.get('reasoning', 'Related context added')}"
            task.notes = (task.notes or "") + enrich_note

        # Convert to dict for return
        enriched_task = {
            "id": task.id,
            "title": task.title,
            "operation": op_type,
            "reasoning": operation.get("reasoning", "")
        }

        enriched_tasks.append(enriched_task)

    await db.commit()
    return enriched_tasks


async def store_context_item(
    db: AsyncSession,
    content: str,
    source_type: str,
    entities: List[Dict],
    relationships: List[Dict],
    quality_metrics: Dict,
    reasoning_trace: List[str],
    source_identifier: Optional[str] = None
) -> int:
    """Store context item and its entities/relationships in the knowledge graph.

    Args:
        db: Database session
        content: Raw context content
        source_type: Type of source
        entities: Extracted entities
        relationships: Inferred relationships
        quality_metrics: Quality scores from agents
        reasoning_trace: Agent reasoning steps
        source_identifier: Optional source identifier

    Returns:
        ID of created ContextItem
    """
    # Create ContextItem
    context_item = ContextItem(
        content=content,
        source_type=source_type,
        source_identifier=source_identifier,
        extraction_strategy=quality_metrics.get("extraction_strategy", "fast"),
        context_complexity=quality_metrics.get("context_complexity", 0.0),
        entity_quality=quality_metrics.get("entity_quality", 0.0),
        relationship_quality=quality_metrics.get("relationship_quality", 0.0),
        task_quality=quality_metrics.get("task_quality", 0.0),
        reasoning_trace=json.dumps(reasoning_trace)
    )

    db.add(context_item)
    await db.flush()  # Get ID without committing

    context_item_id = context_item.id

    # Create Entity records
    entity_id_map = {}  # Map entity name to database ID
    for entity_data in entities:
        entity = Entity(
            name=entity_data.get("name", ""),
            type=entity_data.get("type", "UNKNOWN"),
            confidence=entity_data.get("confidence", 1.0),
            entity_metadata=entity_data.get("metadata"),
            context_item_id=context_item_id
        )
        db.add(entity)
        await db.flush()

        entity_id_map[entity_data.get("name")] = entity.id

    # Create Relationship records
    for rel_data in relationships:
        subject_name = rel_data.get("subject")
        object_name = rel_data.get("object")

        subject_id = entity_id_map.get(subject_name)
        object_id = entity_id_map.get(object_name)

        if subject_id and object_id:
            relationship = Relationship(
                subject_entity_id=subject_id,
                predicate=rel_data.get("predicate", "RELATED_TO"),
                object_entity_id=object_id,
                confidence=rel_data.get("confidence", 1.0),
                context_item_id=context_item_id
            )
            db.add(relationship)

    await db.commit()
    return context_item_id


async def store_chat_message(
    db: AsyncSession,
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict] = None
) -> int:
    """Store a chat message in the conversation history.

    Args:
        db: Database session
        session_id: Chat session ID
        role: 'user' or 'assistant'
        content: Message content
        metadata: Optional metadata (task IDs, confidence scores, etc.)

    Returns:
        ID of created ChatMessage
    """
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        message_metadata=metadata
    )

    db.add(message)
    await db.commit()

    return message.id


async def record_feedback_event(
    db: AsyncSession,
    event_type: str,
    task_id: Optional[str],
    original_data: Optional[Dict],
    modified_data: Optional[Dict],
    context_item_id: Optional[int]
) -> int:
    """Record a user feedback event for learning.

    Args:
        db: Database session
        event_type: 'approved', 'edited', 'rejected', 'deleted'
        task_id: Task ID (None for rejected tasks)
        original_data: Original task data proposed by AI
        modified_data: Modified task data (for edits)
        context_item_id: Context that generated the task

    Returns:
        ID of created FeedbackEvent
    """
    feedback = FeedbackEvent(
        task_id=task_id,
        event_type=event_type,
        original_data=original_data,
        modified_data=modified_data,
        context_item_id=context_item_id
    )

    db.add(feedback)
    await db.commit()

    return feedback.id


async def get_chat_history(
    db: AsyncSession,
    session_id: str,
    limit: int = 50
) -> List[Dict]:
    """Get chat history for a session.

    Args:
        db: Database session
        session_id: Chat session ID
        limit: Maximum messages to return

    Returns:
        List of message dictionaries
    """
    query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    messages = result.scalars().all()

    # Reverse to get chronological order
    messages = list(reversed(messages))

    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "metadata": msg.message_metadata,
            "created_at": msg.created_at.isoformat() if msg.created_at else None
        }
        for msg in messages
    ]
