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
from typing import Optional

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
        today = datetime.utcnow()
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
    db: AsyncSession = Depends(get_db)
):
    """
    Generate scheduling suggestions for tasks.

    Uses SchedulingAgent to suggest optimal times for task work.
    To be implemented with SchedulingAgent.

    Returns:
        {
            "suggestions": [
                {
                    "task_id": "task-123",
                    "task_title": "Complete CRESCO dashboard",
                    "suggested_start": "2025-11-19T14:00:00Z",
                    "suggested_end": "2025-11-19T16:00:00Z",
                    "confidence": 85,
                    "reasoning": "Due tomorrow, free afternoon block available"
                }
            ]
        }
    """
    return {
        "message": "Scheduling agent not yet implemented",
        "suggestions": []
    }


@router.post("/calendar/approve-block")
async def approve_time_block(
    block_id: int,
    user_id: int = Query(default=1, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve a scheduling suggestion and create calendar event.

    Creates a Google Calendar event with 🪷 prefix for the time block.

    Returns:
        {
            "success": true,
            "calendar_event_id": "abc123",
            "message": "Time block created in calendar"
        }
    """
    return {
        "message": "Time block approval not yet implemented",
        "success": False
    }


@router.get("/calendar/meeting-prep")
async def get_meeting_prep_suggestions(
    user_id: int = Query(default=1, description="User ID"),
    days_ahead: int = Query(default=3, description="Days to check"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get meeting prep suggestions.

    Identifies meetings needing preparation and suggests what to do.

    Returns:
        {
            "prep_suggestions": [
                {
                    "meeting": {...},
                    "prep_needed": true,
                    "prep_checklist": ["Review dashboard", "Prepare demo"],
                    "incomplete_tasks": [...],
                    "urgency": "high"
                }
            ]
        }
    """
    return {
        "message": "Meeting prep assistant not yet implemented",
        "prep_suggestions": []
    }
