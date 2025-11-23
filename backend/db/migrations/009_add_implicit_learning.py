"""
Migration 009: Add Implicit Learning System
Phase 6 Stage 5 - Self-Learning Intelligence

Creates tables for implicit learning signals and models:
- implicit_signals: Raw event log (append-only, 90-day retention)
- signal_aggregates: Pre-computed metrics (daily rollups)
- learning_models: Learned patterns that guide AI behavior
- model_performance_logs: Track if learning improves quality

Run: python backend/db/migrations/009_add_implicit_learning.py
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine as sql_create_engine, MetaData, Table, Column, Integer, String, Float, Boolean, DateTime, JSON, Text, Index, Enum as SQLEnum
from datetime import datetime
from db.database import get_database_url
import enum


# Define enums (must match models)
class SignalType(str, enum.Enum):
    AI_OVERRIDE = "ai_override"
    QUESTION_ANSWERED = "question_answered"
    QUESTION_DISMISSED = "question_dismissed"
    OUTCOME_POSITIVE = "outcome_positive"
    OUTCOME_NEGATIVE = "outcome_negative"
    DESCRIPTION_EDITED = "description_edited"
    AUTO_FILL_ACCEPTED = "auto_fill_accepted"
    AUTO_FILL_REJECTED = "auto_fill_rejected"
    QUESTION_FEEDBACK_HELPFUL = "question_feedback_helpful"
    QUESTION_FEEDBACK_NOT_HELPFUL = "question_feedback_not_helpful"


class LearningScope(str, enum.Enum):
    GLOBAL = "global"
    PROJECT = "project"
    USER = "user"


class ModelType(str, enum.Enum):
    PRIORITY_PREDICTION = "priority_prediction"
    EFFORT_ESTIMATION = "effort_estimation"
    FIELD_IMPORTANCE = "field_importance"
    QUESTION_RELEVANCE = "question_relevance"
    DESCRIPTION_QUALITY = "description_quality"
    AUTO_FILL_CONFIDENCE = "auto_fill_confidence"


def run_migration():
    """Create implicit learning tables"""

    # Get database URL and convert to sync
    db_url = get_database_url()
    if db_url.startswith("sqlite+aiosqlite://"):
        db_url = db_url.replace("sqlite+aiosqlite://", "sqlite:///")

    print(f"Connecting to database: {db_url}")
    engine = sql_create_engine(db_url)
    metadata = MetaData()

    # ========================================================================
    # IMPLICIT SIGNALS TABLE
    # ========================================================================

    implicit_signals = Table(
        "implicit_signals",
        metadata,
        Column("id", Integer, primary_key=True),

        # Signal metadata
        Column("signal_type", SQLEnum(SignalType), nullable=False, index=True),
        Column("created_at", DateTime, default=datetime.utcnow, nullable=False, index=True),

        # Context
        Column("user_id", String, nullable=True, index=True),
        Column("task_id", String, nullable=True, index=True),
        Column("project_id", String, nullable=True, index=True),
        Column("question_id", Integer, nullable=True),

        # Signal details
        Column("signal_data", JSON, nullable=False),

        # Weighting
        Column("base_weight", Float, nullable=False, default=1.0),
        Column("confidence", Float, nullable=False, default=1.0),
        Column("recency_factor", Float, nullable=False, default=1.0),
        Column("final_weight", Float, nullable=False, default=1.0),

        # Processing
        Column("processed", Boolean, default=False, index=True),
        Column("processed_at", DateTime, nullable=True),

        # Retention
        Column("retention_days", Integer, default=90),
        Column("expires_at", DateTime, nullable=True, index=True),

        # Composite indexes
        Index("idx_signal_type_time", "signal_type", "created_at"),
        Index("idx_user_signal", "user_id", "signal_type", "created_at"),
        Index("idx_task_signal", "task_id", "signal_type"),
        Index("idx_unprocessed", "processed", "created_at"),
        Index("idx_expiration", "expires_at"),
    )

    # ========================================================================
    # SIGNAL AGGREGATES TABLE
    # ========================================================================

    signal_aggregates = Table(
        "signal_aggregates",
        metadata,
        Column("id", Integer, primary_key=True),

        # Aggregation period
        Column("period_start", DateTime, nullable=False, index=True),
        Column("period_end", DateTime, nullable=False),
        Column("period_type", String(20), nullable=False, default="daily"),

        # Scope
        Column("scope", SQLEnum(LearningScope), nullable=False, index=True),
        Column("scope_id", String, nullable=True, index=True),

        # Signal type
        Column("signal_type", SQLEnum(SignalType), nullable=False, index=True),

        # Aggregated metrics
        Column("total_count", Integer, default=0),
        Column("weighted_sum", Float, default=0.0),
        Column("avg_confidence", Float, default=0.0),
        Column("unique_users", Integer, default=0),
        Column("unique_tasks", Integer, default=0),

        # Field-specific aggregates
        Column("field_aggregates", JSON, nullable=True),

        # Trends
        Column("trend_direction", String(20), nullable=True),
        Column("trend_magnitude", Float, default=0.0),

        # Composite indexes
        Index("idx_aggregate_scope", "scope", "scope_id", "period_start"),
        Index("idx_aggregate_signal", "signal_type", "period_start"),
    )

    # ========================================================================
    # LEARNING MODELS TABLE
    # ========================================================================

    learning_models = Table(
        "learning_models",
        metadata,
        Column("id", Integer, primary_key=True),

        # Model metadata
        Column("model_type", SQLEnum(ModelType), nullable=False, index=True),
        Column("scope", SQLEnum(LearningScope), nullable=False, index=True),
        Column("scope_id", String, nullable=True, index=True),

        # Model details
        Column("model_name", String(200), nullable=False),
        Column("description", Text, nullable=True),

        # Pattern/rule
        Column("pattern", JSON, nullable=False),

        # Model performance
        Column("sample_size", Integer, default=0),
        Column("confidence_score", Float, default=0.0),
        Column("accuracy", Float, nullable=True),
        Column("precision", Float, nullable=True),
        Column("recall", Float, nullable=True),

        # Lifecycle
        Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
        Column("last_updated", DateTime, default=datetime.utcnow),
        Column("last_used", DateTime, nullable=True),
        Column("active", Boolean, default=True, index=True),

        # Training metadata
        Column("trained_on_signal_count", Integer, default=0),
        Column("training_period_start", DateTime, nullable=True),
        Column("training_period_end", DateTime, nullable=True),

        # Composite indexes
        Index("idx_model_scope", "scope", "scope_id", "model_type", "active"),
        Index("idx_model_active", "active", "model_type", "confidence_score"),
    )

    # ========================================================================
    # MODEL PERFORMANCE LOGS TABLE
    # ========================================================================

    model_performance_logs = Table(
        "model_performance_logs",
        metadata,
        Column("id", Integer, primary_key=True),

        # Model reference
        Column("model_id", Integer, nullable=False, index=True),
        Column("model_type", SQLEnum(ModelType), nullable=False),

        # Evaluation period
        Column("evaluated_at", DateTime, default=datetime.utcnow, nullable=False, index=True),
        Column("evaluation_period_start", DateTime, nullable=False),
        Column("evaluation_period_end", DateTime, nullable=False),

        # Performance metrics
        Column("predictions_made", Integer, default=0),
        Column("predictions_correct", Integer, default=0),
        Column("predictions_incorrect", Integer, default=0),
        Column("accuracy", Float, default=0.0),
        Column("precision", Float, nullable=True),
        Column("recall", Float, nullable=True),
        Column("f1_score", Float, nullable=True),

        # Business impact
        Column("tasks_improved", Integer, default=0),
        Column("tasks_degraded", Integer, default=0),
        Column("user_satisfaction", Float, nullable=True),
        Column("time_saved_seconds", Integer, default=0),

        # Comparison baseline
        Column("baseline_accuracy", Float, nullable=True),
        Column("improvement_pct", Float, nullable=True),

        # Composite indexes
        Index("idx_performance_model", "model_id", "evaluated_at"),
    )

    # Create tables
    print("Creating implicit learning tables...")
    metadata.create_all(engine)

    print("✅ Migration 009 complete!")
    print("Created tables:")
    print("  - implicit_signals (with 5 composite indexes)")
    print("  - signal_aggregates (with 2 composite indexes)")
    print("  - learning_models (with 2 composite indexes)")
    print("  - model_performance_logs (with 1 composite index)")

    # Verify tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print(f"\nAll tables in database: {tables}")

    # Show implicit_signals schema
    print("\nimplicit_signals columns:")
    for column in inspector.get_columns("implicit_signals"):
        print(f"  - {column['name']}: {column['type']}")


if __name__ == "__main__":
    run_migration()
