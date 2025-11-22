"""
Email-Calendar Intelligence - Phase 5

Automatically detects meeting invites in emails and creates/updates calendar events.

Key Features:
1. Detect meeting invites from email content
2. Extract meeting details (time, attendees, location)
3. Create Google Calendar events automatically
4. Link calendar events to email records
5. Deduplicate existing calendar events
"""

import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dateutil import parser as date_parser

from services.calendar_sync import get_calendar_sync_service
from db.models import EmailMessage, CalendarEvent
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)


class EmailCalendarIntelligence:
    """Service for email-to-calendar intelligent integration."""

    def __init__(self):
        """Initialize email-calendar intelligence service."""
        self.calendar_service = None

    async def process_meeting_invite(
        self,
        email: EmailMessage,
        db: AsyncSession,
        user_id: int = 1
    ) -> Optional[Dict[str, Any]]:
        """Process meeting invite email and create calendar event.

        Args:
            email: Email message record
            db: Database session
            user_id: User ID for calendar

        Returns:
            Dict with created calendar event info or None if not a meeting
        """
        if not email.is_meeting_invite:
            logger.debug(f"Email {email.id} is not a meeting invite")
            return None

        logger.info(f"Processing meeting invite from email {email.id}: {email.subject}")

        try:
            # Extract meeting details from email
            meeting_details = self._extract_meeting_details(email)

            if not meeting_details:
                logger.warning(f"Could not extract meeting details from email {email.id}")
                return None

            # Check if calendar event already exists for this email
            existing_event = await self._find_existing_event(db, email)
            if existing_event:
                logger.info(f"Calendar event already exists for email {email.id}")
                return {"event_id": existing_event.google_event_id, "created": False}

            # Initialize calendar service if needed
            if not self.calendar_service:
                self.calendar_service = get_calendar_sync_service()

            # Authenticate calendar service
            await self.calendar_service.initialize(db, user_id=user_id)

            # Create calendar event
            calendar_event = await self.calendar_service.create_event(
                summary=meeting_details["title"],
                description=meeting_details["description"],
                start_time=meeting_details["start_time"],
                end_time=meeting_details["end_time"],
                attendees=meeting_details.get("attendees", []),
                location=meeting_details.get("location"),
                db=db
            )

            logger.info(
                f"Created calendar event {calendar_event.google_event_id} "
                f"from email {email.id}"
            )

            return {
                "event_id": calendar_event.google_event_id,
                "created": True,
                "title": meeting_details["title"],
                "start_time": meeting_details["start_time"].isoformat(),
                "end_time": meeting_details["end_time"].isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to process meeting invite from email {email.id}: {e}")
            return None

    def _extract_meeting_details(self, email: EmailMessage) -> Optional[Dict[str, Any]]:
        """Extract meeting details from email content.

        Args:
            email: Email message

        Returns:
            Dict with meeting details or None
        """
        details = {}

        # Title from subject (remove common meeting prefixes)
        subject = email.subject or ""
        title = re.sub(r'^(Meeting:|Invitation:|Re:|Fwd:)\s*', '', subject, flags=re.IGNORECASE).strip()
        details["title"] = title or "Meeting"

        # Description from email body
        body = email.body_text or email.snippet or ""
        details["description"] = self._clean_meeting_description(body)

        # Extract date/time
        date_time = self._extract_datetime_from_email(email)
        if not date_time:
            logger.warning(f"Could not extract date/time from email {email.id}")
            return None

        details["start_time"] = date_time["start"]
        details["end_time"] = date_time["end"]

        # Extract attendees
        attendees = self._extract_attendees(email)
        if attendees:
            details["attendees"] = attendees

        # Extract location
        location = self._extract_location(email)
        if location:
            details["location"] = location

        return details

    def _extract_datetime_from_email(self, email: EmailMessage) -> Optional[Dict[str, datetime]]:
        """Extract meeting date/time from email.

        Args:
            email: Email message

        Returns:
            Dict with start and end datetime or None
        """
        # Strategy 1: Parse from subject line (e.g., "Meeting @ Mon Nov 20")
        subject = email.subject or ""
        date_match = re.search(
            r'@\s*(\w+\s+\w+\s+\d+)',  # @ Mon Nov 20
            subject
        )

        if date_match:
            try:
                date_str = date_match.group(1)
                parsed_date = date_parser.parse(date_str, fuzzy=True)

                # Default to 1 hour meeting
                return {
                    "start": parsed_date,
                    "end": parsed_date + timedelta(hours=1)
                }
            except Exception as e:
                logger.debug(f"Failed to parse date from subject: {e}")

        # Strategy 2: Look for dates in email body
        body = email.body_text or ""

        # Common patterns: "tomorrow at 2pm", "Monday at 3:00", "Nov 20 at 14:00"
        time_patterns = [
            r'(\w+day)\s+at\s+(\d+):?(\d+)?\s*(am|pm)?',  # Monday at 2:00pm
            r'(tomorrow|today)\s+at\s+(\d+):?(\d+)?\s*(am|pm)?',  # tomorrow at 2pm
            r'(\w+\s+\d+)\s+at\s+(\d+):?(\d+)?\s*(am|pm)?',  # Nov 20 at 2pm
        ]

        for pattern in time_patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                try:
                    time_str = match.group(0)
                    parsed_date = date_parser.parse(time_str, fuzzy=True)

                    # Default to 1 hour meeting
                    return {
                        "start": parsed_date,
                        "end": parsed_date + timedelta(hours=1)
                    }
                except Exception as e:
                    logger.debug(f"Failed to parse time pattern: {e}")
                    continue

        # Strategy 3: Use email received time + 1 day as fallback
        if email.received_at:
            default_time = email.received_at + timedelta(days=1)
            # Set to 10am next day
            default_time = default_time.replace(hour=10, minute=0, second=0, microsecond=0)

            logger.info(f"Using fallback time for email {email.id}: {default_time}")

            return {
                "start": default_time,
                "end": default_time + timedelta(hours=1)
            }

        return None

    def _extract_attendees(self, email: EmailMessage) -> List[str]:
        """Extract meeting attendees from email.

        Args:
            email: Email message

        Returns:
            List of attendee email addresses
        """
        attendees = []

        # Add sender
        if email.sender_email:
            attendees.append(email.sender_email)

        # Parse CC recipients
        if email.recipient_cc:
            cc_emails = re.findall(r'[\w\.-]+@[\w\.-]+', email.recipient_cc)
            attendees.extend(cc_emails)

        # Remove duplicates
        return list(set(attendees))

    def _extract_location(self, email: EmailMessage) -> Optional[str]:
        """Extract meeting location from email.

        Args:
            email: Email message

        Returns:
            Location string or None
        """
        body = (email.body_text or "").lower()

        # Look for common location indicators
        location_patterns = [
            r'location:\s*([^\n]+)',
            r'where:\s*([^\n]+)',
            r'room\s+([A-Z0-9-]+)',
            r'meet\s+(?:at|in)\s+([^\n,\.]+)',
        ]

        for pattern in location_patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if len(location) < 100:  # Sanity check
                    return location

        # Check for video conferencing links
        if 'zoom.us' in body:
            return "Zoom (link in email)"
        elif 'meet.google.com' in body or 'google meet' in body:
            return "Google Meet (link in email)"
        elif 'teams.microsoft.com' in body:
            return "Microsoft Teams (link in email)"

        return None

    def _clean_meeting_description(self, body: str, max_length: int = 500) -> str:
        """Clean and truncate meeting description.

        Args:
            body: Email body text
            max_length: Maximum description length

        Returns:
            Cleaned description
        """
        # Remove email signatures
        if '--' in body:
            body = body.split('--')[0]

        if 'Sent from' in body:
            body = body.split('Sent from')[0]

        # Remove excess whitespace
        body = re.sub(r'\n\s*\n', '\n\n', body)
        body = body.strip()

        # Truncate
        if len(body) > max_length:
            body = body[:max_length] + "..."

        return body

    async def _find_existing_event(
        self,
        db: AsyncSession,
        email: EmailMessage
    ) -> Optional[CalendarEvent]:
        """Check if calendar event already exists for this email.

        Args:
            db: Database session
            email: Email message

        Returns:
            CalendarEvent if exists, None otherwise
        """
        # Look for calendar events with similar title and close time
        # (within 24 hours of email received time)
        if not email.received_at:
            return None

        time_window_start = email.received_at - timedelta(days=1)
        time_window_end = email.received_at + timedelta(days=7)

        # Search for events with similar subject
        title_pattern = f"%{email.subject[:50]}%"

        result = await db.execute(
            select(CalendarEvent).where(
                CalendarEvent.title.like(title_pattern),
                CalendarEvent.start_time >= time_window_start,
                CalendarEvent.start_time <= time_window_end
            ).limit(1)
        )

        return result.scalar_one_or_none()


# Singleton instance
_email_calendar_intelligence = None


def get_email_calendar_intelligence() -> EmailCalendarIntelligence:
    """Get singleton email-calendar intelligence instance.

    Returns:
        EmailCalendarIntelligence instance
    """
    global _email_calendar_intelligence
    if _email_calendar_intelligence is None:
        _email_calendar_intelligence = EmailCalendarIntelligence()
    return _email_calendar_intelligence
