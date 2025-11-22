"""
Outcome-Based Learning Priority Models - Phase 6 Stage 5

Connects task outcomes to description quality for outcome-driven learning.

Design Decisions:
1. Outcome taxonomy: Completion (primary) + Process (secondary) + Failure (negative)
2. Correlation method: Causal inference with feature attribution
3. Learning priority: Outcome-impact weighted (not just signal frequency)
4. Measurement timing: Hybrid (immediate + retrospective validation)
5. Schema: Extend task_outcomes + add correlation analysis tables

Outcome-Impact Formula:
  learning_priority = base_signal_weight × outcome_impact × sample_size_factor

Feature Attribution Formula:
  outcome_score = Σ(feature_i × weight_i × impact_i)

This enables learning from what actually works, not just what users do.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text, Index
from datetime import datetime
from db.database import Base


# ============================================================================
# OUTCOME QUALITY CORRELATIONS
# ============================================================================

class OutcomeQualityCorrelation(Base):
    """
    Tracks correlation between description quality features and task outcomes.

    Example: Tasks with "how_to_approach" section complete 30% faster.

    This table answers: "Which quality features actually improve outcomes?"
    """

    __tablename__ = "outcome_quality_correlations"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Feature being analyzed
    feature_name = Column(String(200), nullable=False, index=True)
    # Examples: "has_how_to_approach", "auto_fill_confidence_high", "answered_priority_question"

    # Correlation metrics
    sample_size = Column(Integer, default=0)  # Tasks analyzed
    tasks_with_feature = Column(Integer, default=0)  # Tasks that had this feature
    tasks_without_feature = Column(Integer, default=0)  # Tasks without this feature

    # Outcome impact (with feature vs without)
    completion_rate_with = Column(Float, default=0.0)  # % completed (with feature)
    completion_rate_without = Column(Float, default=0.0)  # % completed (without)
    completion_rate_impact = Column(Float, default=0.0)  # Percentage point difference

    avg_time_to_complete_with = Column(Float, default=0.0)  # Seconds (with feature)
    avg_time_to_complete_without = Column(Float, default=0.0)  # Seconds (without)
    time_improvement_pct = Column(Float, default=0.0)  # % faster/slower

    edit_rate_with = Column(Float, default=0.0)  # % of text edited (with feature)
    edit_rate_without = Column(Float, default=0.0)  # % of text edited (without)
    edit_reduction_pct = Column(Float, default=0.0)  # % less editing needed

    # Statistical significance
    correlation_coefficient = Column(Float, default=0.0)  # Pearson coefficient (-1 to 1)
    p_value = Column(Float, default=1.0)  # Statistical significance (< 0.05 = significant)
    confidence_interval_low = Column(Float, default=0.0)
    confidence_interval_high = Column(Float, default=0.0)

    # Overall impact score
    impact_score = Column(Float, default=0.0, index=True)
    # Weighted combination of all impacts (0.0-2.0, where 1.0 = neutral)

    impact_category = Column(String(20), default="neutral")
    # "high_positive", "moderate_positive", "neutral", "moderate_negative", "high_negative"

    # Metadata
    last_analyzed = Column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_period_start = Column(DateTime, nullable=True)
    analysis_period_end = Column(DateTime, nullable=True)

    # Scope (global, project, user)
    scope = Column(String(20), default="global", index=True)
    scope_id = Column(String, nullable=True, index=True)

    # Indexes
    __table_args__ = (
        Index('idx_feature_impact', 'feature_name', 'impact_score'),
        Index('idx_scope_feature', 'scope', 'scope_id', 'feature_name'),
    )


# ============================================================================
# LEARNING PRIORITY SCORES
# ============================================================================

class LearningPriorityScore(Base):
    """
    Prioritizes learning signals based on outcome impact.

    Not all signals are equal - prioritize those that improve outcomes.

    Example: "Answering dependencies question" has higher priority than
             "Answering color preference" because it correlates with
             40% faster completion.
    """

    __tablename__ = "learning_priority_scores"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Signal identification
    signal_type = Column(String(50), nullable=False, index=True)
    # From SignalType enum (ai_override, question_answered, etc.)

    signal_context = Column(JSON, nullable=True)
    # Context-specific info (e.g., {"field_name": "priority", "question_field": "dependencies"})

    # Priority scoring components
    base_signal_weight = Column(Float, default=1.0)  # From SignalType (0.3-1.0)
    outcome_impact = Column(Float, default=1.0)  # Measured impact on outcomes (0.0-2.0)
    sample_size_factor = Column(Float, default=1.0)  # Statistical confidence (0.5-1.5)

    # Final priority score
    priority_score = Column(Float, default=1.0, index=True)
    # priority_score = base_signal_weight × outcome_impact × sample_size_factor

    priority_rank = Column(Integer, nullable=True, index=True)
    # Rank among all signals (1 = highest priority)

    # Supporting evidence
    supporting_samples = Column(Integer, default=0)  # Number of signals analyzed
    outcome_improvement = Column(Float, default=0.0)  # % improvement in outcomes
    confidence_level = Column(String(20), default="low")  # "high", "medium", "low"

    # Feature attribution
    correlated_features = Column(JSON, default=list)
    # List of quality features correlated with this signal
    # Example: ["has_how_to_approach", "high_auto_fill_confidence"]

    # Metadata
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    active = Column(Boolean, default=True, index=True)

    # Scope
    scope = Column(String(20), default="global", index=True)
    scope_id = Column(String, nullable=True, index=True)

    # Indexes
    __table_args__ = (
        Index('idx_priority_active', 'active', 'priority_score'),
        Index('idx_signal_priority', 'signal_type', 'priority_score'),
    )


# ============================================================================
# QUALITY FEATURE ANALYSIS
# ============================================================================

class QualityFeatureAnalysis(Base):
    """
    Analyzes individual quality features and their impact.

    A "quality feature" is a measurable aspect of task description:
    - Has "how_to_approach" section
    - Auto-fill confidence > 0.8
    - User answered priority question
    - Description length > 200 words
    """

    __tablename__ = "quality_feature_analysis"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Task reference
    task_id = Column(String, nullable=False, index=True)

    # Task outcome data (from task_outcomes table)
    outcome_status = Column(String(20), nullable=True)  # "completed", "abandoned", "blocked"
    time_to_complete = Column(Integer, nullable=True)  # Seconds
    was_successful = Column(Boolean, default=True)

    # Quality features (boolean presence)
    has_summary = Column(Boolean, default=False)
    has_why_it_matters = Column(Boolean, default=False)
    has_how_to_approach = Column(Boolean, default=False)
    has_success_criteria = Column(Boolean, default=False)
    has_technical_context = Column(Boolean, default=False)

    # Auto-fill features
    auto_fill_count = Column(Integer, default=0)
    auto_fill_avg_confidence = Column(Float, default=0.0)
    auto_fill_accept_rate = Column(Float, default=0.0)

    # Question features
    questions_generated = Column(Integer, default=0)
    questions_answered = Column(Integer, default=0)
    question_answer_rate = Column(Float, default=0.0)
    priority_question_answered = Column(Boolean, default=False)

    # Description quality metrics
    description_word_count = Column(Integer, default=0)
    description_edit_pct = Column(Float, default=0.0)  # % of text user edited
    ai_confidence_avg = Column(Float, default=0.0)  # Average AI confidence

    # Feature vector (for ML later)
    feature_vector = Column(JSON, default=dict)
    # All features in structured format for easy analysis

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    analyzed_at = Column(DateTime, nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_task_outcome', 'task_id', 'outcome_status'),
        Index('idx_outcome_time', 'outcome_status', 'created_at'),
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_impact_score(
    completion_rate_impact: float,
    time_improvement_pct: float,
    edit_reduction_pct: float
) -> float:
    """
    Calculate overall impact score from individual metrics.

    Weighted combination:
    - Completion rate: 50% weight (most important)
    - Time improvement: 30% weight
    - Edit reduction: 20% weight

    Returns:
        Impact score (0.0-2.0, where 1.0 = neutral)
    """
    # Normalize to 0.0-2.0 scale
    completion_impact = 1.0 + (completion_rate_impact / 100.0)  # % points → multiplier
    time_impact = 1.0 + (time_improvement_pct / 100.0)  # % improvement → multiplier
    edit_impact = 1.0 + (edit_reduction_pct / 100.0)  # % reduction → multiplier

    # Weighted combination
    impact_score = (
        0.5 * completion_impact +
        0.3 * time_impact +
        0.2 * edit_impact
    )

    return round(impact_score, 3)


def classify_impact(impact_score: float) -> str:
    """
    Classify impact score into category.

    Returns:
        Impact category string
    """
    if impact_score >= 1.3:
        return "high_positive"
    elif impact_score >= 1.1:
        return "moderate_positive"
    elif impact_score >= 0.9:
        return "neutral"
    elif impact_score >= 0.7:
        return "moderate_negative"
    else:
        return "high_negative"


def calculate_learning_priority(
    base_weight: float,
    outcome_impact: float,
    sample_size: int,
    min_samples: int = 10
) -> float:
    """
    Calculate learning priority score.

    Formula: priority = base_weight × outcome_impact × sample_size_factor

    Args:
        base_weight: Signal type base weight (0.3-1.0)
        outcome_impact: Measured impact on outcomes (0.0-2.0)
        sample_size: Number of samples
        min_samples: Minimum samples for confidence

    Returns:
        Priority score (higher = more important to learn from)
    """
    import math

    # Sample size confidence factor
    if sample_size < min_samples:
        sample_size_factor = 0.5  # Low confidence
    else:
        # sqrt growth, capped at 1.5x
        sample_size_factor = min(1.5, math.sqrt(sample_size / min_samples))

    priority = base_weight * outcome_impact * sample_size_factor

    return round(priority, 3)


def get_confidence_level(sample_size: int, p_value: float) -> str:
    """
    Determine confidence level for correlation.

    Args:
        sample_size: Number of samples
        p_value: Statistical significance

    Returns:
        Confidence level: "high", "medium", "low"
    """
    if sample_size >= 100 and p_value < 0.01:
        return "high"
    elif sample_size >= 30 and p_value < 0.05:
        return "medium"
    else:
        return "low"
