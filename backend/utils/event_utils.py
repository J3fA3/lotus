"""
Calendar event utility functions.

Shared logic for determining event properties like blocking status and meeting detection.
"""

import logging
from typing import List

from db.models import CalendarEvent

logger = logging.getLogger(__name__)

# Keywords that indicate working hours blocks (non-blocking)
WORKING_BLOCK_KEYWORDS = [
    "working", "work", "available", "office hours",
    "focus time", "deep work", "block", "busy"
]

# Keywords that indicate unavailability (blocking)
UNAVAILABILITY_KEYWORDS = [
    "out of office", "out of the office", "oof", "away",
    "vacation", "holiday", "sick", "leave", "pto",
    "unavailable", "off", "not available", "do not schedule",
    "guest list", "hidden", "private"
]


def is_blocking_event(event: CalendarEvent) -> bool:
    """Determine if an event should block task scheduling.
    
    Blocks scheduling if:
    - It's an actual meeting (is_meeting=True OR has multiple attendees)
    - It's an "out of office" / "away" / "unavailable" event
    - It's an all-day event that indicates unavailability
    - It's any regular event (not a working hours block)
    
    Does NOT block if:
    - It's a Lotus-created task block (🪷 prefix)
    - It's a personal working hours block ("Working", "Available", etc.)
    
    Args:
        event: Calendar event to check
        
    Returns:
        True if event should block scheduling
    """
    title = event.title or ""
    title_lower = title.lower()
    attendees = event.attendees or []
    has_multiple_attendees = len(attendees) > 1
    
    # Skip Lotus-created task blocks (can be scheduled over)
    if title.startswith("🪷"):
        return False
    
    # CRITICAL: All-day events that indicate unavailability SHOULD block
    if event.all_day:
        if any(keyword in title_lower for keyword in UNAVAILABILITY_KEYWORDS):
            logger.debug(f"Blocking all-day unavailability event: '{title}'")
            return True
        # Other all-day events (like "Working Hours") are usually availability markers
        return False
    
    # If it's marked as a meeting OR has multiple attendees, it blocks
    if event.is_meeting or has_multiple_attendees:
        return True
    
    # CRITICAL: Events with organizer but no/hidden attendees are likely meetings
    # Google Calendar hides guest lists for privacy - these should still block
    if event.organizer and len(attendees) <= 1:
        logger.debug(f"Blocking event with organizer (likely hidden guest list): '{title}'")
        return True
    
    # Check for unavailability keywords (even for timed events)
    if any(keyword in title_lower for keyword in UNAVAILABILITY_KEYWORDS):
        logger.debug(f"Blocking unavailability event: '{title}'")
        return True
    
    # Check description for unavailability keywords
    description = (event.description or "").lower()
    if any(keyword in description for keyword in UNAVAILABILITY_KEYWORDS):
        logger.debug(f"Blocking event (unavailability in description): '{title}'")
        return True
    
    # Check for common working hours block patterns (these DON'T block)
    if any(keyword in title_lower for keyword in WORKING_BLOCK_KEYWORDS):
        if len(attendees) <= 1:
            logger.debug(f"Skipping working hours block: '{title}' (no real attendees)")
            return False
    
    # Calculate duration for long events
    from datetime import timezone
    from utils.datetime_utils import normalize_datetime
    
    event_start = normalize_datetime(event.start_time)
    event_end = normalize_datetime(event.end_time)
    duration_hours = (event_end - event_start).total_seconds() / 3600
    
    # Long events (4+ hours) with no attendees might be working blocks
    if duration_hours >= 4 and len(attendees) <= 1:
        # Only skip if it matches working block patterns
        if any(keyword in title_lower for keyword in WORKING_BLOCK_KEYWORDS):
            logger.debug(f"Skipping long working block: '{title}' ({duration_hours:.1f}h, no attendees)")
            return False
    
    # DEFAULT: Block everything else (conservative approach)
    logger.debug(
        f"Blocking event (default conservative): '{title}' "
        f"(not a working hours block, duration={duration_hours:.1f}h, attendees={len(attendees)})"
    )
    return True


def filter_blocking_events(events: List[CalendarEvent]) -> List[CalendarEvent]:
    """Filter events to only those that block scheduling.
    
    Args:
        events: List of calendar events
        
    Returns:
        List of blocking events only
    """
    return [e for e in events if is_blocking_event(e)]

