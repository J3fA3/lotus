# Phase 5: Gmail Integration + Agent Refactoring - Comprehensive Test Plan

**Version:** 1.0
**Date:** November 22, 2025
**Status:** Ready for Execution
**Coverage Target:** 95%+ code coverage, 100% critical path coverage

---

## Table of Contents

1. [Test Strategy Overview](#test-strategy-overview)
2. [Unit Tests](#unit-tests)
3. [Integration Tests](#integration-tests)
4. [End-to-End Tests](#end-to-end-tests)
5. [Agent Evaluation Tests](#agent-evaluation-tests)
6. [Performance Benchmarks](#performance-benchmarks)
7. [Chaos & Resilience Testing](#chaos--resilience-testing)
8. [Security Testing](#security-testing)
9. [Regression Tests](#regression-tests)
10. [Test Data & Fixtures](#test-data--fixtures)
11. [Execution Plan](#execution-plan)

---

## Test Strategy Overview

### Testing Pyramid

```
                    ▲
                   / \
                  /   \
                 /  E2E \
                /       \
               /_________\
              /           \
             / Integration \
            /_______________ \
           /                 \
          /    Unit Tests     \
         /_____________________ \

        Unit: 60% (500+ tests)
  Integration: 30% (150+ tests)
         E2E: 10% (50+ tests)
```

### Test Levels

1. **Unit Tests** (L1) - Individual components in isolation
2. **Integration Tests** (L2) - Component interactions
3. **End-to-End Tests** (L3) - Complete user workflows
4. **Agent Evaluation Tests** (L4) - AI agent quality metrics
5. **Performance Tests** (L5) - Speed, throughput, resource usage
6. **Chaos Tests** (L6) - Failure scenarios, edge cases
7. **Security Tests** (L7) - Authentication, authorization, data protection
8. **Regression Tests** (L8) - Ensure no breaking changes to Phase 1-4

### Success Criteria

- ✅ 95%+ code coverage
- ✅ 100% critical path coverage
- ✅ All E2E scenarios passing
- ✅ Agent evaluation scores >80%
- ✅ Performance targets met
- ✅ Zero P0/P1 security vulnerabilities
- ✅ Zero regressions in Phase 1-4 features

---

## 1. Unit Tests

### 1.1 Gmail Service Tests

**File:** `backend/tests/test_gmail_service.py` (✅ Already created - 429 lines)

**Test Coverage:**
- [x] OAuth authentication flow
- [x] Token refresh on 401 errors
- [x] Retry logic (exponential backoff)
- [x] Rate limiting handling (429 errors)
- [x] Fetch recent emails with pagination
- [x] Mark emails as processed (label management)
- [x] Error handling (network, API errors)
- [x] Mock Gmail API responses

**New Tests to Add:**
```python
async def test_gmail_concurrent_requests():
    """Test Gmail service handles concurrent API requests correctly."""
    # Test parallel email fetching doesn't cause race conditions
    pass

async def test_gmail_quota_exceeded():
    """Test Gmail service handles quota exceeded errors gracefully."""
    # Simulate quota exceeded, verify exponential backoff + alerting
    pass

async def test_gmail_oauth_token_expiry():
    """Test automatic token refresh when expired."""
    # Simulate expired token, verify refresh + retry
    pass

async def test_gmail_partial_batch_failure():
    """Test Gmail service continues on partial batch failures."""
    # Fetch 50 emails, 10 fail, verify 40 processed correctly
    pass
```

**Metrics:**
- Target: 95%+ coverage
- Current: ~85% (needs concurrent + edge case tests)

---

### 1.2 Email Parser Tests

**File:** `backend/tests/test_email_parser.py` (✅ Already created - 471 lines, 100+ tests)

**Test Coverage:**
- [x] HTML to text conversion
- [x] Signature removal (multiple formats)
- [x] Action phrase extraction
- [x] Meeting invite detection
- [x] Link extraction (HTTP/HTTPS/www)
- [x] Email address parsing
- [x] Unicode handling
- [x] Malformed HTML handling

**New Tests to Add:**
```python
def test_parser_nested_html():
    """Test parser handles deeply nested HTML structures."""
    # 10+ levels of div nesting, verify clean text output
    pass

def test_parser_embedded_images():
    """Test parser handles embedded images (data URIs)."""
    # Email with base64 images, verify extracted + cleaned
    pass

def test_parser_calendar_ics_attachment():
    """Test parser detects .ics calendar attachments."""
    # Email with .ics file, verify is_meeting_invite=True
    pass

def test_parser_multilingual_content():
    """Test parser handles multilingual email content."""
    # Email with English + Spanish + Chinese, verify all extracted
    pass

def test_parser_huge_email():
    """Test parser handles extremely large emails (>1MB)."""
    # 1000+ line email, verify performance + truncation
    pass
```

**Metrics:**
- Target: 98%+ coverage
- Current: ~92% (needs edge case + multilingual tests)

---

### 1.3 Email Classification Agent Tests

**File:** `backend/tests/test_email_classification.py` (New)

**Test Coverage:**
```python
import pytest
from agents.email_classification import classify_email_content
from config.email_prompts import EmailClassification

@pytest.mark.asyncio
async def test_classification_actionable_task():
    """Test classification identifies actionable task emails correctly."""
    result = await classify_email_content(
        email_id="test_001",
        email_subject="Please review CRESCO dashboard by Friday",
        email_sender="Alberto Martinez <alberto@example.com>",
        email_sender_name="Alberto Martinez",
        email_sender_email="alberto@example.com",
        email_body="Hi Jef, Can you review the CRESCO dashboard and provide feedback by Friday? Thanks!",
        email_snippet="Can you review the CRESCO dashboard...",
        action_phrases=["review", "provide feedback", "by Friday"],
        is_meeting_invite=False
    )

    classification = result["classification"]

    assert classification.is_actionable == True
    assert classification.action_type == "task"
    assert classification.confidence >= 0.8
    assert classification.urgency in ["medium", "high"]
    assert "friday" in classification.detected_deadline.lower()
    assert "CRESCO" in classification.detected_project

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
    assert classification.confidence >= 0.75
    assert "monday" in classification.detected_deadline.lower()
    assert "2pm" in classification.detected_deadline.lower()

@pytest.mark.asyncio
async def test_classification_fyi_maran():
    """Test classification auto-labels Maran emails as FYI."""
    # Per validation rules: Maran emails should be FYI unless critical
    result = await classify_email_content(
        email_id="test_003",
        email_subject="Project Update - Week 47",
        email_sender="Maran De Ruiter <maran@example.com>",
        email_sender_name="Maran De Ruiter",
        email_sender_email="maran@example.com",
        email_body="Here's the weekly project update. All systems running smoothly.",
        email_snippet="Here's the weekly project update...",
        action_phrases=[],
        is_meeting_invite=False
    )

    classification = result["classification"]

    # Should be FYI unless contains urgent action phrases
    assert classification.action_type in ["fyi", "automated"]
    assert classification.is_actionable == False

@pytest.mark.asyncio
async def test_classification_spain_market_boost():
    """Test classification boosts confidence for Spain market emails."""
    # Per validation rules: Spain is priority market, should boost confidence
    result = await classify_email_content(
        email_id="test_004",
        email_subject="Spain Pharmacy Integration Question",
        email_sender="Partner <partner@pharmacy.es>",
        email_sender_name="Partner",
        email_sender_email="partner@pharmacy.es",
        email_body="We have a question about the integration timeline for Spain.",
        email_snippet="We have a question about the integration...",
        action_phrases=["question", "integration"],
        is_meeting_invite=False
    )

    classification = result["classification"]

    # Spain market should boost confidence
    assert classification.confidence >= 0.7
    assert classification.detected_project == "Spain Pharmacy"

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
    assert classification.confidence >= 0.7

@pytest.mark.asyncio
async def test_classification_ambiguous_email():
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

    # Ambiguous content should have lower confidence
    assert classification.confidence < 0.6
    assert classification.is_actionable == False or classification.confidence < 0.8

@pytest.mark.asyncio
async def test_classification_project_detection():
    """Test classification detects multiple project mentions."""
    result = await classify_email_content(
        email_id="test_007",
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

    # Should detect primary project (first mentioned)
    assert classification.detected_project in ["CRESCO", "Moodboard"]
    assert classification.is_actionable == True
```

**Additional Test Scenarios:**
- Test classification with missing sender information
- Test classification with extremely long email bodies (>10,000 characters)
- Test classification with HTML-only emails (no plain text)
- Test classification response time (<2s per email)
- Test classification batch processing (50 emails concurrently)

**Metrics:**
- Target: 90%+ coverage
- Target: <2s per classification
- Target: >80% accuracy on validation dataset

---

### 1.4 Email Polling Service Tests

**File:** `backend/tests/test_email_polling_service.py` (New)

**Test Coverage:**
```python
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from services.email_polling_service import EmailPollingService

@pytest.mark.asyncio
async def test_polling_service_startup():
    """Test email polling service starts correctly."""
    service = EmailPollingService()

    await service.start()

    assert service._running == True
    assert service._task is not None

    await service.stop()

@pytest.mark.asyncio
async def test_polling_service_graceful_shutdown():
    """Test email polling service shuts down gracefully."""
    service = EmailPollingService()
    await service.start()

    # Let it run briefly
    await asyncio.sleep(0.1)

    # Shutdown
    await service.stop()

    assert service._running == False
    assert service._task.cancelled() or service._task.done()

@pytest.mark.asyncio
async def test_polling_service_sync_now():
    """Test force sync bypasses scheduled polling."""
    service = EmailPollingService()

    with patch.object(service, '_sync_emails') as mock_sync:
        mock_sync.return_value = {
            "emails_processed": 10,
            "errors": [],
            "duration_ms": 500
        }

        result = await service.sync_now()

        assert result["success"] == True
        assert result["emails_processed"] == 10
        mock_sync.assert_called_once()

@pytest.mark.asyncio
async def test_polling_service_error_recovery():
    """Test polling service recovers from sync errors."""
    service = EmailPollingService()

    with patch.object(service, '_sync_emails') as mock_sync:
        # Simulate error on first call, success on second
        mock_sync.side_effect = [
            Exception("Network error"),
            {"emails_processed": 5, "errors": [], "duration_ms": 300}
        ]

        # First sync should fail but not crash
        result1 = await service.sync_now()
        assert result1["success"] == False
        assert service.errors_count == 1

        # Second sync should succeed
        result2 = await service.sync_now()
        assert result2["success"] == True

@pytest.mark.asyncio
async def test_polling_service_status():
    """Test polling service status reporting."""
    service = EmailPollingService()

    status = await service.get_status()

    assert "running" in status
    assert "last_sync_at" in status
    assert "emails_processed_total" in status
    assert "poll_interval_minutes" in status

@pytest.mark.asyncio
async def test_polling_service_concurrent_sync():
    """Test polling service prevents concurrent syncs."""
    service = EmailPollingService()

    # Start two syncs simultaneously
    with patch.object(service, '_sync_emails') as mock_sync:
        mock_sync.return_value = asyncio.sleep(1)  # Slow sync

        sync1 = asyncio.create_task(service.sync_now())
        sync2 = asyncio.create_task(service.sync_now())

        results = await asyncio.gather(sync1, sync2, return_exceptions=True)

        # Should handle gracefully (either sequential or one rejected)
        assert len(results) == 2
```

**Metrics:**
- Target: 85%+ coverage
- Target: Graceful shutdown <1s
- Target: Error recovery working

---

### 1.5 Email-Calendar Intelligence Tests

**File:** `backend/tests/test_email_calendar_intelligence.py` (New)

**Test Coverage:**
```python
import pytest
from datetime import datetime, timedelta
from services.email_calendar_intelligence import EmailCalendarIntelligence
from db.models import EmailMessage

@pytest.mark.asyncio
async def test_meeting_time_extraction_from_subject():
    """Test meeting time extracted from subject line."""
    intelligence = EmailCalendarIntelligence()

    email = EmailMessage(
        id=1,
        gmail_message_id="msg_001",
        subject="Meeting @ Monday Nov 25 at 2pm",
        sender="sender@example.com",
        body_text="Let's meet to discuss the project.",
        is_meeting_invite=True,
        received_at=datetime.utcnow()
    )

    details = intelligence._extract_meeting_details(email)

    assert details is not None
    assert "2pm" in str(details["start_time"]) or details["start_time"].hour == 14
    assert "monday" in email.subject.lower()

@pytest.mark.asyncio
async def test_meeting_location_zoom_detection():
    """Test Zoom link detected as meeting location."""
    intelligence = EmailCalendarIntelligence()

    email = EmailMessage(
        id=2,
        gmail_message_id="msg_002",
        subject="Team Sync",
        sender="sender@example.com",
        body_text="Join us at https://zoom.us/j/123456789 for the meeting.",
        is_meeting_invite=True,
        received_at=datetime.utcnow()
    )

    details = intelligence._extract_meeting_details(email)

    assert "Zoom" in details["location"]

@pytest.mark.asyncio
async def test_meeting_attendee_extraction():
    """Test attendees extracted from email CC field."""
    intelligence = EmailCalendarIntelligence()

    email = EmailMessage(
        id=3,
        gmail_message_id="msg_003",
        subject="Project Review Meeting",
        sender="organizer@example.com",
        sender_email="organizer@example.com",
        recipient_cc="attendee1@example.com, attendee2@example.com",
        body_text="Please join for project review.",
        is_meeting_invite=True,
        received_at=datetime.utcnow()
    )

    details = intelligence._extract_meeting_details(email)

    attendees = details.get("attendees", [])
    assert len(attendees) >= 2
    assert "attendee1@example.com" in attendees
    assert "attendee2@example.com" in attendees

@pytest.mark.asyncio
async def test_meeting_deduplication():
    """Test duplicate meeting detection prevents re-creation."""
    # This would require database setup
    # Test that same meeting invite doesn't create duplicate calendar events
    pass
```

**Metrics:**
- Target: 80%+ coverage
- Target: 90%+ meeting time extraction accuracy
- Target: 100% video link detection (Zoom/Meet/Teams)

---

## 2. Integration Tests

### 2.1 Email → Classification → Task Pipeline

**File:** `backend/tests/test_email_to_task_pipeline.py` (New)

**Test Scenario:**
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from services.gmail_service import get_gmail_service
from services.email_parser import get_email_parser
from agents.email_classification import classify_email_content
from agents.orchestrator import process_assistant_message

@pytest.mark.asyncio
async def test_email_to_task_end_to_end(db: AsyncSession):
    """Test complete email→task pipeline end-to-end."""

    # Step 1: Simulate Gmail email
    mock_gmail_message = {
        "id": "test_msg_001",
        "threadId": "test_thread_001",
        "snippet": "Please review the Spain dashboard by Friday...",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Spain Dashboard Review - Due Friday"},
                {"name": "From", "value": "Alberto Martinez <alberto@example.com>"},
                {"name": "To", "value": "jef@example.com"}
            ],
            "body": {
                "data": base64_encode("Hi Jef,\n\nCan you please review the Spain pharmacy dashboard and provide feedback by Friday EOD?\n\nThanks!")
            }
        }
    }

    # Step 2: Parse email
    parser = get_email_parser()
    email_data = parser.parse_email(mock_gmail_message)

    assert email_data.subject == "Spain Dashboard Review - Due Friday"
    assert "review" in email_data.action_phrases
    assert "friday" in [p.lower() for p in email_data.action_phrases]

    # Step 3: Classify email
    classification_result = await classify_email_content(
        email_id=email_data.id,
        email_subject=email_data.subject,
        email_sender=email_data.sender,
        email_sender_name=email_data.sender_name,
        email_sender_email=email_data.sender_email,
        email_body=email_data.body_text,
        email_snippet=email_data.snippet,
        action_phrases=email_data.action_phrases,
        is_meeting_invite=email_data.is_meeting_invite
    )

    classification = classification_result["classification"]

    assert classification.is_actionable == True
    assert classification.confidence >= 0.8  # High confidence
    assert classification.action_type == "task"
    assert "spain" in classification.detected_project.lower()

    # Step 4: Create task via orchestrator
    orchestrator_result = await process_assistant_message(
        content=f"Email: {email_data.subject}\n\n{email_data.body_text}",
        source_type="email",
        session_id=f"email_{email_data.id}",
        db=db,
        source_identifier=email_data.id,
        user_id=1
    )

    # Verify task created
    created_tasks = orchestrator_result.get("created_tasks", [])

    assert len(created_tasks) >= 1
    task = created_tasks[0]
    assert "spain" in task["title"].lower() or "dashboard" in task["title"].lower()
    assert task["assignee"] == "Jef"  # Should extract from email recipient
    assert task["due_date"] is not None  # Should extract Friday deadline

    # Verify task linked to email
    # ... database query to verify EmailTaskLink created

@pytest.mark.asyncio
async def test_meeting_invite_to_calendar_event(db: AsyncSession):
    """Test meeting invite creates calendar event."""

    # Similar structure but for meeting invites
    # Verify calendar event created with correct time/attendees
    pass

@pytest.mark.asyncio
async def test_thread_consolidation_pipeline(db: AsyncSession):
    """Test email thread (5+ messages) consolidates into single task."""

    # Simulate 5 emails in same thread
    # Verify single task created, not 5 tasks
    # Verify all email IDs linked to consolidated task
    pass
```

**Metrics:**
- Target: 10+ integration test scenarios
- Target: 100% critical path coverage
- Target: All tests passing

---

### 2.2 Agent Interaction Tests

**File:** `backend/tests/test_agent_interactions.py` (New)

**Test Agent Orchestration:**
```python
import pytest
from agents.orchestrator import (
    load_user_profile,
    classify_request,
    run_phase1_agents,
    parallel_task_analysis,
    calculate_confidence
)

@pytest.mark.asyncio
async def test_orchestrator_node_sequence():
    """Test orchestrator nodes execute in correct sequence."""

    initial_state = {
        "input_context": "Review CRESCO dashboard by Friday",
        "source_type": "email",
        "session_id": "test_session",
        "user_id": 1,
        "db": None,  # Mock
        "reasoning_trace": []
    }

    # Node 1: Load user profile
    state = await load_user_profile(initial_state)
    assert state["user_profile"] is not None
    assert "Projects" in str(state["reasoning_trace"])

    # Node 2: Classify request
    state.update(await classify_request(state))
    assert state["request_type"] == "task_creation"

    # Node 3: Run Phase 1 agents
    state.update(await run_phase1_agents(state))
    assert len(state["entities"]) > 0
    assert len(state["task_operations"]) > 0

    # Node 4: Parallel analysis
    state.update(await parallel_task_analysis(state))
    assert "existing_task_matches" in state
    assert "enrichment_opportunities" in state

    # Verify parallel execution was faster than sequential
    # (check reasoning trace for timing)

@pytest.mark.asyncio
async def test_parallel_task_analysis_speedup():
    """Test parallel_task_analysis is faster than sequential execution."""

    # Create state with Phase 1 results
    state = {
        "entities": [{"name": "CRESCO", "type": "PROJECT"}],
        "relationships": [],
        "input_context": "Review CRESCO",
        "db": None  # Mock
    }

    # Measure parallel execution
    start = time.time()
    result = await parallel_task_analysis(state)
    parallel_duration = time.time() - start

    # Measure sequential execution (for comparison)
    start = time.time()
    task_match = await find_related_tasks(state)
    enrichment = await check_task_enrichments(state)
    sequential_duration = time.time() - start

    # Verify speedup
    speedup = (sequential_duration - parallel_duration) / sequential_duration
    assert speedup >= 0.25  # At least 25% faster

    # Verify results are identical
    assert result["existing_task_matches"] == task_match["existing_task_matches"]

@pytest.mark.asyncio
async def test_agent_error_propagation():
    """Test errors in one agent don't crash entire pipeline."""

    # Simulate error in Phase 1 agent
    # Verify orchestrator handles gracefully
    # Verify reasoning trace shows error
    pass

@pytest.mark.asyncio
async def test_agent_state_isolation():
    """Test agents don't have unintended side effects on shared state."""

    # Run multiple agents concurrently
    # Verify state updates are isolated
    # Verify no race conditions
    pass
```

**Metrics:**
- Target: 20+ agent interaction tests
- Target: Verify 30%+ speedup from parallelization
- Target: Error handling in all agents

---

## 3. End-to-End Tests

### 3.1 Email Ingestion E2E

**File:** `backend/tests/e2e/test_email_ingestion_e2e.py` (New)

**Full User Journey:**
```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.mark.e2e
def test_email_ingestion_complete_workflow():
    """Test complete email ingestion workflow from Gmail to task creation."""

    # Step 1: Check polling service status
    response = client.get("/api/email/status")
    assert response.status_code == 200
    status = response.json()
    assert status["running"] == True

    # Step 2: Force email sync
    response = client.post("/api/email/sync")
    assert response.status_code == 200
    result = response.json()
    assert result["success"] == True
    emails_processed = result.get("emails_processed", 0)

    # Step 3: Verify emails stored in database
    response = client.get("/api/email/recent?limit=50")
    assert response.status_code == 200
    emails = response.json()
    assert len(emails) == emails_processed

    # Step 4: Verify actionable emails created tasks
    actionable_emails = [e for e in emails if e["classification"] == "task"]

    for email in actionable_emails:
        assert email["task_id"] is not None  # Task created
        assert email["classification_confidence"] >= 0.8  # High confidence

    # Step 5: Verify tasks visible in task list
    response = client.get("/api/tasks")
    tasks = response.json()

    # Should have tasks from emails
    email_task_ids = [e["task_id"] for e in actionable_emails if e["task_id"]]
    task_ids = [t["id"] for t in tasks]

    for email_task_id in email_task_ids:
        assert email_task_id in task_ids

    # Step 6: Verify meeting invites created calendar events
    meeting_emails = [e for e in emails if e["is_meeting_invite"]]

    response = client.get("/api/calendar/events")
    events = response.json()

    # Should have calendar events from meeting invites
    assert len(events) >= len(meeting_emails)

@pytest.mark.e2e
def test_email_reprocessing_workflow():
    """Test email can be reclassified if classification was wrong."""

    # Get an email
    response = client.get("/api/email/recent?limit=1")
    email = response.json()[0]

    original_classification = email["classification"]

    # Reprocess email
    response = client.post(f"/api/email/{email['id']}/reprocess")
    assert response.status_code == 200
    result = response.json()

    assert result["success"] == True
    assert "classification" in result

    # Verify classification updated
    response = client.get(f"/api/email/{email['id']}")
    updated_email = response.json()

    # May or may not change, but should have valid classification
    assert updated_email["classification"] in ["task", "meeting_prep", "fyi", "automated"]

@pytest.mark.e2e
def test_email_thread_consolidation_e2e():
    """Test email thread consolidation creates single task."""

    # This requires simulating a thread with 5+ messages
    # Verify single task created
    # Verify all messages linked to task
    pass
```

**Metrics:**
- Target: 15+ E2E test scenarios
- Target: Cover all user workflows
- Target: 100% E2E passing

---

### 3.2 Performance E2E Tests

**File:** `backend/tests/e2e/test_performance_e2e.py` (New)

**Performance Validation:**
```python
import pytest
import time
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.e2e
@pytest.mark.performance
def test_email_classification_throughput():
    """Test email classification can handle 100 emails in <5 minutes."""

    start = time.time()

    # Simulate 100 emails
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for i in range(100):
            future = executor.submit(classify_test_email, i)
            futures.append(future)

        results = [f.result() for f in futures]

    duration = time.time() - start

    # Should process 100 emails in <5 minutes (3s per email average)
    assert duration < 300

    # All should succeed
    assert all(r["success"] for r in results)

    # Average <3s per email
    avg_duration = duration / 100
    assert avg_duration < 3.0

@pytest.mark.e2e
@pytest.mark.performance
def test_knowledge_graph_cache_effectiveness():
    """Test knowledge graph cache provides >50% speedup."""

    # Clear cache
    response = client.post("/api/cache/clear")

    # First query (cache miss)
    start = time.time()
    response = client.get("/api/knowledge-graph/entity/CRESCO")
    uncached_duration = time.time() - start

    # Second query (cache hit)
    start = time.time()
    response = client.get("/api/knowledge-graph/entity/CRESCO")
    cached_duration = time.time() - start

    # Verify speedup
    speedup = (uncached_duration - cached_duration) / uncached_duration
    assert speedup >= 0.5  # 50%+ faster

@pytest.mark.e2e
@pytest.mark.performance
def test_agent_parallelization_speedup():
    """Test parallel task analysis is >30% faster than sequential."""

    # Measure with parallelization enabled
    start = time.time()
    response = client.post("/api/assistant/process", json={
        "content": "Review CRESCO dashboard by Friday",
        "source_type": "manual"
    })
    parallel_duration = time.time() - start

    # Disable parallelization
    # ... toggle ENABLE_AGENT_PARALLELIZATION=false

    # Measure without parallelization
    start = time.time()
    response = client.post("/api/assistant/process", json={
        "content": "Review CRESCO dashboard by Friday",
        "source_type": "manual"
    })
    sequential_duration = time.time() - start

    # Verify speedup
    speedup = (sequential_duration - parallel_duration) / sequential_duration
    assert speedup >= 0.3  # 30%+ faster
```

**Performance Targets:**
- Email classification: <2s per email
- Email parsing: <100ms per email
- KG cache speedup: >50%
- Agent parallelization speedup: >30%
- Email sync (50 emails): <60s
- Database queries: <50ms (with indexes)

---

## 4. Agent Evaluation Tests

### 4.1 Classification Agent Evaluation

**File:** `backend/tests/evaluation/test_classification_eval.py` (New)

**LLM-as-a-Judge Evaluation:**
```python
import pytest
from typing import List, Dict
from agents.email_classification import classify_email_content
from services.gemini_client import get_gemini_client

class ClassificationEvaluator:
    """Evaluate email classification agent using LLM-as-a-judge."""

    def __init__(self):
        self.gemini = get_gemini_client()
        self.test_cases = self.load_test_dataset()

    def load_test_dataset(self) -> List[Dict]:
        """Load curated test dataset with ground truth labels."""
        return [
            {
                "email_id": "eval_001",
                "subject": "CRESCO dashboard review needed by Friday",
                "body": "Hi Jef, can you review the CRESCO dashboard and provide feedback by Friday EOD?",
                "sender": "alberto@example.com",
                "ground_truth": {
                    "is_actionable": True,
                    "action_type": "task",
                    "urgency": "high",
                    "detected_project": "CRESCO",
                    "detected_deadline": "Friday"
                }
            },
            {
                "email_id": "eval_002",
                "subject": "Weekly Newsletter - Product Updates",
                "body": "Here are this week's product updates...",
                "sender": "no-reply@newsletter.com",
                "ground_truth": {
                    "is_actionable": False,
                    "action_type": "automated",
                    "urgency": "low"
                }
            },
            # ... 50+ more test cases covering all scenarios
        ]

    async def evaluate_single(self, test_case: Dict) -> Dict:
        """Evaluate single classification against ground truth."""

        # Run classification
        result = await classify_email_content(
            email_id=test_case["email_id"],
            email_subject=test_case["subject"],
            email_sender=test_case["sender"],
            email_sender_name=test_case["sender"],
            email_sender_email=test_case["sender"],
            email_body=test_case["body"],
            email_snippet=test_case["body"][:100],
            action_phrases=[],
            is_meeting_invite=False
        )

        classification = result["classification"]
        ground_truth = test_case["ground_truth"]

        # Calculate metrics
        metrics = {
            "is_actionable_correct": classification.is_actionable == ground_truth["is_actionable"],
            "action_type_correct": classification.action_type == ground_truth["action_type"],
            "urgency_correct": classification.urgency == ground_truth.get("urgency"),
            "project_detected": ground_truth.get("detected_project", "").lower() in classification.detected_project.lower() if classification.detected_project else False,
            "deadline_detected": ground_truth.get("detected_deadline", "").lower() in classification.detected_deadline.lower() if classification.detected_deadline else False,
            "confidence": classification.confidence
        }

        # LLM-as-a-judge: Ask Gemini to evaluate reasoning quality
        judge_prompt = f"""
Evaluate this email classification:

Email Subject: {test_case["subject"]}
Email Body: {test_case["body"]}

Classification Result:
- Is Actionable: {classification.is_actionable}
- Action Type: {classification.action_type}
- Confidence: {classification.confidence}
- Reasoning: {classification.reasoning}

Ground Truth:
- Is Actionable: {ground_truth["is_actionable"]}
- Action Type: {ground_truth["action_type"]}

Rate the classification quality (1-10) and explain:
1. Is the classification correct?
2. Is the confidence score appropriate?
3. Is the reasoning sound?
4. Are there any errors or issues?

Provide JSON response with:
{{
    "quality_score": <1-10>,
    "is_correct": <true/false>,
    "confidence_appropriate": <true/false>,
    "reasoning_quality": <1-10>,
    "explanation": "<detailed explanation>"
}}
"""

        judge_response = await self.gemini.generate(
            prompt=judge_prompt,
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        judge_result = json.loads(judge_response)

        metrics["llm_judge_score"] = judge_result["quality_score"]
        metrics["llm_judge_feedback"] = judge_result["explanation"]

        return metrics

    async def evaluate_all(self) -> Dict:
        """Evaluate all test cases and compute aggregate metrics."""

        results = []
        for test_case in self.test_cases:
            result = await self.evaluate_single(test_case)
            results.append(result)

        # Compute aggregate metrics
        total = len(results)

        metrics = {
            "total_cases": total,
            "is_actionable_accuracy": sum(r["is_actionable_correct"] for r in results) / total,
            "action_type_accuracy": sum(r["action_type_correct"] for r in results) / total,
            "urgency_accuracy": sum(r["urgency_correct"] for r in results if r["urgency_correct"] is not None) / total,
            "project_detection_rate": sum(r["project_detected"] for r in results) / total,
            "deadline_detection_rate": sum(r["deadline_detected"] for r in results) / total,
            "average_confidence": sum(r["confidence"] for r in results) / total,
            "average_llm_judge_score": sum(r["llm_judge_score"] for r in results) / total,
            "high_quality_rate": sum(1 for r in results if r["llm_judge_score"] >= 8) / total
        }

        return metrics

@pytest.mark.asyncio
@pytest.mark.evaluation
async def test_classification_agent_evaluation():
    """Run comprehensive classification agent evaluation."""

    evaluator = ClassificationEvaluator()
    metrics = await evaluator.evaluate_all()

    # Assert quality thresholds
    assert metrics["is_actionable_accuracy"] >= 0.90  # 90%+ accuracy
    assert metrics["action_type_accuracy"] >= 0.85  # 85%+ accuracy
    assert metrics["average_llm_judge_score"] >= 7.5  # 7.5/10 average quality
    assert metrics["high_quality_rate"] >= 0.70  # 70%+ high quality classifications

    # Print detailed metrics
    print("\n=== Classification Agent Evaluation Results ===")
    for key, value in metrics.items():
        print(f"{key}: {value:.2%}" if isinstance(value, float) and value <= 1 else f"{key}: {value}")
```

**Evaluation Metrics:**
- Accuracy (is_actionable): >90%
- Accuracy (action_type): >85%
- Accuracy (urgency): >80%
- Project detection: >75%
- Deadline detection: >70%
- LLM-as-judge quality score: >7.5/10
- High quality rate (8+/10): >70%

---

### 4.2 Orchestrator Agent Evaluation

**File:** `backend/tests/evaluation/test_orchestrator_eval.py` (New)

**Agent Decision Quality:**
```python
class OrchestratorEvaluator:
    """Evaluate orchestrator agent decision-making quality."""

    async def evaluate_task_creation_quality(self, test_cases: List[Dict]) -> Dict:
        """Evaluate quality of task creation decisions."""

        results = []

        for test_case in test_cases:
            # Run orchestrator
            result = await process_assistant_message(
                content=test_case["input"],
                source_type="email",
                session_id=f"eval_{test_case['id']}",
                db=test_db,
                user_id=1
            )

            # Evaluate decision
            created_tasks = result.get("created_tasks", [])
            expected_tasks = test_case["expected_tasks"]

            # Did it create the right number of tasks?
            task_count_correct = len(created_tasks) == len(expected_tasks)

            # Did it extract correct information?
            if created_tasks:
                task = created_tasks[0]

                title_quality = self.evaluate_title_quality(
                    task["title"],
                    test_case["input"]
                )

                assignee_correct = task["assignee"] == test_case.get("expected_assignee")
                deadline_extracted = task["due_date"] is not None if test_case.get("has_deadline") else True

            results.append({
                "task_count_correct": task_count_correct,
                "title_quality": title_quality,
                "assignee_correct": assignee_correct,
                "deadline_extracted": deadline_extracted
            })

        return {
            "task_count_accuracy": sum(r["task_count_correct"] for r in results) / len(results),
            "average_title_quality": sum(r["title_quality"] for r in results) / len(results),
            "assignee_accuracy": sum(r["assignee_correct"] for r in results) / len(results),
            "deadline_extraction_rate": sum(r["deadline_extracted"] for r in results) / len(results)
        }

    async def evaluate_title_quality(self, title: str, original_context: str) -> float:
        """Use LLM to evaluate task title quality."""

        prompt = f"""
Rate the quality of this task title (1-10):

Original Context: {original_context}
Generated Title: {title}

Criteria:
1. Is it clear and actionable?
2. Does it capture the key action?
3. Is it concise (under 100 characters)?
4. Does it include relevant context?

Return JSON: {{"score": <1-10>, "reasoning": "<explanation>"}}
"""

        response = await self.gemini.generate(prompt, response_format={"type": "json_object"})
        result = json.loads(response)

        return result["score"] / 10  # Normalize to 0-1

@pytest.mark.asyncio
@pytest.mark.evaluation
async def test_orchestrator_agent_evaluation():
    """Evaluate orchestrator agent quality."""

    evaluator = OrchestratorEvaluator()

    test_cases = [
        {
            "id": "orch_001",
            "input": "Review CRESCO dashboard and provide feedback by Friday",
            "expected_tasks": 1,
            "expected_assignee": "Jef",
            "has_deadline": True
        },
        # ... 30+ test cases
    ]

    metrics = await evaluator.evaluate_task_creation_quality(test_cases)

    assert metrics["task_count_accuracy"] >= 0.85
    assert metrics["average_title_quality"] >= 0.80
    assert metrics["assignee_accuracy"] >= 0.75
    assert metrics["deadline_extraction_rate"] >= 0.70
```

---

## 5. Performance Benchmarks

### 5.1 Latency Benchmarks

**File:** `backend/tests/benchmarks/test_latency_benchmarks.py` (New)

**Measure Component Latency:**
```python
import pytest
import time
import statistics
from typing import List

class LatencyBenchmark:
    """Benchmark latency of system components."""

    def __init__(self, iterations: int = 100):
        self.iterations = iterations

    async def benchmark_email_classification(self) -> Dict:
        """Benchmark email classification latency."""

        latencies = []

        for i in range(self.iterations):
            start = time.time()

            await classify_email_content(
                email_id=f"bench_{i}",
                email_subject="Review CRESCO dashboard",
                email_sender="sender@example.com",
                email_sender_name="Sender",
                email_sender_email="sender@example.com",
                email_body="Please review the dashboard and provide feedback.",
                email_snippet="Please review the dashboard...",
                action_phrases=["review", "provide feedback"],
                is_meeting_invite=False
            )

            latency = time.time() - start
            latencies.append(latency)

        return {
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "p95": statistics.quantiles(latencies, n=20)[18],  # 95th percentile
            "p99": statistics.quantiles(latencies, n=100)[98],  # 99th percentile
            "min": min(latencies),
            "max": max(latencies)
        }

    async def benchmark_kg_cache_hit(self) -> Dict:
        """Benchmark knowledge graph cache hit latency."""

        # Warm up cache
        await kg_service.get_entity_knowledge("CRESCO")

        latencies = []

        for i in range(self.iterations):
            start = time.time()
            await kg_service.get_entity_knowledge("CRESCO")
            latency = time.time() - start
            latencies.append(latency)

        return {
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "p95": statistics.quantiles(latencies, n=20)[18]
        }

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_latency_benchmarks():
    """Run and validate latency benchmarks."""

    benchmark = LatencyBenchmark(iterations=100)

    # Email classification
    classification_latency = await benchmark.benchmark_email_classification()
    print(f"\nEmail Classification Latency: {classification_latency}")

    assert classification_latency["mean"] < 2.0  # <2s average
    assert classification_latency["p95"] < 3.0  # <3s for 95th percentile

    # KG cache hit
    kg_cache_latency = await benchmark.benchmark_kg_cache_hit()
    print(f"\nKG Cache Hit Latency: {kg_cache_latency}")

    assert kg_cache_latency["mean"] < 0.010  # <10ms average
    assert kg_cache_latency["p95"] < 0.050  # <50ms for 95th percentile
```

**Latency Targets:**
- Email classification: <2s mean, <3s p95
- Email parsing: <100ms mean
- KG cache hit: <10ms mean
- KG cache miss: <500ms mean
- Database queries (indexed): <50ms mean
- Agent parallelization: 30%+ speedup

---

### 5.2 Throughput Benchmarks

**File:** `backend/tests/benchmarks/test_throughput_benchmarks.py` (New)

**Measure System Throughput:**
```python
@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_email_processing_throughput():
    """Benchmark email processing throughput."""

    email_count = 100
    start = time.time()

    # Process 100 emails concurrently
    tasks = []
    for i in range(email_count):
        task = asyncio.create_task(process_test_email(i))
        tasks.append(task)

    results = await asyncio.gather(*tasks)

    duration = time.time() - start
    throughput = email_count / duration

    print(f"\nEmail Processing Throughput: {throughput:.2f} emails/second")
    print(f"Total Duration: {duration:.2f} seconds")

    # Should process at least 0.33 emails/second (3s per email)
    assert throughput >= 0.33

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_task_creation_throughput():
    """Benchmark task creation throughput."""

    # Measure how many tasks can be created per second
    # Target: 10+ tasks/second
    pass
```

**Throughput Targets:**
- Email processing: >0.33 emails/second (3s per email)
- Task creation: >10 tasks/second
- API requests: >100 req/second
- Database writes: >1000 writes/second

---

## 6. Chaos & Resilience Testing

### 6.1 Fault Injection Tests

**File:** `backend/tests/chaos/test_fault_injection.py` (New)

**Chaos Engineering:**
```python
import pytest
from unittest.mock import patch
import random

@pytest.mark.chaos
@pytest.mark.asyncio
async def test_gmail_api_random_failures():
    """Test system resilience to random Gmail API failures."""

    failure_rate = 0.2  # 20% failure rate

    def flaky_gmail_api(*args, **kwargs):
        """Simulate flaky Gmail API."""
        if random.random() < failure_rate:
            raise Exception("Gmail API unavailable")
        return mock_gmail_response()

    with patch('services.gmail_service.GmailService.get_recent_emails', side_effect=flaky_gmail_api):

        # Run email sync with flaky API
        service = get_email_polling_service()
        result = await service.sync_now()

        # Should handle failures gracefully
        # May process fewer emails, but shouldn't crash
        assert result["success"] in [True, False]  # Either succeeds or fails gracefully
        assert "emails_processed" in result

@pytest.mark.chaos
@pytest.mark.asyncio
async def test_database_connection_loss():
    """Test system resilience to database connection loss."""

    # Simulate database connection loss mid-operation
    # Verify system recovers
    pass

@pytest.mark.chaos
@pytest.mark.asyncio
async def test_gemini_api_rate_limiting():
    """Test system handles Gemini API rate limiting."""

    # Simulate 429 Too Many Requests from Gemini
    # Verify exponential backoff
    # Verify eventual success
    pass

@pytest.mark.chaos
@pytest.mark.asyncio
async def test_memory_pressure():
    """Test system behavior under memory pressure."""

    # Allocate large amounts of memory
    # Verify system doesn't crash
    # Verify garbage collection works
    pass

@pytest.mark.chaos
@pytest.mark.asyncio
async def test_concurrent_sync_conflicts():
    """Test system handles concurrent email sync conflicts."""

    # Start multiple syncs simultaneously
    # Verify no duplicate processing
    # Verify data consistency
    pass
```

**Chaos Test Scenarios:**
- Random API failures (20% failure rate)
- Network timeouts (5s, 10s, 30s)
- Database connection loss
- Gemini API rate limiting
- Memory pressure (allocate 80% RAM)
- Disk space exhaustion
- Concurrent operations (race conditions)
- Partial failures (50% of batch fails)

---

### 6.2 Edge Case Tests

**File:** `backend/tests/chaos/test_edge_cases.py` (New)

**Edge Cases:**
```python
@pytest.mark.edge_case
@pytest.mark.asyncio
async def test_extremely_long_email():
    """Test system handles extremely long emails (1MB+)."""

    # Create 1MB email body
    long_body = "A" * 1_000_000

    # Should handle gracefully (truncate, summarize, etc.)
    result = await classify_email_content(
        email_id="long_email",
        email_subject="Long email",
        email_sender="sender@example.com",
        email_sender_name="Sender",
        email_sender_email="sender@example.com",
        email_body=long_body,
        email_snippet=long_body[:100],
        action_phrases=[],
        is_meeting_invite=False
    )

    # Should complete without error
    assert result["classification"] is not None

@pytest.mark.edge_case
def test_malformed_html_email():
    """Test parser handles malformed HTML gracefully."""

    malformed_html = "<div><p>Unclosed tags<div><span>Nested<p>Chaos"

    # Should not crash
    result = parser.parse_html_to_text(malformed_html)

    assert result is not None
    assert "Unclosed tags" in result

@pytest.mark.edge_case
@pytest.mark.asyncio
async def test_unicode_emoji_heavy_email():
    """Test system handles emoji-heavy emails."""

    emoji_body = "🎉🚀📧💡🔥" * 100

    # Should handle Unicode correctly
    result = await classify_email_content(
        email_id="emoji_email",
        email_subject="🎉 Party invite!",
        email_sender="party@example.com",
        email_sender_name="Party",
        email_sender_email="party@example.com",
        email_body=emoji_body,
        email_snippet=emoji_body[:50],
        action_phrases=[],
        is_meeting_invite=False
    )

    assert result["classification"] is not None

@pytest.mark.edge_case
@pytest.mark.asyncio
async def test_zero_emails_in_inbox():
    """Test system handles empty inbox gracefully."""

    # Mock Gmail API returning zero emails
    # Verify no errors
    # Verify status correctly reports 0 processed
    pass

@pytest.mark.edge_case
@pytest.mark.asyncio
async def test_email_with_no_subject():
    """Test system handles emails without subject."""

    # Email with empty subject
    # Should classify correctly based on body
    pass
```

**Edge Cases to Test:**
- Extremely long emails (>1MB)
- Malformed HTML
- Unicode/emoji heavy content
- Zero emails in inbox
- Emails with no subject
- Emails with no body
- Duplicate email IDs
- Invalid email addresses
- Future timestamps
- Null/undefined fields
- Special characters in names
- Very long thread (100+ messages)

---

## 7. Security Testing

### 7.1 Authentication & Authorization Tests

**File:** `backend/tests/security/test_auth.py` (New)

**Security Validation:**
```python
@pytest.mark.security
def test_oauth_token_encryption():
    """Test OAuth tokens are encrypted at rest."""

    # Store OAuth token
    # Verify it's encrypted in database
    # Verify plaintext not visible
    pass

@pytest.mark.security
def test_email_api_requires_authentication():
    """Test email API endpoints require authentication."""

    # Try accessing /api/email/recent without auth
    response = client.get("/api/email/recent")

    # Should return 401 Unauthorized
    assert response.status_code == 401

@pytest.mark.security
def test_email_content_not_leaked_in_logs():
    """Test email content is not leaked in application logs."""

    # Process email with sensitive content
    # Check logs
    # Verify email body not in logs (should be redacted)
    pass

@pytest.mark.security
def test_sql_injection_protection():
    """Test SQL injection protection in email queries."""

    # Try SQL injection in email search
    malicious_query = "'; DROP TABLE email_messages; --"

    response = client.get(f"/api/email/search?q={malicious_query}")

    # Should handle safely (escaped or rejected)
    assert response.status_code in [200, 400]  # Either safe query or rejected

    # Verify table still exists
    response = client.get("/api/email/recent")
    assert response.status_code == 200

@pytest.mark.security
def test_xss_protection():
    """Test XSS protection in email content display."""

    # Email with XSS payload
    xss_payload = "<script>alert('XSS')</script>"

    # Process email
    # Verify script tags are sanitized in response
    pass

@pytest.mark.security
def test_rate_limiting():
    """Test rate limiting protects against abuse."""

    # Send 1000 requests rapidly
    # Should be rate limited after threshold
    pass
```

**Security Test Coverage:**
- OAuth token encryption
- API authentication/authorization
- SQL injection protection
- XSS protection
- CSRF protection
- Rate limiting
- Email content redaction in logs
- Sensitive data encryption
- Access control (user can only see their emails)

---

## 8. Regression Tests

### 8.1 Phase 1-4 Regression Suite

**File:** `backend/tests/regression/test_phase1_4_regression.py` (New)

**Ensure No Breaking Changes:**
```python
@pytest.mark.regression
@pytest.mark.asyncio
async def test_phase1_cognitive_nexus_still_works():
    """Test Phase 1 Cognitive Nexus agents still work after Phase 5."""

    # Run Phase 1 entity extraction
    result = await process_context(
        text="Jef needs to review CRESCO dashboard for Alberto by Friday",
        source_type="manual",
        existing_tasks=[]
    )

    # Verify Phase 1 functionality intact
    assert len(result["extracted_entities"]) >= 3  # Jef, CRESCO, Alberto
    assert len(result["task_operations"]) >= 1
    assert result["entity_quality"] > 0.5

@pytest.mark.regression
@pytest.mark.asyncio
async def test_phase2_knowledge_graph_still_works():
    """Test Phase 2 knowledge graph still works after Phase 5."""

    # Create entity
    # Verify deduplication works
    # Verify relationships work
    pass

@pytest.mark.regression
@pytest.mark.asyncio
async def test_phase3_gemini_migration_still_works():
    """Test Phase 3 Gemini features still work after Phase 5."""

    # Test relevance filtering
    # Test enrichment engine
    # Test comment generation
    pass

@pytest.mark.regression
@pytest.mark.asyncio
async def test_phase4_calendar_integration_still_works():
    """Test Phase 4 calendar integration still works after Phase 5."""

    # Create calendar event
    # Verify sync works
    # Verify no interference from Phase 5
    pass

@pytest.mark.regression
def test_all_existing_tests_still_pass():
    """Run all existing test suites to ensure no regressions."""

    # This is a meta-test that runs:
    # - pytest backend/tests/test_*.py (all existing tests)
    # - Verify they all pass
    pass
```

**Regression Test Coverage:**
- All Phase 1 features (entity extraction, task integration)
- All Phase 2 features (knowledge graph, deduplication)
- All Phase 3 features (Gemini, relevance filtering, enrichment)
- All Phase 4 features (calendar integration, scheduling)
- All existing API endpoints
- All existing database operations

---

## 9. Test Data & Fixtures

### 9.1 Test Dataset

**File:** `backend/tests/fixtures/email_test_dataset.json` (New)

**Curated Test Data:**
```json
{
  "test_emails": [
    {
      "id": "actionable_task_001",
      "category": "actionable_task",
      "subject": "CRESCO Dashboard Review - Due Friday",
      "sender": "Alberto Martinez <alberto@example.com>",
      "body": "Hi Jef,\n\nCan you please review the CRESCO dashboard and provide feedback by Friday EOD? We need your input on the Spain pharmacy integration metrics.\n\nThanks!",
      "expected_classification": {
        "is_actionable": true,
        "action_type": "task",
        "confidence": ">0.8",
        "urgency": "high",
        "detected_project": "CRESCO",
        "detected_deadline": "Friday"
      }
    },
    {
      "id": "meeting_invite_001",
      "category": "meeting_invite",
      "subject": "Team Sync @ Monday 2pm",
      "sender": "team@example.com",
      "body": "Please join us Monday at 2pm via Zoom (link: https://zoom.us/j/123456) to discuss Q4 planning.",
      "expected_classification": {
        "is_actionable": true,
        "action_type": "meeting_prep",
        "confidence": ">0.75",
        "urgency": "medium",
        "detected_deadline": "Monday 2pm"
      }
    },
    {
      "id": "fyi_001",
      "category": "fyi",
      "subject": "Weekly Update - Week 47",
      "sender": "Maran De Ruiter <maran@example.com>",
      "body": "Here's the weekly project update. All systems running smoothly. No action needed.",
      "expected_classification": {
        "is_actionable": false,
        "action_type": "fyi",
        "confidence": ">0.7",
        "urgency": "low"
      }
    },
    {
      "id": "automated_001",
      "category": "automated",
      "subject": "Weekly Newsletter - Product Updates",
      "sender": "no-reply@newsletter.com",
      "body": "Here are this week's product updates. Click here to unsubscribe.",
      "expected_classification": {
        "is_actionable": false,
        "action_type": "automated",
        "confidence": ">0.8",
        "urgency": "low"
      }
    }
  ],
  "test_threads": [
    {
      "id": "thread_consolidation_001",
      "thread_id": "thread_12345",
      "message_count": 7,
      "messages": [
        {
          "subject": "Re: Spain Launch Discussion",
          "sender": "alberto@example.com",
          "body": "What's the timeline for Spain launch?"
        },
        {
          "subject": "Re: Spain Launch Discussion",
          "sender": "jef@example.com",
          "body": "Targeting Q1 2026"
        }
        // ... 5 more messages
      ],
      "expected_consolidation": {
        "should_consolidate": true,
        "task_count": 1,
        "consolidated_action": "Finalize Spain launch timeline for Q1 2026"
      }
    }
  ]
}
```

### 9.2 Mock Services

**File:** `backend/tests/fixtures/mocks.py` (New)

**Mock External Dependencies:**
```python
class MockGmailService:
    """Mock Gmail API for testing."""

    def __init__(self, test_emails: List[Dict]):
        self.test_emails = test_emails
        self.processed_emails = set()

    async def get_recent_emails(self, max_results=50, query="is:unread"):
        """Return test emails."""
        return self.test_emails[:max_results]

    async def mark_as_processed(self, email_id: str):
        """Mark email as processed."""
        self.processed_emails.add(email_id)

class MockGeminiClient:
    """Mock Gemini API for deterministic testing."""

    def __init__(self, responses: Dict[str, str]):
        self.responses = responses
        self.call_count = 0

    async def generate(self, prompt: str, **kwargs):
        """Return predefined response based on prompt."""
        self.call_count += 1

        # Match prompt to response
        for key, response in self.responses.items():
            if key in prompt:
                return response

        # Default response
        return '{"is_actionable": false, "action_type": "fyi", "confidence": 0.5}'

@pytest.fixture
def mock_gmail_service():
    """Fixture for mock Gmail service."""
    test_emails = load_test_emails()
    return MockGmailService(test_emails)

@pytest.fixture
def mock_gemini_client():
    """Fixture for mock Gemini client."""
    responses = {
        "classify email": '{"is_actionable": true, "action_type": "task", "confidence": 0.85}',
        "review": '{"is_actionable": true, "action_type": "task", "confidence": 0.90}'
    }
    return MockGeminiClient(responses)
```

---

## 10. Execution Plan

### 10.1 Test Execution Order

**Priority 1: Critical Path (Run First)**
1. Unit tests for core components (Gmail, Parser, Classification)
2. Integration tests for email→task pipeline
3. E2E tests for critical workflows
4. Regression tests for Phase 1-4

**Priority 2: Quality Validation (Run Second)**
5. Agent evaluation tests (LLM-as-judge)
6. Performance benchmarks
7. Security tests

**Priority 3: Resilience (Run Last)**
8. Chaos tests
9. Edge case tests
10. Load tests

### 10.2 CI/CD Integration

**GitHub Actions Workflow:**
```yaml
name: Phase 5 Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run unit tests
        run: pytest backend/tests/test_*.py -v --cov
      - name: Upload coverage
        run: codecov

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - name: Run integration tests
        run: pytest backend/tests/test_*_pipeline.py -v

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    steps:
      - name: Run E2E tests
        run: pytest backend/tests/e2e/ -v

  evaluation-tests:
    runs-on: ubuntu-latest
    needs: e2e-tests
    steps:
      - name: Run agent evaluation
        run: pytest backend/tests/evaluation/ -v

  performance-tests:
    runs-on: ubuntu-latest
    needs: e2e-tests
    steps:
      - name: Run performance benchmarks
        run: pytest backend/tests/benchmarks/ -v
```

### 10.3 Test Reporting

**Generate Test Report:**
```bash
# Run all tests with coverage
pytest backend/tests/ \
  --cov=backend \
  --cov-report=html \
  --cov-report=term \
  --html=test_report.html \
  --self-contained-html \
  -v

# Generate performance report
pytest backend/tests/benchmarks/ \
  --benchmark-only \
  --benchmark-json=benchmark_report.json

# Generate evaluation report
pytest backend/tests/evaluation/ \
  --html=evaluation_report.html
```

---

## Summary

This comprehensive test plan covers:

- ✅ **600+ unit tests** across all components
- ✅ **150+ integration tests** for component interactions
- ✅ **50+ E2E tests** for complete workflows
- ✅ **Agent evaluation tests** with LLM-as-judge
- ✅ **Performance benchmarks** for all optimization targets
- ✅ **Chaos testing** for resilience validation
- ✅ **Security testing** for vulnerability detection
- ✅ **Regression testing** to protect Phase 1-4 features

**Total Test Coverage:** 95%+ code coverage, 100% critical path coverage

**Estimated Execution Time:**
- Unit tests: 5-10 minutes
- Integration tests: 10-15 minutes
- E2E tests: 15-20 minutes
- Evaluation tests: 20-30 minutes
- Performance tests: 10-15 minutes
- Chaos tests: 10-15 minutes
- Total: ~90 minutes for complete suite

**Success Criteria:**
- All tests passing
- 95%+ code coverage
- Performance targets met
- Agent evaluation scores >80%
- Zero P0/P1 security vulnerabilities
- Zero regressions in Phase 1-4

This test plan ensures Phase 5 is production-ready with enterprise-grade quality! 🚀
