"""
Datetime and timezone utility functions.

Provides consistent timezone-aware datetime operations across the codebase.
All datetimes are normalized to UTC for consistency.
"""

from datetime import datetime, timezone
from typing import Optional


def now_utc() -> datetime:
    """Get current time as timezone-aware UTC datetime.
    
    Returns:
        Current datetime in UTC with timezone info
    """
    return datetime.now(timezone.utc)


def normalize_datetime(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware (UTC).
    
    Args:
        dt: Datetime (may be naive or timezone-aware)
        
    Returns:
        Timezone-aware datetime in UTC
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def parse_iso_datetime(time_str: str) -> datetime:
    """Parse ISO datetime string and ensure timezone-aware.
    
    Handles both 'Z' suffix and '+00:00' formats.
    
    Args:
        time_str: ISO datetime string (may have 'Z' suffix)
        
    Returns:
        Timezone-aware datetime in UTC
        
    Raises:
        ValueError: If time_str cannot be parsed
    """
    # Replace 'Z' with '+00:00' for proper parsing
    normalized_str = time_str.replace('Z', '+00:00')
    dt = datetime.fromisoformat(normalized_str)
    return normalize_datetime(dt)


def ensure_timezone_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime is timezone-aware, return None if input is None.
    
    Args:
        dt: Datetime or None
        
    Returns:
        Timezone-aware datetime or None
    """
    if dt is None:
        return None
    return normalize_datetime(dt)

