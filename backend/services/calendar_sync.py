"""
Calendar Sync Service - Phase 4

Syncs calendar events from Google Calendar to local database.

Key Features:
1. Fetch events from Google Calendar API
2. Cache events in local database for fast access
3. Background sync every 15 minutes
4. Parse event details (attendees, time, description)

Usage:
    sync_service = CalendarSyncService()

    # Manual sync
    events = await sync_service.sync_calendar(user_id=1, db=db)

    # Get cached events
    events = await sync_service.get_events(user_id=1, db=db, days_ahead=7)
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from googleapiclient.discovery import build
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from db.models import CalendarEvent
from services.google_oauth import get_oauth_service
from utils.datetime_utils import now_utc, normalize_datetime
from utils.event_utils import is_blocking_event

logger = logging.getLogger(__name__)


class CalendarSyncService:
    """Service for syncing Google Calendar events."""

    def __init__(self):
        """Initialize calendar sync service."""
        self.oauth_service = get_oauth_service()
        self.sync_interval_minutes = int(os.getenv("CALENDAR_SYNC_INTERVAL_MINUTES", "15"))
        self.lookahead_days = int(os.getenv("SCHEDULING_LOOKAHEAD_DAYS", "14"))

    async def sync_calendar(
        self,
        user_id: int,
        db: AsyncSession,
        days_ahead: Optional[int] = None
    ) -> List[CalendarEvent]:
        """Fetch events from Google Calendar and cache in database.

        Args:
            user_id: User ID
            db: Database session
            days_ahead: Number of days to fetch (default: SCHEDULING_LOOKAHEAD_DAYS)

        Returns:
            List of CalendarEvent objects

        Raises:
            ValueError: If user not authorized or API call fails
        """
        days = days_ahead or self.lookahead_days

        try:
            # Get valid credentials
            credentials = await self.oauth_service.get_valid_credentials(user_id, db)

            # Build Calendar API client
            service = build('calendar', 'v3', credentials=credentials)

            # Define time range
            now = now_utc()
            end_date = now + timedelta(days=days)

            # Fetch events
            logger.info(f"Fetching calendar events for user {user_id} ({days} days)")
            events_result = service.events().list(
                calendarId='primary',
                timeMin=now.isoformat() + 'Z',
                timeMax=end_date.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime',
                maxResults=250  # Google Calendar API limit per page
            ).execute()

            events_data = events_result.get('items', [])
            logger.info(f"Fetched {len(events_data)} events from Google Calendar")

            # Parse and cache events
            calendar_events = []
            for event_data in events_data:
                calendar_event = await self._parse_and_cache_event(
                    event_data,
                    user_id,
                    db
                )
                if calendar_event:
                    calendar_events.append(calendar_event)

            await db.commit()

            logger.info(f"Synced {len(calendar_events)} events for user {user_id}")
            return calendar_events

        except Exception as e:
            logger.error(f"Calendar sync failed for user {user_id}: {e}")
            raise ValueError(f"Failed to sync calendar: {e}")

    async def _parse_and_cache_event(
        self,
        event_data: dict,
        user_id: int,
        db: AsyncSession
    ) -> Optional[CalendarEvent]:
        """Parse Google Calendar event and cache in database.

        Args:
            event_data: Raw event data from Google Calendar API
            user_id: User ID
            db: Database session

        Returns:
            CalendarEvent object or None if parsing failed
        """
        try:
            google_event_id = event_data.get('id')
            if not google_event_id:
                return None

            # Parse datetime
            start = event_data.get('start', {})
            end = event_data.get('end', {})

            # Handle all-day events
            if 'date' in start:
                start_time = datetime.fromisoformat(start['date'])
                end_time = datetime.fromisoformat(end['date'])
                all_day = True
            else:
                start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
                all_day = False

            # Parse attendees
            attendees_data = event_data.get('attendees', [])
            attendees = [a.get('email') for a in attendees_data if a.get('email')]

            # Get organizer
            organizer_data = event_data.get('organizer', {})
            organizer = organizer_data.get('email')
            
            # Determine if it's a meeting (will be refined after creating CalendarEvent)
            # For now, use simple heuristic: multiple attendees = meeting
            is_meeting = len(attendees) > 1

            # Check if event already exists
            query = select(CalendarEvent).where(
                CalendarEvent.google_event_id == google_event_id
            )
            result = await db.execute(query)
            existing_event = result.scalar_one_or_none()

            if existing_event:
                # Update existing event
                existing_event.title = event_data.get('summary', 'Untitled')
                existing_event.description = event_data.get('description')
                existing_event.location = event_data.get('location')
                existing_event.start_time = start_time
                existing_event.end_time = end_time
                existing_event.all_day = all_day
                existing_event.attendees = attendees
                existing_event.organizer = organizer
                existing_event.is_meeting = is_meeting
                # Refine is_meeting using blocking logic after updating all fields
                existing_event.is_meeting = is_blocking_event(existing_event)
                existing_event.last_synced = now_utc()
                existing_event.updated_at = now_utc()

                return existing_event
            else:
                # Create new event
                new_event = CalendarEvent(
                    user_id=user_id,
                    google_event_id=google_event_id,
                    title=event_data.get('summary', 'Untitled'),
                    description=event_data.get('description'),
                    location=event_data.get('location'),
                    start_time=start_time,
                    end_time=end_time,
                    timezone=start.get('timeZone', 'Europe/Amsterdam'),
                    all_day=all_day,
                    attendees=attendees,
                    organizer=organizer,
                    is_meeting=is_meeting
                )
                # Refine is_meeting using blocking logic (more accurate)
                new_event.is_meeting = is_blocking_event(new_event)
                db.add(new_event)

                return new_event

        except Exception as e:
            logger.error(f"Failed to parse event {event_data.get('id')}: {e}")
            return None

    async def get_events(
        self,
        user_id: int,
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days_ahead: int = 7
    ) -> List[CalendarEvent]:
        """Get cached calendar events from database.

        Args:
            user_id: User ID
            db: Database session
            start_date: Start of date range (default: now)
            end_date: End of date range (default: now + days_ahead)
            days_ahead: Days to look ahead if end_date not specified

        Returns:
            List of CalendarEvent objects
        """
        start = start_date or now_utc()
        end = end_date or (start + timedelta(days=days_ahead))
        
        # Ensure timezone-aware
        start = normalize_datetime(start)
        end = normalize_datetime(end)

        query = select(CalendarEvent).where(
            and_(
                CalendarEvent.user_id == user_id,
                CalendarEvent.start_time >= start,
                CalendarEvent.start_time < end
            )
        ).order_by(CalendarEvent.start_time)

        result = await db.execute(query)
        events = result.scalars().all()

        return list(events)

    async def get_events_by_date(
        self,
        user_id: int,
        db: AsyncSession,
        date: datetime
    ) -> List[CalendarEvent]:
        """Get all events for a specific date.

        Args:
            user_id: User ID
            db: Database session
            date: Date to get events for

        Returns:
            List of CalendarEvent objects
        """
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        return await self.get_events(user_id, db, start_of_day, end_of_day)

    async def create_calendar_event(
        self,
        user_id: int,
        db: AsyncSession,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None
    ) -> CalendarEvent:
        """Create a new event in Google Calendar.

        Args:
            user_id: User ID
            db: Database session
            title: Event title
            start_time: Start time
            end_time: End time
            description: Event description (optional)
            location: Event location (optional)

        Returns:
            Created CalendarEvent object

        Raises:
            ValueError: If creation fails
        """
        try:
            # Get valid credentials
            credentials = await self.oauth_service.get_valid_credentials(user_id, db)

            # Build Calendar API client
            service = build('calendar', 'v3', credentials=credentials)

            # Create event
            event_body = {
                'summary': title,
                'description': description,
                'location': location,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'Europe/Amsterdam',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'Europe/Amsterdam',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
            }

            created_event = service.events().insert(
                calendarId='primary',
                body=event_body
            ).execute()

            logger.info(f"Created calendar event: {title}")

            # Cache in database
            calendar_event = CalendarEvent(
                user_id=user_id,
                google_event_id=created_event['id'],
                title=title,
                description=description,
                location=location,
                start_time=start_time,
                end_time=end_time,
                timezone='Europe/Amsterdam',
                all_day=False,
                attendees=[],
                is_meeting=False
            )
            db.add(calendar_event)
            await db.commit()
            await db.refresh(calendar_event)

            return calendar_event

        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            raise ValueError(f"Failed to create event: {e}")

    async def delete_calendar_event(
        self,
        user_id: int,
        db: AsyncSession,
        google_event_id: str
    ):
        """Delete an event from Google Calendar and local cache.

        Args:
            user_id: User ID
            db: Database session
            google_event_id: Google Calendar event ID

        Raises:
            ValueError: If deletion fails
        """
        try:
            # Get valid credentials
            credentials = await self.oauth_service.get_valid_credentials(user_id, db)

            # Build Calendar API client
            service = build('calendar', 'v3', credentials=credentials)

            # Delete from Google Calendar
            service.events().delete(
                calendarId='primary',
                eventId=google_event_id
            ).execute()

            logger.info(f"Deleted calendar event: {google_event_id}")

            # Delete from local cache
            query = select(CalendarEvent).where(
                CalendarEvent.google_event_id == google_event_id
            )
            result = await db.execute(query)
            event = result.scalar_one_or_none()

            if event:
                await db.delete(event)
                await db.commit()

        except Exception as e:
            logger.error(f"Failed to delete calendar event: {e}")
            raise ValueError(f"Failed to delete event: {e}")


# Singleton instance
_calendar_sync_service = None


def get_calendar_sync_service() -> CalendarSyncService:
    """Get singleton calendar sync service instance.

    Returns:
        CalendarSyncService instance
    """
    global _calendar_sync_service
    if _calendar_sync_service is None:
        _calendar_sync_service = CalendarSyncService()
    return _calendar_sync_service
