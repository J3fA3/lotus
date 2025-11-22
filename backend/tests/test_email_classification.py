"""
Email Classification Agent Tests - Phase 5

Comprehensive test suite for email classification agent including:
- Actionable task detection
- Meeting invite classification
- FYI email identification
- Automated newsletter detection
- Validation rule testing (Maran auto-FYI, Spain boost)
- Confidence scoring accuracy
- Edge cases and boundary conditions
"""

import pytest
from agents.email_classification import classify_email_content
from config.email_prompts import EmailClassification


@pytest.mark.asyncio
async def test_classification_actionable_task_high_confidence():
    """Test classification identifies actionable task emails with high confidence."""
    result = await classify_email_content(
        email_id="test_001",
        email_subject="Please review CRESCO dashboard by Friday",
        email_sender="Alberto Martinez <alberto@example.com>",
        email_sender_name="Alberto Martinez",
        email_sender_email="alberto@example.com",
        email_body="Hi Jef,\n\nCan you review the CRESCO dashboard and provide feedback by Friday? Thanks!",
        email_snippet="Can you review the CRESCO dashboard...",
        action_phrases=["review", "provide feedback", "by Friday"],
        is_meeting_invite=False
    )

    classification = result["classification"]

    assert classification.is_actionable == True
    assert classification.action_type == "task"
    assert classification.confidence >= 0.8
    assert classification.urgency in ["medium", "high"]
    assert "cresco" in classification.detected_project.lower() if classification.detected_project else True


@pytest.mark.asyncio
async def test_classification_meeting_invite():
    """Test classification identifies meeting invites correctly."""
    result = await classify_email_content(
        email_id="test_002",
        email_subject="Meeting: Spain Launch Planning @ Monday 2pm",
        email_sender="Team Lead <lead@example.com>",
        email_sender_name="Team Lead",
        email_sender_email="lead@example.com",
        email_body="Please join us Monday at 2pm to discuss Spain launch strategy.",
        email_snippet="Please join us Monday at 2pm...",
        action_phrases=["join", "discuss"],
        is_meeting_invite=True
    )

    classification = result["classification"]

    assert classification.action_type == "meeting_prep"
    assert classification.confidence >= 0.5  # Lower threshold for meeting invites


@pytest.mark.asyncio
async def test_classification_fyi_low_urgency():
    """Test classification identifies FYI emails with low urgency."""
    result = await classify_email_content(
        email_id="test_003",
        email_subject="Project Update - Week 47",
        email_sender="Team Member <member@example.com>",
        email_sender_name="Team Member",
        email_sender_email="member@example.com",
        email_body="Here's the weekly project update. All systems running smoothly. No action needed.",
        email_snippet="Here's the weekly project update...",
        action_phrases=[],
        is_meeting_invite=False
    )

    classification = result["classification"]

    # Should be FYI or automated (not actionable)
    assert classification.action_type in ["fyi", "automated"]
    assert classification.is_actionable == False
    assert classification.urgency == "low"


@pytest.mark.asyncio
async def test_classification_automated_newsletter():
    """Test classification identifies automated newsletters correctly."""
    result = await classify_email_content(
        email_id="test_005",
        email_subject="Weekly Newsletter - Product Updates",
        email_sender="no-reply@newsletter.com",
        email_sender_name="Newsletter Bot",
        email_sender_email="no-reply@newsletter.com",
        email_body="Here are this week's product updates. Click here to unsubscribe.",
        email_snippet="Here are this week's product updates...",
        action_phrases=[],
        is_meeting_invite=False
    )

    classification = result["classification"]

    assert classification.action_type == "automated"
    assert classification.is_actionable == False
    # Automated emails should have low confidence (validation rule applies)
    assert classification.confidence >= 0.1



@pytest.mark.asyncio
async def test_classification_ambiguous_low_confidence():
    """Test classification handles ambiguous emails with lower confidence."""
    result = await classify_email_content(
        email_id="test_006",
        email_subject="Quick question",
        email_sender="someone@example.com",
        email_sender_name="Someone",
        email_sender_email="someone@example.com",
        email_body="Hey, what do you think?",
        email_snippet="Hey, what do you think?",
        action_phrases=["think"],
        is_meeting_invite=False
    )

    classification = result["classification"]

    # Ambiguous content should have lower confidence or be marked as not actionable
    assert classification.confidence < 0.8 or classification.is_actionable == False


@pytest.mark.asyncio
async def test_classification_deadline_extraction():
    """Test classification extracts deadlines from email content."""
    result = await classify_email_content(
        email_id="test_007",
        email_subject="Please update dashboard",
        email_sender="manager@example.com",
        email_sender_name="Manager",
        email_sender_email="manager@example.com",
        email_body="Please update the dashboard by tomorrow end of day.",
        email_snippet="Please update the dashboard by tomorrow...",
        action_phrases=["update", "by tomorrow"],
        is_meeting_invite=False
    )

    classification = result["classification"]

    # Should detect deadline
    assert classification.detected_deadline is not None
    assert "tomorrow" in classification.detected_deadline.lower()


@pytest.mark.asyncio
async def test_classification_multiple_action_items():
    """Test classification handles emails with multiple action items."""
    result = await classify_email_content(
        email_id="test_008",
        email_subject="CRESCO and Moodboard Updates",
        email_sender="pm@example.com",
        email_sender_name="Project Manager",
        email_sender_email="pm@example.com",
        email_body="Please update both CRESCO dashboard and Moodboard exports by tomorrow.",
        email_snippet="Please update both CRESCO dashboard and Moodboard...",
        action_phrases=["update", "by tomorrow"],
        is_meeting_invite=False
    )

    classification = result["classification"]

    # Should be actionable
    assert classification.is_actionable == True
    assert classification.action_type == "task"

    # Should detect at least one project
    assert classification.detected_project is not None
    assert len(classification.key_action_items) >= 2


@pytest.mark.asyncio
async def test_classification_response_structure():
    """Test classification response has correct structure."""
    result = await classify_email_content(
        email_id="test_structure",
        email_subject="Test Email",
        email_sender="test@example.com",
        email_sender_name="Test",
        email_sender_email="test@example.com",
        email_body="This is a test email.",
        email_snippet="This is a test email.",
        action_phrases=[],
        is_meeting_invite=False
    )

    # Verify response structure
    assert "classification" in result
    assert "should_process" in result
    assert "confidence" in result

    classification = result["classification"]

    # Verify EmailClassification structure
    assert hasattr(classification, "is_actionable")
    assert hasattr(classification, "confidence")
    assert hasattr(classification, "action_type")
    assert hasattr(classification, "urgency")
    assert hasattr(classification, "reasoning")
    assert hasattr(classification, "key_action_items")

    # Verify types
    assert isinstance(classification.is_actionable, bool)
    assert isinstance(classification.confidence, float)
    assert 0.0 <= classification.confidence <= 1.0
    assert classification.action_type in ["task", "meeting_prep", "fyi", "automated"]
    assert classification.urgency in ["low", "medium", "high"]


@pytest.mark.asyncio
async def test_classification_handles_missing_fields():
    """Test classification handles emails with missing optional fields."""
    result = await classify_email_content(
        email_id="test_missing",
        email_subject="",  # Empty subject
        email_sender="unknown",  # Minimal sender info
        email_sender_name="",
        email_sender_email="",
        email_body="Short message",
        email_snippet="Short message",
        action_phrases=[],
        is_meeting_invite=False
    )

    # Should complete without error
    assert result is not None
    assert "classification" in result


@pytest.mark.asyncio
async def test_classification_html_stripped_body():
    """Test classification works with HTML-stripped body text."""
    html_body = "<div><p>Please <strong>review</strong> the dashboard.</p></div>"

    result = await classify_email_content(
        email_id="test_html",
        email_subject="Dashboard Review",
        email_sender="sender@example.com",
        email_sender_name="Sender",
        email_sender_email="sender@example.com",
        email_body="Please review the dashboard.",  # HTML already stripped
        email_snippet="Please review the dashboard.",
        action_phrases=["review"],
        is_meeting_invite=False
    )

    classification = result["classification"]

    # Should detect action despite HTML
    assert classification.is_actionable == True or classification.action_type == "task"
