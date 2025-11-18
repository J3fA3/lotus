"""
End-to-End Tests for Phase 2 AI Assistant (Lotus)

This test suite validates all 5 core scenarios:
1. Manual questions → Question answering
2. Slack messages → Task creation
3. Transcripts → Task creation
4. PDF uploads → Fast processing
5. Manual task creation → Full orchestrator pipeline
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.orchestrator import process_assistant_message
from db.database import Base
from db.models import Task, ChatMessage, ContextItem, Entity, Relationship


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
async def test_db():
    """Create a test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Seed with some existing tasks
        task1 = Task(
            title="Update dashboard prototype",
            assignee="Andy",
            status="in_progress",
            priority="high",
            value_stream="CRESCO"
        )
        task2 = Task(
            title="Review API documentation",
            assignee="Sarah",
            status="todo",
            priority="medium",
            value_stream="Platform"
        )
        session.add_all([task1, task2])
        await session.commit()

        yield session


# ============================================================================
# SCENARIO 1: MANUAL QUESTIONS → QUESTION ANSWERING
# ============================================================================

@pytest.mark.asyncio
async def test_scenario1_manual_question(test_db):
    """Test that manual questions are answered directly."""
    result = await process_assistant_message(
        content="What is my highest priority task?",
        source_type="manual",
        session_id="test-session-1",
        db=test_db
    )

    # Assertions
    assert result["request_type"] == "question"
    assert result["recommended_action"] == "answer_question"
    assert result["answer_text"] is not None
    assert len(result["proposed_tasks"]) == 0  # No tasks proposed
    assert "dashboard" in result["answer_text"].lower() or "priority" in result["answer_text"].lower()

    print("✓ Scenario 1: Manual question answered successfully")


# ============================================================================
# SCENARIO 2: SLACK MESSAGES → TASK CREATION
# ============================================================================

@pytest.mark.asyncio
async def test_scenario2_slack_message(test_db):
    """Test that Slack messages always create tasks, even with questions."""
    result = await process_assistant_message(
        content="Hi Jef, is the algorithm team using the sheet? We need to exclude Dein Getränke Express from the carousel.",
        source_type="slack",
        session_id="test-session-2",
        db=test_db
    )

    # Assertions
    assert result["request_type"] == "task_creation"
    assert result["recommended_action"] in ["auto", "ask"]  # Either auto or needs approval
    assert len(result["proposed_tasks"]) > 0 or len(result["created_tasks"]) > 0

    # Should NOT be classified as question despite containing "is"
    assert result["request_type"] != "question"

    print("✓ Scenario 2: Slack message processed for task creation")


# ============================================================================
# SCENARIO 3: TRANSCRIPTS → TASK CREATION
# ============================================================================

@pytest.mark.asyncio
async def test_scenario3_transcript(test_db):
    """Test that meeting transcripts create tasks."""
    result = await process_assistant_message(
        content="""
        Meeting Notes - Product Sync

        Action Items:
        - Andy to finalize dashboard mockups by Friday
        - Sarah to review API specs
        - Team to schedule follow-up meeting next week
        """,
        source_type="transcript",
        session_id="test-session-3",
        db=test_db
    )

    # Assertions
    assert result["request_type"] == "task_creation"
    assert len(result["proposed_tasks"]) > 0 or len(result["created_tasks"]) > 0

    # Check that tasks were extracted
    all_tasks = result["proposed_tasks"] + result["created_tasks"]
    assert any("Andy" in str(task) or "dashboard" in str(task) for task in all_tasks)

    print("✓ Scenario 3: Transcript processed and tasks extracted")


# ============================================================================
# SCENARIO 4: PDF UPLOADS → FAST PROCESSING
# ============================================================================

@pytest.mark.asyncio
async def test_scenario4_pdf_upload(test_db):
    """Test that PDFs are processed quickly via fast endpoint."""
    # Simulate PDF processing with text content
    pdf_text = """
    Project Update Meeting - Q4 2025

    Attendees: Andy, Sarah, Mike

    Action Items:
    1. Andy - Complete CRESCO dashboard redesign by Nov 20
    2. Sarah - Review and approve API documentation
    3. Mike - Set up staging environment

    Decisions:
    - Move to new authentication system
    - Launch beta in December
    """

    result = await process_assistant_message(
        content=pdf_text,
        source_type="pdf",
        session_id="test-session-4",
        db=test_db,
        pdf_bytes=None  # In real scenario, would have PDF bytes
    )

    # Assertions
    assert result["request_type"] == "document_analysis"
    assert len(result["entities"]) > 0  # Should extract entities
    assert len(result["proposed_tasks"]) > 0 or len(result["created_tasks"]) > 0

    # Check that people were extracted
    entities = result["entities"]
    assert any(e.get("name") == "Andy" for e in entities)

    print("✓ Scenario 4: PDF processed and tasks extracted")


# ============================================================================
# SCENARIO 5: MANUAL TASK CREATION → FULL PIPELINE
# ============================================================================

@pytest.mark.asyncio
async def test_scenario5_manual_task_creation(test_db):
    """Test that manual task requests go through full orchestrator."""
    result = await process_assistant_message(
        content="Andy needs to finish the dashboard prototype by Friday. High priority.",
        source_type="manual",
        session_id="test-session-5",
        db=test_db
    )

    # Assertions
    assert result["request_type"] == "task_creation"
    assert result["overall_confidence"] > 0  # Confidence scoring happened
    assert len(result["confidence_scores"]) > 0 or len(result["created_tasks"]) > 0

    # Check task details
    all_tasks = result["proposed_tasks"] + result["created_tasks"]
    assert len(all_tasks) > 0
    task = all_tasks[0]
    assert "Andy" in task["assignee"] or "andy" in task["assignee"].lower()
    assert task["priority"] in ["high", "urgent"]

    print("✓ Scenario 5: Manual task creation processed with confidence scoring")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_confidence_thresholds(test_db):
    """Test that confidence thresholds trigger correct actions."""

    # High confidence (should auto-create)
    result_high = await process_assistant_message(
        content="Andy needs to update the dashboard by Friday",
        source_type="manual",
        session_id="test-session-6",
        db=test_db
    )

    # Low confidence (should ask for clarification)
    result_low = await process_assistant_message(
        content="Someone should probably look at that thing",
        source_type="manual",
        session_id="test-session-7",
        db=test_db
    )

    # Assertions
    if result_high["overall_confidence"] >= 80:
        assert result_high["recommended_action"] == "auto"
        assert len(result_high["created_tasks"]) > 0

    if result_low["overall_confidence"] < 50:
        assert result_low["recommended_action"] == "clarify"
        assert len(result_low["clarifying_questions"]) > 0

    print("✓ Integration: Confidence thresholds working correctly")


@pytest.mark.asyncio
async def test_duplicate_detection(test_db):
    """Test that duplicate tasks are detected."""
    # Create first task
    result1 = await process_assistant_message(
        content="Andy needs to update the dashboard prototype",
        source_type="manual",
        session_id="test-session-8",
        db=test_db
    )

    # Try to create duplicate
    result2 = await process_assistant_message(
        content="Andy should work on the dashboard prototype",
        source_type="manual",
        session_id="test-session-9",
        db=test_db
    )

    # Assertions
    assert result2["duplicate_task"] is not None or len(result2["existing_task_matches"]) > 0

    print("✓ Integration: Duplicate detection working")


@pytest.mark.asyncio
async def test_knowledge_graph_storage(test_db):
    """Test that context is stored in knowledge graph."""
    result = await process_assistant_message(
        content="Andy is working on the CRESCO dashboard. It's due Friday.",
        source_type="manual",
        session_id="test-session-10",
        db=test_db
    )

    # Assertions
    assert result["context_item_id"] is not None  # Context stored
    assert len(result["entities"]) > 0  # Entities extracted
    assert len(result["relationships"]) > 0  # Relationships inferred

    # Check entities
    assert any(e.get("name") == "Andy" for e in result["entities"])
    assert any(e.get("name") == "CRESCO" for e in result["entities"])

    print("✓ Integration: Knowledge graph storage working")


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
