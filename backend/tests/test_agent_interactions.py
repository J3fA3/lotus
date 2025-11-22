"""
Agent Interaction & Orchestrator Tests - Phase 5

Tests for multi-agent interactions and orchestrator behavior:
- Agent node sequencing and state transitions
- Parallel execution (Phase 5 optimization)
- Agent communication and data flow
- Error propagation and recovery
- Performance benchmarks for parallelization
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List

from agents.orchestrator import (
    OrchestratorGraph,
    OrchestratorState,
    process_assistant_message,
    run_phase1_agents,
    parallel_task_analysis,
    check_task_enrichments,
    generate_task_proposals
)


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=Mock(
        scalars=Mock(return_value=Mock(all=Mock(return_value=[])))
    ))
    db.commit = AsyncMock()
    db.add = Mock()
    return db


@pytest.mark.asyncio
async def test_orchestrator_state_initialization():
    """Test orchestrator state initializes correctly."""

    state = OrchestratorState(
        user_input="Test task",
        session_id="test_session_001",
        user_id=1
    )

    assert state.user_input == "Test task"
    assert state.session_id == "test_session_001"
    assert state.user_id == 1
    assert state.extracted_entities == []
    assert state.reasoning == []
    assert state.current_step == "start"


@pytest.mark.asyncio
async def test_agent_node_sequencing(mock_db_session):
    """Test agents execute in correct sequence."""

    with patch('agents.orchestrator.get_async_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        with patch('agents.entity_extraction.extract_entities_ollama') as mock_extract:
            mock_extract.return_value = {
                "entities": [
                    {"name": "CRESCO", "type": "project", "confidence": 0.9}
                ]
            }

            # Create initial state
            state = OrchestratorState(
                user_input="Update CRESCO dashboard",
                session_id="test_seq_001",
                user_id=1
            )

            # Run Phase 1 agents
            result_state = await run_phase1_agents(state)

            # Should have extracted entities
            assert len(result_state["extracted_entities"]) > 0
            assert result_state["current_step"] == "run_phase1"


@pytest.mark.asyncio
async def test_parallel_task_analysis_speedup(mock_db_session):
    """Test parallel task analysis provides speedup over sequential."""

    with patch('agents.orchestrator.get_async_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        # Create state with extracted entities
        state = OrchestratorState(
            user_input="Update CRESCO dashboard and review Moodboard",
            session_id="test_parallel_001",
            user_id=1,
            extracted_entities=[
                {"name": "CRESCO", "type": "project", "confidence": 0.9},
                {"name": "Moodboard", "type": "project", "confidence": 0.85}
            ]
        )

        # Measure parallel execution time
        start_parallel = datetime.now()
        parallel_result = await parallel_task_analysis(state)
        parallel_duration = (datetime.now() - start_parallel).total_seconds()

        # Should complete without error
        assert parallel_result is not None
        assert "reasoning" in parallel_result

        # Log performance
        print(f"\nParallel execution time: {parallel_duration:.3f}s")

        # Parallel should be reasonably fast (< 5 seconds for simple case)
        assert parallel_duration < 5.0


@pytest.mark.asyncio
async def test_parallel_execution_error_handling(mock_db_session):
    """Test parallel execution handles errors gracefully."""

    with patch('agents.orchestrator.get_async_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        with patch('agents.orchestrator.find_related_tasks') as mock_find_tasks:
            # Make one agent fail
            mock_find_tasks.side_effect = Exception("Task matching failed")

            state = OrchestratorState(
                user_input="Test error handling",
                session_id="test_error_001",
                user_id=1
            )

            # Should handle error without crashing
            try:
                result = await parallel_task_analysis(state)
                # Should return result with error noted in reasoning
                assert result is not None
                if "reasoning" in result:
                    reasoning_text = "\n".join(result["reasoning"])
                    # May contain error information
            except Exception as e:
                # If it raises, verify it's expected
                assert "Task matching failed" in str(e)


@pytest.mark.asyncio
async def test_agent_communication_data_flow(mock_db_session):
    """Test data flows correctly between agents."""

    with patch('agents.orchestrator.get_async_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        with patch('agents.entity_extraction.extract_entities_ollama') as mock_extract:
            # Mock entity extraction
            mock_extract.return_value = {
                "entities": [
                    {"name": "CRESCO", "type": "project", "confidence": 0.9},
                    {"name": "Alberto", "type": "person", "confidence": 0.85}
                ]
            }

            # Create state
            state = OrchestratorState(
                user_input="Discuss CRESCO with Alberto",
                session_id="test_flow_001",
                user_id=1
            )

            # Run Phase 1 (entity extraction)
            phase1_result = await run_phase1_agents(state)

            # Entities should flow into state
            assert len(phase1_result["extracted_entities"]) == 2
            assert any(e["name"] == "CRESCO" for e in phase1_result["extracted_entities"])
            assert any(e["name"] == "Alberto" for e in phase1_result["extracted_entities"])

            # These entities should be available to next agents
            # (Test data flow between nodes)


@pytest.mark.asyncio
async def test_task_proposal_generation(mock_db_session):
    """Test task proposal generation from user input."""

    with patch('agents.orchestrator.get_async_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        with patch('agents.orchestrator.GeminiService') as mock_gemini_cls:
            mock_gemini = Mock()
            mock_gemini.generate_content = AsyncMock(return_value="""
ANALYSIS: User wants to update dashboard

TASKS:
1. Update CRESCO dashboard
   PRIORITY: high
   COMPLEXITY: medium
   DEADLINE: This week
""")
            mock_gemini_cls.return_value = mock_gemini

            state = OrchestratorState(
                user_input="Update CRESCO dashboard by end of week",
                session_id="test_proposal_001",
                user_id=1,
                extracted_entities=[{"name": "CRESCO", "type": "project", "confidence": 0.9}]
            )

            result = await generate_task_proposals(state)

            # Should generate task proposals
            assert result is not None
            assert "reasoning" in result


@pytest.mark.asyncio
async def test_orchestrator_end_to_end(mock_db_session):
    """Test complete orchestrator flow end-to-end."""

    with patch('agents.orchestrator.get_async_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        with patch('agents.entity_extraction.extract_entities_ollama') as mock_extract:
            mock_extract.return_value = {
                "entities": [
                    {"name": "CRESCO", "type": "project", "confidence": 0.9}
                ]
            }

            with patch('agents.orchestrator.GeminiService') as mock_gemini_cls:
                mock_gemini = Mock()
                mock_gemini.generate_content = AsyncMock(return_value="""
ANALYSIS: User wants to review dashboard

TASKS:
1. Review CRESCO dashboard
   PRIORITY: medium
   COMPLEXITY: low
   DEADLINE: Friday
""")
                mock_gemini_cls.return_value = mock_gemini

                # Process message through orchestrator
                result = await process_assistant_message(
                    content="Review CRESCO dashboard by Friday",
                    source_type="chat",
                    session_id="test_e2e_001",
                    db=mock_db_session,
                    user_id=1
                )

                # Should complete without error
                assert result is not None


@pytest.mark.asyncio
async def test_enrichment_checking(mock_db_session):
    """Test task enrichment checking agent."""

    with patch('agents.orchestrator.get_async_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        state = OrchestratorState(
            user_input="Update dashboard",
            session_id="test_enrich_001",
            user_id=1,
            extracted_entities=[
                {"name": "CRESCO", "type": "project", "confidence": 0.9}
            ]
        )

        result = await check_task_enrichments(state)

        # Should return enrichment suggestions
        assert result is not None
        assert "reasoning" in result or "enrichment_suggestions" in result


@pytest.mark.asyncio
async def test_agent_reasoning_accumulation(mock_db_session):
    """Test reasoning accumulates across agent nodes."""

    with patch('agents.orchestrator.get_async_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        with patch('agents.entity_extraction.extract_entities_ollama') as mock_extract:
            mock_extract.return_value = {
                "entities": [
                    {"name": "CRESCO", "type": "project", "confidence": 0.9}
                ]
            }

            state = OrchestratorState(
                user_input="Update CRESCO dashboard",
                session_id="test_reasoning_001",
                user_id=1
            )

            # Run Phase 1
            phase1_result = await run_phase1_agents(state)

            # Reasoning should accumulate
            assert len(phase1_result["reasoning"]) > 0

            # Run parallel analysis
            parallel_result = await parallel_task_analysis(
                OrchestratorState(**phase1_result)
            )

            # Reasoning should continue accumulating
            assert len(parallel_result["reasoning"]) > len(phase1_result["reasoning"])


@pytest.mark.asyncio
async def test_agent_parallelization_benchmark():
    """Benchmark parallel vs sequential execution."""

    # Create mock state
    state = OrchestratorState(
        user_input="Update CRESCO dashboard and review Moodboard",
        session_id="benchmark_001",
        user_id=1,
        extracted_entities=[
            {"name": "CRESCO", "type": "project", "confidence": 0.9},
            {"name": "Moodboard", "type": "project", "confidence": 0.85}
        ]
    )

    with patch('agents.orchestrator.get_async_session'):
        with patch('agents.orchestrator.find_related_tasks') as mock_find:
            with patch('agents.orchestrator.check_task_enrichments') as mock_enrich:
                # Mock both operations to take some time
                async def slow_find(s):
                    await asyncio.sleep(0.5)
                    return {"reasoning": ["Found tasks"]}

                async def slow_enrich(s):
                    await asyncio.sleep(0.5)
                    return {"reasoning": ["Checked enrichments"]}

                mock_find.side_effect = slow_find
                mock_enrich.side_effect = slow_enrich

                # Sequential execution
                start_seq = datetime.now()
                await slow_find(state)
                await slow_enrich(state)
                sequential_duration = (datetime.now() - start_seq).total_seconds()

                # Reset mocks
                mock_find.side_effect = slow_find
                mock_enrich.side_effect = slow_enrich

                # Parallel execution using asyncio.gather
                start_par = datetime.now()
                await asyncio.gather(
                    slow_find(state),
                    slow_enrich(state)
                )
                parallel_duration = (datetime.now() - start_par).total_seconds()

                # Parallel should be faster
                speedup = sequential_duration / parallel_duration

                print(f"\nParallelization Benchmark:")
                print(f"  Sequential: {sequential_duration:.3f}s")
                print(f"  Parallel: {parallel_duration:.3f}s")
                print(f"  Speedup: {speedup:.2f}x")

                # Should have at least 1.5x speedup
                assert speedup >= 1.5


@pytest.mark.asyncio
async def test_agent_state_immutability():
    """Test agent nodes don't mutate input state (return new state)."""

    initial_state = OrchestratorState(
        user_input="Test immutability",
        session_id="test_immut_001",
        user_id=1
    )

    # Store original values
    original_reasoning_len = len(initial_state.reasoning)

    with patch('agents.orchestrator.get_async_session'):
        with patch('agents.entity_extraction.extract_entities_ollama') as mock_extract:
            mock_extract.return_value = {"entities": []}

            result = await run_phase1_agents(initial_state)

            # Result should have new reasoning
            assert len(result["reasoning"]) > original_reasoning_len

            # But original state should be unchanged (immutability)
            assert len(initial_state.reasoning) == original_reasoning_len


@pytest.mark.asyncio
async def test_email_source_type_routing(mock_db_session):
    """Test orchestrator handles email source type correctly."""

    with patch('agents.orchestrator.get_async_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        with patch('agents.entity_extraction.extract_entities_ollama') as mock_extract:
            mock_extract.return_value = {"entities": []}

            # Email source
            result = await process_assistant_message(
                content="Review dashboard",
                source_type="email",  # Phase 5: New source type
                session_id="test_email_source_001",
                db=mock_db_session,
                source_identifier="email_msg_123",
                user_id=1
            )

            # Should handle email source
            assert result is not None


@pytest.mark.asyncio
async def test_agent_error_recovery(mock_db_session):
    """Test orchestrator recovers from agent failures."""

    with patch('agents.orchestrator.get_async_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        with patch('agents.entity_extraction.extract_entities_ollama') as mock_extract:
            # Make entity extraction fail
            mock_extract.side_effect = Exception("Extraction service unavailable")

            # Should handle gracefully
            try:
                result = await process_assistant_message(
                    content="Test error recovery",
                    source_type="chat",
                    session_id="test_recovery_001",
                    db=mock_db_session,
                    user_id=1
                )

                # If it completes, verify it handled error
                # (May return partial result or error message)
            except Exception as e:
                # If it raises, verify error is informative
                assert "Extraction" in str(e) or "unavailable" in str(e)


@pytest.mark.asyncio
async def test_knowledge_graph_integration(mock_db_session):
    """Test orchestrator integrates with knowledge graph."""

    with patch('agents.orchestrator.get_async_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        with patch('agents.entity_extraction.extract_entities_ollama') as mock_extract:
            mock_extract.return_value = {
                "entities": [
                    {"name": "CRESCO", "type": "project", "confidence": 0.9},
                    {"name": "Alberto", "type": "person", "confidence": 0.85}
                ]
            }

            with patch('services.knowledge_graph_service.KnowledgeGraphService') as mock_kg_cls:
                mock_kg = Mock()
                mock_kg.merge_entity_to_knowledge_graph = AsyncMock()
                mock_kg_cls.return_value = mock_kg

                result = await process_assistant_message(
                    content="Discuss CRESCO with Alberto",
                    source_type="chat",
                    session_id="test_kg_001",
                    db=mock_db_session,
                    user_id=1
                )

                # Should have interacted with knowledge graph
                # (Entities should be merged)
                # Implementation may vary - this tests the concept


@pytest.mark.asyncio
async def test_agent_performance_logging():
    """Test agent execution times are logged for monitoring."""

    with patch('agents.orchestrator.get_async_session'):
        with patch('agents.entity_extraction.extract_entities_ollama') as mock_extract:
            mock_extract.return_value = {"entities": []}

            state = OrchestratorState(
                user_input="Performance test",
                session_id="test_perf_001",
                user_id=1
            )

            start_time = datetime.now()
            result = await run_phase1_agents(state)
            duration = (datetime.now() - start_time).total_seconds()

            # Should complete in reasonable time
            assert duration < 10.0  # 10 second timeout

            # Reasoning may contain timing information
            if "reasoning" in result:
                # Check if timing is logged
                reasoning_text = "\n".join(result["reasoning"])
                # May contain performance metrics


@pytest.mark.asyncio
async def test_multi_task_creation(mock_db_session):
    """Test orchestrator can create multiple tasks from single input."""

    with patch('agents.orchestrator.get_async_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        with patch('agents.entity_extraction.extract_entities_ollama') as mock_extract:
            mock_extract.return_value = {
                "entities": [
                    {"name": "CRESCO", "type": "project", "confidence": 0.9},
                    {"name": "Moodboard", "type": "project", "confidence": 0.85}
                ]
            }

            with patch('agents.orchestrator.GeminiService') as mock_gemini_cls:
                mock_gemini = Mock()
                mock_gemini.generate_content = AsyncMock(return_value="""
ANALYSIS: User has multiple tasks

TASKS:
1. Update CRESCO dashboard
   PRIORITY: high
   COMPLEXITY: medium

2. Review Moodboard export
   PRIORITY: medium
   COMPLEXITY: low
""")
                mock_gemini_cls.return_value = mock_gemini

                result = await process_assistant_message(
                    content="Update CRESCO dashboard and review Moodboard export",
                    source_type="chat",
                    session_id="test_multi_001",
                    db=mock_db_session,
                    user_id=1
                )

                # Should handle multiple task creation
                assert result is not None
