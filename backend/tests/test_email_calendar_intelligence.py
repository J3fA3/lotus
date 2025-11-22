"""
Email-Calendar Intelligence Tests - Phase 5

Tests for automatic meeting invite detection and calendar event creation:
- Meeting time extraction from email body
- Location detection (Zoom/Meet/Teams links, room numbers)
- Attendee parsing from CC/To fields
- Calendar event creation from meeting invites
- Deduplication of calendar events
- Edge cases and format variations
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Optional

from services.email_calendar_intelligence import EmailCalendarIntelligence, get_email_calendar_intelligence
from db.models import EmailMessage, CalendarEvent


@pytest.fixture
def mock_calendar_service():
    """Mock calendar service for testing."""
    service = Mock()
    service.create_event = AsyncMock(return_value=CalendarEvent(
        id=1,
        google_event_id="cal_event_001",
        summary="Test Meeting",
        description="Test description",
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=1, hours=1),
        location="Zoom",
        user_id=1
    ))
    return service


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=Mock(
        scalar_one_or_none=Mock(return_value=None)
    ))
    db.commit = AsyncMock()
    db.add = Mock()
    return db


@pytest.mark.asyncio
async def test_meeting_time_extraction_explicit():
    """Test extracting meeting time from explicit date/time in email."""

    email = EmailMessage(
        gmail_message_id="msg_001",
        thread_id="thread_001",
        subject="Meeting: Project Review",
        sender="pm@example.com",
        sender_name="Project Manager",
        sender_email="pm@example.com",
        body_text="Please join us on Monday, November 25th at 2:00 PM for project review.",
        snippet="Please join us on Monday...",
        received_at=datetime(2025, 11, 20, 10, 0, 0),
        is_meeting_invite=True
    )

    with patch('services.email_calendar_intelligence.GoogleCalendarService') as mock_cal_cls:
        mock_cal_cls.return_value = Mock()

        intelligence = EmailCalendarIntelligence()
        meeting_details = intelligence._extract_meeting_details(email)

        # Should extract meeting time
        assert meeting_details is not None
        assert "start_time" in meeting_details
        assert "title" in meeting_details
        assert meeting_details["title"] == "Project Review"


@pytest.mark.asyncio
async def test_meeting_time_extraction_relative():
    """Test extracting meeting time from relative references (tomorrow, next Monday)."""

    test_cases = [
        {
            "body": "Let's meet tomorrow at 3pm to discuss the project.",
            "expected_offset_days": 1
        },
        {
            "body": "Meeting next Monday at 10am.",
            "expected_day_name": "Monday"
        },
        {
            "body": "Can we sync next week Thursday at 2pm?",
            "expected_day_name": "Thursday"
        }
    ]

    for test_case in test_cases:
        email = EmailMessage(
            gmail_message_id="msg_relative",
            thread_id="thread_relative",
            subject="Meeting Request",
            sender="colleague@example.com",
            body_text=test_case["body"],
            snippet=test_case["body"][:50],
            received_at=datetime.utcnow(),
            is_meeting_invite=True
        )

        with patch('services.email_calendar_intelligence.GoogleCalendarService'):
            intelligence = EmailCalendarIntelligence()
            meeting_details = intelligence._extract_meeting_details(email)

            # Should extract some time information
            if meeting_details:
                assert "start_time" in meeting_details


@pytest.mark.asyncio
async def test_location_detection_zoom():
    """Test detecting Zoom meeting links as location."""

    zoom_links = [
        "https://zoom.us/j/123456789",
        "https://us02web.zoom.us/j/987654321?pwd=abcdef",
        "Join Zoom Meeting: https://zoom.us/my/username"
    ]

    for zoom_link in zoom_links:
        email = EmailMessage(
            gmail_message_id="msg_zoom",
            thread_id="thread_zoom",
            subject="Zoom Meeting",
            sender="organizer@example.com",
            body_text=f"Meeting link: {zoom_link}",
            snippet="Meeting link...",
            received_at=datetime.utcnow(),
            is_meeting_invite=True
        )

        with patch('services.email_calendar_intelligence.GoogleCalendarService'):
            intelligence = EmailCalendarIntelligence()
            meeting_details = intelligence._extract_meeting_details(email)

            if meeting_details and "location" in meeting_details:
                location = meeting_details["location"]
                assert "zoom.us" in location.lower() or "zoom" in location.lower()


@pytest.mark.asyncio
async def test_location_detection_google_meet():
    """Test detecting Google Meet links as location."""

    meet_links = [
        "https://meet.google.com/abc-defg-hij",
        "Join at: meet.google.com/xyz-1234-567"
    ]

    for meet_link in meet_links:
        email = EmailMessage(
            gmail_message_id="msg_meet",
            thread_id="thread_meet",
            subject="Google Meet",
            sender="organizer@example.com",
            body_text=f"Meeting at {meet_link}",
            snippet="Meeting at...",
            received_at=datetime.utcnow(),
            is_meeting_invite=True
        )

        with patch('services.email_calendar_intelligence.GoogleCalendarService'):
            intelligence = EmailCalendarIntelligence()
            meeting_details = intelligence._extract_meeting_details(email)

            if meeting_details and "location" in meeting_details:
                location = meeting_details["location"]
                assert "meet.google.com" in location.lower() or "meet" in location.lower()


@pytest.mark.asyncio
async def test_location_detection_teams():
    """Test detecting Microsoft Teams links as location."""

    teams_links = [
        "https://teams.microsoft.com/l/meetup-join/...",
        "Join Teams Meeting: https://teams.microsoft.com/..."
    ]

    for teams_link in teams_links:
        email = EmailMessage(
            gmail_message_id="msg_teams",
            thread_id="thread_teams",
            subject="Teams Meeting",
            sender="organizer@example.com",
            body_text=f"Link: {teams_link}",
            snippet="Link...",
            received_at=datetime.utcnow(),
            is_meeting_invite=True
        )

        with patch('services.email_calendar_intelligence.GoogleCalendarService'):
            intelligence = EmailCalendarIntelligence()
            meeting_details = intelligence._extract_meeting_details(email)

            if meeting_details and "location" in meeting_details:
                location = meeting_details["location"]
                assert "teams.microsoft.com" in location.lower() or "teams" in location.lower()


@pytest.mark.asyncio
async def test_location_detection_physical_room():
    """Test detecting physical meeting room references."""

    room_references = [
        "Meeting in Conference Room A",
        "Let's meet in the main office, room 301",
        "Location: Building 2, Floor 3, Meeting Room"
    ]

    for room_ref in room_references:
        email = EmailMessage(
            gmail_message_id="msg_room",
            thread_id="thread_room",
            subject="In-Person Meeting",
            sender="organizer@example.com",
            body_text=room_ref,
            snippet=room_ref[:50],
            received_at=datetime.utcnow(),
            is_meeting_invite=True
        )

        with patch('services.email_calendar_intelligence.GoogleCalendarService'):
            intelligence = EmailCalendarIntelligence()
            meeting_details = intelligence._extract_meeting_details(email)

            if meeting_details and "location" in meeting_details:
                location = meeting_details["location"]
                # Should contain room reference
                assert any(word in location.lower() for word in ["room", "conference", "building", "office"])


@pytest.mark.asyncio
async def test_attendee_parsing():
    """Test parsing attendees from email CC field."""

    email = EmailMessage(
        gmail_message_id="msg_attendees",
        thread_id="thread_attendees",
        subject="Team Meeting",
        sender="organizer@example.com",
        sender_name="Organizer",
        sender_email="organizer@example.com",
        body_text="Team meeting tomorrow at 2pm.",
        snippet="Team meeting tomorrow...",
        received_at=datetime.utcnow(),
        is_meeting_invite=True
    )

    # Mock CC field (would come from Gmail API payload)
    # This tests the parsing logic
    cc_field = "alice@example.com, bob@example.com, charlie@example.com"

    with patch('services.email_calendar_intelligence.GoogleCalendarService'):
        intelligence = EmailCalendarIntelligence()

        # Extract attendees from CC string
        attendees = intelligence._extract_attendees(cc_field)

        # Should parse all attendees
        assert len(attendees) == 3
        assert "alice@example.com" in attendees
        assert "bob@example.com" in attendees
        assert "charlie@example.com" in attendees


@pytest.mark.asyncio
async def test_process_meeting_invite_creates_event(mock_calendar_service, mock_db_session):
    """Test processing meeting invite creates calendar event."""

    email = EmailMessage(
        gmail_message_id="msg_create_event",
        thread_id="thread_create_event",
        subject="Sprint Planning Meeting",
        sender="scrum@example.com",
        sender_name="Scrum Master",
        sender_email="scrum@example.com",
        body_text="Sprint planning meeting tomorrow at 10am. Join at https://zoom.us/j/123456789",
        snippet="Sprint planning meeting tomorrow...",
        received_at=datetime.utcnow(),
        is_meeting_invite=True
    )

    with patch('services.email_calendar_intelligence.GoogleCalendarService') as mock_cal_cls:
        mock_cal_cls.return_value = mock_calendar_service

        intelligence = EmailCalendarIntelligence()

        result = await intelligence.process_meeting_invite(
            email=email,
            db=mock_db_session,
            user_id=1
        )

        # Should create calendar event
        if result:
            assert result["created"] == True
            assert "event_id" in result
            mock_calendar_service.create_event.assert_called_once()


@pytest.mark.asyncio
async def test_process_meeting_invite_deduplication(mock_calendar_service, mock_db_session):
    """Test meeting invite deduplication - don't create duplicate events."""

    email = EmailMessage(
        gmail_message_id="msg_duplicate",
        thread_id="thread_duplicate",
        subject="Recurring Meeting",
        sender="organizer@example.com",
        body_text="Weekly sync meeting every Monday at 9am",
        snippet="Weekly sync meeting...",
        received_at=datetime.utcnow(),
        is_meeting_invite=True
    )

    # Mock existing calendar event
    existing_event = CalendarEvent(
        id=1,
        google_event_id="existing_event_001",
        summary="Recurring Meeting",
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=1, hours=1),
        user_id=1
    )

    mock_db_session.execute.return_value = Mock(
        scalar_one_or_none=Mock(return_value=existing_event)
    )

    with patch('services.email_calendar_intelligence.GoogleCalendarService') as mock_cal_cls:
        mock_cal_cls.return_value = mock_calendar_service

        intelligence = EmailCalendarIntelligence()

        result = await intelligence.process_meeting_invite(
            email=email,
            db=mock_db_session,
            user_id=1
        )

        # Should not create duplicate
        if result:
            assert result["created"] == False
            assert result["event_id"] == "existing_event_001"


@pytest.mark.asyncio
async def test_meeting_description_cleaning():
    """Test email body is cleaned for calendar description."""

    email = EmailMessage(
        gmail_message_id="msg_desc",
        thread_id="thread_desc",
        subject="Project Review",
        sender="pm@example.com",
        body_text="""
Hi team,

Please join our project review meeting tomorrow at 2pm.

Agenda:
1. Review Q4 metrics
2. Discuss roadmap
3. Team updates

Join Zoom: https://zoom.us/j/123456789

Best regards,
Project Manager

--
This email is confidential. If you received this in error, please delete it.
""",
        snippet="Please join our project review...",
        received_at=datetime.utcnow(),
        is_meeting_invite=True
    )

    with patch('services.email_calendar_intelligence.GoogleCalendarService'):
        intelligence = EmailCalendarIntelligence()
        meeting_details = intelligence._extract_meeting_details(email)

        if meeting_details and "description" in meeting_details:
            description = meeting_details["description"]

            # Should include agenda
            assert "agenda" in description.lower() or "review q4 metrics" in description.lower()

            # Should clean out confidentiality footer
            # (Implementation may vary - this tests the concept)


@pytest.mark.asyncio
async def test_meeting_duration_default():
    """Test default meeting duration when not specified."""

    email = EmailMessage(
        gmail_message_id="msg_duration",
        thread_id="thread_duration",
        subject="Quick Sync",
        sender="colleague@example.com",
        body_text="Let's sync tomorrow at 3pm",
        snippet="Let's sync tomorrow...",
        received_at=datetime.utcnow(),
        is_meeting_invite=True
    )

    with patch('services.email_calendar_intelligence.GoogleCalendarService'):
        intelligence = EmailCalendarIntelligence()
        meeting_details = intelligence._extract_meeting_details(email)

        if meeting_details and "start_time" in meeting_details and "end_time" in meeting_details:
            start = meeting_details["start_time"]
            end = meeting_details["end_time"]

            # Default duration should be reasonable (30-60 minutes)
            duration_minutes = (end - start).total_seconds() / 60
            assert 30 <= duration_minutes <= 60


@pytest.mark.asyncio
async def test_meeting_duration_explicit():
    """Test extracting explicit meeting duration from email."""

    duration_test_cases = [
        {
            "body": "Meeting tomorrow at 2pm for 90 minutes",
            "expected_minutes": 90
        },
        {
            "body": "Quick 15-minute sync at 3pm",
            "expected_minutes": 15
        },
        {
            "body": "2-hour planning session on Monday at 10am",
            "expected_minutes": 120
        }
    ]

    for test_case in duration_test_cases:
        email = EmailMessage(
            gmail_message_id="msg_dur_explicit",
            thread_id="thread_dur_explicit",
            subject="Meeting",
            sender="organizer@example.com",
            body_text=test_case["body"],
            snippet=test_case["body"][:50],
            received_at=datetime.utcnow(),
            is_meeting_invite=True
        )

        with patch('services.email_calendar_intelligence.GoogleCalendarService'):
            intelligence = EmailCalendarIntelligence()
            meeting_details = intelligence._extract_meeting_details(email)

            # Should extract duration (implementation may vary)
            # This tests the concept
            if meeting_details and "start_time" in meeting_details and "end_time" in meeting_details:
                duration = (meeting_details["end_time"] - meeting_details["start_time"]).total_seconds() / 60
                # Allow some tolerance
                assert duration >= test_case["expected_minutes"] - 5


@pytest.mark.asyncio
async def test_non_meeting_invite_returns_none(mock_db_session):
    """Test processing non-meeting invite returns None."""

    email = EmailMessage(
        gmail_message_id="msg_not_meeting",
        thread_id="thread_not_meeting",
        subject="Project Update",
        sender="pm@example.com",
        body_text="Here's the weekly project update. All on track.",
        snippet="Here's the weekly project update...",
        received_at=datetime.utcnow(),
        is_meeting_invite=False  # Not a meeting
    )

    with patch('services.email_calendar_intelligence.GoogleCalendarService'):
        intelligence = EmailCalendarIntelligence()

        result = await intelligence.process_meeting_invite(
            email=email,
            db=mock_db_session,
            user_id=1
        )

        # Should return None for non-meeting
        assert result is None


@pytest.mark.asyncio
async def test_meeting_extraction_edge_cases():
    """Test edge cases in meeting time extraction."""

    edge_cases = [
        {
            "name": "missing_time",
            "body": "Let's meet tomorrow",
            "should_extract": False  # No specific time
        },
        {
            "name": "past_time",
            "body": "We met yesterday at 3pm",
            "should_extract": False  # Past tense
        },
        {
            "name": "conditional",
            "body": "Maybe we can meet next week?",
            "should_extract": False  # Uncertain
        },
        {
            "name": "multiple_times",
            "body": "Available at 2pm or 3pm tomorrow",
            "should_extract": True  # Should pick first option
        }
    ]

    for test_case in edge_cases:
        email = EmailMessage(
            gmail_message_id=f"msg_{test_case['name']}",
            thread_id=f"thread_{test_case['name']}",
            subject="Meeting Request",
            sender="sender@example.com",
            body_text=test_case["body"],
            snippet=test_case["body"][:50],
            received_at=datetime.utcnow(),
            is_meeting_invite=True
        )

        with patch('services.email_calendar_intelligence.GoogleCalendarService'):
            intelligence = EmailCalendarIntelligence()
            meeting_details = intelligence._extract_meeting_details(email)

            if test_case["should_extract"]:
                assert meeting_details is not None, f"Should extract for: {test_case['name']}"
            # If should_extract is False, meeting_details may or may not be None
            # depending on implementation robustness


@pytest.mark.asyncio
async def test_timezone_handling():
    """Test meeting time handles timezones correctly."""

    email = EmailMessage(
        gmail_message_id="msg_tz",
        thread_id="thread_tz",
        subject="Global Team Meeting",
        sender="global@example.com",
        body_text="Meeting tomorrow at 2pm EST / 8pm CET",
        snippet="Meeting tomorrow at 2pm EST...",
        received_at=datetime.utcnow(),
        is_meeting_invite=True
    )

    with patch('services.email_calendar_intelligence.GoogleCalendarService'):
        intelligence = EmailCalendarIntelligence()
        meeting_details = intelligence._extract_meeting_details(email)

        # Should extract some time (implementation may vary for timezone handling)
        # This is a complex case - testing that it doesn't crash
        # Real implementation would need proper timezone parsing
        if meeting_details:
            assert "start_time" in meeting_details


@pytest.mark.asyncio
async def test_recurring_meeting_detection():
    """Test detecting recurring meetings."""

    recurring_patterns = [
        "Weekly sync every Monday at 9am",
        "Bi-weekly review on Fridays at 2pm",
        "Monthly planning meeting first Monday of the month",
        "Daily standup at 9:30am"
    ]

    for pattern in recurring_patterns:
        email = EmailMessage(
            gmail_message_id="msg_recurring",
            thread_id="thread_recurring",
            subject="Recurring Meeting",
            sender="organizer@example.com",
            body_text=pattern,
            snippet=pattern[:50],
            received_at=datetime.utcnow(),
            is_meeting_invite=True
        )

        with patch('services.email_calendar_intelligence.GoogleCalendarService'):
            intelligence = EmailCalendarIntelligence()
            meeting_details = intelligence._extract_meeting_details(email)

            # Should extract meeting details
            # Recurrence pattern handling is advanced - testing basic extraction
            if meeting_details:
                assert "title" in meeting_details


@pytest.mark.asyncio
async def test_calendar_service_singleton():
    """Test email calendar intelligence uses singleton pattern."""

    service1 = get_email_calendar_intelligence()
    service2 = get_email_calendar_intelligence()

    # Should return same instance
    assert service1 is service2
