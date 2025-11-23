"""
Migration 011: Add Task Quality Evaluation
Phase 6 Stage 6 - Quality & Trust Metrics

Creates tables for task quality evaluation and trend tracking:
- task_quality_scores: Quality metrics for each task description
- quality_trends: Aggregated quality trends over time

Run: python backend/db/migrations/011_add_task_quality.py
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
    """Create task quality evaluation tables"""

    # Get database URL and convert to sync
    db_url = get_database_url()
    if db_url.startswith("sqlite+aiosqlite://"):
        db_url = db_url.replace("sqlite+aiosqlite://", "sqlite:///")

    print(f"Connecting to database: {db_url}")
    engine = sql_create_engine(db_url)
    metadata = MetaData()

    # ========================================================================
    # TASK QUALITY SCORES TABLE
    # ========================================================================

    task_quality_scores = Table(
        "task_quality_scores",
        metadata,
        Column("id", Integer, primary_key=True),

        # Task reference
        Column("task_id", String, nullable=False, index=True),
        Column("description_id", Integer, nullable=True),

        # Overall quality
        Column("overall_score", Float, default=0.0, index=True),
        Column("quality_tier", String(20), default="fair", index=True),

        # Quality dimensions (0-100 each)
        Column("completeness_score", Float, default=0.0),
        Column("clarity_score", Float, default=0.0),
        Column("actionability_score", Float, default=0.0),
        Column("relevance_score", Float, default=0.0),
        Column("confidence_score", Float, default=0.0),

        # Detailed metrics
        Column("quality_metrics", JSON, nullable=True),

        # Improvement suggestions
        Column("suggestions", JSON, nullable=True),
        Column("strengths", JSON, nullable=True),

        # Metadata
        Column("evaluated_at", DateTime, default=datetime.utcnow, nullable=False, index=True),
        Column("evaluator_version", String(20), default="1.0"),
        Column("evaluation_time_ms", Integer, default=0),

        # Scope
        Column("user_id", String, nullable=True, index=True),
        Column("project_id", String, nullable=True, index=True),

        # Composite indexes
        Index("idx_task_evaluated", "task_id", "evaluated_at"),
        Index("idx_quality_tier", "quality_tier", "overall_score"),
        Index("idx_user_quality", "user_id", "overall_score"),
        Index("idx_project_quality", "project_id", "overall_score"),
    )

    # ========================================================================
    # QUALITY TRENDS TABLE
    # ========================================================================

    quality_trends = Table(
        "quality_trends",
        metadata,
        Column("id", Integer, primary_key=True),

        # Aggregation period
        Column("period_type", String(20), nullable=False, index=True),
        Column("period_start", DateTime, nullable=False, index=True),
        Column("period_end", DateTime, nullable=False),

        # Scope
        Column("scope", String(20), default="global", index=True),
        Column("scope_id", String, nullable=True, index=True),

        # Aggregated quality metrics
        Column("tasks_evaluated", Integer, default=0),

        Column("avg_overall_score", Float, default=0.0),
        Column("avg_completeness_score", Float, default=0.0),
        Column("avg_clarity_score", Float, default=0.0),
        Column("avg_actionability_score", Float, default=0.0),
        Column("avg_relevance_score", Float, default=0.0),
        Column("avg_confidence_score", Float, default=0.0),

        # Tier distribution
        Column("excellent_count", Integer, default=0),
        Column("good_count", Integer, default=0),
        Column("fair_count", Integer, default=0),
        Column("needs_improvement_count", Integer, default=0),

        # Trend indicators
        Column("score_trend", String(20), nullable=True),
        Column("score_change", Float, default=0.0),

        # Metadata
        Column("calculated_at", DateTime, default=datetime.utcnow, nullable=False),

        # Composite indexes
        Index("idx_period_scope", "period_type", "scope", "period_start"),
        Index("idx_trend_quality", "period_start", "avg_overall_score"),
    )

    # Create tables
    print("Creating task quality evaluation tables...")
    metadata.create_all(engine)

    print("✅ Migration 011 complete!")
    print("Created tables:")
    print("  - task_quality_scores (with 4 composite indexes)")
    print("  - quality_trends (with 2 composite indexes)")

    # Verify tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print(f"\nAll tables in database ({len(tables)} total)")

    # Show task_quality_scores schema
    print("\ntask_quality_scores columns:")
    for column in inspector.get_columns("task_quality_scores"):
        print(f"  - {column['name']}: {column['type']}")


if __name__ == "__main__":
    run_migration()
