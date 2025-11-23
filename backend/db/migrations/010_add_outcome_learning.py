"""
Migration 010: Add Outcome-Based Learning Priority
Phase 6 Stage 5 - Outcome-Driven Intelligence

Creates tables for outcome correlation analysis and learning prioritization:
- outcome_quality_correlations: Feature → outcome correlations
- learning_priority_scores: Signal prioritization based on impact
- quality_feature_analysis: Per-task quality feature tracking

Run: python backend/db/migrations/010_add_outcome_learning.py
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine as sql_create_engine, MetaData, Table, Column, Integer, String, Float, Boolean, DateTime, JSON, Text, Index
from datetime import datetime
from db.database import get_database_url


def run_migration():
    """Create outcome-based learning tables"""

    # Get database URL and convert to sync
    db_url = get_database_url()
    if db_url.startswith("sqlite+aiosqlite://"):
        db_url = db_url.replace("sqlite+aiosqlite://", "sqlite:///")

    print(f"Connecting to database: {db_url}")
    engine = sql_create_engine(db_url)
    metadata = MetaData()

    # ========================================================================
    # OUTCOME QUALITY CORRELATIONS TABLE
    # ========================================================================

    outcome_quality_correlations = Table(
        "outcome_quality_correlations",
        metadata,
        Column("id", Integer, primary_key=True),

        # Feature being analyzed
        Column("feature_name", String(200), nullable=False, index=True),

        # Correlation metrics
        Column("sample_size", Integer, default=0),
        Column("tasks_with_feature", Integer, default=0),
        Column("tasks_without_feature", Integer, default=0),

        # Outcome impact (with vs without feature)
        Column("completion_rate_with", Float, default=0.0),
        Column("completion_rate_without", Float, default=0.0),
        Column("completion_rate_impact", Float, default=0.0),

        Column("avg_time_to_complete_with", Float, default=0.0),
        Column("avg_time_to_complete_without", Float, default=0.0),
        Column("time_improvement_pct", Float, default=0.0),

        Column("edit_rate_with", Float, default=0.0),
        Column("edit_rate_without", Float, default=0.0),
        Column("edit_reduction_pct", Float, default=0.0),

        # Statistical significance
        Column("correlation_coefficient", Float, default=0.0),
        Column("p_value", Float, default=1.0),
        Column("confidence_interval_low", Float, default=0.0),
        Column("confidence_interval_high", Float, default=0.0),

        # Overall impact
        Column("impact_score", Float, default=0.0, index=True),
        Column("impact_category", String(20), default="neutral"),

        # Metadata
        Column("last_analyzed", DateTime, default=datetime.utcnow, nullable=False),
        Column("analysis_period_start", DateTime, nullable=True),
        Column("analysis_period_end", DateTime, nullable=True),

        # Scope
        Column("scope", String(20), default="global", index=True),
        Column("scope_id", String, nullable=True, index=True),

        # Composite indexes
        Index("idx_feature_impact", "feature_name", "impact_score"),
        Index("idx_scope_feature", "scope", "scope_id", "feature_name"),
    )

    # ========================================================================
    # LEARNING PRIORITY SCORES TABLE
    # ========================================================================

    learning_priority_scores = Table(
        "learning_priority_scores",
        metadata,
        Column("id", Integer, primary_key=True),

        # Signal identification
        Column("signal_type", String(50), nullable=False, index=True),
        Column("signal_context", JSON, nullable=True),

        # Priority scoring components
        Column("base_signal_weight", Float, default=1.0),
        Column("outcome_impact", Float, default=1.0),
        Column("sample_size_factor", Float, default=1.0),

        # Final priority
        Column("priority_score", Float, default=1.0, index=True),
        Column("priority_rank", Integer, nullable=True, index=True),

        # Supporting evidence
        Column("supporting_samples", Integer, default=0),
        Column("outcome_improvement", Float, default=0.0),
        Column("confidence_level", String(20), default="low"),

        # Feature attribution
        Column("correlated_features", JSON, nullable=True),

        # Metadata
        Column("calculated_at", DateTime, default=datetime.utcnow, nullable=False),
        Column("active", Boolean, default=True, index=True),

        # Scope
        Column("scope", String(20), default="global", index=True),
        Column("scope_id", String, nullable=True, index=True),

        # Composite indexes
        Index("idx_priority_active", "active", "priority_score"),
        Index("idx_signal_priority", "signal_type", "priority_score"),
    )

    # ========================================================================
    # QUALITY FEATURE ANALYSIS TABLE
    # ========================================================================

    quality_feature_analysis = Table(
        "quality_feature_analysis",
        metadata,
        Column("id", Integer, primary_key=True),

        # Task reference
        Column("task_id", String, nullable=False, index=True),

        # Task outcome
        Column("outcome_status", String(20), nullable=True),
        Column("time_to_complete", Integer, nullable=True),
        Column("was_successful", Boolean, default=True),

        # Quality features (boolean presence)
        Column("has_summary", Boolean, default=False),
        Column("has_why_it_matters", Boolean, default=False),
        Column("has_how_to_approach", Boolean, default=False),
        Column("has_success_criteria", Boolean, default=False),
        Column("has_technical_context", Boolean, default=False),

        # Auto-fill features
        Column("auto_fill_count", Integer, default=0),
        Column("auto_fill_avg_confidence", Float, default=0.0),
        Column("auto_fill_accept_rate", Float, default=0.0),

        # Question features
        Column("questions_generated", Integer, default=0),
        Column("questions_answered", Integer, default=0),
        Column("question_answer_rate", Float, default=0.0),
        Column("priority_question_answered", Boolean, default=False),

        # Description quality
        Column("description_word_count", Integer, default=0),
        Column("description_edit_pct", Float, default=0.0),
        Column("ai_confidence_avg", Float, default=0.0),

        # Feature vector
        Column("feature_vector", JSON, nullable=True),

        # Timestamps
        Column("created_at", DateTime, default=datetime.utcnow, nullable=False, index=True),
        Column("analyzed_at", DateTime, nullable=True),

        # Composite indexes
        Index("idx_task_outcome", "task_id", "outcome_status"),
        Index("idx_outcome_time", "outcome_status", "created_at"),
    )

    # Create tables
    print("Creating outcome-based learning tables...")
    metadata.create_all(engine)

    print("✅ Migration 010 complete!")
    print("Created tables:")
    print("  - outcome_quality_correlations (with 2 composite indexes)")
    print("  - learning_priority_scores (with 2 composite indexes)")
    print("  - quality_feature_analysis (with 2 composite indexes)")

    # Verify tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print(f"\nAll tables in database ({len(tables)} total)")

    # Show outcome_quality_correlations schema
    print("\noutcome_quality_correlations columns:")
    for column in inspector.get_columns("outcome_quality_correlations"):
        print(f"  - {column['name']}: {column['type']}")


if __name__ == "__main__":
    run_migration()
