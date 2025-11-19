"""
Work Preferences Service - Phase 4

Manages user work preferences for intelligent scheduling.

Key Features:
1. Get/create user preferences
2. Default preferences for Jef (afternoon deep work, back-to-back meetings)
3. Update preferences via API
4. Cache for performance

Usage:
    prefs = await get_work_preferences(db, user_id=1)
    # Returns WorkPreferences with Jef's settings

    await update_work_preferences(db, user_id=1, {"deep_work_time": "morning"})
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.models import WorkPreferences
from services.performance_cache import get_cache

logger = logging.getLogger(__name__)


async def get_work_preferences(
    db: AsyncSession,
    user_id: int = 1
) -> WorkPreferences:
    """Get user work preferences (with caching).

    Args:
        db: Database session
        user_id: User ID (default 1 for single-user mode)

    Returns:
        WorkPreferences instance
    """
    cache = get_cache()

    # Try cache first
    cache_key = f"work_prefs:{user_id}"
    cached_prefs = await cache.get(cache_key, prefix="preferences")

    if cached_prefs:
        logger.debug(f"Work preferences cache hit: user {user_id}")
        # Reconstruct WorkPreferences from cached dict
        return _dict_to_preferences(cached_prefs)

    # Query database
    query = select(WorkPreferences).where(WorkPreferences.user_id == user_id)
    result = await db.execute(query)
    prefs = result.scalar_one_or_none()

    if prefs:
        # Cache for 5 minutes
        await cache.set(cache_key, _preferences_to_dict(prefs), ttl=300, prefix="preferences")
        logger.debug(f"Loaded work preferences from database: user {user_id}")
        return prefs

    # No preferences found - create default for Jef
    logger.warning(f"No work preferences found for user {user_id}, creating default (Jef's profile)")
    return await create_default_preferences(db, user_id)


async def create_default_preferences(
    db: AsyncSession,
    user_id: int = 1
) -> WorkPreferences:
    """Create default work preferences (Jef's preferences as specified).

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Created WorkPreferences
    """
    # Jef's preferences from requirements
    default_prefs = WorkPreferences(
        user_id=user_id,

        # Time preferences
        deep_work_time="afternoon_evening",  # Most productive 2pm-7pm
        preferred_task_time="afternoon",
        no_meetings_before="09:00",  # Never before 9am
        no_meetings_after="18:00",  # 6pm end of workday

        # Meeting style
        meeting_style="back_to_back",  # Bunch meetings together
        meeting_buffer=0,  # No buffer needed

        # Task scheduling
        min_task_block=30,  # Minimum 30 minutes for any task
        preferred_block_sizes=[30, 60, 90, 120],  # 30min, 1hr, 1.5hr, 2hr

        # Calendar preferences
        task_event_prefix="🪷 ",  # Lotus emoji prefix
        task_event_color="9",  # Google Calendar color (blue)

        # Automation
        auto_create_blocks=False,  # Phase 4: Always ask approval
        high_confidence_threshold=90,  # Future: auto-create if >90%

        # Additional preferences
        preferences_json={
            "work_location": "remote",
            "notification_time": "08:00",  # Daily summary at 8am
            "timezone": "Europe/Amsterdam",
            "focus_mode_hours": [14, 15, 16, 17],  # 2pm-6pm prime focus time
        }
    )

    db.add(default_prefs)
    await db.commit()
    await db.refresh(default_prefs)

    logger.info(f"Created default work preferences for user {user_id}")
    return default_prefs


async def update_work_preferences(
    db: AsyncSession,
    user_id: int,
    updates: Dict[str, Any]
) -> WorkPreferences:
    """Update user work preferences.

    Args:
        db: Database session
        user_id: User ID
        updates: Fields to update (partial updates allowed)

    Returns:
        Updated WorkPreferences

    Raises:
        ValueError: If preferences not found or invalid updates
    """
    query = select(WorkPreferences).where(WorkPreferences.user_id == user_id)
    result = await db.execute(query)
    prefs = result.scalar_one_or_none()

    if not prefs:
        raise ValueError(f"Work preferences not found for user {user_id}")

    # Validate and apply updates
    for key, value in updates.items():
        if hasattr(prefs, key):
            # Validate specific fields
            if key == "deep_work_time" and value not in ["morning", "afternoon", "evening", "afternoon_evening"]:
                raise ValueError(f"Invalid deep_work_time: {value}")

            if key == "meeting_style" and value not in ["back_to_back", "spaced_out"]:
                raise ValueError(f"Invalid meeting_style: {value}")

            if key == "min_task_block" and (not isinstance(value, int) or value < 15):
                raise ValueError(f"min_task_block must be >= 15 minutes, got {value}")

            # Apply update
            setattr(prefs, key, value)
        else:
            logger.warning(f"Unknown preference field: {key}")

    await db.commit()
    await db.refresh(prefs)

    # Invalidate cache
    cache = get_cache()
    await cache.delete(f"work_prefs:{user_id}", prefix="preferences")

    logger.info(f"Updated work preferences for user {user_id}: {list(updates.keys())}")
    return prefs


def _preferences_to_dict(prefs: WorkPreferences) -> Dict[str, Any]:
    """Convert WorkPreferences to dict for caching.

    Args:
        prefs: WorkPreferences instance

    Returns:
        Dictionary representation
    """
    return {
        "id": prefs.id,
        "user_id": prefs.user_id,
        "deep_work_time": prefs.deep_work_time,
        "preferred_task_time": prefs.preferred_task_time,
        "no_meetings_before": prefs.no_meetings_before,
        "no_meetings_after": prefs.no_meetings_after,
        "meeting_style": prefs.meeting_style,
        "meeting_buffer": prefs.meeting_buffer,
        "min_task_block": prefs.min_task_block,
        "preferred_block_sizes": prefs.preferred_block_sizes,
        "task_event_prefix": prefs.task_event_prefix,
        "task_event_color": prefs.task_event_color,
        "auto_create_blocks": prefs.auto_create_blocks,
        "high_confidence_threshold": prefs.high_confidence_threshold,
        "preferences_json": prefs.preferences_json,
    }


def _dict_to_preferences(data: Dict[str, Any]) -> WorkPreferences:
    """Reconstruct WorkPreferences from cached dict.

    Args:
        data: Cached dictionary

    Returns:
        WorkPreferences instance
    """
    # Create a temporary instance (not attached to session)
    prefs = WorkPreferences(
        id=data["id"],
        user_id=data["user_id"],
        deep_work_time=data["deep_work_time"],
        preferred_task_time=data["preferred_task_time"],
        no_meetings_before=data["no_meetings_before"],
        no_meetings_after=data["no_meetings_after"],
        meeting_style=data["meeting_style"],
        meeting_buffer=data["meeting_buffer"],
        min_task_block=data["min_task_block"],
        preferred_block_sizes=data["preferred_block_sizes"],
        task_event_prefix=data["task_event_prefix"],
        task_event_color=data["task_event_color"],
        auto_create_blocks=data["auto_create_blocks"],
        high_confidence_threshold=data["high_confidence_threshold"],
        preferences_json=data["preferences_json"],
    )
    return prefs


async def ensure_preferences_exist(db: AsyncSession, user_id: int = 1):
    """Ensure work preferences exist for user (create if missing).

    Called on app startup to ensure preferences are initialized.

    Args:
        db: Database session
        user_id: User ID
    """
    query = select(WorkPreferences).where(WorkPreferences.user_id == user_id)
    result = await db.execute(query)
    prefs = result.scalar_one_or_none()

    if not prefs:
        await create_default_preferences(db, user_id)
        logger.info(f"Initialized work preferences for user {user_id}")
