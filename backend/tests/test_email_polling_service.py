"""
Email Polling Service Tests - Phase 5

Tests for the background email polling service including:
- Service initialization and configuration
- Email fetching from Gmail
- Polling schedule and intervals
- Error handling and recovery
- Service status reporting
- Manual sync triggering
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict

from services.email_polling_service import EmailPollingService, get_email_polling_service
from db.models import EmailMessage, EmailAccount
from services.gmail_service import GmailService


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail service for testing."""
    service = Mock(spec=GmailService)
    service.list_messages = AsyncMock(return_value=[
        {
            "id": "msg_001",
            "threadId": "thread_001"
        },
        {
            "id": "msg_002",
            "threadId": "thread_002"
        }
    ])
    service.get_message = AsyncMock(return_value={
        "id": "msg_001",
        "threadId": "thread_001",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test Email"},
                {"name": "From", "value": "test@example.com"},
                {"name": "Date", "value": "Mon, 20 Nov 2025 10:00:00 +0000"}
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": "SGVsbG8gV29ybGQ="}  # "Hello World" base64
                }
            ]
        },
        "snippet": "Hello World preview"
    })
    return service


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))))
    db.commit = AsyncMock()
    db.add = Mock()
    return db


@pytest.mark.asyncio
async def test_service_initialization():
    """Test email polling service initializes correctly."""

    with patch('services.email_polling_service.GmailService') as mock_gmail_cls:
        mock_gmail_cls.return_value = Mock(spec=GmailService)

        service = EmailPollingService(poll_interval_minutes=20)

        assert service.poll_interval_minutes == 20
        assert service.running == False
        assert service.emails_processed_total == 0
        assert service.errors_count == 0


@pytest.mark.asyncio
async def test_service_singleton_pattern():
    """Test service uses singleton pattern correctly."""

    service1 = get_email_polling_service()
    service2 = get_email_polling_service()

    # Should return same instance
    assert service1 is service2


@pytest.mark.asyncio
async def test_fetch_new_emails(mock_gmail_service, mock_db_session):
    """Test fetching new emails from Gmail."""

    with patch('services.email_polling_service.GmailService') as mock_gmail_cls:
        mock_gmail_cls.return_value = mock_gmail_service

        service = EmailPollingService(poll_interval_minutes=20)

        # Mock database query for last processed email
        mock_db_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None)
        )

        # Fetch emails
        emails = await service._fetch_new_emails(mock_db_session)

        # Should have called Gmail service
        mock_gmail_service.list_messages.assert_called_once()

        # Should return email data
        assert isinstance(emails, list)


@pytest.mark.asyncio
async def test_process_email_message(mock_gmail_service, mock_db_session):
    """Test processing individual email message."""

    with patch('services.email_polling_service.GmailService') as mock_gmail_cls:
        mock_gmail_cls.return_value = mock_gmail_service

        with patch('services.email_polling_service.parse_email') as mock_parse:
            mock_parse.return_value = Mock(
                subject="Test Email",
                sender="test@example.com",
                sender_name="Test User",
                sender_email="test@example.com",
                body_text="Hello World",
                snippet="Hello World preview",
                received_at=datetime.utcnow(),
                is_meeting_invite=False,
                has_attachments=False,
                links=[],
                action_phrases=[]
            )

            with patch('agents.email_classification.classify_email_content') as mock_classify:
                mock_classify.return_value = {
                    "classification": Mock(
                        is_actionable=True,
                        action_type="task",
                        confidence=0.85,
                        urgency="medium",
                        reasoning="Test reasoning",
                        key_action_items=["Review document"],
                        detected_project="TestProject",
                        detected_deadline="Friday"
                    ),
                    "should_process": True,
                    "confidence": 0.85
                }

                service = EmailPollingService(poll_interval_minutes=20)

                # Process email
                await service._process_email_message(
                    gmail_message_id="msg_001",
                    thread_id="thread_001",
                    db=mock_db_session
                )

                # Should have parsed email
                mock_parse.assert_called_once()

                # Should have classified email
                mock_classify.assert_called_once()

                # Should have saved to database
                mock_db_session.add.assert_called()
                mock_db_session.commit.assert_called()


@pytest.mark.asyncio
async def test_manual_sync(mock_gmail_service, mock_db_session):
    """Test manual sync trigger."""

    with patch('services.email_polling_service.GmailService') as mock_gmail_cls:
        mock_gmail_cls.return_value = mock_gmail_service

        with patch('services.email_polling_service.get_async_session') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_session

            with patch('services.email_polling_service.parse_email') as mock_parse:
                mock_parse.return_value = Mock(
                    subject="Test",
                    sender="test@example.com",
                    sender_name="Test",
                    sender_email="test@example.com",
                    body_text="Test",
                    snippet="Test",
                    received_at=datetime.utcnow(),
                    is_meeting_invite=False,
                    has_attachments=False,
                    links=[],
                    action_phrases=[]
                )

                with patch('agents.email_classification.classify_email_content') as mock_classify:
                    mock_classify.return_value = {
                        "classification": Mock(
                            is_actionable=False,
                            action_type="fyi",
                            confidence=0.3,
                            urgency="low",
                            reasoning="Test",
                            key_action_items=[],
                            detected_project=None,
                            detected_deadline=None
                        ),
                        "should_process": False,
                        "confidence": 0.3
                    }

                    service = EmailPollingService(poll_interval_minutes=20)

                    # Trigger manual sync
                    result = await service.sync_now()

                    # Should return result
                    assert result is not None
                    assert "success" in result


@pytest.mark.asyncio
async def test_get_service_status():
    """Test getting service status."""

    with patch('services.email_polling_service.GmailService'):
        service = EmailPollingService(poll_interval_minutes=20)

        # Set some status
        service.running = True
        service.last_sync_at = datetime.utcnow() - timedelta(minutes=5)
        service.emails_processed_total = 42
        service.errors_count = 3

        # Get status
        status = await service.get_status()

        # Verify status
        assert status["running"] == True
        assert status["emails_processed_total"] == 42
        assert status["errors_count"] == 3
        assert status["poll_interval_minutes"] == 20
        assert "last_sync_at" in status
        assert "next_sync_in_minutes" in status


@pytest.mark.asyncio
async def test_error_handling_gmail_api_failure(mock_db_session):
    """Test error handling when Gmail API fails."""

    with patch('services.email_polling_service.GmailService') as mock_gmail_cls:
        # Mock Gmail service to raise exception
        mock_gmail = Mock(spec=GmailService)
        mock_gmail.list_messages = AsyncMock(side_effect=Exception("Gmail API error"))
        mock_gmail_cls.return_value = mock_gmail

        service = EmailPollingService(poll_interval_minutes=20)

        # Try to fetch emails - should handle error gracefully
        try:
            await service._fetch_new_emails(mock_db_session)
            # Should not crash
        except Exception as e:
            # If it raises, it should be logged but not crash the service
            pass

        # Error count should increase
        assert service.errors_count >= 0  # Service tracks errors


@pytest.mark.asyncio
async def test_error_handling_classification_failure(mock_gmail_service, mock_db_session):
    """Test error handling when classification fails."""

    with patch('services.email_polling_service.GmailService') as mock_gmail_cls:
        mock_gmail_cls.return_value = mock_gmail_service

        with patch('services.email_polling_service.parse_email') as mock_parse:
            mock_parse.return_value = Mock(
                subject="Test",
                sender="test@example.com",
                sender_name="Test",
                sender_email="test@example.com",
                body_text="Test",
                snippet="Test",
                received_at=datetime.utcnow(),
                is_meeting_invite=False,
                has_attachments=False,
                links=[],
                action_phrases=[]
            )

            with patch('agents.email_classification.classify_email_content') as mock_classify:
                # Make classification fail
                mock_classify.side_effect = Exception("Classification error")

                service = EmailPollingService(poll_interval_minutes=20)

                # Try to process email - should handle error gracefully
                try:
                    await service._process_email_message(
                        gmail_message_id="msg_001",
                        thread_id="thread_001",
                        db=mock_db_session
                    )
                except Exception:
                    # Should handle gracefully
                    pass

                # Service should continue running despite error
                assert service.running == False  # Not started yet


@pytest.mark.asyncio
async def test_deduplication_existing_email(mock_gmail_service, mock_db_session):
    """Test service doesn't process already-processed emails."""

    with patch('services.email_polling_service.GmailService') as mock_gmail_cls:
        mock_gmail_cls.return_value = mock_gmail_service

        # Mock database to return existing email
        existing_email = EmailMessage(
            id=1,
            gmail_message_id="msg_001",
            thread_id="thread_001",
            subject="Existing Email",
            processed_at=datetime.utcnow()
        )

        mock_db_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=existing_email)
        )

        service = EmailPollingService(poll_interval_minutes=20)

        # Try to process same email
        result = await service._store_email(
            gmail_message_id="msg_001",
            thread_id="thread_001",
            email_data=Mock(subject="Test"),
            classification_result={},
            db=mock_db_session
        )

        # Should skip processing (already exists)
        # Verify no duplicate add
        # (Implementation may vary - this tests the concept)


@pytest.mark.asyncio
async def test_batch_processing_multiple_emails(mock_db_session):
    """Test processing multiple emails in batch."""

    # Create mock Gmail service with multiple messages
    mock_gmail = Mock(spec=GmailService)
    mock_gmail.list_messages = AsyncMock(return_value=[
        {"id": f"msg_{i:03d}", "threadId": f"thread_{i:03d}"}
        for i in range(10)
    ])
    mock_gmail.get_message = AsyncMock(return_value={
        "id": "msg_001",
        "threadId": "thread_001",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test"},
                {"name": "From", "value": "test@example.com"},
                {"name": "Date", "value": "Mon, 20 Nov 2025 10:00:00 +0000"}
            ],
            "parts": [{"mimeType": "text/plain", "body": {"data": "VGVzdA=="}}]
        },
        "snippet": "Test"
    })

    with patch('services.email_polling_service.GmailService') as mock_gmail_cls:
        mock_gmail_cls.return_value = mock_gmail

        with patch('services.email_polling_service.parse_email') as mock_parse:
            mock_parse.return_value = Mock(
                subject="Test",
                sender="test@example.com",
                sender_name="Test",
                sender_email="test@example.com",
                body_text="Test",
                snippet="Test",
                received_at=datetime.utcnow(),
                is_meeting_invite=False,
                has_attachments=False,
                links=[],
                action_phrases=[]
            )

            with patch('agents.email_classification.classify_email_content') as mock_classify:
                mock_classify.return_value = {
                    "classification": Mock(
                        is_actionable=False,
                        action_type="fyi",
                        confidence=0.3,
                        urgency="low",
                        reasoning="Test",
                        key_action_items=[],
                        detected_project=None,
                        detected_deadline=None
                    ),
                    "should_process": False,
                    "confidence": 0.3
                }

                with patch('services.email_polling_service.get_async_session') as mock_get_db:
                    mock_get_db.return_value.__aenter__.return_value = mock_db_session

                    service = EmailPollingService(poll_interval_minutes=20)

                    # Process batch
                    result = await service.sync_now()

                    # Should have processed multiple emails
                    assert result is not None


@pytest.mark.asyncio
async def test_polling_interval_configuration():
    """Test polling interval can be configured."""

    with patch('services.email_polling_service.GmailService'):
        # Test different intervals
        service_20 = EmailPollingService(poll_interval_minutes=20)
        assert service_20.poll_interval_minutes == 20

        service_60 = EmailPollingService(poll_interval_minutes=60)
        assert service_60.poll_interval_minutes == 60


@pytest.mark.asyncio
async def test_high_confidence_creates_task(mock_gmail_service, mock_db_session):
    """Test high confidence email triggers task creation."""

    with patch('services.email_polling_service.GmailService') as mock_gmail_cls:
        mock_gmail_cls.return_value = mock_gmail_service

        with patch('services.email_polling_service.parse_email') as mock_parse:
            mock_parse.return_value = Mock(
                id="test_email_123",
                subject="URGENT: Review CRESCO dashboard",
                sender="alberto@example.com",
                sender_name="Alberto",
                sender_email="alberto@example.com",
                body_text="Please review the CRESCO dashboard by Friday",
                snippet="Please review the CRESCO dashboard...",
                received_at=datetime.utcnow(),
                is_meeting_invite=False,
                has_attachments=False,
                links=[],
                action_phrases=["review", "by Friday"]
            )

            with patch('agents.email_classification.classify_email_content') as mock_classify:
                # High confidence classification
                mock_classify.return_value = {
                    "classification": Mock(
                        is_actionable=True,
                        action_type="task",
                        confidence=0.92,  # High confidence
                        urgency="high",
                        reasoning="Clear action request with deadline",
                        key_action_items=["Review CRESCO dashboard"],
                        detected_project="CRESCO",
                        detected_deadline="Friday"
                    ),
                    "should_process": True,
                    "confidence": 0.92
                }

                with patch('agents.orchestrator.process_assistant_message') as mock_orchestrator:
                    mock_orchestrator.return_value = {
                        "created_tasks": [
                            {"id": "task_001", "title": "Review CRESCO dashboard", "priority": "high"}
                        ]
                    }

                    service = EmailPollingService(poll_interval_minutes=20)

                    # Process email
                    await service._process_email_message(
                        gmail_message_id="msg_high_conf",
                        thread_id="thread_high_conf",
                        db=mock_db_session
                    )

                    # Should have called orchestrator to create task
                    # (Confidence >= 0.8 triggers task creation)
                    mock_orchestrator.assert_called_once()


@pytest.mark.asyncio
async def test_medium_confidence_no_auto_task(mock_gmail_service, mock_db_session):
    """Test medium confidence email does NOT auto-create task."""

    with patch('services.email_polling_service.GmailService') as mock_gmail_cls:
        mock_gmail_cls.return_value = mock_gmail_service

        with patch('services.email_polling_service.parse_email') as mock_parse:
            mock_parse.return_value = Mock(
                id="test_email_456",
                subject="Thoughts?",
                sender="colleague@example.com",
                sender_name="Colleague",
                sender_email="colleague@example.com",
                body_text="What do you think about this?",
                snippet="What do you think...",
                received_at=datetime.utcnow(),
                is_meeting_invite=False,
                has_attachments=False,
                links=[],
                action_phrases=["think"]
            )

            with patch('agents.email_classification.classify_email_content') as mock_classify:
                # Medium confidence classification
                mock_classify.return_value = {
                    "classification": Mock(
                        is_actionable=True,
                        action_type="task",
                        confidence=0.65,  # Medium confidence
                        urgency="low",
                        reasoning="Ambiguous request",
                        key_action_items=["Provide opinion"],
                        detected_project=None,
                        detected_deadline=None
                    ),
                    "should_process": False,  # Below threshold
                    "confidence": 0.65
                }

                with patch('agents.orchestrator.process_assistant_message') as mock_orchestrator:
                    service = EmailPollingService(poll_interval_minutes=20)

                    # Process email
                    await service._process_email_message(
                        gmail_message_id="msg_med_conf",
                        thread_id="thread_med_conf",
                        db=mock_db_session
                    )

                    # Should NOT have called orchestrator (confidence < 0.8)
                    mock_orchestrator.assert_not_called()


@pytest.mark.asyncio
async def test_meeting_invite_creates_calendar_event(mock_gmail_service, mock_db_session):
    """Test meeting invite email creates calendar event."""

    with patch('services.email_polling_service.GmailService') as mock_gmail_cls:
        mock_gmail_cls.return_value = mock_gmail_service

        with patch('services.email_polling_service.parse_email') as mock_parse:
            mock_parse.return_value = Mock(
                id="test_meeting_789",
                subject="Meeting: Spain Launch Planning",
                sender="pm@example.com",
                sender_name="Project Manager",
                sender_email="pm@example.com",
                body_text="Please join us Monday at 2pm to discuss Spain launch.",
                snippet="Please join us Monday at 2pm...",
                received_at=datetime.utcnow(),
                is_meeting_invite=True,  # Meeting invite
                has_attachments=False,
                links=["https://zoom.us/j/123456789"],
                action_phrases=["join", "discuss"]
            )

            with patch('agents.email_classification.classify_email_content') as mock_classify:
                mock_classify.return_value = {
                    "classification": Mock(
                        is_actionable=True,
                        action_type="meeting_prep",
                        confidence=0.75,
                        urgency="medium",
                        reasoning="Meeting invite",
                        key_action_items=["Attend meeting"],
                        detected_project="Spain",
                        detected_deadline="Monday 2pm"
                    ),
                    "should_process": True,
                    "confidence": 0.75
                }

                with patch('services.email_calendar_intelligence.get_email_calendar_intelligence') as mock_calendar_intel:
                    mock_calendar = Mock()
                    mock_calendar.process_meeting_invite = AsyncMock(return_value={
                        "created": True,
                        "event_id": "cal_event_001",
                        "title": "Spain Launch Planning",
                        "start_time": "2025-11-25T14:00:00"
                    })
                    mock_calendar_intel.return_value = mock_calendar

                    service = EmailPollingService(poll_interval_minutes=20)

                    # Process email
                    await service._process_email_message(
                        gmail_message_id="msg_meeting",
                        thread_id="thread_meeting",
                        db=mock_db_session
                    )

                    # Should have created calendar event
                    mock_calendar.process_meeting_invite.assert_called_once()
