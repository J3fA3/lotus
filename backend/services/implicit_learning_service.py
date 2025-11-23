"""
Implicit Learning Service - Phase 6 Stage 5

The "brain" that learns from user behavior and improves AI over time.

Core Responsibilities:
1. Signal Capture: Record implicit signals from user actions
2. Signal Aggregation: Roll up raw signals into analytics
3. Pattern Extraction: Train learning models from signals
4. Model Application: Apply learned patterns to improve AI
5. Performance Tracking: Validate that learning improves outcomes

Design Principles:
- Fail-safe: Learning errors don't break primary flows
- Async: Non-blocking signal capture
- Hierarchical: Global → Project → User learning
- Validated: Track performance, deactivate poor models
- Privacy-respecting: No PII, aggregated analytics only
"""

import logging
import json
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, update as sql_update
from datetime import datetime, timedelta

from db.implicit_learning_models import (
    ImplicitSignal,
    SignalAggregate,
    LearningModel,
    ModelPerformanceLog,
    SignalType,
    LearningScope,
    ModelType,
    get_signal_base_weight,
    calculate_recency_factor,
    calculate_consistency_boost
)

logger = logging.getLogger(__name__)


# ============================================================================
# IMPLICIT LEARNING SERVICE
# ============================================================================

class ImplicitLearningService:
    """
    Service for capturing and learning from implicit user signals.

    This is the self-improvement engine that makes the AI progressively better.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

        # Minimum samples for statistical significance
        self.MIN_SAMPLES_FOR_PATTERN = 10
        self.MIN_SAMPLES_FOR_USER_MODEL = 15
        self.MIN_SAMPLES_FOR_PROJECT_MODEL = 20

        # Confidence thresholds
        self.MIN_MODEL_CONFIDENCE = 0.6  # Don't use models below this
        self.MIN_MODEL_ACCURACY = 0.65  # Deactivate if below this

    # ========================================================================
    # SIGNAL CAPTURE
    # ========================================================================

    async def capture_signal(
        self,
        signal_type: SignalType,
        signal_data: Dict,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        project_id: Optional[str] = None,
        question_id: Optional[int] = None,
        confidence: float = 1.0
    ) -> Optional[ImplicitSignal]:
        """
        Capture an implicit learning signal.

        This is the entry point for all learning signals across the system.

        Args:
            signal_type: Type of signal (AI_OVERRIDE, QUESTION_ANSWERED, etc.)
            signal_data: Signal-specific data (flexible JSON)
            user_id: User who triggered signal
            task_id: Related task
            project_id: Related project
            question_id: Related question (if applicable)
            confidence: AI's confidence in the signal (0.0-1.0)

        Returns:
            Created signal or None if capture failed
        """
        try:
            # Calculate weights
            base_weight = get_signal_base_weight(signal_type)
            recency_factor = 1.0  # New signal, max recency
            final_weight = base_weight * confidence * recency_factor

            # Calculate expiration
            retention_days = 90
            expires_at = datetime.utcnow() + timedelta(days=retention_days)

            # Create signal
            signal = ImplicitSignal(
                signal_type=signal_type,
                user_id=user_id,
                task_id=task_id,
                project_id=project_id,
                question_id=question_id,
                signal_data=signal_data,
                base_weight=base_weight,
                confidence=confidence,
                recency_factor=recency_factor,
                final_weight=final_weight,
                retention_days=retention_days,
                expires_at=expires_at,
                processed=False
            )

            self.db.add(signal)
            await self.db.commit()

            logger.info(
                f"Captured signal: {signal_type.value} "
                f"(user={user_id}, task={task_id}, weight={final_weight:.2f})"
            )

            return signal

        except Exception as e:
            logger.error(f"Failed to capture signal {signal_type}: {e}")
            await self.db.rollback()
            return None

    async def capture_ai_override(
        self,
        field_name: str,
        ai_suggested: any,
        user_selected: any,
        ai_confidence: float,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        project_id: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Optional[ImplicitSignal]:
        """
        Convenience method for capturing AI override signals.

        This is a Tier 1 (high-value) signal.

        Args:
            field_name: Which field was overridden (priority, effort, etc.)
            ai_suggested: What AI recommended
            user_selected: What user actually chose
            ai_confidence: AI's confidence in its suggestion
            ...context: Additional context

        Returns:
            Created signal
        """
        signal_data = {
            "field_name": field_name,
            "ai_suggested": str(ai_suggested),
            "user_selected": str(user_selected),
            "ai_confidence": ai_confidence,
            "context": context or {}
        }

        return await self.capture_signal(
            signal_type=SignalType.AI_OVERRIDE,
            signal_data=signal_data,
            user_id=user_id,
            task_id=task_id,
            project_id=project_id,
            confidence=ai_confidence  # Use AI's confidence
        )

    async def capture_question_engagement(
        self,
        question_id: int,
        answered: bool,
        helpful_feedback: Optional[bool] = None,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> Optional[ImplicitSignal]:
        """
        Capture question engagement signal (answered or dismissed).

        Args:
            question_id: Question ID
            answered: True if answered, False if dismissed
            helpful_feedback: User's feedback (if provided)
            ...

        Returns:
            Created signal
        """
        if answered:
            signal_type = SignalType.QUESTION_ANSWERED
        else:
            signal_type = SignalType.QUESTION_DISMISSED

        signal_data = {
            "question_id": question_id,
            "answered": answered,
            "helpful_feedback": helpful_feedback
        }

        return await self.capture_signal(
            signal_type=signal_type,
            signal_data=signal_data,
            user_id=user_id,
            task_id=task_id,
            question_id=question_id
        )

    # ========================================================================
    # SIGNAL AGGREGATION
    # ========================================================================

    async def aggregate_signals_daily(
        self,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> int:
        """
        Aggregate unprocessed signals into daily rollups.

        This should be run as a daily cron job.

        Args:
            period_start: Start of period (default: yesterday)
            period_end: End of period (default: today)

        Returns:
            Number of aggregates created
        """
        try:
            # Default to yesterday's signals
            if not period_start:
                period_start = datetime.utcnow() - timedelta(days=1)
                period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)

            if not period_end:
                period_end = period_start + timedelta(days=1)

            logger.info(f"Aggregating signals from {period_start} to {period_end}")

            # Get unprocessed signals in period
            result = await self.db.execute(
                select(ImplicitSignal)
                .where(
                    and_(
                        ImplicitSignal.processed == False,
                        ImplicitSignal.created_at >= period_start,
                        ImplicitSignal.created_at < period_end
                    )
                )
            )
            signals = list(result.scalars().all())

            if not signals:
                logger.info("No unprocessed signals to aggregate")
                return 0

            # Group signals by (scope, scope_id, signal_type)
            aggregates_to_create = {}

            for signal in signals:
                # Create aggregates for each scope level
                scopes = [
                    (LearningScope.GLOBAL, None),
                    (LearningScope.PROJECT, signal.project_id) if signal.project_id else None,
                    (LearningScope.USER, signal.user_id) if signal.user_id else None
                ]

                for scope_info in scopes:
                    if scope_info is None:
                        continue

                    scope, scope_id = scope_info
                    key = (scope, scope_id, signal.signal_type)

                    if key not in aggregates_to_create:
                        aggregates_to_create[key] = []

                    aggregates_to_create[key].append(signal)

            # Create aggregates
            aggregates_created = 0
            for (scope, scope_id, signal_type), signal_group in aggregates_to_create.items():
                aggregate = await self._create_aggregate(
                    scope=scope,
                    scope_id=scope_id,
                    signal_type=signal_type,
                    signals=signal_group,
                    period_start=period_start,
                    period_end=period_end
                )

                if aggregate:
                    aggregates_created += 1

            # Mark signals as processed
            for signal in signals:
                signal.processed = True
                signal.processed_at = datetime.utcnow()

            await self.db.commit()

            logger.info(f"Created {aggregates_created} aggregates from {len(signals)} signals")

            return aggregates_created

        except Exception as e:
            logger.error(f"Failed to aggregate signals: {e}")
            await self.db.rollback()
            return 0

    async def _create_aggregate(
        self,
        scope: LearningScope,
        scope_id: Optional[str],
        signal_type: SignalType,
        signals: List[ImplicitSignal],
        period_start: datetime,
        period_end: datetime
    ) -> Optional[SignalAggregate]:
        """Create a single aggregate from group of signals."""
        try:
            total_count = len(signals)
            weighted_sum = sum(s.final_weight for s in signals)
            avg_confidence = sum(s.confidence for s in signals) / total_count
            unique_users = len(set(s.user_id for s in signals if s.user_id))
            unique_tasks = len(set(s.task_id for s in signals if s.task_id))

            # Field-specific aggregates (for AI overrides)
            field_aggregates = {}
            if signal_type == SignalType.AI_OVERRIDE:
                for signal in signals:
                    field_name = signal.signal_data.get("field_name")
                    if field_name:
                        if field_name not in field_aggregates:
                            field_aggregates[field_name] = {
                                "override_count": 0,
                                "ai_suggestions": {},
                                "user_selections": {}
                            }

                        field_aggregates[field_name]["override_count"] += 1

                        ai_suggested = signal.signal_data.get("ai_suggested")
                        user_selected = signal.signal_data.get("user_selected")

                        if ai_suggested:
                            field_aggregates[field_name]["ai_suggestions"][ai_suggested] = \
                                field_aggregates[field_name]["ai_suggestions"].get(ai_suggested, 0) + 1

                        if user_selected:
                            field_aggregates[field_name]["user_selections"][user_selected] = \
                                field_aggregates[field_name]["user_selections"].get(user_selected, 0) + 1

            aggregate = SignalAggregate(
                period_start=period_start,
                period_end=period_end,
                period_type="daily",
                scope=scope,
                scope_id=scope_id,
                signal_type=signal_type,
                total_count=total_count,
                weighted_sum=weighted_sum,
                avg_confidence=avg_confidence,
                unique_users=unique_users,
                unique_tasks=unique_tasks,
                field_aggregates=field_aggregates if field_aggregates else None
            )

            self.db.add(aggregate)

            return aggregate

        except Exception as e:
            logger.error(f"Failed to create aggregate: {e}")
            return None

    # ========================================================================
    # PATTERN EXTRACTION & MODEL TRAINING
    # ========================================================================

    async def train_models_from_aggregates(
        self,
        min_samples: Optional[int] = None
    ) -> int:
        """
        Train learning models from aggregated signals.

        Extracts patterns and creates/updates models.

        Args:
            min_samples: Minimum samples required for training (default: self.MIN_SAMPLES_FOR_PATTERN)

        Returns:
            Number of models trained
        """
        if min_samples is None:
            min_samples = self.MIN_SAMPLES_FOR_PATTERN

        try:
            logger.info(f"Training models (min_samples={min_samples})")

            models_trained = 0

            # Train priority prediction models
            models_trained += await self._train_priority_models(min_samples)

            # Train field importance models
            models_trained += await self._train_field_importance_models(min_samples)

            # Train question relevance models
            models_trained += await self._train_question_relevance_models(min_samples)

            await self.db.commit()

            logger.info(f"Trained {models_trained} models")

            return models_trained

        except Exception as e:
            logger.error(f"Failed to train models: {e}")
            await self.db.rollback()
            return 0

    async def _train_priority_models(self, min_samples: int) -> int:
        """
        Train priority prediction models from AI override signals.

        Example pattern: "When task title contains 'bug', users override AI to set priority=HIGH"
        """
        try:
            # Get AI override signals for priority field
            result = await self.db.execute(
                select(SignalAggregate)
                .where(
                    and_(
                        SignalAggregate.signal_type == SignalType.AI_OVERRIDE,
                        SignalAggregate.total_count >= min_samples
                    )
                )
            )
            aggregates = list(result.scalars().all())

            models_trained = 0

            for aggregate in aggregates:
                if not aggregate.field_aggregates:
                    continue

                priority_data = aggregate.field_aggregates.get("priority")
                if not priority_data:
                    continue

                # Analyze override patterns
                override_count = priority_data.get("override_count", 0)
                if override_count < min_samples:
                    continue

                user_selections = priority_data.get("user_selections", {})
                if not user_selections:
                    continue

                # Find most common user selection
                most_common_priority = max(user_selections, key=user_selections.get)
                frequency = user_selections[most_common_priority] / override_count

                if frequency < 0.6:  # Need at least 60% consistency
                    continue

                # Create/update model
                model = await self._create_or_update_model(
                    model_type=ModelType.PRIORITY_PREDICTION,
                    scope=aggregate.scope,
                    scope_id=aggregate.scope_id,
                    pattern={
                        "field": "priority",
                        "prediction": most_common_priority,
                        "conditions": {},  # Could add task title patterns here
                        "supporting_signals": override_count
                    },
                    confidence=frequency,
                    sample_size=override_count
                )

                if model:
                    models_trained += 1

            return models_trained

        except Exception as e:
            logger.error(f"Failed to train priority models: {e}")
            return 0

    async def _train_field_importance_models(self, min_samples: int) -> int:
        """
        Train field importance models from question engagement.

        Learns which fields users care about (answer questions) vs ignore (dismiss).
        """
        try:
            # Get question answer/dismiss aggregates
            result = await self.db.execute(
                select(SignalAggregate)
                .where(
                    and_(
                        SignalAggregate.signal_type.in_([
                            SignalType.QUESTION_ANSWERED,
                            SignalType.QUESTION_DISMISSED
                        ]),
                        SignalAggregate.total_count >= min_samples
                    )
                )
            )
            aggregates = list(result.scalars().all())

            # Group by scope
            scope_data = {}
            for agg in aggregates:
                key = (agg.scope, agg.scope_id)
                if key not in scope_data:
                    scope_data[key] = {"answered": 0, "dismissed": 0}

                if agg.signal_type == SignalType.QUESTION_ANSWERED:
                    scope_data[key]["answered"] += agg.total_count
                else:
                    scope_data[key]["dismissed"] += agg.total_count

            models_trained = 0

            for (scope, scope_id), data in scope_data.items():
                total = data["answered"] + data["dismissed"]
                if total < min_samples:
                    continue

                answer_rate = data["answered"] / total

                # Create field importance model
                model = await self._create_or_update_model(
                    model_type=ModelType.FIELD_IMPORTANCE,
                    scope=scope,
                    scope_id=scope_id,
                    pattern={
                        "answer_rate": answer_rate,
                        "answered_count": data["answered"],
                        "dismissed_count": data["dismissed"],
                        "interpretation": "high" if answer_rate > 0.7 else "medium" if answer_rate > 0.4 else "low"
                    },
                    confidence=answer_rate,
                    sample_size=total
                )

                if model:
                    models_trained += 1

            return models_trained

        except Exception as e:
            logger.error(f"Failed to train field importance models: {e}")
            return 0

    async def _train_question_relevance_models(self, min_samples: int) -> int:
        """Train question relevance models from feedback."""
        # Simplified implementation - could be expanded
        return 0

    async def _create_or_update_model(
        self,
        model_type: ModelType,
        scope: LearningScope,
        scope_id: Optional[str],
        pattern: Dict,
        confidence: float,
        sample_size: int
    ) -> Optional[LearningModel]:
        """Create new model or update existing one."""
        try:
            # Check if model exists
            result = await self.db.execute(
                select(LearningModel)
                .where(
                    and_(
                        LearningModel.model_type == model_type,
                        LearningModel.scope == scope,
                        LearningModel.scope_id == scope_id,
                        LearningModel.active == True
                    )
                )
            )
            existing_model = result.scalar_one_or_none()

            if existing_model:
                # Update existing model
                existing_model.pattern = pattern
                existing_model.confidence_score = confidence
                existing_model.sample_size = sample_size
                existing_model.last_updated = datetime.utcnow()
                existing_model.trained_on_signal_count = sample_size
                return existing_model
            else:
                # Create new model
                model = LearningModel(
                    model_type=model_type,
                    scope=scope,
                    scope_id=scope_id,
                    model_name=f"{model_type.value}_{scope.value}_{scope_id or 'global'}",
                    pattern=pattern,
                    confidence_score=confidence,
                    sample_size=sample_size,
                    trained_on_signal_count=sample_size,
                    active=True
                )
                self.db.add(model)
                return model

        except Exception as e:
            logger.error(f"Failed to create/update model: {e}")
            return None

    # ========================================================================
    # MODEL APPLICATION
    # ========================================================================

    async def get_priority_prediction(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        task_context: Optional[Dict] = None
    ) -> Optional[Tuple[str, float]]:
        """
        Get learned priority prediction for a task.

        Uses hierarchical model lookup (user → project → global).

        Returns:
            (priority_value, confidence) or None
        """
        # Try user-specific model first
        if user_id:
            prediction = await self._get_model_prediction(
                ModelType.PRIORITY_PREDICTION,
                LearningScope.USER,
                user_id
            )
            if prediction:
                return prediction

        # Try project-specific model
        if project_id:
            prediction = await self._get_model_prediction(
                ModelType.PRIORITY_PREDICTION,
                LearningScope.PROJECT,
                project_id
            )
            if prediction:
                return prediction

        # Fall back to global model
        prediction = await self._get_model_prediction(
            ModelType.PRIORITY_PREDICTION,
            LearningScope.GLOBAL,
            None
        )

        return prediction

    async def _get_model_prediction(
        self,
        model_type: ModelType,
        scope: LearningScope,
        scope_id: Optional[str]
    ) -> Optional[Tuple[str, float]]:
        """Get prediction from specific model."""
        try:
            result = await self.db.execute(
                select(LearningModel)
                .where(
                    and_(
                        LearningModel.model_type == model_type,
                        LearningModel.scope == scope,
                        LearningModel.scope_id == scope_id,
                        LearningModel.active == True,
                        LearningModel.confidence_score >= self.MIN_MODEL_CONFIDENCE
                    )
                )
                .order_by(desc(LearningModel.confidence_score))
                .limit(1)
            )
            model = result.scalar_one_or_none()

            if not model:
                return None

            # Extract prediction from pattern
            prediction = model.pattern.get("prediction")
            confidence = model.confidence_score

            if prediction:
                return (prediction, confidence)

            return None

        except Exception as e:
            logger.error(f"Failed to get model prediction: {e}")
            return None


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

async def get_implicit_learning_service(db: AsyncSession) -> ImplicitLearningService:
    """Factory function to get implicit learning service instance."""
    return ImplicitLearningService(db)
