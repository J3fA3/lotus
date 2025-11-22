"""
Availability Analyzer - Phase 4

Analyzes calendar to find free time blocks for task work.

Key Features:
1. Find free blocks between meetings
2. Score blocks by quality (based on user preferences)
3. Respect work hours (no work before 9am)
4. Prefer afternoon blocks for Jef (deep work time)
5. Handle all-day events and conflicts

Usage:
    analyzer = AvailabilityAnalyzer()
    free_blocks = analyzer.find_free_blocks(
        calendar_events,
        preferences,
        min_duration=30
    )

    # Returns sorted list of FreeBlock objects (best first)
"""

import logging
from datetime import datetime, timedelta, time, timezone
from typing import List, Optional
from dataclasses import dataclass

from db.models import CalendarEvent, WorkPreferences
from utils.datetime_utils import normalize_datetime
from utils.event_utils import is_blocking_event, filter_blocking_events

logger = logging.getLogger(__name__)


@dataclass
class FreeBlock:
    """Represents a free time block."""
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    quality_score: int  # 0-100 (higher = better for task work)
    time_of_day: str  # morning, afternoon, evening


class AvailabilityAnalyzer:
    """Service for analyzing calendar availability."""

    def __init__(self):
        """Initialize availability analyzer."""
        pass

    def find_free_blocks(
        self,
        calendar_events: List[CalendarEvent],
        preferences: WorkPreferences,
        start_date: datetime,
        end_date: datetime,
        min_duration: int = 30
    ) -> List[FreeBlock]:
        """Find free time blocks for task work.

        Args:
            calendar_events: List of calendar events (meetings, blocks)
            preferences: User work preferences
            start_date: Start of search range
            end_date: End of search range
            min_duration: Minimum block duration in minutes

        Returns:
            Sorted list of free blocks (best quality first)
        """
        logger.info(f"Finding free blocks: {len(calendar_events)} events, {start_date} to {end_date}, min {min_duration}min")
        logger.info(f"Work hours: {preferences.no_meetings_before} to {preferences.no_meetings_after}")
        
        # Reset debug counter
        self._overlap_debug_count = 0
        
        # Ensure timezone-aware datetimes
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        logger.info(f"Date range (timezone-aware): {start_date} to {end_date}")
        
        # Generate potential work time slots (workday hours)
        potential_blocks = self._generate_workday_blocks(
            start_date,
            end_date,
            preferences
        )
        
        logger.info(f"Generated {len(potential_blocks)} potential workday blocks")

        # Remove busy times (meetings)
        free_blocks = []
        overlapping_count = 0
        
        # Filter events to date range and separate blocking vs non-blocking
        # CRITICAL: Ensure all event times are timezone-aware before comparison
        events_in_range = []
        for e in calendar_events:
            event_start = e.start_time
            event_end = e.end_time
            
            # Ensure timezone-aware
            if event_start.tzinfo is None:
                event_start = event_start.replace(tzinfo=timezone.utc)
            if event_end.tzinfo is None:
                event_end = event_end.replace(tzinfo=timezone.utc)
            
            # Now safe to compare
            if event_start < end_date and event_end > start_date:
                events_in_range.append(e)
        
        # Separate blocking events (actual meetings) from non-blocking (working hours blocks)
        blocking_events = filter_blocking_events(events_in_range)
        non_blocking_events = [e for e in events_in_range if not is_blocking_event(e)]
        
        logger.info(
            f"Events in date range: {len(events_in_range)}/{len(calendar_events)} "
            f"({len(blocking_events)} blocking meetings, {len(non_blocking_events)} working hours blocks)"
        )
        
        if blocking_events:
            sample_meetings = blocking_events[:5]
            logger.info(f"Sample blocking meetings (first 5):")
            for event in sample_meetings:
                attendees_count = len(event.attendees or [])
                logger.info(
                    f"  - '{event.title}': {event.start_time} to {event.end_time} "
                    f"({attendees_count} attendees, is_meeting={event.is_meeting})"
                )
        
        if non_blocking_events:
            sample_blocks = non_blocking_events[:5]
            logger.info(f"Sample non-blocking events (working hours blocks, first 5):")
            for event in sample_blocks:
                logger.info(f"  - '{event.title}': {event.start_time} to {event.end_time} (ignored for scheduling)")
        
        # Use only blocking events (actual meetings) for overlap checking
        calendar_events = blocking_events
        
        for block in potential_blocks:
            # Check if block overlaps with any blocking event
            # CRITICAL: Double-check overlap to ensure we're not missing anything
            overlaps = self._overlaps_with_events(block, calendar_events)
            
            if not overlaps:
                # Score block quality
                quality_score = self._score_block_quality(block, preferences)

                if block['duration_minutes'] >= min_duration:
                    free_blocks.append(FreeBlock(
                        start_time=block['start'],
                        end_time=block['end'],
                        duration_minutes=block['duration_minutes'],
                        quality_score=quality_score,
                        time_of_day=self._get_time_of_day(block['start'])
                    ))
            else:
                overlapping_count += 1
                # Log first few overlaps for debugging
                if overlapping_count <= 3:
                    logger.debug(
                        f"Block {block['start']} to {block['end']} overlaps with blocking event"
                    )
        
        # Log diagnostic info
        if len(potential_blocks) > 0:
            logger.info(f"Block filtering: {overlapping_count}/{len(potential_blocks)} blocks overlap with events, {len(free_blocks)} free blocks remain")
            if len(free_blocks) == 0 and len(potential_blocks) > 0:
                # Log sample of potential blocks to see what we're generating
                logger.info(f"Sample potential blocks (first 3):")
                for block in potential_blocks[:3]:
                    logger.info(f"  - {block['start']} to {block['end']} ({block['duration_minutes']}min, tz={block['start'].tzinfo})")

        # Merge adjacent blocks to create larger blocks (better for deep work)
        if free_blocks:
            free_blocks = self.merge_adjacent_blocks(free_blocks, max_gap_minutes=0)
            logger.info(f"After merging adjacent blocks: {len(free_blocks)} free blocks")
        
        # Sort by quality score (best first)
        free_blocks.sort(key=lambda b: b.quality_score, reverse=True)

        logger.info(f"Found {len(free_blocks)} free blocks (min {min_duration}min) after filtering and merging")
        if len(free_blocks) == 0 and len(calendar_events) > 0:
            logger.warning(
                f"No free blocks found despite {len(potential_blocks)} potential blocks. "
                f"Calendar may be completely full. "
                f"Work hours: {preferences.no_meetings_before}-{preferences.no_meetings_after}, "
                f"Events in range: {len(events_in_range)}"
            )
        elif len(free_blocks) == 0:
            logger.warning(f"No free blocks found. Check work hours configuration (start: {preferences.no_meetings_before}, end: {preferences.no_meetings_after})")
        
        return free_blocks

    def _generate_workday_blocks(
        self,
        start_date: datetime,
        end_date: datetime,
        preferences: WorkPreferences
    ) -> List[dict]:
        """Generate potential work time blocks for each day.

        Args:
            start_date: Start date (timezone-aware)
            end_date: End date (timezone-aware)
            preferences: Work preferences

        Returns:
            List of time block dictionaries with timezone-aware datetimes
        """
        blocks = []

        # Parse work hours
        work_start_hour = int(preferences.no_meetings_before.split(':')[0])
        work_end_hour = int(preferences.no_meetings_after.split(':')[0]) if preferences.no_meetings_after else 18

        # Get timezone from start_date, or default to UTC
        tz = start_date.tzinfo or timezone.utc

        current_date = start_date.date()
        end = end_date.date()
        # CRITICAL: Ensure now is timezone-aware with same timezone as start_date
        now = datetime.now(tz) if tz else datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        while current_date <= end:
            # Skip weekends (Saturday=5, Sunday=6)
            if current_date.weekday() < 5:  # Monday=0, Friday=4
                # Create blocks for this workday (timezone-aware)
                day_start = datetime.combine(current_date, time(work_start_hour, 0), tz)
                day_end = datetime.combine(current_date, time(work_end_hour, 0), tz)
                
                # If this is today, start from current time (not beginning of day)
                # CRITICAL: Both must be timezone-aware for comparison
                if current_date == now.date():
                    # Ensure both are in same timezone for max() comparison
                    if day_start.tzinfo != now.tzinfo:
                        if day_start.tzinfo is None:
                            day_start = day_start.replace(tzinfo=now.tzinfo)
                        elif now.tzinfo is None:
                            now = now.replace(tzinfo=day_start.tzinfo)
                    day_start = max(day_start, now)
                    # Round up to next 30-minute mark for cleaner blocks
                    if day_start.minute % 30 != 0:
                        minutes_to_add = 30 - (day_start.minute % 30)
                        day_start = day_start + timedelta(minutes=minutes_to_add)

                # Split into 30-minute blocks for finer granularity
                current_time = day_start
                while current_time < day_end:
                    block_end = min(current_time + timedelta(minutes=30), day_end)
                    duration = int((block_end - current_time).total_seconds() / 60)

                    blocks.append({
                        'start': current_time,
                        'end': block_end,
                        'duration_minutes': duration
                    })

                    current_time = block_end

            current_date += timedelta(days=1)

        return blocks

    def _overlaps_with_events(
        self,
        block: dict,
        events: List[CalendarEvent]
    ) -> bool:
        """Check if time block overlaps with any blocking calendar event.

        Args:
            block: Time block dictionary with timezone-aware datetimes
            events: List of calendar events

        Returns:
            True if block overlaps with any blocking event
        """
        block_start = block['start']
        block_end = block['end']

        # Ensure block times are timezone-aware
        if block_start.tzinfo is None:
            block_start = block_start.replace(tzinfo=timezone.utc)
        if block_end.tzinfo is None:
            block_end = block_end.replace(tzinfo=timezone.utc)

        for event in events:
            # Skip non-blocking events (working hours blocks, personal blocks, etc.)
            if not is_blocking_event(event):
                continue

            # Ensure event times are timezone-aware for comparison
            event_start = normalize_datetime(event.start_time)
            event_end = normalize_datetime(event.end_time)

            # Check for overlap (blocks overlap if they share any time)
            # Two time ranges overlap if: start1 < end2 AND start2 < end1
            overlaps = (block_start < event_end and block_end > event_start)
            
            if overlaps:
                # Log first few overlaps for debugging
                if hasattr(self, '_overlap_debug_count'):
                    self._overlap_debug_count += 1
                else:
                    self._overlap_debug_count = 1
                
                if self._overlap_debug_count <= 3:
                    logger.debug(
                        f"Block overlaps with meeting: "
                        f"block [{block_start} - {block_end}] vs "
                        f"meeting '{event.title}' [{event_start} - {event_end}] "
                        f"(attendees: {len(event.attendees or [])})"
                    )
                
                return True

        return False

    def _score_block_quality(
        self,
        block: dict,
        preferences: WorkPreferences
    ) -> int:
        """Score time block quality based on user preferences.

        Args:
            block: Time block dictionary
            preferences: User preferences

        Returns:
            Quality score 0-100 (higher = better)
        """
        score = 50  # Base score

        hour = block['start'].hour
        duration = block['duration_minutes']

        # Jef prefers afternoon (2pm-7pm) for deep work
        if preferences.deep_work_time == "afternoon_evening":
            if 14 <= hour < 17:
                score += 30  # Afternoon peak (2pm-5pm)
            elif 17 <= hour < 19:
                score += 25  # Evening still good
            elif 12 <= hour < 14:
                score += 15  # Early afternoon okay
            elif 9 <= hour < 12:
                score += 5   # Morning less preferred
            else:
                score -= 10  # Too early or too late

        elif preferences.deep_work_time == "morning":
            if 9 <= hour < 12:
                score += 30  # Morning peak
            elif 8 <= hour < 9:
                score += 20  # Early morning
            else:
                score += 10  # Afternoon okay

        elif preferences.deep_work_time == "evening":
            if 17 <= hour < 20:
                score += 30  # Evening peak
            elif 14 <= hour < 17:
                score += 20  # Afternoon good
            else:
                score += 10  # Other times okay

        # Longer blocks are better (deep work)
        if duration >= 120:
            score += 20  # 2+ hours
        elif duration >= 90:
            score += 15  # 1.5 hours
        elif duration >= 60:
            score += 10  # 1 hour
        elif duration >= 30:
            score += 5   # 30 minutes

        # Penalize very early or very late
        if hour < 9:
            score -= 20  # Before work hours
        elif hour >= 19:
            score -= 10  # After work hours

        # Ensure score stays in 0-100 range
        return max(0, min(100, score))

    def _get_time_of_day(self, dt: datetime) -> str:
        """Get time of day category.

        Args:
            dt: Datetime

        Returns:
            "morning", "afternoon", or "evening"
        """
        hour = dt.hour

        if hour < 12:
            return "morning"
        elif hour < 17:
            return "afternoon"
        else:
            return "evening"

    def merge_adjacent_blocks(
        self,
        blocks: List[FreeBlock],
        max_gap_minutes: int = 15
    ) -> List[FreeBlock]:
        """Merge adjacent free blocks into larger blocks.

        Args:
            blocks: List of free blocks
            max_gap_minutes: Maximum gap to merge (default: 15 min)

        Returns:
            List of merged blocks
        """
        if not blocks:
            return []

        # Sort by start time
        sorted_blocks = sorted(blocks, key=lambda b: b.start_time)

        merged = []
        current = sorted_blocks[0]

        for next_block in sorted_blocks[1:]:
            # Check if blocks are adjacent (or close enough to merge)
            gap_minutes = int((next_block.start_time - current.end_time).total_seconds() / 60)

            if gap_minutes <= max_gap_minutes:
                # Merge blocks
                current = FreeBlock(
                    start_time=current.start_time,
                    end_time=next_block.end_time,
                    duration_minutes=int((next_block.end_time - current.start_time).total_seconds() / 60),
                    quality_score=(current.quality_score + next_block.quality_score) // 2,
                    time_of_day=current.time_of_day
                )
            else:
                # Save current and start new block
                merged.append(current)
                current = next_block

        # Add last block
        merged.append(current)

        return merged

    def find_best_block_for_duration(
        self,
        free_blocks: List[FreeBlock],
        duration_minutes: int
    ) -> Optional[FreeBlock]:
        """Find best free block that can fit the given duration.

        Args:
            free_blocks: List of free blocks (should be sorted by quality)
            duration_minutes: Required duration

        Returns:
            Best matching block or None
        """
        # Find blocks that can fit the duration
        suitable_blocks = [
            b for b in free_blocks
            if b.duration_minutes >= duration_minutes
        ]

        if not suitable_blocks:
            return None

        # Return best quality block
        return suitable_blocks[0]


# Singleton instance
_availability_analyzer = None


def get_availability_analyzer() -> AvailabilityAnalyzer:
    """Get singleton availability analyzer instance.

    Returns:
        AvailabilityAnalyzer instance
    """
    global _availability_analyzer
    if _availability_analyzer is None:
        _availability_analyzer = AvailabilityAnalyzer()
    return _availability_analyzer
