"""
Meeting Prep Assistant - Phase 4

Proactively identifies meetings needing preparation and suggests what to do.

Key Features:
1. Analyze upcoming meetings (next 3-7 days)
2. Identify incomplete related tasks
3. Generate prep checklists using Gemini
4. Calculate urgency based on meeting time
5. Prioritize high-importance meetings

Usage:
    assistant = get_meeting_prep_assistant()
    prep_suggestions = await assistant.analyze_upcoming_meetings(
        user_id=1,
        db=db,
        days_ahead=3
    )

    # Returns list of MeetingPrep objects with:
    # - meeting details
    # - prep checklist
    # - incomplete tasks
    # - urgency level
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from db.models import CalendarEvent, Task, MeetingPrep
from agents.enrichment_engine import get_gemini_client
from services.user_profile import get_user_profile
from utils.datetime_utils import now_utc, normalize_datetime
from utils.json_utils import parse_json_response

logger = logging.getLogger(__name__)


@dataclass
class MeetingPrepSuggestion:
    """Meeting prep suggestion."""
    calendar_event: CalendarEvent
    prep_needed: bool
    prep_checklist: List[str]
    incomplete_tasks: List[Task]
    estimated_prep_time: int  # minutes
    urgency: str  # critical, high, medium, low
    priority_score: int  # 0-100
    reasoning: str


class MeetingPrepAssistant:
    """Assistant for identifying meeting prep needs."""

    def __init__(self):
        """Initialize meeting prep assistant."""
        self.gemini = get_gemini_client()

    async def analyze_upcoming_meetings(
        self,
        user_id: int,
        db: AsyncSession,
        days_ahead: int = 3
    ) -> List[MeetingPrep]:
        """Analyze upcoming meetings and identify prep needs.

        Args:
            user_id: User ID
            db: Database session
            days_ahead: Days to look ahead (default: 3)

        Returns:
            List of MeetingPrep objects
        """
        try:
            logger.info(f"Analyzing meetings for user {user_id}, next {days_ahead} days")

            # 1. Get upcoming meetings
            meetings = await self._get_upcoming_meetings(user_id, db, days_ahead)
            logger.info(f"Found {len(meetings)} upcoming meetings")

            if not meetings:
                return []

            # 2. Get user profile for context
            user_profile = await get_user_profile(db, user_id)

            # 3. Analyze each meeting
            prep_suggestions = []
            for meeting in meetings:
                prep = await self._analyze_single_meeting(
                    meeting,
                    user_id,
                    user_profile,
                    db
                )
                if prep:
                    prep_suggestions.append(prep)

            logger.info(f"Generated {len(prep_suggestions)} prep suggestions")
            return prep_suggestions

        except Exception as e:
            logger.error(f"Meeting prep analysis failed: {e}")
            raise ValueError(f"Failed to analyze meetings: {e}")

    async def _get_upcoming_meetings(
        self,
        user_id: int,
        db: AsyncSession,
        days_ahead: int
    ) -> List[CalendarEvent]:
        """Get upcoming calendar meetings.

        Args:
            user_id: User ID
            db: Database session
            days_ahead: Days to look ahead

        Returns:
            List of CalendarEvent objects (meetings only)
        """
        start_time = now_utc()
        end_time = start_time + timedelta(days=days_ahead)

        query = select(CalendarEvent).where(
            and_(
                CalendarEvent.user_id == user_id,
                CalendarEvent.start_time >= start_time,
                CalendarEvent.start_time < end_time,
                CalendarEvent.is_meeting == True  # Only actual meetings, not task blocks
            )
        ).order_by(CalendarEvent.start_time)

        result = await db.execute(query)
        meetings = result.scalars().all()

        return list(meetings)

    async def _analyze_single_meeting(
        self,
        meeting: CalendarEvent,
        user_id: int,
        user_profile: any,
        db: AsyncSession
    ) -> Optional[MeetingPrep]:
        """Analyze a single meeting for prep needs.

        Args:
            meeting: Calendar event (meeting)
            user_id: User ID
            user_profile: User profile
            db: Database session

        Returns:
            MeetingPrep object or None if no prep needed
        """
        try:
            # 1. Check if meeting already marked as needing prep (from MeetingParser)
            if not meeting.prep_needed and not meeting.related_task_ids:
                # No prep needed and no related tasks
                logger.debug(f"Meeting '{meeting.title}' needs no prep")
                return None

            # 2. Get incomplete related tasks
            incomplete_tasks = await self._get_incomplete_tasks(
                meeting.related_task_ids or [],
                db
            )

            # 3. Calculate urgency
            urgency = self._calculate_urgency(meeting.start_time)

            # 4. Determine if prep actually needed (high-importance or has incomplete tasks)
            if not incomplete_tasks and meeting.importance_score < 70:
                logger.debug(f"Meeting '{meeting.title}' importance too low ({meeting.importance_score}), skipping")
                return None

            # 5. Generate prep checklist (use existing or generate with Gemini)
            if meeting.prep_checklist:
                prep_checklist = meeting.prep_checklist
                estimated_time = len(prep_checklist) * 15  # 15 min per item
                reasoning = "Meeting analysis indicated prep needed"
            else:
                prep_info = await self._generate_prep_checklist(
                    meeting,
                    incomplete_tasks,
                    user_profile
                )
                prep_checklist = prep_info['checklist']
                estimated_time = prep_info['estimated_time']
                reasoning = prep_info['reasoning']

            # 6. Calculate priority score
            priority_score = self._calculate_priority(
                meeting,
                incomplete_tasks,
                urgency
            )

            # 7. Check if prep record already exists
            existing_prep = await self._get_existing_prep(meeting.id, db)

            if existing_prep:
                # Update existing
                existing_prep.prep_checklist = prep_checklist
                existing_prep.incomplete_task_ids = [t.id for t in incomplete_tasks]
                existing_prep.estimated_prep_time = estimated_time
                existing_prep.urgency = urgency
                existing_prep.priority_score = priority_score
                existing_prep.reasoning = reasoning
                existing_prep.prep_completed = False  # Reset if new tasks appeared
                await db.commit()
                return existing_prep
            else:
                # Create new prep record
                prep = MeetingPrep(
                    calendar_event_id=meeting.id,
                    user_id=user_id,
                    prep_needed=True,
                    prep_checklist=prep_checklist,
                    incomplete_task_ids=[t.id for t in incomplete_tasks],
                    estimated_prep_time=estimated_time,
                    urgency=urgency,
                    priority_score=priority_score,
                    reasoning=reasoning
                )
                db.add(prep)
                await db.commit()
                await db.refresh(prep)

                logger.info(f"Created prep suggestion for '{meeting.title}' (urgency: {urgency})")
                return prep

        except Exception as e:
            logger.error(f"Failed to analyze meeting '{meeting.title}': {e}")
            return None

    async def _get_incomplete_tasks(
        self,
        task_ids: List[str],
        db: AsyncSession
    ) -> List[Task]:
        """Get incomplete tasks from list of IDs.

        Args:
            task_ids: List of task IDs
            db: Database session

        Returns:
            List of incomplete Task objects
        """
        if not task_ids:
            return []

        try:
            query = select(Task).where(
                and_(
                    Task.id.in_(task_ids),
                    Task.status.in_(['todo', 'doing'])  # Not completed
                )
            )

            result = await db.execute(query)
            tasks = result.scalars().all()

            return list(tasks)

        except Exception as e:
            logger.error(f"Failed to get incomplete tasks: {e}")
            return []

    def _calculate_urgency(self, meeting_time: datetime) -> str:
        """Calculate meeting urgency based on time until meeting.

        Args:
            meeting_time: Meeting start time

        Returns:
            "critical", "high", "medium", or "low"
        """
        now = now_utc()
        # Ensure meeting_time is timezone-aware
        meeting_time = normalize_datetime(meeting_time)
        hours_until = (meeting_time - now).total_seconds() / 3600

        if hours_until < 4:
            return "critical"  # Meeting in <4 hours
        elif hours_until < 24:
            return "high"  # Meeting today or tomorrow morning
        elif hours_until < 48:
            return "medium"  # Meeting tomorrow
        else:
            return "low"  # Meeting 2+ days away

    async def _generate_prep_checklist(
        self,
        meeting: CalendarEvent,
        incomplete_tasks: List[Task],
        user_profile: any
    ) -> dict:
        """Generate prep checklist using Gemini.

        Args:
            meeting: Calendar event
            incomplete_tasks: Incomplete related tasks
            user_profile: User profile

        Returns:
            Dictionary with checklist, estimated_time, reasoning
        """
        try:
            # Build prompt for Gemini
            tasks_str = "\n".join([
                f"- {task.title} ({task.status})"
                for task in incomplete_tasks
            ]) if incomplete_tasks else "None"

            prompt = f"""You are Lotus, {user_profile.name}'s AI assistant. Generate a prep checklist for this meeting.

**Meeting:**
- Title: {meeting.title}
- Time: {meeting.start_time.strftime('%A, %B %d at %I:%M %p')}
- Attendees: {', '.join(meeting.attendees[:5]) if meeting.attendees else 'Unknown'}
- Description: {meeting.description or 'None'}

**Context:**
- User: {user_profile.name} ({user_profile.role})
- Projects: {', '.join(user_profile.projects)}
- Importance: {meeting.importance_score}/100

**Incomplete Related Tasks:**
{tasks_str}

**Generate:**
1. **Prep Checklist**: 2-4 specific action items to prepare for this meeting
2. **Estimated Time**: Total minutes needed for prep (realistic estimate)
3. **Reasoning**: Brief explanation of why this prep is important

Return ONLY valid JSON (no markdown):
{{
  "checklist": ["Review Q4 metrics dashboard", "Prepare demo walkthrough"],
  "estimated_time": 45,
  "reasoning": "High-stakes quarterly review with senior stakeholders"
}}

JSON response:"""

            # Call Gemini
            response_text = await self.gemini.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=1024,
                fallback_to_qwen=True
            )

            # Parse response using shared utility
            default = {
                'checklist': [],
                'estimated_time': 30,
                'reasoning': 'Basic prep needed'
            }
            result = parse_json_response(response_text, default=default)

            return {
                'checklist': result.get('checklist', []),
                'estimated_time': result.get('estimated_time', 30),
                'reasoning': result.get('reasoning', 'Prep needed for meeting')
            }

        except Exception as e:
            logger.error(f"Failed to generate prep checklist with Gemini: {e}")
            # Fallback to simple checklist
            checklist = []
            if incomplete_tasks:
                checklist.append(f"Complete {len(incomplete_tasks)} related task(s)")
            checklist.append(f"Review meeting agenda and materials")

            return {
                'checklist': checklist,
                'estimated_time': 30,
                'reasoning': 'Basic prep needed'
            }

    def _calculate_priority(
        self,
        meeting: CalendarEvent,
        incomplete_tasks: List[Task],
        urgency: str
    ) -> int:
        """Calculate priority score for meeting prep.

        Args:
            meeting: Calendar event
            incomplete_tasks: Incomplete tasks
            urgency: Urgency level

        Returns:
            Priority score 0-100
        """
        score = 50  # Base score

        # Importance boost
        if meeting.importance_score:
            score += (meeting.importance_score - 50) * 0.5

        # Urgency boost
        urgency_scores = {
            'critical': 40,
            'high': 25,
            'medium': 10,
            'low': 0
        }
        score += urgency_scores.get(urgency, 0)

        # Incomplete tasks penalty (urgent if tasks not done)
        score += min(20, len(incomplete_tasks) * 5)

        return min(100, max(0, int(score)))

    async def _get_existing_prep(
        self,
        calendar_event_id: int,
        db: AsyncSession
    ) -> Optional[MeetingPrep]:
        """Get existing prep record for meeting.

        Args:
            calendar_event_id: Calendar event ID
            db: Database session

        Returns:
            MeetingPrep object or None
        """
        query = select(MeetingPrep).where(
            MeetingPrep.calendar_event_id == calendar_event_id
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_daily_prep_summary(
        self,
        user_id: int,
        db: AsyncSession
    ) -> dict:
        """Get daily prep summary for notifications.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Dictionary with prep summary
        """
        # Get prep suggestions for today and tomorrow
        prep_items = await self.analyze_upcoming_meetings(
            user_id,
            db,
            days_ahead=2
        )

        # Filter to incomplete prep
        incomplete_prep = [
            p for p in prep_items
            if not p.prep_completed and p.urgency in ['critical', 'high']
        ]

        return {
            'total_meetings': len(prep_items),
            'needs_prep': len(incomplete_prep),
            'prep_items': incomplete_prep,
            'estimated_total_time': sum(p.estimated_prep_time or 0 for p in incomplete_prep)
        }


# Singleton instance
_meeting_prep_assistant = None


def get_meeting_prep_assistant() -> MeetingPrepAssistant:
    """Get singleton meeting prep assistant instance.

    Returns:
        MeetingPrepAssistant instance
    """
    global _meeting_prep_assistant
    if _meeting_prep_assistant is None:
        _meeting_prep_assistant = MeetingPrepAssistant()
    return _meeting_prep_assistant
