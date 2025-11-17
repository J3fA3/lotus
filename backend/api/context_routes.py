"""
Cognitive Nexus API Routes - Context Ingestion and Agent Processing

These endpoints allow clients to:
1. Ingest context (Slack messages, transcripts, manual text)
2. Process context through LangGraph agents
3. View reasoning traces and quality metrics
4. Query extracted entities and relationships
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import json

from db.database import get_db
from db.models import ContextItem, Entity, Relationship
from agents.cognitive_nexus_graph import process_context


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class ContextIngestRequest(BaseModel):
    """Request schema for context ingestion."""
    content: str = Field(..., min_length=10, description="The context text to process")
    source_type: str = Field(default="manual", description="Source type: slack, transcript, or manual")
    source_identifier: Optional[str] = Field(None, description="Optional identifier for the source")

    class Config:
        json_schema_extra = {
            "example": {
                "content": "Hey Jef, hope all is well. I want to send an email about low performance of occasions tile. Could you share the data points you presented during the meeting when we decided not to activate the tile? We need to get this done by Friday.",
                "source_type": "slack",
                "source_identifier": "channel-general-2025-11-16"
            }
        }


class ContextIngestResponse(BaseModel):
    """Response schema for context ingestion."""
    context_item_id: int
    entities_extracted: int
    relationships_inferred: int
    tasks_generated: int
    quality_metrics: Dict[str, float]
    reasoning_steps: List[str]


class EntityResponse(BaseModel):
    """Response schema for entity data."""
    id: int
    name: str
    type: str
    confidence: float
    created_at: str


class RelationshipResponse(BaseModel):
    """Response schema for relationship data."""
    id: int
    subject: str
    predicate: str
    object: str
    confidence: float


class ReasoningTraceResponse(BaseModel):
    """Response schema for reasoning trace."""
    context_item_id: int
    reasoning_steps: List[str]
    extraction_strategy: str
    quality_metrics: Dict[str, float]


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(prefix="/context", tags=["Cognitive Nexus"])


@router.post("/", response_model=ContextIngestResponse)
async def ingest_context(
    request: ContextIngestRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Process context through the LangGraph agent system.

    This endpoint:
    1. Runs the context through all 4 agents (analysis, extraction, relationships, tasks)
    2. Stores results in the database
    3. Returns quality metrics and reasoning trace

    The system uses self-evaluation and retry loops to ensure quality.
    """
    try:
        # Run LangGraph agents
        final_state = await process_context(
            text=request.content,
            source_type=request.source_type,
            source_identifier=request.source_identifier
        )

        # Create ContextItem
        context_item = ContextItem(
            content=request.content,
            source_type=request.source_type,
            source_identifier=request.source_identifier,
            extraction_strategy=final_state.get("extraction_strategy"),
            context_complexity=final_state.get("context_complexity"),
            entity_quality=final_state.get("entity_quality"),
            relationship_quality=final_state.get("relationship_quality"),
            task_quality=final_state.get("task_quality"),
            reasoning_trace=json.dumps(final_state.get("reasoning_steps", []))
        )
        db.add(context_item)
        await db.flush()

        # Store entities
        entity_map = {}
        for entity_data in final_state.get("extracted_entities", []):
            entity = Entity(
                name=entity_data["name"],
                type=entity_data["type"],
                confidence=entity_data.get("confidence", 1.0),
                metadata=entity_data.get("metadata"),  # Store team metadata
                context_item_id=context_item.id
            )
            db.add(entity)
            await db.flush()
            entity_map[entity_data["name"]] = entity.id

        # Store relationships
        for rel_data in final_state.get("inferred_relationships", []):
            subject_name = rel_data.get("subject")
            object_name = rel_data.get("object")

            if subject_name in entity_map and object_name in entity_map:
                relationship = Relationship(
                    subject_entity_id=entity_map[subject_name],
                    predicate=rel_data["predicate"],
                    object_entity_id=entity_map[object_name],
                    confidence=rel_data.get("confidence", 1.0),
                    context_item_id=context_item.id
                )
                db.add(relationship)

        await db.commit()

        return ContextIngestResponse(
            context_item_id=context_item.id,
            entities_extracted=len(final_state.get("extracted_entities", [])),
            relationships_inferred=len(final_state.get("inferred_relationships", [])),
            tasks_generated=len(final_state.get("generated_tasks", [])),
            quality_metrics={
                "entity_quality": final_state.get("entity_quality", 0.0),
                "relationship_quality": final_state.get("relationship_quality", 0.0),
                "task_quality": final_state.get("task_quality", 0.0),
                "context_complexity": final_state.get("context_complexity", 0.0)
            },
            reasoning_steps=final_state.get("reasoning_steps", [])
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Context processing failed: {str(e)}")


@router.get("/{context_item_id}/reasoning", response_model=ReasoningTraceResponse)
async def get_reasoning_trace(
    context_item_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the agent reasoning trace for a specific context item.

    This shows:
    - Each agent's decision-making process
    - Quality evaluation steps
    - Retry logic reasoning
    - Strategic choices made by agents

    This transparency helps users understand why agents made specific decisions.
    """
    result = await db.execute(
        select(ContextItem).where(ContextItem.id == context_item_id)
    )
    context_item = result.scalar_one_or_none()

    if not context_item:
        raise HTTPException(status_code=404, detail="Context item not found")

    return ReasoningTraceResponse(
        context_item_id=context_item.id,
        reasoning_steps=json.loads(context_item.reasoning_trace or "[]"),
        extraction_strategy=context_item.extraction_strategy or "unknown",
        quality_metrics={
            "entity_quality": context_item.entity_quality or 0.0,
            "relationship_quality": context_item.relationship_quality or 0.0,
            "task_quality": context_item.task_quality or 0.0,
            "context_complexity": context_item.context_complexity or 0.0
        }
    )


@router.get("/{context_item_id}/entities", response_model=List[EntityResponse])
async def get_entities(
    context_item_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all entities extracted from a specific context item.

    Entities are categorized as:
    - PERSON: Full names
    - PROJECT: Project names
    - COMPANY: Organizations
    - DATE: Deadlines and dates
    """
    result = await db.execute(
        select(Entity)
        .where(Entity.context_item_id == context_item_id)
        .order_by(Entity.type, Entity.name)
    )
    entities = result.scalars().all()

    return [
        EntityResponse(
            id=e.id,
            name=e.name,
            type=e.type,
            confidence=e.confidence or 1.0,
            created_at=e.created_at.isoformat()
        )
        for e in entities
    ]


@router.get("/{context_item_id}/relationships", response_model=List[RelationshipResponse])
async def get_relationships(
    context_item_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all relationships inferred from a specific context item.

    Relationships connect entities and represent:
    - WORKS_ON: person works on project
    - COMMUNICATES_WITH: person talks to person
    - HAS_DEADLINE: project has deadline
    - MENTIONED_WITH: entities co-occur
    """
    result = await db.execute(
        select(Relationship)
        .join(Entity, Entity.id == Relationship.subject_entity_id)
        .where(Relationship.context_item_id == context_item_id)
        .order_by(Relationship.predicate)
    )
    relationships = result.scalars().all()

    response = []
    for rel in relationships:
        # Get subject and object entities
        subject_result = await db.execute(
            select(Entity).where(Entity.id == rel.subject_entity_id)
        )
        subject = subject_result.scalar_one()

        object_result = await db.execute(
            select(Entity).where(Entity.id == rel.object_entity_id)
        )
        obj = object_result.scalar_one()

        response.append(
            RelationshipResponse(
                id=rel.id,
                subject=subject.name,
                predicate=rel.predicate,
                object=obj.name,
                confidence=rel.confidence or 1.0
            )
        )

    return response


@router.get("/recent", response_model=List[Dict])
async def get_recent_contexts(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Get recently processed context items with summary statistics.

    Useful for:
    - Viewing context processing history
    - Monitoring agent performance
    - Debugging quality issues
    """
    result = await db.execute(
        select(ContextItem)
        .order_by(ContextItem.created_at.desc())
        .limit(limit)
    )
    contexts = result.scalars().all()

    response = []
    for ctx in contexts:
        # Count entities
        entity_result = await db.execute(
            select(Entity).where(Entity.context_item_id == ctx.id)
        )
        entity_count = len(entity_result.scalars().all())

        # Count relationships
        rel_result = await db.execute(
            select(Relationship).where(Relationship.context_item_id == ctx.id)
        )
        rel_count = len(rel_result.scalars().all())

        response.append({
            "id": ctx.id,
            "source_type": ctx.source_type,
            "source_identifier": ctx.source_identifier,
            "created_at": ctx.created_at.isoformat(),
            "extraction_strategy": ctx.extraction_strategy,
            "context_complexity": ctx.context_complexity,
            "entity_count": entity_count,
            "relationship_count": rel_count,
            "quality_metrics": {
                "entity_quality": ctx.entity_quality or 0.0,
                "relationship_quality": ctx.relationship_quality or 0.0,
                "task_quality": ctx.task_quality or 0.0
            }
        })

    return response


@router.delete("/{context_item_id}")
async def delete_context(
    context_item_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a context item and all associated entities and relationships.

    This uses cascade delete to clean up all related data.
    """
    result = await db.execute(
        select(ContextItem).where(ContextItem.id == context_item_id)
    )
    context_item = result.scalar_one_or_none()

    if not context_item:
        raise HTTPException(status_code=404, detail="Context item not found")

    await db.delete(context_item)
    await db.commit()

    return {"message": f"Context item {context_item_id} deleted successfully"}
