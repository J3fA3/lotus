"""
Contextual Question Queue Service - Phase 6 Stage 4

Intelligent question queue management for task clarification.

Core Responsibilities:
1. Ingest context gaps from task synthesizer
2. Create questions with priority scoring
3. Manage lifecycle (queued → ready → shown → answered)
4. Track user engagement for adaptive learning
5. Apply answers back to tasks (with validation)

Design Decisions:
- Async all the way (non-blocking question processing)
- Engagement-driven prioritization (learn what users care about)
- Fail-safe (errors don't break task creation)
- Outcome tracking (did answer help?)
"""

import logging
import uuid
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, update as sql_update
from datetime import datetime, timedelta

from db.question_queue_models import (
    QuestionQueue,
    QuestionBatch,
    QuestionEngagementMetrics,
    calculate_priority_score,
    get_field_impact,
    calculate_recency_factor,
    should_batch_together
)

logger = logging.getLogger(__name__)


# ============================================================================
# CONTEXTUAL QUESTION ENGINE
# ============================================================================

class QuestionQueueService:
    """
    Service for managing contextual question queue.

    Handles question lifecycle, prioritization, batching, and engagement tracking.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # QUESTION CREATION (FROM CONTEXT GAPS)
    # ========================================================================

    async def create_question_from_context_gap(
        self,
        task_id: str,
        context_gap: Dict,
        task_context: Optional[Dict] = None
    ) -> QuestionQueue:
        """
        Create a question from a context gap detected during task synthesis.

        Args:
            task_id: Task ID
            context_gap: ContextGap dict {field_name, question, importance, suggested_answer, confidence}
            task_context: Snapshot of task state when gap detected

        Returns:
            Created QuestionQueue object
        """
        # Extract context gap fields
        field_name = context_gap.get("field_name", "unknown")
        question = context_gap.get("question", "")
        importance = context_gap.get("importance", "MEDIUM")
        suggested_answer = context_gap.get("suggested_answer")
        confidence = context_gap.get("confidence", 0.5)

        # Calculate priority components
        field_impact = get_field_impact(field_name)
        recency_factor = 1.0  # New question, max recency

        # Get engagement rate for this field (from historical metrics)
        engagement_rate = await self._get_field_engagement_rate(field_name)

        # Calculate priority score
        priority_score = calculate_priority_score(
            importance=importance,
            field_impact=field_impact,
            recency_factor=recency_factor,
            engagement_rate=engagement_rate
        )

        # Determine semantic cluster (for cross-task batching)
        semantic_cluster = self._determine_semantic_cluster(field_name)

        # Create question
        question_obj = QuestionQueue(
            task_id=task_id,
            field_name=field_name,
            question=question,
            suggested_answer=suggested_answer,
            importance=importance,
            confidence=confidence,
            priority_score=priority_score,
            field_impact=field_impact,
            recency_factor=recency_factor,
            semantic_cluster=semantic_cluster,
            status="queued",
            task_context=task_context
        )

        self.db.add(question_obj)
        await self.db.flush()  # Get ID without committing

        logger.info(
            f"Created question {question_obj.id} for task {task_id} "
            f"(field: {field_name}, priority: {priority_score:.2f})"
        )

        return question_obj

    async def create_questions_from_context_gaps(
        self,
        task_id: str,
        context_gaps: List[Dict],
        task_context: Optional[Dict] = None
    ) -> List[QuestionQueue]:
        """
        Create multiple questions from context gaps (batch operation).

        Args:
            task_id: Task ID
            context_gaps: List of ContextGap dicts
            task_context: Snapshot of task state

        Returns:
            List of created QuestionQueue objects
        """
        questions = []
        for gap in context_gaps:
            try:
                question = await self.create_question_from_context_gap(
                    task_id=task_id,
                    context_gap=gap,
                    task_context=task_context
                )
                questions.append(question)
            except Exception as e:
                logger.error(f"Failed to create question from gap: {e}")
                # Continue creating other questions

        await self.db.commit()

        logger.info(f"Created {len(questions)} questions for task {task_id}")

        return questions

    # ========================================================================
    # QUESTION QUERYING
    # ========================================================================

    async def get_ready_questions(
        self,
        limit: int = 10,
        task_id: Optional[str] = None
    ) -> List[QuestionQueue]:
        """
        Get questions ready to be shown to user.

        Ordered by priority score (highest first).

        Args:
            limit: Max questions to return
            task_id: Filter by specific task (optional)

        Returns:
            List of QuestionQueue objects in "ready" status
        """
        query = select(QuestionQueue).where(QuestionQueue.status == "ready")

        if task_id:
            query = query.where(QuestionQueue.task_id == task_id)

        query = query.order_by(desc(QuestionQueue.priority_score)).limit(limit)

        result = await self.db.execute(query)
        questions = list(result.scalars().all())

        return questions

    async def get_pending_questions(
        self,
        task_id: Optional[str] = None,
        limit: int = 50
    ) -> List[QuestionQueue]:
        """
        Get all pending questions (queued or ready).

        Args:
            task_id: Filter by specific task (optional)
            limit: Max questions to return

        Returns:
            List of QuestionQueue objects
        """
        query = select(QuestionQueue).where(
            QuestionQueue.status.in_(["queued", "ready"])
        )

        if task_id:
            query = query.where(QuestionQueue.task_id == task_id)

        query = query.order_by(desc(QuestionQueue.priority_score)).limit(limit)

        result = await self.db.execute(query)
        questions = list(result.scalars().all())

        return questions

    async def get_question(self, question_id: int) -> Optional[QuestionQueue]:
        """Get specific question by ID."""
        result = await self.db.execute(
            select(QuestionQueue).where(QuestionQueue.id == question_id)
        )
        return result.scalar_one_or_none()

    # ========================================================================
    # LIFECYCLE MANAGEMENT
    # ========================================================================

    async def mark_ready(self, question_id: int) -> bool:
        """
        Mark question as ready to be shown.

        Transition: queued → ready

        Args:
            question_id: Question ID

        Returns:
            True if successful
        """
        try:
            await self.db.execute(
                sql_update(QuestionQueue)
                .where(QuestionQueue.id == question_id)
                .values(status="ready", ready_at=datetime.utcnow())
            )
            await self.db.commit()
            logger.info(f"Question {question_id} marked as ready")
            return True
        except Exception as e:
            logger.error(f"Failed to mark question {question_id} as ready: {e}")
            return False

    async def mark_shown(self, question_id: int) -> bool:
        """
        Mark question as shown to user.

        Transition: ready → shown

        Args:
            question_id: Question ID

        Returns:
            True if successful
        """
        try:
            await self.db.execute(
                sql_update(QuestionQueue)
                .where(QuestionQueue.id == question_id)
                .values(status="shown", shown_at=datetime.utcnow())
            )
            await self.db.commit()
            logger.info(f"Question {question_id} marked as shown")
            return True
        except Exception as e:
            logger.error(f"Failed to mark question {question_id} as shown: {e}")
            return False

    async def answer_question(
        self,
        question_id: int,
        answer: str,
        answer_source: str = "user_input",
        feedback: Optional[str] = None,
        feedback_comment: Optional[str] = None
    ) -> bool:
        """
        Record user's answer to a question.

        Transition: shown → answered

        Args:
            question_id: Question ID
            answer: User's answer
            answer_source: "user_input", "selected_suggestion", etc.
            feedback: "helpful", "not_helpful" (optional)
            feedback_comment: User's feedback comment (optional)

        Returns:
            True if successful
        """
        try:
            await self.db.execute(
                sql_update(QuestionQueue)
                .where(QuestionQueue.id == question_id)
                .values(
                    status="answered",
                    answer=answer,
                    answer_source=answer_source,
                    answered_at=datetime.utcnow(),
                    user_feedback=feedback,
                    user_feedback_comment=feedback_comment
                )
            )
            await self.db.commit()

            logger.info(
                f"Question {question_id} answered (source: {answer_source}, "
                f"feedback: {feedback})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to answer question {question_id}: {e}")
            return False

    async def dismiss_question(self, question_id: int) -> bool:
        """
        User dismissed question without answering.

        Transition: shown → dismissed

        Args:
            question_id: Question ID

        Returns:
            True if successful
        """
        try:
            await self.db.execute(
                sql_update(QuestionQueue)
                .where(QuestionQueue.id == question_id)
                .values(
                    status="dismissed",
                    answered_at=datetime.utcnow(),
                    answer_source="dismissed"
                )
            )
            await self.db.commit()
            logger.info(f"Question {question_id} dismissed")
            return True
        except Exception as e:
            logger.error(f"Failed to dismiss question {question_id}: {e}")
            return False

    async def snooze_question(
        self,
        question_id: int,
        snooze_hours: int = 24
    ) -> bool:
        """
        Snooze question (show again later).

        Transition: shown → snoozed

        Args:
            question_id: Question ID
            snooze_hours: Hours to snooze (default 24)

        Returns:
            True if successful
        """
        try:
            snooze_until = datetime.utcnow() + timedelta(hours=snooze_hours)

            await self.db.execute(
                sql_update(QuestionQueue)
                .where(QuestionQueue.id == question_id)
                .values(
                    status="snoozed",
                    snoozed_until=snooze_until
                )
            )
            await self.db.commit()

            logger.info(f"Question {question_id} snoozed until {snooze_until}")
            return True
        except Exception as e:
            logger.error(f"Failed to snooze question {question_id}: {e}")
            return False

    async def wake_snoozed_questions(self) -> int:
        """
        Wake up snoozed questions whose snooze time has passed.

        Transition: snoozed → ready

        Returns:
            Number of questions woken up
        """
        try:
            result = await self.db.execute(
                sql_update(QuestionQueue)
                .where(
                    and_(
                        QuestionQueue.status == "snoozed",
                        QuestionQueue.snoozed_until <= datetime.utcnow()
                    )
                )
                .values(status="ready", ready_at=datetime.utcnow())
            )
            await self.db.commit()

            count = result.rowcount
            logger.info(f"Woke up {count} snoozed questions")
            return count
        except Exception as e:
            logger.error(f"Failed to wake snoozed questions: {e}")
            return 0

    # ========================================================================
    # ANSWER APPLICATION (TO TASKS)
    # ========================================================================

    async def apply_answer_to_task(
        self,
        question_id: int,
        user_approved: bool = True
    ) -> bool:
        """
        Apply question answer to the task (update task field).

        This should be called AFTER user reviews the suggested update.

        Args:
            question_id: Question ID
            user_approved: User explicitly approved the update

        Returns:
            True if successful
        """
        try:
            # Get question
            question = await self.get_question(question_id)
            if not question or not question.answer:
                logger.warning(f"Question {question_id} has no answer to apply")
                return False

            # Get task
            from db.models import Task
            result = await self.db.execute(
                select(Task).where(Task.id == question.task_id)
            )
            task = result.scalar_one_or_none()

            if not task:
                logger.error(f"Task {question.task_id} not found")
                return False

            # Apply answer to task field
            # This is a simplified version - in production, add validation
            field_name = question.field_name
            answer = question.answer

            if hasattr(task, field_name):
                setattr(task, field_name, answer)
                task.updated_at = datetime.utcnow()

                # Mark question as applied
                question.answer_applied = True

                await self.db.commit()

                logger.info(
                    f"Applied answer from question {question_id} to task {question.task_id} "
                    f"(field: {field_name}, value: {answer})"
                )
                return True
            else:
                logger.warning(f"Task does not have field: {field_name}")
                return False

        except Exception as e:
            logger.error(f"Failed to apply answer from question {question_id}: {e}")
            await self.db.rollback()
            return False

    # ========================================================================
    # ENGAGEMENT TRACKING
    # ========================================================================

    async def track_outcome(
        self,
        question_id: int,
        outcome_impact: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Track the outcome impact of a question (learning signal).

        Args:
            question_id: Question ID
            outcome_impact: "high_impact", "medium_impact", "low_impact", "no_impact"
            notes: Optional notes

        Returns:
            True if successful
        """
        try:
            await self.db.execute(
                sql_update(QuestionQueue)
                .where(QuestionQueue.id == question_id)
                .values(
                    outcome_impact=outcome_impact,
                    outcome_tracked=True,
                    outcome_notes=notes
                )
            )
            await self.db.commit()

            logger.info(f"Tracked outcome for question {question_id}: {outcome_impact}")
            return True
        except Exception as e:
            logger.error(f"Failed to track outcome for question {question_id}: {e}")
            return False

    async def update_engagement_metrics(self) -> bool:
        """
        Update aggregated engagement metrics for adaptive learning.

        Should be called periodically (e.g., daily cron job).

        Returns:
            True if successful
        """
        try:
            # This is a simplified version - in production, add more sophisticated metrics
            period_start = datetime.utcnow() - timedelta(days=30)
            period_end = datetime.utcnow()

            # Count question statistics
            total_result = await self.db.execute(
                select(func.count(QuestionQueue.id))
                .where(QuestionQueue.created_at >= period_start)
            )
            total_questions = total_result.scalar()

            shown_result = await self.db.execute(
                select(func.count(QuestionQueue.id))
                .where(
                    and_(
                        QuestionQueue.created_at >= period_start,
                        QuestionQueue.shown_at.isnot(None)
                    )
                )
            )
            questions_shown = shown_result.scalar()

            answered_result = await self.db.execute(
                select(func.count(QuestionQueue.id))
                .where(
                    and_(
                        QuestionQueue.created_at >= period_start,
                        QuestionQueue.status == "answered"
                    )
                )
            )
            questions_answered = answered_result.scalar()

            # Calculate rates
            helpful_result = await self.db.execute(
                select(func.count(QuestionQueue.id))
                .where(
                    and_(
                        QuestionQueue.created_at >= period_start,
                        QuestionQueue.user_feedback == "helpful"
                    )
                )
            )
            helpful_count = helpful_result.scalar()
            helpful_rate = (helpful_count / questions_answered) if questions_answered > 0 else 0.0

            # Create/update metrics record
            metrics = QuestionEngagementMetrics(
                period_start=period_start,
                period_end=period_end,
                period_type="30_day",
                total_questions=total_questions,
                questions_shown=questions_shown,
                questions_answered=questions_answered,
                helpful_rate=helpful_rate
            )

            self.db.add(metrics)
            await self.db.commit()

            logger.info(f"Updated engagement metrics: {total_questions} total, {helpful_rate:.2%} helpful")
            return True

        except Exception as e:
            logger.error(f"Failed to update engagement metrics: {e}")
            return False

    # ========================================================================
    # PRIVATE HELPERS
    # ========================================================================

    async def _get_field_engagement_rate(self, field_name: str) -> float:
        """
        Get historical engagement rate for a field.

        Returns:
            Engagement rate 0.0-1.0 (default 0.5)
        """
        # Simplified: return default for now
        # In production, query QuestionEngagementMetrics
        return 0.5

    def _determine_semantic_cluster(self, field_name: str) -> str:
        """
        Determine semantic cluster for cross-task batching.

        Args:
            field_name: Field name

        Returns:
            Semantic cluster name
        """
        # Group related fields
        priority_planning = {"priority", "effort_estimate", "due_date"}
        team_coordination = {"assignee", "project", "dependencies"}
        metadata_fields = {"tags", "notes", "color", "icon"}

        if field_name in priority_planning:
            return "priority_planning"
        elif field_name in team_coordination:
            return "team_coordination"
        elif field_name in metadata_fields:
            return "metadata"
        else:
            return "general"


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

async def get_question_queue_service(db: AsyncSession) -> QuestionQueueService:
    """Factory function to get question queue service instance."""
    return QuestionQueueService(db)
