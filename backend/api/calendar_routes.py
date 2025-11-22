"""
Calendar API Routes - Phase 4

API endpoints for Google Calendar integration:
1. OAuth authorization flow
2. Calendar event syncing
3. Scheduling suggestions
4. Time block management

Routes:
- GET  /api/auth/google/authorize - Start OAuth flow
- GET  /api/auth/google/callback  - Handle OAuth callback
- GET  /api/auth/google/status    - Check authorization status
- POST /api/calendar/sync         - Manually trigger calendar sync
- GET  /api/calendar/events       - Get cached calendar events
- POST /api/calendar/schedule     - Generate scheduling suggestions
- POST /api/calendar/approve-block - Approve time block and create calendar event
- GET  /api/calendar/meeting-prep - Get meeting prep suggestions
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from db.database import get_db
from services.google_oauth import get_oauth_service
from services.calendar_sync import get_calendar_sync_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Calendar"])

# ============================================================================
# OAUTH ROUTES
# ============================================================================


@router.get("/auth/google/authorize")
async def authorize_google_calendar(
    user_id: int = Query(default=1, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Start OAuth flow for Google Calendar access.

    Returns authorization URL for user to visit and grant access.

    Example:
        GET /api/auth/google/authorize?user_id=1

        Response:
        {
            "authorization_url": "https://accounts.google.com/o/oauth2/auth?...",
            "message": "Please visit this URL to authorize calendar access"
        }
    """
    try:
        oauth_service = get_oauth_service()
        auth_url = oauth_service.get_authorization_url(user_id)

        return {
            "authorization_url": auth_url,
            "message": "Please visit this URL to authorize calendar access"
        }

    except Exception as e:
        logger.error(f"Failed to generate OAuth URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/google/callback")
async def google_calendar_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="User ID from state parameter"),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle OAuth callback from Google.

    This endpoint is called by Google after user authorizes access.
    It exchanges the authorization code for access/refresh tokens.

    After successful authorization, redirects user to frontend.

    Example:
        GET /api/auth/google/callback?code=4/xxx&state=1

        Redirects to: http://localhost:8080/calendar-connected
    """
    try:
        user_id = int(state)
        oauth_service = get_oauth_service()

        # Exchange code for tokens
        await oauth_service.handle_callback(code, user_id, db)

        logger.info(f"OAuth callback successful for user {user_id}")

        # Trigger initial calendar sync
        calendar_service = get_calendar_sync_service()
        await calendar_service.sync_calendar(user_id, db)

        # Redirect to frontend success page
        frontend_url = "http://localhost:8080/calendar-connected"
        return RedirectResponse(url=frontend_url)

    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        # Redirect to error page
        return RedirectResponse(url=f"http://localhost:8080/calendar-error?error={str(e)}")


@router.get("/auth/google/status")
async def check_google_auth_status(
    user_id: int = Query(default=1, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if user has authorized Google Calendar access.

    Returns:
        {
            "authorized": true/false,
            "user_id": 1
        }
    """
    try:
        oauth_service = get_oauth_service()
        is_authorized = await oauth_service.is_authorized(user_id, db)

        return {
            "authorized": is_authorized,
            "user_id": user_id
        }

    except Exception as e:
        logger.error(f"Failed to check auth status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/auth/google/revoke")
async def revoke_google_authorization(
    user_id: int = Query(default=1, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke Google Calendar authorization and delete tokens.

    Returns:
        {
            "success": true,
            "message": "Authorization revoked"
        }
    """
    try:
        oauth_service = get_oauth_service()
        await oauth_service.revoke_authorization(user_id, db)

        return {
            "success": True,
            "message": "Authorization revoked"
        }

    except Exception as e:
        logger.error(f"Failed to revoke authorization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CALENDAR SYNC ROUTES
# ============================================================================


@router.post("/calendar/sync")
async def sync_calendar(
    user_id: int = Query(default=1, description="User ID"),
    days_ahead: int = Query(default=14, description="Days to sync ahead"),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger calendar sync from Google Calendar.

    Fetches events from Google Calendar and caches them locally.
    Background sync runs automatically every 15 minutes.

    Args:
        user_id: User ID
        days_ahead: Number of days to sync (default: 14)

    Returns:
        {
            "success": true,
            "events_count": 42,
            "synced_at": "2025-11-18T10:30:00Z"
        }
    """
    try:
        calendar_service = get_calendar_sync_service()
        events = await calendar_service.sync_calendar(user_id, db, days_ahead)

        return {
            "success": True,
            "events_count": len(events),
            "synced_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Calendar sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calendar/events")
async def get_calendar_events(
    user_id: int = Query(default=1, description="User ID"),
    days_ahead: int = Query(default=7, description="Days to look ahead"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get cached calendar events.

    Returns events from local cache (fast, no API calls).

    Args:
        user_id: User ID
        days_ahead: Number of days to return (default: 7)

    Returns:
        {
            "events": [
                {
                    "id": 1,
                    "title": "Team Standup",
                    "start_time": "2025-11-18T09:00:00Z",
                    "end_time": "2025-11-18T09:30:00Z",
                    "is_meeting": true,
                    "attendees": ["andy@example.com"],
                    ...
                }
            ],
            "total": 42
        }
    """
    try:
        calendar_service = get_calendar_sync_service()
        events = await calendar_service.get_events(
            user_id,
            db,
            days_ahead=days_ahead
        )

        # Convert to dict
        events_data = [
            {
                "id": e.id,
                "google_event_id": e.google_event_id,
                "title": e.title,
                "description": e.description,
                "location": e.location,
                "start_time": e.start_time.isoformat(),
                "end_time": e.end_time.isoformat(),
                "all_day": e.all_day,
                "attendees": e.attendees or [],
                "organizer": e.organizer,
                "is_meeting": e.is_meeting,
                "importance_score": e.importance_score,
                "related_projects": e.related_projects or [],
                "prep_needed": e.prep_needed
            }
            for e in events
        ]

        return {
            "events": events_data,
            "total": len(events_data)
        }

    except Exception as e:
        logger.error(f"Failed to get events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calendar/events/today")
async def get_todays_events(
    user_id: int = Query(default=1, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get today's calendar events.

    Returns:
        {
            "events": [...],
            "date": "2025-11-18"
        }
    """
    try:
        calendar_service = get_calendar_sync_service()
        from datetime import timezone
        today = datetime.now(timezone.utc)
        events = await calendar_service.get_events_by_date(user_id, db, today)

        events_data = [
            {
                "id": e.id,
                "title": e.title,
                "start_time": e.start_time.isoformat(),
                "end_time": e.end_time.isoformat(),
                "is_meeting": e.is_meeting,
                "attendees": e.attendees or []
            }
            for e in events
        ]

        return {
            "events": events_data,
            "date": today.date().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get today's events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PLACEHOLDER ROUTES (To be implemented with agents)
# ============================================================================


@router.post("/calendar/schedule-tasks")
async def schedule_tasks(
    user_id: int = Query(default=1, description="User ID"),
    days_ahead: int = Query(default=7, description="Days to schedule ahead"),
    max_suggestions: int = Query(default=10, description="Max suggestions to generate"),
    task_id: Optional[str] = Query(default=None, description="Optional: Schedule only this specific task"),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate scheduling suggestions for tasks.

    Uses SchedulingAgent with Gemini to suggest optimal times for task work.
    Considers urgency, deadlines, meeting prep, and user preferences.

    Args:
        user_id: User ID
        days_ahead: Days to look ahead for scheduling
        max_suggestions: Maximum number of suggestions to generate
        task_id: Optional task ID to schedule only that specific task

    Returns:
        {
            "suggestions": [
                {
                    "id": 1,
                    "task_id": "task-123",
                    "task_title": "Complete CRESCO dashboard",
                    "start_time": "2025-11-19T14:00:00Z",
                    "end_time": "2025-11-19T16:00:00Z",
                    "duration_minutes": 120,
                    "confidence": 85,
                    "quality_score": 90,
                    "reasoning": "Due tomorrow, free afternoon block available",
                    "status": "suggested"
                }
            ],
            "total": 5
        }
    """
    try:
        from agents.scheduling_agent import get_scheduling_agent
        from sqlalchemy import select
        from db.models import Task

        # Get active tasks (optionally filter by task_id)
        if task_id:
            # Schedule only the specific task
            query = select(Task).where(
                Task.id == task_id,
                Task.status.in_(['todo', 'doing'])
            )
            logger.info(f"Scheduling specific task: {task_id}")
        else:
            # Schedule all active tasks
            query = select(Task).where(
                Task.status.in_(['todo', 'doing'])
            ).order_by(Task.created_at.desc())
            logger.info("Scheduling all active tasks")

        result = await db.execute(query)
        tasks = result.scalars().all()

        if not tasks:
            if task_id:
                return {
                    "suggestions": [],
                    "total": 0,
                    "message": f"Task '{task_id}' not found or not active (must be 'todo' or 'doing')"
                }
            return {
                "suggestions": [],
                "total": 0,
                "message": "No active tasks to schedule"
            }

        # Check if user is authorized
        oauth_service = get_oauth_service()
        is_authorized = await oauth_service.is_authorized(user_id, db)
        if not is_authorized:
            return {
                "suggestions": [],
                "total": 0,
                "message": "Calendar not authorized. Please connect your Google Calendar first."
            }

        # Check if calendar has been synced (has events in the date range)
        calendar_service = get_calendar_sync_service()
        check_events = await calendar_service.get_events(user_id, db, days_ahead=days_ahead)
        
        # If no events found, suggest syncing calendar
        # (But still proceed - maybe calendar is empty, which is fine)
        if len(check_events) == 0:
            logger.info(f"No calendar events found for user {user_id}. Calendar may not be synced yet.")

        # Generate suggestions
        logger.info(f"Calling scheduling agent for {len(tasks)} tasks, max_suggestions={max_suggestions}")
        agent = get_scheduling_agent()
        scheduled_blocks = await agent.schedule_tasks(
            tasks=list(tasks),
            user_id=user_id,
            db=db,
            days_ahead=days_ahead,
            max_suggestions=max_suggestions
        )
        logger.info(f"Scheduling agent returned {len(scheduled_blocks)} scheduled blocks")

        # Convert to response format
        suggestions = []
        logger.info(f"Converting {len(scheduled_blocks)} scheduled blocks to response format...")
        for block in scheduled_blocks:
            # Get task for title
            task_query = select(Task).where(Task.id == block.task_id)
            task_result = await db.execute(task_query)
            task = task_result.scalar_one_or_none()

            suggestions.append({
                "id": block.id,
                "task_id": block.task_id,
                "task_title": task.title if task else "Unknown Task",
                "start_time": block.start_time.isoformat(),
                "end_time": block.end_time.isoformat(),
                "duration_minutes": block.duration_minutes,
                "confidence": block.confidence_score,
                "quality_score": block.quality_score,
                "reasoning": block.reasoning,
                "status": block.status
            })

        logger.info(f"Converted {len(suggestions)} suggestions for API response")
        
        if len(suggestions) == 0:
            logger.warning("⚠ No suggestions to return - generating diagnostic message")
            # Provide helpful message about why no suggestions
            calendar_service = get_calendar_sync_service()
            events = await calendar_service.get_events(user_id, db, days_ahead=days_ahead)
            
            # Get preferences for work hours info
            from services.work_preferences import get_work_preferences
            prefs = await get_work_preferences(db, user_id)
            
            # Count events per day
            from collections import defaultdict
            events_by_day = defaultdict(int)
            for event in events:
                if not event.all_day:
                    day_key = event.start_time.date()
                    events_by_day[day_key] += 1
            
            avg_events_per_day = len(events_by_day) and (len(events) / len(events_by_day)) or 0
            
            message = (
                f"No available time slots found in the next {days_ahead} days. "
                f"Calendar has {len(events)} events ({avg_events_per_day:.1f} per day on average). "
                f"Work hours: {prefs.no_meetings_before} to {prefs.no_meetings_after}. "
                "Your calendar may be completely full. Try adjusting work hours or look further ahead."
            )
            
            return {
                "suggestions": [],
                "total": 0,
                "message": message,
                "diagnostics": {
                    "events_count": len(events),
                    "events_per_day": round(avg_events_per_day, 1),
                    "work_hours": f"{prefs.no_meetings_before} to {prefs.no_meetings_after}",
                    "days_ahead": days_ahead
                }
            }

        return {
            "suggestions": suggestions,
            "total": len(suggestions),
            "message": f"Found {len(suggestions)} scheduling suggestion(s)"
        }

    except Exception as e:
        logger.error(f"Failed to generate scheduling suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate scheduling suggestions: {str(e)}")


@router.post("/calendar/approve-block")
async def approve_time_block(
    block_id: int,
    user_id: int = Query(default=1, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve a scheduling suggestion and create calendar event.

    Creates a Google Calendar event with 🪷 prefix for the time block.
    Adds a comment to the task explaining the time block.

    Args:
        block_id: Scheduled block ID
        user_id: User ID

    Returns:
        {
            "success": true,
            "calendar_event_id": "abc123",
            "block_id": 1,
            "task_id": "task-123",
            "message": "Time block created in Google Calendar"
        }
    """
    try:
        from sqlalchemy import select
        from db.models import ScheduledBlock, Task, Comment
        from services.work_preferences import get_work_preferences
        import uuid

        # 1. Get scheduled block
        query = select(ScheduledBlock).where(ScheduledBlock.id == block_id)
        result = await db.execute(query)
        block = result.scalar_one_or_none()

        if not block:
            raise HTTPException(status_code=404, detail="Scheduled block not found")

        if block.status == 'approved':
            raise HTTPException(status_code=400, detail="Block already approved")

        # 2. Get task
        task_query = select(Task).where(Task.id == block.task_id)
        task_result = await db.execute(task_query)
        task = task_result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # 3. Get user preferences for event styling
        preferences = await get_work_preferences(db, user_id)

        # 4. Create Google Calendar event
        calendar_service = get_calendar_sync_service()

        event_title = f"{preferences.task_event_prefix}{task.title}"
        event_description = (
            f"Task: {task.title}\n"
            f"Description: {task.description or 'No description'}\n"
            f"Project: {task.value_stream or 'None'}\n"
            f"\n"
            f"Created by Lotus - AI Work Orchestrator"
        )

        try:
            calendar_event = await calendar_service.create_calendar_event(
                user_id=user_id,
                db=db,
                title=event_title,
                start_time=block.start_time,
                end_time=block.end_time,
                description=event_description
            )

            # 5. Update block status
            block.status = 'approved'
            block.calendar_event_id = calendar_event.google_event_id

            # 6. Add comment to task
            comment_text = (
                f"⏰ Time blocked: {block.start_time.strftime('%A, %B %d at %I:%M %p')} - "
                f"{block.end_time.strftime('%I:%M %p')} ({block.duration_minutes} minutes)\n\n"
                f"I've added this to your calendar as '{event_title}'. "
                f"Quality score: {block.quality_score}/100 ({_get_quality_label(block.quality_score)})"
            )

            comment = Comment(
                id=str(uuid.uuid4()),
                task_id=task.id,
                text=comment_text,
                author="Lotus"
            )
            db.add(comment)

            await db.commit()

            logger.info(f"Approved time block {block_id} for task '{task.title}'")

            return {
                "success": True,
                "calendar_event_id": calendar_event.google_event_id,
                "block_id": block.id,
                "task_id": task.id,
                "message": "Time block created in Google Calendar"
            }

        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create calendar event: {e}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve time block: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calendar/task-scheduled")
async def check_task_scheduled(
    task_id: str = Query(..., description="Task ID to check"),
    user_id: int = Query(default=1, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if a task has an approved scheduled block.

    Checks both ScheduledBlock table and CalendarEvent table to find
    if a task is scheduled. Returns the scheduled block information if found.

    Args:
        task_id: Task ID to check
        user_id: User ID

    Returns:
        {
            "scheduled": true/false,
            "block": {
                "id": 1,
                "start_time": "2025-11-19T14:00:00Z",
                "end_time": "2025-11-19T16:00:00Z",
                "duration_minutes": 120,
                "calendar_event_id": "abc123",
                "quality_score": 90
            } or null
        }
    """
    try:
        from sqlalchemy import select, or_, and_
        from db.models import ScheduledBlock, Task, CalendarEvent
        from services.work_preferences import get_work_preferences
        from datetime import datetime, timezone

        # First, get the task to get its title
        task_query = select(Task).where(Task.id == task_id)
        task_result = await db.execute(task_query)
        task = task_result.scalar_one_or_none()

        if not task:
            logger.warning(f"Task {task_id} not found")
            return {
                "scheduled": False,
                "block": None
            }

        # Method 1: Check ScheduledBlock table (primary method)
        block_query = select(ScheduledBlock).where(
            ScheduledBlock.task_id == task_id,
            ScheduledBlock.user_id == user_id,
            ScheduledBlock.status == 'approved'
        ).order_by(ScheduledBlock.created_at.desc())

        block_result = await db.execute(block_query)
        block = block_result.scalar_one_or_none()

        if block:
            logger.info(f"Found approved ScheduledBlock {block.id} for task {task_id}")
            return {
                "scheduled": True,
                "block": {
                    "id": block.id,
                    "start_time": block.start_time.isoformat(),
                    "end_time": block.end_time.isoformat(),
                    "duration_minutes": block.duration_minutes,
                    "calendar_event_id": block.calendar_event_id,
                    "quality_score": block.quality_score,
                    "confidence_score": block.confidence_score
                }
            }

        # Method 2: Check CalendarEvent table for matching events
        # Get user preferences to know the task event prefix
        try:
            preferences = await get_work_preferences(db, user_id)
            task_prefix = preferences.task_event_prefix or "🪷 "
        except Exception as e:
            logger.warning(f"Could not get work preferences: {e}, using default prefix")
            task_prefix = "🪷 "

        # Build expected event title variations
        expected_title_with_prefix = f"{task_prefix}{task.title}"
        expected_title_no_prefix = task.title

        # Check for calendar events that match:
        # 1. Event title matches expected title (with or without prefix)
        # 2. Event description contains "Task: [task title]"
        # 3. Event has this task_id in related_task_ids
        # 4. Event is in the future (not past)
        now = datetime.now(timezone.utc)
        
        # Get all future events for this user to check multiple criteria
        all_events_query = select(CalendarEvent).where(
            and_(
                CalendarEvent.user_id == user_id,
                CalendarEvent.end_time >= now  # Only future events
            )
        ).order_by(CalendarEvent.start_time.asc())
        
        all_events_result = await db.execute(all_events_query)
        all_events = all_events_result.scalars().all()
        
        logger.info(f"Checking {len(all_events)} future calendar events for task {task_id} ('{task.title}')")
        
        # Check each event for matches
        for event in all_events:
            # Method 1: Check title (with or without prefix)
            if event.title == expected_title_with_prefix or event.title == expected_title_no_prefix:
                calendar_event = event
                logger.info(f"Found calendar event {event.id} by title match: '{event.title}'")
                break
            
            # Method 2: Check description for "Task: [task title]" pattern
            if event.description:
                # Look for patterns like "Task: Katie Data Deep Dive" or "Task: {task.title}"
                description_lower = event.description.lower()
                task_title_lower = task.title.lower()
                
                # Check for "Task: [title]" pattern
                if f"task: {task_title_lower}" in description_lower:
                    calendar_event = event
                    logger.info(f"Found calendar event {event.id} by description match: contains 'Task: {task.title}'")
                    break
                
                # Also check if description contains the task title directly
                if task_title_lower in description_lower and len(task_title_lower) > 5:
                    # Additional check: make sure it's not just a partial match
                    # Look for the task title as a standalone word/phrase
                    import re
                    pattern = rf'\b{re.escape(task_title_lower)}\b'
                    if re.search(pattern, description_lower):
                        calendar_event = event
                        logger.info(f"Found calendar event {event.id} by description pattern match: '{task.title}'")
                        break
            
            # Method 3: Check related_task_ids
            if event.related_task_ids and task_id in event.related_task_ids:
                calendar_event = event
                logger.info(f"Found calendar event {event.id} with task {task_id} in related_task_ids")
                break

        if calendar_event:
            logger.info(f"Found matching CalendarEvent {calendar_event.id} for task {task_id}")
            # Calculate duration
            duration = int((calendar_event.end_time - calendar_event.start_time).total_seconds() / 60)
            
            return {
                "scheduled": True,
                "block": {
                    "id": calendar_event.id,  # Use calendar event ID
                    "start_time": calendar_event.start_time.isoformat(),
                    "end_time": calendar_event.end_time.isoformat(),
                    "duration_minutes": duration,
                    "calendar_event_id": calendar_event.google_event_id,
                    "quality_score": None,  # Not available from calendar event
                    "confidence_score": None  # Not available from calendar event
                }
            }

        logger.debug(f"No scheduled block or calendar event found for task {task_id}")
        return {
            "scheduled": False,
            "block": None
        }

    except Exception as e:
        logger.error(f"Failed to check task scheduled status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/calendar/cancel-block/{task_id}")
async def cancel_scheduled_block(
    task_id: str,
    user_id: int = Query(default=1, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a scheduled block for a task (delete calendar event but keep task).
    
    This removes the calendar event from Google Calendar and marks the scheduled
    block as cancelled, but does not delete the task itself. Adds a cancellation
    comment from Lotus to show the chain of events.
    
    Args:
        task_id: Task ID
        user_id: User ID
        
    Returns:
        {
            "success": true,
            "message": "Scheduled block cancelled and calendar event removed",
            "deleted_calendar_events": 1
        }
    """
    try:
        from sqlalchemy import select
        from db.models import ScheduledBlock, Task, Comment
        import uuid
        from datetime import datetime, timezone
        
        # Get the task to add comment to
        task_query = select(Task).where(Task.id == task_id)
        task_result = await db.execute(task_query)
        task = task_result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Find all approved scheduled blocks for this task
        scheduled_blocks_query = select(ScheduledBlock).where(
            ScheduledBlock.task_id == task_id,
            ScheduledBlock.user_id == user_id,
            ScheduledBlock.status == 'approved',
            ScheduledBlock.calendar_event_id.isnot(None)
        )
        scheduled_blocks_result = await db.execute(scheduled_blocks_query)
        scheduled_blocks = scheduled_blocks_result.scalars().all()
        
        if not scheduled_blocks:
            raise HTTPException(
                status_code=404,
                detail="No scheduled blocks found for this task"
            )
        
        # Delete calendar events and mark blocks as cancelled
        calendar_service = get_calendar_sync_service()
        deleted_events = []
        cancelled_blocks_count = 0
        
        from db.models import CalendarEvent
        
        for block in scheduled_blocks:
            if not block.calendar_event_id:
                continue
                
            try:
                # Delete calendar event from Google Calendar
                await calendar_service.delete_calendar_event(
                    user_id=user_id,
                    db=db,
                    google_event_id=block.calendar_event_id
                )
                deleted_events.append(block.calendar_event_id)
                
                # Mark block as cancelled in database
                block.status = 'cancelled'
                block.calendar_event_id = None
                cancelled_blocks_count += 1
                
            except Exception as e:
                # Log warning but continue - event may already be deleted
                # (e.g., user deleted it manually in Google Calendar)
                logger.warning(
                    f"Failed to delete calendar event {block.calendar_event_id}: {e}. "
                    "Event may have been deleted manually."
                )
        
        # Add cancellation comment from Lotus to show chain of events
        if cancelled_blocks_count > 0:
            comment_text = (
                "❌ You cancelled the scheduled task block"
                if cancelled_blocks_count == 1
                else f"❌ You cancelled {cancelled_blocks_count} scheduled task blocks"
            )
            
            comment = Comment(
                id=str(uuid.uuid4()),
                task_id=task.id,
                text=comment_text,
                author="Lotus"
            )
            db.add(comment)
            logger.info(f"Added cancellation comment to task {task_id}")
        
        await db.commit()
        
        return {
            "success": True,
            "message": "Scheduled block cancelled and calendar event removed",
            "deleted_calendar_events": len(deleted_events)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel scheduled block: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_quality_label(score: int) -> str:
    """Get human-readable quality label."""
    if score >= 90:
        return "Excellent time - prime focus hours"
    elif score >= 75:
        return "Great time for this task"
    elif score >= 60:
        return "Good time available"
    else:
        return "Available time"


@router.get("/calendar/meeting-prep")
async def get_meeting_prep_suggestions(
    user_id: int = Query(default=1, description="User ID"),
    days_ahead: int = Query(default=3, description="Days to check"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get meeting prep suggestions.

    Identifies meetings needing preparation and suggests what to do.
    Uses MeetingPrepAssistant with Gemini to generate prep checklists.

    Args:
        user_id: User ID
        days_ahead: Days to look ahead (default: 3)

    Returns:
        {
            "prep_suggestions": [
                {
                    "id": 1,
                    "meeting": {
                        "title": "CRESCO Q4 Review",
                        "start_time": "2025-11-20T14:00:00Z",
                        "attendees": ["andy@example.com"],
                        "importance": 85
                    },
                    "prep_checklist": ["Review Q4 metrics", "Prepare demo"],
                    "incomplete_tasks": [
                        {"id": "task-123", "title": "Complete dashboard"}
                    ],
                    "estimated_prep_time": 45,
                    "urgency": "high",
                    "priority_score": 85
                }
            ],
            "total": 3,
            "estimated_total_time": 120
        }
    """
    try:
        from agents.meeting_prep_assistant import get_meeting_prep_assistant
        from sqlalchemy import select
        from db.models import CalendarEvent, Task

        # Generate prep suggestions
        assistant = get_meeting_prep_assistant()
        prep_items = await assistant.analyze_upcoming_meetings(
            user_id=user_id,
            db=db,
            days_ahead=days_ahead
        )

        # Convert to response format
        prep_suggestions = []
        total_time = 0

        for prep in prep_items:
            # Get meeting details
            meeting_query = select(CalendarEvent).where(
                CalendarEvent.id == prep.calendar_event_id
            )
            meeting_result = await db.execute(meeting_query)
            meeting = meeting_result.scalar_one_or_none()

            if not meeting:
                continue

            # Get incomplete tasks
            if prep.incomplete_task_ids:
                task_query = select(Task).where(
                    Task.id.in_(prep.incomplete_task_ids)
                )
                task_result = await db.execute(task_query)
                incomplete_tasks = task_result.scalars().all()
            else:
                incomplete_tasks = []

            prep_suggestions.append({
                "id": prep.id,
                "meeting": {
                    "id": meeting.id,
                    "title": meeting.title,
                    "start_time": meeting.start_time.isoformat(),
                    "end_time": meeting.end_time.isoformat(),
                    "attendees": meeting.attendees or [],
                    "importance": meeting.importance_score,
                    "location": meeting.location
                },
                "prep_checklist": prep.prep_checklist or [],
                "incomplete_tasks": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "status": t.status
                    }
                    for t in incomplete_tasks
                ],
                "estimated_prep_time": prep.estimated_prep_time or 30,
                "urgency": prep.urgency,
                "priority_score": prep.priority_score,
                "reasoning": prep.reasoning,
                "prep_completed": prep.prep_completed
            })

            total_time += prep.estimated_prep_time or 0

        return {
            "prep_suggestions": prep_suggestions,
            "total": len(prep_suggestions),
            "estimated_total_time": total_time
        }

    except Exception as e:
        logger.error(f"Failed to generate meeting prep suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WORK PREFERENCES ROUTES
# ============================================================================


@router.get("/calendar/preferences")
async def get_user_preferences(
    user_id: int = Query(default=1, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user work preferences.

    Returns scheduling preferences like deep work time, meeting style, etc.

    Returns:
        {
            "user_id": 1,
            "deep_work_time": "afternoon_evening",
            "preferred_task_time": "afternoon",
            "no_meetings_before": "09:00",
            "no_meetings_after": "18:00",
            "meeting_style": "back_to_back",
            "meeting_buffer": 0,
            "min_task_block": 30,
            "preferred_block_sizes": [30, 60, 90, 120],
            "task_event_prefix": "🪷 ",
            "task_event_color": "9",
            "auto_create_blocks": false,
            "preferences_json": {...}
        }
    """
    try:
        from services.work_preferences import get_work_preferences

        prefs = await get_work_preferences(db, user_id)

        return {
            "user_id": prefs.user_id,
            "deep_work_time": prefs.deep_work_time,
            "preferred_task_time": prefs.preferred_task_time,
            "no_meetings_before": prefs.no_meetings_before,
            "no_meetings_after": prefs.no_meetings_after,
            "meeting_style": prefs.meeting_style,
            "meeting_buffer": prefs.meeting_buffer,
            "min_task_block": prefs.min_task_block,
            "preferred_block_sizes": prefs.preferred_block_sizes or [],
            "task_event_prefix": prefs.task_event_prefix,
            "task_event_color": prefs.task_event_color,
            "auto_create_blocks": prefs.auto_create_blocks,
            "high_confidence_threshold": prefs.high_confidence_threshold,
            "preferences_json": prefs.preferences_json or {}
        }

    except Exception as e:
        logger.error(f"Failed to get user preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PreferencesUpdate(BaseModel):
    """Request model for updating preferences."""
    deep_work_time: Optional[str] = None
    preferred_task_time: Optional[str] = None
    no_meetings_before: Optional[str] = None
    no_meetings_after: Optional[str] = None
    meeting_style: Optional[str] = None
    meeting_buffer: Optional[int] = None
    min_task_block: Optional[int] = None
    preferred_block_sizes: Optional[List[int]] = None
    task_event_prefix: Optional[str] = None
    task_event_color: Optional[str] = None
    auto_create_blocks: Optional[bool] = None


@router.patch("/calendar/preferences")
async def update_user_preferences(
    updates: PreferencesUpdate,
    user_id: int = Query(default=1, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user work preferences.

    Allows partial updates (only send fields you want to change).

    Args:
        updates: Preference fields to update
        user_id: User ID

    Returns:
        Updated preferences object
    """
    try:
        from services.work_preferences import update_work_preferences

        # Convert to dict, removing None values
        updates_dict = {
            k: v for k, v in updates.dict().items()
            if v is not None
        }

        if not updates_dict:
            raise HTTPException(status_code=400, detail="No updates provided")

        # Update preferences
        prefs = await update_work_preferences(db, user_id, updates_dict)

        return {
            "success": True,
            "message": "Preferences updated successfully",
            "preferences": {
                "user_id": prefs.user_id,
                "deep_work_time": prefs.deep_work_time,
                "preferred_task_time": prefs.preferred_task_time,
                "no_meetings_before": prefs.no_meetings_before,
                "no_meetings_after": prefs.no_meetings_after,
                "meeting_style": prefs.meeting_style,
                "meeting_buffer": prefs.meeting_buffer,
                "min_task_block": prefs.min_task_block,
                "preferred_block_sizes": prefs.preferred_block_sizes or [],
                "task_event_prefix": prefs.task_event_prefix,
                "task_event_color": prefs.task_event_color,
                "auto_create_blocks": prefs.auto_create_blocks
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calendar/preferences/reset")
async def reset_user_preferences(
    user_id: int = Query(default=1, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Reset user preferences to defaults.

    Returns:
        Reset preferences object
    """
    try:
        from services.work_preferences import create_default_preferences
        from sqlalchemy import select, delete
        from db.models import WorkPreferences

        # Delete existing preferences
        delete_query = delete(WorkPreferences).where(
            WorkPreferences.user_id == user_id
        )
        await db.execute(delete_query)
        await db.commit()

        # Create new default preferences
        prefs = await create_default_preferences(db, user_id)

        return {
            "success": True,
            "message": "Preferences reset to defaults",
            "preferences": {
                "user_id": prefs.user_id,
                "deep_work_time": prefs.deep_work_time,
                "preferred_task_time": prefs.preferred_task_time,
                "no_meetings_before": prefs.no_meetings_before,
                "meeting_style": prefs.meeting_style
            }
        }

    except Exception as e:
        logger.error(f"Failed to reset preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))
