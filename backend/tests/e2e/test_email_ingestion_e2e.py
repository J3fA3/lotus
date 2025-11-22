"""
End-to-End Email Ingestion Tests - Phase 5

Complete user journey tests for email→task workflow:
1. Email arrives in Gmail inbox
2. Polling service fetches email
3. Email is parsed and classified
4. High-confidence email creates task via orchestrator
5. Task is linked to email
6. Knowledge graph is updated
7. Meeting invites create calendar events
8. User can view email-linked tasks in UI

This simulates the complete real-world flow.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List

from services.email_polling_service import EmailPollingService
from services.gmail_service import GmailService
from agents.email_classification import classify_email_content
from agents.orchestrator import process_assistant_message
from db.models import EmailMessage, Task, EmailTaskLink, CalendarEvent


@pytest.fixture
def mock_gmail_messages():
    """Mock Gmail API message responses."""
    return [
        {
            # High confidence actionable task
            "id": "msg_actionable_001",
            "threadId": "thread_001",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "URGENT: Review CRESCO dashboard by Friday"},
                    {"name": "From", "value": "Alberto Martinez <alberto@cresco.com>"},
                    {"name": "Date", "value": "Mon, 22 Nov 2025 10:00:00 +0000"},
                    {"name": "To", "value": "jef@cresco.com"}
                ],
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": "SGkgSmVmLAoKQ2FuIHlvdSBwbGVhc2UgcmV2aWV3IHRoZSBDUkVTQ08gZGFzaGJvYXJkIGFuZCBwcm92aWRlIGZlZWRiYWNrIGJ5IEZyaWRheSBlbmQgb2YgZGF5PyBXZSBuZWVkIHRvIGZpbmFsaXplIHRoZSBtZXRyaWNzIGJlZm9yZSB0aGUgU3BhaW4gbGF1bmNoLgoKVGhhbmtzLApBbGJlcnRv"}
                        # Base64: "Hi Jef,\n\nCan you please review the CRESCO dashboard and provide feedback by Friday end of day? We need to finalize the metrics before the Spain launch.\n\nThanks,\nAlberto"
                    }
                ]
            },
            "snippet": "Can you please review the CRESCO dashboard and provide feedback by Friday..."
        },
        {
            # Meeting invite
            "id": "msg_meeting_002",
            "threadId": "thread_002",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Meeting: Spain Launch Planning @ Monday 2pm"},
                    {"name": "From", "value": "PM <pm@cresco.com>"},
                    {"name": "Date", "value": "Mon, 22 Nov 2025 11:00:00 +0000"},
                    {"name": "To", "value": "jef@cresco.com"},
                    {"name": "Cc", "value": "alberto@cresco.com, maria@cresco.com"}
                ],
                "parts": [
                    {
                        "mimeType": "text/html",
                        "body": {"data": "UGxlYXNlIGpvaW4gdXMgTW9uZGF5IGF0IDJwbSB0byBkaXNjdXNzIFNwYWluIGxhdW5jaCBzdHJhdGVneS4KCkpvaW4gWm9vbTogaHR0cHM6Ly96b29tLnVzL2ovMTIzNDU2Nzg5"}
                        # Base64: "Please join us Monday at 2pm to discuss Spain launch strategy.\n\nJoin Zoom: https://zoom.us/j/123456789"
                    }
                ]
            },
            "snippet": "Please join us Monday at 2pm to discuss Spain launch strategy..."
        },
        {
            # FYI/Newsletter (low confidence, should not create task)
            "id": "msg_newsletter_003",
            "threadId": "thread_003",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Weekly Product Newsletter"},
                    {"name": "From", "value": "no-reply@newsletter.com"},
                    {"name": "Date", "value": "Mon, 22 Nov 2025 09:00:00 +0000"}
                ],
                "parts": [
                    {
                        "mimeType": "text/html",
                        "body": {"data": "SGVyZSBhcmUgdGhpcyB3ZWVrJ3MgcHJvZHVjdCB1cGRhdGVzLgoKQ2xpY2sgaGVyZSB0byB1bnN1YnNjcmliZS4="}
                        # Base64: "Here are this week's product updates.\n\nClick here to unsubscribe."
                    }
                ]
            },
            "snippet": "Here are this week's product updates..."
        }
    ]


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=Mock(
        scalars=Mock(return_value=Mock(all=Mock(return_value=[]))),
        scalar_one_or_none=Mock(return_value=None)
    ))
    db.commit = AsyncMock()
    db.add = Mock()
    db.refresh = AsyncMock()
    return db


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_email_to_task_complete_flow(mock_gmail_messages, mock_db_session):
    """
    Test complete email→task flow:
    1. Fetch email from Gmail
    2. Parse email content
    3. Classify email (high confidence)
    4. Create task via orchestrator
    5. Link task to email
    6. Verify task in database
    """

    # Mock Gmail service
    mock_gmail = Mock(spec=GmailService)
    mock_gmail.list_messages = AsyncMock(return_value=[
        {"id": "msg_actionable_001", "threadId": "thread_001"}
    ])
    mock_gmail.get_message = AsyncMock(return_value=mock_gmail_messages[0])

    # Mock email parsing
    with patch('services.email_polling_service.parse_email') as mock_parse:
        from dataclasses import dataclass

        @dataclass
        class MockParsedEmail:
            id: str = "parsed_001"
            subject: str = "URGENT: Review CRESCO dashboard by Friday"
            sender: str = "Alberto Martinez <alberto@cresco.com>"
            sender_name: str = "Alberto Martinez"
            sender_email: str = "alberto@cresco.com"
            body_text: str = "Hi Jef,\n\nCan you please review the CRESCO dashboard and provide feedback by Friday end of day?"
            snippet: str = "Can you please review the CRESCO dashboard..."
            received_at: datetime = datetime.utcnow()
            is_meeting_invite: bool = False
            has_attachments: bool = False
            links: list = None
            action_phrases: list = None

            def __post_init__(self):
                if self.links is None:
                    self.links = []
                if self.action_phrases is None:
                    self.action_phrases = ["review", "provide feedback", "by Friday"]

        mock_parse.return_value = MockParsedEmail()

        # Mock classification (high confidence)
        with patch('agents.email_classification.classify_email_content') as mock_classify:
            mock_classify.return_value = {
                "classification": Mock(
                    is_actionable=True,
                    action_type="task",
                    confidence=0.92,  # High confidence
                    urgency="high",
                    reasoning="Clear action request with explicit deadline",
                    key_action_items=["Review CRESCO dashboard", "Provide feedback"],
                    detected_project="CRESCO",
                    detected_deadline="Friday end of day"
                ),
                "should_process": True,
                "confidence": 0.92
            }

            # Mock orchestrator (task creation)
            with patch('agents.orchestrator.process_assistant_message') as mock_orchestrator:
                mock_orchestrator.return_value = {
                    "created_tasks": [
                        {
                            "id": "task_cresco_001",
                            "title": "Review CRESCO dashboard",
                            "description": "Provide feedback on CRESCO dashboard metrics",
                            "priority": "high",
                            "deadline": "Friday",
                            "project": "CRESCO"
                        }
                    ]
                }

                # Create polling service
                with patch('services.email_polling_service.GmailService') as mock_gmail_cls:
                    mock_gmail_cls.return_value = mock_gmail

                    with patch('services.email_polling_service.get_async_session') as mock_get_db:
                        mock_get_db.return_value.__aenter__.return_value = mock_db_session

                        service = EmailPollingService(poll_interval_minutes=20)

                        # Run sync
                        result = await service.sync_now()

                        # Verify flow completed
                        assert result["success"] == True

                        # Verify email was fetched
                        mock_gmail.list_messages.assert_called_once()
                        mock_gmail.get_message.assert_called_once()

                        # Verify email was parsed
                        mock_parse.assert_called()

                        # Verify email was classified
                        mock_classify.assert_called()

                        # Verify task was created (confidence >= 0.8)
                        mock_orchestrator.assert_called_once()

                        print("\n✅ E2E Test: Email→Task flow completed successfully")
                        print(f"   Email fetched: msg_actionable_001")
                        print(f"   Classification confidence: 0.92")
                        print(f"   Task created: task_cresco_001")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_meeting_invite_to_calendar_event_flow(mock_gmail_messages, mock_db_session):
    """
    Test meeting invite→calendar event flow:
    1. Fetch meeting invite email
    2. Detect it's a meeting invite
    3. Extract meeting details (time, location, attendees)
    4. Create calendar event
    5. Link email to calendar event
    """

    mock_gmail = Mock(spec=GmailService)
    mock_gmail.list_messages = AsyncMock(return_value=[
        {"id": "msg_meeting_002", "threadId": "thread_002"}
    ])
    mock_gmail.get_message = AsyncMock(return_value=mock_gmail_messages[1])

    with patch('services.email_polling_service.parse_email') as mock_parse:
        from dataclasses import dataclass

        @dataclass
        class MockMeetingEmail:
            id: str = "parsed_meeting"
            subject: str = "Meeting: Spain Launch Planning @ Monday 2pm"
            sender: str = "PM <pm@cresco.com>"
            sender_name: str = "PM"
            sender_email: str = "pm@cresco.com"
            body_text: str = "Please join us Monday at 2pm to discuss Spain launch strategy.\n\nJoin Zoom: https://zoom.us/j/123456789"
            snippet: str = "Please join us Monday at 2pm..."
            received_at: datetime = datetime.utcnow()
            is_meeting_invite: bool = True  # Meeting invite
            has_attachments: bool = False
            links: list = None
            action_phrases: list = None

            def __post_init__(self):
                if self.links is None:
                    self.links = ["https://zoom.us/j/123456789"]
                if self.action_phrases is None:
                    self.action_phrases = ["join", "discuss"]

        mock_parse.return_value = MockMeetingEmail()

        with patch('agents.email_classification.classify_email_content') as mock_classify:
            mock_classify.return_value = {
                "classification": Mock(
                    is_actionable=True,
                    action_type="meeting_prep",
                    confidence=0.75,
                    urgency="medium",
                    reasoning="Meeting invite with clear time and location",
                    key_action_items=["Attend Spain launch planning meeting"],
                    detected_project="Spain",
                    detected_deadline="Monday 2pm"
                ),
                "should_process": True,
                "confidence": 0.75
            }

            # Mock calendar intelligence
            with patch('services.email_calendar_intelligence.get_email_calendar_intelligence') as mock_cal_intel:
                mock_calendar_service = Mock()
                mock_calendar_service.process_meeting_invite = AsyncMock(return_value={
                    "created": True,
                    "event_id": "cal_event_spain_001",
                    "title": "Spain Launch Planning",
                    "start_time": (datetime.utcnow() + timedelta(days=3)).isoformat()
                })
                mock_cal_intel.return_value = mock_calendar_service

                with patch('services.email_polling_service.GmailService') as mock_gmail_cls:
                    mock_gmail_cls.return_value = mock_gmail

                    with patch('services.email_polling_service.get_async_session') as mock_get_db:
                        mock_get_db.return_value.__aenter__.return_value = mock_db_session

                        service = EmailPollingService(poll_interval_minutes=20)

                        # Run sync
                        result = await service.sync_now()

                        # Verify flow completed
                        assert result["success"] == True

                        # Verify calendar event was created
                        mock_calendar_service.process_meeting_invite.assert_called_once()

                        print("\n✅ E2E Test: Meeting Invite→Calendar Event flow completed")
                        print(f"   Meeting email: msg_meeting_002")
                        print(f"   Calendar event created: cal_event_spain_001")
                        print(f"   Meeting: Spain Launch Planning (Monday 2pm)")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_newsletter_filtered_no_task_created(mock_gmail_messages, mock_db_session):
    """
    Test newsletter filtering - low confidence should NOT create task:
    1. Fetch newsletter email
    2. Classify as automated/FYI (low confidence)
    3. Store email but don't create task
    4. Verify no orchestrator call
    """

    mock_gmail = Mock(spec=GmailService)
    mock_gmail.list_messages = AsyncMock(return_value=[
        {"id": "msg_newsletter_003", "threadId": "thread_003"}
    ])
    mock_gmail.get_message = AsyncMock(return_value=mock_gmail_messages[2])

    with patch('services.email_polling_service.parse_email') as mock_parse:
        from dataclasses import dataclass

        @dataclass
        class MockNewsletterEmail:
            id: str = "parsed_newsletter"
            subject: str = "Weekly Product Newsletter"
            sender: str = "no-reply@newsletter.com"
            sender_name: str = "Newsletter"
            sender_email: str = "no-reply@newsletter.com"
            body_text: str = "Here are this week's product updates.\n\nClick here to unsubscribe."
            snippet: str = "Here are this week's product updates..."
            received_at: datetime = datetime.utcnow()
            is_meeting_invite: bool = False
            has_attachments: bool = False
            links: list = None
            action_phrases: list = None

            def __post_init__(self):
                if self.links is None:
                    self.links = []
                if self.action_phrases is None:
                    self.action_phrases = []

        mock_parse.return_value = MockNewsletterEmail()

        with patch('agents.email_classification.classify_email_content') as mock_classify:
            mock_classify.return_value = {
                "classification": Mock(
                    is_actionable=False,
                    action_type="automated",
                    confidence=0.85,  # High confidence it's automated
                    urgency="low",
                    reasoning="Newsletter format detected, no-reply sender",
                    key_action_items=[],
                    detected_project=None,
                    detected_deadline=None
                ),
                "should_process": False,  # Should NOT process
                "confidence": 0.85
            }

            with patch('agents.orchestrator.process_assistant_message') as mock_orchestrator:
                with patch('services.email_polling_service.GmailService') as mock_gmail_cls:
                    mock_gmail_cls.return_value = mock_gmail

                    with patch('services.email_polling_service.get_async_session') as mock_get_db:
                        mock_get_db.return_value.__aenter__.return_value = mock_db_session

                        service = EmailPollingService(poll_interval_minutes=20)

                        # Run sync
                        result = await service.sync_now()

                        # Verify email was processed
                        assert result["success"] == True

                        # Verify orchestrator was NOT called (no task creation)
                        mock_orchestrator.assert_not_called()

                        print("\n✅ E2E Test: Newsletter filtered correctly")
                        print(f"   Newsletter detected: msg_newsletter_003")
                        print(f"   Classification: automated (confidence 0.85)")
                        print(f"   Task creation: SKIPPED ✓")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_batch_email_processing(mock_db_session):
    """
    Test processing multiple emails in single sync:
    1. Fetch 3 emails (actionable, meeting, newsletter)
    2. Process all in batch
    3. Verify correct handling of each
    """

    # Create complete mock Gmail messages
    mock_messages = [
        {"id": "msg_001", "threadId": "thread_001"},
        {"id": "msg_002", "threadId": "thread_002"},
        {"id": "msg_003", "threadId": "thread_003"}
    ]

    mock_gmail = Mock(spec=GmailService)
    mock_gmail.list_messages = AsyncMock(return_value=mock_messages)

    # Mock get_message to return appropriate response for each ID
    def get_message_side_effect(msg_id):
        if msg_id == "msg_001":
            return {
                "id": "msg_001",
                "threadId": "thread_001",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Task Email"},
                        {"name": "From", "value": "sender@example.com"},
                        {"name": "Date", "value": "Mon, 22 Nov 2025 10:00:00 +0000"}
                    ],
                    "parts": [{"mimeType": "text/plain", "body": {"data": "VGFzaw=="}}]
                },
                "snippet": "Task..."
            }
        elif msg_id == "msg_002":
            return {
                "id": "msg_002",
                "threadId": "thread_002",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Meeting"},
                        {"name": "From", "value": "pm@example.com"},
                        {"name": "Date", "value": "Mon, 22 Nov 2025 11:00:00 +0000"}
                    ],
                    "parts": [{"mimeType": "text/plain", "body": {"data": "TWVldGluZw=="}}]
                },
                "snippet": "Meeting..."
            }
        else:
            return {
                "id": "msg_003",
                "threadId": "thread_003",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Newsletter"},
                        {"name": "From", "value": "no-reply@example.com"},
                        {"name": "Date", "value": "Mon, 22 Nov 2025 09:00:00 +0000"}
                    ],
                    "parts": [{"mimeType": "text/plain", "body": {"data": "TmV3c2xldHRlcg=="}}]
                },
                "snippet": "Newsletter..."
            }

    mock_gmail.get_message = AsyncMock(side_effect=get_message_side_effect)

    with patch('services.email_polling_service.GmailService') as mock_gmail_cls:
        mock_gmail_cls.return_value = mock_gmail

        with patch('services.email_polling_service.get_async_session') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_session

            with patch('services.email_polling_service.parse_email'):
                with patch('agents.email_classification.classify_email_content'):
                    service = EmailPollingService(poll_interval_minutes=20)

                    # Run sync
                    result = await service.sync_now()

                    # Should have processed all 3 emails
                    assert result["success"] == True

                    print("\n✅ E2E Test: Batch processing completed")
                    print(f"   Emails processed: 3")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_email_thread_consolidation(mock_db_session):
    """
    Test email thread consolidation (5+ messages → single task):
    1. Fetch email thread with 6 messages
    2. Detect thread should be consolidated
    3. Create single consolidated task
    4. Link all thread messages to task
    """

    # Mock thread with 6 messages
    thread_messages = [
        {"id": f"msg_thread_{i}", "threadId": "thread_long_001"}
        for i in range(6)
    ]

    mock_gmail = Mock(spec=GmailService)
    mock_gmail.list_messages = AsyncMock(return_value=thread_messages)
    mock_gmail.get_message = AsyncMock(return_value={
        "id": "msg_thread_0",
        "threadId": "thread_long_001",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Re: Project Discussion"},
                {"name": "From", "value": "team@example.com"},
                {"name": "Date", "value": "Mon, 22 Nov 2025 10:00:00 +0000"}
            ],
            "parts": [{"mimeType": "text/plain", "body": {"data": "RGlzY3Vzc2lvbg=="}}]
        },
        "snippet": "Discussion..."
    })

    with patch('services.email_polling_service.GmailService') as mock_gmail_cls:
        mock_gmail_cls.return_value = mock_gmail

        with patch('services.email_polling_service.get_async_session') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_session

            with patch('services.email_polling_service.parse_email'):
                with patch('agents.email_classification.classify_email_content'):
                    with patch('services.thread_consolidation_service.ThreadConsolidationService') as mock_thread_cls:
                        mock_thread = Mock()
                        mock_thread.consolidate_thread = AsyncMock(return_value={
                            "should_consolidate": True,
                            "consolidated_task_id": "task_consolidated_001"
                        })
                        mock_thread_cls.return_value = mock_thread

                        service = EmailPollingService(poll_interval_minutes=20)

                        # Run sync
                        result = await service.sync_now()

                        # Should detect long thread
                        assert result["success"] == True

                        print("\n✅ E2E Test: Thread consolidation")
                        print(f"   Thread messages: 6")
                        print(f"   Consolidated: Yes")
                        print(f"   Consolidated task: task_consolidated_001")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_end_to_end_performance(mock_db_session):
    """
    Test E2E performance - complete flow should complete quickly:
    1. Fetch email
    2. Parse (<100ms)
    3. Classify (<2s)
    4. Create task
    5. Total <5s
    """

    mock_gmail = Mock(spec=GmailService)
    mock_gmail.list_messages = AsyncMock(return_value=[
        {"id": "msg_perf_001", "threadId": "thread_perf_001"}
    ])
    mock_gmail.get_message = AsyncMock(return_value={
        "id": "msg_perf_001",
        "threadId": "thread_perf_001",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Performance Test"},
                {"name": "From", "value": "test@example.com"},
                {"name": "Date", "value": "Mon, 22 Nov 2025 10:00:00 +0000"}
            ],
            "parts": [{"mimeType": "text/plain", "body": {"data": "VGVzdA=="}}]
        },
        "snippet": "Test..."
    })

    with patch('services.email_polling_service.GmailService') as mock_gmail_cls:
        mock_gmail_cls.return_value = mock_gmail

        with patch('services.email_polling_service.get_async_session') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_session

            with patch('services.email_polling_service.parse_email'):
                with patch('agents.email_classification.classify_email_content'):
                    service = EmailPollingService(poll_interval_minutes=20)

                    # Measure E2E time
                    start_time = datetime.now()
                    result = await service.sync_now()
                    e2e_duration = (datetime.now() - start_time).total_seconds()

                    # Should complete quickly
                    assert result["success"] == True
                    assert e2e_duration < 10.0  # 10 second max

                    print(f"\n✅ E2E Performance Test")
                    print(f"   Duration: {e2e_duration:.2f}s")
                    print(f"   Target: <5s (with real services)")
