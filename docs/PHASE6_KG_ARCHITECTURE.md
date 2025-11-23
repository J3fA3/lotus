# Phase 6 Knowledge Graph Architecture

## Overview

Phase 6 extends the Lotus knowledge graph from simple entity tracking to a rich contextual memory system that:
- Tracks domain-specific **concepts** (not just entities)
- Records **conversation threads** with decisions and questions
- Learns from **task outcomes** (completion, cancellation, quality)
- Builds **strategic context** through concept relationships
- Pre-computes **task similarity** for fast lookups

This transforms tasks from "dumb transcriptions" to "intelligent living documents" with rich context.

---

## Schema Design

### **1. ConceptNode**

Tracks domain-specific concepts extracted from context.

**Purpose:** Identify strategic themes and topics that matter to the user.

**Examples of VALID concepts:**
- "pharmacy pinning effectiveness"
- "Spain market launch"
- "position 3 visibility"
- "Netherlands rollout"
- "RF16 Q4 priority"

**Examples of INVALID concepts (too generic):**
- "email" ❌
- "meeting" ❌
- "analysis" ❌
- "dashboard" ❌

**Fields:**
```python
{
    "id": 1,
    "name": "pharmacy pinning effectiveness",
    "definition": "Analysis of pharmacy visibility and engagement at position 3 in search results",
    "importance_score": 0.85,  # 0.0-1.0 (high = mentioned often, urgent, strategic)
    "confidence_tier": "ESTABLISHED",  # ESTABLISHED (10+ mentions) | EMERGING (3-9) | TENTATIVE (1-2)
    "first_mentioned": "2024-11-15T10:00:00Z",
    "last_mentioned": "2024-11-22T14:30:00Z",
    "mention_count_30d": 12,
    "mention_count_total": 24,
    "related_projects": ["RF16", "CRESCO"],
    "related_markets": ["Spain", "Netherlands"],
    "related_people": ["Alberto", "Andy"],
    "archived_at": null
}
```

**Importance Score Calculation:**
```
importance_score = (
    mention_frequency_30d * 0.4 +
    urgency_signals * 0.3 +
    strategic_alignment * 0.3
)

where:
- mention_frequency_30d: Normalized count (0-1)
- urgency_signals: Urgency indicators in emails/calendar (0-1)
- strategic_alignment: Matches user projects/markets (0-1)
```

**Confidence Tiers:**
- **ESTABLISHED** (10+ mentions): High confidence, well-understood concept
- **EMERGING** (3-9 mentions): Building understanding
- **TENTATIVE** (1-2 mentions): Early signal, may be noise

**Lifecycle:**
- Concepts mentioned <3 times historically are NOT tracked (noise filtering)
- Concepts not mentioned in 6 months are archived
- Similar concepts (similarity >0.9) are merged

**Query Examples:**
```sql
-- Top 10 most important concepts
SELECT * FROM concept_nodes
WHERE archived_at IS NULL
ORDER BY importance_score DESC
LIMIT 10;

-- Concepts related to CRESCO project
SELECT * FROM concept_nodes
WHERE related_projects @> '["CRESCO"]'::jsonb
ORDER BY importance_score DESC;

-- Emerging concepts (gaining traction)
SELECT * FROM concept_nodes
WHERE confidence_tier = 'EMERGING'
  AND mention_count_30d > mention_count_total / 2;
```

---

### **2. ConversationThreadNode**

Tracks conversation threads with key decisions and unresolved questions.

**Purpose:** Remember what was discussed, track decisions, surface open questions.

**Example:**
```python
{
    "id": 1,
    "topic": "Spain pharmacy pinning analysis",
    "participants": ["Alberto Moraleda", "Jef Adriaenssens", "Andy Maclean"],
    "start_date": "2024-11-20T09:00:00Z",
    "last_updated": "2024-11-22T16:45:00Z",
    "message_count": 7,
    "key_decisions": [
        "Analysis due before Dec 5 kickoff",
        "Include position 3 visibility metrics",
        "Compare to Netherlands rollout data",
        "Sarah to review dashboard before Alberto"
    ],
    "unresolved_questions": [
        "Should we include UK pharmacy data for comparison?",
        "Do we need Italy market benchmarks?"
    ],
    "related_projects": ["RF16"],
    "related_tasks": ["task-123", "task-456"],
    "importance_score": 0.92,
    "is_active": true,
    "is_archived": false
}
```

**Key Decisions Extraction:**
Uses Gemini to identify statements like:
- "Let's do X by Y date"
- "Decision: Include Z metric"
- "Alberto confirmed [action]"
- "We agreed to [decision]"

**Unresolved Questions Extraction:**
Identifies questions that remain unanswered:
- Explicit questions ending with "?"
- Implicit questions: "We need to figure out..."
- Tentative statements: "Not sure if we should..."

**Lifecycle:**
- Threads inactive >60 days: `is_active = false`
- Threads >6 months old: `is_archived = true`
- Archive old threads to keep KG lean

**Query Examples:**
```sql
-- Active conversations with unresolved questions
SELECT * FROM conversation_threads
WHERE is_active = true
  AND jsonb_array_length(unresolved_questions) > 0
ORDER BY importance_score DESC;

-- All decisions related to CRESCO
SELECT topic, key_decisions FROM conversation_threads
WHERE related_projects @> '["CRESCO"]'::jsonb
  AND jsonb_array_length(key_decisions) > 0;
```

---

### **3. TaskOutcomeNode**

Records task completion outcomes with lessons learned.

**Purpose:** Learn from what worked (and what didn't) to improve future tasks.

**Example:**
```python
{
    "task_id": "task-123",
    "outcome": "COMPLETED",
    "completion_quality": 4.2,  # 0.0-5.0
    "estimated_effort_hours": 4.0,
    "actual_effort_hours": 6.0,
    "effort_variance": 1.5,  # actual / estimated
    "blockers": [
        "Waiting on data from Andy (1 day)",
        "Spain API access delayed (half day)",
        "Dashboard design iteration (1 hour)"
    ],
    "lessons_learned": "Position 3 analysis took 6 hours (estimated 4) due to data access delays. Similar tasks should include 2-hour buffer for data retrieval from Andy's team.",
    "task_title": "Analyze pharmacy pinning effectiveness for Spain",
    "task_project": "RF16",
    "task_market": "Spain",
    "task_assignee": "Jef Adriaenssens",
    "follow_up_task_count": 2,
    "user_satisfaction": 4,  # 1-5 stars
    "recorded_at": "2024-11-22T17:00:00Z",
    "completed_at": "2024-11-22T16:30:00Z"
}
```

**Outcome Types:**
- **COMPLETED**: Task finished successfully
- **COMPLETED_WITH_ISSUES**: Finished but had blockers/quality issues
- **CANCELLED**: User explicitly cancelled
- **IGNORED**: Created but never acted on (>7 days in todo)
- **MERGED**: Merged into another task (duplicate)

**Quality Score (0.0-5.0):**
```
quality = base_score - deductions

base_score = 5.0

deductions:
- Major edits to description: -0.5
- Significant blockers: -0.3 each
- User comments indicating issues: -0.2 each
- Follow-up tasks >3: -0.5
- Effort variance >1.5: -0.3
```

**Lessons Learned Generation:**
Uses Gemini to analyze:
- What took longer than expected?
- What blockers occurred?
- What would help similar tasks in the future?

**Signal Weight:**
Task outcomes are the **HIGHEST QUALITY** learning signal (weight = 1.0).
- Completion outcomes: 1.0 (strongest signal)
- Task edits: 0.4 (weaker signal, may be style preference)
- Cancellations: 0.6 (medium signal)

**Query Examples:**
```sql
-- High-quality completed tasks for pattern learning
SELECT * FROM task_outcomes
WHERE outcome = 'COMPLETED'
  AND completion_quality >= 4.0
ORDER BY completion_quality DESC;

-- Tasks that took significantly longer than estimated
SELECT task_title, estimated_effort_hours, actual_effort_hours,
       effort_variance, blockers
FROM task_outcomes
WHERE effort_variance > 1.5
ORDER BY effort_variance DESC;

-- Lessons learned for similar work
SELECT task_title, lessons_learned
FROM task_outcomes
WHERE task_project = 'RF16'
  AND task_market = 'Spain'
  AND lessons_learned IS NOT NULL;
```

---

### **4. ConceptRelationship**

Tracks relationships between concepts.

**Purpose:** Understand how concepts relate (similarity, prerequisites, hierarchy).

**Relationship Types:**
- **SIMILAR_TO**: Concepts are semantically similar (similarity >0.7)
- **PREREQUISITE_OF**: One concept must happen before another
- **PART_OF**: Concept is component of larger concept
- **RELATED_TO**: General relationship

**Example:**
```python
{
    "id": 1,
    "concept_id": 15,  # "pharmacy pinning effectiveness"
    "related_to_id": 23,  # "pharmacy visibility metrics"
    "relationship_type": "SIMILAR_TO",
    "strength": 0.87,
    "confidence": 0.92,
    "reason": "Both concepts analyze pharmacy search result positioning and engagement",
    "first_seen": "2024-11-15T10:00:00Z",
    "last_reinforced": "2024-11-22T14:30:00Z"
}
```

**Strength Calculation:**
```
strength = (
    semantic_similarity * 0.5 +
    co_occurrence_rate * 0.3 +
    user_confirmation * 0.2
)
```

**Lifecycle:**
- Relationships with strength <0.3 are pruned monthly
- Similar concepts (similarity >0.9) trigger merge suggestion
- Strength decays by 10% monthly if not reinforced

---

### **5. TaskSimilarityIndex**

Pre-computed task similarity for fast lookups.

**Purpose:** Enable <50ms "find similar tasks" queries (vs 500ms+ on-the-fly computation).

**Example:**
```python
{
    "task_id": "task-123",
    "similar_task_ids": ["task-456", "task-789", "task-234"],
    "similar_task_titles": [
        "Analyze pharmacy visibility for Netherlands",
        "Position 3 engagement metrics - UK market",
        "RF16 pharmacy pinning dashboard review"
    ],
    "similarity_scores": [0.92, 0.87, 0.81],
    "similarity_explanations": [
        "Both analyze pharmacy metrics for market launch",
        "Same metrics (position 3 visibility)",
        "Related project (RF16) and dashboard work"
    ],
    "computed_at": "2024-11-22T03:00:00Z",
    "is_stale": false
}
```

**Computation:**
- Runs nightly at 3am
- Computes pairwise semantic similarity for all tasks
- Stores top 10 matches per task
- Marks as stale if task updated since computation

**Similarity Score:**
```
similarity = (
    title_similarity * 0.4 +
    description_similarity * 0.3 +
    concept_overlap * 0.2 +
    context_similarity * 0.1
)
```

**Performance:**
- Without index: 500ms per query (computes embeddings + similarity)
- With index: <50ms per query (simple lookup)
- Trade-off: 5MB storage for 10x+ speed improvement

---

### **6. ConceptTaskLink**

Links concepts to tasks they're mentioned in.

**Purpose:** Enable queries like "all tasks related to X concept".

**Example:**
```python
{
    "id": 1,
    "concept_id": 15,  # "pharmacy pinning effectiveness"
    "task_id": "task-123",
    "strength": 1.0,  # Mentioned in title
    "mention_location": "title",
    "linked_at": "2024-11-22T14:30:00Z"
}
```

**Strength Scoring:**
- 1.0: Mentioned in title
- 0.7: Mentioned in description
- 0.5: Mentioned in related context (email, comment)
- 0.3: Weakly related (same project/market)

---

## New Relationship Types

### **Enhanced KG Predicates**

In addition to existing relationships (WORKS_ON, COMMUNICATES_WITH), Phase 6 adds:

**Task-Level Relationships:**
- **SIMILAR_TO**: Tasks are semantically similar
- **PREREQUISITE_OF**: Task A must complete before task B
- **FOLLOW_UP_TO**: Task B is follow-up work from task A
- **DUPLICATE_OF**: Task is duplicate (should be merged)

**Concept-Level Relationships:**
- **DISCUSSED_IN**: Concept discussed in conversation thread
- **OUTCOME_INFORMED_BY**: Task outcome provides insight for concept
- **MENTIONED_WITH**: Concepts frequently co-occur

**Example Usage:**
```python
# Find prerequisite tasks
SELECT t.* FROM tasks t
JOIN knowledge_edges e ON e.object_node_id = (
    SELECT id FROM knowledge_nodes WHERE canonical_name = 'task-123'
)
WHERE e.predicate = 'PREREQUISITE_OF'
ORDER BY e.strength DESC;

# Find concepts discussed in conversation
SELECT c.* FROM concept_nodes c
JOIN concept_relationships cr ON cr.concept_id = c.id
WHERE cr.relationship_type = 'DISCUSSED_IN'
  AND cr.related_to_id = 5  -- conversation thread ID
ORDER BY cr.strength DESC;
```

---

## Schema Evolution Strategy

### **Migration Path:**

**Migration 006: Add Phase 6 tables**
```sql
-- Create new tables
CREATE TABLE concept_nodes (...);
CREATE TABLE conversation_threads (...);
CREATE TABLE task_outcomes (...);
CREATE TABLE concept_relationships (...);
CREATE TABLE task_similarity_index (...);
CREATE TABLE concept_task_links (...);

-- Add indexes
CREATE INDEX idx_concept_importance ON concept_nodes(importance_score);
CREATE INDEX idx_concept_tier ON concept_nodes(confidence_tier);
CREATE INDEX idx_conversation_active ON conversation_threads(is_active);
CREATE INDEX idx_outcome_type ON task_outcomes(outcome);
-- ... (see models for full index list)
```

**Rollback Strategy:**
```sql
-- Drop all Phase 6 tables
DROP TABLE IF EXISTS concept_task_links;
DROP TABLE IF EXISTS task_similarity_index;
DROP TABLE IF EXISTS concept_relationships;
DROP TABLE IF EXISTS task_outcomes;
DROP TABLE IF EXISTS conversation_threads;
DROP TABLE IF EXISTS concept_nodes;
```

---

## Performance Considerations

### **KG Size Management:**

**Target:** <5000 total nodes

**Lifecycle Rules:**
1. **Concepts:** Archive if not mentioned in 6 months
2. **Conversations:** Archive if >6 months old
3. **Outcomes:** Keep indefinitely (small, high value)
4. **Relationships:** Prune if strength <0.3
5. **Similarity Index:** Rebuild nightly, prune stale entries

**Pruning Schedule:**
- Nightly (3am): Rebuild similarity index
- Weekly: Prune weak relationships (<0.3)
- Monthly: Archive old conversations, merge similar concepts
- Quarterly: Deep cleanup, optimize indexes

### **Query Performance:**

**Critical Paths (must be <500ms):**

1. **Rich context query:**
```sql
-- Get all context for task synthesis
SELECT c.*, cr.*, co.*
FROM concept_nodes c
LEFT JOIN concept_relationships cr ON cr.concept_id = c.id
LEFT JOIN conversation_threads co ON co.related_projects @> c.related_projects
WHERE c.importance_score > 0.5
  AND c.archived_at IS NULL
LIMIT 20;
```
Target: <300ms

2. **Similar task lookup:**
```sql
-- Find similar tasks (using pre-computed index)
SELECT * FROM task_similarity_index
WHERE task_id = 'task-123';
```
Target: <50ms

3. **Task outcome patterns:**
```sql
-- Find successful patterns for similar work
SELECT * FROM task_outcomes
WHERE task_project = 'RF16'
  AND outcome = 'COMPLETED'
  AND completion_quality >= 4.0
ORDER BY completed_at DESC
LIMIT 10;
```
Target: <200ms

**Optimization Strategies:**
- Index all foreign keys
- Denormalize frequently-accessed fields (task_title in outcomes)
- Use JSONB indexes for array queries
- Pre-compute expensive operations (similarity index)
- Cache frequently-accessed queries (30s TTL)

---

## Integration with Existing KG

### **Relationship to Phase 1 Models:**

**Phase 1 (existing):**
- `KnowledgeNode`: Canonical entities (people, projects, teams)
- `KnowledgeEdge`: Entity relationships (WORKS_ON, etc.)
- `EntityKnowledgeLink`: Raw entity → canonical mapping

**Phase 6 (new):**
- `ConceptNode`: Strategic themes/topics
- `ConversationThreadNode`: Discussion context
- `TaskOutcomeNode`: Learning from results
- `ConceptRelationship`: Concept connections
- `TaskSimilarityIndex`: Fast similarity lookups
- `ConceptTaskLink`: Concept-task associations

**They work together:**
- Entities track WHO/WHAT (people, projects, teams)
- Concepts track WHY (strategic themes, topics)
- Outcomes track RESULTS (what worked, what didn't)
- Conversations track CONTEXT (decisions, questions)

**Example Query (combines both):**
```sql
-- Find all tasks where Jef worked on pharmacy concepts
SELECT t.*, c.name as concept_name
FROM tasks t
JOIN concept_task_links ctl ON ctl.task_id = t.id
JOIN concept_nodes c ON c.id = ctl.concept_id
WHERE t.assignee = 'Jef Adriaenssens'
  AND c.name ILIKE '%pharmacy%'
ORDER BY c.importance_score DESC;
```

---

## Quality Metrics

### **KG Health Indicators:**

**Node Quality:**
- Average concept importance score: Target >0.6
- % concepts with confidence_tier = ESTABLISHED: Target >30%
- % concepts archived (noise): Should be <20%

**Relationship Quality:**
- Average relationship strength: Target >0.7
- % relationships with strength <0.3: Should be <10%

**Outcome Coverage:**
- % tasks with recorded outcomes: Target >80%
- Average completion quality: Target >4.0
- % outcomes with lessons learned: Target >60%

**Performance:**
- Rich context query time: <500ms
- Similar task lookup time: <50ms
- Nightly index rebuild time: <5 minutes
- Total KG size: <5000 nodes

---

## Future Enhancements

### **Phase 7 Potential:**

1. **Concept Embeddings**: Store vector embeddings for semantic search
2. **Temporal Patterns**: Track when concepts trend (weekly/monthly)
3. **Cross-User Concepts**: Share concepts across team (not just single user)
4. **Concept Hierarchies**: Build taxonomy trees (parent/child concepts)
5. **Predictive Outcomes**: ML model to predict task success from features

---

## Summary

Phase 6 KG enhancements enable:
✅ **Concept tracking**: Strategic themes beyond simple entities
✅ **Conversation memory**: Decisions and unresolved questions
✅ **Outcome learning**: What worked, what didn't, why
✅ **Fast similarity**: <50ms similar task lookups
✅ **Rich context**: Deep understanding for intelligent tasks
✅ **Performance**: <500ms queries, <5000 node limit

This transforms the KG from entity storage to a living, learning memory system.
