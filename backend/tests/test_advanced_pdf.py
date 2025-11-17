"""
Tests for Advanced PDF Processing and Document Analysis
"""
import pytest
import asyncio
from pathlib import Path
from agents.advanced_pdf_processor import (
    AdvancedPDFProcessor,
    PDFMetadata,
    DocumentSection,
    ProcessedDocument
)
from agents.document_analyzer import DocumentAnalyzer


@pytest.fixture
def sample_pdf_bytes():
    """
    Create a simple PDF for testing
    In real tests, you would load an actual PDF file
    """
    # For now, return a minimal PDF structure
    # In production, use: Path("test_files/sample.pdf").read_bytes()
    return b"%PDF-1.4 minimal test content"


class TestAdvancedPDFProcessor:
    """Test cases for AdvancedPDFProcessor"""

    def test_validate_pdf_empty(self):
        """Test PDF validation with empty bytes"""
        result = AdvancedPDFProcessor.validate_pdf(b"")
        assert result is False

    def test_validate_pdf_invalid(self):
        """Test PDF validation with invalid content"""
        result = AdvancedPDFProcessor.validate_pdf(b"not a pdf")
        assert result is False

    def test_max_file_size_limit(self):
        """Test file size limit constant"""
        assert AdvancedPDFProcessor.MAX_FILE_SIZE == 10 * 1024 * 1024

    def test_chunk_size_constants(self):
        """Test chunking constants"""
        assert AdvancedPDFProcessor.MAX_CHUNK_SIZE == 4000
        assert AdvancedPDFProcessor.MIN_CHUNK_SIZE == 500

    def test_table_to_markdown_simple(self):
        """Test table to markdown conversion"""
        table = [
            ["Name", "Age", "City"],
            ["Alice", "30", "NYC"],
            ["Bob", "25", "LA"]
        ]

        markdown = AdvancedPDFProcessor._table_to_markdown(table)

        assert "Name" in markdown
        assert "Alice" in markdown
        assert "|" in markdown
        assert "---" in markdown

    def test_table_to_markdown_empty(self):
        """Test empty table handling"""
        markdown = AdvancedPDFProcessor._table_to_markdown([])
        assert markdown == ""

    def test_classify_text_block_heading(self):
        """Test heading detection"""
        block = {
            "lines": [{
                "spans": [{
                    "text": "Introduction",
                    "size": 18.0
                }]
            }]
        }

        section_type, level = AdvancedPDFProcessor._classify_text_block(
            "Introduction",
            block
        )

        assert section_type == "heading"
        assert level == 1

    def test_classify_text_block_list(self):
        """Test list item detection"""
        block = {
            "lines": [{
                "spans": [{
                    "text": "1. First item",
                    "size": 11.0
                }]
            }]
        }

        section_type, level = AdvancedPDFProcessor._classify_text_block(
            "1. First item",
            block
        )

        assert section_type == "list"

    def test_classify_text_block_paragraph(self):
        """Test paragraph detection"""
        block = {
            "lines": [{
                "spans": [{
                    "text": "This is a long paragraph with multiple sentences.",
                    "size": 11.0
                }]
            }]
        }

        section_type, level = AdvancedPDFProcessor._classify_text_block(
            "This is a long paragraph with multiple sentences.",
            block
        )

        assert section_type == "paragraph"

    def test_parse_pdf_date_valid(self):
        """Test PDF date parsing"""
        pdf_date = "D:20251115143000"
        result = AdvancedPDFProcessor._parse_pdf_date(pdf_date)

        assert result is not None
        assert "2025-11-15" in result
        assert "14:30:00" in result

    def test_parse_pdf_date_invalid(self):
        """Test invalid PDF date"""
        result = AdvancedPDFProcessor._parse_pdf_date("invalid")
        assert result is None

    def test_get_avg_font_size(self):
        """Test average font size calculation"""
        block = {
            "lines": [
                {"spans": [{"size": 12.0}, {"size": 14.0}]},
                {"spans": [{"size": 13.0}]}
            ]
        }

        avg = AdvancedPDFProcessor._get_avg_font_size(block)
        assert avg == 13.0  # (12 + 14 + 13) / 3

    def test_get_avg_font_size_empty(self):
        """Test font size with no spans"""
        block = {"lines": []}
        avg = AdvancedPDFProcessor._get_avg_font_size(block)
        assert avg == 11.0  # Default

    @pytest.mark.asyncio
    async def test_process_document_empty_bytes(self):
        """Test processing with empty bytes"""
        with pytest.raises(ValueError, match="PDF bytes cannot be empty"):
            await AdvancedPDFProcessor.process_document(b"")

    @pytest.mark.asyncio
    async def test_process_document_too_large(self):
        """Test file size validation"""
        large_bytes = b"x" * (11 * 1024 * 1024)  # 11MB
        with pytest.raises(ValueError, match="PDF file too large"):
            await AdvancedPDFProcessor.process_document(large_bytes)


class TestDocumentAnalyzer:
    """Test cases for DocumentAnalyzer"""

    @pytest.fixture
    def analyzer(self):
        """Create DocumentAnalyzer instance"""
        return DocumentAnalyzer(
            ollama_base_url="http://localhost:11434",
            model="qwen2.5:7b-instruct"
        )

    def test_extract_json_valid(self, analyzer):
        """Test JSON extraction from response"""
        response = 'Some text {"key": "value"} more text'
        result = analyzer._extract_json(response)
        assert result == '{"key": "value"}'

    def test_extract_json_array(self, analyzer):
        """Test JSON array extraction"""
        response = 'Text before [{"item": 1}, {"item": 2}] after'
        result = analyzer._extract_json(response)
        assert '{"item": 1}' in result

    def test_extract_json_none(self, analyzer):
        """Test extraction with no JSON"""
        response = 'Just plain text without any JSON'
        result = analyzer._extract_json(response)
        assert result is None

    def test_parse_summary_response_valid(self, analyzer):
        """Test summary parsing"""
        response = """{
            "executive_summary": "This is a test summary",
            "key_points": ["Point 1", "Point 2"],
            "document_type": "meeting_notes",
            "topics": ["planning", "strategy"],
            "confidence": 0.9
        }"""

        summary = analyzer._parse_summary_response(response)

        assert summary.executive_summary == "This is a test summary"
        assert len(summary.key_points) == 2
        assert summary.document_type == "meeting_notes"
        assert summary.confidence == 0.9

    def test_parse_summary_response_invalid(self, analyzer):
        """Test summary parsing with invalid JSON"""
        response = "Not valid JSON at all"
        summary = analyzer._parse_summary_response(response)

        assert summary.executive_summary != ""
        assert summary.confidence == 0.5  # Low confidence fallback

    def test_parse_entity_response_valid(self, analyzer):
        """Test entity extraction parsing"""
        response = """{
            "people": ["Alice Smith", "Bob Jones"],
            "organizations": ["Acme Corp"],
            "dates": ["2025-11-15"],
            "locations": ["San Francisco"],
            "key_decisions": ["Approved budget"],
            "action_items": ["Schedule meeting"]
        }"""

        entities = analyzer._parse_entity_response(response)

        assert len(entities.people) == 2
        assert "Alice Smith" in entities.people
        assert len(entities.organizations) == 1
        assert "Acme Corp" in entities.organizations

    def test_parse_entity_response_invalid(self, analyzer):
        """Test entity parsing with invalid JSON"""
        response = "Invalid JSON"
        entities = analyzer._parse_entity_response(response)

        assert entities.people == []
        assert entities.organizations == []
        assert entities.dates == []

    def test_parse_task_response_valid(self, analyzer):
        """Test task parsing"""
        response = """{
            "tasks": [
                {
                    "title": "Complete project proposal",
                    "description": "Draft and submit Q4 proposal",
                    "dueDate": "2025-11-30",
                    "valueStream": "Planning"
                }
            ]
        }"""

        tasks = analyzer._parse_task_response(response, "John Doe")

        assert len(tasks) == 1
        assert tasks[0]["title"] == "Complete project proposal"
        assert tasks[0]["assignee"] == "John Doe"
        assert tasks[0]["status"] == "todo"

    def test_parse_task_response_no_title(self, analyzer):
        """Test task parsing skips tasks without titles"""
        response = """{
            "tasks": [
                {"description": "No title"},
                {"title": "Valid task"}
            ]
        }"""

        tasks = analyzer._parse_task_response(response, "User")

        assert len(tasks) == 1
        assert tasks[0]["title"] == "Valid task"

    def test_constants(self, analyzer):
        """Test analyzer constants"""
        assert analyzer.DEFAULT_TEMPERATURE == 0.3
        assert analyzer.DEFAULT_TOP_P == 0.9
        assert analyzer.DEFAULT_MAX_TOKENS == 2000
        assert analyzer.REQUEST_TIMEOUT == 180.0


class TestIntegration:
    """Integration tests for the full pipeline"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires actual PDF file and Ollama running")
    async def test_full_pipeline(self):
        """
        Full integration test with real PDF
        This requires:
        1. A sample PDF file
        2. Ollama running with qwen2.5:7b-instruct
        """
        # Load real PDF
        pdf_path = Path("test_files/sample_meeting_notes.pdf")
        if not pdf_path.exists():
            pytest.skip("Sample PDF not found")

        pdf_bytes = pdf_path.read_bytes()

        # Process PDF
        processor = AdvancedPDFProcessor()
        processed_doc = await processor.process_document(pdf_bytes)

        # Verify structure extraction
        assert processed_doc.metadata.page_count > 0
        assert len(processed_doc.structured_sections) > 0
        assert processed_doc.raw_text != ""

        # Analyze document
        analyzer = DocumentAnalyzer(
            "http://localhost:11434",
            "qwen2.5:7b-instruct"
        )
        analysis = await analyzer.analyze_document(processed_doc)

        # Verify analysis
        assert analysis.summary.executive_summary != ""
        assert len(analysis.summary.key_points) > 0
        assert analysis.summary.document_type != "unknown"

        # Extract tasks
        task_result = await analyzer.extract_tasks_with_context(
            processed_doc,
            "Test User"
        )

        assert "tasks" in task_result
        assert "context" in task_result


# Utility function for manual testing
async def manual_test_with_file(pdf_path: str):
    """
    Manual test with actual PDF file

    Usage:
        python -m pytest backend/tests/test_advanced_pdf.py::manual_test_with_file
    """
    from pathlib import Path

    print(f"\n=== Testing with {pdf_path} ===\n")

    # Read PDF
    pdf_bytes = Path(pdf_path).read_bytes()
    print(f"File size: {len(pdf_bytes)} bytes")

    # Process
    processor = AdvancedPDFProcessor()
    doc = await processor.process_document(pdf_bytes)

    print(f"\nMetadata:")
    print(f"  Title: {doc.metadata.title}")
    print(f"  Author: {doc.metadata.author}")
    print(f"  Pages: {doc.metadata.page_count}")
    print(f"  Has tables: {doc.metadata.has_tables}")

    print(f"\nStatistics:")
    print(f"  Sections: {doc.summary_stats['total_sections']}")
    print(f"  Tables: {doc.summary_stats['total_tables']}")
    print(f"  Words: {doc.summary_stats['word_count']}")
    print(f"  Chunks: {doc.summary_stats['total_chunks']}")

    if doc.tables:
        print(f"\nFirst table:")
        print(doc.tables[0]['markdown'][:200])

    # Analyze
    analyzer = DocumentAnalyzer("http://localhost:11434", "qwen2.5:7b-instruct")
    analysis = await analyzer.analyze_document(doc)

    print(f"\nSummary:")
    print(f"  Type: {analysis.summary.document_type}")
    print(f"  Executive: {analysis.summary.executive_summary[:200]}...")
    print(f"  Key points: {len(analysis.summary.key_points)}")

    print(f"\nEntities:")
    print(f"  People: {analysis.entities.people}")
    print(f"  Organizations: {analysis.entities.organizations}")
    print(f"  Dates: {analysis.entities.dates}")

    print(f"\nProcessing time: {analysis.inference_time_ms}ms")


if __name__ == "__main__":
    # Run manual test if a PDF path is provided
    import sys
    if len(sys.argv) > 1:
        asyncio.run(manual_test_with_file(sys.argv[1]))
    else:
        print("Usage: python test_advanced_pdf.py <path_to_pdf>")
        print("   Or: pytest test_advanced_pdf.py")
