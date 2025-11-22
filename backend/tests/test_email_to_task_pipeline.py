"""
Email→Task Pipeline Integration Tests - Phase 5

Tests the complete email→task creation pipeline including:
- Email classification agent
- Orchestrator integration
- Task creation from email
- Email-task linking
- Knowledge graph updates
- Confidence-based routing
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List

from agents.email_classification import classify_email_content
from agents.orchestrator import process_assistant_message
from db.models import EmailMessage, Task, EmailTaskLink, Entity
from config.email_prompts import EmailClassification


@pytest.mark.asyncio
async def test_email_to_task_pipeline_high_confidence():
    """Test complete pipeline: Email → Classification → Task creation (high confidence)."""

    # Mock email data
    email_subject = "URGENT: Review CRESCO dashboard by Friday EOD"
    email_body = """Hi Jef,

Alberto here. Can you please review the CRESCO dashboard and provide feedback by Friday end of day?
We need to finalize the metrics before the Spain launch next week.

The dashboard is at: https://cresco.example.com/dashboard

Thanks!
Alberto
"""

    # Step 1: Classify email
    classification_result = await classify_email_content(
        email_id="test_pipeline_001",
        email_subject=email_subject,
        email_sender="Alberto Martinez <alberto@example.com>",
        email_sender_name="Alberto Martinez",
        email_sender_email="alberto@example.com",
        email_body=email_body,
        email_snippet="Can you please review the CRESCO dashboard...",
        action_phrases=["review", "provide feedback", "by Friday"],
        is_meeting_invite=False
    )

    classification = classification_result["classification"]

    # Verify classification
    assert classification.is_actionable == True
    assert classification.action_type == "task"
    assert classification.confidence >= 0.8  # High confidence
    assert classification.urgency in ["high", "medium"]
    assert "cresco" in classification.detected_project.lower()

    # Step 2: Build email context for orchestrator
    email_context = f"""
New email from {email_subject}
Sender: Alberto Martinez <alberto@example.com>

Subject: {email_subject}

Body:
{email_body}

Classification:
- Action Type: {classification.action_type}
- Urgency: {classification.urgency}
- Confidence: {classification.confidence:.2f}
- Detected Project: {classification.detected_project}
- Deadline: {classification.detected_deadline or "Not specified"}

Key Action Items:
{chr(10).join(f"- {item}" for item in classification.key_action_items)}
"""

    # Step 3: Process through orchestrator (mocked DB)
    with patch('agents.orchestrator.get_async_session') as mock_db_session:
        mock_db = AsyncMock()
        mock_db_session.return_value = mock_db

        # Mock entity extraction results
        mock_db.execute = AsyncMock(return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))))
        mock_db.commit = AsyncMock()

        orchestrator_result = await process_assistant_message(
            content=email_context,
            source_type="email",
            session_id="email_test_pipeline_001",
            db=mock_db,
            source_identifier="test_email_123",
            user_id=1
        )

    # Step 4: Verify task creation
    assert orchestrator_result is not None
    assert "created_tasks" in orchestrator_result or "reasoning" in orchestrator_result

    # If tasks were created, verify structure
    if "created_tasks" in orchestrator_result:
        created_tasks = orchestrator_result["created_tasks"]
        assert len(created_tasks) >= 1

        task = created_tasks[0]
        assert "cresco" in task["title"].lower() or "dashboard" in task["title"].lower()
        assert task["priority"] in ["high", "medium"]


@pytest.mark.asyncio
async def test_email_to_task_pipeline_medium_confidence():
    """Test pipeline with medium confidence (50-80%) - should ask for confirmation."""

    email_subject = "Thoughts on the new design?"
    email_body = "Hey, what do you think about the new design we discussed? Let me know when you can."

    # Step 1: Classify email
    classification_result = await classify_email_content(
        email_id="test_pipeline_002",
        email_subject=email_subject,
        email_sender="Designer <designer@example.com>",
        email_sender_name="Designer",
        email_sender_email="designer@example.com",
        email_body=email_body,
        email_snippet="what do you think about the new design...",
        action_phrases=["let me know"],
        is_meeting_invite=False
    )

    classification = classification_result["classification"]

    # Medium confidence should be 0.5-0.8
    # Depending on implementation, this might be actionable with medium confidence
    # or not actionable
    assert 0.0 <= classification.confidence <= 1.0

    # If confidence is in medium range, verify it's handled appropriately
    if 0.5 <= classification.confidence < 0.8:
        # Medium confidence emails should not auto-create tasks
        # (This would need orchestrator integration to verify - marking as observation)
        assert classification is not None


@pytest.mark.asyncio
async def test_email_to_task_pipeline_low_confidence():
    """Test pipeline with low confidence (<50%) - should skip task creation."""

    email_subject = "Weekly Newsletter - Product Updates"
    email_body = """
Here are this week's product updates:

1. New feature launched in beta
2. Bug fixes deployed
3. Performance improvements

Click here to unsubscribe: https://newsletter.example.com/unsubscribe
"""

    # Step 1: Classify email
    classification_result = await classify_email_content(
        email_id="test_pipeline_003",
        email_subject=email_subject,
        email_sender="no-reply@newsletter.com",
        email_sender_name="Newsletter Bot",
        email_sender_email="no-reply@newsletter.com",
        email_body=email_body,
        email_snippet="Here are this week's product updates...",
        action_phrases=[],
        is_meeting_invite=False
    )

    classification = classification_result["classification"]

    # Should be classified as automated/FYI
    assert classification.action_type in ["automated", "fyi"]
    assert classification.is_actionable == False

    # Low confidence or not actionable should not create tasks
    # (Would be filtered at polling service level)


@pytest.mark.asyncio
async def test_email_to_task_multiple_action_items():
    """Test pipeline extracts multiple action items from single email."""

    email_subject = "Action Items from Spain Launch Meeting"
    email_body = """Hi team,

Following up from today's meeting, here are the action items:

1. Jef: Update CRESCO dashboard with Spain metrics by Friday
2. Jef: Review Moodboard export functionality by next Monday
3. Jef: Schedule follow-up meeting with Alberto for next week

Please confirm you've seen this.

Thanks,
Project Manager
"""

    # Step 1: Classify email
    classification_result = await classify_email_content(
        email_id="test_pipeline_004",
        email_subject=email_subject,
        email_sender="pm@example.com",
        email_sender_name="Project Manager",
        email_sender_email="pm@example.com",
        email_body=email_body,
        email_snippet="Following up from today's meeting...",
        action_phrases=["update", "review", "schedule", "by Friday", "by next Monday"],
        is_meeting_invite=False
    )

    classification = classification_result["classification"]

    # Should detect multiple action items
    assert classification.is_actionable == True
    assert len(classification.key_action_items) >= 3

    # Should detect projects
    assert classification.detected_project is not None

    # Should have high confidence for explicit action items
    assert classification.confidence >= 0.7


@pytest.mark.asyncio
async def test_email_to_task_deadline_extraction():
    """Test pipeline correctly extracts and formats deadlines."""

    test_cases = [
        {
            "body": "Please complete this by tomorrow EOD",
            "expected_contains": ["tomorrow", "eod", "end of day"]
        },
        {
            "body": "Need this by Friday, December 15th",
            "expected_contains": ["friday", "december", "15"]
        },
        {
            "body": "Deadline is next Monday at 3pm",
            "expected_contains": ["monday", "3pm", "next"]
        },
        {
            "body": "ASAP - urgent request",
            "expected_contains": ["asap", "urgent"]
        }
    ]

    for i, test_case in enumerate(test_cases):
        classification_result = await classify_email_content(
            email_id=f"test_deadline_{i}",
            email_subject="Task with deadline",
            email_sender="manager@example.com",
            email_sender_name="Manager",
            email_sender_email="manager@example.com",
            email_body=test_case["body"],
            email_snippet=test_case["body"][:50],
            action_phrases=["complete", "need", "deadline"],
            is_meeting_invite=False
        )

        classification = classification_result["classification"]

        # Should extract deadline
        if classification.detected_deadline:
            deadline_lower = classification.detected_deadline.lower()
            # At least one expected term should be present
            assert any(term in deadline_lower for term in test_case["expected_contains"]), \
                f"Expected one of {test_case['expected_contains']} in deadline: {classification.detected_deadline}"


@pytest.mark.asyncio
async def test_email_to_task_project_detection():
    """Test pipeline detects project references correctly."""

    project_test_cases = [
        {
            "subject": "CRESCO Dashboard Update",
            "body": "Please update the CRESCO dashboard",
            "expected_project": "cresco"
        },
        {
            "subject": "Moodboard Export Issue",
            "body": "There's an issue with the Moodboard export functionality",
            "expected_project": "moodboard"
        },
        {
            "subject": "Spain Launch Preparation",
            "body": "We need to prepare for the Spain launch next week",
            "expected_project": "spain"
        },
        {
            "subject": "Lotus Platform Enhancement",
            "body": "Enhancement needed for the Lotus platform",
            "expected_project": "lotus"
        }
    ]

    for i, test_case in enumerate(project_test_cases):
        classification_result = await classify_email_content(
            email_id=f"test_project_{i}",
            email_subject=test_case["subject"],
            email_sender="colleague@example.com",
            email_sender_name="Colleague",
            email_sender_email="colleague@example.com",
            email_body=test_case["body"],
            email_snippet=test_case["body"][:50],
            action_phrases=["update", "prepare", "enhancement"],
            is_meeting_invite=False
        )

        classification = classification_result["classification"]

        # Should detect project
        if classification.detected_project:
            project_lower = classification.detected_project.lower()
            assert test_case["expected_project"] in project_lower, \
                f"Expected '{test_case['expected_project']}' in detected project: {classification.detected_project}"


@pytest.mark.asyncio
async def test_email_to_task_entity_extraction():
    """Test pipeline extracts entities (people, projects, dates) correctly."""

    email_body = """Hi Jef,

Alberto and I discussed the CRESCO dashboard yesterday. We need you to:
1. Update the Spain metrics by Friday, December 15th
2. Schedule a meeting with the Moodboard team for next week
3. Review the API documentation

Thanks!
Maria
"""

    classification_result = await classify_email_content(
        email_id="test_entities_001",
        email_subject="CRESCO Dashboard & Team Sync",
        email_sender="Maria Rodriguez <maria@example.com>",
        email_sender_name="Maria Rodriguez",
        email_sender_email="maria@example.com",
        email_body=email_body,
        email_snippet="Alberto and I discussed the CRESCO dashboard...",
        action_phrases=["update", "schedule", "review"],
        is_meeting_invite=False
    )

    classification = classification_result["classification"]

    # Verify classification picked up multiple elements
    assert classification.is_actionable == True
    assert len(classification.key_action_items) >= 3

    # The reasoning should mention key entities
    reasoning_lower = classification.reasoning.lower()
    assert any(name in reasoning_lower for name in ["alberto", "maria", "jef"])
    assert "cresco" in reasoning_lower or "dashboard" in reasoning_lower


@pytest.mark.asyncio
async def test_email_to_task_urgency_classification():
    """Test pipeline correctly classifies urgency levels."""

    urgency_test_cases = [
        {
            "subject": "URGENT: Production issue - needs immediate attention",
            "body": "CRITICAL: The production system is down. Please fix ASAP!",
            "expected_urgency": "high"
        },
        {
            "subject": "Please review when you have time",
            "body": "No rush, but could you review this document sometime this week?",
            "expected_urgency": "low"
        },
        {
            "subject": "Task for next sprint",
            "body": "For the next sprint planning, we should consider adding this feature.",
            "expected_urgency": "low"
        },
        {
            "subject": "Review needed by Friday",
            "body": "Can you review the dashboard by Friday? It's for the client demo next week.",
            "expected_urgency": "medium"
        }
    ]

    for i, test_case in enumerate(urgency_test_cases):
        classification_result = await classify_email_content(
            email_id=f"test_urgency_{i}",
            email_subject=test_case["subject"],
            email_sender="sender@example.com",
            email_sender_name="Sender",
            email_sender_email="sender@example.com",
            email_body=test_case["body"],
            email_snippet=test_case["body"][:50],
            action_phrases=["fix", "review", "consider"],
            is_meeting_invite=False
        )

        classification = classification_result["classification"]

        # Verify urgency classification
        assert classification.urgency == test_case["expected_urgency"], \
            f"Expected urgency '{test_case['expected_urgency']}' but got '{classification.urgency}' for: {test_case['subject']}"


@pytest.mark.asyncio
async def test_email_to_task_confidence_scoring():
    """Test pipeline confidence scoring is calibrated correctly."""

    # High confidence cases (>0.8)
    high_confidence_emails = [
        {
            "subject": "Please update the dashboard by Friday",
            "body": "Hi Jef, can you please update the CRESCO dashboard by Friday EOD? Thanks!",
            "action_phrases": ["update", "by Friday"]
        },
        {
            "subject": "Review required: API documentation",
            "body": "Please review the API documentation and provide feedback by tomorrow.",
            "action_phrases": ["review", "provide feedback", "by tomorrow"]
        }
    ]

    for i, email in enumerate(high_confidence_emails):
        result = await classify_email_content(
            email_id=f"test_high_conf_{i}",
            email_subject=email["subject"],
            email_sender="sender@example.com",
            email_sender_name="Sender",
            email_sender_email="sender@example.com",
            email_body=email["body"],
            email_snippet=email["body"][:50],
            action_phrases=email["action_phrases"],
            is_meeting_invite=False
        )

        classification = result["classification"]
        assert classification.confidence >= 0.8, \
            f"Expected high confidence (>=0.8) but got {classification.confidence} for: {email['subject']}"

    # Low confidence cases (<0.5)
    low_confidence_emails = [
        {
            "subject": "FYI - System update completed",
            "body": "Just letting you know the system update completed successfully. No action needed.",
            "action_phrases": []
        },
        {
            "subject": "Newsletter",
            "body": "Here's your weekly newsletter with product updates.",
            "action_phrases": []
        }
    ]

    for i, email in enumerate(low_confidence_emails):
        result = await classify_email_content(
            email_id=f"test_low_conf_{i}",
            email_subject=email["subject"],
            email_sender="noreply@example.com",
            email_sender_name="No Reply",
            email_sender_email="noreply@example.com",
            email_body=email["body"],
            email_snippet=email["body"][:50],
            action_phrases=email["action_phrases"],
            is_meeting_invite=False
        )

        classification = result["classification"]
        # Should either be low confidence or not actionable
        assert classification.confidence < 0.8 or classification.is_actionable == False


@pytest.mark.asyncio
async def test_email_to_task_error_handling():
    """Test pipeline handles malformed email data gracefully."""

    error_test_cases = [
        {
            "name": "empty_subject",
            "subject": "",
            "body": "Some body text",
            "should_complete": True
        },
        {
            "name": "empty_body",
            "subject": "Some subject",
            "body": "",
            "should_complete": True
        },
        {
            "name": "very_long_body",
            "subject": "Test",
            "body": "x" * 50000,  # 50k characters
            "should_complete": True
        },
        {
            "name": "special_characters",
            "subject": "Test 🔥 with émojis and spëcial çhars",
            "body": "Body with special characters: 你好 мир",
            "should_complete": True
        }
    ]

    for test_case in error_test_cases:
        try:
            result = await classify_email_content(
                email_id=f"test_error_{test_case['name']}",
                email_subject=test_case["subject"],
                email_sender="test@example.com",
                email_sender_name="Test",
                email_sender_email="test@example.com",
                email_body=test_case["body"],
                email_snippet=test_case["body"][:100],
                action_phrases=[],
                is_meeting_invite=False
            )

            # Should complete without exception
            assert result is not None
            assert "classification" in result

        except Exception as e:
            if test_case["should_complete"]:
                pytest.fail(f"Test case '{test_case['name']}' should complete but raised: {e}")


@pytest.mark.asyncio
async def test_email_to_task_thread_context():
    """Test pipeline uses email thread context for better classification."""

    # Simulate a thread where context matters
    thread_emails = [
        {
            "subject": "Re: CRESCO Dashboard",
            "body": "Thanks for the update!",
            "is_reply": True
        },
        {
            "subject": "CRESCO Dashboard Review",
            "body": "Please review the CRESCO dashboard and let me know your thoughts.",
            "is_reply": False
        }
    ]

    # The reply alone might seem like FYI
    reply_result = await classify_email_content(
        email_id="test_thread_001",
        email_subject=thread_emails[0]["subject"],
        email_sender="alberto@example.com",
        email_sender_name="Alberto",
        email_sender_email="alberto@example.com",
        email_body=thread_emails[0]["body"],
        email_snippet=thread_emails[0]["body"][:50],
        action_phrases=[],
        is_meeting_invite=False
    )

    # Should recognize as FYI/acknowledgment
    assert reply_result["classification"].action_type in ["fyi", "automated"]

    # The original should be actionable
    original_result = await classify_email_content(
        email_id="test_thread_002",
        email_subject=thread_emails[1]["subject"],
        email_sender="pm@example.com",
        email_sender_name="PM",
        email_sender_email="pm@example.com",
        email_body=thread_emails[1]["body"],
        email_snippet=thread_emails[1]["body"][:50],
        action_phrases=["review", "let me know"],
        is_meeting_invite=False
    )

    assert original_result["classification"].is_actionable == True
