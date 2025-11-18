"""
Knowledge Graph Query Cache

This module provides caching for expensive knowledge graph queries to improve
performance of task matching and entity lookups.

Uses a simple in-memory LRU cache with TTL (time-to-live) support.
"""

from functools import lru_cache
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
import json


# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

# Cache sizes
ENTITY_CACHE_SIZE = 500
RELATIONSHIP_CACHE_SIZE = 500
TASK_MATCH_CACHE_SIZE = 200

# Cache TTL (time-to-live)
CACHE_TTL_SECONDS = 300  # 5 minutes


# ============================================================================
# CACHE KEY GENERATION
# ============================================================================

def _generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a cache key from function arguments.

    Args:
        prefix: Cache key prefix (e.g., "entity", "relationship")
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Cache key string
    """
    # Create deterministic hash of arguments
    data = {
        "args": args,
        "kwargs": {k: v for k, v in kwargs.items() if k not in ["db"]}  # Exclude db session
    }
    data_str = json.dumps(data, sort_keys=True, default=str)
    hash_val = hashlib.md5(data_str.encode()).hexdigest()[:12]

    return f"{prefix}:{hash_val}"


# ============================================================================
# CACHE STORES
# ============================================================================

# In-memory cache with TTL
_cache_store: Dict[str, Tuple[any, datetime]] = {}


def _get_from_cache(key: str) -> Optional[any]:
    """Get value from cache if not expired.

    Args:
        key: Cache key

    Returns:
        Cached value or None if not found/expired
    """
    if key not in _cache_store:
        return None

    value, expiry = _cache_store[key]

    if datetime.now() > expiry:
        # Expired - remove from cache
        del _cache_store[key]
        return None

    return value


def _set_in_cache(key: str, value: any, ttl_seconds: int = CACHE_TTL_SECONDS):
    """Set value in cache with TTL.

    Args:
        key: Cache key
        value: Value to cache
        ttl_seconds: Time-to-live in seconds
    """
    expiry = datetime.now() + timedelta(seconds=ttl_seconds)
    _cache_store[key] = (value, expiry)

    # Cleanup old entries if cache is getting too large
    if len(_cache_store) > 1000:
        _cleanup_expired()


def _cleanup_expired():
    """Remove expired entries from cache."""
    now = datetime.now()
    expired_keys = [
        key for key, (_, expiry) in _cache_store.items()
        if now > expiry
    ]

    for key in expired_keys:
        del _cache_store[key]


def clear_cache():
    """Clear all cached data."""
    _cache_store.clear()


# ============================================================================
# CACHED QUERY FUNCTIONS
# ============================================================================

def cache_entity_lookup(entity_name: str, entity_type: str = None) -> Optional[Dict]:
    """Get cached entity lookup result.

    Args:
        entity_name: Entity name
        entity_type: Optional entity type

    Returns:
        Cached entity dict or None
    """
    cache_key = _generate_cache_key("entity", entity_name, entity_type)
    return _get_from_cache(cache_key)


def set_entity_lookup_cache(entity_name: str, entity_type: str, entities: List[Dict]):
    """Cache entity lookup result.

    Args:
        entity_name: Entity name
        entity_type: Entity type
        entities: List of entity dicts to cache
    """
    cache_key = _generate_cache_key("entity", entity_name, entity_type)
    _set_in_cache(cache_key, entities)


def cache_relationship_lookup(entity1: str, entity2: str = None) -> Optional[List[Dict]]:
    """Get cached relationship lookup result.

    Args:
        entity1: First entity name
        entity2: Optional second entity name

    Returns:
        Cached relationships list or None
    """
    cache_key = _generate_cache_key("relationship", entity1, entity2)
    return _get_from_cache(cache_key)


def set_relationship_lookup_cache(entity1: str, entity2: str, relationships: List[Dict]):
    """Cache relationship lookup result.

    Args:
        entity1: First entity name
        entity2: Second entity name
        relationships: List of relationship dicts to cache
    """
    cache_key = _generate_cache_key("relationship", entity1, entity2)
    _set_in_cache(cache_key, relationships)


def cache_task_matches(entities: List[str], relationships: List[str]) -> Optional[List[Dict]]:
    """Get cached task matching result.

    Args:
        entities: List of entity names
        relationships: List of relationship IDs

    Returns:
        Cached task matches or None
    """
    # Sort for deterministic key
    entities_sorted = tuple(sorted(entities))
    relationships_sorted = tuple(sorted(relationships))

    cache_key = _generate_cache_key("task_match", entities_sorted, relationships_sorted)
    return _get_from_cache(cache_key)


def set_task_matches_cache(entities: List[str], relationships: List[str], matches: List[Dict]):
    """Cache task matching result.

    Args:
        entities: List of entity names
        relationships: List of relationship IDs
        matches: List of task match dicts to cache
    """
    entities_sorted = tuple(sorted(entities))
    relationships_sorted = tuple(sorted(relationships))

    cache_key = _generate_cache_key("task_match", entities_sorted, relationships_sorted)
    _set_in_cache(cache_key, matches)


# ============================================================================
# CACHE STATISTICS
# ============================================================================

def get_cache_stats() -> Dict:
    """Get cache statistics.

    Returns:
        Dict with cache statistics
    """
    now = datetime.now()
    active_entries = sum(1 for _, expiry in _cache_store.values() if now <= expiry)
    expired_entries = len(_cache_store) - active_entries

    return {
        "total_entries": len(_cache_store),
        "active_entries": active_entries,
        "expired_entries": expired_entries,
        "cache_size_bytes": sum(
            len(str(v[0])) for v in _cache_store.values()
        )
    }
