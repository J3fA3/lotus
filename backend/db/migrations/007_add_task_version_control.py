"""
Migration 007: Add Task Version Control Tables - Phase 6 Stage 3

Creates tables for intelligent task version control:
1. task_versions - Main version tracking table (snapshots + deltas)
2. version_diffs - Detailed field-level diffs
3. version_comments - PR-style discussion on changes

Features:
- Hybrid versioning (snapshots at milestones, deltas for minor changes)
- Full provenance tracking (who, when, why, which AI)
- Learning signals (AI suggestions overridden by user)
- Pre-generated PR-style comments
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime,
    JSON, ForeignKey, Index, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

# Define tables (same as in task_version_models.py but standalone for migration)


class TaskVersion(Base):
    __tablename__ = "task_versions"

    id = Column(Integer, primary_key=True)
    task_id = Column(String, nullable=False, index=True)  # FK to tasks.id (enforced by application)
    version_number = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    is_snapshot = Column(Boolean, default=False, nullable=False)
    is_milestone = Column(Boolean, default=False, nullable=False)

    changed_by = Column(String, nullable=True)
    change_source = Column(String, nullable=False, index=True)
    ai_model = Column(String, nullable=True)

    change_type = Column(String, nullable=False, index=True)
    changed_fields = Column(JSON, default=list)

    snapshot_data = Column(JSON, nullable=True)
    delta_data = Column(JSON, nullable=True)

    pr_comment = Column(Text, nullable=True)
    pr_comment_generated_at = Column(DateTime, nullable=True)

    ai_suggestion_overridden = Column(Boolean, default=False, nullable=False, index=True)
    overridden_fields = Column(JSON, default=list)
    override_reason = Column(Text, nullable=True)

    change_confidence = Column(Float, nullable=True)
    user_approved = Column(Boolean, nullable=True)

    __table_args__ = (
        Index('idx_task_version_lookup', 'task_id', 'version_number'),
        Index('idx_task_version_timeline', 'task_id', 'created_at'),
        Index('idx_ai_overrides', 'ai_suggestion_overridden', 'created_at'),
        Index('idx_change_type', 'change_type', 'created_at'),
    )


class VersionDiff(Base):
    __tablename__ = "version_diffs"

    id = Column(Integer, primary_key=True)
    version_id = Column(Integer, nullable=False, index=True)  # FK to task_versions.id (enforced by application)

    field_name = Column(String(100), nullable=False, index=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)

    diff_type = Column(String(50), nullable=False)
    diff_summary = Column(Text, nullable=True)
    unified_diff = Column(Text, nullable=True)


class VersionComment(Base):
    __tablename__ = "version_comments"

    id = Column(Integer, primary_key=True)
    version_id = Column(Integer, nullable=False, index=True)  # FK to task_versions.id (enforced by application)

    comment_text = Column(Text, nullable=False)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    comment_type = Column(String(50), nullable=False)


def upgrade(engine):
    """Create version control tables."""
    print("Creating task version control tables...")

    # Create all tables
    Base.metadata.create_all(engine, tables=[
        TaskVersion.__table__,
        VersionDiff.__table__,
        VersionComment.__table__
    ])

    print("✅ Created 3 version control tables:")
    print("   - task_versions (hybrid snapshots + deltas)")
    print("   - version_diffs (detailed field-level diffs)")
    print("   - version_comments (PR-style discussions)")
    print("   - 4 composite indexes for performance")


def downgrade(engine):
    """Drop version control tables."""
    print("Dropping task version control tables...")

    Base.metadata.drop_all(engine, tables=[
        VersionComment.__table__,
        VersionDiff.__table__,
        TaskVersion.__table__
    ])

    print("✅ Dropped version control tables")


if __name__ == "__main__":
    # Run migration
    import sys
    import os

    # Add backend directory to path
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, backend_dir)

    from db.database import get_database_url
    from sqlalchemy import create_engine as sql_create_engine

    print("=" * 80)
    print("MIGRATION 007: Add Task Version Control Tables")
    print("=" * 80)

    # Get database URL and convert async URL to sync for migration
    db_url = get_database_url()
    if db_url.startswith("sqlite+aiosqlite://"):
        db_url = db_url.replace("sqlite+aiosqlite://", "sqlite:///")

    engine = sql_create_engine(db_url)

    try:
        upgrade(engine)
        print("\n✅ Migration 007 completed successfully")
    except Exception as e:
        print(f"\n❌ Migration 007 failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
