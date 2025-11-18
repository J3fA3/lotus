"""
Phase 3 Orchestrator Compilation Test

This script tests that the Phase 3 orchestrator graph compiles without errors.
Run this to verify the integration is successful before full testing.
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_graph_compilation():
    """Test that the orchestrator graph compiles successfully."""
    print("🔧 Testing Phase 3 Orchestrator Graph Compilation...")
    print("=" * 60)

    try:
        # Import the orchestrator
        from agents.orchestrator import create_orchestrator_graph

        print("✓ Orchestrator module imported successfully")

        # Create the graph
        print("\n📊 Compiling graph...")
        graph = create_orchestrator_graph()

        print("✓ Graph compiled successfully!")
        print("\n📋 Graph Structure:")
        print(f"   Nodes: {len(graph.nodes)} nodes")
        print(f"   Entry point: load_profile (Phase 3)")

        # Check that all expected nodes exist
        expected_nodes = [
            "load_profile",
            "classify",
            "answer",
            "run_phase1",
            "find_tasks",
            "check_enrichments",
            "enrich_proposals",
            "filter_relevance",
            "calculate_confidence",
            "generate_questions",
            "execute"
        ]

        print("\n🔍 Verifying nodes:")
        graph_nodes = list(graph.nodes.keys()) if hasattr(graph.nodes, 'keys') else graph.nodes
        for node_name in expected_nodes:
            if node_name in graph_nodes:
                print(f"   ✓ {node_name}")
            else:
                print(f"   ✗ {node_name} - MISSING!")
                raise Exception(f"Node {node_name} not found in graph")

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED - Graph is ready for use!")
        print("\nPhase 3 Enhancements Active:")
        print("  • User profile loading")
        print("  • Gemini-powered classification")
        print("  • Task enrichment checking")
        print("  • Relevance filtering")
        print("  • Natural comment generation")
        print("\nNext Steps:")
        print("  1. Set GOOGLE_AI_API_KEY in backend/.env")
        print("  2. Run database migration: python -m db.migrations.003_add_phase3_tables")
        print("  3. Start backend: uvicorn main:app --reload")
        print("  4. Test with real messages")

        return True

    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        print("\nMake sure you're in the backend directory and dependencies are installed:")
        print("  pip install -r requirements.txt")
        return False

    except Exception as e:
        print(f"\n❌ Compilation Error: {e}")
        print("\nCheck the orchestrator.py file for errors:")
        print("  - Verify all Phase 3 fields are defined in OrchestratorState")
        print("  - Check that all nodes are properly defined")
        print("  - Ensure all edges are correctly connected")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_graph_compilation())
    sys.exit(0 if result else 1)
