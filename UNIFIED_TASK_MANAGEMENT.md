# Unified Task Management System

## Overview

The Cognitive Nexus system has been upgraded to provide **unified task management** - a single endpoint that intelligently processes context and automatically creates, updates, or enriches tasks as appropriate.

This is a **"living system"** where every piece of context makes the task management system better, whether by creating new tasks, updating existing ones, adding comments, or simply enriching the knowledge graph.

---

## Key Concepts

### The Problem We Solved

Previously, there were two separate systems:
1. **Task Inference API**: Manually create tasks from text
2. **Context Ingestion API**: Extract entities and relationships

This led to:
- Duplicate task creation
- No connection between context and existing tasks
- Manual effort to update tasks with new information

### The Solution: Task Integration Agent

The new **Task Integration Agent** is the 4th agent in the Cognitive Nexus pipeline. It intelligently decides how each piece of context should integrate with your task management system.

**Four Operation Types:**

| Operation | When to Use | Example |
|-----------|-------------|---------|
| **CREATE** | Clear new action item not covered by existing tasks | "We need to prepare the Q4 report by Friday" → Creates new task |
| **UPDATE** | Changes core task properties (deadline, status, assignee) | "The CRESCO deadline moved to next Monday" → Updates task deadline |
| **COMMENT** | Related discussion/update without changing task core | "Jef mentioned we should use the new API" → Adds comment to task |
| **ENRICH** | Contextual information with no task implications | "Jef works on the Menu Team" → Just updates knowledge graph |

---

## Architecture

### Agent Pipeline

```
Context Input
    ↓
[1] Context Analysis Agent
    ↓ (extraction_strategy, context_complexity)
[2] Entity Extraction Agent
    ↓ (extracted_entities: people, projects, dates, teams)
[3] Relationship Synthesis Agent
    ↓ (inferred_relationships: WORKS_ON, COMMUNICATES_WITH, etc.)
[4] Task Integration Agent ← NEW!
    ↓ (task_operations: CREATE/UPDATE/COMMENT/ENRICH)
Database Execution
    ↓
Response (entities, relationships, tasks created/updated/commented)
```

### Task Integration Logic

The Task Integration Agent:

1. **Extracts Key Information** from entities:
   - People (assignees)
   - Projects (value streams)
   - Dates (deadlines)
   - Context topics

2. **Queries Existing Tasks** (last 50 by updated_at):
   - Loads task metadata (title, assignee, project, status)
   - Prepares for similarity matching

3. **Calculates Task Similarity**:
   - Project match (40% weight)
   - Assignee match (30% weight)
   - Keyword overlap (30% weight)

4. **Calls LLM with Context**:
   - Provides conversation text
   - Provides existing tasks summary
   - Requests operation decision with reasoning

5. **Validates Operations**:
   - Ensures task_id exists for UPDATE/COMMENT
   - Checks operation appropriateness
   - Calculates quality score

6. **Returns task_operations**:
```json
[
  {
    "operation": "CREATE",
    "task_id": null,
    "data": {
      "title": "Prepare Q4 Report",
      "assignee": "Jef Adriaenssens",
      "project": "CRESCO",
      "due_date": "2025-11-22",
      "description": "Quarterly report covering all metrics",
      "notes": "Mentioned in Slack by Andy"
    },
    "reasoning": "Clear deadline (Friday) and action item not covered by existing tasks"
  }
]
```

---

## API Usage

### Endpoint: POST /api/context/

**Request:**
```json
{
  "content": "Hey Jef, the CRESCO deadline moved to next Monday. Can you update the report to include the new metrics?",
  "source_type": "slack",
  "source_identifier": "channel-engineering-2025-11-17"
}
```

**Response:**
```json
{
  "context_item_id": 42,
  "entities_extracted": 3,
  "relationships_inferred": 2,
  "tasks_created": 0,
  "tasks_updated": 1,
  "comments_added": 1,
  "quality_metrics": {
    "entity_quality": 0.95,
    "relationship_quality": 0.90,
    "task_quality": 0.92,
    "context_complexity": 0.65
  },
  "reasoning_steps": [
    "Agent 1: Context complexity=0.65, extraction_strategy=detailed",
    "Agent 2: Extracted 3 entities (PERSON: Jef Adriaenssens, PROJECT: CRESCO, DATE: next Monday)",
    "Agent 3: Inferred 2 relationships (Jef WORKS_ON CRESCO, CRESCO HAS_DEADLINE next Monday)",
    "Agent 4: UPDATE operation - deadline change for existing CRESCO task, COMMENT operation - context about new metrics"
  ]
}
```

### What Happened Behind the Scenes

1. **Queried existing tasks** - Found task with title "CRESCO Q4 Report" assigned to Jef
2. **Task Integration Agent decided**:
   - **UPDATE**: Deadline changed from "2025-11-22" to "2025-11-20" (next Monday)
   - **COMMENT**: Added comment "Update to include new metrics (from Slack discussion)"
3. **Knowledge Graph Updated**:
   - Merged "Jef Adriaenssens" entity (seen before, incremented mention count)
   - Strengthened "Jef WORKS_ON CRESCO" relationship
   - Updated "CRESCO HAS_DEADLINE" relationship with new date

---

## Decision Criteria

### When CREATE is Chosen

✅ Clear action item with deadline
✅ Not covered by any existing task
✅ Has assignee (person) and optional project

**Example:**
```
"We need to send an email about occasions tile performance by Friday"
→ CREATE: New task "Send email about occasions tile performance"
```

### When UPDATE is Chosen

✅ Mentions existing task (by project/topic)
✅ Changes core properties:
   - Deadline moved
   - Status changed (e.g., "CRESCO is done")
   - Assignee changed
   - Scope significantly changed

**Example:**
```
"The CRESCO deadline moved to next Monday"
→ UPDATE: Existing task due_date changed
```

### When COMMENT is Chosen

✅ Related to existing task
✅ Provides context but doesn't change core properties:
   - Progress update ("making good progress")
   - Discussion point ("should we use the new API?")
   - Reference material ("here are the data points")

**Example:**
```
"Jef mentioned we should add the conversion metrics to the report"
→ COMMENT: Added to CRESCO task
```

### When ENRICH is Chosen

✅ No clear action item
✅ Just contextual/informational
✅ Updates knowledge graph but no task implications

**Example:**
```
"Jef works on the Menu Team in the Customer Pillar"
→ ENRICH: Knowledge graph updated, no task action
```

---

## Quality Metrics

### Task Quality Score (0.0 - 1.0)

The agent calculates task quality based on:

- **Operation appropriateness** (0.4 weight):
  - CREATE with all required fields: 1.0
  - UPDATE with valid task_id: 1.0
  - COMMENT with valid task_id: 0.9
  - ENRICH: 0.8

- **Information completeness** (0.3 weight):
  - Has assignee: +0.3
  - Has project: +0.3
  - Has deadline: +0.4

- **Reasoning quality** (0.3 weight):
  - Clear reasoning provided: +0.3

**Example:**
```json
{
  "operation": "CREATE",
  "data": {
    "title": "Send Q4 report",
    "assignee": "Jef Adriaenssens",
    "project": "CRESCO",
    "due_date": "2025-11-22"
  },
  "reasoning": "Clear deadline and action item"
}
```
**Quality Score**: 0.4 (operation) + 1.0 (all info complete) + 0.3 (reasoning) = **0.85**

---

## Examples

### Example 1: Creating a New Task

**Input:**
```
"Hey team, we need to launch the new search feature by December 1st.
Andy will lead this and Jef will help with the backend."
```

**Agent Decision:**
```json
{
  "operation": "CREATE",
  "task_id": null,
  "data": {
    "title": "Launch new search feature",
    "assignee": "Andy Maclean",
    "project": "Search Team",
    "due_date": "2025-12-01",
    "description": "Launch new search feature with backend support",
    "notes": "Jef helping with backend implementation"
  },
  "reasoning": "Clear action item with deadline and assignee, not covered by existing tasks"
}
```

**Result:**
- ✅ New task created
- ✅ Entities extracted: Andy Maclean, Jef Adriaenssens, Search Team, December 1st
- ✅ Relationships: Andy WORKS_ON Search Team, Jef WORKS_ON Search Team

---

### Example 2: Updating Existing Task

**Input:**
```
"The CRESCO report deadline needs to be pushed to next Friday due to
data collection delays."
```

**Agent Decision:**
```json
{
  "operation": "UPDATE",
  "task_id": "existing-task-uuid",
  "data": {
    "due_date": "2025-11-29",
    "notes": "Deadline extended due to data collection delays"
  },
  "reasoning": "Existing CRESCO task found, deadline change required"
}
```

**Result:**
- ✅ Existing task due_date updated
- ✅ Notes appended with reason for extension
- ✅ Knowledge graph relationship "CRESCO HAS_DEADLINE" updated

---

### Example 3: Adding Comment to Task

**Input:**
```
"Quick update on the CRESCO project - we've finished the data analysis
and starting the report writing phase."
```

**Agent Decision:**
```json
{
  "operation": "COMMENT",
  "task_id": "existing-task-uuid",
  "data": {
    "text": "Progress update: Data analysis complete, starting report writing phase",
    "author": "Cognitive Nexus"
  },
  "reasoning": "Progress update on existing CRESCO task, no core property changes needed"
}
```

**Result:**
- ✅ Comment added to existing task
- ✅ Knowledge graph updated with CRESCO mentions

---

### Example 4: Knowledge Graph Enrichment Only

**Input:**
```
"Jef Adriaenssens is a senior engineer on the Menu Team within the
Customer Pillar. He specializes in backend systems."
```

**Agent Decision:**
```json
{
  "operation": "ENRICH",
  "task_id": null,
  "data": {},
  "reasoning": "Contextual information about team structure, no actionable task items"
}
```

**Result:**
- ✅ Entity "Jef Adriaenssens" merged in knowledge graph
- ✅ Team hierarchy captured:
  ```json
  {
    "pillar": "Customer Pillar",
    "team_name": "Menu Team",
    "role": "Engineering"
  }
  ```
- ❌ No task action taken

---

## Advanced Features

### 1. Task Similarity Matching

The system calculates similarity between context and existing tasks to avoid duplicates:

```python
def calculate_task_similarity(context_project, context_person, task) -> float:
    score = 0.0

    # Project match (40% weight)
    if context_project and task.value_stream:
        if context_project.lower() in task.value_stream.lower():
            score += 0.4

    # Assignee match (30% weight)
    if context_person and task.assignee:
        if context_person.lower() in task.assignee.lower():
            score += 0.3

    # Keyword overlap (30% weight)
    # ... (checks title/description overlap)

    return score
```

**Usage:**
- Similarity ≥ 0.6: High match, likely UPDATE or COMMENT
- Similarity 0.3-0.6: Possible match, agent decides
- Similarity < 0.3: No match, likely CREATE

---

### 2. Intelligent Note Appending

When updating task notes, the system appends rather than overwrites:

```python
# Existing notes
"Original task description from meeting"

# New context
"Deadline extended due to data delays"

# Result
"Original task description from meeting

Deadline extended due to data delays"
```

This preserves task history while adding new context.

---

### 3. Cross-Context Knowledge Persistence

The knowledge graph tracks entities and relationships **across all contexts**:

**Context 1:**
```
"Jef is working on CRESCO"
→ Jef WORKS_ON CRESCO (strength: 1.0, mentions: 1)
```

**Context 2:**
```
"Jef updated the CRESCO report"
→ Jef WORKS_ON CRESCO (strength: 1.5, mentions: 2)  # Strengthened!
```

This helps the Task Integration Agent make better decisions with more context history.

---

### 4. Transparent Reasoning Traces

Every decision includes reasoning that's visible in the API response:

```json
{
  "reasoning_steps": [
    "Agent 1: Context complexity=0.72 (multiple people and deadlines), using detailed extraction",
    "Agent 2: Extracted 4 entities: Jef Adriaenssens (PERSON), Andy Maclean (PERSON), CRESCO (PROJECT), Friday (DATE)",
    "Agent 3: Inferred 3 relationships: Jef WORKS_ON CRESCO, Andy COMMUNICATES_WITH Jef, CRESCO HAS_DEADLINE Friday",
    "Agent 4: UPDATE operation - Found existing CRESCO task, deadline change detected. COMMENT operation - Progress update about metrics"
  ]
}
```

Use the `/api/context/{id}/reasoning` endpoint to view full reasoning traces.

---

## Configuration

### Environment Variables

```bash
# No additional config needed - uses existing Cognitive Nexus settings
OLLAMA_MODEL=qwen2.5:7b-instruct
OLLAMA_BASE_URL=http://localhost:11434
```

### Task Matching Settings

In `agents/cognitive_nexus_graph.py`:

```python
# Number of recent tasks to consider for matching
TASK_MATCHING_LIMIT = 50  # Default: last 50 tasks

# Similarity threshold for task matching
TASK_SIMILARITY_THRESHOLD = 0.6  # 0.0-1.0
```

---

## Best Practices

### 1. Clear Context is Key

**❌ Poor:**
```
"Update that thing we talked about"
```

**✅ Good:**
```
"The CRESCO report deadline moved to next Monday"
```

### 2. Include Key Information

For best results, include:
- **Who**: Person names (assignees)
- **What**: Project or task names
- **When**: Deadlines or dates
- **Action**: What needs to be done

### 3. Source Identifiers

Use meaningful source identifiers for tracking:

```json
{
  "source_type": "slack",
  "source_identifier": "channel-engineering-2025-11-17-10:30am"
}
```

This helps trace which context led to which task operations.

### 4. Monitor Quality Metrics

Watch the quality scores to ensure good extraction:

- `entity_quality` > 0.8: Good entity extraction
- `relationship_quality` > 0.7: Good relationship inference
- `task_quality` > 0.75: Good task operation decisions

Low scores indicate:
- Context too vague or ambiguous
- Missing key information (people, dates, projects)
- Complex context that needs human review

---

## Troubleshooting

### No Tasks Created/Updated

**Problem:** `tasks_created=0, tasks_updated=0, comments_added=0`

**Possible Causes:**
1. Context has no actionable items → Check `reasoning_steps` for "ENRICH" operation
2. Task Integration Agent couldn't match to existing tasks → Review similarity matching
3. Missing key information (assignee, deadline) → Add more context

**Solution:**
- Include clear action items with deadlines
- Mention people explicitly
- Reference project names

---

### Duplicate Tasks Created

**Problem:** Multiple similar tasks created

**Possible Causes:**
1. Similarity threshold too high
2. Task titles don't match well
3. Different assignees or projects

**Solution:**
- Use consistent project naming
- Mention the same assignee names
- Lower `TASK_SIMILARITY_THRESHOLD` (default: 0.6)

---

### Wrong Operation Chosen

**Problem:** Agent chose UPDATE when CREATE was expected (or vice versa)

**Possible Causes:**
1. Existing task matched unexpectedly
2. Context ambiguous about intention

**Solution:**
- Review reasoning traces: `/api/context/{id}/reasoning`
- Be more explicit about intention:
  - "We need a NEW task for..."
  - "Update the EXISTING CRESCO task..."
- Check existing tasks to see what matched

---

## API Reference

### POST /api/context/

**Description:** Unified context ingestion with intelligent task integration

**Request Body:**
```typescript
{
  content: string;          // Context text (min 10 chars)
  source_type: string;      // "slack" | "transcript" | "manual"
  source_identifier?: string; // Optional source ID
}
```

**Response:**
```typescript
{
  context_item_id: number;
  entities_extracted: number;
  relationships_inferred: number;
  tasks_created: number;      // NEW
  tasks_updated: number;      // NEW
  comments_added: number;     // NEW
  quality_metrics: {
    entity_quality: number;
    relationship_quality: number;
    task_quality: number;     // NEW
    context_complexity: number;
  };
  reasoning_steps: string[];
}
```

---

### GET /api/context/{id}/reasoning

**Description:** Get detailed reasoning trace for context processing

**Response:**
```typescript
{
  context_item_id: number;
  reasoning_steps: string[];
  extraction_strategy: "fast" | "detailed";
  quality_metrics: {
    entity_quality: number;
    relationship_quality: number;
    task_quality: number;
    context_complexity: number;
  };
}
```

---

## Technical Implementation

### Database Changes

**No schema changes required!** The system uses existing tables:

- `tasks`: Create/Update operations
- `comments`: Comment operations
- `entities`: Entity extraction (existing)
- `relationships`: Relationship inference (existing)
- `knowledge_nodes`: Cross-context entity tracking (existing)
- `knowledge_edges`: Cross-context relationship tracking (existing)

---

### Agent State

New fields in `CognitiveNexusState`:

```python
class CognitiveNexusState(TypedDict):
    # ... existing fields ...

    # NEW: Task Integration
    existing_tasks: List[Dict]  # Tasks from database
    task_operations: List[Dict]  # CREATE/UPDATE/COMMENT/ENRICH operations
```

---

### Task Operation Schema

```python
{
  "operation": "CREATE" | "UPDATE" | "COMMENT" | "ENRICH",
  "task_id": Optional[str],  # Required for UPDATE/COMMENT
  "data": {
    # For CREATE:
    "title": str,
    "assignee": str,
    "project": str,
    "due_date": Optional[str],
    "description": str,
    "notes": str,

    # For UPDATE (any subset):
    "due_date": str,
    "description": str,
    "notes": str,
    "status": str,
    "title": str,

    # For COMMENT:
    "text": str,
    "author": str

    # For ENRICH:
    # (empty - no task action)
  },
  "reasoning": str  # Agent's decision explanation
}
```

---

## Migration from Old System

### Before (Task Inference API)

```python
POST /api/tasks/infer
{
  "text": "Prepare CRESCO report by Friday"
}
→ Creates task (no entity/relationship tracking)
```

### After (Unified System)

```python
POST /api/context/
{
  "content": "Prepare CRESCO report by Friday",
  "source_type": "manual"
}
→ Creates task + extracts entities + builds knowledge graph
```

**Benefits:**
- ✅ Single endpoint for all context
- ✅ Automatic task matching and updates
- ✅ Cross-context knowledge persistence
- ✅ Transparent reasoning traces

---

## Future Enhancements

Potential improvements for the unified system:

1. **Confidence Scores per Operation**: Show confidence for each CREATE/UPDATE/COMMENT decision

2. **Task Dependency Detection**: Identify when tasks depend on each other
   - "We can't start X until Y is done"

3. **Priority Inference**: Determine task priority from language cues
   - "URGENT", "high priority", "when you have time"

4. **Multi-Task Updates**: Single context updating multiple tasks
   - "All CRESCO tasks are blocked until data arrives"

5. **Smart Reminders**: Detect follow-up needs
   - "Remind me on Monday about this"

6. **Status Transitions**: Infer status changes from context
   - "CRESCO is done" → status = "done"

---

## Summary

The **Unified Task Management System** transforms context ingestion into an intelligent, living task management system:

- **One Endpoint**: Single API for all context → task integration
- **Four Operations**: CREATE, UPDATE, COMMENT, ENRICH
- **Smart Decisions**: LLM-powered operation selection
- **Transparent**: Full reasoning traces for every decision
- **Cross-Context**: Knowledge graph tracks everything
- **Quality Metrics**: Monitor extraction and decision quality

**The result:** Every piece of context makes your task management system better. 🚀
