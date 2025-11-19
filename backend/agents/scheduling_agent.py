"""
Scheduling Agent - Phase 4

Uses Gemini 2.0 Flash to intelligently schedule tasks based on:
- Task urgency (due dates, deadlines)
- Meeting context (prep needed for upcoming meetings)
- User preferences (Jef works best in afternoon)
- Calendar availability (free blocks)
- Task dependencies and priorities

This is the "brain" of Phase 4 - decides WHEN to work on each task.

Usage:
    agent = get_scheduling_agent()
    suggestions = await agent.schedule_tasks(
        tasks=active_tasks,
        user_id=1,
        db=db
    )

    # Returns list of ScheduledBlock objects with:
    # - task_id, start_time, end_time
    # - confidence_score (0-100)
    # - reasoning (why this time was chosen)
"""

import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from db.models import Task, CalendarEvent, ScheduledBlock, WorkPreferences
from agents.enrichment_engine import get_gemini_client
from services.availability_analyzer import get_availability_analyzer, FreeBlock
from services.calendar_sync import get_calendar_sync_service
from services.work_preferences import get_work_preferences
from services.user_profile import get_user_profile

logger = logging.getLogger(__name__)


@dataclass
class SchedulingSuggestion:
    """Scheduling suggestion for a single task."""
    task_id: str
    task_title: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    confidence_score: int  # 0-100
    reasoning: str
    quality_score: int  # Time block quality 0-100
    urgency_level: str  # critical, high, medium, low


class SchedulingAgent:
    """Agent for intelligent task scheduling using Gemini."""

    def __init__(self):
        """Initialize scheduling agent."""
        self.gemini = get_gemini_client()
        self.availability = get_availability_analyzer()
        self.calendar_service = get_calendar_sync_service()

    async def schedule_tasks(
        self,
        tasks: List[Task],
        user_id: int,
        db: AsyncSession,
        days_ahead: int = 7,
        max_suggestions: int = 10
    ) -> List[ScheduledBlock]:
        """Generate scheduling suggestions for tasks.

        Args:
            tasks: List of tasks to schedule
            user_id: User ID
            db: Database session
            days_ahead: Days to look ahead for scheduling
            max_suggestions: Maximum number of suggestions to generate

        Returns:
            List of ScheduledBlock objects (status='suggested')

        Raises:
            ValueError: If inputs invalid or scheduling fails
        """
        try:
            logger.info(f"Starting scheduling for {len(tasks)} tasks, user {user_id}")

            # 1. Get user preferences
            preferences = await get_work_preferences(db, user_id)
            user_profile = await get_user_profile(db, user_id)

            # 2. Get calendar events
            calendar_events = await self.calendar_service.get_events(
                user_id,
                db,
                days_ahead=days_ahead
            )
            logger.info(f"Found {len(calendar_events)} calendar events")

            # 3. Find free time blocks
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=days_ahead)

            free_blocks = self.availability.find_free_blocks(
                calendar_events,
                preferences,
                start_date,
                end_date,
                min_duration=preferences.min_task_block
            )
            logger.info(f"Found {len(free_blocks)} free blocks")

            if not free_blocks:
                logger.warning("No free blocks available for scheduling")
                return []

            # 4. Identify urgent tasks
            urgent_tasks = self._identify_urgent_tasks(tasks, calendar_events)
            logger.info(f"Identified {len(urgent_tasks)} urgent tasks")

            # 5. Filter tasks for scheduling (active, not already scheduled)
            schedulable_tasks = await self._filter_schedulable_tasks(tasks, db)
            logger.info(f"Filtered to {len(schedulable_tasks)} schedulable tasks")

            if not schedulable_tasks:
                logger.info("No schedulable tasks found")
                return []

            # 6. Use Gemini to generate suggestions
            suggestions = await self._generate_suggestions_with_gemini(
                schedulable_tasks,
                free_blocks,
                urgent_tasks,
                calendar_events,
                preferences,
                user_profile,
                max_suggestions
            )

            # 7. Create ScheduledBlock records
            scheduled_blocks = []
            for suggestion in suggestions[:max_suggestions]:
                # Check if task already has a suggested block
                existing = await self._get_existing_suggestion(suggestion.task_id, db)
                if existing:
                    logger.debug(f"Updating existing suggestion for task {suggestion.task_id}")
                    # Update existing suggestion
                    existing.start_time = suggestion.start_time
                    existing.end_time = suggestion.end_time
                    existing.duration_minutes = suggestion.duration_minutes
                    existing.confidence_score = suggestion.confidence_score
                    existing.reasoning = suggestion.reasoning
                    existing.quality_score = suggestion.quality_score
                    scheduled_blocks.append(existing)
                else:
                    # Create new suggestion
                    block = ScheduledBlock(
                        task_id=suggestion.task_id,
                        user_id=user_id,
                        start_time=suggestion.start_time,
                        end_time=suggestion.end_time,
                        duration_minutes=suggestion.duration_minutes,
                        status='suggested',
                        confidence_score=suggestion.confidence_score,
                        reasoning=suggestion.reasoning,
                        quality_score=suggestion.quality_score
                    )
                    db.add(block)
                    scheduled_blocks.append(block)

            await db.commit()

            logger.info(f"Generated {len(scheduled_blocks)} scheduling suggestions")
            return scheduled_blocks

        except Exception as e:
            logger.error(f"Scheduling failed: {e}")
            raise ValueError(f"Failed to generate scheduling suggestions: {e}")

    def _identify_urgent_tasks(
        self,
        tasks: List[Task],
        calendar_events: List[CalendarEvent]
    ) -> List[Task]:
        """Identify urgent tasks that need immediate scheduling.

        Args:
            tasks: All tasks
            calendar_events: Upcoming calendar events

        Returns:
            List of urgent tasks
        """
        urgent = []
        now = datetime.utcnow()

        for task in tasks:
            # Check 1: Task has due date within 48 hours
            if task.due_date:
                try:
                    if isinstance(task.due_date, str):
                        due = datetime.fromisoformat(task.due_date.replace('Z', '+00:00'))
                    else:
                        due = task.due_date

                    hours_until_due = (due - now).total_seconds() / 3600
                    if 0 < hours_until_due <= 48:
                        urgent.append(task)
                        logger.debug(f"Task '{task.title}' urgent: due in {hours_until_due:.1f} hours")
                        continue
                except Exception as e:
                    logger.warning(f"Failed to parse due date for task {task.id}: {e}")

            # Check 2: Task related to meeting happening soon
            for event in calendar_events:
                if task.id in (event.related_task_ids or []):
                    hours_until_meeting = (event.start_time - now).total_seconds() / 3600
                    if 0 < hours_until_meeting <= 24:
                        urgent.append(task)
                        logger.debug(f"Task '{task.title}' urgent: related to meeting in {hours_until_meeting:.1f} hours")
                        break

        return list(set(urgent))  # Remove duplicates

    async def _filter_schedulable_tasks(
        self,
        tasks: List[Task],
        db: AsyncSession
    ) -> List[Task]:
        """Filter tasks that can be scheduled (active, not already approved).

        Args:
            tasks: All tasks
            db: Database session

        Returns:
            List of schedulable tasks
        """
        schedulable = []

        for task in tasks:
            # Must be active (todo or doing)
            if task.status not in ['todo', 'doing']:
                continue

            # Check if already has approved time block
            query = select(ScheduledBlock).where(
                and_(
                    ScheduledBlock.task_id == task.id,
                    ScheduledBlock.status == 'approved'
                )
            )
            result = await db.execute(query)
            approved_block = result.scalar_one_or_none()

            if approved_block:
                logger.debug(f"Task '{task.title}' already has approved block, skipping")
                continue

            schedulable.append(task)

        return schedulable

    async def _get_existing_suggestion(
        self,
        task_id: str,
        db: AsyncSession
    ) -> Optional[ScheduledBlock]:
        """Get existing scheduling suggestion for task.

        Args:
            task_id: Task ID
            db: Database session

        Returns:
            Existing ScheduledBlock or None
        """
        query = select(ScheduledBlock).where(
            and_(
                ScheduledBlock.task_id == task_id,
                ScheduledBlock.status == 'suggested'
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _generate_suggestions_with_gemini(
        self,
        tasks: List[Task],
        free_blocks: List[FreeBlock],
        urgent_tasks: List[Task],
        calendar_events: List[CalendarEvent],
        preferences: WorkPreferences,
        user_profile: Any,
        max_suggestions: int
    ) -> List[SchedulingSuggestion]:
        """Use Gemini to generate scheduling suggestions.

        Args:
            tasks: Tasks to schedule
            free_blocks: Available time blocks
            urgent_tasks: Urgent tasks (subset of tasks)
            calendar_events: Upcoming calendar events
            preferences: User preferences
            user_profile: User profile
            max_suggestions: Max suggestions to generate

        Returns:
            List of SchedulingSuggestion objects
        """
        try:
            # Build prompt for Gemini
            prompt = self._build_scheduling_prompt(
                tasks,
                free_blocks,
                urgent_tasks,
                calendar_events,
                preferences,
                user_profile,
                max_suggestions
            )

            # Call Gemini
            logger.debug("Calling Gemini for scheduling suggestions...")
            response = await self.gemini.generate_content_async(prompt)

            # Parse response
            suggestions = self._parse_gemini_response(response.text, tasks, free_blocks)

            logger.info(f"Gemini generated {len(suggestions)} suggestions")
            return suggestions

        except Exception as e:
            logger.error(f"Gemini scheduling failed: {e}")
            # Fallback to simple rule-based scheduling
            logger.warning("Falling back to rule-based scheduling")
            return self._fallback_scheduling(tasks, free_blocks, urgent_tasks, max_suggestions)

    def _build_scheduling_prompt(
        self,
        tasks: List[Task],
        free_blocks: List[FreeBlock],
        urgent_tasks: List[Task],
        calendar_events: List[CalendarEvent],
        preferences: WorkPreferences,
        user_profile: Any,
        max_suggestions: int
    ) -> str:
        """Build Gemini prompt for scheduling.

        Args:
            tasks: Tasks to schedule
            free_blocks: Available time blocks
            urgent_tasks: Urgent tasks
            calendar_events: Calendar events
            preferences: User preferences
            user_profile: User profile
            max_suggestions: Max suggestions

        Returns:
            Prompt string
        """
        # Format tasks
        tasks_str = "\n".join([
            f"{i+1}. \"{task.title}\" (ID: {task.id})\n"
            f"   - Status: {task.status}\n"
            f"   - Project: {task.value_stream or 'None'}\n"
            f"   - Due: {task.due_date or 'No deadline'}\n"
            f"   - Description: {(task.description or 'None')[:100]}...\n"
            f"   - {'⚠️ URGENT' if task in urgent_tasks else 'Normal priority'}"
            for i, task in enumerate(tasks[:20])  # Limit to 20 tasks for token efficiency
        ])

        # Format free blocks (group by day for clarity)
        blocks_by_day = {}
        for block in free_blocks[:30]:  # Limit to 30 blocks
            day_key = block.start_time.strftime('%A, %B %d')
            if day_key not in blocks_by_day:
                blocks_by_day[day_key] = []
            blocks_by_day[day_key].append(block)

        blocks_str = ""
        for day, day_blocks in blocks_by_day.items():
            blocks_str += f"\n{day}:\n"
            for block in day_blocks:
                blocks_str += (
                    f"  - {block.start_time.strftime('%I:%M %p')} - {block.end_time.strftime('%I:%M %p')} "
                    f"({block.duration_minutes} min, quality: {block.quality_score}/100, {block.time_of_day})\n"
                )

        # Format upcoming meetings
        meetings_str = "\n".join([
            f"- {event.title} - {event.start_time.strftime('%A %I:%M %p')}"
            for event in calendar_events[:10]
            if event.is_meeting
        ])

        # Build prompt
        prompt = f"""You are Lotus, {user_profile.name}'s AI work scheduler. Schedule tasks optimally based on his work style and calendar.

**{user_profile.name}'s Profile:**
- Role: {user_profile.role} at {user_profile.company}
- Projects: {', '.join(user_profile.projects)}
- Work Style: {preferences.deep_work_time.replace('_', ' ')} is best for deep work
- Meeting Preference: {preferences.meeting_style.replace('_', ' ')}
- Minimum task block: {preferences.min_task_block} minutes

**Tasks to Schedule ({len(tasks)} total):**
{tasks_str}

**Available Free Blocks:**
{blocks_str}

**Upcoming Meetings (next 7 days):**
{meetings_str or 'None'}

**Scheduling Rules:**
1. **Urgent tasks first** - Tasks due soon or needed for meetings get priority
2. **Match duration** - Pick blocks that fit task complexity (simple=30min, complex=90-120min)
3. **Best time for task type** - Deep work in afternoon (Jef's preference), admin in morning
4. **Respect preferences** - Use high-quality blocks (score >70) for important tasks
5. **Leave buffer** - Don't schedule everything, leave some free time
6. **Realistic scheduling** - Only schedule what can actually be done

**Output Format:**
Return ONLY valid JSON array (no markdown, no explanation):
[
  {{
    "task_id": "task-123",
    "start_time": "2025-11-19T14:00:00",
    "end_time": "2025-11-19T16:00:00",
    "confidence": 85,
    "reasoning": "Due tomorrow, needs 2hrs, best afternoon block available"
  }}
]

**Important:**
- Schedule only top {max_suggestions} highest-priority tasks
- If no good time exists for a task, skip it (don't force bad scheduling)
- Consider meeting prep needs (tasks related to upcoming meetings)
- Use ISO 8601 format for times

JSON response:"""

        return prompt

    def _parse_gemini_response(
        self,
        response_text: str,
        tasks: List[Task],
        free_blocks: List[FreeBlock]
    ) -> List[SchedulingSuggestion]:
        """Parse Gemini response into SchedulingSuggestion objects.

        Args:
            response_text: Raw Gemini response
            tasks: Original tasks
            free_blocks: Available free blocks

        Returns:
            List of SchedulingSuggestion objects
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
            suggestions_data = json.loads(text)

            if not isinstance(suggestions_data, list):
                raise ValueError("Response must be a JSON array")

            suggestions = []
            task_dict = {t.id: t for t in tasks}

            for item in suggestions_data:
                try:
                    # Validate required fields
                    task_id = item.get('task_id')
                    if not task_id or task_id not in task_dict:
                        logger.warning(f"Invalid task_id: {task_id}")
                        continue

                    # Parse times
                    start_time = datetime.fromisoformat(item['start_time'].replace('Z', '+00:00'))
                    end_time = datetime.fromisoformat(item['end_time'].replace('Z', '+00:00'))
                    duration = int((end_time - start_time).total_seconds() / 60)

                    # Find matching free block for quality score
                    quality_score = self._find_block_quality(start_time, end_time, free_blocks)

                    # Determine urgency level
                    task = task_dict[task_id]
                    urgency = self._determine_urgency(task)

                    suggestion = SchedulingSuggestion(
                        task_id=task_id,
                        task_title=task.title,
                        start_time=start_time,
                        end_time=end_time,
                        duration_minutes=duration,
                        confidence_score=min(100, max(0, item.get('confidence', 70))),
                        reasoning=item.get('reasoning', 'Optimal time for this task'),
                        quality_score=quality_score,
                        urgency_level=urgency
                    )
                    suggestions.append(suggestion)

                except (KeyError, ValueError) as e:
                    logger.warning(f"Failed to parse suggestion item: {e}")
                    continue

            return suggestions

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.debug(f"Raw response: {response_text}")
            raise ValueError(f"Invalid JSON response from Gemini: {e}")

    def _find_block_quality(
        self,
        start_time: datetime,
        end_time: datetime,
        free_blocks: List[FreeBlock]
    ) -> int:
        """Find quality score for a time block.

        Args:
            start_time: Block start
            end_time: Block end
            free_blocks: Available free blocks

        Returns:
            Quality score 0-100
        """
        for block in free_blocks:
            # Check if times overlap
            if (start_time >= block.start_time and end_time <= block.end_time):
                return block.quality_score

        # Not in any free block (shouldn't happen, but handle gracefully)
        return 50  # Default medium quality

    def _determine_urgency(self, task: Task) -> str:
        """Determine urgency level for task.

        Args:
            task: Task to assess

        Returns:
            "critical", "high", "medium", or "low"
        """
        if not task.due_date:
            return "low"

        try:
            if isinstance(task.due_date, str):
                due = datetime.fromisoformat(task.due_date.replace('Z', '+00:00'))
            else:
                due = task.due_date

            hours_until = (due - datetime.utcnow()).total_seconds() / 3600

            if hours_until < 4:
                return "critical"
            elif hours_until < 24:
                return "high"
            elif hours_until < 72:
                return "medium"
            else:
                return "low"

        except Exception:
            return "low"

    def _fallback_scheduling(
        self,
        tasks: List[Task],
        free_blocks: List[FreeBlock],
        urgent_tasks: List[Task],
        max_suggestions: int
    ) -> List[SchedulingSuggestion]:
        """Fallback rule-based scheduling if Gemini fails.

        Args:
            tasks: Tasks to schedule
            free_blocks: Available blocks
            urgent_tasks: Urgent tasks
            max_suggestions: Max suggestions

        Returns:
            List of SchedulingSuggestion objects
        """
        logger.info("Using fallback rule-based scheduling")
        suggestions = []

        # Sort tasks: urgent first, then by due date
        sorted_tasks = sorted(
            tasks,
            key=lambda t: (
                t not in urgent_tasks,  # Urgent tasks first
                t.due_date if t.due_date else '9999-12-31',  # Then by due date
                t.created_at  # Then by creation time
            )
        )

        # Sort blocks: best quality first
        sorted_blocks = sorted(free_blocks, key=lambda b: b.quality_score, reverse=True)

        used_blocks = set()

        for task in sorted_tasks[:max_suggestions]:
            # Find best available block for this task
            # Estimate duration: 60 minutes default
            estimated_duration = 60

            for block in sorted_blocks:
                if block.start_time in used_blocks:
                    continue

                if block.duration_minutes >= estimated_duration:
                    # Use this block
                    end_time = block.start_time + timedelta(minutes=estimated_duration)

                    suggestion = SchedulingSuggestion(
                        task_id=task.id,
                        task_title=task.title,
                        start_time=block.start_time,
                        end_time=end_time,
                        duration_minutes=estimated_duration,
                        confidence_score=60,  # Lower confidence for fallback
                        reasoning=f"Best available {block.time_of_day} block (fallback scheduling)",
                        quality_score=block.quality_score,
                        urgency_level=self._determine_urgency(task)
                    )
                    suggestions.append(suggestion)
                    used_blocks.add(block.start_time)
                    break

            if len(suggestions) >= max_suggestions:
                break

        return suggestions


# Singleton instance
_scheduling_agent = None


def get_scheduling_agent() -> SchedulingAgent:
    """Get singleton scheduling agent instance.

    Returns:
        SchedulingAgent instance
    """
    global _scheduling_agent
    if _scheduling_agent is None:
        _scheduling_agent = SchedulingAgent()
    return _scheduling_agent
