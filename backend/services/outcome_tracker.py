"""
Task Outcome Tracker - Phase 6 Cognitive Nexus

Automatically records task outcomes when tasks are completed, cancelled, or ignored.
This is the HIGHEST QUALITY learning signal (weight = 1.0).

Key Features:
1. Auto-records on status change (todo→done, or explicit cancel)
2. Calculates completion quality (0.0-5.0)
3. Extracts blockers from comments
4. Generates lessons learned via AI
5. Tracks effort variance (actual vs estimated)

Usage:
    tracker = OutcomeTracker(db)
    await tracker.record_outcome_on_status_change(task_id, "done")
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging

from db.models import Task, Comment
from services.kg_evolution_service import KGEvolutionService

logger = logging.getLogger(__name__)


class OutcomeTracker:
    """Tracks task outcomes automatically when task status changes."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.kg_service = KGEvolutionService(db)

    async def record_outcome_on_status_change(
        self,
        task_id: str,
        new_status: str,
        previous_status: Optional[str] = None
    ) -> Optional[str]:
        """Record task outcome when status changes.

        Args:
            task_id: Task ID
            new_status: New status (todo, doing, done)
            previous_status: Previous status (optional)

        Returns:
            Outcome type if recorded, None if not applicable
        """
        # Only record outcomes for certain status changes
        outcome_type = self._determine_outcome_type(new_status, previous_status)

        if not outcome_type:
            return None  # No outcome to record

        try:
            # Fetch task
            result = await self.db.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()

            if not task:
                logger.warning(f"Task {task_id} not found for outcome tracking")
                return None

            # Record outcome using KG Evolution Service
            await self.kg_service.record_task_outcome(
                task_id=task_id,
                outcome=outcome_type,
                task=task
            )

            logger.info(f"Recorded {outcome_type} outcome for task {task_id}")
            return outcome_type

        except Exception as e:
            logger.error(f"Failed to record outcome for task {task_id}: {e}")
            return None

    async def record_ignored_task(self, task_id: str):
        """Record outcome for task that was ignored (>7 days in todo).

        This is called by a background job that checks for ignored tasks.

        Args:
            task_id: Task ID
        """
        try:
            await self.kg_service.record_task_outcome(
                task_id=task_id,
                outcome="IGNORED"
            )
            logger.info(f"Recorded IGNORED outcome for task {task_id}")
        except Exception as e:
            logger.error(f"Failed to record ignored outcome for task {task_id}: {e}")

    async def record_merged_task(self, task_id: str, merged_into_id: str):
        """Record outcome for task that was merged into another.

        Args:
            task_id: Task ID that was merged (closed)
            merged_into_id: Task ID it was merged into
        """
        try:
            # Fetch task
            result = await self.db.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()

            if not task:
                return

            # Record as merged
            outcome_node = await self.kg_service.record_task_outcome(
                task_id=task_id,
                outcome="MERGED",
                task=task
            )

            # Add note about merge target
            outcome_node.user_notes = f"Merged into task {merged_into_id}"
            await self.db.commit()

            logger.info(f"Recorded MERGED outcome for task {task_id} → {merged_into_id}")
        except Exception as e:
            logger.error(f"Failed to record merged outcome: {e}")

    def _determine_outcome_type(
        self,
        new_status: str,
        previous_status: Optional[str]
    ) -> Optional[str]:
        """Determine outcome type based on status change.

        Returns:
            Outcome type (COMPLETED, CANCELLED) or None
        """
        # Task completed
        if new_status == "done":
            return "COMPLETED"

        # Task cancelled (explicit deletion or status change to cancelled)
        # TODO: Add "cancelled" status to task model
        # For now, we only track completions automatically
        # Cancellations must be explicitly recorded via API

        return None


async def get_outcome_tracker(db: AsyncSession) -> OutcomeTracker:
    """Factory function to get outcome tracker instance.

    Args:
        db: Database session

    Returns:
        OutcomeTracker instance
    """
    return OutcomeTracker(db)
