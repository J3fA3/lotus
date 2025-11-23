"""
Migration 008: Add Question Queue System
Phase 6 Stage 4 - Contextual Questions

Creates tables for intelligent question queue:
- question_queue: Stores questions with priority, batching, lifecycle tracking
- question_batches: Groups related questions
- question_engagement_metrics: Tracks user engagement for adaptive learning

Run: python backend/db/migrations/008_add_question_queue.py
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine as sql_create_engine, MetaData, Table, Column, Integer, String, Text, Float, Boolean, DateTime, JSON, Index
from datetime import datetime
from db.database import get_database_url


def run_migration():
    """Create question queue tables"""

    # Get database URL and convert to sync
    db_url = get_database_url()
    if db_url.startswith("sqlite+aiosqlite://"):
        db_url = db_url.replace("sqlite+aiosqlite://", "sqlite:///")

    print(f"Connecting to database: {db_url}")
    engine = sql_create_engine(db_url)
    metadata = MetaData()

    # ========================================================================
    # QUESTION QUEUE TABLE
    # ========================================================================

    question_queue = Table(
        "question_queue",
        metadata,
        Column("id", Integer, primary_key=True),

        # Foreign keys
        Column("task_id", String, nullable=False, index=True),

        # Question content
        Column("field_name", String(100), nullable=False, index=True),
        Column("question", Text, nullable=False),
        Column("suggested_answer", Text, nullable=True),

        # Importance
        Column("importance", String(20), nullable=False, index=True),
        Column("confidence", Float, nullable=False),

        # Priority (calculated)
        Column("priority_score", Float, nullable=False, index=True),
        Column("field_impact", Float, nullable=False),
        Column("recency_factor", Float, nullable=False),

        # Batching
        Column("batch_id", String, nullable=True, index=True),
        Column("semantic_cluster", String, nullable=True),

        # Lifecycle
        Column("status", String(20), nullable=False, index=True),
        Column("created_at", DateTime, default=datetime.utcnow, nullable=False, index=True),
        Column("ready_at", DateTime, nullable=True),
        Column("shown_at", DateTime, nullable=True),
        Column("answered_at", DateTime, nullable=True),
        Column("snoozed_until", DateTime, nullable=True),

        # Answer
        Column("answer", Text, nullable=True),
        Column("answer_source", String(20), nullable=True),
        Column("answer_applied", Boolean, default=False),

        # User feedback
        Column("user_feedback", String(20), nullable=True),
        Column("user_feedback_comment", Text, nullable=True),

        # Outcome tracking
        Column("outcome_impact", String(20), nullable=True),
        Column("outcome_tracked", Boolean, default=False),
        Column("outcome_notes", Text, nullable=True),

        # Context
        Column("task_context", JSON, nullable=True),
        Column("related_questions", JSON, nullable=True),

        # Indexes
        Index("idx_queue_task_status", "task_id", "status"),
        Index("idx_queue_priority", "status", "priority_score"),
        Index("idx_queue_batch", "batch_id", "created_at"),
        Index("idx_queue_ready", "status", "ready_at"),
    )

    # ========================================================================
    # QUESTION BATCHES TABLE
    # ========================================================================

    question_batches = Table(
        "question_batches",
        metadata,
        Column("id", String, primary_key=True),

        # Batch metadata
        Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
        Column("batch_type", String(50), nullable=False),
        Column("semantic_cluster", String, nullable=True),

        # Questions
        Column("question_count", Integer, nullable=False, default=0),
        Column("question_ids", JSON, nullable=True),

        # Task association
        Column("task_ids", JSON, nullable=True),

        # Display
        Column("shown_to_user", Boolean, default=False),
        Column("shown_at", DateTime, nullable=True),
        Column("completed", Boolean, default=False),
        Column("completed_at", DateTime, nullable=True),

        # Statistics
        Column("answered_count", Integer, default=0),
        Column("dismissed_count", Integer, default=0),
        Column("snoozed_count", Integer, default=0),
    )

    # ========================================================================
    # QUESTION ENGAGEMENT METRICS TABLE
    # ========================================================================

    question_engagement_metrics = Table(
        "question_engagement_metrics",
        metadata,
        Column("id", Integer, primary_key=True),

        # Aggregation period
        Column("period_start", DateTime, nullable=False, index=True),
        Column("period_end", DateTime, nullable=False),
        Column("period_type", String(20), nullable=False),

        # Question statistics
        Column("total_questions", Integer, default=0),
        Column("questions_shown", Integer, default=0),
        Column("questions_answered", Integer, default=0),
        Column("questions_dismissed", Integer, default=0),
        Column("questions_snoozed", Integer, default=0),

        # Field-level metrics
        Column("field_metrics", JSON, nullable=True),

        # Timing metrics
        Column("avg_time_to_answer", Float, nullable=True),
        Column("avg_batch_size", Float, nullable=True),
        Column("optimal_timing", String(50), nullable=True),

        # Quality metrics
        Column("helpful_rate", Float, nullable=True),
        Column("answer_applied_rate", Float, nullable=True),
        Column("high_impact_rate", Float, nullable=True),
    )

    # Create tables
    print("Creating question queue tables...")
    metadata.create_all(engine)

    print("✅ Migration 008 complete!")
    print("Created tables:")
    print("  - question_queue (with 4 composite indexes)")
    print("  - question_batches")
    print("  - question_engagement_metrics")

    # Verify tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print(f"\nAll tables in database: {tables}")

    # Show question_queue schema
    print("\nquestion_queue columns:")
    for column in inspector.get_columns("question_queue"):
        print(f"  - {column['name']}: {column['type']}")


if __name__ == "__main__":
    run_migration()
