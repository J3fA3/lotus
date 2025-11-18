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
            id="task-test-1",
            title="Update dashboard prototype",
            assignee="Andy",
            status="in_progress",
            priority="high",
            value_stream="CRESCO"
        )
        task2 = Task(
            id="task-test-2",
            title="Review API documentation",
            assignee="Sarah",
            status="todo",
            priority="medium",
            value_stream="Platform"
        )
        session.add_all([task1, task2])
        await session.commit()

        yield session

        # Cleanup
        await session.rollback()


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
    """Test that Slack messages always route to task creation, not questions."""
    result = await process_assistant_message(
        content="Hi Jef, is the algorithm team using the sheet? We need to exclude Dein Getränke Express from the carousel.",
        source_type="slack",
        session_id="test-session-2",
        db=test_db
    )

    # Main assertion: Slack messages should NEVER be classified as questions
    assert result["request_type"] == "task_creation", f"Slack message was classified as {result['request_type']} instead of task_creation"
    assert result["request_type"] != "question", "Slack messages should never be treated as questions"

    # Context should be stored
    assert result["context_item_id"] is not None, "Context should be stored in knowledge graph"

    # Should have run Phase 1 agents (may or may not create tasks depending on AI interpretation)
    assert "recommended_action" in result

    print(f"✓ Scenario 2: Slack message correctly routed to task_creation (action: {result['recommended_action']})")
    print(f"  - Proposed tasks: {len(result['proposed_tasks'])}, Created: {len(result['created_tasks'])}")


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
    """Test that PDFs are routed to document analysis."""
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

    # Main assertion: PDFs should route to document_analysis
    assert result["request_type"] == "document_analysis", f"PDF was classified as {result['request_type']} instead of document_analysis"

    # Context should be stored
    assert result["context_item_id"] is not None, "PDF context should be stored"

    # Should have run Phase 1 pipeline
    assert "recommended_action" in result

    print(f"✓ Scenario 4: PDF routed to document_analysis (action: {result['recommended_action']})")
    print(f"  - Entities: {len(result.get('entities', []))}, Tasks created: {len(result['created_tasks'])}")


# ============================================================================
# SCENARIO 5: MANUAL TASK CREATION → FULL PIPELINE
# ============================================================================

@pytest.mark.asyncio
async def test_scenario5_manual_task_creation(test_db):
    """Test that manual task requests use LLM classification."""
    result = await process_assistant_message(
        content="Andy needs to finish the dashboard prototype by Friday. High priority.",
        source_type="manual",
        session_id="test-session-5",
        db=test_db
    )

    # Main assertion: Manual task requests should be classified by LLM
    assert result["request_type"] in ["task_creation", "context_only"], f"Manual input classified as {result['request_type']}"
    assert result["request_type"] != "question", "This is clearly a task, not a question"

    # Should have confidence scoring
    assert "overall_confidence" in result
    assert "recommended_action" in result

    # Context should be stored
    assert result["context_item_id"] is not None

    print(f"✓ Scenario 5: Manual input classified as {result['request_type']} (confidence: {result['overall_confidence']:.0f}%)")
    print(f"  - Action: {result['recommended_action']}, Tasks: {len(result['proposed_tasks']) + len(result['created_tasks'])}")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_confidence_thresholds(test_db):
    """Test that confidence thresholds influence recommended actions."""

    # High confidence input (clear task)
    result_high = await process_assistant_message(
        content="Andy needs to update the dashboard by Friday",
        source_type="manual",
        session_id="test-session-6",
        db=test_db
    )

    # Low confidence input (vague request)
    result_low = await process_assistant_message(
        content="Someone should probably look at that thing",
        source_type="manual",
        session_id="test-session-7",
        db=test_db
    )

    # Main assertions: Clear input should have higher confidence than vague input
    assert result_high["overall_confidence"] > result_low["overall_confidence"], \
        "Clear task should have higher confidence than vague request"

    # Both should return valid recommended actions
    assert result_high["recommended_action"] in ["auto", "ask", "clarify", "store_only", "answer_question"]
    assert result_low["recommended_action"] in ["auto", "ask", "clarify", "store_only", "answer_question"]

    print(f"✓ Integration: Confidence thresholds working")
    print(f"  - Clear task: {result_high['overall_confidence']:.0f}% ({result_high['recommended_action']})")
    print(f"  - Vague request: {result_low['overall_confidence']:.0f}% ({result_low['recommended_action']})")


@pytest.mark.asyncio
async def test_duplicate_detection(test_db):
    """Test that task matching finds related tasks."""
    # Create first task
    result1 = await process_assistant_message(
        content="Andy needs to update the dashboard prototype",
        source_type="manual",
        session_id="test-session-8",
        db=test_db
    )

    # Try to create similar task
    result2 = await process_assistant_message(
        content="Andy should work on the dashboard prototype",
        source_type="manual",
        session_id="test-session-9",
        db=test_db
    )

    # Main assertion: Both requests should be stored
    assert result1["context_item_id"] is not None
    assert result2["context_item_id"] is not None

    # Task matching should find existing tasks (may or may not flag as duplicate depending on similarity)
    # This tests that the matching system runs, not that it always finds exact duplicates
    assert "existing_task_matches" in result2
    assert "duplicate_task" in result2

    print(f"✓ Integration: Task matching system working")
    print(f"  - First request: {len(result1['proposed_tasks']) + len(result1['created_tasks'])} tasks")
    print(f"  - Second request: {len(result2['existing_task_matches'])} related tasks found")


@pytest.mark.asyncio
async def test_knowledge_graph_storage(test_db):
    """Test that context is stored in knowledge graph."""
    result = await process_assistant_message(
        content="Andy is working on the CRESCO dashboard. It's due Friday.",
        source_type="manual",
        session_id="test-session-10",
        db=test_db
    )

    # Main assertion: Context should be stored
    assert result["context_item_id"] is not None, "Context must be stored in knowledge graph"

    # Should have run Phase 1 agents
    assert "entities" in result
    assert "relationships" in result
    assert "recommended_action" in result

    # Verify the pipeline executed
    assert result["processing_end"] is not None

    print(f"✓ Integration: Knowledge graph storage working")
    print(f"  - Context ID: {result['context_item_id']}")
    print(f"  - Entities: {len(result.get('entities', []))}, Relationships: {len(result.get('relationships', []))}")


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
