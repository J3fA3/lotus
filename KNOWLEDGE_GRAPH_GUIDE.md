# Knowledge Graph - Complete Guide

## 🎯 Overview

The **Cross-Context Knowledge Graph** is a living, evolving knowledge base that remembers and learns from all contexts processed through the Cognitive Nexus system.

**Key Capability:** The system now remembers that "Jef works on CRESCO" permanently across all future contexts, and this knowledge gets stronger and more accurate over time.

---

## 🧠 What Problems Does It Solve?

### Problem 1: Entity Duplication

**Before Knowledge Graph:**
```
Context 1: "Jef works on CRESCO"        → Creates Entity(name="Jef")
Context 2: "jef adriaenssens needs..."  → Creates Entity(name="jef adriaenssens")
Context 3: "Jef A will review..."       → Creates Entity(name="Jef A")

Result: 3 duplicate entities for the same person!
```

**After Knowledge Graph:**
```
Context 1: "Jef works on CRESCO"        → KnowledgeNode(canonical_name="Jef")
Context 2: "jef adriaenssens needs..."  → Merges into same KnowledgeNode
                                           Updates canonical_name="Jef Adriaenssens"
                                           Adds alias: "jef"
Context 3: "Jef A will review..."       → Merges into same KnowledgeNode
                                           Adds alias: "jef a"

Result: 1 canonical entity with 3 aliases, mention_count=3
```

### Problem 2: No Cross-Context Memory

**Before Knowledge Graph:**
```
Context 1: "Jef works on CRESCO"
Context 2: "Jef needs to finish the API"  → System doesn't know Jef works on CRESCO!
```

**After Knowledge Graph:**
```
Context 1: "Jef works on CRESCO"          → Relationship(Jef WORKS_ON CRESCO, strength=0.8)
Context 2: "Jef needs to finish the API"  → System knows: Jef's strongest relationship
                                              is WORKS_ON CRESCO (strength: 0.8)
                                           → Can infer this API work is likely CRESCO-related
```

### Problem 3: Hardcoded Organizational Structure

**Before Knowledge Graph:**
```
Code has hardcoded: ["Customer Pillar", "Partner Pillar", "Menu Team"]
Reality changes → Code must be updated
```

**After Knowledge Graph:**
```
System learns from context:
- Sees "Customer Pillar" mentioned → Records it
- Sees "Customer Pillar's Menu Team" → Records hierarchy
- Tracks mention counts → Knows most important structures
- Adapts as org changes → No code updates needed!
```

---

## 🏗️ Architecture

### Core Components

```
┌─────────────────────────────────────────────────────┐
│             Context Ingestion Pipeline               │
│                                                       │
│  1. Extract entities (PERSON, PROJECT, TEAM, DATE)  │
│  2. Infer relationships (WORKS_ON, HAS_DEADLINE)    │
│  3. Store in raw tables (entities, relationships)   │
│                                                       │
│  NEW: Knowledge Graph Integration                    │
│  4. Merge entities → KnowledgeNode (deduplicate!)   │
│  5. Aggregate relationships → KnowledgeEdge         │
│  6. Learn team structures → TeamStructureEvolution  │
└─────────────────────────────────────────────────────┘
                         ↓
        ┌────────────────────────────────┐
        │   Knowledge Graph Tables       │
        │                                │
        │  • knowledge_nodes             │
        │  • knowledge_edges             │
        │  • entity_knowledge_links      │
        │  • team_structure_evolution    │
        └────────────────────────────────┘
                         ↓
        ┌────────────────────────────────┐
        │   Query APIs                   │
        │                                │
        │  GET /api/knowledge/entity/:name│
        │  GET /api/knowledge/structures │
        │  GET /api/knowledge/stats      │
        │  GET /api/knowledge/search     │
        └────────────────────────────────┘
```

### Database Schema

#### **knowledge_nodes** - Canonical Entities

Stores deduplicated, canonical representations of entities.

| Column              | Type     | Description                                      |
|---------------------|----------|--------------------------------------------------|
| `id`                | INTEGER  | Primary key                                      |
| `canonical_name`    | VARCHAR  | Best/most complete name (e.g., "Jef Adriaenssens") |
| `entity_type`       | VARCHAR  | PERSON, PROJECT, TEAM, DATE                      |
| `first_seen`        | DATETIME | When first discovered                            |
| `last_seen`         | DATETIME | Most recent mention                              |
| `mention_count`     | INTEGER  | How many times mentioned across all contexts    |
| `entity_metadata`   | JSON     | Accumulated metadata (teams, roles, etc.)        |
| `aliases`           | JSON     | Alternative names ["jef", "jef a"]               |
| `average_confidence`| FLOAT    | Average confidence score (0.0-1.0)               |

**Example Row:**
```json
{
  "canonical_name": "Jef Adriaenssens",
  "entity_type": "PERSON",
  "mention_count": 12,
  "aliases": ["jef", "jef adriaenssens", "jef a"],
  "first_seen": "2025-11-10T10:00:00",
  "last_seen": "2025-11-16T15:30:00",
  "average_confidence": 0.92
}
```

#### **knowledge_edges** - Aggregated Relationships

Stores relationships between knowledge nodes with strength scores.

| Column                  | Type     | Description                                   |
|-------------------------|----------|-----------------------------------------------|
| `id`                    | INTEGER  | Primary key                                   |
| `subject_node_id`       | INTEGER  | FK to knowledge_nodes                         |
| `predicate`             | VARCHAR  | WORKS_ON, COMMUNICATES_WITH, HAS_DEADLINE     |
| `object_node_id`        | INTEGER  | FK to knowledge_nodes                         |
| `strength`              | FLOAT    | Relationship strength (0.0-1.0)               |
| `mention_count`         | INTEGER  | How many times this relationship appeared     |
| `context_count`         | INTEGER  | In how many different contexts               |
| `average_confidence`    | FLOAT    | Average confidence across mentions            |
| `first_seen`            | DATETIME | When relationship first observed              |
| `last_seen`             | DATETIME | Most recent observation                       |

**Strength Calculation Formula:**
```python
strength = sqrt(
    (mention_count / 10) *     # Capped at 10 mentions
    (context_count / 5) *       # Capped at 5 contexts
    average_confidence          # 0.0-1.0
)
```

**Example Row:**
```json
{
  "subject": "Jef Adriaenssens",
  "predicate": "WORKS_ON",
  "object": "CRESCO",
  "strength": 0.95,
  "mention_count": 8,
  "context_count": 5,
  "average_confidence": 0.9
}
```

#### **entity_knowledge_links** - Entity-to-Node Mapping

Links raw extracted entities to canonical knowledge nodes.

| Column              | Type    | Description                                    |
|---------------------|---------|------------------------------------------------|
| `entity_id`         | INTEGER | FK to entities (raw extracted)                 |
| `knowledge_node_id` | INTEGER | FK to knowledge_nodes (canonical)              |
| `similarity_score`  | FLOAT   | How similar was the match (0.0-1.0)            |
| `match_method`      | VARCHAR | exact, fuzzy, alias                            |

**Purpose:** Allows tracing from knowledge node back to source contexts.

#### **team_structure_evolution** - Discovered Org Structure

Dynamically learns and tracks organizational hierarchy.

| Column                | Type     | Description                                 |
|-----------------------|----------|---------------------------------------------|
| `id`                  | INTEGER  | Primary key                                 |
| `structure_type`      | VARCHAR  | pillar, team, role                          |
| `structure_name`      | VARCHAR  | "Customer Pillar", "Menu Team", "Engineering" |
| `parent_structure_id` | INTEGER  | FK to self (parent in hierarchy)            |
| `first_seen`          | DATETIME | When first discovered                       |
| `last_seen`           | DATETIME | Most recent mention                         |
| `mention_count`       | INTEGER  | How often mentioned                         |
| `context_count`       | INTEGER  | In how many contexts                        |
| `associated_nodes`    | JSON     | List of knowledge_node_ids in this structure|

**Example Hierarchy:**
```
Customer Pillar (pillar, mentions: 15)
  └─ Menu Team (team, mentions: 12, parent: Customer Pillar)
      └─ Engineering (role, mentions: 10, parent: Menu Team)
```

---

## 🔧 How It Works

### 1. Entity Deduplication Algorithm

When a new entity is extracted, the system:

**Step 1: Find Candidates**
```python
# Try exact match (case-insensitive)
"Jef Adriaenssens" → finds KnowledgeNode("Jef Adriaenssens")

# Try alias match
"jef" → finds KnowledgeNode with alias "jef"

# Try fuzzy match (string similarity)
"Jef A" → calculates similarity to all PERSON nodes
         → finds "Jef Adriaenssens" (similarity: 0.85)
```

**Step 2: Select Best Match**
```python
# Score candidates based on:
similarity_score = string_similarity(new_name, candidate_name)  # 0.0-1.0
mention_boost = min(candidate.mention_count / 100, 0.1)         # Up to +0.1
recency_boost = max(0, 0.1 - (days_since_seen / 100))          # Up to +0.1

total_score = similarity_score + mention_boost + recency_boost
```

**Step 3: Merge or Create**
```python
if total_score >= 0.75:
    # High confidence → merge
    node.mention_count += 1
    node.aliases.append(new_name.lower())
    if new_confidence > node.average_confidence:
        node.canonical_name = new_name  # Better name found!

elif total_score >= 0.60:
    # Medium confidence → merge with flag
    merge_with_low_confidence_flag()

else:
    # Low confidence → create new node
    create_new_knowledge_node()
```

**String Similarity Algorithm:**
```python
def calculate_similarity(str1, str2):
    # 1. Sequence matcher (edit distance)
    base_similarity = SequenceMatcher(str1, str2).ratio()

    # 2. Token overlap (handles word order)
    tokens1 = set(str1.split())
    tokens2 = set(str2.split())
    token_overlap = len(tokens1 & tokens2) / max(len(tokens1), len(tokens2))

    # 3. Abbreviation bonus
    if is_abbreviation(str1, str2):
        abbrev_bonus = 0.3

    return max(base_similarity, token_overlap, base_similarity + abbrev_bonus)
```

### 2. Relationship Aggregation

When a relationship is inferred:

```python
# Example: Jef WORKS_ON CRESCO (from Context #5)

# Step 1: Get or create knowledge nodes for subject and object
subject_node = get_knowledge_node("Jef Adriaenssens")
object_node = get_knowledge_node("CRESCO")

# Step 2: Find existing edge
edge = find_edge(subject_node.id, "WORKS_ON", object_node.id)

if edge:
    # Update existing edge
    edge.mention_count += 1
    edge.context_count += 1  # Assuming different context
    edge.average_confidence = (
        (edge.average_confidence * (edge.mention_count - 1) + new_confidence)
        / edge.mention_count
    )
    edge.strength = calculate_strength(
        edge.mention_count,
        edge.context_count,
        edge.average_confidence
    )
else:
    # Create new edge
    create_edge(
        subject_node.id,
        "WORKS_ON",
        object_node.id,
        strength=new_confidence,
        mention_count=1,
        context_count=1
    )
```

### 3. Dynamic Team Structure Learning

When a TEAM entity is extracted with metadata:

```python
# Example: Entity(name="Menu Team", metadata={
#   "pillar": "Customer Pillar",
#   "team_name": "Menu Team",
#   "role": "Engineering"
# })

# Step 1: Learn pillar
record_structure(
    type="pillar",
    name="Customer Pillar",
    parent=None
)

# Step 2: Learn team (link to pillar)
pillar_id = get_structure_id("pillar", "Customer Pillar")
record_structure(
    type="team",
    name="Menu Team",
    parent=pillar_id
)

# Step 3: Learn role (link to team)
team_id = get_structure_id("team", "Menu Team")
record_structure(
    type="role",
    name="Engineering",
    parent=team_id
)

# Result: Hierarchy automatically discovered!
# Customer Pillar
#   └─ Menu Team
#       └─ Engineering
```

---

## 📡 API Usage

### 1. Get Entity Knowledge

**GET** `/api/knowledge/entity/{name}`

Get all knowledge about an entity across all contexts.

**Example Request:**
```bash
GET /api/knowledge/entity/Jef%20Adriaenssens
```

**Response:**
```json
{
  "entity": "Jef Adriaenssens",
  "type": "PERSON",
  "aliases": ["jef", "jef adriaenssens", "jef a"],
  "mentioned_in": 12,
  "first_seen": "2025-11-10T10:00:00",
  "last_seen": "2025-11-16T15:30:00",
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
      },
      {
        "type": "COMMUNICATES_WITH",
        "target": "Andy Maclean",
        "target_type": "PERSON",
        "strength": 0.83,
        "mentioned_in": 5,
        "contexts": 3
      }
    ],
    "incoming": []
  }
}
```

### 2. Get Discovered Team Structures

**GET** `/api/knowledge/structures`

View the organizational hierarchy learned from context.

**Response:**
```json
{
  "structures": [
    {
      "name": "Customer Pillar",
      "type": "pillar",
      "mentioned": 15,
      "contexts": 8,
      "first_seen": "2025-11-10T10:00:00",
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
            },
            {
              "name": "Product",
              "mentioned": 7,
              "contexts": 4
            }
          ]
        }
      ]
    },
    {
      "name": "Partner Pillar",
      "type": "pillar",
      "mentioned": 10,
      "contexts": 5,
      "teams": []
    }
  ],
  "total_pillars": 2,
  "total_teams": 1,
  "total_roles": 2
}
```

### 3. Search Knowledge Graph

**GET** `/api/knowledge/search?query={text}`

Fuzzy search across knowledge graph.

**Example:**
```bash
GET /api/knowledge/search?query=cresc&limit=10
```

**Response:**
```json
[
  {
    "name": "CRESCO",
    "type": "PROJECT",
    "aliases": ["cresco"],
    "mentioned": 15,
    "last_seen": "2025-11-16T14:20:00"
  }
]
```

### 4. Get Knowledge Graph Stats

**GET** `/api/knowledge/stats`

Get graph statistics.

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
    {"name": "Jef Adriaenssens", "type": "PERSON", "mentions": 12},
    {"name": "CRESCO", "type": "PROJECT", "mentions": 15},
    {"name": "Menu Team", "type": "TEAM", "mentions": 10}
  ],
  "timestamp": "2025-11-16T16:00:00"
}
```

### 5. Get Entity Evolution Timeline

**GET** `/api/knowledge/evolution/{name}`

View how entity knowledge evolved over time.

**Response:**
```json
{
  "entity": "Jef Adriaenssens",
  "type": "PERSON",
  "first_seen": "2025-11-10T10:00:00",
  "last_seen": "2025-11-16T15:30:00",
  "total_mentions": 12,
  "aliases": ["jef", "jef adriaenssens", "jef a"],
  "current_metadata": {},
  "timeline": [
    {
      "timestamp": "2025-11-10T10:00:00",
      "name_variant": "Jef",
      "confidence": 0.8,
      "similarity_to_canonical": 1.0,
      "context_source": "slack",
      "context_id": 1
    },
    {
      "timestamp": "2025-11-12T14:20:00",
      "name_variant": "Jef Adriaenssens",
      "confidence": 0.95,
      "similarity_to_canonical": 0.85,
      "context_source": "transcript",
      "context_id": 5
    }
  ]
}
```

---

## 🚀 Deployment & Migration

### For New Installations

No action needed! The knowledge graph tables are created automatically when the backend starts.

```bash
cd backend
python main.py
```

The `init_db()` function in `database.py` creates all tables, including knowledge graph tables.

### For Existing Databases

Run the migration script:

```bash
cd backend
python db/migrations/001_add_knowledge_graph_tables.py migrate
```

To check migration status:
```bash
python db/migrations/001_add_knowledge_graph_tables.py status
```

To rollback (if needed):
```bash
python db/migrations/001_add_knowledge_graph_tables.py rollback
```

---

## 🎯 Example Use Cases

### Use Case 1: Cross-Context Entity Recognition

**Scenario:**
```
Week 1: "Jef is working on CRESCO data pipeline"
Week 2: "jef adriaenssens will present at Friday's meeting"
Week 3: "Jef A needs to review the API specs"
```

**What Happens:**
1. Week 1: Creates KnowledgeNode(canonical_name="Jef", type=PERSON)
2. Week 2: Fuzzy match finds existing node, updates canonical_name="Jef Adriaenssens", adds alias "jef"
3. Week 3: Alias match finds node immediately, adds alias "jef a"

**Query Result:**
```bash
GET /api/knowledge/entity/Jef
```
Returns:
- canonical_name: "Jef Adriaenssens"
- aliases: ["jef", "jef adriaenssens", "jef a"]
- mentioned_in: 3 contexts
- relationships: [WORKS_ON CRESCO (strength: 0.8)]

### Use Case 2: Relationship Strength Tracking

**Scenario:**
```
Context 1: "Jef works on CRESCO" (confidence: 0.9)
Context 2: "Jef presented CRESCO results" (confidence: 0.85)
Context 3: "CRESCO team includes Jef" (confidence: 0.95)
Context 4: "Jef needs CRESCO data" (confidence: 0.8)
```

**Edge Evolution:**
```
After Context 1:
  Jef WORKS_ON CRESCO
  strength: 0.9, mentions: 1, contexts: 1

After Context 2:
  Jef WORKS_ON CRESCO
  strength: 0.91, mentions: 2, contexts: 2
  (increased due to context diversity)

After Context 3:
  Jef WORKS_ON CRESCO
  strength: 0.93, mentions: 3, contexts: 3
  (high confidence + multiple contexts)

After Context 4:
  Jef WORKS_ON CRESCO
  strength: 0.95, mentions: 4, contexts: 4
```

### Use Case 3: Dynamic Org Chart Learning

**Scenario:**
```
Context 1: "Customer Pillar is working on personalization"
Context 2: "Menu Team (Customer Pillar) needs review"
Context 3: "Customer Pillar's Menu Team Engineering deployed API"
Context 4: "Search Team is also part of Customer Pillar"
```

**Structure Evolution:**
```
After Context 1:
  Customer Pillar (pillar, mentions: 1)

After Context 2:
  Customer Pillar (pillar, mentions: 2)
    └─ Menu Team (team, mentions: 1, parent: Customer Pillar)

After Context 3:
  Customer Pillar (pillar, mentions: 3)
    └─ Menu Team (team, mentions: 2, parent: Customer Pillar)
        └─ Engineering (role, mentions: 1, parent: Menu Team)

After Context 4:
  Customer Pillar (pillar, mentions: 4)
    ├─ Menu Team (team, mentions: 2, parent: Customer Pillar)
    │   └─ Engineering (role, mentions: 1, parent: Menu Team)
    └─ Search Team (team, mentions: 1, parent: Customer Pillar)
```

**Query Result:**
```bash
GET /api/knowledge/structures
```
Shows complete hierarchy with mention statistics!

---

## 🔍 Troubleshooting

### Issue: Entities not being deduplicated

**Symptom:** Same entity appearing multiple times

**Possible Causes:**
1. Names are too different (similarity < 0.60)
2. Entity types don't match (PERSON vs TEAM)
3. Confidence scores too low

**Solution:**
- Check similarity scores in `entity_knowledge_links` table
- Adjust similarity thresholds in `KnowledgeGraphService._select_best_match()`
- Review entity extraction quality

### Issue: Relationship strength not increasing

**Symptom:** Edge strength stays the same despite multiple mentions

**Possible Causes:**
1. Same context being processed multiple times
2. Low confidence scores
3. Mentions in same context (not increasing context_count)

**Solution:**
- Check `context_count` field (should increase for different contexts)
- Verify average_confidence is reasonable (> 0.5)
- Review strength calculation formula

### Issue: Team structures not being learned

**Symptom:** `/api/knowledge/structures` returns empty

**Possible Causes:**
1. No TEAM entities extracted
2. Team metadata not present
3. Structure names don't match exactly

**Solution:**
- Check entity extraction includes TEAM type
- Verify entity_metadata field contains pillar/team_name/role
- Review `_learn_team_structure()` method logic

---

## 📊 Performance Considerations

### Database Indexes

The knowledge graph uses indexes for fast queries:

**knowledge_nodes:**
- `canonical_name` (for name lookups)
- `entity_type` (for type filtering)

**knowledge_edges:**
- `subject_node_id + predicate` (for outgoing relationships)
- `object_node_id + predicate` (for incoming relationships)
- `strength` (for sorting by strength)

**entity_knowledge_links:**
- `entity_id` (for reverse lookup)
- `knowledge_node_id` (for node lookup)

### Query Optimization Tips

1. **Filter by entity_type** when searching:
   ```
   GET /api/knowledge/entity/Jef?entity_type=PERSON
   ```

2. **Use pagination** for large result sets:
   ```
   GET /api/knowledge/search?query=team&limit=20
   ```

3. **Cache** frequently accessed entities client-side

---

## 🎓 Advanced Topics

### Custom Similarity Algorithms

To add custom entity matching logic, modify `KnowledgeGraphService._calculate_string_similarity()`:

```python
def _calculate_string_similarity(self, str1: str, str2: str) -> float:
    # Existing logic...

    # Add custom domain-specific matching
    if is_project_code(str1) and is_project_code(str2):
        return project_code_similarity(str1, str2)

    return final_score
```

### Relationship Strength Tuning

Adjust strength calculation in `_calculate_edge_strength()`:

```python
# Current formula
strength = sqrt(
    (mention_count / 10) *
    (context_count / 5) *
    average_confidence
)

# Custom: Emphasize context diversity more
strength = sqrt(
    (mention_count / 10) *
    (context_count / 3) *      # Lower cap → higher weight
    average_confidence
) ** 0.8  # Smooth curve
```

### Adding New Structure Types

To learn additional hierarchy levels beyond pillar/team/role:

1. Add new structure_type in `TeamStructureEvolution`
2. Update entity extraction prompts to capture new types
3. Add logic to `_learn_team_structure()` method

---

## 🚀 Future Enhancements

### Planned Features

1. **Entity Merging UI**
   - Manual merge/split entities
   - Confirm fuzzy matches
   - Manage aliases

2. **Relationship Confidence Decay**
   - Reduce strength over time if not re-observed
   - Model temporal validity of relationships

3. **Knowledge Graph Visualization**
   - Interactive D3.js network graph
   - Filter by entity type, strength threshold
   - Timeline view of evolution

4. **Semantic Similarity**
   - Use embeddings for entity matching
   - Better abbreviation detection
   - Multilingual support

5. **Knowledge Export**
   - Export to RDF/OWL formats
   - Integration with external knowledge bases
   - GraphQL API for advanced queries

---

## 📚 References

**Code Locations:**
- Models: `backend/db/knowledge_graph_models.py`
- Service: `backend/services/knowledge_graph_service.py`
- API Routes: `backend/api/knowledge_routes.py`
- Integration: `backend/api/context_routes.py` (lines 126-173)
- Migration: `backend/db/migrations/001_add_knowledge_graph_tables.py`

**Related Documentation:**
- [Cognitive Nexus Phase 1](./COGNITIVE_NEXUS_PHASE1.md) - LangGraph agents
- [Cognitive Nexus Phase 2](./COGNITIVE_NEXUS_PHASE2.md) - Frontend UI
- [Team Entities Guide](./TEAM_ENTITIES_AND_KNOWLEDGE_PERSISTENCE.md) - Team hierarchy

---

## ✅ Summary

The Knowledge Graph transforms the Cognitive Nexus from a stateless processor into a **living, evolving knowledge base**:

✅ **Deduplicates entities** across all contexts
✅ **Tracks relationship strength** based on evidence
✅ **Learns organizational structure** dynamically
✅ **Remembers knowledge** permanently
✅ **Evolves** with each new context

**Result:** The system gets smarter over time, providing increasingly accurate insights into your organization's people, projects, and teams.

🎉 **Knowledge Graph is ready to use!**
