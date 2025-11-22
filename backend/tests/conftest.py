"""
Pytest Configuration and Shared Fixtures - Phase 5

Provides common fixtures and configuration for all tests.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
from typing import List, Dict, Any

# Configure asyncio for pytest
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==============================================================================
# Database Fixtures
# ==============================================================================

@pytest.fixture
def mock_db_session():
    """Mock async database session for testing."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=Mock(
        scalars=Mock(return_value=Mock(all=Mock(return_value=[]))),
        scalar_one_or_none=Mock(return_value=None),
        scalar=Mock(return_value=None)
    ))
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.add = Mock()
    db.delete = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    return db


# ==============================================================================
# Email Test Data Fixtures
# ==============================================================================

@pytest.fixture
def sample_actionable_email():
    """Sample high-confidence actionable email."""
    return {
        "id": "email_actionable_001",
        "subject": "URGENT: Review CRESCO dashboard by Friday",
        "sender": "Alberto Martinez <alberto@cresco.com>",
        "sender_name": "Alberto Martinez",
        "sender_email": "alberto@cresco.com",
        "body": """Hi Jef,

Can you please review the CRESCO dashboard and provide feedback by Friday end of day?
We need to finalize the metrics before the Spain launch.

Thanks,
Alberto""",
        "snippet": "Can you please review the CRESCO dashboard...",
        "received_at": datetime.utcnow(),
        "is_meeting_invite": False,
        "action_phrases": ["review", "provide feedback", "by Friday"],
        "expected_classification": {
            "is_actionable": True,
            "action_type": "task",
            "urgency": "high",
            "confidence_min": 0.8
        }
    }


@pytest.fixture
def sample_meeting_email():
    """Sample meeting invite email."""
    return {
        "id": "email_meeting_001",
        "subject": "Meeting: Spain Launch Planning @ Monday 2pm",
        "sender": "Project Manager <pm@cresco.com>",
        "sender_name": "Project Manager",
        "sender_email": "pm@cresco.com",
        "body": """Please join us Monday at 2pm to discuss Spain launch strategy.

Zoom Link: https://zoom.us/j/123456789

Agenda:
- Review metrics
- Discuss timeline
- Assign action items""",
        "snippet": "Please join us Monday at 2pm...",
        "received_at": datetime.utcnow(),
        "is_meeting_invite": True,
        "action_phrases": ["join", "discuss"],
        "expected_classification": {
            "is_actionable": True,
            "action_type": "meeting_prep",
            "urgency": "medium",
            "confidence_min": 0.5
        }
    }


@pytest.fixture
def sample_newsletter_email():
    """Sample newsletter/automated email."""
    return {
        "id": "email_newsletter_001",
        "subject": "Weekly Product Newsletter",
        "sender": "no-reply@newsletter.com",
        "sender_name": "Newsletter Bot",
        "sender_email": "no-reply@newsletter.com",
        "body": """Here are this week's product updates:

1. New feature launched in beta
2. Bug fixes deployed
3. Performance improvements

Click here to unsubscribe: https://newsletter.example.com/unsubscribe""",
        "snippet": "Here are this week's product updates...",
        "received_at": datetime.utcnow(),
        "is_meeting_invite": False,
        "action_phrases": [],
        "expected_classification": {
            "is_actionable": False,
            "action_type": "automated",
            "urgency": "low",
            "confidence_min": 0.5
        }
    }


@pytest.fixture
def sample_fyi_email():
    """Sample FYI/informational email."""
    return {
        "id": "email_fyi_001",
        "subject": "FYI - Deployment completed successfully",
        "sender": "DevOps <devops@cresco.com>",
        "sender_name": "DevOps",
        "sender_email": "devops@cresco.com",
        "body": "Just letting you know the deployment to production completed successfully. No action needed.",
        "snippet": "Just letting you know...",
        "received_at": datetime.utcnow(),
        "is_meeting_invite": False,
        "action_phrases": [],
        "expected_classification": {
            "is_actionable": False,
            "action_type": "fyi",
            "urgency": "low",
            "confidence_min": 0.5
        }
    }


@pytest.fixture
def sample_ambiguous_email():
    """Sample ambiguous email with medium confidence."""
    return {
        "id": "email_ambiguous_001",
        "subject": "Thoughts on the new design?",
        "sender": "Designer <designer@cresco.com>",
        "sender_name": "Designer",
        "sender_email": "designer@cresco.com",
        "body": "Hey, what do you think about the new design we discussed? Let me know when you can.",
        "snippet": "What do you think about the new design...",
        "received_at": datetime.utcnow(),
        "is_meeting_invite": False,
        "action_phrases": ["let me know"],
        "expected_classification": {
            "is_actionable": True,  # Could be True or False
            "action_type": "task",
            "urgency": "low",
            "confidence_min": 0.4,
            "confidence_max": 0.7
        }
    }


@pytest.fixture
def sample_multi_action_email():
    """Sample email with multiple action items."""
    return {
        "id": "email_multi_001",
        "subject": "Action Items from Meeting",
        "sender": "PM <pm@cresco.com>",
        "sender_name": "PM",
        "sender_email": "pm@cresco.com",
        "body": """Following up from today's meeting:

1. Jef: Update CRESCO dashboard by Friday
2. Jef: Review Moodboard export by Monday
3. Jef: Schedule follow-up with Alberto

Please confirm you've seen this.""",
        "snippet": "Following up from today's meeting...",
        "received_at": datetime.utcnow(),
        "is_meeting_invite": False,
        "action_phrases": ["update", "review", "schedule", "by Friday", "by Monday"],
        "expected_classification": {
            "is_actionable": True,
            "action_type": "task",
            "urgency": "high",
            "confidence_min": 0.85,
            "expected_action_items_count": 3
        }
    }


# ==============================================================================
# Gmail API Mock Fixtures
# ==============================================================================

@pytest.fixture
def mock_gmail_message_list():
    """Mock Gmail API message list response."""
    return [
        {"id": "msg_001", "threadId": "thread_001"},
        {"id": "msg_002", "threadId": "thread_002"},
        {"id": "msg_003", "threadId": "thread_003"}
    ]


@pytest.fixture
def mock_gmail_message_detail():
    """Mock Gmail API message detail response."""
    return {
        "id": "msg_001",
        "threadId": "thread_001",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test Email"},
                {"name": "From", "value": "Test Sender <test@example.com>"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Date", "value": "Mon, 22 Nov 2025 10:00:00 +0000"}
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": "VGhpcyBpcyBhIHRlc3QgZW1haWwgYm9keS4="  # Base64: "This is a test email body."
                    }
                }
            ]
        },
        "snippet": "This is a test email body..."
    }


# ==============================================================================
# Service Mock Fixtures
# ==============================================================================

@pytest.fixture
def mock_gemini_service():
    """Mock Gemini AI service."""
    service = Mock()
    service.generate_content = AsyncMock(return_value="""
ANALYSIS: Test analysis

TASKS:
1. Test task
   PRIORITY: medium
   COMPLEXITY: low
""")
    return service


@pytest.fixture
def mock_calendar_service():
    """Mock Google Calendar service."""
    service = Mock()
    service.create_event = AsyncMock(return_value=Mock(
        id=1,
        google_event_id="cal_event_001",
        summary="Test Event",
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=1, hours=1)
    ))
    service.list_events = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail API service."""
    service = Mock()
    service.list_messages = AsyncMock(return_value=[
        {"id": "msg_001", "threadId": "thread_001"}
    ])
    service.get_message = AsyncMock(return_value={
        "id": "msg_001",
        "threadId": "thread_001",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test"},
                {"name": "From", "value": "test@example.com"},
                {"name": "Date", "value": "Mon, 22 Nov 2025 10:00:00 +0000"}
            ],
            "parts": [{"mimeType": "text/plain", "body": {"data": "VGVzdA=="}}]
        },
        "snippet": "Test..."
    })
    return service


# ==============================================================================
# Entity/Knowledge Graph Fixtures
# ==============================================================================

@pytest.fixture
def sample_entities():
    """Sample extracted entities."""
    return [
        {
            "name": "CRESCO",
            "type": "project",
            "confidence": 0.92,
            "context": "dashboard review"
        },
        {
            "name": "Alberto Martinez",
            "type": "person",
            "confidence": 0.88,
            "context": "email sender"
        },
        {
            "name": "Spain",
            "type": "location",
            "confidence": 0.85,
            "context": "launch location"
        },
        {
            "name": "Friday",
            "type": "deadline",
            "confidence": 0.90,
            "context": "review deadline"
        }
    ]


# ==============================================================================
# Orchestrator State Fixtures
# ==============================================================================

@pytest.fixture
def sample_orchestrator_state():
    """Sample orchestrator state for testing."""
    from agents.orchestrator import OrchestratorState

    return OrchestratorState(
        user_input="Update CRESCO dashboard by Friday",
        session_id="test_session_001",
        user_id=1,
        extracted_entities=[
            {"name": "CRESCO", "type": "project", "confidence": 0.9}
        ],
        reasoning=[],
        current_step="start"
    )


# ==============================================================================
# Test Markers Configuration
# ==============================================================================

def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "e2e: End-to-end integration tests"
    )
    config.addinivalue_line(
        "markers", "evaluation: LLM-as-a-judge evaluation tests"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take longer than 5 seconds"
    )
    config.addinivalue_line(
        "markers", "requires_gmail: Tests that require Gmail API access"
    )
    config.addinivalue_line(
        "markers", "requires_gemini: Tests that require Gemini API access"
    )


# ==============================================================================
# Test Utilities
# ==============================================================================

@pytest.fixture
def assert_email_classification():
    """Helper to assert email classification results."""
    def _assert(classification, expected):
        assert classification.is_actionable == expected["is_actionable"]
        assert classification.action_type == expected["action_type"]
        assert classification.urgency == expected["urgency"]

        if "confidence_min" in expected:
            assert classification.confidence >= expected["confidence_min"]

        if "confidence_max" in expected:
            assert classification.confidence <= expected["confidence_max"]

        if "expected_action_items_count" in expected:
            assert len(classification.key_action_items) >= expected["expected_action_items_count"]

    return _assert


# ==============================================================================
# Cleanup Fixtures
# ==============================================================================

@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Cleanup after each test."""
    yield
    # Cleanup code here if needed
    # e.g., clear caches, close connections, etc.
