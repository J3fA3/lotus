"""
User Profile Manager - Phase 3

Manages user profile information for personalized task management.

Key Features:
1. Get/create user profiles
2. Check if tasks are relevant for the user
3. Auto-correct name variants ("Jeff" → "Jef")
4. Provide user context to AI agents

Usage:
    profile = await get_user_profile(db, user_id=1)
    is_relevant = profile.is_task_for_me(proposed_task)
"""

import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from db.models import UserProfile as UserProfileModel
from services.performance_cache import get_cache

logger = logging.getLogger(__name__)


class UserProfile(BaseModel):
    """User profile data model."""
    id: int
    user_id: int
    name: str
    aliases: List[str] = []
    role: Optional[str] = None
    company: Optional[str] = None
    projects: List[str] = []
    markets: List[str] = []
    colleagues: Dict[str, str] = {}
    preferences: Dict[str, Any] = {}

    def is_task_for_me(self, task: Dict[str, Any]) -> Optional[bool]:
        """Check if a task is relevant to this user.

        Args:
            task: Proposed task dict with title, description, assignee, etc.

        Returns:
            True if task is definitely for this user
            False if task is definitely NOT for this user (e.g., assigned to someone else)
            None if relevance is unclear and needs AI scoring
        """
        # Check 1: Explicitly assigned to someone else
        assignee = task.get("assignee", "").lower()
        if assignee and assignee not in ["unassigned", "", self.name.lower()]:
            # Check if assignee is in our aliases
            if not any(alias.lower() in assignee for alias in self.aliases):
                # Assigned to someone else
                logger.debug(f"Task assigned to someone else: {assignee}")
                return False

        # Check 2: Direct mention of user's name in title/description
        title = task.get("title", "").lower()
        description = task.get("description", "").lower()
        text = f"{title} {description}"

        # Check name and aliases
        for name_variant in [self.name] + self.aliases:
            if name_variant.lower() in text:
                logger.debug(f"Task mentions user's name: {name_variant}")
                return True

        # Check for first-person pronouns (I, me, my)
        if any(word in text for word in [" i ", " me ", " my ", "i'm", "i'll", "i've"]):
            logger.debug("Task uses first-person pronouns")
            return True

        # Check 3: Related to user's projects
        for project in self.projects:
            if project.lower() in text:
                logger.debug(f"Task mentions user's project: {project}")
                return True

        # Check 4: Related to user's markets
        for market in self.markets:
            if market.lower() in text:
                logger.debug(f"Task mentions user's market: {market}")
                return True

        # Default: unclear, might be relevant (let relevance filter decide)
        return None  # Let relevance agent score this

    def normalize_name(self, name: str) -> str:
        """Normalize a name variant to the canonical name.

        Args:
            name: Name to normalize (e.g., "Jeff")

        Returns:
            Canonical name (e.g., "Jef Adriaenssens")
        """
        name_lower = name.lower()

        # Check if it's an alias
        for alias in self.aliases:
            if alias.lower() == name_lower:
                return self.name

        # Check if it's already the correct name
        if name_lower == self.name.lower():
            return self.name

        # Unknown name, return as-is
        return name

    def get_colleague_info(self, name: str) -> Optional[str]:
        """Get full information about a colleague.

        Args:
            name: Colleague first name or partial name

        Returns:
            Full colleague info string or None
        """
        # Exact match
        if name in self.colleagues:
            return self.colleagues[name]

        # Case-insensitive match
        name_lower = name.lower()
        for key, value in self.colleagues.items():
            if key.lower() == name_lower:
                return value

        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary for AI prompts and state storage."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "aliases": self.aliases,
            "role": self.role,
            "company": self.company,
            "projects": self.projects,
            "markets": self.markets,
            "colleagues": self.colleagues,
            "preferences": self.preferences
        }


async def get_user_profile(
    db: AsyncSession,
    user_id: int = 1
) -> UserProfile:
    """Get user profile from database (with caching).

    Args:
        db: Database session
        user_id: User ID (default 1 for single-user mode)

    Returns:
        UserProfile instance
    """
    cache = get_cache()

    # Try cache first
    cache_key = f"user:{user_id}"
    cached_profile = await cache.get(cache_key, prefix="profiles")

    if cached_profile:
        logger.debug(f"User profile cache hit: {user_id}")
        return UserProfile(**cached_profile)

    # Query database
    query = select(UserProfileModel).where(UserProfileModel.user_id == user_id)
    result = await db.execute(query)
    profile_model = result.scalar_one_or_none()

    if profile_model:
        profile = UserProfile(
            id=profile_model.id,
            user_id=profile_model.user_id,
            name=profile_model.name,
            aliases=profile_model.aliases or [],
            role=profile_model.role,
            company=profile_model.company,
            projects=profile_model.projects or [],
            markets=profile_model.markets or [],
            colleagues=profile_model.colleagues or {},
            preferences=profile_model.preferences or {}
        )

        # Cache for 5 minutes (profiles change rarely)
        await cache.set(cache_key, profile.dict(), ttl=300, prefix="profiles")

        logger.debug(f"Loaded user profile from database: {profile.name}")
        return profile

    # No profile found - create default
    logger.warning(f"No user profile found for user_id={user_id}, creating default")
    return await create_default_profile(db, user_id)


async def create_default_profile(
    db: AsyncSession,
    user_id: int = 1
) -> UserProfile:
    """Create default user profile (Jef's profile as specified).

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Created UserProfile
    """
    # Default profile for Jef as specified in requirements
    default_data = {
        "user_id": user_id,
        "name": "Jef Adriaenssens",
        "aliases": ["Jeff", "Jef", "jef", "JA"],
        "role": "Product Manager",
        "company": "JustEat Takeaway",
        "projects": ["CRESCO", "RF16", "Just Deals"],
        "markets": ["Spain", "UK", "Netherlands"],
        "colleagues": {
            "Andy": "Andy Maclean",
            "Alberto": "Alberto Moraleda Fernandez - Spain market",
            "Maran": "Maran Vleems",
            "Sarah": "Sarah (Last Name Unknown)"
        },
        "preferences": {}
    }

    # Create model
    profile_model = UserProfileModel(**default_data)
    db.add(profile_model)
    await db.commit()
    await db.refresh(profile_model)

    profile = UserProfile(
        id=profile_model.id,
        user_id=profile_model.user_id,
        name=profile_model.name,
        aliases=profile_model.aliases or [],
        role=profile_model.role,
        company=profile_model.company,
        projects=profile_model.projects or [],
        markets=profile_model.markets or [],
        colleagues=profile_model.colleagues or {},
        preferences=profile_model.preferences or {}
    )

    logger.info(f"Created default user profile: {profile.name}")
    return profile


async def update_user_profile(
    db: AsyncSession,
    user_id: int,
    updates: Dict[str, Any]
) -> UserProfile:
    """Update user profile.

    Args:
        db: Database session
        user_id: User ID
        updates: Fields to update

    Returns:
        Updated UserProfile
    """
    query = select(UserProfileModel).where(UserProfileModel.user_id == user_id)
    result = await db.execute(query)
    profile_model = result.scalar_one_or_none()

    if not profile_model:
        raise ValueError(f"User profile not found: user_id={user_id}")

    # Update fields
    for key, value in updates.items():
        if hasattr(profile_model, key):
            setattr(profile_model, key, value)

    await db.commit()
    await db.refresh(profile_model)

    # Invalidate cache
    cache = get_cache()
    await cache.delete(f"user:{user_id}", prefix="profiles")

    logger.info(f"Updated user profile: {profile_model.name}")

    return await get_user_profile(db, user_id)
