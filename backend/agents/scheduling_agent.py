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
import re
import traceback
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from db.models import Task, CalendarEvent, ScheduledBlock, WorkPreferences
from services.gemini_client import get_gemini_client
from services.availability_analyzer import get_availability_analyzer, FreeBlock
from services.calendar_sync import get_calendar_sync_service
from services.work_preferences import get_work_preferences
from services.user_profile import get_user_profile

logger = logging.getLogger(__name__)


class TaskSchedulingSuggestion(BaseModel):
    """Structured scheduling suggestion from AI."""
    task_id: str = Field(..., description="ID of the task to schedule")
    start_time: str = Field(..., description="ISO 8601 start time (e.g., '2025-11-19T14:00:00Z')")
    end_time: str = Field(..., description="ISO 8601 end time (e.g., '2025-11-19T16:00:00Z')")
    confidence: int = Field(..., ge=0, le=100, description="Confidence score 0-100")
    reasoning: str = Field(..., description="Reasoning (will be generated from actual times)")
    estimated_duration_minutes: int = Field(..., ge=15, description="Estimated duration in minutes")


class SchedulingResponse(BaseModel):
    """Structured response from AI scheduling."""
    suggestions: List[TaskSchedulingSuggestion] = Field(..., description="List of scheduling suggestions")
    reasoning_summary: str = Field(..., description="Overall scheduling strategy explanation")


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
    """Agent for intelligent task scheduling using Gemini 2.0 Flash.
    
    This agent uses AI to intelligently schedule tasks based on:
    - Task urgency (due dates, deadlines)
    - Meeting context (prep needed for upcoming meetings)
    - User preferences (work hours, deep work times)
    - Calendar availability (free blocks)
    - Task dependencies and priorities
    
    The agent generates scheduling suggestions that are:
    - Varied in time and duration (not uniform)
    - Respectful of work hours and preferences
    - Avoids weekends and out-of-office days
    - Considers task complexity for duration estimation
    """

    def __init__(self):
        """Initialize scheduling agent with required services."""
        logger.info("Initializing SchedulingAgent...")
        self.gemini = get_gemini_client()
        logger.info(f"Gemini client initialized: available={getattr(self.gemini, 'available', 'UNKNOWN')}")
        self.availability = get_availability_analyzer()
        self.calendar_service = get_calendar_sync_service()
        logger.info("SchedulingAgent initialization complete")

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
            logger.info("=" * 80)
            logger.info("SCHEDULING AGENT: Starting task scheduling")
            logger.info("=" * 80)
            logger.info(f"Input: {len(tasks)} tasks, user {user_id}, {days_ahead} days ahead, max {max_suggestions} suggestions")
            logger.info(f"Gemini client status: available={getattr(self.gemini, 'available', 'UNKNOWN')}")

            # 1. Get user preferences
            preferences = await get_work_preferences(db, user_id)
            user_profile = await get_user_profile(db, user_id)

            # 2. Get calendar events
            calendar_events = await self.calendar_service.get_events(
                user_id,
                db,
                days_ahead=days_ahead
            )
            logger.info(f"Found {len(calendar_events)} calendar events for user {user_id}")

            # 3. Find free time blocks
            start_date = datetime.now(timezone.utc)
            end_date = start_date + timedelta(days=days_ahead)

            free_blocks = self.availability.find_free_blocks(
                calendar_events,
                preferences,
                start_date,
                end_date,
                min_duration=preferences.min_task_block
            )
            logger.info(f"Found {len(free_blocks)} free blocks (min {preferences.min_task_block}min)")

            # Note: We continue even if no free blocks - let AI analyze and provide reasoning
            if not free_blocks:
                logger.warning(
                    f"No free blocks found by availability analyzer. "
                    f"Calendar events: {len(calendar_events)}, "
                    f"Work hours: {preferences.no_meetings_before}-{preferences.no_meetings_after}, "
                    f"Days ahead: {days_ahead}. "
                    f"Proceeding to AI analysis anyway - AI may find creative solutions."
                )

            # 4. Identify urgent tasks
            urgent_tasks = self._identify_urgent_tasks(tasks, calendar_events)
            logger.info(f"Identified {len(urgent_tasks)} urgent tasks")

            # 5. Filter tasks for scheduling (active, not already scheduled)
            schedulable_tasks = await self._filter_schedulable_tasks(tasks, db)
            logger.info(f"Filtered to {len(schedulable_tasks)} schedulable tasks")

            if not schedulable_tasks:
                logger.info("No schedulable tasks found")
                return []

            # 6. Use Gemini/Qwen to generate suggestions (ALWAYS call AI, even with no free blocks)
            logger.info("Calling AI (Gemini/Qwen) for intelligent scheduling analysis...")
            
            # Diagnostic: Group events by day to show what AI will see
            if calendar_events:
                events_by_day_diag = defaultdict(list)
                for event in calendar_events:
                    day_key = event.start_time.date() if not event.all_day else event.start_time.date()
                    events_by_day_diag[day_key].append(event)
                
                logger.info("Calendar events by day (what AI will analyze):")
                for day in sorted(events_by_day_diag.keys()):
                    day_events = events_by_day_diag[day]
                    day_name = day.strftime('%A, %B %d')
                    out_of_office = any(
                        any(kw in (e.title or "").lower() for kw in ["out of office", "away", "vacation", "off"])
                        for e in day_events if e.all_day
                    )
                    oof_marker = " [OUT OF OFFICE]" if out_of_office else ""
                    logger.info(f"  {day_name}{oof_marker}: {len(day_events)} events")
                    for event in day_events[:3]:  # Show first 3
                        if event.all_day:
                            logger.info(f"    - {event.title} (ALL DAY)")
                        else:
                            logger.info(f"    - {event.title} ({event.start_time.strftime('%I:%M %p')} - {event.end_time.strftime('%I:%M %p')})")
            
            suggestions = await self._generate_suggestions_with_gemini(
                schedulable_tasks,
                free_blocks,  # May be empty - AI can handle this
                urgent_tasks,
                calendar_events,
                preferences,
                user_profile,
                max_suggestions
            )
            logger.info(f"✓ AI returned {len(suggestions)} suggestions")
            
            if len(suggestions) == 0:
                logger.error("❌ CRITICAL: AI returned ZERO suggestions!")
                logger.error("   This could mean:")
                logger.error("   1. AI couldn't find any available time slots")
                logger.error("   2. AI response parsing failed")
                logger.error("   3. AI didn't generate suggestions in expected format")
                logger.error("   Check logs above for AI response details")
            else:
                logger.info(f"   Sample suggestions:")
                for i, sug in enumerate(suggestions[:3]):
                    logger.info(f"     {i+1}. Task '{sug.task_title}' at {sug.start_time.strftime('%A %I:%M %p')} ({sug.duration_minutes}min, confidence={sug.confidence_score})")

            # 7. Create ScheduledBlock records
            scheduled_blocks = []
            logger.info(f"Creating {len(suggestions[:max_suggestions])} ScheduledBlock records...")
            for idx, suggestion in enumerate(suggestions[:max_suggestions]):
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

            logger.info(f"✓ Successfully created {len(scheduled_blocks)} ScheduledBlock records in database")
            if len(scheduled_blocks) == 0:
                logger.error("❌ CRITICAL: No ScheduledBlock records were created!")
                logger.error(f"   Input: {len(suggestions)} suggestions from AI")
                logger.error(f"   Max suggestions: {max_suggestions}")
            
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
        now = datetime.now(timezone.utc)

        for task in tasks:
            # Check 1: Task has due date within 48 hours
            if task.due_date:
                try:
                    if isinstance(task.due_date, str):
                        due = self._parse_iso_datetime(task.due_date)
                    else:
                        due = self._normalize_datetime(task.due_date)

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
                    # Ensure event.start_time is timezone-aware
                    event_start = self._normalize_datetime(event.start_time)
                    
                    hours_until_meeting = (event_start - now).total_seconds() / 3600
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

            # Allow rescheduling - don't skip tasks with approved blocks
            # User might want to reschedule even if already approved
            schedulable.append(task)

        return schedulable

    async def _get_existing_suggestion(
        self,
        task_id: str,
        db: AsyncSession
    ) -> Optional[ScheduledBlock]:
        """Get existing scheduling suggestion for task.
        
        If multiple suggestions exist, returns the most recent one.
        Also cleans up old duplicate suggestions.

        Args:
            task_id: Task ID
            db: Database session

        Returns:
            Existing ScheduledBlock or None
        """
        from sqlalchemy import desc
        
        # Get all suggested blocks for this task, ordered by most recent first (by ID)
        query = select(ScheduledBlock).where(
            and_(
                ScheduledBlock.task_id == task_id,
                ScheduledBlock.status == 'suggested'
            )
        ).order_by(desc(ScheduledBlock.id))  # Most recent ID first (auto-increment)
        
        result = await db.execute(query)
        all_suggestions = result.scalars().all()
        
        if not all_suggestions:
            return None
        
        # If multiple exist, delete the older ones and keep only the most recent
        if len(all_suggestions) > 1:
            logger.warning(f"Found {len(all_suggestions)} suggested blocks for task {task_id}, cleaning up duplicates")
            # Keep the first (most recent) and delete the rest
            for old_suggestion in all_suggestions[1:]:
                await db.delete(old_suggestion)
            await db.flush()  # Flush deletes before returning
        
        return all_suggestions[0]  # Return the most recent one

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
        """Use Gemini to generate intelligent, agentic scheduling suggestions.

        Args:
            tasks: Tasks to schedule
            free_blocks: Available time blocks
            urgent_tasks: Urgent tasks (subset of tasks)
            calendar_events: Upcoming calendar events
            preferences: User preferences
            user_profile: User profile
            max_suggestions: Max suggestions to generate

        Returns:
            List of SchedulingSuggestion objects with varied times and durations
        """
        try:
            # Build comprehensive prompt for Gemini
            logger.info(f"Building AI scheduling prompt for {len(tasks)} tasks, {len(free_blocks)} free blocks")
            prompt = self._build_scheduling_prompt(
                tasks,
                free_blocks,
                urgent_tasks,
                calendar_events,
                preferences,
                user_profile,
                max_suggestions
            )
            logger.debug(f"Prompt built: {len(prompt)} chars")
            
            try:
                # Use structured output for better reliability
                logger.info("Calling AI for structured scheduling suggestions...")
                structured_response = await self.gemini.generate_structured(
                    prompt=prompt,
                    schema=SchedulingResponse,
                    temperature=0.4,
                    fallback_to_qwen=True
                )
                logger.info(f"AI returned {len(structured_response.suggestions)} suggestions")
                if structured_response.reasoning_summary:
                    logger.debug(f"AI reasoning: {structured_response.reasoning_summary}")
                
                # Convert structured response to SchedulingSuggestion objects
                suggestions = []
                task_dict = {t.id: t for t in tasks}
                
                logger.debug(f"Parsing {len(structured_response.suggestions)} AI suggestions...")
                for idx, item in enumerate(structured_response.suggestions):
                    try:
                        
                        # Parse and validate times
                        start_time = self._parse_iso_datetime(item.start_time)
                        end_time = self._parse_iso_datetime(item.end_time)
                        
                        # Reject weekend scheduling
                        if not self._validate_weekday(start_time):
                            logger.warning(f"      ⚠ Rejecting weekend suggestion: {start_time.strftime('%A')}")
                            continue
                        
                        duration = item.estimated_duration_minutes
                        
                        # Get task
                        if item.task_id not in task_dict:
                            logger.warning(f"Task {item.task_id} not found - skipping")
                            continue
                        
                        task = task_dict[item.task_id]
                        urgency = self._determine_urgency(task)
                        quality_score = self._find_block_quality(start_time, end_time, free_blocks)
                        reasoning = self._generate_reasoning(start_time, end_time, duration, urgency, quality_score)
                        
                        suggestion = SchedulingSuggestion(
                            task_id=item.task_id,
                            task_title=task.title,
                            start_time=start_time,
                            end_time=end_time,
                            duration_minutes=duration,
                            confidence_score=item.confidence,
                            reasoning=reasoning,
                            quality_score=quality_score,
                            urgency_level=urgency
                        )
                        suggestions.append(suggestion)
                        logger.debug(f"Added suggestion: '{task.title}' at {start_time.strftime('%A %I:%M %p')} ({duration}min)")
                        
                    except (KeyError, ValueError, Exception) as parse_error:
                        logger.error(f"Failed to parse suggestion {idx+1}: {parse_error}", exc_info=True)
                        logger.debug(f"Item data: task_id={getattr(item, 'task_id', 'MISSING')}, start_time={getattr(item, 'start_time', 'MISSING')}")
                        continue
                
                logger.info(f"Successfully parsed {len(suggestions)}/{len(structured_response.suggestions)} suggestions")
                if len(suggestions) == 0 and len(structured_response.suggestions) > 0:
                    logger.error(f"CRITICAL: AI returned {len(structured_response.suggestions)} suggestions but ALL failed to parse!")
                elif len(suggestions) < len(structured_response.suggestions):
                    logger.warning(f"Only {len(suggestions)}/{len(structured_response.suggestions)} suggestions parsed successfully")
                
                return suggestions
                
            except Exception as structured_error:
                logger.error(f"Structured output failed: {structured_error}", exc_info=True)
                logger.info("Falling back to text generation...")
                
                try:
                    # Fallback to text generation
                    response_text = await self.gemini.generate(
                        prompt=prompt,
                        temperature=0.4,
                        max_tokens=2048,
                        fallback_to_qwen=True
                    )
                    logger.info(f"Text generation successful ({len(response_text)} chars)")
                    
                    # Parse text response
                    suggestions = self._parse_gemini_response(response_text, tasks, free_blocks)
                    logger.info(f"Parsed {len(suggestions)} suggestions from text response")
                    return suggestions
                except Exception as text_error:
                    logger.error(f"Text generation also failed: {text_error}", exc_info=True)
                    raise  # Re-raise to trigger fallback scheduling

        except Exception as e:
            logger.error(f"AI scheduling failed: {e}", exc_info=True)
            # Fallback to intelligent rule-based scheduling
            logger.warning("   → Falling back to intelligent rule-based scheduling (AI unavailable)")
            return self._intelligent_fallback_scheduling(tasks, free_blocks, urgent_tasks, max_suggestions)

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
        # Format tasks with concise context (limit to reduce tokens)
        tasks_str = "\n".join([
            f"{i+1}. \"{task.title}\" (ID: {task.id})\n"
            f"   - Status: {task.status}, Project: {task.value_stream or 'None'}\n"
            f"   - Due: {task.due_date or 'No deadline'}\n"
            f"   - Desc: {(task.description or '')[:80]}{'...' if task.description and len(task.description) > 80 else ''}\n"
            f"   - Priority: {'⚠️ URGENT' if task in urgent_tasks else 'Normal'}"
            for i, task in enumerate(tasks[:10])  # Limit to 10 tasks to reduce tokens
        ])

        # Format free blocks (group by day for clarity)
        if free_blocks:
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
        else:
            blocks_str = "\n⚠️ NO FREE BLOCKS FOUND by availability analyzer.\n"
            blocks_str += "\nCRITICAL: The availability analyzer found no free blocks, but you MUST analyze the calendar events below to find scheduling opportunities.\n"
            blocks_str += "\nLook carefully for:\n"
            blocks_str += "1. Days with FEWER events (like Thursday in the example below)\n"
            blocks_str += "2. Gaps between meetings on any day\n"
            blocks_str += "3. Early morning (before 9am) or late evening (after 6pm) slots\n"
            blocks_str += "4. Days that are NOT marked 'out of office' or 'away'\n"
            blocks_str += "5. Opportunities to schedule during 'working hours' blocks (9am-6pm blocks that are just availability markers)\n"
            blocks_str += "\nIMPORTANT: If you see a day with only a few events or large gaps, that day HAS available time slots!\n"
            blocks_str += "Generate suggestions for those days even if the analyzer didn't find them.\n"

        # Format upcoming meetings (limit to reduce tokens)
        meetings_str = "\n".join([
            f"- {event.title} - {event.start_time.strftime('%A %I:%M %p')}"
            for event in calendar_events[:5]  # Limit to 5 meetings
            if event.is_meeting
        ])
        
        # Group events by day (concise format to reduce tokens)
        events_by_day = {}
        for event in calendar_events:
            day_key = event.start_time.date()
            if day_key not in events_by_day:
                events_by_day[day_key] = []
            events_by_day[day_key].append(event)
        
        # Format events by day (concise - only show key info)
        all_events_str = ""
        for day in sorted(events_by_day.keys())[:7]:  # Only next 7 days
            day_events = events_by_day[day]
            day_name = day.strftime('%A, %B %d')
            
            # Check if out of office
            oof = any(
                any(kw in (e.title or "").lower() for kw in ["out of office", "away", "vacation", "off"])
                for e in day_events if e.all_day
            )
            oof_marker = " [OUT OF OFFICE]" if oof else ""
            
            all_events_str += f"\n{day_name}{oof_marker} ({len(day_events)} events):\n"
            
            # Show only first 5 events per day to save tokens
            for event in sorted(day_events, key=lambda e: e.start_time if not e.all_day else e.start_time)[:5]:
                if event.all_day:
                    all_events_str += f"  - {event.title} (ALL DAY)\n"
                else:
                    start_str = event.start_time.strftime('%I:%M %p')
                    end_str = event.end_time.strftime('%I:%M %p')
                    all_events_str += f"  - {event.title} ({start_str}-{end_str})\n"

        # Build concise prompt (reduced from 9500+ to ~3000 chars)
        prompt = f"""You are Lotus, {user_profile.name}'s AI scheduler. Schedule tasks intelligently.

**Profile:** {preferences.deep_work_time.replace('_', ' ')} best for deep work. Work hours: {preferences.no_meetings_before}-{preferences.no_meetings_after}.

**Tasks ({len(tasks)}):**
{tasks_str}

**Free Blocks:**
{blocks_str}

**Calendar Events:**
{all_events_str or 'None'}

**Rules:**
1. ONLY schedule on WEEKDAYS (Monday-Friday) - NEVER on weekends (Saturday/Sunday)
2. Find days NOT "OUT OF OFFICE" - these have available slots
3. Match task type: Deep work → Afternoon (2-6pm), Admin → Morning (9am-12pm)
4. Estimate duration: Simple=30min, Medium=60min, Complex=90-120min
5. Vary times - don't schedule all tasks at same time
6. If no free blocks, analyze calendar events to find gaps on WEEKDAYS only

**Output:** Return JSON with "suggestions" array. Each suggestion: task_id, start_time (ISO format, WEEKDAY only), end_time (ISO), confidence (0-100), reasoning (brief explanation, will be auto-corrected), estimated_duration_minutes. MUST generate at least 1 suggestion."""

        return prompt

    def _parse_gemini_response(
        self,
        response_text: str,
        tasks: List[Task],
        free_blocks: List[FreeBlock]
    ) -> List[SchedulingSuggestion]:
        """Parse Gemini text response into SchedulingSuggestion objects.
        
        Handles both structured JSON format and text responses with embedded JSON.
        Validates weekend scheduling and ensures timezone-aware datetimes.

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

            # Parse JSON - handle both old format (array) and new format (object with suggestions)
            response_data = json.loads(text)
            
            # Handle new structured format
            if isinstance(response_data, dict) and 'suggestions' in response_data:
                suggestions_data = response_data['suggestions']
                if 'reasoning_summary' in response_data:
                    logger.info(f"AI scheduling strategy: {response_data['reasoning_summary']}")
            elif isinstance(response_data, list):
                # Old format - direct array
                suggestions_data = response_data
            else:
                raise ValueError("Response must be a JSON array or object with 'suggestions' field")

            if not isinstance(suggestions_data, list):
                raise ValueError("Suggestions must be a JSON array")

            suggestions = []
            task_dict = {t.id: t for t in tasks}

            for item in suggestions_data:
                try:
                    # Validate required fields
                    task_id = item.get('task_id')
                    if not task_id or task_id not in task_dict:
                        logger.warning(f"Invalid task_id: {task_id}")
                        continue

                    # Parse and validate times
                    start_time = self._parse_iso_datetime(item['start_time'])
                    end_time = self._parse_iso_datetime(item['end_time'])
                    
                    # Reject weekend scheduling
                    if not self._validate_weekday(start_time):
                        logger.warning(f"Rejecting weekend suggestion: {start_time.strftime('%A')}")
                        continue
                    
                    # Use estimated_duration_minutes if provided, otherwise calculate from times
                    if 'estimated_duration_minutes' in item:
                        duration = item['estimated_duration_minutes']
                        end_time = start_time + timedelta(minutes=duration)
                    else:
                        duration = int((end_time - start_time).total_seconds() / 60)

                    # Get task and calculate metrics
                    task = task_dict[task_id]
                    urgency = self._determine_urgency(task)
                    quality_score = self._find_block_quality(start_time, end_time, free_blocks)
                    reasoning = self._generate_reasoning(start_time, end_time, duration, urgency, quality_score)

                    suggestion = SchedulingSuggestion(
                        task_id=task_id,
                        task_title=task.title,
                        start_time=start_time,
                        end_time=end_time,
                        duration_minutes=duration,
                        confidence_score=min(100, max(0, item.get('confidence', 70))),
                        reasoning=reasoning,
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
            logger.error(f"Raw response (first 500 chars): {response_text[:500]}")
            logger.error(f"Full response length: {len(response_text)} chars")
            
            # Try to extract JSON array from response if it's embedded in text
            json_match = re.search(r'\[[\s\S]*?\]', response_text)
            if json_match:
                try:
                    extracted_json = json_match.group(0)
                    suggestions_data = json.loads(extracted_json)
                    logger.info("Successfully extracted JSON array from response text")
                    
                    if not isinstance(suggestions_data, list):
                        raise ValueError("Response must be a JSON array")
                    
                    # Continue with normal parsing...
                    # Handle both old format (array) and new format (object with suggestions)
                    if isinstance(suggestions_data, dict) and 'suggestions' in suggestions_data:
                        suggestions_data = suggestions_data['suggestions']
                    
                    task_dict = {t.id: t for t in tasks}
                    suggestions = []
                    for item in suggestions_data:
                        try:
                            task_id = item.get('task_id')
                            if not task_id or task_id not in task_dict:
                                continue
                            # Parse and validate times
                            start_time = self._parse_iso_datetime(item['start_time'])
                            end_time = self._parse_iso_datetime(item['end_time'])
                            
                            # Reject weekend scheduling
                            if not self._validate_weekday(start_time):
                                logger.warning(f"Rejecting weekend suggestion: {start_time.strftime('%A')}")
                                continue
                            
                            # Use estimated_duration_minutes if provided
                            if 'estimated_duration_minutes' in item:
                                duration = item['estimated_duration_minutes']
                                end_time = start_time + timedelta(minutes=duration)
                            else:
                                duration = int((end_time - start_time).total_seconds() / 60)
                            
                            # Get task and calculate metrics
                            task = task_dict[task_id]
                            urgency = self._determine_urgency(task)
                            quality_score = self._find_block_quality(start_time, end_time, free_blocks)
                            reasoning = self._generate_reasoning(start_time, end_time, duration, urgency, quality_score)
                            
                            suggestion = SchedulingSuggestion(
                                task_id=task_id,
                                task_title=task.title,
                                start_time=start_time,
                                end_time=end_time,
                                duration_minutes=duration,
                                confidence_score=min(100, max(0, item.get('confidence', 70))),
                                reasoning=reasoning,
                                quality_score=quality_score,
                                urgency_level=urgency
                            )
                            suggestions.append(suggestion)
                        except (KeyError, ValueError) as parse_error:
                            logger.warning(f"Failed to parse suggestion item: {parse_error}")
                            continue
                    return suggestions
                except Exception as extract_error:
                    logger.error(f"Failed to extract JSON from response: {extract_error}")
            
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

    def _normalize_datetime(self, dt: datetime) -> datetime:
        """Ensure datetime is timezone-aware (UTC).
        
        Args:
            dt: Datetime (may be naive or timezone-aware)
            
        Returns:
            Timezone-aware datetime in UTC
        """
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    
    def _generate_reasoning(
        self,
        start_time: datetime,
        end_time: datetime,
        duration_minutes: int,
        urgency_level: str,
        quality_score: int
    ) -> str:
        """Generate accurate reasoning text from actual scheduled times.
        
        Args:
            start_time: Scheduled start time
            end_time: Scheduled end time
            duration_minutes: Task duration
            urgency_level: Task urgency (critical, high, medium, low)
            quality_score: Block quality score (0-100)
            
        Returns:
            Formatted reasoning string
        """
        day_name = start_time.strftime('%A, %B %d')
        start_time_str = start_time.strftime('%I:%M %p').lstrip('0')
        end_time_str = end_time.strftime('%I:%M %p').lstrip('0')
        
        # Determine time of day
        hour = start_time.hour
        if 6 <= hour < 12:
            time_of_day = "morning"
        elif 12 <= hour < 17:
            time_of_day = "afternoon"
        else:
            time_of_day = "evening"
        
        urgency_text = 'Urgent' if urgency_level in ['critical', 'high'] else 'Normal priority'
        
        return (
            f"Scheduled for {start_time_str} to {end_time_str} on {day_name}. "
            f"{urgency_text} task estimated at {duration_minutes} minutes. "
            f"{time_of_day.capitalize()} slot with quality score {quality_score}/100."
        )
    
    def _parse_iso_datetime(self, time_str: str) -> datetime:
        """Parse ISO datetime string and ensure timezone-aware.
        
        Args:
            time_str: ISO datetime string (may have 'Z' suffix)
            
        Returns:
            Timezone-aware datetime in UTC
        """
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        return self._normalize_datetime(dt)
    
    def _validate_weekday(self, dt: datetime) -> bool:
        """Check if datetime is on a weekday (Monday-Friday).
        
        Args:
            dt: Datetime to check
            
        Returns:
            True if weekday, False if weekend
        """
        return dt.weekday() < 5  # Monday=0, Friday=4, Saturday=5, Sunday=6

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
            now = datetime.now(timezone.utc)
            
            if isinstance(task.due_date, str):
                due = self._parse_iso_datetime(task.due_date)
            else:
                due = self._normalize_datetime(task.due_date)

            hours_until = (due - now).total_seconds() / 3600

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

    def _intelligent_fallback_scheduling(
        self,
        tasks: List[Task],
        free_blocks: List[FreeBlock],
        urgent_tasks: List[Task],
        max_suggestions: int
    ) -> List[SchedulingSuggestion]:
        """Intelligent fallback scheduling when AI is unavailable.
        
        This fallback provides agentic scheduling by:
        - Analyzing task complexity to estimate varied durations (30/60/90/120 min)
        - Matching task types to preferred times (deep work → afternoon, admin → morning)
        - Spreading tasks across different days and times
        - Prioritizing urgent tasks and high-quality blocks
        - Tracking used blocks to avoid duplicates

        Args:
            tasks: Tasks to schedule
            free_blocks: Available time blocks from availability analyzer
            urgent_tasks: Subset of tasks marked as urgent
            max_suggestions: Maximum number of suggestions to generate

        Returns:
            List of SchedulingSuggestion objects with varied times and durations
        """
        logger.info("Using intelligent fallback scheduling with complexity analysis")
        suggestions = []

        # Sort tasks: urgent first, then by due date
        def get_due_date_for_sort(task):
            if not task.due_date:
                return datetime.max.replace(tzinfo=timezone.utc)
            
            if isinstance(task.due_date, str):
                try:
                    return self._parse_iso_datetime(task.due_date)
                except:
                    return datetime.max.replace(tzinfo=timezone.utc)
            else:
                return self._normalize_datetime(task.due_date)
        
        sorted_tasks = sorted(
            tasks,
            key=lambda t: (
                t not in urgent_tasks,  # Urgent tasks first
                get_due_date_for_sort(t),  # Then by due date
                t.created_at  # Then by creation time
            )
        )

        # Analyze task complexity and estimate duration
        def estimate_task_duration(task: Task) -> int:
            """Estimate task duration in minutes based on complexity analysis."""
            title_lower = (task.title or "").lower()
            desc_lower = (task.description or "").lower() if task.description else ""
            combined_text = f"{title_lower} {desc_lower}"
            
            # Complexity indicators
            complex_keywords = [
                "develop", "build", "create", "implement", "design", "architecture",
                "refactor", "migrate", "integrate", "dashboard", "feature", "system"
            ]
            simple_keywords = [
                "email", "reply", "update", "review", "check", "quick", "follow up",
                "confirm", "approve", "acknowledge"
            ]
            medium_keywords = [
                "analyze", "review", "plan", "document", "test", "verify", "prepare"
            ]
            
            # Count complexity indicators
            complex_count = sum(1 for kw in complex_keywords if kw in combined_text)
            simple_count = sum(1 for kw in simple_keywords if kw in combined_text)
            medium_count = sum(1 for kw in medium_keywords if kw in combined_text)
            
            # Estimate based on indicators
            if complex_count >= 2 or len(combined_text) > 200:
                # Very complex task
                return 120  # 2 hours
            elif complex_count >= 1 or (medium_count >= 2 and len(combined_text) > 100):
                # Complex task
                return 90  # 1.5 hours
            elif medium_count >= 1 or len(combined_text) > 50:
                # Medium task
                return 60  # 1 hour
            elif simple_count >= 1 or len(combined_text) < 30:
                # Simple task
                return 30  # 30 minutes
            else:
                # Default medium
                return 45  # 45 minutes
        
        # Determine best time of day for task type
        def get_preferred_time_of_day(task: Task) -> str:
            """Determine preferred time of day based on task type."""
            title_lower = (task.title or "").lower()
            desc_lower = (task.description or "").lower() if task.description else ""
            combined = f"{title_lower} {desc_lower}"
            
            # Deep work tasks (coding, design, complex work) → afternoon
            deep_work_keywords = [
                "develop", "code", "build", "create", "design", "architecture",
                "implement", "refactor", "dashboard", "feature", "system"
            ]
            if any(kw in combined for kw in deep_work_keywords):
                return "afternoon"
            
            # Admin tasks → morning
            admin_keywords = [
                "email", "reply", "update", "review", "check", "follow up",
                "confirm", "approve", "acknowledge", "meeting prep"
            ]
            if any(kw in combined for kw in admin_keywords):
                return "morning"
            
            # Default: afternoon (Jef's preference)
            return "afternoon"
        
        # Handle case where no free blocks found
        if not free_blocks:
            logger.warning("No free blocks available for intelligent fallback scheduling")
            # Return empty suggestions - let the API route provide helpful message
            return []
        
        # Group blocks by day and time of day for intelligent selection
        blocks_by_day = {}
        for block in free_blocks:
            day_key = block.start_time.strftime('%Y-%m-%d')
            if day_key not in blocks_by_day:
                blocks_by_day[day_key] = []
            blocks_by_day[day_key].append(block)
        
        # Sort days (earlier first)
        sorted_days = sorted(blocks_by_day.keys())
        
        # Track used blocks to avoid duplicates
        used_blocks = set()
        
        # Process tasks intelligently
        for task in sorted_tasks[:max_suggestions]:
            if len(suggestions) >= max_suggestions:
                break
            
            # Estimate duration
            estimated_duration = estimate_task_duration(task)
            preferred_time = get_preferred_time_of_day(task)
            urgency = self._determine_urgency(task)
            
            logger.debug(
                f"Task '{task.title}': duration={estimated_duration}min, "
                f"preferred={preferred_time}, urgency={urgency}"
            )
            
            # Find best matching block
            best_block = None
            best_score = -1
            
            # Try to find blocks matching preferred time
            for day_key in sorted_days:
                day_blocks = blocks_by_day[day_key]
                
                for block in day_blocks:
                    # Skip if already used
                    block_id = f"{block.start_time.isoformat()}-{block.end_time.isoformat()}"
                    if block_id in used_blocks:
                        continue
                    
                    # Check if block fits duration (with some flexibility)
                    block_duration = block.duration_minutes
                    if block_duration < estimated_duration - 15:  # Need at least estimated - 15min
                        continue
                    
                    # Determine time of day for this block
                    hour = block.start_time.hour
                    if 6 <= hour < 12:
                        block_time_of_day = "morning"
                    elif 12 <= hour < 17:
                        block_time_of_day = "afternoon"
                    else:
                        block_time_of_day = "evening"
                    
                    # Score this block
                    score = block.quality_score
                    
                    # Boost score if time matches preference
                    if block_time_of_day == preferred_time:
                        score += 20
                    
                    # Boost score for urgent tasks (sooner is better)
                    if urgency in ["critical", "high"]:
                        days_away = (block.start_time.date() - datetime.now(timezone.utc).date()).days
                        if days_away <= 2:
                            score += 15
                    
                    # Boost score if task is urgent and block is high quality
                    if task in urgent_tasks and block.quality_score > 70:
                        score += 10
                    
                    # Prefer blocks that fit duration well (not too much extra time)
                    duration_fit = 100 - abs(block_duration - estimated_duration)
                    score += duration_fit // 10
                    
                    if score > best_score:
                        best_score = score
                        best_block = block
            
            if best_block:
                # Calculate actual end time (use estimated duration, not full block)
                start_time = best_block.start_time
                end_time = start_time + timedelta(minutes=estimated_duration)
                
                # Don't exceed block end time
                if end_time > best_block.end_time:
                    end_time = best_block.end_time
                    estimated_duration = int((end_time - start_time).total_seconds() / 60)
                
                # Mark block as used
                block_id = f"{best_block.start_time.isoformat()}-{best_block.end_time.isoformat()}"
                used_blocks.add(block_id)
                
                # Generate reasoning using helper method
                urgency = self._determine_urgency(task)
                reasoning = self._generate_reasoning(
                    start_time, end_time, estimated_duration, urgency, best_block.quality_score
                )
                
                suggestion = SchedulingSuggestion(
                    task_id=task.id,
                    task_title=task.title,
                    start_time=start_time,
                    end_time=end_time,
                    duration_minutes=estimated_duration,
                    confidence_score=min(100, best_score),
                    reasoning=reasoning,
                    quality_score=best_block.quality_score,
                    urgency_level=urgency
                )
                suggestions.append(suggestion)
                
                time_str = start_time.strftime('%A, %B %d at %I:%M %p')
                logger.info(
                    f"Scheduled '{task.title}' for {time_str} "
                    f"({estimated_duration}min, score={best_score})"
                )
            else:
                logger.warning(f"No suitable block found for task '{task.title}'")
        
        logger.info(f"Intelligent fallback generated {len(suggestions)} varied suggestions")
        return suggestions

    def _fallback_scheduling(
        self,
        tasks: List[Task],
        free_blocks: List[FreeBlock],
        urgent_tasks: List[Task],
        max_suggestions: int
    ) -> List[SchedulingSuggestion]:
        """Legacy fallback - redirects to intelligent fallback."""
        return self._intelligent_fallback_scheduling(tasks, free_blocks, urgent_tasks, max_suggestions)


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
