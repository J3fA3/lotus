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
from datetime import datetime, timedelta, time
from typing import List, Optional
from dataclasses import dataclass

from db.models import CalendarEvent, WorkPreferences

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
        # Generate potential work time slots (workday hours)
        potential_blocks = self._generate_workday_blocks(
            start_date,
            end_date,
            preferences
        )

        # Remove busy times (meetings)
        free_blocks = []
        for block in potential_blocks:
            # Check if block overlaps with any event
            if not self._overlaps_with_events(block, calendar_events):
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

        # Sort by quality score (best first)
        free_blocks.sort(key=lambda b: b.quality_score, reverse=True)

        logger.info(f"Found {len(free_blocks)} free blocks (min {min_duration}min)")
        return free_blocks

    def _generate_workday_blocks(
        self,
        start_date: datetime,
        end_date: datetime,
        preferences: WorkPreferences
    ) -> List[dict]:
        """Generate potential work time blocks for each day.

        Args:
            start_date: Start date
            end_date: End date
            preferences: Work preferences

        Returns:
            List of time block dictionaries
        """
        blocks = []

        # Parse work hours
        work_start_hour = int(preferences.no_meetings_before.split(':')[0])
        work_end_hour = int(preferences.no_meetings_after.split(':')[0]) if preferences.no_meetings_after else 18

        current_date = start_date.date()
        end = end_date.date()

        while current_date <= end:
            # Skip weekends (Saturday=5, Sunday=6)
            if current_date.weekday() < 5:  # Monday=0, Friday=4
                # Create blocks for this workday
                day_start = datetime.combine(current_date, time(work_start_hour, 0))
                day_end = datetime.combine(current_date, time(work_end_hour, 0))

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
        """Check if time block overlaps with any calendar event.

        Args:
            block: Time block dictionary
            events: List of calendar events

        Returns:
            True if block overlaps with any event
        """
        block_start = block['start']
        block_end = block['end']

        for event in events:
            # Skip all-day events
            if event.all_day:
                continue

            # Check for overlap
            if (block_start < event.end_time and block_end > event.start_time):
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
