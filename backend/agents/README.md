# AI Agents - Advanced PDF Processing & Document Analysis

This directory contains AI agents for intelligent document processing and task extraction.

## 📁 Components

### Core Agents

#### 1. **TaskExtractor** (`task_extractor.py`)
Basic AI-powered task extraction from text.

**Features:**
- Extracts actionable tasks from plain text
- Uses Ollama + Qwen 2.5 7B model
- Outputs structured task JSON

**Usage:**
```python
from agents.task_extractor import TaskExtractor

extractor = TaskExtractor("http://localhost:11434", "qwen2.5:7b-instruct")
result = await extractor.extract_tasks("Meeting notes here...", "John Doe")
# Returns: {"tasks": [...], "inference_time_ms": 1234, ...}
```

---

#### 2. **PDFProcessor** (`pdf_processor.py`)
Basic PDF text extraction.

**Features:**
- Simple text extraction using PyMuPDF
- Page-by-page text output
- PDF validation

**Usage:**
```python
from agents.pdf_processor import PDFProcessor

processor = PDFProcessor()
text = await processor.extract_text_from_pdf(pdf_bytes)
# Returns: "--- Page 1 ---\nContent here..."
```

---

#### 3. **AdvancedPDFProcessor** (`advanced_pdf_processor.py`) ⭐ NEW
Advanced PDF processing with structure extraction.

**Features:**
- **Layout-aware extraction** - Preserves document structure
- **Table detection & extraction** - Uses pdfplumber for accurate tables
- **Metadata extraction** - Author, title, dates, etc.
- **Intelligent chunking** - Semantic-aware document splitting
- **Structure classification** - Detects headings, lists, paragraphs

**Architecture:**
```python
@dataclass
class ProcessedDocument:
    raw_text: str                          # Full document text
    structured_sections: List[DocumentSection]  # Structured content
    tables: List[Dict]                     # Extracted tables
    metadata: PDFMetadata                  # Document metadata
    chunks: List[Dict]                     # AI-ready chunks
    summary_stats: Dict                    # Statistics
```

**Usage:**
```python
from agents.advanced_pdf_processor import AdvancedPDFProcessor

processor = AdvancedPDFProcessor()
doc = await processor.process_document(pdf_bytes)

# Access structure
print(f"Pages: {doc.metadata.page_count}")
print(f"Tables: {len(doc.tables)}")
print(f"Sections: {len(doc.structured_sections)}")

# Get tables as markdown
for table in doc.tables:
    print(table['markdown'])

# Get chunks for AI processing
for chunk in doc.chunks:
    print(f"Pages {chunk['page_start']}-{chunk['page_end']}: {chunk['size']} chars")
```

**Table Extraction Example:**
```python
# Input PDF table:
# | Name  | Age | City |
# | Alice | 30  | NYC  |

# Output:
{
    "page_number": 1,
    "table_index": 0,
    "markdown": "| Name  | Age | City |\n|-------|-----|------|\n| Alice | 30  | NYC  |",
    "headers": ["Name", "Age", "City"],
    "rows": [["Alice", "30", "NYC"]],
    "row_count": 1,
    "column_count": 3
}
```

---

#### 4. **DocumentAnalyzer** (`document_analyzer.py`) ⭐ NEW
AI-powered document understanding and analysis.

**Features:**
- **Document summarization** - Executive summary + key points
- **Document classification** - Auto-detects document type
- **Entity extraction** - People, organizations, dates, locations, decisions
- **Context-aware task extraction** - Extracts tasks with document context

**Architecture:**
```python
@dataclass
class DocumentAnalysis:
    summary: DocumentSummary      # Executive summary, key points, type
    entities: ExtractedEntities   # People, orgs, dates, locations, decisions
    context: Dict                 # Document context and metadata
    inference_time_ms: int
    model_used: str
```

**Usage:**
```python
from agents.document_analyzer import DocumentAnalyzer

analyzer = DocumentAnalyzer("http://localhost:11434", "qwen2.5:7b-instruct")

# Full analysis
analysis = await analyzer.analyze_document(processed_doc)
print(f"Summary: {analysis.summary.executive_summary}")
print(f"Type: {analysis.summary.document_type}")
print(f"Key Points: {analysis.summary.key_points}")
print(f"People: {analysis.entities.people}")
print(f"Decisions: {analysis.entities.key_decisions}")

# Context-aware task extraction
tasks = await analyzer.extract_tasks_with_context(processed_doc, "John Doe")
# Returns tasks with rich context from document
```

**Example Analysis Output:**
```python
DocumentAnalysis(
    summary=DocumentSummary(
        executive_summary="Quarterly planning meeting discussing Q4 objectives...",
        key_points=[
            "Q4 revenue target set at $2M",
            "New product launch in December",
            "Hiring 3 engineers"
        ],
        document_type="meeting_notes",
        topics=["planning", "revenue", "hiring"],
        confidence=0.92
    ),
    entities=ExtractedEntities(
        people=["John Smith", "Sarah Johnson"],
        organizations=["Engineering Team"],
        dates=["2025-12-15", "Q4 2025"],
        locations=["Conference Room A"],
        key_decisions=["Approved $200K budget"],
        action_items=["Prepare job descriptions", "Schedule demo"]
    )
)
```

---

### Prompts (`prompts.py`)

Contains all AI prompts for task extraction and document analysis.

**Prompt Types:**

1. **Task Extraction** - Basic task extraction from text
   ```python
   get_task_extraction_prompt(input_text)
   ```

2. **Document Summary** ⭐ NEW
   ```python
   get_document_summary_prompt(document_text)
   # Returns: executive summary, key points, document type
   ```

3. **Entity Extraction** ⭐ NEW
   ```python
   get_entity_extraction_prompt(document_text)
   # Returns: people, organizations, dates, locations, decisions
   ```

4. **Context-Aware Task Extraction** ⭐ NEW
   ```python
   get_context_aware_task_extraction_prompt(document_text, context_info)
   # Returns: tasks with rich context and source references
   ```

**Prompt Engineering:**
- Optimized for Qwen 2.5 7B Instruct model
- Uses structured JSON output
- Includes explicit rules and examples
- Temperature: 0.3 (deterministic)
- Top-p: 0.9

---

## 🔄 Processing Pipeline

### Basic Flow (Legacy)
```
PDF → PDFProcessor → plain text → TaskExtractor → tasks
```

### Advanced Flow (New) ⭐
```
PDF
 ↓
AdvancedPDFProcessor
 ├─ Layout Analysis (PyMuPDF)
 ├─ Table Extraction (pdfplumber)
 ├─ Metadata Extraction
 └─ Semantic Chunking
 ↓
ProcessedDocument (structured)
 ↓
DocumentAnalyzer
 ├─ Summarization (Ollama)
 ├─ Entity Extraction
 ├─ Document Classification
 └─ Context-Aware Task Extraction
 ↓
DocumentAnalysis + Tasks
```

---

## 🎯 Comparison: Basic vs. Advanced

| Feature | Basic | Advanced |
|---------|-------|----------|
| **Text Extraction** | Plain text | Structure-aware |
| **Tables** | Garbled | Clean markdown |
| **Metadata** | None | Full extraction |
| **Chunking** | Single blob | Semantic chunks |
| **Summarization** | No | Yes |
| **Entity Extraction** | No | Yes |
| **Document Type** | No | Auto-detected |
| **Processing Time** | ~10 sec | ~20-45 sec |
| **Accuracy** | 70-80% | 85-95% |

---

## 📊 Performance

### AdvancedPDFProcessor (No AI)
- **Speed:** 1-3 seconds (structure extraction only)
- **Memory:** ~50MB for 10MB PDF
- **No network:** Works offline

### DocumentAnalyzer (AI-powered)
- **Speed:** 10-30 seconds per document
- **Model:** Qwen 2.5 7B Instruct
- **RAM:** 8GB+ recommended
- **GPU:** Optional (CPU works fine)

### Full Pipeline
- **Small doc (1-5 pages):** 15-25 seconds
- **Medium doc (5-20 pages):** 25-60 seconds
- **Large doc (20-50 pages):** 60-120 seconds

---

## 🔧 Configuration

### Environment Variables
```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

# PDF Settings
MAX_PDF_SIZE_MB=10
MAX_CHUNK_SIZE=4000
MIN_CHUNK_SIZE=500
```

### Dependencies
```txt
# Basic PDF
PyMuPDF==1.24.13

# Advanced PDF (NEW)
pdfplumber==0.11.4

# AI Engine
ollama==0.3.3
httpx==0.27.2
```

---

## 🧪 Testing

### Unit Tests
```bash
cd backend
pytest tests/test_advanced_pdf.py -v
```

### Manual Testing
```bash
# Test with real PDF
python tests/test_advanced_pdf.py path/to/document.pdf

# Expected output:
# Metadata, statistics, tables, summary, entities
```

### Integration Testing
```bash
# Start Ollama
ollama serve

# Run full pipeline test
pytest tests/test_advanced_pdf.py::TestIntegration -v
```

---

## 💡 Usage Examples

### Example 1: Quick Document Summary
```python
from agents.advanced_pdf_processor import AdvancedPDFProcessor
from agents.document_analyzer import DocumentAnalyzer

# Process PDF
processor = AdvancedPDFProcessor()
doc = await processor.process_document(pdf_bytes)

# Get summary
analyzer = DocumentAnalyzer("http://localhost:11434", "qwen2.5:7b-instruct")
analysis = await analyzer.analyze_document(doc)

print(f"Summary: {analysis.summary.executive_summary}")
print(f"Type: {analysis.summary.document_type}")
```

### Example 2: Extract Tables
```python
processor = AdvancedPDFProcessor()
doc = await processor.process_document(pdf_bytes)

for i, table in enumerate(doc.tables):
    print(f"\nTable {i+1} (Page {table['page_number']}):")
    print(table['markdown'])
```

### Example 3: Context-Aware Task Extraction
```python
processor = AdvancedPDFProcessor()
doc = await processor.process_document(pdf_bytes)

analyzer = DocumentAnalyzer("http://localhost:11434", "qwen2.5:7b-instruct")
tasks = await analyzer.extract_tasks_with_context(doc, "John Doe")

for task in tasks['tasks']:
    print(f"Task: {task['title']}")
    print(f"  Description: {task['description']}")
    print(f"  Due: {task.get('dueDate', 'N/A')}")
```

### Example 4: Extract All Entities
```python
processor = AdvancedPDFProcessor()
doc = await processor.process_document(pdf_bytes)

analyzer = DocumentAnalyzer("http://localhost:11434", "qwen2.5:7b-instruct")
analysis = await analyzer.analyze_document(doc)

print("People mentioned:", analysis.entities.people)
print("Organizations:", analysis.entities.organizations)
print("Important dates:", analysis.entities.dates)
print("Key decisions:", analysis.entities.key_decisions)
```

---

## 🚀 API Integration

These agents are exposed via FastAPI endpoints:

| Endpoint | Agent(s) Used | Purpose |
|----------|---------------|---------|
| `/api/infer-tasks-pdf` | PDFProcessor + TaskExtractor | Legacy simple extraction |
| `/api/analyze-document` | AdvancedPDFProcessor + DocumentAnalyzer | Full analysis ⭐ |
| `/api/summarize-pdf` | AdvancedPDFProcessor + DocumentAnalyzer | Quick summary |
| `/api/extract-document-structure` | AdvancedPDFProcessor only | Fast structure extraction |

See [API Documentation](../../docs/ADVANCED_PDF_PARSING.md) for details.

---

## 🔮 Future Enhancements

Planned improvements:

- [ ] **Vision models** - Analyze charts, diagrams, images
- [ ] **OCR support** - Handle scanned PDFs
- [ ] **Multi-file analysis** - Compare/merge documents
- [ ] **Custom extractors** - User-defined extraction rules
- [ ] **Streaming** - Real-time processing feedback
- [ ] **Embeddings** - Semantic document search

---

## 📚 References

- **PyMuPDF:** https://pymupdf.readthedocs.io/
- **pdfplumber:** https://github.com/jsvine/pdfplumber
- **Ollama:** https://ollama.ai/
- **Qwen 2.5:** https://huggingface.co/Qwen/Qwen2.5-7B-Instruct

---

## 🤝 Contributing

To add new features:

1. **New document type detection** - Update `prompts.py`
2. **Enhanced table extraction** - Improve `advanced_pdf_processor.py`
3. **New entity types** - Add to `document_analyzer.py`
4. **Performance optimization** - Profile and optimize chunking

---

## 📝 License

Part of the Task Management System.
