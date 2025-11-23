"""
Outcome-Based Learning Service - Phase 6 Stage 5

Correlates task description quality with real-world outcomes to prioritize learning.

Core Responsibilities:
1. Track quality features for each task
2. Correlate features with outcomes (completion, time, edits)
3. Calculate learning priority scores based on impact
4. Provide outcome-driven recommendations for AI

This service answers: "Which quality improvements actually help users succeed?"

Design Pattern: Evidence-based learning (measure, don't assume)
"""

import logging
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from datetime import datetime, timedelta
import statistics

from db.outcome_learning_models import (
    OutcomeQualityCorrelation,
    LearningPriorityScore,
    QualityFeatureAnalysis,
    calculate_impact_score,
    classify_impact,
    calculate_learning_priority,
    get_confidence_level
)

logger = logging.getLogger(__name__)


# ============================================================================
# OUTCOME LEARNING SERVICE
# ============================================================================

class OutcomeLearningService:
    """
    Service for outcome-based learning priority analysis.

    Measures what quality features actually improve task outcomes.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

        # Minimum samples for reliable correlation
        self.MIN_SAMPLES_FOR_CORRELATION = 30
        self.MIN_TASKS_WITH_FEATURE = 10
        self.MIN_TASKS_WITHOUT_FEATURE = 10

        # Statistical significance threshold
        self.P_VALUE_THRESHOLD = 0.05  # p < 0.05 = statistically significant

    # ========================================================================
    # QUALITY FEATURE TRACKING
    # ========================================================================

    async def track_task_quality_features(
        self,
        task_id: str,
        intelligent_description: Optional[Dict] = None,
        questions_data: Optional[Dict] = None,
        auto_fill_data: Optional[Dict] = None
    ) -> Optional[QualityFeatureAnalysis]:
        """
        Track quality features for a task when it's created.

        This captures the "input" side of the correlation.

        Args:
            task_id: Task ID
            intelligent_description: Task description data
            questions_data: Question generation data
            auto_fill_data: Auto-fill data

        Returns:
            Created QualityFeatureAnalysis record
        """
        try:
            # Extract quality features
            has_summary = False
            has_why_it_matters = False
            has_how_to_approach = False
            has_success_criteria = False
            has_technical_context = False
            description_word_count = 0
            ai_confidence_avg = 0.0

            if intelligent_description:
                has_summary = bool(intelligent_description.get("summary"))
                has_why_it_matters = bool(intelligent_description.get("why_it_matters"))
                has_how_to_approach = bool(intelligent_description.get("how_to_approach"))
                has_success_criteria = bool(intelligent_description.get("success_criteria"))
                has_technical_context = bool(intelligent_description.get("technical_context"))

                # Calculate word count
                summary = intelligent_description.get("summary", "")
                why = intelligent_description.get("why_it_matters", {})
                how = intelligent_description.get("how_to_approach", {})

                description_word_count = (
                    len(summary.split()) +
                    len(str(why).split()) +
                    len(str(how).split())
                )

            # Extract question features
            questions_generated = 0
            questions_answered = 0
            question_answer_rate = 0.0
            priority_question_answered = False

            if questions_data:
                questions_generated = questions_data.get("total_questions", 0)
                questions_answered = questions_data.get("answered_count", 0)
                if questions_generated > 0:
                    question_answer_rate = questions_answered / questions_generated
                priority_question_answered = questions_data.get("priority_question_answered", False)

            # Extract auto-fill features
            auto_fill_count = 0
            auto_fill_avg_confidence = 0.0
            auto_fill_accept_rate = 0.0

            if auto_fill_data:
                auto_fill_count = auto_fill_data.get("filled_count", 0)
                auto_fill_avg_confidence = auto_fill_data.get("avg_confidence", 0.0)
                auto_fill_accept_rate = auto_fill_data.get("accept_rate", 0.0)

            # Create feature vector
            feature_vector = {
                "has_summary": has_summary,
                "has_why_it_matters": has_why_it_matters,
                "has_how_to_approach": has_how_to_approach,
                "has_success_criteria": has_success_criteria,
                "has_technical_context": has_technical_context,
                "description_word_count": description_word_count,
                "questions_generated": questions_generated,
                "questions_answered": questions_answered,
                "priority_question_answered": priority_question_answered,
                "auto_fill_count": auto_fill_count,
                "auto_fill_avg_confidence": auto_fill_avg_confidence
            }

            # Create analysis record
            analysis = QualityFeatureAnalysis(
                task_id=task_id,
                has_summary=has_summary,
                has_why_it_matters=has_why_it_matters,
                has_how_to_approach=has_how_to_approach,
                has_success_criteria=has_success_criteria,
                has_technical_context=has_technical_context,
                auto_fill_count=auto_fill_count,
                auto_fill_avg_confidence=auto_fill_avg_confidence,
                auto_fill_accept_rate=auto_fill_accept_rate,
                questions_generated=questions_generated,
                questions_answered=questions_answered,
                question_answer_rate=question_answer_rate,
                priority_question_answered=priority_question_answered,
                description_word_count=description_word_count,
                ai_confidence_avg=ai_confidence_avg,
                feature_vector=feature_vector
            )

            self.db.add(analysis)
            await self.db.commit()

            logger.info(f"Tracked quality features for task {task_id}")

            return analysis

        except Exception as e:
            logger.error(f"Failed to track quality features for task {task_id}: {e}")
            await self.db.rollback()
            return None

    async def update_task_outcome(
        self,
        task_id: str,
        outcome_status: str,
        time_to_complete: Optional[int] = None,
        was_successful: bool = True,
        description_edit_pct: Optional[float] = None
    ) -> bool:
        """
        Update task outcome when task is completed/abandoned.

        This captures the "output" side of the correlation.

        Args:
            task_id: Task ID
            outcome_status: "completed", "abandoned", "blocked"
            time_to_complete: Seconds to complete (if completed)
            was_successful: Whether task was successful
            description_edit_pct: % of AI text user edited

        Returns:
            True if successful
        """
        try:
            # Get quality feature analysis
            result = await self.db.execute(
                select(QualityFeatureAnalysis)
                .where(QualityFeatureAnalysis.task_id == task_id)
            )
            analysis = result.scalar_one_or_none()

            if not analysis:
                logger.warning(f"No quality analysis found for task {task_id}")
                return False

            # Update outcome
            analysis.outcome_status = outcome_status
            analysis.time_to_complete = time_to_complete
            analysis.was_successful = was_successful
            if description_edit_pct is not None:
                analysis.description_edit_pct = description_edit_pct
            analysis.analyzed_at = datetime.utcnow()

            await self.db.commit()

            logger.info(f"Updated outcome for task {task_id}: {outcome_status}")

            return True

        except Exception as e:
            logger.error(f"Failed to update outcome for task {task_id}: {e}")
            await self.db.rollback()
            return False

    # ========================================================================
    # CORRELATION ANALYSIS
    # ========================================================================

    async def analyze_feature_correlations(
        self,
        min_samples: Optional[int] = None
    ) -> int:
        """
        Analyze correlations between quality features and outcomes.

        This should be run periodically (e.g., weekly) to update correlations.

        Args:
            min_samples: Minimum samples required (default: self.MIN_SAMPLES_FOR_CORRELATION)

        Returns:
            Number of correlations analyzed
        """
        if min_samples is None:
            min_samples = self.MIN_SAMPLES_FOR_CORRELATION

        try:
            logger.info(f"Analyzing feature correlations (min_samples={min_samples})")

            correlations_analyzed = 0

            # Analyze each feature
            features_to_analyze = [
                "has_summary",
                "has_why_it_matters",
                "has_how_to_approach",
                "has_success_criteria",
                "has_technical_context",
                "priority_question_answered"
            ]

            for feature_name in features_to_analyze:
                correlation = await self._analyze_single_feature(feature_name, min_samples)
                if correlation:
                    correlations_analyzed += 1

            await self.db.commit()

            logger.info(f"Analyzed {correlations_analyzed} feature correlations")

            return correlations_analyzed

        except Exception as e:
            logger.error(f"Failed to analyze feature correlations: {e}")
            await self.db.rollback()
            return 0

    async def _analyze_single_feature(
        self,
        feature_name: str,
        min_samples: int
    ) -> Optional[OutcomeQualityCorrelation]:
        """
        Analyze correlation for a single feature.

        Compares outcomes: tasks WITH feature vs tasks WITHOUT feature.
        """
        try:
            # Get all completed tasks
            result = await self.db.execute(
                select(QualityFeatureAnalysis)
                .where(
                    and_(
                        QualityFeatureAnalysis.outcome_status == "completed",
                        QualityFeatureAnalysis.time_to_complete.isnot(None)
                    )
                )
            )
            all_tasks = list(result.scalars().all())

            if len(all_tasks) < min_samples:
                return None

            # Split into with/without feature
            tasks_with = [t for t in all_tasks if getattr(t, feature_name, False)]
            tasks_without = [t for t in all_tasks if not getattr(t, feature_name, False)]

            if len(tasks_with) < self.MIN_TASKS_WITH_FEATURE:
                return None
            if len(tasks_without) < self.MIN_TASKS_WITHOUT_FEATURE:
                return None

            # Calculate completion rates (both should be 100% since we filtered)
            completion_rate_with = 1.0
            completion_rate_without = 1.0
            completion_rate_impact = 0.0

            # Calculate average time to complete
            times_with = [t.time_to_complete for t in tasks_with if t.time_to_complete]
            times_without = [t.time_to_complete for t in tasks_without if t.time_to_complete]

            avg_time_with = statistics.mean(times_with) if times_with else 0.0
            avg_time_without = statistics.mean(times_without) if times_without else 0.0

            time_improvement_pct = 0.0
            if avg_time_without > 0:
                time_improvement_pct = ((avg_time_without - avg_time_with) / avg_time_without) * 100

            # Calculate edit rates
            edits_with = [t.description_edit_pct for t in tasks_with if t.description_edit_pct is not None]
            edits_without = [t.description_edit_pct for t in tasks_without if t.description_edit_pct is not None]

            edit_rate_with = statistics.mean(edits_with) if edits_with else 0.0
            edit_rate_without = statistics.mean(edits_without) if edits_without else 0.0

            edit_reduction_pct = 0.0
            if edit_rate_without > 0:
                edit_reduction_pct = ((edit_rate_without - edit_rate_with) / edit_rate_without) * 100

            # Calculate impact score
            impact = calculate_impact_score(
                completion_rate_impact=completion_rate_impact,
                time_improvement_pct=time_improvement_pct,
                edit_reduction_pct=edit_reduction_pct
            )

            impact_cat = classify_impact(impact)

            # Calculate correlation coefficient (simplified - use scipy in production)
            correlation_coef = 0.0  # Placeholder
            p_value = 0.05  # Placeholder

            # Create/update correlation
            result = await self.db.execute(
                select(OutcomeQualityCorrelation)
                .where(
                    and_(
                        OutcomeQualityCorrelation.feature_name == feature_name,
                        OutcomeQualityCorrelation.scope == "global"
                    )
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing
                existing.sample_size = len(all_tasks)
                existing.tasks_with_feature = len(tasks_with)
                existing.tasks_without_feature = len(tasks_without)
                existing.completion_rate_with = completion_rate_with
                existing.completion_rate_without = completion_rate_without
                existing.completion_rate_impact = completion_rate_impact
                existing.avg_time_to_complete_with = avg_time_with
                existing.avg_time_to_complete_without = avg_time_without
                existing.time_improvement_pct = time_improvement_pct
                existing.edit_rate_with = edit_rate_with
                existing.edit_rate_without = edit_rate_without
                existing.edit_reduction_pct = edit_reduction_pct
                existing.impact_score = impact
                existing.impact_category = impact_cat
                existing.last_analyzed = datetime.utcnow()
                return existing
            else:
                # Create new
                correlation = OutcomeQualityCorrelation(
                    feature_name=feature_name,
                    sample_size=len(all_tasks),
                    tasks_with_feature=len(tasks_with),
                    tasks_without_feature=len(tasks_without),
                    completion_rate_with=completion_rate_with,
                    completion_rate_without=completion_rate_without,
                    completion_rate_impact=completion_rate_impact,
                    avg_time_to_complete_with=avg_time_with,
                    avg_time_to_complete_without=avg_time_without,
                    time_improvement_pct=time_improvement_pct,
                    edit_rate_with=edit_rate_with,
                    edit_rate_without=edit_rate_without,
                    edit_reduction_pct=edit_reduction_pct,
                    correlation_coefficient=correlation_coef,
                    p_value=p_value,
                    impact_score=impact,
                    impact_category=impact_cat,
                    scope="global"
                )
                self.db.add(correlation)
                return correlation

        except Exception as e:
            logger.error(f"Failed to analyze feature {feature_name}: {e}")
            return None

    # ========================================================================
    # LEARNING PRIORITY CALCULATION
    # ========================================================================

    async def calculate_learning_priorities(self) -> int:
        """
        Calculate learning priority scores based on outcome impact.

        Prioritizes signals that demonstrably improve outcomes.

        Returns:
            Number of priority scores calculated
        """
        try:
            logger.info("Calculating learning priority scores")

            # Get all feature correlations
            result = await self.db.execute(
                select(OutcomeQualityCorrelation)
                .where(OutcomeQualityCorrelation.impact_score > 0)
            )
            correlations = list(result.scalars().all())

            priorities_created = 0

            for correlation in correlations:
                # Map feature to signal type
                signal_mapping = {
                    "has_how_to_approach": "description_edited",
                    "priority_question_answered": "question_answered",
                    "has_success_criteria": "description_edited"
                }

                signal_type = signal_mapping.get(correlation.feature_name)
                if not signal_type:
                    continue

                # Get base weight (simplified - should come from signal type)
                base_weight = 0.7

                # Use impact score as outcome impact
                outcome_impact = correlation.impact_score

                # Calculate priority
                priority = calculate_learning_priority(
                    base_weight=base_weight,
                    outcome_impact=outcome_impact,
                    sample_size=correlation.sample_size
                )

                # Determine confidence level
                confidence = get_confidence_level(
                    sample_size=correlation.sample_size,
                    p_value=correlation.p_value
                )

                # Create/update priority score
                await self._create_or_update_priority(
                    signal_type=signal_type,
                    signal_context={"feature": correlation.feature_name},
                    base_weight=base_weight,
                    outcome_impact=outcome_impact,
                    priority_score=priority,
                    supporting_samples=correlation.sample_size,
                    outcome_improvement=correlation.time_improvement_pct,
                    confidence_level=confidence,
                    correlated_features=[correlation.feature_name]
                )

                priorities_created += 1

            await self.db.commit()

            logger.info(f"Calculated {priorities_created} learning priority scores")

            return priorities_created

        except Exception as e:
            logger.error(f"Failed to calculate learning priorities: {e}")
            await self.db.rollback()
            return 0

    async def _create_or_update_priority(
        self,
        signal_type: str,
        signal_context: Dict,
        base_weight: float,
        outcome_impact: float,
        priority_score: float,
        supporting_samples: int,
        outcome_improvement: float,
        confidence_level: str,
        correlated_features: List[str]
    ) -> Optional[LearningPriorityScore]:
        """Create or update learning priority score."""
        try:
            # Check if exists
            result = await self.db.execute(
                select(LearningPriorityScore)
                .where(
                    and_(
                        LearningPriorityScore.signal_type == signal_type,
                        LearningPriorityScore.scope == "global"
                    )
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update
                existing.base_signal_weight = base_weight
                existing.outcome_impact = outcome_impact
                existing.priority_score = priority_score
                existing.supporting_samples = supporting_samples
                existing.outcome_improvement = outcome_improvement
                existing.confidence_level = confidence_level
                existing.correlated_features = correlated_features
                existing.calculated_at = datetime.utcnow()
                return existing
            else:
                # Create
                priority = LearningPriorityScore(
                    signal_type=signal_type,
                    signal_context=signal_context,
                    base_signal_weight=base_weight,
                    outcome_impact=outcome_impact,
                    priority_score=priority_score,
                    supporting_samples=supporting_samples,
                    outcome_improvement=outcome_improvement,
                    confidence_level=confidence_level,
                    correlated_features=correlated_features,
                    scope="global"
                )
                self.db.add(priority)
                return priority

        except Exception as e:
            logger.error(f"Failed to create/update priority: {e}")
            return None

    # ========================================================================
    # RECOMMENDATION RETRIEVAL
    # ========================================================================

    async def get_high_impact_features(
        self,
        min_impact_score: float = 1.1,
        limit: int = 10
    ) -> List[OutcomeQualityCorrelation]:
        """
        Get quality features with high outcome impact.

        Returns features that demonstrably improve outcomes.

        Args:
            min_impact_score: Minimum impact score (1.0 = neutral)
            limit: Max features to return

        Returns:
            List of high-impact correlations
        """
        try:
            result = await self.db.execute(
                select(OutcomeQualityCorrelation)
                .where(OutcomeQualityCorrelation.impact_score >= min_impact_score)
                .order_by(desc(OutcomeQualityCorrelation.impact_score))
                .limit(limit)
            )
            correlations = list(result.scalars().all())

            return correlations

        except Exception as e:
            logger.error(f"Failed to get high-impact features: {e}")
            return []


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

async def get_outcome_learning_service(db: AsyncSession) -> OutcomeLearningService:
    """Factory function to get outcome learning service instance."""
    return OutcomeLearningService(db)
