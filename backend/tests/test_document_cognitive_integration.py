"""
Tests for Document-Cognitive Nexus Integration
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import asdict

from services.document_cognitive_integration import DocumentCognitiveIntegration
from agents.advanced_pdf_processor import (
    ProcessedDocument,
    PDFMetadata,
    DocumentSection
)
from agents.document_analyzer import (
    DocumentAnalysis,
    DocumentSummary,
    ExtractedEntities
)


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = Mock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def sample_processed_doc():
    """Create sample ProcessedDocument"""
    return ProcessedDocument(
        raw_text="Meeting notes about Q4 planning with John Smith and Sarah Johnson.",
        structured_sections=[
            DocumentSection(
                section_type="heading",
                content="Q4 Planning Meeting",
                page_number=1,
                level=1
            )
        ],
        tables=[],
        metadata=PDFMetadata(
            title="Q4 Planning",
            author="John Smith",
            page_count=1,
            has_tables=False,
            has_images=False,
            file_size_bytes=50000
        ),
        chunks=[{
            "content": "Meeting notes about Q4 planning...",
            "page_start": 1,
            "page_end": 1,
            "size": 100
        }],
        summary_stats={
            "total_sections": 1,
            "total_tables": 0,
            "word_count": 50
        }
    )


@pytest.fixture
def sample_analysis():
    """Create sample DocumentAnalysis"""
    return DocumentAnalysis(
        summary=DocumentSummary(
            executive_summary="Q4 planning meeting discussing revenue targets.",
            key_points=["Q4 target: $2M", "New product launch"],
            document_type="meeting_notes",
            topics=["planning", "revenue"],
            confidence=0.9
        ),
        entities=ExtractedEntities(
            people=["John Smith", "Sarah Johnson"],
            organizations=["Engineering Team"],
            dates=["2025-11-30"],
            locations=["Conference Room A"],
            key_decisions=["Approved budget"],
            action_items=["Prepare proposal"]
        ),
        context={},
        inference_time_ms=5000,
        model_used="qwen2.5:7b-instruct"
    )


class TestDocumentCognitiveIntegration:
    """Test Document-Cognitive Nexus integration"""

    def test_build_context_text(
        self,
        mock_db_session,
        sample_processed_doc,
        sample_analysis
    ):
        """Test context text building from document"""
        integration = DocumentCognitiveIntegration(mock_db_session)

        context_text = integration._build_context_text(
            sample_processed_doc,
            sample_analysis
        )

        # Should include metadata
        assert "Document: Q4 Planning" in context_text
        assert "Author: John Smith" in context_text

        # Should include summary
        assert "Q4 planning meeting" in context_text

        # Should include entities
        assert "John Smith" in context_text
        assert "Sarah Johnson" in context_text

    @pytest.mark.asyncio
    async def test_enrich_document_with_entities(
        self,
        mock_db_session,
        sample_analysis
    ):
        """Test entity enrichment conversion"""
        integration = DocumentCognitiveIntegration(mock_db_session)

        entities = await integration.enrich_document_with_entities(sample_analysis)

        # Should convert people to PERSON entities
        person_entities = [e for e in entities if e["type"] == "PERSON"]
        assert len(person_entities) == 2
        assert any(e["name"] == "John Smith" for e in person_entities)

        # Should convert organizations to TEAM entities
        team_entities = [e for e in entities if e["type"] == "TEAM"]
        assert len(team_entities) == 1
        assert team_entities[0]["name"] == "Engineering Team"

        # Should convert dates to DATE entities
        date_entities = [e for e in entities if e["type"] == "DATE"]
        assert len(date_entities) == 1

    @pytest.mark.asyncio
    async def test_get_existing_tasks(self, mock_db_session):
        """Test fetching existing tasks"""
        # Mock task results
        mock_task = Mock()
        mock_task.id = "task-1"
        mock_task.title = "Test Task"
        mock_task.assignee = "John"
        mock_task.value_stream = "Planning"
        mock_task.description = "Test description"
        mock_task.status = "todo"
        mock_task.due_date = "2025-11-30"

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_task]
        mock_db_session.execute.return_value = mock_result

        integration = DocumentCognitiveIntegration(mock_db_session)
        tasks = await integration._get_existing_tasks()

        assert len(tasks) == 1
        assert tasks[0]["id"] == "task-1"
        assert tasks[0]["title"] == "Test Task"

    @pytest.mark.asyncio
    @patch('services.document_cognitive_integration.process_context')
    async def test_process_document_with_knowledge_graph(
        self,
        mock_process_context,
        mock_db_session,
        sample_processed_doc,
        sample_analysis
    ):
        """Test full document processing with KG integration"""
        # Mock Cognitive Nexus response
        mock_process_context.return_value = {
            "extracted_entities": [
                {"name": "John Smith", "type": "PERSON", "confidence": 0.9},
                {"name": "Engineering Team", "type": "TEAM", "confidence": 0.9}
            ],
            "inferred_relationships": [
                {
                    "subject": "John Smith",
                    "predicate": "WORKS_ON",
                    "object": "Q4 Planning",
                    "confidence": 0.8
                }
            ],
            "task_operations": [
                {
                    "operation": "CREATE",
                    "data": {
                        "title": "Test Task",
                        "assignee": "John Smith"
                    }
                }
            ],
            "entity_quality": 0.9,
            "relationship_quality": 0.85,
            "task_quality": 0.88,
            "context_complexity": 0.6,
            "extraction_strategy": "detailed",
            "reasoning_steps": ["Step 1", "Step 2"]
        }

        # Mock context item creation
        mock_context_item = Mock()
        mock_context_item.id = 1

        # Mock entity creation
        mock_entity = Mock()
        mock_entity.id = 1

        # Patch ContextItem and Entity creation
        with patch('services.document_cognitive_integration.ContextItem') as MockContextItem, \
             patch('services.document_cognitive_integration.Entity') as MockEntity, \
             patch('services.document_cognitive_integration.KnowledgeGraphService'):

            MockContextItem.return_value = mock_context_item
            MockEntity.return_value = mock_entity

            integration = DocumentCognitiveIntegration(mock_db_session)

            # Mock get_existing_tasks
            with patch.object(integration, '_get_existing_tasks', return_value=[]):
                result = await integration.process_document_with_knowledge_graph(
                    processed_doc=sample_processed_doc,
                    analysis=sample_analysis,
                    document_id="test-doc-1",
                    source_identifier="test.pdf"
                )

            # Verify results
            assert result["context_item_id"] == 1
            assert result["entities_extracted"] == 2
            assert result["relationships_inferred"] >= 0
            assert result["quality_metrics"]["entity_quality"] == 0.9
            assert result["extraction_strategy"] == "detailed"
            assert len(result["reasoning_steps"]) == 2

            # Verify Cognitive Nexus was called
            mock_process_context.assert_called_once()


class TestEntityMapping:
    """Test entity type mapping"""

    @pytest.mark.asyncio
    async def test_person_entity_mapping(self, mock_db_session):
        """Test people are mapped to PERSON entities"""
        analysis = DocumentAnalysis(
            summary=Mock(),
            entities=ExtractedEntities(
                people=["Alice", "Bob"],
                organizations=[],
                dates=[],
                locations=[],
                key_decisions=[],
                action_items=[]
            ),
            context={},
            inference_time_ms=1000,
            model_used="test"
        )

        integration = DocumentCognitiveIntegration(mock_db_session)
        entities = await integration.enrich_document_with_entities(analysis)

        person_entities = [e for e in entities if e["type"] == "PERSON"]
        assert len(person_entities) == 2
        assert person_entities[0]["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_organization_entity_mapping(self, mock_db_session):
        """Test organizations are mapped to TEAM entities"""
        analysis = DocumentAnalysis(
            summary=Mock(),
            entities=ExtractedEntities(
                people=[],
                organizations=["Acme Corp", "Engineering"],
                dates=[],
                locations=[],
                key_decisions=[],
                action_items=[]
            ),
            context={},
            inference_time_ms=1000,
            model_used="test"
        )

        integration = DocumentCognitiveIntegration(mock_db_session)
        entities = await integration.enrich_document_with_entities(analysis)

        team_entities = [e for e in entities if e["type"] == "TEAM"]
        assert len(team_entities) == 2
        assert team_entities[0]["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_date_entity_mapping(self, mock_db_session):
        """Test dates are mapped to DATE entities"""
        analysis = DocumentAnalysis(
            summary=Mock(),
            entities=ExtractedEntities(
                people=[],
                organizations=[],
                dates=["2025-11-30", "next Friday"],
                locations=[],
                key_decisions=[],
                action_items=[]
            ),
            context={},
            inference_time_ms=1000,
            model_used="test"
        )

        integration = DocumentCognitiveIntegration(mock_db_session)
        entities = await integration.enrich_document_with_entities(analysis)

        date_entities = [e for e in entities if e["type"] == "DATE"]
        assert len(date_entities) == 2
        assert date_entities[0]["confidence"] == 0.85


# Manual integration test
async def manual_integration_test():
    """
    Manual test with real database and Cognitive Nexus

    Requires:
    - Running backend
    - Ollama with Qwen 2.5
    - Sample PDF

    Usage:
        python -m pytest backend/tests/test_document_cognitive_integration.py::manual_integration_test -v
    """
    from pathlib import Path
    from agents.advanced_pdf_processor import AdvancedPDFProcessor
    from agents.document_analyzer import DocumentAnalyzer
    from db.database import get_db

    # Read PDF
    pdf_path = Path("test_files/sample_meeting.pdf")
    if not pdf_path.exists():
        pytest.skip("Sample PDF not found")

    pdf_bytes = pdf_path.read_bytes()

    # Process
    processor = AdvancedPDFProcessor()
    doc = await processor.process_document(pdf_bytes)

    # Analyze
    analyzer = DocumentAnalyzer("http://localhost:11434", "qwen2.5:7b-instruct")
    analysis = await analyzer.analyze_document(doc)

    # Integrate with knowledge graph
    async for db in get_db():
        integration = DocumentCognitiveIntegration(db)
        result = await integration.process_document_with_knowledge_graph(
            processed_doc=doc,
            analysis=analysis,
            source_identifier="test_meeting.pdf"
        )

        print(f"\n=== Knowledge Graph Integration Result ===")
        print(f"Context Item ID: {result['context_item_id']}")
        print(f"Entities: {result['entities_extracted']}")
        print(f"Relationships: {result['relationships_inferred']}")
        print(f"Tasks Created: {result['tasks_created']}")
        print(f"Quality Metrics: {result['quality_metrics']}")
        print(f"Reasoning Steps: {len(result['reasoning_steps'])}")

        break  # Only use first db session


if __name__ == "__main__":
    import asyncio
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "manual":
        asyncio.run(manual_integration_test())
    else:
        print("Usage: python test_document_cognitive_integration.py manual")
        print("   Or: pytest test_document_cognitive_integration.py")
