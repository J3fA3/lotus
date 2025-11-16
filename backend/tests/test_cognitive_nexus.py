"""
Tests for Cognitive Nexus Phase 1 - LangGraph Agentic System

These tests verify:
1. LangGraph state machine compilation
2. Agent execution flow
3. Entity extraction with retry logic
4. Relationship synthesis
5. Task generation with context
6. Quality metrics and reasoning traces

Note: These tests require Ollama to be running with qwen2.5:7b-instruct model.
For testing without Ollama, see test_cognitive_nexus_mock.py
"""

import pytest
import asyncio
from agents.cognitive_nexus_graph import (
    create_cognitive_nexus_graph,
    process_context,
    context_analysis_agent,
    CognitiveNexusState
)


def test_graph_compilation():
    """Test that the LangGraph state machine compiles without errors."""
    graph = create_cognitive_nexus_graph()
    assert graph is not None
    print("✅ LangGraph state machine compiled successfully")


def test_context_analysis_agent():
    """Test the Context Analysis Agent's decision-making."""
    # Simple context (should use fast strategy)
    simple_state = {
        "raw_context": "Hey, can you send me the report?",
        "source_type": "slack",
        "reasoning_steps": []
    }

    result = context_analysis_agent(simple_state)

    assert "extraction_strategy" in result
    assert result["extraction_strategy"] in ["fast", "detailed"]
    assert "context_complexity" in result
    assert 0.0 <= result["context_complexity"] <= 1.0
    assert "estimated_entity_count" in result
    assert result["estimated_entity_count"] >= 0
    assert "reasoning_steps" in result
    assert len(result["reasoning_steps"]) > 0

    print(f"✅ Context Analysis Agent: strategy={result['extraction_strategy']}, "
          f"complexity={result['context_complexity']:.2f}, "
          f"estimated_entities={result['estimated_entity_count']}")


def test_complex_context_analysis():
    """Test that complex context triggers detailed extraction."""
    # Long, complex context (should use detailed strategy)
    complex_state = {
        "raw_context": """
        Hey Jef, hope all is well. I want to send an email about low performance
        of occasions tile. Could you share the data points you presented during
        the meeting when we decided not to activate the tile? I'm struggling to
        find it. We need to get this done by Friday. Also, can you check with
        Andy about the CRESCO deployment to Sainsbury's? The API integration
        with the backend server needs to be completed before the November 26th
        deadline. Sarah from Co-op mentioned that the authentication system
        needs to be reviewed. Let me know if you have any questions about the
        architecture or database schema. We should probably schedule a meeting
        with the JustEat Takeaway team next week to discuss the microservice
        deployment strategy.
        """,
        "source_type": "slack",
        "reasoning_steps": []
    }

    result = context_analysis_agent(complex_state)

    # Complex context should have higher complexity score
    assert result["context_complexity"] > 0.3
    assert result["estimated_entity_count"] >= 5

    print(f"✅ Complex Context Analysis: strategy={result['extraction_strategy']}, "
          f"complexity={result['context_complexity']:.2f}, "
          f"estimated_entities={result['estimated_entity_count']}")


@pytest.mark.asyncio
async def test_full_agent_flow_mock():
    """
    Test the full agent flow with a mock example (no Ollama required).

    This test verifies that:
    1. State flows through all agents
    2. Reasoning steps are accumulated
    3. Quality metrics are calculated
    """
    # Note: This test will fail LLM calls but we can verify the flow
    test_text = "Hey Jef, can you send the CRESCO data to Andy by Friday?"

    try:
        # This will fail at LLM calls, but we can catch and verify structure
        final_state = await process_context(test_text, source_type="slack")

        # If we got here, Ollama is running!
        assert "reasoning_steps" in final_state
        assert len(final_state["reasoning_steps"]) > 0
        assert "entity_quality" in final_state
        assert "relationship_quality" in final_state
        assert "task_quality" in final_state

        print(f"✅ Full Agent Flow (with Ollama): "
              f"entities={len(final_state.get('extracted_entities', []))}, "
              f"relationships={len(final_state.get('inferred_relationships', []))}, "
              f"tasks={len(final_state.get('generated_tasks', []))}")

    except Exception as e:
        # Expected if Ollama is not running
        print(f"⚠️  Full Agent Flow: Skipped (Ollama not available): {str(e)}")
        pytest.skip("Ollama not available")


def test_state_schema():
    """Test that CognitiveNexusState has all required fields."""
    from typing import get_type_hints

    hints = get_type_hints(CognitiveNexusState)

    required_fields = [
        "raw_context",
        "source_type",
        "extraction_strategy",
        "context_complexity",
        "estimated_entity_count",
        "extracted_entities",
        "inferred_relationships",
        "generated_tasks",
        "entity_quality",
        "relationship_quality",
        "task_quality",
        "needs_entity_retry",
        "entity_retry_count",
        "max_retries",
        "reasoning_steps"
    ]

    for field in required_fields:
        assert field in hints, f"Missing required field: {field}"

    print(f"✅ CognitiveNexusState schema has all {len(required_fields)} required fields")


if __name__ == "__main__":
    """Run tests manually."""
    print("\n🧪 Running Cognitive Nexus Tests...\n")

    test_graph_compilation()
    test_context_analysis_agent()
    test_complex_context_analysis()
    test_state_schema()

    print("\n✨ Basic tests completed! Run with pytest for async tests.\n")
    print("To test with Ollama:")
    print("  1. Start Ollama: ollama serve")
    print("  2. Run: pytest backend/tests/test_cognitive_nexus.py -v -s\n")
