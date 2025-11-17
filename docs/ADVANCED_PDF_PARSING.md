# Advanced PDF Parsing & Document Analysis

## Overview

The task management system now includes **advanced PDF parsing and AI-powered document analysis** capabilities that go far beyond simple text extraction. This comprehensive system provides intelligent document understanding, task extraction, summarization, and entity recognition.

## 🎯 Key Features

### 1. **Intelligent Document Structure Extraction**
- **Layout-aware parsing** - Preserves document structure (headings, paragraphs, lists)
- **Table detection & extraction** - Extracts tables with structure, converts to markdown
- **Metadata extraction** - Author, title, dates, page count, file info
- **Smart chunking** - Breaks large documents into semantic chunks for AI processing

### 2. **AI-Powered Document Analysis**
- **Executive summaries** - 2-3 sentence overview of document content
- **Key points extraction** - Bullet-point highlights of main ideas
- **Document classification** - Auto-detects document type (meeting notes, reports, invoices, etc.)
- **Topic identification** - Identifies main themes and subjects

### 3. **Entity Extraction**
- **People** - Names of individuals mentioned
- **Organizations** - Companies, teams, departments
- **Dates** - Deadlines, meeting times, important dates
- **Locations** - Physical locations, cities, offices
- **Key Decisions** - Important decisions documented
- **Action Items** - Explicit action items identified

### 4. **Context-Aware Task Extraction**
- Extracts tasks with **full document context**
- Links tasks to **source sections/pages**
- Infers **task priority** from context (deadlines, urgency indicators)
- Provides **richer task descriptions** using document metadata

---

## 🏗️ Architecture

### Processing Pipeline

```
PDF Upload
    ↓
[Advanced PDF Processor]
    ├── Layout Analysis (PyMuPDF)
    ├── Table Extraction (pdfplumber)
    ├── Metadata Extraction
    └── Semantic Chunking
    ↓
[Document Analyzer (AI)]
    ├── Summarization (Ollama/Qwen 2.5)
    ├── Entity Extraction
    ├── Document Classification
    └── Context-Aware Task Extraction
    ↓
Structured Output + Database Storage
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Basic Text** | PyMuPDF (fitz) | Fast text extraction, layout analysis |
| **Table Extraction** | pdfplumber | Accurate table detection & parsing |
| **AI Engine** | Ollama + Qwen 2.5 7B | Local LLM for analysis (no cloud APIs) |
| **Structure** | Custom algorithms | Heading detection, chunking, classification |

---

## 📡 API Endpoints

### 1. **Full Document Analysis** (Recommended)
`POST /api/analyze-document`

**Purpose:** Complete document processing with all features

**Request:**
```bash
curl -X POST http://localhost:8000/api/analyze-document \
  -F "file=@meeting_notes.pdf" \
  -F "assignee=John Smith"
```

**Response:**
```json
{
  "tasks": [...],
  "summary": {
    "executive_summary": "Quarterly planning meeting discussing Q4 objectives...",
    "key_points": [
      "Q4 revenue target set at $2M",
      "New product launch scheduled for December",
      "Engineering team to be expanded by 3 people"
    ],
    "document_type": "meeting_notes",
    "topics": ["planning", "revenue", "hiring"],
    "confidence": 0.92
  },
  "entities": {
    "people": ["John Smith", "Sarah Johnson", "Mike Chen"],
    "organizations": ["Engineering Team", "Sales Dept"],
    "dates": ["2025-12-15", "Q4 2025"],
    "locations": ["Conference Room A"],
    "key_decisions": [
      "Approved $200K budget for new hire"
    ],
    "action_items": [
      "Prepare job descriptions",
      "Schedule product demo"
    ]
  },
  "metadata": {
    "title": "Q4 Planning Meeting",
    "author": "Sarah Johnson",
    "creation_date": "2025-11-15T14:30:00",
    "page_count": 5,
    "has_tables": true,
    "has_images": false
  },
  "statistics": {
    "total_sections": 12,
    "total_tables": 2,
    "word_count": 1543,
    "inference_time_ms": 8234
  },
  "tables": [...]
}
```

### 2. **Quick Summarization**
`POST /api/summarize-pdf`

**Purpose:** Fast summary without task extraction (useful for document preview)

**Request:**
```bash
curl -X POST http://localhost:8000/api/summarize-pdf \
  -F "file=@report.pdf"
```

**Response:**
```json
{
  "summary": {
    "executive_summary": "Annual financial report showing...",
    "key_points": [...],
    "document_type": "report",
    "topics": [...],
    "confidence": 0.88
  },
  "metadata": {...},
  "statistics": {...},
  "tables_count": 3,
  "inference_time_ms": 4521
}
```

### 3. **Structure Extraction Only**
`POST /api/extract-document-structure`

**Purpose:** Fast structure extraction without AI (no LLM required)

**Request:**
```bash
curl -X POST http://localhost:8000/api/extract-document-structure \
  -F "file=@document.pdf"
```

**Response:**
```json
{
  "metadata": {...},
  "sections": [
    {
      "section_type": "heading",
      "content": "Introduction",
      "page_number": 1,
      "level": 1
    },
    {
      "section_type": "paragraph",
      "content": "This document outlines...",
      "page_number": 1,
      "level": 0
    }
  ],
  "tables": [
    {
      "page_number": 3,
      "table_index": 0,
      "markdown": "| Header 1 | Header 2 |\n|----------|----------|\n| Data 1   | Data 2   |",
      "row_count": 5,
      "column_count": 2
    }
  ],
  "chunks": [
    {
      "content": "...",
      "page_start": 1,
      "page_end": 2,
      "size": 3421
    }
  ]
}
```

### 4. **Legacy Simple Extraction**
`POST /api/infer-tasks-pdf`

**Purpose:** Basic text extraction + task inference (backward compatible)

---

## 🚀 Usage Examples

### Python Client Example

```python
import httpx

async def analyze_document(pdf_path: str):
    """Analyze PDF document with full AI processing"""

    async with httpx.AsyncClient() as client:
        with open(pdf_path, 'rb') as f:
            files = {'file': f}
            data = {'assignee': 'Team Lead'}

            response = await client.post(
                'http://localhost:8000/api/analyze-document',
                files=files,
                data=data,
                timeout=180.0  # 3 minutes for large docs
            )

            result = response.json()

            print(f"Summary: {result['summary']['executive_summary']}")
            print(f"Tasks found: {len(result['tasks'])}")
            print(f"Entities: {result['entities']}")

            return result
```

### Frontend Integration (React)

```typescript
async function analyzeDocument(file: File, assignee: string) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('assignee', assignee);

  const response = await fetch('/api/analyze-document', {
    method: 'POST',
    body: formData
  });

  const analysis = await response.json();

  // Use analysis results
  console.log('Summary:', analysis.summary.executive_summary);
  console.log('Key Points:', analysis.summary.key_points);
  console.log('Tasks:', analysis.tasks);
  console.log('People mentioned:', analysis.entities.people);

  return analysis;
}
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

# File Size Limits
MAX_PDF_SIZE_MB=10
```

### Model Requirements

**Recommended Model:** Qwen 2.5 7B Instruct
- **Size:** ~7 billion parameters
- **RAM Required:** 8GB+
- **Performance:** 10-30 seconds per document
- **Quality:** High accuracy for task extraction and summarization

**Installation:**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Download model
ollama pull qwen2.5:7b-instruct

# Start server
ollama serve
```

---

## 🧪 Testing

### Test with Sample Document

```bash
# 1. Start backend
cd backend
uvicorn main:app --reload

# 2. Test full analysis
curl -X POST http://localhost:8000/api/analyze-document \
  -F "file=@test_meeting_notes.pdf" \
  -F "assignee=Test User" | jq

# 3. Test summarization only
curl -X POST http://localhost:8000/api/summarize-pdf \
  -F "file=@test_report.pdf" | jq '.summary'

# 4. Test structure extraction (fast, no AI)
curl -X POST http://localhost:8000/api/extract-document-structure \
  -F "file=@test_doc.pdf" | jq '.tables'
```

### Expected Performance

| Document Type | Pages | Processing Time | Accuracy |
|--------------|-------|----------------|----------|
| Meeting Notes | 1-5 | 8-15 seconds | 90-95% |
| Reports | 5-20 | 15-45 seconds | 85-90% |
| Technical Docs | 10-50 | 30-120 seconds | 80-85% |

---

## 🔍 How It Works

### 1. **Layout Analysis**

The system analyzes PDF structure using PyMuPDF's layout detection:

```python
# Detects headings based on font size and position
if len(text) < 100 and avg_font_size > 12:
    if avg_font_size >= 18:
        return ("heading", 1)  # H1
    elif avg_font_size >= 15:
        return ("heading", 2)  # H2
```

### 2. **Table Extraction**

Uses `pdfplumber` for accurate table detection:

```python
with pdfplumber.open(pdf_bytes) as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        # Convert to markdown for AI consumption
        markdown = table_to_markdown(tables)
```

### 3. **Intelligent Chunking**

Chunks documents while preserving semantic structure:

- **Max chunk size:** 4000 characters
- **Min chunk size:** 500 characters
- **Strategy:** Keep related sections together (headings + content)
- **Table handling:** Include full tables in chunks

### 4. **AI Prompting**

Context-aware prompts for better results:

```python
prompt = f"""
DOCUMENT CONTEXT:
- Type: {doc.metadata.document_type}
- Author: {doc.metadata.author}
- Pages: {doc.metadata.page_count}
- Has tables: {doc.metadata.has_tables}

CONTENT:
{document_text}

Extract tasks with context awareness...
"""
```

---

## 🎨 Advanced Use Cases

### 1. **Meeting Minutes Processing**
- Extract action items automatically
- Identify attendees and decisions
- Generate executive summary
- Create tasks with assignments

### 2. **Report Analysis**
- Summarize lengthy reports
- Extract key metrics from tables
- Identify trends and recommendations
- Create follow-up tasks

### 3. **Invoice/Contract Processing**
- Extract key dates and amounts
- Identify parties and terms
- Create payment/review tasks
- Track important deadlines

### 4. **Research Paper Processing**
- Summarize abstract and conclusions
- Extract citations and references
- Identify methodology
- Create research tasks

---

## 🔧 Troubleshooting

### Issue: "Cannot connect to Ollama"

**Solution:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve
```

### Issue: "Table extraction failed"

**Possible causes:**
- PDF has scanned images instead of text
- Table has complex merged cells
- PDF is corrupted

**Solution:** Use OCR pre-processing or manual table entry

### Issue: "Processing too slow"

**Optimizations:**
1. Use smaller model (qwen2.5:1.5b)
2. Reduce chunk size
3. Use `/summarize-pdf` for quick summaries
4. Use `/extract-document-structure` for structure only (no AI)

### Issue: "Poor task extraction quality"

**Improvements:**
1. Ensure Ollama model is properly loaded
2. Check document quality (scanned vs. native PDFs)
3. Use `/analyze-document` for best results (uses context)
4. Provide better assignee information

---

## 📊 Comparison: Basic vs. Advanced

| Feature | Basic (`/infer-tasks-pdf`) | Advanced (`/analyze-document`) |
|---------|---------------------------|-------------------------------|
| Text Extraction | Plain text, no structure | Layout-aware with structure |
| Tables | Garbled text | Clean markdown formatting |
| Metadata | None | Complete (author, dates, etc.) |
| Summarization | No | Yes (executive + key points) |
| Entity Extraction | No | Yes (people, dates, orgs, etc.) |
| Document Classification | No | Yes (auto-detects type) |
| Task Context | Limited | Rich context with source refs |
| Processing Time | 10-15 sec | 20-45 sec |
| Accuracy | 70-80% | 85-95% |
| Use Case | Quick extraction | Production analysis |

---

## 🚦 Best Practices

1. **Choose the right endpoint:**
   - `/analyze-document` - Best quality, full features
   - `/summarize-pdf` - Quick previews
   - `/extract-document-structure` - Fast structure extraction
   - `/infer-tasks-pdf` - Legacy/simple extraction

2. **Optimize for performance:**
   - Use structure extraction first for large docs
   - Batch process multiple small documents
   - Cache summaries for frequently accessed docs

3. **Improve accuracy:**
   - Provide high-quality PDFs (native, not scanned)
   - Use descriptive assignee names
   - Pre-process complex tables if needed

4. **Handle errors gracefully:**
   - Implement retries with exponential backoff
   - Fall back to basic extraction on failure
   - Validate results before storing

---

## 🔮 Future Enhancements

Planned features for future releases:

- [ ] **Multi-modal AI** - Image and chart analysis using vision models
- [ ] **OCR Support** - Handle scanned PDFs
- [ ] **Multi-file analysis** - Compare and merge multiple documents
- [ ] **Custom prompts** - User-defined extraction rules
- [ ] **Streaming responses** - Real-time processing feedback
- [ ] **Document embeddings** - Semantic search across documents
- [ ] **Template detection** - Auto-detect and parse form templates
- [ ] **Multi-language support** - Extract from non-English documents

---

## 📚 Related Documentation

- [Architecture Overview](./ARCHITECTURE.md)
- [API Reference](./API.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Prompt Engineering](../backend/agents/prompts.py)

---

## 🤝 Contributing

To improve PDF parsing capabilities:

1. **Add new document types** - Update classification in `prompts.py`
2. **Enhance table extraction** - Improve algorithms in `advanced_pdf_processor.py`
3. **Add new entity types** - Update entity extraction prompts
4. **Optimize performance** - Profile and optimize chunking algorithms

---

## 📝 License

Part of the Task Management System - See main LICENSE file.
