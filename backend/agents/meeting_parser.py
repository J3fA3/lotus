"""
Meeting Parser Agent - Phase 4

Uses Gemini 2.0 Flash to analyze calendar meetings and extract context.

Key Features:
1. Extract related projects from meeting title/description
2. Identify related tasks from knowledge graph
3. Score meeting importance (0-100)
4. Determine if prep needed
5. Generate prep checklist

Usage:
    parser = MeetingParserAgent()
    parsed = await parser.parse_meeting(calendar_event, user_profile, db)

    # Result:
    # - related_projects: ["CRESCO", "RF16"]
    # - related_tasks: [task objects]
    # - importance_score: 85
    # - prep_needed: True
    # - prep_checklist: ["Review dashboard", "Prepare demo"]
"""

import logging
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.models import CalendarEvent, Task
from services.user_profile import UserProfile
from agents.enrichment_engine import get_gemini_client

logger = logging.getLogger(__name__)


@dataclass
class ParsedMeeting:
    """Parsed meeting with extracted context."""
    event: CalendarEvent
    related_projects: List[str]
    related_task_ids: List[str]
    importance_score: int  # 0-100
    prep_needed: bool
    prep_checklist: List[str]
    reasoning: str


class MeetingParserAgent:
    """Agent for parsing calendar meetings using Gemini."""

    def __init__(self):
        """Initialize meeting parser."""
        self.gemini = get_gemini_client()

    async def parse_meeting(
        self,
        event: CalendarEvent,
        user_profile: UserProfile,
        db: AsyncSession
    ) -> ParsedMeeting:
        """Parse meeting using Gemini to extract relevant context.

        Args:
            event: Calendar event to parse
            user_profile: User profile for context
            db: Database session

        Returns:
            ParsedMeeting with extracted context
        """
        try:
            # Get recent tasks for context
            recent_tasks = await self._get_recent_tasks(user_profile.user_id, db)

            # Build prompt for Gemini
            prompt = self._build_parsing_prompt(event, user_profile, recent_tasks)

            # Call Gemini
            response_text = await self.gemini.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=1024,
                fallback_to_qwen=True
            )
            result = self._parse_gemini_response(response_text)

            # Get related tasks from knowledge graph
            related_tasks = await self._find_related_tasks(
                result.get("related_projects", []),
                user_profile.user_id,
                db
            )

            parsed = ParsedMeeting(
                event=event,
                related_projects=result.get("related_projects", []),
                related_task_ids=[t.id for t in related_tasks],
                importance_score=result.get("importance_score", 50),
                prep_needed=result.get("prep_needed", False),
                prep_checklist=result.get("prep_checklist", []),
                reasoning=result.get("reasoning", "")
            )

            # Update calendar event with parsed data
            event.related_projects = parsed.related_projects
            event.related_task_ids = parsed.related_task_ids
            event.importance_score = parsed.importance_score
            event.prep_needed = parsed.prep_needed
            event.prep_checklist = parsed.prep_checklist
            await db.commit()

            logger.info(f"Parsed meeting '{event.title}': importance={parsed.importance_score}, prep={parsed.prep_needed}")
            return parsed

        except Exception as e:
            logger.error(f"Meeting parsing failed for '{event.title}': {e}")

            # Return default values on error
            return ParsedMeeting(
                event=event,
                related_projects=[],
                related_task_ids=[],
                importance_score=50,
                prep_needed=False,
                prep_checklist=[],
                reasoning=f"Failed to parse: {e}"
            )

    def _build_parsing_prompt(
        self,
        event: CalendarEvent,
        user_profile: UserProfile,
        recent_tasks: List[Task]
    ) -> str:
        """Build Gemini prompt for meeting parsing.

        Args:
            event: Calendar event
            user_profile: User profile
            recent_tasks: Recent tasks for context

        Returns:
            Prompt string
        """
        # Format attendees
        attendees_str = ", ".join(event.attendees[:5]) if event.attendees else "None"
        if len(event.attendees) > 5:
            attendees_str += f" and {len(event.attendees) - 5} more"

        # Format recent tasks
        tasks_context = "\n".join([
            f"- {t.title} (status: {t.status}, project: {t.value_stream or 'unknown'})"
            for t in recent_tasks[:10]
        ])

        prompt = f"""You are Lotus, Jef's AI work assistant. Analyze this calendar meeting and extract relevant context.

Meeting Details:
- Title: {event.title}
- Description: {event.description or 'None'}
- Time: {event.start_time.strftime('%Y-%m-%d %H:%M')} to {event.end_time.strftime('%H:%M')}
- Attendees: {attendees_str}
- Location: {event.location or 'None'}

Jef's Context:
- Name: {user_profile.name}
- Role: {user_profile.role}
- Company: {user_profile.company}
- Projects: {', '.join(user_profile.projects)}
- Markets: {', '.join(user_profile.markets)}
- Colleagues: {', '.join(user_profile.colleagues.keys())}

Recent Tasks (for reference):
{tasks_context}

Analyze this meeting and extract:
1. **Related Projects**: Which of Jef's projects is this meeting about? (from: {', '.join(user_profile.projects)})
2. **Importance Score**: How important is this meeting for Jef? (0-100)
   - 90-100: Critical (CEO, major deadlines, key decisions)
   - 70-89: High (team meetings, project reviews, demos)
   - 50-69: Medium (regular 1:1s, status updates)
   - 30-49: Low (FYI meetings, optional attendance)
   - 0-29: Very low (informational, could skip)
3. **Prep Needed**: Does Jef need to prepare anything? (true/false)
4. **Prep Checklist**: If prep needed, what should Jef do? (2-3 specific items)
5. **Reasoning**: Brief explanation of your analysis

Return ONLY valid JSON (no markdown, no explanation):
{{
    "related_projects": ["CRESCO"],
    "importance_score": 85,
    "prep_needed": true,
    "prep_checklist": ["Review Q4 metrics", "Prepare demo of dashboard"],
    "reasoning": "Important quarterly review for CRESCO project with senior stakeholders"
}}

JSON response:"""

        return prompt

    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini response JSON.

        Args:
            response_text: Raw response from Gemini

        Returns:
            Parsed dictionary
        """
        try:
            # Remove markdown code blocks if present
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            text = text.strip()

            # Parse JSON
            result = json.loads(text)
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.debug(f"Raw response: {response_text}")

            # Return default values
            return {
                "related_projects": [],
                "importance_score": 50,
                "prep_needed": False,
                "prep_checklist": [],
                "reasoning": "Failed to parse response"
            }

    async def _get_recent_tasks(
        self,
        user_id: int,
        db: AsyncSession,
        limit: int = 20
    ) -> List[Task]:
        """Get recent tasks for context.

        Args:
            user_id: User ID (currently unused, but for future multi-user support)
            db: Database session
            limit: Maximum tasks to return

        Returns:
            List of recent tasks
        """
        try:
            # Get recent tasks (active or recently updated)
            query = select(Task).where(
                Task.status.in_(['todo', 'doing'])
            ).order_by(Task.updated_at.desc()).limit(limit)

            result = await db.execute(query)
            tasks = result.scalars().all()
            return list(tasks)

        except Exception as e:
            logger.error(f"Failed to get recent tasks: {e}")
            return []

    async def _find_related_tasks(
        self,
        projects: List[str],
        user_id: int,
        db: AsyncSession
    ) -> List[Task]:
        """Find tasks related to meeting projects.

        Args:
            projects: Project names
            user_id: User ID
            db: Database session

        Returns:
            List of related tasks
        """
        if not projects:
            return []

        try:
            # Find tasks with matching projects
            query = select(Task).where(
                Task.value_stream.in_(projects),
                Task.status.in_(['todo', 'doing'])
            ).limit(10)

            result = await db.execute(query)
            tasks = result.scalars().all()
            return list(tasks)

        except Exception as e:
            logger.error(f"Failed to find related tasks: {e}")
            return []

    async def parse_all_upcoming_meetings(
        self,
        user_id: int,
        user_profile: UserProfile,
        db: AsyncSession,
        days_ahead: int = 7
    ) -> List[ParsedMeeting]:
        """Parse all upcoming meetings for a user.

        Args:
            user_id: User ID
            user_profile: User profile
            db: Database session
            days_ahead: Days to look ahead

        Returns:
            List of parsed meetings
        """
        from datetime import datetime, timedelta

        from datetime import timezone
        # Get upcoming calendar events
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(days=days_ahead)

        query = select(CalendarEvent).where(
            CalendarEvent.user_id == user_id,
            CalendarEvent.start_time >= start_time,
            CalendarEvent.start_time < end_time,
            CalendarEvent.is_meeting == True  # Only parse actual meetings
        ).order_by(CalendarEvent.start_time)

        result = await db.execute(query)
        events = result.scalars().all()

        # Parse each meeting
        parsed_meetings = []
        for event in events:
            parsed = await self.parse_meeting(event, user_profile, db)
            parsed_meetings.append(parsed)

        logger.info(f"Parsed {len(parsed_meetings)} upcoming meetings")
        return parsed_meetings


# Singleton instance
_meeting_parser = None


def get_meeting_parser() -> MeetingParserAgent:
    """Get singleton meeting parser instance.

    Returns:
        MeetingParserAgent instance
    """
    global _meeting_parser
    if _meeting_parser is None:
        _meeting_parser = MeetingParserAgent()
    return _meeting_parser
