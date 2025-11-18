# Document + Knowledge Graph Integration

## 🎯 Overview

This system combines **Advanced PDF Processing** with the **Cognitive Nexus Knowledge Graph** to create a truly intelligent document processing pipeline that builds organizational intelligence over time.

### What This Means

When you upload a meeting notes PDF, the system now:

1. **Extracts structure** - Tables, headings, metadata (Advanced PDF Processing)
2. **Analyzes content** - Summaries, key points, entities (Document Analyzer)
3. **Builds knowledge graph** - Persistent entity relationships (Cognitive Nexus)
4. **Enables intelligence** - Cross-document insights, relationship tracking

---

## 🔄 Architecture

### Before Integration (Separate Systems)

```
Document Upload → PDF Parsing → Entities → Storage ❌ (Dead end)

Manual Text → Cognitive Nexus → Knowledge Graph ✅ (But manual only)
```

**Problem:** Document entities weren't feeding the knowledge graph!

### After Integration (Unified Pipeline)

```
Document Upload
    ↓
[Advanced PDF Processor]
    ├─ Layout analysis
    ├─ Table extraction
    ├─ Metadata extraction
    └─ Semantic chunking
    ↓
[Document Analyzer (AI)]
    ├─ Summarization
    ├─ Entity extraction (People, Orgs, Dates)
    ├─ Key decisions & action items
    └─ Document classification
    ↓
[Document-Cognitive Integration] ⭐ NEW
    ├─ Convert entities to KG format
    ├─ Build context text
    └─ Feed to Cognitive Nexus
    ↓
[Cognitive Nexus (LangGraph)]
    ├─ Entity extraction with quality loops
    ├─ Relationship inference
    ├─ Task integration (CREATE/UPDATE/COMMENT)
    └─ Cross-context aggregation
    ↓
[Knowledge Graph]
    ├─ Persistent entities
    ├─ Relationship strength tracking
    ├─ Team structure mapping
    └─ Cross-document intelligence
```

---

## 🚀 How to Use

### 1. Upload Document with Knowledge Graph (Default)

```bash
curl -X POST http://localhost:8000/api/analyze-document \
  -F "file=@meeting_notes.pdf" \
  -F "assignee=John Smith" \
  -F "enable_knowledge_graph=true"
```

**What Happens:**
1. PDF is parsed with structure preservation
2. AI extracts entities, summaries, insights
3. Entities are fed to Cognitive Nexus
4. Knowledge graph is automatically built
5. Relationships are inferred and persisted

**Response:**
```json
{
  "tasks": [...],
  "summary": {
    "executive_summary": "Quarterly planning meeting...",
    "key_points": ["Q4 target: $2M", ...],
    "document_type": "meeting_notes"
  },
  "entities": {
    "people": ["John Smith", "Sarah Johnson"],
    "organizations": ["Engineering Team"],
    "dates": ["2025-11-30"],
    "key_decisions": ["Approved $200K budget"],
    "action_items": ["Prepare proposal"]
  },
  "knowledge_graph": {
    "enabled": true,
    "context_item_id": 42,
    "entities_extracted": 15,
    "relationships_inferred": 8,
    "tasks_created": 3,
    "tasks_updated": 1,
    "comments_added": 2,
    "quality_metrics": {
      "entity_quality": 0.92,
      "relationship_quality": 0.85,
      "task_quality": 0.88
    },
    "extraction_strategy": "detailed",
    "reasoning_steps": [
      "Analyzing context complexity: 127 proper nouns detected",
      "Choosing detailed extraction strategy",
      "Extracted 15 entities with 92% quality",
      "Inferred 8 relationships (John WORKS_ON Q4_Planning, etc.)",
      "Created 3 new tasks, updated 1 existing task"
    ]
  }
}
```

### 2. Disable Knowledge Graph (Legacy Mode)

```bash
curl -X POST http://localhost:8000/api/analyze-document \
  -F "file=@meeting_notes.pdf" \
  -F "assignee=John Smith" \
  -F "enable_knowledge_graph=false"
```

**What Happens:**
- Only PDF processing and entity extraction
- No knowledge graph population
- Faster but no cross-document intelligence

---

## 🧠 What Gets Extracted

### From Document Analyzer → Cognitive Nexus

| Document Analyzer Output | → | Cognitive Nexus Entity |
|--------------------------|---|----------------------|
| `entities.people` | → | `PERSON` entities |
| `entities.organizations` | → | `TEAM` entities |
| `entities.dates` | → | `DATE` entities |
| `entities.key_decisions` (with "project") | → | `PROJECT` entities (inferred) |

### Relationship Inference

The Cognitive Nexus then infers relationships like:

- **WORKS_ON:** "John Smith" WORKS_ON "Q4 Planning Project"
- **COMMUNICATES_WITH:** "Sarah Johnson" COMMUNICATES_WITH "Mike Chen"
- **HAS_DEADLINE:** "Product Launch" HAS_DEADLINE "2025-12-15"
- **MANAGES:** "Engineering Team" MANAGES "API Redesign"

---

## 📊 Knowledge Graph Benefits

### 1. **Cross-Document Entity Persistence**

**Scenario:** Upload 3 meeting notes PDFs over time

- **PDF 1:** Mentions "John Smith" working on "API Redesign"
- **PDF 2:** Mentions "John Smith" working on "Database Migration"
- **PDF 3:** Mentions "Sarah Johnson" working on "API Redesign"

**Knowledge Graph Result:**
```
PERSON: John Smith
  ├─ WORKS_ON → API Redesign (strength: 0.8, seen 2 times)
  ├─ WORKS_ON → Database Migration (strength: 0.6, seen 1 time)
  └─ COMMUNICATES_WITH → Sarah Johnson (inferred, strength: 0.7)

PROJECT: API Redesign
  ├─ HAS_CONTRIBUTOR → John Smith
  ├─ HAS_CONTRIBUTOR → Sarah Johnson
  └─ STATUS → Active
```

### 2. **Organizational Intelligence**

Query the knowledge graph to answer:

- "Who has worked on the most projects in Q4?"
- "What's the team structure around the API Redesign?"
- "Who should I assign this task to?" (based on historical patterns)
- "Which projects have deadlines next week?"

### 3. **Automatic Task Updates**

**Scenario:** Upload meeting notes with update for existing task

- Existing task: "Complete API documentation" (status: todo)
- Meeting notes: "John updated that API docs are 80% complete"

**Result:**
- Task automatically updated with progress comment
- Assignee confirmed or suggested
- Due date extracted if mentioned

---

## 🔍 Example: Real-World Flow

### Meeting Notes PDF Content:

```
Q4 Planning Meeting - November 15, 2025

Attendees:
- John Smith (Engineering Lead)
- Sarah Johnson (Product Manager)
- Mike Chen (Designer)

Topics Discussed:
1. Q4 Revenue Target: $2M (Approved)
2. New product launch scheduled for December 15
3. Engineering team expansion: Hiring 3 new engineers

Action Items:
- John: Prepare job descriptions by Nov 20
- Sarah: Schedule product demo with stakeholders
- Mike: Finalize design mockups by Nov 30

Decisions Made:
- Approved $200K budget for new hires
- Selected vendor XYZ for cloud infrastructure
```

### Processing Result:

**1. Document Analysis:**
- Summary: "Quarterly planning meeting discussing Q4 objectives..."
- Key Points: 3 extracted
- Document Type: "meeting_notes"

**2. Entities Extracted:**
- People: John Smith, Sarah Johnson, Mike Chen
- Organizations: Engineering Team
- Dates: 2025-11-20, 2025-11-30, 2025-12-15
- Decisions: "Approved $200K budget", "Selected vendor XYZ"
- Action Items: 3 items

**3. Knowledge Graph Built:**
- 7 entities created/merged
- 9 relationships inferred:
  - John Smith WORKS_ON Q4_Planning
  - Sarah Johnson WORKS_ON Product_Launch
  - Mike Chen WORKS_ON Design_Mockups
  - Engineering_Team HAS_MEMBER John_Smith
  - Engineering_Team HAS_MEMBER Sarah_Johnson
  - Q4_Planning HAS_DEADLINE 2025-11-20
  - Product_Launch HAS_DEADLINE 2025-12-15
  - Design_Mockups HAS_DEADLINE 2025-11-30
  - John_Smith COMMUNICATES_WITH Sarah_Johnson

**4. Tasks Created:**
- Task 1: "Prepare job descriptions" (assignee: John Smith, due: Nov 20)
- Task 2: "Schedule product demo" (assignee: Sarah Johnson)
- Task 3: "Finalize design mockups" (assignee: Mike Chen, due: Nov 30)

**5. Cross-Document Intelligence:**
- Next time you upload a document mentioning "John Smith", the system knows:
  - He's the Engineering Lead
  - He works on Q4_Planning and job descriptions
  - He communicates with Sarah Johnson
  - He has tasks due Nov 20

---

## 🛠️ Technical Details

### Integration Service

**File:** `backend/services/document_cognitive_integration.py`

**Key Methods:**

```python
async def process_document_with_knowledge_graph(
    processed_doc: ProcessedDocument,
    analysis: DocumentAnalysis,
    document_id: Optional[str],
    source_identifier: Optional[str]
) -> Dict:
    """
    Main integration method that:
    1. Builds context text from document
    2. Processes through Cognitive Nexus
    3. Stores entities and relationships
    4. Executes task operations
    5. Returns comprehensive results
    """
```

### Context Text Building

The integration service builds rich context text for Cognitive Nexus:

```python
def _build_context_text(processed_doc, analysis) -> str:
    """
    Combines:
    - Document metadata (title, author, date)
    - Executive summary
    - Key points
    - Entity mentions
    - Key decisions
    - Action items
    - Sample content

    Result: Optimally formatted text for LLM processing
    """
```

### Entity Mapping

```python
async def enrich_document_with_entities(analysis) -> List[Dict]:
    """
    Maps DocumentAnalysis entities to Cognitive Nexus format:
    - entities.people → PERSON (confidence: 0.9)
    - entities.organizations → TEAM (confidence: 0.9)
    - entities.dates → DATE (confidence: 0.85)
    - entities.key_decisions → PROJECT (inferred, confidence: 0.7)
    """
```

---

## 📈 Performance

### Processing Time

| Document Type | Pages | PDF Processing | AI Analysis | KG Integration | Total |
|--------------|-------|---------------|-------------|----------------|-------|
| Meeting Notes | 1-5 | 1-3 sec | 10-15 sec | 8-12 sec | 20-30 sec |
| Reports | 5-20 | 2-5 sec | 15-30 sec | 10-20 sec | 30-55 sec |
| Technical Docs | 10-50 | 3-8 sec | 30-60 sec | 15-35 sec | 50-100 sec |

### Resource Usage

- **Memory:** ~200MB per document (peak)
- **CPU:** Moderate (LLM inference)
- **Database:** ~50KB per document + entities/relationships

---

## 🎛️ Configuration

### Enable/Disable Knowledge Graph

**Default:** Enabled

**Disable globally:**
```python
# In routes.py
enable_knowledge_graph: bool = Form(False)  # Change default to False
```

**Disable per request:**
```bash
curl -F "enable_knowledge_graph=false" ...
```

### Quality Thresholds

Configure in `backend/config/constants.py`:

```python
QUALITY_THRESHOLD_HIGH = 0.85    # Entity quality threshold
QUALITY_THRESHOLD_MEDIUM = 0.70  # Relationship quality threshold
DEFAULT_MAX_RETRIES = 2          # Retry loops for quality
```

---

## 🔮 Future Enhancements

### Planned Features

1. **Semantic Search:**
   - "Find all documents mentioning John Smith and API projects"
   - Vector embeddings for document similarity

2. **Relationship Visualization:**
   - Interactive knowledge graph UI
   - Team structure diagrams
   - Project timeline views

3. **Smart Suggestions:**
   - "You might want to assign this to John (he worked on similar tasks)"
   - "This mentions Sarah - add her as a stakeholder?"

4. **Temporal Intelligence:**
   - Track how projects evolve over time
   - Identify stale relationships
   - Predict future collaborations

5. **Multi-Document Synthesis:**
   - "Summarize all Q4 planning meetings"
   - "What's the status of API Redesign across all documents?"

---

## 🧪 Testing

### Test the Integration

```bash
# 1. Start backend
cd backend
uvicorn main:app --reload

# 2. Upload test document with KG enabled
curl -X POST http://localhost:8000/api/analyze-document \
  -F "file=@test_meeting_notes.pdf" \
  -F "assignee=Test User" \
  -F "enable_knowledge_graph=true" | jq

# 3. Query entities created
curl http://localhost:8000/api/knowledge/entities | jq

# 4. Query relationships
curl http://localhost:8000/api/knowledge/relationships | jq

# 5. View reasoning trace
curl http://localhost:8000/api/context/1/reasoning | jq
```

### Verify Cross-Document Intelligence

```bash
# Upload 2 documents mentioning the same person
curl -X POST http://localhost:8000/api/analyze-document \
  -F "file=@doc1.pdf" -F "enable_knowledge_graph=true"

curl -X POST http://localhost:8000/api/analyze-document \
  -F "file=@doc2.pdf" -F "enable_knowledge_graph=true"

# Check that entity appears with aggregated relationships
curl http://localhost:8000/api/knowledge/entities?name=John%20Smith | jq
```

---

## 📚 Related Documentation

- [Advanced PDF Parsing](./ADVANCED_PDF_PARSING.md)
- [Cognitive Nexus Phase 2](../COGNITIVE_NEXUS_PHASE2.md)
- [Knowledge Graph Guide](../KNOWLEDGE_GRAPH_GUIDE.md)
- [Unified Task Management](../UNIFIED_TASK_MANAGEMENT.md)

---

## 🤝 Summary

The Document + Knowledge Graph integration creates a **unified intelligence pipeline** that:

✅ **Automatically builds organizational knowledge** from documents
✅ **Tracks entity relationships** across all uploads
✅ **Enables cross-document insights** and queries
✅ **Improves task extraction** with historical context
✅ **Provides reasoning transparency** through LangGraph traces

**Key Benefit:** Every document upload enriches your organizational intelligence graph, making the system smarter over time!
