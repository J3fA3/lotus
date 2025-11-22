"""
Task Version Control Service - Phase 6 Stage 3

Provides business logic for intelligent task version control:
1. Creating versions (snapshots or deltas)
2. Querying version history
3. Comparing versions
4. Detecting AI overrides (learning signals)
5. Calculating version statistics

Critical Design Decisions:
- Version numbers: Auto-increment per task (query max + 1)
- Snapshot vs Delta: Snapshot on milestones, delta otherwise
- Performance: Synchronous (part of transaction)
- Concurrency: Use database transaction isolation
"""

import logging
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from datetime import datetime

from db.task_version_models import (
    TaskVersion,
    VersionDiff,
    VersionComment,
    create_snapshot,
    create_delta,
    is_significant_change,
    calculate_description_similarity
)
from db.models import Task

logger = logging.getLogger(__name__)


# ============================================================================
# TASK VERSION CONTROL SERVICE
# ============================================================================

class TaskVersionService:
    """
    Service for managing task versions with intelligent versioning logic.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # VERSION CREATION
    # ========================================================================

    async def create_initial_version(
        self,
        task: Task,
        changed_by: str,
        ai_model: Optional[str] = None
    ) -> TaskVersion:
        """
        Create initial version when task is created.

        Always creates a snapshot (full state).

        Args:
            task: Task object
            changed_by: User ID or "AI:agent_name"
            ai_model: AI model name if AI-created

        Returns:
            Created TaskVersion
        """
        # Serialize task to dict
        task_data = self._task_to_dict(task)

        # Create snapshot
        version = create_snapshot(
            task_data=task_data,
            changed_by=changed_by,
            change_source="ai_synthesis" if ai_model else "user_create",
            change_type="created"
        )

        # Set version number (always 1 for initial)
        version.version_number = 1
        version.task_id = task.id
        version.ai_model = ai_model

        # Add to session
        self.db.add(version)

        logger.info(f"Created initial version for task {task.id}")
        return version

    async def create_update_version(
        self,
        task_id: str,
        old_values: Dict,
        new_values: Dict,
        changed_by: str,
        change_source: str = "user_edit",
        ai_model: Optional[str] = None,
        ai_suggestions: Optional[Dict] = None
    ) -> Optional[TaskVersion]:
        """
        Create version when task is updated.

        Uses smart versioning logic:
        - Status changes: ALWAYS snapshot
        - AI overrides: ALWAYS snapshot (learning signal!)
        - Significant changes: Delta
        - Insignificant changes: No version

        Args:
            task_id: Task ID
            old_values: Previous values {field: value}
            new_values: New values {field: value}
            changed_by: User ID or "AI:agent_name"
            change_source: "user_edit", "ai_enrichment", etc.
            ai_model: AI model name if AI-generated
            ai_suggestions: AI-suggested values (for override detection)

        Returns:
            Created TaskVersion or None if not significant
        """
        # Detect change type
        change_type = self._detect_change_type(old_values, new_values, ai_suggestions)

        # Check if significant
        if not is_significant_change(old_values, new_values, change_type):
            logger.debug(f"Skipping version for task {task_id}: insignificant change")
            return None

        # Get next version number
        version_number = await self._get_next_version_number(task_id)

        # Detect AI overrides (learning signal!)
        ai_overridden = False
        overridden_fields = []
        if ai_suggestions and change_source == "user_edit":
            ai_overridden, overridden_fields = self._detect_ai_overrides(
                new_values,
                ai_suggestions
            )

        # Decide: Snapshot or Delta?
        is_milestone = change_type in ["status_change", "ai_override"] or ai_overridden

        if is_milestone:
            # Fetch full task state for snapshot
            task = await self._get_task(task_id)
            if not task:
                logger.error(f"Task {task_id} not found for versioning")
                return None

            task_data = self._task_to_dict(task)
            version = create_snapshot(
                task_data=task_data,
                changed_by=changed_by,
                change_source=change_source,
                change_type=change_type
            )
            version.is_milestone = True
        else:
            # Create delta
            version = create_delta(
                task_id=task_id,
                old_values=old_values,
                new_values=new_values,
                changed_by=changed_by,
                change_source=change_source,
                change_type=change_type
            )

        # Set metadata
        version.version_number = version_number
        version.task_id = task_id
        version.ai_model = ai_model
        version.ai_suggestion_overridden = ai_overridden
        version.overridden_fields = overridden_fields

        # Add to session
        self.db.add(version)

        logger.info(
            f"Created version {version_number} for task {task_id} "
            f"(type: {change_type}, milestone: {is_milestone}, ai_override: {ai_overridden})"
        )

        return version

    # ========================================================================
    # VERSION QUERYING
    # ========================================================================

    async def get_version_history(
        self,
        task_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[TaskVersion]:
        """
        Get version history for a task (most recent first).

        Args:
            task_id: Task ID
            limit: Max versions to return
            offset: Pagination offset

        Returns:
            List of TaskVersion objects
        """
        result = await self.db.execute(
            select(TaskVersion)
            .where(TaskVersion.task_id == task_id)
            .order_by(desc(TaskVersion.created_at))
            .limit(limit)
            .offset(offset)
        )
        versions = result.scalars().all()
        return list(versions)

    async def get_version(
        self,
        task_id: str,
        version_number: int
    ) -> Optional[TaskVersion]:
        """
        Get specific version of a task.

        Args:
            task_id: Task ID
            version_number: Version number

        Returns:
            TaskVersion or None if not found
        """
        result = await self.db.execute(
            select(TaskVersion).where(
                and_(
                    TaskVersion.task_id == task_id,
                    TaskVersion.version_number == version_number
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_version(
        self,
        task_id: str
    ) -> Optional[TaskVersion]:
        """
        Get most recent version of a task.

        Args:
            task_id: Task ID

        Returns:
            Latest TaskVersion or None if no versions
        """
        result = await self.db.execute(
            select(TaskVersion)
            .where(TaskVersion.task_id == task_id)
            .order_by(desc(TaskVersion.version_number))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_milestones(
        self,
        task_id: str
    ) -> List[TaskVersion]:
        """
        Get milestone versions (major changes) for a task.

        Args:
            task_id: Task ID

        Returns:
            List of milestone TaskVersions
        """
        result = await self.db.execute(
            select(TaskVersion)
            .where(
                and_(
                    TaskVersion.task_id == task_id,
                    TaskVersion.is_milestone == True
                )
            )
            .order_by(desc(TaskVersion.created_at))
        )
        return list(result.scalars().all())

    # ========================================================================
    # VERSION COMPARISON
    # ========================================================================

    async def compare_versions(
        self,
        task_id: str,
        version_a: int,
        version_b: int
    ) -> Dict:
        """
        Compare two versions and return diff.

        Args:
            task_id: Task ID
            version_a: First version number
            version_b: Second version number

        Returns:
            Dict with diff information
        """
        # Get both versions
        v_a = await self.get_version(task_id, version_a)
        v_b = await self.get_version(task_id, version_b)

        if not v_a or not v_b:
            raise ValueError(f"Version not found: {version_a} or {version_b}")

        # Reconstruct full state for both versions
        state_a = await self._reconstruct_state(task_id, version_a)
        state_b = await self._reconstruct_state(task_id, version_b)

        # Calculate diff
        diff = self._calculate_diff(state_a, state_b)

        return {
            "version_a": version_a,
            "version_b": version_b,
            "created_at_a": v_a.created_at.isoformat(),
            "created_at_b": v_b.created_at.isoformat(),
            "changed_fields": list(diff.keys()),
            "diff": diff
        }

    # ========================================================================
    # LEARNING SIGNALS (AI OVERRIDES)
    # ========================================================================

    async def get_ai_overrides(
        self,
        limit: int = 100,
        days: int = 30
    ) -> List[TaskVersion]:
        """
        Get recent AI overrides for learning analytics.

        These are high-value signals showing when users disagree with AI.

        Args:
            limit: Max versions to return
            days: Look back period

        Returns:
            List of TaskVersions where AI was overridden
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(TaskVersion)
            .where(
                and_(
                    TaskVersion.ai_suggestion_overridden == True,
                    TaskVersion.created_at >= cutoff
                )
            )
            .order_by(desc(TaskVersion.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_override_statistics(
        self,
        days: int = 30
    ) -> Dict:
        """
        Get statistics on AI overrides for learning analytics.

        Args:
            days: Look back period

        Returns:
            Dict with override statistics
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        # Count total versions
        total_result = await self.db.execute(
            select(func.count(TaskVersion.id))
            .where(TaskVersion.created_at >= cutoff)
        )
        total_versions = total_result.scalar()

        # Count AI-generated versions
        ai_result = await self.db.execute(
            select(func.count(TaskVersion.id))
            .where(
                and_(
                    TaskVersion.created_at >= cutoff,
                    TaskVersion.ai_model.isnot(None)
                )
            )
        )
        ai_versions = ai_result.scalar()

        # Count overrides
        override_result = await self.db.execute(
            select(func.count(TaskVersion.id))
            .where(
                and_(
                    TaskVersion.created_at >= cutoff,
                    TaskVersion.ai_suggestion_overridden == True
                )
            )
        )
        overrides = override_result.scalar()

        override_rate = (overrides / ai_versions * 100) if ai_versions > 0 else 0.0

        # Get most overridden fields
        # This would require JSON querying - simplified for now
        # TODO: Implement field-level override statistics

        return {
            "days": days,
            "total_versions": total_versions,
            "ai_versions": ai_versions,
            "overrides": overrides,
            "override_rate": round(override_rate, 2),
            "message": f"{overrides}/{ai_versions} AI suggestions overridden ({override_rate:.1f}%)"
        }

    # ========================================================================
    # PRIVATE HELPERS
    # ========================================================================

    async def _get_next_version_number(self, task_id: str) -> int:
        """Get next version number for a task."""
        result = await self.db.execute(
            select(func.max(TaskVersion.version_number))
            .where(TaskVersion.task_id == task_id)
        )
        max_version = result.scalar()
        return (max_version or 0) + 1

    async def _get_task(self, task_id: str) -> Optional[Task]:
        """Fetch task by ID."""
        result = await self.db.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    def _task_to_dict(self, task: Task) -> Dict:
        """Serialize task to dict for versioning."""
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "effort": task.effort,
            "project": task.project,
            "assignee": task.assignee,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None
        }

    def _detect_change_type(
        self,
        old_values: Dict,
        new_values: Dict,
        ai_suggestions: Optional[Dict]
    ) -> str:
        """Detect type of change."""
        # Status change
        if "status" in new_values and old_values.get("status") != new_values["status"]:
            return "status_change"

        # AI override
        if ai_suggestions:
            for field, new_value in new_values.items():
                if field in ai_suggestions and ai_suggestions[field] != new_value:
                    return "ai_override"

        # Description edit
        if "description" in new_values:
            return "description_edit"

        # Field update
        return "field_update"

    def _detect_ai_overrides(
        self,
        new_values: Dict,
        ai_suggestions: Dict
    ) -> Tuple[bool, List[str]]:
        """
        Detect which fields user overrode from AI suggestions.

        Returns:
            (overridden, list of field names)
        """
        overridden_fields = []
        for field, new_value in new_values.items():
            if field in ai_suggestions and ai_suggestions[field] != new_value:
                overridden_fields.append(field)

        return len(overridden_fields) > 0, overridden_fields

    async def _reconstruct_state(
        self,
        task_id: str,
        version_number: int
    ) -> Dict:
        """
        Reconstruct full task state at a specific version.

        Walks backward from target version, applying snapshots and deltas.
        """
        versions = await self.db.execute(
            select(TaskVersion)
            .where(
                and_(
                    TaskVersion.task_id == task_id,
                    TaskVersion.version_number <= version_number
                )
            )
            .order_by(TaskVersion.version_number)
        )
        versions = list(versions.scalars().all())

        if not versions:
            return {}

        # Find most recent snapshot at or before target version
        state = {}
        for v in reversed(versions):
            if v.is_snapshot and v.snapshot_data:
                state = v.snapshot_data.copy()
                snapshot_version = v.version_number
                break

        if not state:
            # No snapshot found, use first version if it's a snapshot
            if versions[0].is_snapshot and versions[0].snapshot_data:
                state = versions[0].snapshot_data.copy()
                snapshot_version = versions[0].version_number
            else:
                return {}

        # Apply deltas after snapshot
        for v in versions:
            if v.version_number > snapshot_version and v.version_number <= version_number:
                if not v.is_snapshot and v.delta_data:
                    # Apply delta
                    new_values = v.delta_data.get("new", {})
                    state.update(new_values)

        return state

    def _calculate_diff(self, state_a: Dict, state_b: Dict) -> Dict:
        """Calculate diff between two states."""
        diff = {}
        all_fields = set(state_a.keys()) | set(state_b.keys())

        for field in all_fields:
            val_a = state_a.get(field)
            val_b = state_b.get(field)

            if val_a != val_b:
                diff[field] = {
                    "old": val_a,
                    "new": val_b
                }

        return diff


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

async def get_task_version_service(db: AsyncSession) -> TaskVersionService:
    """Factory function to get task version service instance."""
    return TaskVersionService(db)
