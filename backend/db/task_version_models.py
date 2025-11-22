"""
Task Version Control Models - Phase 6 Stage 3

Tracks task evolution with intelligent version control:
- Hybrid versioning (snapshots + deltas)
- Smart significance detection
- Full provenance tracking (who, when, why, which AI)
- PR-style explanatory comments
- Learning signals (AI suggestions overridden by user)

Design Decisions:
1. Hybrid: Snapshots at milestones + deltas for minor changes
2. Smart auto-versioning with significance detection
3. Full provenance (changed_by, changed_at, change_reason, ai_model)
4. Pre-generated PR-style comments (cached)
5. Single versions table with structured diff JSON
"""

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base


# ============================================================================
# TASK VERSION MODEL
# ============================================================================

class TaskVersion(Base):
    """
    Represents a version/snapshot of a task at a point in time.

    Versions are created for:
    - Task creation (initial version)
    - Status changes (always significant)
    - Field changes where AI suggestion was overridden (learning signal!)
    - Description changes >20%
    - Major updates (manually triggered)

    Each version includes:
    - Full snapshot OR delta (based on is_snapshot flag)
    - PR-style explanatory comment (pre-generated)
    - Provenance metadata (who, when, why, which AI)
    - Learning signals (user overrides)
    """

    __tablename__ = "task_versions"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Foreign keys
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False, index=True)

    # Version metadata
    version_number = Column(Integer, nullable=False, index=True)  # Sequential: 1, 2, 3...
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Versioning type
    is_snapshot = Column(Boolean, default=False, nullable=False)  # True = full snapshot, False = delta
    is_milestone = Column(Boolean, default=False, nullable=False)  # Major version (e.g., status change)

    # Change provenance
    changed_by = Column(String, nullable=True)  # User ID or "AI:orchestrator", "AI:enrichment", etc.
    change_source = Column(String, nullable=False, index=True)  # "user_edit", "ai_synthesis", "ai_enrichment", "system"
    ai_model = Column(String, nullable=True)  # "gemini-2.0-flash", etc. if AI-generated

    # Change detection
    change_type = Column(String, nullable=False, index=True)  # "created", "status_change", "field_update", "description_edit", "ai_override"
    changed_fields = Column(JSON, default=list)  # List of field names that changed: ["priority", "effort_estimate"]

    # Snapshot or Delta
    # If is_snapshot=True: snapshot_data contains full task state
    # If is_snapshot=False: delta_data contains only changes
    snapshot_data = Column(JSON, nullable=True)  # Full task state (if snapshot)
    delta_data = Column(JSON, nullable=True)  # Changes only (if delta)
    # Delta format: {"old": {"priority": "P2_MEDIUM"}, "new": {"priority": "P1_HIGH"}}

    # PR-Style Comment (Pre-generated)
    pr_comment = Column(Text, nullable=True)  # "**Status Update**: Task moved from 'todo' to 'doing'. Priority increased to P1 due to blocking production issue."
    pr_comment_generated_at = Column(DateTime, nullable=True)

    # Learning Signals
    ai_suggestion_overridden = Column(Boolean, default=False, nullable=False, index=True)  # User changed AI-suggested value
    overridden_fields = Column(JSON, default=list)  # Fields where AI was overridden: ["priority", "effort_estimate"]
    override_reason = Column(Text, nullable=True)  # User's explanation (if provided)

    # Quality & Confidence
    change_confidence = Column(Float, nullable=True)  # AI confidence in this change (if AI-generated)
    user_approved = Column(Boolean, nullable=True)  # Did user explicitly approve this change? (for auto-updates)

    # Indexes for common queries
    __table_args__ = (
        Index('idx_task_version_lookup', 'task_id', 'version_number'),
        Index('idx_task_version_timeline', 'task_id', 'created_at'),
        Index('idx_ai_overrides', 'ai_suggestion_overridden', 'created_at'),  # For learning analytics
        Index('idx_change_type', 'change_type', 'created_at'),
    )

    # Relationships
    task = relationship("Task", back_populates="versions", foreign_keys=[task_id])


# ============================================================================
# VERSION DIFF MODEL (For complex diffs)
# ============================================================================

class VersionDiff(Base):
    """
    Detailed field-level diff for complex changes.

    For simple changes, delta_data in TaskVersion is sufficient.
    For complex changes (e.g., rich text description edits), this provides
    detailed diff information.
    """

    __tablename__ = "version_diffs"

    id = Column(Integer, primary_key=True)
    version_id = Column(Integer, ForeignKey("task_versions.id"), nullable=False, index=True)

    # Field-level diff
    field_name = Column(String(100), nullable=False, index=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)

    # Diff metadata
    diff_type = Column(String(50), nullable=False)  # "text_edit", "value_change", "addition", "deletion"
    diff_summary = Column(Text, nullable=True)  # Human-readable summary: "Priority increased from P2 to P1"

    # For text edits: unified diff or similar
    unified_diff = Column(Text, nullable=True)  # Standard unified diff format

    # Relationships
    version = relationship("TaskVersion", backref="detailed_diffs")


# ============================================================================
# VERSION COMMENT MODEL (For PR-style discussions)
# ============================================================================

class VersionComment(Base):
    """
    Comments on specific versions (like PR review comments).

    Allows users to discuss changes, ask questions, or provide context.
    """

    __tablename__ = "version_comments"

    id = Column(Integer, primary_key=True)
    version_id = Column(Integer, ForeignKey("task_versions.id"), nullable=False, index=True)

    # Comment content
    comment_text = Column(Text, nullable=False)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Comment type
    comment_type = Column(String(50), nullable=False)  # "question", "explanation", "approval", "concern"

    # Relationships
    version = relationship("TaskVersion", backref="comments")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_snapshot(task_data: dict, changed_by: str, change_source: str, change_type: str = "created") -> TaskVersion:
    """
    Create a snapshot version (full task state).

    Args:
        task_data: Full task state as dict
        changed_by: User ID or "AI:agent_name"
        change_source: "user_edit", "ai_synthesis", etc.
        change_type: Type of change

    Returns:
        TaskVersion instance (not committed)
    """
    return TaskVersion(
        task_id=task_data["id"],
        version_number=1,  # Will be set by service
        is_snapshot=True,
        is_milestone=(change_type in ["created", "status_change"]),
        changed_by=changed_by,
        change_source=change_source,
        change_type=change_type,
        snapshot_data=task_data,
        changed_fields=list(task_data.keys())
    )


def create_delta(task_id: str, old_values: dict, new_values: dict, changed_by: str, change_source: str, change_type: str) -> TaskVersion:
    """
    Create a delta version (only changes).

    Args:
        task_id: Task ID
        old_values: Previous values {field: value}
        new_values: New values {field: value}
        changed_by: User ID or "AI:agent_name"
        change_source: "user_edit", "ai_synthesis", etc.
        change_type: Type of change

    Returns:
        TaskVersion instance (not committed)
    """
    return TaskVersion(
        task_id=task_id,
        version_number=1,  # Will be set by service
        is_snapshot=False,
        is_milestone=(change_type == "status_change"),
        changed_by=changed_by,
        change_source=change_source,
        change_type=change_type,
        delta_data={"old": old_values, "new": new_values},
        changed_fields=list(new_values.keys())
    )


def calculate_description_similarity(old_text: str, new_text: str) -> float:
    """
    Calculate similarity between two text descriptions.

    Uses simple word-based similarity (can be enhanced with embeddings later).

    Returns:
        Similarity score 0.0-1.0
    """
    if not old_text and not new_text:
        return 1.0
    if not old_text or not new_text:
        return 0.0

    old_words = set(old_text.lower().split())
    new_words = set(new_text.lower().split())

    if not old_words and not new_words:
        return 1.0
    if not old_words or not new_words:
        return 0.0

    intersection = old_words & new_words
    union = old_words | new_words

    return len(intersection) / len(union) if union else 0.0


def is_significant_change(old_values: dict, new_values: dict, change_type: str) -> bool:
    """
    Determine if a change is significant enough to create a version.

    Significance rules:
    - Status changes: ALWAYS significant
    - AI overrides: ALWAYS significant (learning signal!)
    - Description changes: Significant if <80% similarity
    - Field changes: Significant if value actually changed

    Args:
        old_values: Previous values
        new_values: New values
        change_type: Type of change

    Returns:
        True if significant, False otherwise
    """
    # Status changes are always significant
    if change_type == "status_change":
        return True

    # AI overrides are always significant (learning signal)
    if change_type == "ai_override":
        return True

    # Check description changes
    if "description" in new_values and "description" in old_values:
        similarity = calculate_description_similarity(
            old_values.get("description", ""),
            new_values.get("description", "")
        )
        if similarity < 0.8:  # >20% change
            return True

    # Check if any value actually changed
    for field, new_value in new_values.items():
        old_value = old_values.get(field)
        if old_value != new_value:
            return True

    return False
