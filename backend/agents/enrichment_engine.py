"""
Task Enrichment Engine - Phase 3

Automatically updates existing tasks when new context arrives.

Examples:
- "Co-op presentation moved to Dec 3" → Updates existing Co-op task deadline
- "Alberto confirmed Spain launch" → Adds confirmation note to Spain tasks
- "CRESCO dashboard delayed" → Adds delay note to CRESCO tasks

Key Features:
1. Finds existing tasks related to new context
2. Determines what should be updated
3. Auto-applies high-confidence changes (>80%)
4. Asks for approval on medium-confidence changes (50-80%)
5. Generates natural comments explaining updates

Confidence Thresholds:
- >80%: Auto-apply changes
- 50-80%: Ask for user approval
- <50%: Skip enrichment
"""

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from services.gemini_client import get_gemini_client
from config.gemini_prompts import get_task_enrichment_prompt
from db.models import Task

logger = logging.getLogger(__name__)


class EnrichmentChanges(BaseModel):
    """Changes to apply to a task."""
    due_date: Optional[str] = None
    note_to_add: Optional[str] = None
    priority_change: Optional[str] = None  # high, medium, low
    status_change: Optional[str] = None  # todo, doing, done


class EnrichmentDecision(BaseModel):
    """Decision about whether to enrich a task."""
    should_update: bool
    confidence: int  # 0-100
    changes: EnrichmentChanges
    reasoning: str


class EnrichmentAction(BaseModel):
    """Action to enrich a task."""
    task_id: str
    task_title: str
    changes: Dict[str, Any]
    reasoning: str
    confidence: float
    auto_apply: bool  # True if confidence > 80


class TaskEnrichmentEngine:
    """Finds and applies enrichments to existing tasks."""

    def __init__(
        self,
        auto_apply_threshold: int = 80,
        min_confidence_threshold: int = 50
    ):
        """Initialize enrichment engine.

        Args:
            auto_apply_threshold: Confidence threshold for auto-applying (default 80)
            min_confidence_threshold: Minimum confidence to propose enrichment (default 50)
        """
        self.gemini = get_gemini_client()
        self.auto_apply_threshold = auto_apply_threshold
        self.min_confidence_threshold = min_confidence_threshold

    async def find_enrichment_opportunities(
        self,
        new_context: str,
        entities: List[Dict],
        existing_tasks: List[Dict],
        max_enrichments: int = 5
    ) -> List[EnrichmentAction]:
        """Find existing tasks that should be updated based on new context.

        Args:
            new_context: New input context
            entities: Entities extracted from new context
            existing_tasks: List of existing tasks to check
            max_enrichments: Maximum enrichments to return

        Returns:
            List of EnrichmentAction objects
        """
        if not existing_tasks or not entities:
            logger.debug("No existing tasks or entities - skipping enrichment")
            return []

        enrichments = []

        # Extract entity names for matching
        entity_names = {e.get("name", "").lower() for e in entities}

        for task in existing_tasks:
            # Check entity overlap
            task_text = f"{task.get('title', '')} {task.get('description', '')}".lower()

            # Count matching entities
            matches = sum(1 for entity_name in entity_names if entity_name in task_text)

            # Need at least 2 matching entities for strong relationship
            if matches >= 2:
                logger.debug(
                    f"Task '{task.get('title', 'Unknown')}' has {matches} entity matches - "
                    f"checking for enrichment"
                )

                # Use Gemini to determine if/how to update
                decision = await self._decide_enrichment(task, new_context, entities)

                if decision and decision.should_update:
                    # Confidence check
                    if decision.confidence >= self.min_confidence_threshold:
                        enrichment = EnrichmentAction(
                            task_id=task.get("id", ""),
                            task_title=task.get("title", "Unknown"),
                            changes=decision.changes.dict(exclude_none=True),
                            reasoning=decision.reasoning,
                            confidence=decision.confidence / 100.0,
                            auto_apply=(decision.confidence >= self.auto_apply_threshold)
                        )

                        enrichments.append(enrichment)

                        logger.info(
                            f"{'AUTO-APPLY' if enrichment.auto_apply else 'PROPOSE'} "
                            f"enrichment for task '{task.get('title', 'Unknown')}' "
                            f"(confidence: {decision.confidence}%)"
                        )

                        # Stop if we have enough
                        if len(enrichments) >= max_enrichments:
                            break

        logger.info(f"Found {len(enrichments)} enrichment opportunities")
        return enrichments

    async def _decide_enrichment(
        self,
        task: Dict[str, Any],
        new_context: str,
        entities: List[Dict]
    ) -> Optional[EnrichmentDecision]:
        """Decide if a task should be enriched and how.

        Args:
            task: Existing task dict
            new_context: New context
            entities: Extracted entities

        Returns:
            EnrichmentDecision or None if decision fails
        """
        try:
            prompt = get_task_enrichment_prompt(
                existing_task=task,
                new_context=new_context,
                entities=entities
            )

            decision = await self.gemini.generate_structured(
                prompt=prompt,
                schema=EnrichmentDecision,
                temperature=0.1
            )

            logger.debug(
                f"Enrichment decision for '{task.get('title', 'Unknown')}': "
                f"should_update={decision.should_update}, confidence={decision.confidence}%"
            )

            return decision

        except Exception as e:
            logger.error(f"Enrichment decision failed for task {task.get('id', 'unknown')}: {e}")
            return None

    async def apply_enrichment(
        self,
        enrichment: EnrichmentAction,
        db: AsyncSession
    ) -> bool:
        """Apply enrichment to a task in the database.

        Args:
            enrichment: EnrichmentAction to apply
            db: Database session

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get task
            query = select(Task).where(Task.id == enrichment.task_id)
            result = await db.execute(query)
            task = result.scalar_one_or_none()

            if not task:
                logger.error(f"Task not found: {enrichment.task_id}")
                return False

            # Apply changes
            changes = enrichment.changes

            if changes.get("due_date"):
                old_date = task.due_date
                task.due_date = changes["due_date"]
                logger.info(f"Updated due date: {old_date} → {changes['due_date']}")

            if changes.get("note_to_add"):
                # Append to notes
                note = changes["note_to_add"]
                if task.notes:
                    task.notes += f"\n\n{note}"
                else:
                    task.notes = note
                logger.info(f"Added note: {note[:50]}...")

            if changes.get("priority_change"):
                # Note: Priority not in current Task model, would need to add
                logger.warning("Priority field not in Task model - skipping priority change")

            if changes.get("status_change"):
                old_status = task.status
                task.status = changes["status_change"]
                logger.info(f"Updated status: {old_status} → {changes['status_change']}")

            await db.commit()
            logger.info(f"Successfully applied enrichment to task: {enrichment.task_title}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply enrichment: {e}")
            await db.rollback()
            return False


# Singleton instance
_enrichment_engine: Optional[TaskEnrichmentEngine] = None


def get_enrichment_engine(
    auto_apply_threshold: int = 80,
    min_confidence_threshold: int = 50
) -> TaskEnrichmentEngine:
    """Get or create global TaskEnrichmentEngine instance.

    Args:
        auto_apply_threshold: Confidence threshold for auto-apply
        min_confidence_threshold: Minimum confidence to propose

    Returns:
        TaskEnrichmentEngine singleton
    """
    global _enrichment_engine
    if _enrichment_engine is None:
        _enrichment_engine = TaskEnrichmentEngine(
            auto_apply_threshold=auto_apply_threshold,
            min_confidence_threshold=min_confidence_threshold
        )
    return _enrichment_engine
