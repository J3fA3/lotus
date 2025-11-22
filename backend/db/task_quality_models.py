"""
Task Quality Evaluation Models - Phase 6 Stage 6

Measures and tracks the quality of AI-generated task descriptions.

Design Decisions:
1. Quality dimensions: Completeness (30%) + Clarity (25%) + Actionability (25%) + Relevance (15%) + Confidence (5%)
2. Scoring scale: 0-100 with tier classification (Excellent/Good/Fair/Needs Improvement)
3. Schema: Separate quality_scores table (not extending descriptions) for evolution tracking
4. Metrics: Lightweight calculations (no heavy NLP) for performance
5. Suggestions: Actionable feedback for improvement

Quality Formula:
  overall_score = 0.30×completeness + 0.25×clarity + 0.25×actionability + 0.15×relevance + 0.05×confidence

This provides transparency and builds user trust in AI-generated content.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text, Index, ForeignKey
from datetime import datetime
from db.database import Base


# ============================================================================
# TASK QUALITY SCORE
# ============================================================================

class TaskQualityScore(Base):
    """
    Quality evaluation for AI-generated task descriptions.

    Measures how complete, clear, actionable, and relevant the description is.

    This builds user trust by making quality measurable and visible.
    """

    __tablename__ = "task_quality_scores"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Task reference
    task_id = Column(String, nullable=False, index=True)
    # Maps to tasks.id

    description_id = Column(Integer, nullable=True)
    # Maps to intelligent_task_descriptions.id (if applicable)

    # Overall quality
    overall_score = Column(Float, default=0.0, index=True)
    # 0-100 scale (weighted combination of dimension scores)

    quality_tier = Column(String(20), default="fair", index=True)
    # "excellent" (90-100), "good" (75-89), "fair" (60-74), "needs_improvement" (<60)

    # ========================================================================
    # QUALITY DIMENSIONS (0-100 each)
    # ========================================================================

    # Completeness: Are all sections filled?
    completeness_score = Column(Float, default=0.0)
    # Weight: 30% (most important - can't use what's not there)

    # Clarity: Is it understandable?
    clarity_score = Column(Float, default=0.0)
    # Weight: 25% (understanding is critical)

    # Actionability: Can user act on it?
    actionability_score = Column(Float, default=0.0)
    # Weight: 25% (must be usable)

    # Relevance: Contextually appropriate?
    relevance_score = Column(Float, default=0.0)
    # Weight: 15% (contextual fit)

    # Confidence: How confident is the AI?
    confidence_score = Column(Float, default=0.0)
    # Weight: 5% (AI's own assessment)

    # ========================================================================
    # DETAILED METRICS
    # ========================================================================

    quality_metrics = Column(JSON, default=dict)
    # Detailed breakdown of quality metrics:
    # {
    #   "completeness": {
    #     "fields_filled": 8,
    #     "fields_total": 10,
    #     "fill_rate": 0.80,
    #     "has_summary": true,
    #     "has_why_it_matters": true,
    #     "has_how_to_approach": true,
    #     "has_success_criteria": false,
    #     "has_technical_context": true
    #   },
    #   "clarity": {
    #     "word_count": 350,
    #     "avg_section_length": 70,
    #     "readability_score": 65.2,
    #     "has_structure": true,
    #     "uses_lists": true,
    #     "paragraph_count": 5
    #   },
    #   "actionability": {
    #     "has_steps": true,
    #     "step_count": 5,
    #     "has_criteria": true,
    #     "has_context": true,
    #     "specificity_score": 75.0
    #   },
    #   "relevance": {
    #     "concept_match_count": 5,
    #     "project_alignment": 0.85,
    #     "user_pattern_match": 0.70
    #   },
    #   "confidence": {
    #     "avg_confidence": 0.82,
    #     "min_confidence": 0.65,
    #     "max_confidence": 0.95,
    #     "confidence_variance": 0.08
    #   }
    # }

    # ========================================================================
    # IMPROVEMENT SUGGESTIONS
    # ========================================================================

    suggestions = Column(JSON, default=list)
    # Actionable feedback for improvement:
    # [
    #   {
    #     "category": "completeness",
    #     "severity": "medium",
    #     "message": "Add 'success_criteria' to clarify completion conditions",
    #     "impact": "+15 points"
    #   },
    #   {
    #     "category": "clarity",
    #     "severity": "low",
    #     "message": "Break long paragraphs into bullet points",
    #     "impact": "+5 points"
    #   }
    # ]

    strengths = Column(JSON, default=list)
    # What's working well:
    # [
    #   "Excellent step-by-step approach section",
    #   "Clear technical context with dependencies",
    #   "High AI confidence (avg 0.82)"
    # ]

    # ========================================================================
    # METADATA
    # ========================================================================

    evaluated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    evaluator_version = Column(String(20), default="1.0")
    # Track evaluator evolution (can re-evaluate with newer versions)

    evaluation_time_ms = Column(Integer, default=0)
    # Performance tracking

    # Scope (for filtering)
    user_id = Column(String, nullable=True, index=True)
    project_id = Column(String, nullable=True, index=True)

    # Indexes
    __table_args__ = (
        Index('idx_task_evaluated', 'task_id', 'evaluated_at'),
        Index('idx_quality_tier', 'quality_tier', 'overall_score'),
        Index('idx_user_quality', 'user_id', 'overall_score'),
        Index('idx_project_quality', 'project_id', 'overall_score'),
    )


# ============================================================================
# QUALITY TREND TRACKING
# ============================================================================

class QualityTrend(Base):
    """
    Tracks quality trends over time.

    Answers questions like:
    - Is quality improving as the system learns?
    - Which users get the best quality?
    - Which projects have quality issues?
    """

    __tablename__ = "quality_trends"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Aggregation period
    period_type = Column(String(20), nullable=False, index=True)
    # "daily", "weekly", "monthly"

    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)

    # Scope
    scope = Column(String(20), default="global", index=True)
    # "global", "project", "user"

    scope_id = Column(String, nullable=True, index=True)

    # Aggregated quality metrics
    tasks_evaluated = Column(Integer, default=0)

    avg_overall_score = Column(Float, default=0.0)
    avg_completeness_score = Column(Float, default=0.0)
    avg_clarity_score = Column(Float, default=0.0)
    avg_actionability_score = Column(Float, default=0.0)
    avg_relevance_score = Column(Float, default=0.0)
    avg_confidence_score = Column(Float, default=0.0)

    # Tier distribution
    excellent_count = Column(Integer, default=0)
    good_count = Column(Integer, default=0)
    fair_count = Column(Integer, default=0)
    needs_improvement_count = Column(Integer, default=0)

    # Trend indicators
    score_trend = Column(String(20), nullable=True)
    # "improving", "stable", "declining"

    score_change = Column(Float, default=0.0)
    # Change from previous period

    # Metadata
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_period_scope', 'period_type', 'scope', 'period_start'),
        Index('idx_trend_quality', 'period_start', 'avg_overall_score'),
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def classify_quality_tier(overall_score: float) -> str:
    """
    Classify quality score into tier.

    Args:
        overall_score: Overall quality score (0-100)

    Returns:
        Quality tier: "excellent", "good", "fair", "needs_improvement"
    """
    if overall_score >= 90.0:
        return "excellent"
    elif overall_score >= 75.0:
        return "good"
    elif overall_score >= 60.0:
        return "fair"
    else:
        return "needs_improvement"


def calculate_overall_score(
    completeness: float,
    clarity: float,
    actionability: float,
    relevance: float,
    confidence: float
) -> float:
    """
    Calculate overall quality score from dimension scores.

    Weighted combination:
    - Completeness: 30% (most important)
    - Clarity: 25%
    - Actionability: 25%
    - Relevance: 15%
    - Confidence: 5%

    Args:
        completeness: Completeness score (0-100)
        clarity: Clarity score (0-100)
        actionability: Actionability score (0-100)
        relevance: Relevance score (0-100)
        confidence: Confidence score (0-100)

    Returns:
        Overall score (0-100)
    """
    overall = (
        0.30 * completeness +
        0.25 * clarity +
        0.25 * actionability +
        0.15 * relevance +
        0.05 * confidence
    )

    return round(overall, 2)


def determine_score_trend(current: float, previous: float, threshold: float = 2.0) -> str:
    """
    Determine quality trend.

    Args:
        current: Current period average score
        previous: Previous period average score
        threshold: Minimum change for trend classification

    Returns:
        Trend: "improving", "stable", "declining"
    """
    change = current - previous

    if change >= threshold:
        return "improving"
    elif change <= -threshold:
        return "declining"
    else:
        return "stable"
