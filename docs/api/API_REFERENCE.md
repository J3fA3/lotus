# API Reference - Task Crate

Complete REST API documentation for Task Crate backend.

**Base URL:** `http://localhost:8000/api`  
**Interactive Docs:** http://localhost:8000/docs (Swagger UI)

## 🔗 Quick Links

- [Task Management](#task-management)
- [AI Assistant (Lotus)](#ai-assistant-lotus)
- [Context & Cognitive Nexus](#context--cognitive-nexus)
- [Knowledge Graph](#knowledge-graph)
- [User Profiles](#user-profiles)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Health & System](#health--system)

---

## Task Management

### List Tasks

```http
GET /api/tasks
```

**Response:**
```json
[
  {
    "id": "uuid",
    "title": "Update API docs",
    "description": "Before Friday release",
    "status": "todo",
    "assignee": "Jef Adriaenssens",
    "priority": "high",
    "due_date": "2025-11-22",
    "value_stream": "CRESCO",
    "notes": "Remember changelog",
    "comments": [
      {
        "id": "uuid",
        "text": "Started work",
        "author": "Jef",
        "created_at": "2025-11-16T10:00:00Z"
      }
    ],
    "attachments": ["https://example.com/file.pdf"],
    "created_at": "2025-11-15T10:00:00Z",
    "updated_at": "2025-11-16T12:00:00Z"
  }
]
```

### Get Task

```http
GET /api/tasks/{id}
```

**Parameters:**
- `id` (path) - Task UUID

**Response:** Same as single task object above

### Create Task

```http
POST /api/tasks
```

**Request Body:**
```json
{
  "title": "New task",
  "description": "Task description",
  "status": "todo",
  "assignee": "John Doe",
  "priority": "medium",
  "due_date": "2025-12-01",
  "value_stream": "Project X",
  "notes": "Additional notes"
}
```

**Response:** Created task object (201 Created)

### Update Task

```http
PUT /api/tasks/{id}
```

**Request Body:** (all fields optional)
```json
{
  "title": "Updated title",
  "status": "doing",
  "notes": "Updated notes",
  "comments": [
    {
      "id": "existing-id",
      "text": "Updated comment",
      "author": "User",
      "created_at": "2025-11-16T10:00:00Z"
    }
  ],
  "attachments": ["https://new-file.pdf"]
}
```

**Note:** Comments and attachments are replaced (not appended)

**Response:** Updated task object

### Delete Task

```http
DELETE /api/tasks/{id}
```

**Response:** 204 No Content

---

## AI Assistant (Lotus)

### Process Message

```http
POST /api/assistant/message
```

**Request Body:**
```json
{
  "content": "Meeting notes: Jef needs to share CRESCO data with Andy by Friday",
  "source_type": "manual",
  "source_identifier": "user-input-001"
}
```

**Parameters:**
- `content` (required) - Text to process
- `source_type` (optional) - One of: `manual`, `slack`, `transcript`, `email`
- `source_identifier` (optional) - Tracking ID for source

**Response:**
```json
{
  "context_item_id": 42,
  "entities_extracted": 3,
  "relationships_inferred": 2,
  "tasks_created": 1,
  "tasks_updated": 0,
  "comments_added": 0,
  "quality_metrics": {
    "entity_quality": 0.95,
    "relationship_quality": 0.90,
    "task_quality": 0.92,
    "context_complexity": 0.65
  },
  "reasoning_steps": [
    "Loaded user profile for Jef Adriaenssens",
    "Classified as task creation request",
    "Extracted 3 entities: Jef, Andy, CRESCO",
    "Relevance score: 95 (CRESCO is your project)",
    "Confidence: 90% - auto-creating task"
  ]
}
```

### Process PDF

```http
POST /api/assistant/process-pdf
```

**Content-Type:** `multipart/form-data`

**Form Data:**
- `file` (required) - PDF file
- `assignee` (optional) - Default assignee for extracted tasks

**Response:** Same as Process Message

### Process PDF (Fast)

```http
POST /api/assistant/process-pdf-fast
```

Bypasses full pipeline for speed (2-3s instead of 10s+).

**Content-Type:** `multipart/form-data`

**Form Data:**
- `file` (required) - PDF file

**Response:**
```json
{
  "tasks_created": 5,
  "processing_time_seconds": 2.3,
  "pdf_pages": 3
}
```

### Answer Question

```http
POST /api/assistant/question
```

**Request Body:**
```json
{
  "question": "What tasks are due this week?"
}
```

**Response:**
```json
{
  "answer": "You have 3 tasks due this week:\n1. Share CRESCO data (Friday)\n2. Review auth PR (Thursday)\n3. Q4 planning (Wednesday)",
  "confidence": 0.92,
  "sources": [
    {
      "task_id": "uuid-1",
      "title": "Share CRESCO data"
    }
  ]
}
```

### Get Usage Statistics

```http
GET /api/assistant/usage-stats
```

**Response:**
```json
{
  "gemini": {
    "total_requests": 150,
    "total_input_tokens": 45000,
    "total_output_tokens": 15000,
    "total_cost_usd": 0.0084,
    "average_latency_ms": 1200
  },
  "ollama": {
    "total_requests": 25,
    "average_latency_ms": 8500
  },
  "cache": {
    "hit_rate": 0.62,
    "miss_rate": 0.38
  }
}
```

---

## Context & Cognitive Nexus

### Ingest Context

```http
POST /api/context/
```

**Request Body:**
```json
{
  "content": "Context text to process",
  "source_type": "slack",
  "source_identifier": "channel-eng-001"
}
```

**Response:**
```json
{
  "context_item_id": 123,
  "entities_extracted": 5,
  "relationships_inferred": 3,
  "tasks_created": 1,
  "tasks_updated": 0,
  "comments_added": 1,
  "quality_metrics": {
    "entity_quality": 0.95,
    "relationship_quality": 0.88,
    "task_quality": 0.90,
    "context_complexity": 0.72
  },
  "reasoning_steps": [
    "Context Analysis: complexity=0.72",
    "Entity Extraction: 5 entities found",
    "Relationship Synthesis: 3 relationships inferred",
    "Task Integration: Created 1 task"
  ]
}
```

### Get Context Reasoning

```http
GET /api/context/{id}/reasoning
```

**Parameters:**
- `id` (path) - Context item ID

**Response:**
```json
{
  "context_item_id": 123,
  "reasoning_steps": [
    "Step 1: Context Analysis...",
    "Step 2: Entity Extraction...",
    "Step 3: Relationship Synthesis...",
    "Step 4: Task Integration..."
  ],
  "extraction_strategy": "detailed",
  "quality_metrics": {
    "entity_quality": 0.95,
    "relationship_quality": 0.88,
    "task_quality": 0.90
  }
}
```

---

## Knowledge Graph

### Get Entity Knowledge

```http
GET /api/knowledge/entity/{name}
```

**Parameters:**
- `name` (path) - Entity name (URL encoded)

**Example:** `/api/knowledge/entity/Jef%20Adriaenssens`

**Response:**
```json
{
  "entity": "Jef Adriaenssens",
  "type": "PERSON",
  "aliases": ["jef", "jef adriaenssens", "jef a"],
  "mentioned_in": 12,
  "first_seen": "2025-11-10T10:00:00Z",
  "last_seen": "2025-11-16T15:30:00Z",
  "average_confidence": 0.92,
  "metadata": {},
  "relationships": {
    "outgoing": [
      {
        "type": "WORKS_ON",
        "target": "CRESCO",
        "target_type": "PROJECT",
        "strength": 0.95,
        "mentioned_in": 8,
        "contexts": 5
      }
    ],
    "incoming": []
  }
}
```

### Search Knowledge Graph

```http
GET /api/knowledge/search?query={text}&limit={n}
```

**Parameters:**
- `query` (required) - Search text
- `limit` (optional) - Max results (default: 10)

**Example:** `/api/knowledge/search?query=cresco&limit=5`

**Response:**
```json
[
  {
    "name": "CRESCO",
    "type": "PROJECT",
    "aliases": ["cresco"],
    "mentioned": 15,
    "last_seen": "2025-11-16T14:20:00Z",
    "relevance_score": 0.98
  }
]
```

### Get Team Structures

```http
GET /api/knowledge/structures
```

**Response:**
```json
{
  "structures": [
    {
      "name": "Customer Pillar",
      "type": "pillar",
      "mentioned": 15,
      "contexts": 8,
      "first_seen": "2025-11-10T10:00:00Z",
      "teams": [
        {
          "name": "Menu Team",
          "type": "team",
          "mentioned": 12,
          "contexts": 6,
          "roles": [
            {
              "name": "Engineering",
              "mentioned": 10,
              "contexts": 5
            }
          ]
        }
      ]
    }
  ],
  "total_pillars": 2,
  "total_teams": 3,
  "total_roles": 8
}
```

### Get Knowledge Statistics

```http
GET /api/knowledge/stats
```

**Response:**
```json
{
  "total_nodes": 45,
  "total_edges": 78,
  "nodes_by_type": {
    "PERSON": 20,
    "PROJECT": 15,
    "TEAM": 8,
    "DATE": 2
  },
  "top_mentioned": [
    {
      "name": "Jef Adriaenssens",
      "type": "PERSON",
      "mentions": 12
    },
    {
      "name": "CRESCO",
      "type": "PROJECT",
      "mentions": 15
    }
  ],
  "timestamp": "2025-11-16T16:00:00Z"
}
```

---

## User Profiles

### Get User Profile

```http
GET /api/profiles/{id}
```

**Parameters:**
- `id` (path) - User profile ID

**Response:**
```json
{
  "id": 1,
  "name": "Jef Adriaenssens",
  "normalized_name": "jef adriaenssens",
  "role": "Senior Engineer",
  "projects": ["CRESCO", "Just Deals"],
  "markets": ["Spain", "Netherlands"],
  "colleagues": ["Andy", "Sarah", "Alberto"],
  "preferences": {
    "relevance_threshold": 70,
    "auto_apply_threshold": 80
  },
  "created_at": "2025-11-15T10:00:00Z",
  "updated_at": "2025-11-16T12:00:00Z"
}
```

### Create User Profile

```http
POST /api/profiles/
```

**Request Body:**
```json
{
  "name": "John Doe",
  "role": "Product Manager",
  "projects": ["Project A", "Project B"],
  "markets": ["US", "UK"],
  "colleagues": ["Jane", "Bob"],
  "preferences": {
    "relevance_threshold": 75
  }
}
```

**Response:** Created profile object (201 Created)

### Update User Profile

```http
PUT /api/profiles/{id}
```

**Request Body:** (all fields optional)
```json
{
  "projects": ["New Project"],
  "markets": ["Germany"],
  "preferences": {
    "relevance_threshold": 80
  }
}
```

**Response:** Updated profile object

---

## Keyboard Shortcuts

### Get Shortcuts

```http
GET /api/shortcuts
```

**Response:**
```json
[
  {
    "id": 1,
    "action": "quick_add_todo",
    "key": "1",
    "description": "Quick add to To-Do",
    "category": "task_creation",
    "is_enabled": true
  }
]
```

### Update Shortcut

```http
PUT /api/shortcuts/{id}
```

**Request Body:**
```json
{
  "key": "2",
  "is_enabled": false
}
```

**Response:** Updated shortcut object

---

## Health & System

### Health Check

```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-16T16:00:00Z",
  "services": {
    "database": "connected",
    "ollama": {
      "status": "connected",
      "url": "http://localhost:11434",
      "model": "qwen2.5:7b-instruct"
    },
    "gemini": {
      "status": "connected",
      "model": "gemini-2.0-flash-exp"
    }
  },
  "version": "1.0.0"
}
```

### Get System Info

```http
GET /api/system/info
```

**Response:**
```json
{
  "version": "1.0.0",
  "python_version": "3.11.5",
  "fastapi_version": "0.104.1",
  "database": {
    "type": "sqlite",
    "size_mb": 45.2,
    "tables": 12
  },
  "uptime_seconds": 3600
}
```

---

## Error Responses

All endpoints may return error responses in this format:

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters",
  "error_code": "INVALID_INPUT"
}
```

### 404 Not Found
```json
{
  "detail": "Task not found",
  "error_code": "NOT_FOUND"
}
```

### 500 Internal Server Error
```json
{
  "detail": "An internal error occurred",
  "error_code": "INTERNAL_ERROR",
  "trace_id": "uuid"
}
```

---

## Rate Limiting

Current implementation has no rate limiting. For production:

- **Recommended:** 100 requests/minute per IP
- **Burst:** 20 requests/second

---

## Authentication

**Current:** No authentication (local development)

**Future:** JWT-based authentication
```http
Authorization: Bearer <jwt_token>
```

---

## Pagination

For endpoints returning lists (where supported):

**Query Parameters:**
- `page` - Page number (default: 1)
- `limit` - Items per page (default: 50, max: 200)

**Response Headers:**
- `X-Total-Count` - Total items
- `X-Page` - Current page
- `X-Per-Page` - Items per page

---

## Webhooks

**Coming Soon:** Webhook support for external integrations

**Planned events:**
- `task.created`
- `task.updated`
- `task.completed`
- `context.processed`

---

## SDK Examples

### Python

```python
import requests

BASE_URL = "http://localhost:8000/api"

# Get all tasks
response = requests.get(f"{BASE_URL}/tasks")
tasks = response.json()

# Create task
new_task = {
    "title": "New task",
    "status": "todo",
    "assignee": "John"
}
response = requests.post(f"{BASE_URL}/tasks", json=new_task)

# Process context with Lotus
context = {
    "content": "Meeting notes...",
    "source_type": "manual"
}
response = requests.post(f"{BASE_URL}/assistant/message", json=context)
```

### TypeScript

```typescript
const BASE_URL = 'http://localhost:8000/api';

// Get all tasks
const tasks = await fetch(`${BASE_URL}/tasks`).then(r => r.json());

// Create task
const newTask = {
  title: 'New task',
  status: 'todo',
  assignee: 'John'
};
const response = await fetch(`${BASE_URL}/tasks`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(newTask)
});

// Process context
const context = {
  content: 'Meeting notes...',
  source_type: 'manual'
};
await fetch(`${BASE_URL}/assistant/message`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(context)
});
```

### cURL

```bash
# Get all tasks
curl http://localhost:8000/api/tasks

# Create task
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"New task","status":"todo"}'

# Process context
curl -X POST http://localhost:8000/api/assistant/message \
  -H "Content-Type: application/json" \
  -d '{"content":"Meeting notes...","source_type":"manual"}'

# Upload PDF
curl -X POST http://localhost:8000/api/assistant/process-pdf \
  -F "file=@meeting.pdf"
```

---

## Testing

The interactive API documentation (Swagger UI) at http://localhost:8000/docs allows you to test all endpoints directly in your browser.

---

**Last Updated:** November 2025  
**API Version:** 1.0.0  
**Status:** Production Ready
