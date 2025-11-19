# Cognitive Nexus - AI-Powered Context Analysis

## 🧠 Overview

The **Cognitive Nexus** is an agentic AI system built with LangGraph that transforms passive task management into intelligent, context-aware assistance. It processes conversations, meeting notes, and messages to automatically extract entities, infer relationships, and create or update tasks.

## 🎯 Key Features

### Intelligent Context Processing
- **4 Autonomous Agents** working in a LangGraph pipeline
- **Self-evaluation** with quality metrics and retry loops
- **Cross-context memory** via Knowledge Graph
- **Transparent reasoning** traces for every decision

### Entity Recognition
- **PERSON**: Full names (e.g., "Jef Adriaenssens", "Andy Maclean")
- **PROJECT**: Project names (e.g., "CRESCO", "Just Deals")
- **TEAM**: Hierarchical teams (Pillar → Team → Role)
- **DATE**: Deadlines (e.g., "November 26th", "next Friday")

### Relationship Inference
- **WORKS_ON**: Person works on project
- **COMMUNICATES_WITH**: Person talks to person
- **HAS_DEADLINE**: Project has deadline
- **MENTIONED_WITH**: Entities co-occur frequently

### Task Intelligence
- **CREATE**: New actionable tasks
- **UPDATE**: Modify existing task properties
- **COMMENT**: Add context to existing tasks
- **ENRICH**: Update knowledge graph without task action

## 🏗️ Architecture

### LangGraph Agent Pipeline

```
User Input (Text)
    ↓
┌─────────────────────────────────────────────┐
│ Agent 1: Context Analysis                   │
│ • Analyzes complexity and entity density    │
│ • Selects extraction strategy (fast/detail) │
│ • Estimates entity count                    │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│ Agent 2: Entity Extraction (with retry)     │
│ • Extracts entities using selected strategy │
│ • Self-evaluates quality                    │
│ • Retries if quality < 0.7 (max 2 retries) │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│ Agent 3: Relationship Synthesis             │
│ • Infers relationships between entities     │
│ • Validates entity references               │
│ • Calculates relationship quality           │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│ Agent 4: Task Integration                   │
│ • Queries existing tasks                    │
│ • Decides operation (CREATE/UPDATE/COMMENT) │
│ • Executes task actions                     │
└──────────────────┬──────────────────────────┘
                   ↓
         Database + Knowledge Graph
```

### Quality-Based Retry Loop

```
Entity Extraction
    ↓
Quality Check
    ↓
< 0.7? ──Yes──> Retry (up to 2x) ──> Quality Check
    │                                      ↓
    No                                  > 0.7?
    ↓                                      ↓
Continue to Relationships            Continue
```

## 📊 Knowledge Graph

### Cross-Context Memory

The Knowledge Graph remembers entities and relationships across all contexts:

```
Context 1: "Jef works on CRESCO"
→ KnowledgeNode(Jef) + KnowledgeEdge(Jef WORKS_ON CRESCO)

Context 2: "jef adriaenssens updated CRESCO"
→ Merges to same KnowledgeNode (fuzzy matching!)
→ Strengthens edge (mention_count: 2, strength: 0.9)

Context 3: "Jef A needs CRESCO data"
→ Merges to same KnowledgeNode (alias: "jef a")
→ Further strengthens edge (mention_count: 3, strength: 0.95)
```

### Entity Deduplication

**Problem Solved:**
- "Jef" vs "jef adriaenssens" vs "Jef A" → All merged into one canonical entity
- Automatic alias tracking
- Fuzzy name matching with configurable thresholds

**Algorithm:**
1. Try exact match (case-insensitive)
2. Try alias match
3. Try fuzzy match (string similarity > 0.75)
4. Merge or create new node based on confidence

### Hierarchical Teams

TEAM entities support organizational hierarchy:

```json
{
  "name": "Menu Team",
  "type": "TEAM",
  "metadata": {
    "pillar": "Customer Pillar",
    "team_name": "Menu Team",
    "role": "Engineering"
  }
}
```

**Hierarchy Visualization:**
```
Customer Pillar (pillar)
  └─ Menu Team (team)
      ├─ Engineering (role)
      ├─ Product (role)
      └─ Design (role)

Partner Pillar (pillar)
  └─ Search Team (team)
```

The system **learns** this structure dynamically from context—no hardcoded org charts!

## 🚀 API Usage

### POST /api/context/

Process context through Cognitive Nexus agents.

**Request:**
```json
{
  "content": "Hey Jef, can you share the CRESCO data with Andy by Friday?",
  "source_type": "slack",
  "source_identifier": "channel-engineering-2025-11-18"
}
```

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
    "entity_quality": 0.92,
    "relationship_quality": 0.88,
    "task_quality": 0.85,
    "context_complexity": 0.65
  },
  "reasoning_steps": [
    "Context complexity: 0.65 (moderate)",
    "Estimated 3-5 entities based on density",
    "Using DETAILED extraction strategy",
    "Extracted 3 entities: Jef Adriaenssens (PERSON), Andy Maclean (PERSON), CRESCO (PROJECT), Friday (DATE)",
    "Entity quality: 0.92 (acceptable)",
    "Inferred 2 relationships: Jef WORKS_ON CRESCO, Jef COMMUNICATES_WITH Andy",
    "Relationship quality: 0.88 (acceptable)",
    "CREATE operation: New task 'Share CRESCO data with Andy' (due: Friday)"
  ]
}
```

### GET /api/knowledge/entity/{name}

Get all knowledge about an entity across all contexts.

**Request:**
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
  "first_seen": "2025-11-10T10:00:00Z",
  "last_seen": "2025-11-18T15:30:00Z",
  "average_confidence": 0.92,
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
    ]
  }
}
```

### GET /api/knowledge/structures

View organizational hierarchy learned from contexts.

**Response:**
```json
{
  "structures": [
    {
      "name": "Customer Pillar",
      "type": "pillar",
      "mentioned": 15,
      "contexts": 8,
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

## 💡 Usage Examples

### Example 1: Slack Message Analysis

**Input:**
```
"Hey team, the CRESCO report needs to be ready by Friday. 
Jef will handle the backend and Andy will do the frontend. 
Sarah from Product should review before we ship."
```

**Agent Processing:**
1. **Context Analysis**: Complexity 0.72 → Use DETAILED strategy
2. **Entity Extraction**: 
   - Jef Adriaenssens (PERSON)
   - Andy Maclean (PERSON)
   - Sarah (PERSON)
   - CRESCO (PROJECT)
   - Product (TEAM, role: Product)
   - Friday (DATE)
3. **Relationship Inference**:
   - Jef WORKS_ON CRESCO
   - Andy WORKS_ON CRESCO
   - Sarah PART_OF Product
4. **Task Integration**: CREATE task "Complete CRESCO report" (due: Friday, assignee: Jef)

### Example 2: Meeting Transcript

**Input:**
```
"Meeting notes from Nov 18, 2025:
- Menu Team Engineering completed the search API
- Next sprint: Partner Pillar integration
- Mike and Emma will lead the integration work
- Target completion: end of month"
```

**Agent Processing:**
1. **Context Analysis**: Transcript detected → Use DETAILED strategy
2. **Entity Extraction**:
   - Menu Team (TEAM, pillar: Menu Team, role: Engineering)
   - Partner Pillar (TEAM, pillar: Partner Pillar)
   - Mike (PERSON)
   - Emma (PERSON)
   - End of month (DATE)
3. **Relationship Inference**:
   - Mike WORKS_ON Partner Pillar integration
   - Emma WORKS_ON Partner Pillar integration
4. **Task Integration**: CREATE task "Partner Pillar integration" (due: end of month, assignees: Mike, Emma)

### Example 3: Updating Existing Task

**Input:**
```
"Quick update: The CRESCO deadline moved to next Monday 
due to data collection delays."
```

**Agent Processing:**
1. **Context Analysis**: Low complexity → Use FAST strategy
2. **Entity Extraction**: CRESCO (PROJECT), next Monday (DATE)
3. **Task Integration**: 
   - Finds existing task with project="CRESCO"
   - UPDATE operation: Changes due_date to next Monday
   - Adds note: "Deadline extended due to data collection delays"

## ⚙️ Configuration

### Constants

All AI behavior is controlled via `backend/config/constants.py`:

```python
# Quality thresholds
QUALITY_THRESHOLD_HIGH = 0.7      # Minimum for accepting results
QUALITY_THRESHOLD_MEDIUM = 0.6    # Warning threshold
DEFAULT_MAX_RETRIES = 2           # Max retry attempts

# Entity matching
ENTITY_SIMILARITY_THRESHOLD = 0.75  # Fuzzy match threshold
ALIAS_MATCH_BOOST = 0.1            # Boost for alias matches

# Task matching
MAX_RECENT_TASKS_FOR_MATCHING = 50  # Tasks to consider for updates
TASK_SIMILARITY_THRESHOLD = 0.6     # Minimum similarity to match

# Complexity weights
COMPLEXITY_WORD_COUNT_WEIGHT = 0.3
COMPLEXITY_ENTITY_DENSITY_WEIGHT = 0.2
COMPLEXITY_TECHNICAL_TERMS_WEIGHT = 0.2
COMPLEXITY_TOPIC_DIVERSITY_WEIGHT = 0.3
```

### Prompts

LLM prompts are in `backend/agents/prompts.py`:

```python
SIMPLE_ENTITY_PROMPT = """Extract entities from text. Output JSON only..."""
DETAILED_ENTITY_PROMPT = """You are an expert entity extractor..."""
RELATIONSHIP_PROMPT = """Infer relationships between entities..."""
TASK_GENERATION_PROMPT = """Extract actionable tasks from conversation..."""
```

Modify these to adjust agent behavior!

## 🎯 Quality Metrics

### Entity Quality Score

Calculated from:
- **Completeness** (0.5 weight): Found entities / Expected entities
- **Accuracy** (0.5 weight): Valid entities / Total entities

**Thresholds:**
- ≥ 0.7: Good (green ✓)
- 0.5-0.7: Fair (yellow ⚠)
- < 0.5: Low (red ✗)

### Relationship Quality Score

Calculated from:
- **Validity**: Both subject and object exist in entities
- **Confidence**: Average confidence across relationships

### Task Quality Score

Calculated from:
- **Operation appropriateness** (0.4 weight): Right operation type
- **Information completeness** (0.3 weight): Has assignee, project, deadline
- **Reasoning quality** (0.3 weight): Clear reasoning provided

## 🐛 Troubleshooting

### Low Entity Quality

**Symptoms:** entity_quality < 0.7, frequent retries

**Solutions:**
- Use more specific context with clear names
- Include more detail about people and projects
- Try source_type="transcript" for complex contexts

### No Tasks Created/Updated

**Symptoms:** tasks_created=0, tasks_updated=0

**Solutions:**
- Check reasoning_steps for "ENRICH" operation (no actionable items)
- Include clear action items with deadlines
- Mention people explicitly by name
- Reference project names

### Duplicate Entities

**Symptoms:** Same person appears multiple times in knowledge graph

**Solutions:**
- Check fuzzy matching threshold (default: 0.75)
- Review aliases in knowledge node
- Use consistent naming in contexts

### Wrong Task Operation

**Symptoms:** Agent chose UPDATE when CREATE was expected

**Solutions:**
- Review reasoning trace: `/api/context/{id}/reasoning`
- Be explicit: "We need a NEW task for..." vs "Update the EXISTING task..."
- Check task similarity scoring

## 🔬 Advanced Topics

### Custom Similarity Algorithms

Modify `KnowledgeGraphService._calculate_string_similarity()`:

```python
def _calculate_string_similarity(self, str1: str, str2: str) -> float:
    base_similarity = SequenceMatcher(None, str1, str2).ratio()
    
    # Add domain-specific logic
    if is_project_code(str1) and is_project_code(str2):
        return project_code_similarity(str1, str2)
    
    return base_similarity
```

### Relationship Strength Tuning

Adjust `_calculate_edge_strength()`:

```python
# Current formula
strength = sqrt(
    (mention_count / 10) *
    (context_count / 5) *
    average_confidence
)

# Custom: Emphasize recency
days_since_last = (now() - edge.last_seen).days
recency_factor = max(0.5, 1.0 - (days_since_last / 365))
strength = base_strength * recency_factor
```

### Adding New Entity Types

1. Add constant in `backend/config/constants.py`:
   ```python
   ENTITY_TYPE_LOCATION = "LOCATION"
   ```

2. Update prompts in `backend/agents/prompts.py`:
   ```python
   "- LOCATION: Physical locations (e.g., 'London', 'Office HQ')"
   ```

3. Update knowledge graph models if needed

## 📈 Performance

### Typical Processing Times

- **First run**: 30-60s (model loading)
- **Subsequent runs**: 10-30s
- **Simple context (< 100 words)**: 5-10s
- **Complex context (> 500 words)**: 20-40s
- **With retries**: +10-20s per retry

### Optimization Tips

1. **Batch processing**: Process multiple contexts in parallel
2. **Caching**: Cache entity extractions for similar contexts
3. **Model selection**: Use smaller models for simple tasks
4. **Prompt optimization**: Shorter prompts = faster inference

## 🚀 Future Enhancements

### Planned Features

1. **Multi-language support**: Process contexts in different languages
2. **Semantic search**: Use embeddings for better entity matching
3. **Confidence visualization**: Show confidence scores in UI
4. **Active learning**: Learn from user corrections
5. **Batch operations**: Process multiple contexts at once
6. **Custom entity types**: User-defined entity categories
7. **Relationship rules**: User-defined relationship patterns
8. **Export/import**: Knowledge graph backup and restore

---

**Related Documentation:**
- [Knowledge Graph Guide](./KNOWLEDGE_GRAPH_GUIDE.md) - Detailed KG internals
- [Unified Task Management](./UNIFIED_TASK_MANAGEMENT.md) - Task intelligence details
- [Development Guide](./DEVELOPMENT.md) - Code structure and patterns

**Last Updated:** November 2025
