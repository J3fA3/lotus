"""
Smart Question Batching Service - Phase 6 Stage 4

Intelligent batching of related questions to minimize user interruption.

Design Decisions:
1. Batch size: 3-5 questions (optimal cognitive load)
2. Batching criteria:
   - Same task: Always batch together
   - Semantic cluster: Batch within 1-hour window
   - Related fields: priority_planning, team_coordination
3. Timing strategy:
   - Defer during active task creation (don't interrupt flow)
   - Batch accumulation: Wait 5 minutes for related questions
   - Max wait: 1 hour (don't delay too long)
4. Background processing: Periodic batch creation (every 5 minutes)

Batching Algorithm:
1. Fetch queued questions
2. Group by task_id (priority)
3. Group by semantic cluster (within time window)
4. Create batches (3-5 questions each)
5. Mark questions as ready (batch assigned)
6. Track batch lifecycle
"""

import logging
import uuid
from typing import List, Dict, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from datetime import datetime, timedelta
from collections import defaultdict

from db.question_queue_models import QuestionQueue, QuestionBatch, should_batch_together

logger = logging.getLogger(__name__)


# ============================================================================
# SMART BATCHING SERVICE
# ============================================================================

class QuestionBatchingService:
    """
    Service for intelligent question batching.

    Minimizes user interruption by grouping related questions.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

        # Batching configuration
        self.MIN_BATCH_SIZE = 1  # Minimum questions per batch
        self.MAX_BATCH_SIZE = 5  # Maximum questions per batch (cognitive load limit)
        self.OPTIMAL_BATCH_SIZE = 3  # Target batch size

        self.BATCH_ACCUMULATION_WINDOW = 5 * 60  # 5 minutes (wait for related questions)
        self.MAX_WAIT_TIME = 60 * 60  # 1 hour (don't delay too long)
        self.SEMANTIC_CLUSTER_WINDOW = 60 * 60  # 1 hour (for cross-task clustering)

    # ========================================================================
    # BATCH CREATION
    # ========================================================================

    async def create_batches_from_queued(self) -> List[QuestionBatch]:
        """
        Main batching algorithm: Create batches from queued questions.

        This should be called periodically (e.g., every 5 minutes) as a background job.

        Returns:
            List of created batches
        """
        # Fetch queued questions
        queued_questions = await self._get_queued_questions()

        if not queued_questions:
            logger.debug("No queued questions to batch")
            return []

        logger.info(f"Processing {len(queued_questions)} queued questions for batching")

        # Group questions using batching criteria
        question_groups = self._group_questions(queued_questions)

        # Create batches from groups
        created_batches = []
        for group in question_groups:
            if len(group) >= self.MIN_BATCH_SIZE:
                batch = await self._create_batch(group)
                if batch:
                    created_batches.append(batch)

        logger.info(f"Created {len(created_batches)} batches from {len(queued_questions)} questions")

        return created_batches

    async def create_batch_for_task(self, task_id: str) -> Optional[QuestionBatch]:
        """
        Create a batch for all queued questions for a specific task.

        Useful when user explicitly requests questions for a task.

        Args:
            task_id: Task ID

        Returns:
            Created batch or None
        """
        # Fetch queued questions for task
        result = await self.db.execute(
            select(QuestionQueue)
            .where(
                and_(
                    QuestionQueue.task_id == task_id,
                    QuestionQueue.status == "queued"
                )
            )
            .order_by(desc(QuestionQueue.priority_score))
        )
        questions = list(result.scalars().all())

        if not questions:
            logger.debug(f"No queued questions for task {task_id}")
            return None

        # Create batch
        batch = await self._create_batch(questions)

        logger.info(f"Created batch for task {task_id} with {len(questions)} questions")

        return batch

    # ========================================================================
    # BATCH QUERYING
    # ========================================================================

    async def get_ready_batches(self, limit: int = 10) -> List[QuestionBatch]:
        """
        Get batches ready to be shown to user.

        Args:
            limit: Max batches to return

        Returns:
            List of ready batches
        """
        result = await self.db.execute(
            select(QuestionBatch)
            .where(
                and_(
                    QuestionBatch.shown_to_user == False,
                    QuestionBatch.completed == False
                )
            )
            .order_by(QuestionBatch.created_at)
            .limit(limit)
        )
        batches = list(result.scalars().all())

        return batches

    async def get_batch(self, batch_id: str) -> Optional[QuestionBatch]:
        """Get specific batch by ID."""
        result = await self.db.execute(
            select(QuestionBatch).where(QuestionBatch.id == batch_id)
        )
        return result.scalar_one_or_none()

    async def get_batch_questions(self, batch_id: str) -> List[QuestionQueue]:
        """
        Get all questions in a batch.

        Args:
            batch_id: Batch ID

        Returns:
            List of questions in batch
        """
        batch = await self.get_batch(batch_id)
        if not batch or not batch.question_ids:
            return []

        # Fetch questions
        result = await self.db.execute(
            select(QuestionQueue)
            .where(QuestionQueue.id.in_(batch.question_ids))
            .order_by(desc(QuestionQueue.priority_score))
        )
        questions = list(result.scalars().all())

        return questions

    # ========================================================================
    # BATCH LIFECYCLE
    # ========================================================================

    async def mark_batch_shown(self, batch_id: str) -> bool:
        """
        Mark batch as shown to user.

        Args:
            batch_id: Batch ID

        Returns:
            True if successful
        """
        try:
            batch = await self.get_batch(batch_id)
            if not batch:
                return False

            batch.shown_to_user = True
            batch.shown_at = datetime.utcnow()

            # Mark all questions in batch as shown
            if batch.question_ids:
                from services.question_queue_service import get_question_queue_service
                service = await get_question_queue_service(self.db)

                for q_id in batch.question_ids:
                    await service.mark_shown(q_id)

            await self.db.commit()

            logger.info(f"Batch {batch_id} marked as shown")
            return True

        except Exception as e:
            logger.error(f"Failed to mark batch {batch_id} as shown: {e}")
            return False

    async def mark_batch_completed(self, batch_id: str) -> bool:
        """
        Mark batch as completed (all questions answered/dismissed).

        Args:
            batch_id: Batch ID

        Returns:
            True if successful
        """
        try:
            batch = await self.get_batch(batch_id)
            if not batch:
                return False

            # Count question statuses
            questions = await self.get_batch_questions(batch_id)

            answered_count = sum(1 for q in questions if q.status == "answered")
            dismissed_count = sum(1 for q in questions if q.status == "dismissed")
            snoozed_count = sum(1 for q in questions if q.status == "snoozed")

            batch.answered_count = answered_count
            batch.dismissed_count = dismissed_count
            batch.snoozed_count = snoozed_count
            batch.completed = True
            batch.completed_at = datetime.utcnow()

            await self.db.commit()

            logger.info(
                f"Batch {batch_id} completed: {answered_count} answered, "
                f"{dismissed_count} dismissed, {snoozed_count} snoozed"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to mark batch {batch_id} as completed: {e}")
            return False

    # ========================================================================
    # PRIVATE HELPERS
    # ========================================================================

    async def _get_queued_questions(self) -> List[QuestionQueue]:
        """
        Get all queued questions that are ready for batching.

        Criteria:
        - Status = queued
        - Created at least BATCH_ACCUMULATION_WINDOW ago (give time to accumulate)
          OR created more than MAX_WAIT_TIME ago (don't wait forever)
        """
        now = datetime.utcnow()
        accumulation_cutoff = now - timedelta(seconds=self.BATCH_ACCUMULATION_WINDOW)
        max_wait_cutoff = now - timedelta(seconds=self.MAX_WAIT_TIME)

        result = await self.db.execute(
            select(QuestionQueue)
            .where(
                and_(
                    QuestionQueue.status == "queued",
                    or_(
                        QuestionQueue.created_at <= accumulation_cutoff,
                        QuestionQueue.created_at <= max_wait_cutoff
                    )
                )
            )
            .order_by(desc(QuestionQueue.priority_score))
        )
        questions = list(result.scalars().all())

        return questions

    def _group_questions(self, questions: List[QuestionQueue]) -> List[List[QuestionQueue]]:
        """
        Group questions using batching criteria.

        Grouping logic:
        1. Group by task_id (same task questions always together)
        2. Within each task group, split into batches of max size
        3. Group orphaned questions by semantic cluster (if close in time)
        4. Create individual batches for ungrouped questions

        Args:
            questions: List of questions to group

        Returns:
            List of question groups (each group will become a batch)
        """
        groups = []

        # Group 1: By task_id
        task_groups = defaultdict(list)
        for q in questions:
            task_groups[q.task_id].append(q)

        # Split large task groups into smaller batches
        for task_id, task_questions in task_groups.items():
            # Sort by priority within task
            task_questions.sort(key=lambda q: q.priority_score, reverse=True)

            # Split into batches of max size
            for i in range(0, len(task_questions), self.MAX_BATCH_SIZE):
                batch_group = task_questions[i:i + self.MAX_BATCH_SIZE]
                groups.append(batch_group)

        logger.debug(f"Created {len(groups)} task-based groups from {len(questions)} questions")

        # Note: Semantic clustering across tasks could be added here
        # For simplicity, we're keeping same-task batching for now

        return groups

    async def _create_batch(self, questions: List[QuestionQueue]) -> Optional[QuestionBatch]:
        """
        Create a batch from a group of questions.

        Args:
            questions: Questions to batch

        Returns:
            Created batch or None
        """
        if not questions:
            return None

        try:
            # Generate batch ID
            batch_id = str(uuid.uuid4())

            # Determine batch type
            task_ids = list(set(q.task_id for q in questions))
            if len(task_ids) == 1:
                batch_type = "task_specific"
            else:
                batch_type = "semantic_cluster"

            # Determine semantic cluster (if all same)
            semantic_clusters = list(set(q.semantic_cluster for q in questions if q.semantic_cluster))
            semantic_cluster = semantic_clusters[0] if len(semantic_clusters) == 1 else None

            # Create batch
            batch = QuestionBatch(
                id=batch_id,
                batch_type=batch_type,
                semantic_cluster=semantic_cluster,
                question_count=len(questions),
                question_ids=[q.id for q in questions],
                task_ids=task_ids
            )

            self.db.add(batch)

            # Update questions: assign batch_id and mark as ready
            for q in questions:
                q.batch_id = batch_id
                q.status = "ready"
                q.ready_at = datetime.utcnow()
                q.related_questions = [other_q.id for other_q in questions if other_q.id != q.id]

            await self.db.commit()

            logger.info(
                f"Created batch {batch_id}: {len(questions)} questions, "
                f"type={batch_type}, tasks={task_ids}"
            )

            return batch

        except Exception as e:
            logger.error(f"Failed to create batch: {e}")
            await self.db.rollback()
            return None

    # ========================================================================
    # BACKGROUND JOB
    # ========================================================================

    async def process_batches_background(self) -> Dict:
        """
        Background job to process question batches.

        Should be called periodically (e.g., every 5 minutes via cron/scheduler).

        Steps:
        1. Create batches from queued questions
        2. Wake up snoozed questions
        3. Clean up completed batches (optional)

        Returns:
            Stats dict with counts
        """
        try:
            # Wake snoozed questions
            from services.question_queue_service import get_question_queue_service
            service = await get_question_queue_service(self.db)
            woken = await service.wake_snoozed_questions()

            # Create batches from queued
            batches = await self.create_batches_from_queued()

            stats = {
                "batches_created": len(batches),
                "questions_woken": woken,
                "processed_at": datetime.utcnow().isoformat()
            }

            logger.info(
                f"Background batch processing: created {len(batches)} batches, "
                f"woke {woken} snoozed questions"
            )

            return stats

        except Exception as e:
            logger.error(f"Background batch processing failed: {e}")
            return {
                "batches_created": 0,
                "questions_woken": 0,
                "error": str(e)
            }


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

async def get_question_batching_service(db: AsyncSession) -> QuestionBatchingService:
    """Factory function to get batching service instance."""
    return QuestionBatchingService(db)
