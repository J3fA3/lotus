"""
Implicit Learning Signal Models - Phase 6 Stage 5

Self-learning system that improves task quality by learning from user behavior.

Design Decisions:
1. Signal Taxonomy: Tier 1 (high-value) + Tier 2 (moderate) signals only
2. Storage: Hybrid (raw events for 90 days + aggregated metrics)
3. Weighting: Bayesian confidence weighting with consistency boost
4. Scope: Hierarchical learning (global → project → user)
5. Schema: Immutable events, time-series optimized, partitioned

Signal Taxonomy:
- Tier 1 (High-Value):
  - AI overrides (user changes AI suggestion)
  - Question engagement (answer vs dismiss patterns)
  - Outcome correlation (quality → completion speed)

- Tier 2 (Medium-Value):
  - Description edit patterns (which sections users change)
  - Auto-fill acceptance (keep vs change rates)
  - Question feedback (helpful vs not helpful)

Learning Hierarchy:
  Global defaults (baseline)
    ↓ (override if sufficient data)
  Project-specific (context)
    ↓ (override if sufficient data)
  User-specific (personalization)

Confidence Weighting Formula:
  signal_strength = base_weight × confidence × recency_factor × consistency_boost
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base
import enum


# ============================================================================
# ENUMS
# ============================================================================

class SignalType(str, enum.Enum):
    """Types of implicit learning signals"""
    # Tier 1: High-value signals
    AI_OVERRIDE = "ai_override"  # User changed AI suggestion
    QUESTION_ANSWERED = "question_answered"  # User answered question
    QUESTION_DISMISSED = "question_dismissed"  # User dismissed question
    OUTCOME_POSITIVE = "outcome_positive"  # Task completed successfully
    OUTCOME_NEGATIVE = "outcome_negative"  # Task abandoned/failed

    # Tier 2: Medium-value signals
    DESCRIPTION_EDITED = "description_edited"  # User edited AI-generated section
    AUTO_FILL_ACCEPTED = "auto_fill_accepted"  # User kept auto-filled value
    AUTO_FILL_REJECTED = "auto_fill_rejected"  # User changed auto-filled value
    QUESTION_FEEDBACK_HELPFUL = "question_feedback_helpful"  # User marked helpful
    QUESTION_FEEDBACK_NOT_HELPFUL = "question_feedback_not_helpful"  # User marked not helpful


class LearningScope(str, enum.Enum):
    """Scope of learning pattern"""
    GLOBAL = "global"  # All users, all projects
    PROJECT = "project"  # Specific project
    USER = "user"  # Specific user


class ModelType(str, enum.Enum):
    """Type of learned model/pattern"""
    PRIORITY_PREDICTION = "priority_prediction"  # Learn priority patterns
    EFFORT_ESTIMATION = "effort_estimation"  # Learn effort patterns
    FIELD_IMPORTANCE = "field_importance"  # Learn which fields users care about
    QUESTION_RELEVANCE = "question_relevance"  # Learn which questions are useful
    DESCRIPTION_QUALITY = "description_quality"  # Learn quality indicators
    AUTO_FILL_CONFIDENCE = "auto_fill_confidence"  # Calibrate confidence thresholds


# ============================================================================
# IMPLICIT SIGNAL MODEL (Raw Events)
# ============================================================================

class ImplicitSignal(Base):
    """
    Raw implicit learning signal (append-only event log).

    Captures user behaviors that indicate quality/preference without explicit rating.
    Immutable once created (audit trail).
    """

    __tablename__ = "implicit_signals"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Signal metadata
    signal_type = Column(SQLEnum(SignalType), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Context (who, what, where)
    user_id = Column(String, nullable=True, index=True)  # User who triggered signal
    task_id = Column(String, nullable=True, index=True)  # Related task
    project_id = Column(String, nullable=True, index=True)  # Related project
    question_id = Column(Integer, nullable=True)  # Related question (if applicable)

    # Signal details (flexible JSON for extensibility)
    signal_data = Column(JSON, nullable=False)
    # Example for AI_OVERRIDE:
    # {
    #   "field_name": "priority",
    #   "ai_suggested": "P2_MEDIUM",
    #   "user_selected": "P1_HIGH",
    #   "ai_confidence": 0.75,
    #   "context": {...}
    # }

    # Weighting
    base_weight = Column(Float, nullable=False, default=1.0)  # Signal type base weight
    confidence = Column(Float, nullable=False, default=1.0)  # 0.0-1.0
    recency_factor = Column(Float, nullable=False, default=1.0)  # Time decay
    final_weight = Column(Float, nullable=False, default=1.0)  # Computed: base × confidence × recency

    # Processing
    processed = Column(Boolean, default=False, index=True)  # Has this been aggregated?
    processed_at = Column(DateTime, nullable=True)

    # Retention (for cleanup)
    retention_days = Column(Integer, default=90)  # Auto-delete after 90 days
    expires_at = Column(DateTime, nullable=True, index=True)

    # Indexes for common queries
    __table_args__ = (
        Index('idx_signal_type_time', 'signal_type', 'created_at'),
        Index('idx_user_signal', 'user_id', 'signal_type', 'created_at'),
        Index('idx_task_signal', 'task_id', 'signal_type'),
        Index('idx_unprocessed', 'processed', 'created_at'),
        Index('idx_expiration', 'expires_at'),
    )


# ============================================================================
# SIGNAL AGGREGATES (Pre-computed Metrics)
# ============================================================================

class SignalAggregate(Base):
    """
    Pre-computed signal aggregates for fast analytics.

    Rolled up daily from raw signals.
    """

    __tablename__ = "signal_aggregates"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Aggregation period
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)
    period_type = Column(String(20), nullable=False, default="daily")  # daily, weekly, monthly

    # Scope
    scope = Column(SQLEnum(LearningScope), nullable=False, index=True)
    scope_id = Column(String, nullable=True, index=True)  # user_id, project_id, or NULL for global

    # Signal type
    signal_type = Column(SQLEnum(SignalType), nullable=False, index=True)

    # Aggregated metrics
    total_count = Column(Integer, default=0)  # Total signals of this type
    weighted_sum = Column(Float, default=0.0)  # Sum of final_weight values
    avg_confidence = Column(Float, default=0.0)  # Average confidence
    unique_users = Column(Integer, default=0)  # Distinct users
    unique_tasks = Column(Integer, default=0)  # Distinct tasks

    # Field-specific aggregates (JSON for flexibility)
    field_aggregates = Column(JSON, default=dict)
    # Example for AI_OVERRIDE on priority:
    # {
    #   "priority": {
    #     "override_count": 25,
    #     "ai_suggested_p1": 10,
    #     "user_selected_p1": 20,
    #     "accuracy": 0.60
    #   }
    # }

    # Trends
    trend_direction = Column(String(20), nullable=True)  # "improving", "declining", "stable"
    trend_magnitude = Column(Float, default=0.0)  # % change from previous period

    # Indexes
    __table_args__ = (
        Index('idx_aggregate_scope', 'scope', 'scope_id', 'period_start'),
        Index('idx_aggregate_signal', 'signal_type', 'period_start'),
    )


# ============================================================================
# LEARNING MODELS (Learned Patterns)
# ============================================================================

class LearningModel(Base):
    """
    Learned patterns/models that guide future AI behavior.

    Example: "For user Alice on Project X, when task title contains 'bug',
             AI should suggest priority=HIGH with confidence=0.9"
    """

    __tablename__ = "learning_models"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Model metadata
    model_type = Column(SQLEnum(ModelType), nullable=False, index=True)
    scope = Column(SQLEnum(LearningScope), nullable=False, index=True)
    scope_id = Column(String, nullable=True, index=True)  # user_id, project_id, or NULL

    # Model details
    model_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Pattern/rule (JSON for flexibility)
    pattern = Column(JSON, nullable=False)
    # Example for PRIORITY_PREDICTION:
    # {
    #   "conditions": {
    #     "task_title_contains": ["bug", "urgent", "critical"],
    #     "task_description_length": "> 100"
    #   },
    #   "prediction": "P1_HIGH",
    #   "confidence": 0.85,
    #   "supporting_signals": 45
    # }

    # Model performance
    sample_size = Column(Integer, default=0)  # How many signals support this
    confidence_score = Column(Float, default=0.0)  # 0.0-1.0
    accuracy = Column(Float, nullable=True)  # If we can measure it
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)

    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)  # When was this pattern last applied?
    active = Column(Boolean, default=True, index=True)  # Can be deactivated if performance drops

    # Training metadata
    trained_on_signal_count = Column(Integer, default=0)
    training_period_start = Column(DateTime, nullable=True)
    training_period_end = Column(DateTime, nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_model_scope', 'scope', 'scope_id', 'model_type', 'active'),
        Index('idx_model_active', 'active', 'model_type', 'confidence_score'),
    )


# ============================================================================
# MODEL PERFORMANCE TRACKING
# ============================================================================

class ModelPerformanceLog(Base):
    """
    Tracks model performance over time to detect drift and improvements.

    Critical for validating that learning actually improves outcomes.
    """

    __tablename__ = "model_performance_logs"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Model reference
    model_id = Column(Integer, nullable=False, index=True)  # FK to learning_models
    model_type = Column(SQLEnum(ModelType), nullable=False)

    # Evaluation period
    evaluated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    evaluation_period_start = Column(DateTime, nullable=False)
    evaluation_period_end = Column(DateTime, nullable=False)

    # Performance metrics
    predictions_made = Column(Integer, default=0)
    predictions_correct = Column(Integer, default=0)
    predictions_incorrect = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)

    # Business impact
    tasks_improved = Column(Integer, default=0)  # Tasks where AI helped
    tasks_degraded = Column(Integer, default=0)  # Tasks where AI hurt
    user_satisfaction = Column(Float, nullable=True)  # Avg feedback score
    time_saved_seconds = Column(Integer, default=0)  # Estimated time savings

    # Comparison baseline
    baseline_accuracy = Column(Float, nullable=True)  # Accuracy before learning
    improvement_pct = Column(Float, nullable=True)  # % improvement vs baseline

    # Indexes
    __table_args__ = (
        Index('idx_performance_model', 'model_id', 'evaluated_at'),
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_signal_base_weight(signal_type: SignalType) -> float:
    """
    Get base weight for signal type (before confidence/recency adjustments).

    Based on signal strength and reliability.
    """
    weights = {
        # Tier 1: High-value signals (0.8-1.0)
        SignalType.AI_OVERRIDE: 1.0,  # Strongest signal (explicit disagreement)
        SignalType.QUESTION_ANSWERED: 0.8,  # Strong (user engaged)
        SignalType.OUTCOME_POSITIVE: 0.9,  # Very strong (measurable success)
        SignalType.OUTCOME_NEGATIVE: 0.9,  # Very strong (measurable failure)

        # Tier 2: Medium-value signals (0.3-0.6)
        SignalType.QUESTION_DISMISSED: 0.3,  # Weak (maybe just busy)
        SignalType.DESCRIPTION_EDITED: 0.5,  # Medium (could be for many reasons)
        SignalType.AUTO_FILL_ACCEPTED: 0.6,  # Medium-strong (implicit approval)
        SignalType.AUTO_FILL_REJECTED: 0.7,  # Strong (explicit rejection)
        SignalType.QUESTION_FEEDBACK_HELPFUL: 0.8,  # Strong (explicit positive)
        SignalType.QUESTION_FEEDBACK_NOT_HELPFUL: 0.7,  # Strong (explicit negative)
    }
    return weights.get(signal_type, 0.5)


def calculate_recency_factor(created_at: datetime, decay_days: int = 30) -> float:
    """
    Calculate time decay factor (recent signals weighted higher).

    Exponential decay over decay_days period.
    """
    from datetime import datetime, timedelta

    age = datetime.utcnow() - created_at
    days = age.total_seconds() / 86400

    # Exponential decay: 1.0 at 0 days, 0.5 at decay_days, approaches 0
    factor = max(0.1, min(1.0, 2 ** (-days / decay_days)))

    return round(factor, 3)


def calculate_consistency_boost(signal_count: int, threshold: int = 10) -> float:
    """
    Boost weight for consistent patterns (user does same thing repeatedly).

    Args:
        signal_count: Number of times user exhibited this pattern
        threshold: Min count for boost (default 10)

    Returns:
        Multiplier (1.0 = no boost, 1.5 = max boost)
    """
    if signal_count < threshold:
        return 1.0

    # Logarithmic boost: caps at 1.5x for very consistent patterns
    boost = 1.0 + min(0.5, 0.1 * (signal_count - threshold) ** 0.5)

    return round(boost, 2)
