# Cognitive Nexus - Entity & Knowledge Persistence Guide

## 🎯 Overview

This guide addresses two key topics:
1. **Hierarchical TEAM entities** (replacing COMPANY)
2. **Knowledge persistence** across contexts

---

## 1. Hierarchical TEAM Entities

### What Changed?

**Before:** `COMPANY` entity type for organizations (e.g., "Co-op", "Sainsbury's")

**After:** `TEAM` entity type with **hierarchical metadata** that supports:
- **Pillars**: Customer Pillar, Partner Pillar, Ventures Pillar
- **Teams**: Menu Team, Search Team, Platform Team, Growth Team
- **Roles/Contexts**: Engineering, Product, Research, Sales, Design

### Entity Structure

```typescript
{
  "name": "Menu Team",
  "type": "TEAM",
  "metadata": {
    "pillar": "Customer Pillar",      // Optional
    "team_name": "Menu Team",         // Optional
    "role": "Engineering"              // Optional
  }
}
```

### Examples

**1. Pillar-level team:**
```
Input: "The Customer Pillar is working on personalization"
Entity: {
  name: "Customer Pillar",
  type: "TEAM",
  metadata: { pillar: "Customer Pillar" }
}
```

**2. Specific team:**
```
Input: "Menu Team needs to review the specs"
Entity: {
  name: "Menu Team",
  type: "TEAM",
  metadata: { team_name: "Menu Team" }
}
```

**3. Team with pillar context:**
```
Input: "Customer Pillar's Menu Team is handling this"
Entity: {
  name: "Menu Team",
  type: "TEAM",
  metadata: {
    pillar: "Customer Pillar",
    team_name: "Menu Team"
  }
}
```

**4. Role-based team:**
```
Input: "The Engineering team needs to deploy"
Entity: {
  name: "Engineering",
  type: "TEAM",
  metadata: { role: "Engineering" }
}
```

**5. Full hierarchy:**
```
Input: "Customer Pillar's Menu Team Engineering needs review"
Entity: {
  name: "Menu Team Engineering",
  type: "TEAM",
  metadata: {
    pillar: "Customer Pillar",
    team_name: "Menu Team",
    role: "Engineering"
  }
}
```

### UI Display

Teams are shown with **green badges** and metadata below:

```
[Menu Team]
Customer Pillar / Menu Team / Engineering
```

---

## 2. Knowledge Persistence

### Current State: ✅ What DOES Persist

**Database Storage:**
- ✅ All entities are stored in `entities` table
- ✅ All relationships are stored in `relationships` table
- ✅ Context items are stored with reasoning traces
- ✅ Data persists across sessions
- ✅ You can query historical data

**Example:**
```sql
SELECT * FROM entities WHERE name = 'Jef Adriaenssens';
-- Returns all contexts where Jef was mentioned
```

### Current State: ❌ What DOESN'T Persist (Yet)

**No Cross-Context Memory:**
- ❌ Each analysis is independent
- ❌ "Jef works on CRESCO" from Analysis #1 doesn't inform Analysis #2
- ❌ No entity deduplication across contexts
- ❌ No aggregate knowledge graph

**Example:**
```
Context 1: "Jef is working on CRESCO"
→ Creates: Entity(Jef), Entity(CRESCO), Relationship(Jef WORKS_ON CRESCO)

Context 2: "Jef needs to review the API"
→ Creates: Entity(Jef) again (duplicate!)
→ Doesn't know Jef works on CRESCO from Context 1
```

---

## 3. Building Cross-Context Knowledge Graph (Proposed)

### Goal: Persistent Knowledge Base

**What it would provide:**
1. **Entity Deduplication**: Merge "Jef" across multiple contexts
2. **Aggregate Relationships**: "Jef ALWAYS works on CRESCO" (from 5 contexts)
3. **Knowledge Queries**: "What has Jef worked on?" → [CRESCO, Just Deals, RF16]
4. **Context-Aware Inference**: Use historical data to improve extraction

### Implementation Approach

**Database Schema:**
```sql
-- New table: Knowledge Graph Nodes
CREATE TABLE knowledge_nodes (
    id INTEGER PRIMARY KEY,
    canonical_name VARCHAR(255),  -- "Jef Adriaenssens"
    entity_type VARCHAR(50),      -- PERSON, PROJECT, TEAM, DATE
    first_seen DATETIME,
    last_seen DATETIME,
    mention_count INTEGER,        -- How many contexts mentioned this
    metadata JSON                 -- Merged metadata
);

-- New table: Knowledge Edges (Relationships)
CREATE TABLE knowledge_edges (
    id INTEGER PRIMARY KEY,
    subject_node_id INTEGER,
    predicate VARCHAR(100),
    object_node_id INTEGER,
    strength FLOAT,               -- 0.0-1.0 based on mention frequency
    first_seen DATETIME,
    last_seen DATETIME,
    mention_count INTEGER
);

-- Link entities to knowledge nodes
ALTER TABLE entities ADD COLUMN knowledge_node_id INTEGER;
```

**Entity Deduplication Algorithm:**
```python
def merge_entity_to_knowledge_graph(entity: Entity):
    """Merge extracted entity into knowledge graph."""

    # 1. Find existing node (fuzzy match on name)
    existing_node = find_similar_node(entity.name, entity.type)

    if existing_node:
        # Update existing node
        existing_node.mention_count += 1
        existing_node.last_seen = now()
        existing_node.merge_metadata(entity.metadata)
        entity.knowledge_node_id = existing_node.id
    else:
        # Create new node
        node = KnowledgeNode(
            canonical_name=entity.name,
            entity_type=entity.type,
            first_seen=now(),
            last_seen=now(),
            mention_count=1,
            metadata=entity.metadata
        )
        entity.knowledge_node_id = node.id
```

**Relationship Aggregation:**
```python
def aggregate_relationships():
    """Aggregate relationships across contexts."""

    # Group relationships by (subject, predicate, object)
    grouped = db.query(
        Relationship.subject_entity.knowledge_node_id,
        Relationship.predicate,
        Relationship.object_entity.knowledge_node_id,
        func.count().label('count')
    ).group_by(subject, predicate, object).all()

    for subject, predicate, obj, count in grouped:
        edge = KnowledgeEdge(
            subject_node_id=subject,
            predicate=predicate,
            object_node_id=obj,
            strength=calculate_strength(count),
            mention_count=count
        )
```

**Query API:**
```python
@router.get("/knowledge/entity/{name}")
async def get_entity_knowledge(name: str):
    """Get all knowledge about an entity."""

    node = find_node(name)

    return {
        "entity": node.canonical_name,
        "type": node.entity_type,
        "mentioned_in": node.mention_count,
        "first_seen": node.first_seen,
        "last_seen": node.last_seen,
        "relationships": [
            {
                "type": edge.predicate,
                "target": edge.object_node.canonical_name,
                "strength": edge.strength,
                "mentioned_in": edge.mention_count
            }
            for edge in node.outgoing_edges
        ]
    }

# Example query
GET /api/knowledge/entity/Jef%20Adriaenssens

# Response
{
  "entity": "Jef Adriaenssens",
  "type": "PERSON",
  "mentioned_in": 12,
  "first_seen": "2025-11-10",
  "last_seen": "2025-11-16",
  "relationships": [
    {
      "type": "WORKS_ON",
      "target": "CRESCO",
      "strength": 0.95,
      "mentioned_in": 8
    },
    {
      "type": "WORKS_ON",
      "target": "Just Deals",
      "strength": 0.67,
      "mentioned_in": 3
    },
    {
      "type": "COMMUNICATES_WITH",
      "target": "Andy Maclean",
      "strength": 0.83,
      "mentioned_in": 5
    }
  ]
}
```

---

## 4. Context-Aware Inference (Future)

With knowledge graph, agents can use historical data:

**Before (no memory):**
```
Input: "Jef needs to finish the API work by Friday"
Agent: Extracts [Jef (PERSON), Friday (DATE)]
       No project context!
```

**After (with knowledge):**
```
Input: "Jef needs to finish the API work by Friday"
Agent: Extracts [Jef (PERSON), Friday (DATE)]
       Queries knowledge: "Jef works on CRESCO (strength: 0.95)"
       Infers: [CRESCO (PROJECT)] - even though not mentioned!
       Relationship: "Jef WORKS_ON CRESCO" (inferred from history)
```

---

## 5. UI Enhancements for Knowledge Graph

**1. Entity Profile View:**
```tsx
<EntityProfile entity="Jef Adriaenssens">
  <Stats>
    - Mentioned in 12 contexts
    - Works on: CRESCO (8 mentions), Just Deals (3 mentions)
    - Communicates with: Andy (5 mentions), Sarah (3 mentions)
  </Stats>
  <Timeline>
    - Nov 10: First mentioned in "Menu Team meeting notes"
    - Nov 12: Mentioned in "CRESCO deployment discussion"
    - Nov 16: Mentioned in "API review"
  </Timeline>
</EntityProfile>
```

**2. Knowledge Graph Visualization:**
```
[Jef Adriaenssens]
    ├─WORKS_ON→ [CRESCO] (8 mentions, 95% strength)
    ├─WORKS_ON→ [Just Deals] (3 mentions, 67% strength)
    ├─PART_OF→ [Menu Team] (12 mentions, 100% strength)
    └─COMMUNICATES_WITH→ [Andy Maclean] (5 mentions, 83% strength)
```

**3. Smart Suggestions:**
```
When creating task:
"Assignee: Jef"
→ Suggests: Project: CRESCO (based on 95% relationship strength)
```

---

## 6. Would You Like Me to Build This?

I can implement the **Cross-Context Knowledge Graph** feature:

**Estimated effort:** 4-6 hours
- Database schema changes (1 hour)
- Entity deduplication algorithm (2 hours)
- Relationship aggregation (1 hour)
- Query APIs (1 hour)
- UI components (1 hour)

**Benefits:**
- ✅ Remembers "Jef works on CRESCO" permanently
- ✅ Deduplicates entities across contexts
- ✅ Shows historical relationships
- ✅ Enables smart task suggestions
- ✅ Builds true organizational knowledge base

**Let me know if you want me to build this!**

---

## 7. Testing the TEAM Entity Changes

### Example Input:
```
Hey team, the Customer Pillar's Menu Team Engineering needs to deploy
the new search API by Friday. Sarah from Product and Mike from Research
should review the Partner Pillar's integration specs. The Ventures Pillar
Growth Team is waiting on this.
```

### Expected Output:

**Entities:**
- Jef (PERSON)
- Sarah (PERSON)
- Mike (PERSON)
- Friday (DATE)
- Menu Team (TEAM - pillar: Customer Pillar, team: Menu Team, role: Engineering)
- Product (TEAM - role: Product)
- Research (TEAM - role: Research)
- Partner Pillar (TEAM - pillar: Partner Pillar)
- Growth Team (TEAM - pillar: Ventures Pillar, team: Growth Team)

**UI Display:**
```
Teams (4):
  [Menu Team]
  Customer Pillar / Menu Team / Engineering

  [Product]
  Product

  [Research]
  Research

  [Growth Team]
  Ventures Pillar / Growth Team
```

---

## Summary

**✅ TEAM Entity Enhancements: DONE**
- Hierarchical metadata (pillar, team, role)
- UI shows team hierarchy
- Backend extracts team context

**⏳ Knowledge Persistence: NOT YET**
- Data persists in database
- But no cross-context memory
- Each analysis is independent

**🚀 Next Step: Build Knowledge Graph?**
- Would enable "Jef always works on CRESCO" memory
- Entity deduplication across contexts
- Historical relationship tracking
- Smart task suggestions

**Let me know if you want the Knowledge Graph feature!**
