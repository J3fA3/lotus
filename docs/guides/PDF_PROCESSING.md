# Document Handling System

## Overview

The task management system now includes comprehensive document handling capabilities with support for multiple file formats, persistent storage, and knowledge base integration.

## Supported Document Types

- **PDF** (.pdf) - Portable Document Format
- **Word** (.docx, .doc) - Microsoft Word documents
- **Markdown** (.md, .markdown) - Markdown files
- **Plain Text** (.txt) - Text files
- **Excel** (.xlsx, .xls) - Microsoft Excel spreadsheets

## Features

### 1. Async/Await Fix for PDF Processing

**Problem Solved:** The original PDF processor was causing `greenlet_spawn` errors when used with SQLAlchemy's async session because PyMuPDF operations are blocking.

**Solution:** All blocking I/O operations are now wrapped in `asyncio.to_thread()` to run in a thread pool, preventing event loop blocking.

**Files Updated:**
- `backend/agents/pdf_processor.py` - Fixed async/await handling
- `backend/api/routes.py` - Updated to await validate_pdf call

### 2. Unified Document Processor

**File:** `backend/agents/document_processor.py`

**Features:**
- Automatic file type detection
- Text extraction from multiple formats
- Async wrapper for all blocking operations
- File validation with size limits (50MB max)
- Document metadata extraction (page count, MIME type, etc.)

**Usage:**
```python
from agents.document_processor import DocumentProcessor

# Extract text from any supported document
text = await DocumentProcessor.extract_text(file_bytes, filename)

# Validate document
is_valid, error = await DocumentProcessor.validate_document(file_bytes, filename)

# Get document info
info = await DocumentProcessor.get_document_info(file_bytes, filename)
```

### 3. Document Storage System

**File:** `backend/agents/document_storage.py`

**Features:**
- Persistent file storage with organized directory structure
- Unique file IDs to prevent collisions
- SHA-256 hash computation for deduplication
- File retrieval and deletion
- Category-based organization (tasks, inference, knowledge)

**Directory Structure:**
```
data/documents/
├── tasks/          # Documents attached to tasks
├── inference/      # Documents used for AI inference
└── knowledge/      # Documents in knowledge base
```

**Usage:**
```python
from agents.document_storage import DocumentStorage

storage = DocumentStorage("./data/documents")
await storage.initialize()

# Save document
doc_info = await storage.save_document(
    file_bytes,
    filename,
    category="knowledge",
    metadata={"task_id": "123"}
)

# Retrieve document
file_bytes = await storage.get_document(file_id, category)

# Delete document
deleted = await storage.delete_document(file_id, category)
```

### 4. Knowledge Base Integration

**File:** `backend/agents/knowledge_base.py`

**Features:**
- Document indexing for search
- Full-text search across documents
- Context retrieval for AI processing
- Document summarization
- Keyword extraction
- Usage statistics

**Usage:**
```python
from agents.knowledge_base import KnowledgeBase

kb = KnowledgeBase()

# Index document
await kb.index_document(db, document_id, extracted_text)

# Search documents
results = await kb.search_documents(db, query="meeting notes", category="knowledge")

# Get document context
context = await kb.get_document_context(db, ["doc1", "doc2"], max_chars=10000)

# Get statistics
summary = await kb.get_knowledge_base_summary(db)
```

### 5. Database Models

**File:** `backend/db/models.py`

**New Model:** `Document`

**Fields:**
- `id` - UUID
- `file_id` - Storage file ID
- `original_filename` - Original name
- `file_extension` - .pdf, .docx, etc.
- `mime_type` - MIME type
- `file_hash` - SHA-256 hash
- `size_bytes` - File size
- `storage_path` - Relative path in storage
- `category` - tasks, inference, knowledge
- `extracted_text` - Full extracted text
- `text_preview` - First 500 characters
- `page_count` - For PDFs
- `metadata` - JSON metadata
- `task_id` - Optional task association
- `inference_history_id` - Optional inference association

**Relationships:**
- Documents can be attached to tasks
- Documents can be linked to inference history

## API Endpoints

### Upload Document to Knowledge Base
```http
POST /api/documents/upload
Content-Type: multipart/form-data

Parameters:
- file: Document file (required)
- category: tasks|inference|knowledge (default: knowledge)
- task_id: Optional task ID to attach document to
```

### Upload Document for Task Inference
```http
POST /api/documents/upload-for-inference
Content-Type: multipart/form-data

Parameters:
- file: Document file (required)
- assignee: Task assignee (default: "You")

Returns: InferenceResponse with extracted tasks
```

### Upload PDF for Task Inference (Legacy)
```http
POST /api/infer-tasks-pdf
Content-Type: multipart/form-data

Parameters:
- file: PDF file (required)
- assignee: Task assignee (default: "You")

Note: Now saves PDF to storage for future access
```

### List Documents
```http
GET /api/documents?category=knowledge&task_id=123

Returns: List of documents with metadata
```

### Get Document Metadata
```http
GET /api/documents/{document_id}

Returns: Document metadata
```

### Download Document
```http
GET /api/documents/{document_id}/download

Returns: Document file with appropriate MIME type
```

### Delete Document
```http
DELETE /api/documents/{document_id}

Deletes both database record and physical file
```

### Search Documents
```http
GET /api/documents/search/{query}?category=knowledge&limit=10

Returns: Documents matching search query
```

### Knowledge Base Summary
```http
GET /api/knowledge-base/summary

Returns: Statistics about document storage
```

## Integration Examples

### 1. Attach Document to Task

```python
# Frontend
const formData = new FormData();
formData.append('file', file);
formData.append('category', 'tasks');
formData.append('task_id', taskId);

const response = await fetch('/api/documents/upload', {
    method: 'POST',
    body: formData
});
```

### 2. Upload Meeting Notes for Task Extraction

```python
# Frontend
const formData = new FormData();
formData.append('file', meetingNotesFile);
formData.append('assignee', 'John Doe');

const response = await fetch('/api/documents/upload-for-inference', {
    method: 'POST',
    body: formData
});

const { tasks } = await response.json();
// Tasks are automatically created from document content
```

### 3. Build Knowledge Base from Documents

```python
# Upload multiple documents
for document in documents:
    formData = new FormData();
    formData.append('file', document);
    formData.append('category', 'knowledge');

    await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData
    });

// Search knowledge base
const searchResults = await fetch('/api/documents/search/project requirements');
```

## Configuration

### Environment Variables

```bash
# Document storage path
DOCUMENT_STORAGE_PATH=./data/documents

# Maximum file size (default: 50MB)
# Configured in DocumentProcessor.MAX_FILE_SIZE
```

### File Size Limits

- **Default Maximum:** 50MB
- **Configurable in:** `backend/agents/document_processor.py`
- **Per-format limits:** Can be customized in processor classes

## Error Handling

### Common Errors

1. **"greenlet_spawn has not been called"**
   - **Cause:** Blocking I/O in async context
   - **Solution:** Fixed by using `asyncio.to_thread()`

2. **"File too large"**
   - **Cause:** File exceeds MAX_FILE_SIZE
   - **Solution:** Compress file or adjust limit

3. **"Unsupported file type"**
   - **Cause:** File extension not in SUPPORTED_FORMATS
   - **Solution:** Convert to supported format

4. **"No text found in document"**
   - **Cause:** Document has no extractable text (scanned PDF, images)
   - **Solution:** Use OCR preprocessing or different document

## Performance Considerations

1. **Async Operations:** All I/O operations run in thread pools to avoid blocking
2. **Text Extraction:** Large documents are processed efficiently with streaming
3. **Storage:** Files organized by category for fast retrieval
4. **Search:** Uses database LIKE queries (consider FTS5 for production)
5. **Caching:** Document metadata cached in database

## Future Enhancements

- [ ] OCR support for scanned PDFs
- [ ] Document preview/thumbnail generation
- [ ] Full-text search with FTS5 or Elasticsearch
- [ ] Document versioning
- [ ] Collaborative document editing
- [ ] Document templates
- [ ] Batch upload/processing
- [ ] Document conversion between formats
- [ ] Advanced metadata extraction (author, creation date, etc.)
- [ ] Document similarity/clustering

## Dependencies

```txt
# Core dependencies
PyMuPDF==1.24.13              # PDF processing
python-docx==1.1.2            # Word document processing
openpyxl==3.1.5               # Excel files
markdown==3.7                 # Markdown processing
chardet==5.2.0                # Text encoding detection
python-multipart==0.0.12      # File upload support
```

## Testing

### Unit Tests

```python
# Test document upload
async def test_upload_document():
    with open("test.pdf", "rb") as f:
        response = await client.post(
            "/api/documents/upload",
            files={"file": f},
            data={"category": "knowledge"}
        )
    assert response.status_code == 200

# Test document extraction
async def test_extract_text():
    with open("test.docx", "rb") as f:
        file_bytes = f.read()
    text = await DocumentProcessor.extract_text(file_bytes, "test.docx")
    assert len(text) > 0
```

### Integration Tests

```python
# Test end-to-end workflow
async def test_document_to_tasks():
    # Upload document
    with open("meeting_notes.md", "rb") as f:
        response = await client.post(
            "/api/documents/upload-for-inference",
            files={"file": f},
            data={"assignee": "Test User"}
        )

    # Verify tasks created
    data = response.json()
    assert len(data["tasks"]) > 0

    # Verify document stored
    docs = await client.get("/api/documents?category=inference")
    assert len(docs.json()["documents"]) > 0
```

## Troubleshooting

### Issue: Documents not persisting after upload

**Solution:** Check that document storage directories exist and are writable:
```bash
mkdir -p data/documents/{tasks,inference,knowledge}
chmod -R 755 data/documents
```

### Issue: Text extraction fails for Word documents

**Solution:** Ensure python-docx is installed:
```bash
pip install python-docx==1.1.2
```

### Issue: Database doesn't have documents table

**Solution:** Database tables are auto-created on startup. Restart the backend:
```bash
cd backend
python main.py
```

## Migration Guide

### From Old PDF-Only System

1. Existing PDFs processed via `/infer-tasks-pdf` are now automatically saved
2. Document records created in database with metadata
3. Files stored in `data/documents/inference/`
4. No action required - backward compatible

### Adding Document Support to Existing Tasks

1. Upload documents via `/api/documents/upload`
2. Include `task_id` parameter to attach to existing task
3. Documents accessible via task's document relationship
4. Frontend can display attached documents

## Security Considerations

1. **File Validation:** All uploads validated for type and size
2. **Filename Sanitization:** Prevents directory traversal attacks
3. **Hash Verification:** SHA-256 hashing for integrity
4. **Access Control:** TODO - Add user-based permissions
5. **Virus Scanning:** TODO - Add malware detection
6. **Rate Limiting:** TODO - Prevent upload abuse

## License

Same as main project.
