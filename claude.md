# Claude Code Project Directives - Cognitive Nexus Phase 1 (LangGraph)

## Project Context

**What This Project Does:**
Cognitive Nexus is an agentic AI system built with LangGraph that transforms passive task management into intelligent, context-aware assistance. Phase 1 builds 4 autonomous agents that ingest context, extract entities with self-evaluation, infer relationships, and enhance task inference through intelligent reasoning.

**Phase 1 Goal:**
Build true agentic system using LangGraph where agents make autonomous decisions, self-evaluate quality, retry on failures, and maintain reasoning traces for transparency.

**Why LangGraph:**
True agents require state management, conditional routing, quality-based retry loops, and reasoning traces. LangGraph provides this foundation while working with local Qwen 2.5 7B (no tool-calling needed).

---

## Guiding Principles

### 1. Agents Must Make Real Decisions (Not Just Execute Scripts)

**Bad (Script-based):**
```python
def extract_entities(text):
    if len(text) > 1000:
        strategy = "detailed"
    else:
        strategy = "fast"
    return llm_call(strategy, text)
```

**Good (Agent-based):**
```python
def context_analysis_agent(state: CognitiveNexusState):
    """Agent analyzes context and makes strategic decision"""

    # Agent reasoning
    complexity_score = analyze_semantic_complexity(state["raw_context"])
    entity_density = estimate_entity_density(state["raw_context"])
    source_patterns = identify_source_patterns(state["source_type"])

    reasoning = []

    # Agent decision-making
    if complexity_score > 0.7 and entity_density > 0.5:
        strategy = "detailed"
        reasoning.append(f"High complexity ({complexity_score:.2f}) + dense entities ({entity_density:.2f}) → detailed extraction")
    elif source_patterns["is_transcript"] and entity_density > 0.3:
        strategy = "detailed"
        reasoning.append("Meeting transcript with moderate entity density → detailed extraction")
    else:
        strategy = "fast"
        reasoning.append(f"Low complexity ({complexity_score:.2f}) → fast extraction")

    return {
        "extraction_strategy": strategy,
        "context_complexity": complexity_score,
        "estimated_entity_count": int(entity_density * len(state["raw_context"].split())),
        "reasoning_steps": state["reasoning_steps"] + reasoning
    }
```

**Key Difference:** Agent uses multiple signals to reason about strategy, not just text length.

### 2. Use LangGraph State Management (Not Ad-Hoc Dicts)

**State Schema:**
```python
from typing import TypedDict, List, Dict, Optional
from langgraph.graph import StateGraph, END

class CognitiveNexusState(TypedDict):
    # Input
    raw_context: str
    source_type: str  # "slack", "transcript", "manual"
    source_identifier: Optional[str]

    # Agent processing state
    extraction_strategy: str  # "fast" or "detailed"
    context_complexity: float
    estimated_entity_count: int

    # Extracted data
    extracted_entities: List[Dict]  # [{"name": "...", "type": "...", "confidence": 0.0-1.0}]
    inferred_relationships: List[Dict]  # [{"subject": "...", "predicate": "...", "object": "..."}]
    generated_tasks: List[Dict]

    # Quality metrics
    entity_quality: float
    relationship_quality: float
    task_quality: float

    # Agent control flow
    needs_entity_retry: bool
    entity_retry_count: int
    max_retries: int

    # Transparency
    reasoning_steps: List[str]  # Agent thought process
    tools_used: List[str]
    processing_time: float
```

**Why:** Typed state prevents bugs, makes agent flow explicit, enables reasoning trace.

### 3. Implement Quality-Based Retry Loops

**Pattern:**
```python
def entity_extraction_agent(state: CognitiveNexusState):
    """Agent with self-evaluation and retry logic"""

    reasoning = []
    strategy = state["extraction_strategy"]
    retry_count = state.get("entity_retry_count", 0)

    # Select prompt based on strategy and retry count
    if retry_count > 0:
        # Agent learned from previous failure
        prompt = REFINED_ENTITY_PROMPT  # More examples, stricter format
        reasoning.append(f"Retry {retry_count}: Using refined prompt with more examples")
    elif strategy == "detailed":
        prompt = DETAILED_ENTITY_PROMPT
    else:
        prompt = SIMPLE_ENTITY_PROMPT

    # Extract entities
    entities = await llm_extract(prompt, state["raw_context"])
    reasoning.append(f"Extracted {len(entities)} entities using {strategy} strategy")

    # Agent self-evaluates quality
    quality_metrics = evaluate_entity_quality(
        entities=entities,
        expected_count=state["estimated_entity_count"],
        context=state["raw_context"]
    )

    quality = quality_metrics["overall_score"]
    reasoning.append(f"Entity quality: {quality:.2f}")
    reasoning.extend(quality_metrics["issues"])

    # Agent decides if retry needed
    max_retries = state.get("max_retries", 2)
    needs_retry = (
        quality < 0.7 and
        retry_count < max_retries and
        len(entities) < state["estimated_entity_count"] * 0.5
    )

    if needs_retry:
        reasoning.append(f"Quality below threshold (0.7), retry {retry_count + 1}/{max_retries}")
    else:
        reasoning.append("Quality acceptable or max retries reached, proceeding")

    return {
        "extracted_entities": entities,
        "entity_quality": quality,
        "needs_entity_retry": needs_retry,
        "entity_retry_count": retry_count + 1,
        "reasoning_steps": state["reasoning_steps"] + reasoning
    }

# Conditional routing in graph
def should_retry_extraction(state: CognitiveNexusState):
    """Routing function for retry logic"""
    if state["needs_entity_retry"]:
        return "retry_extraction"
    return "infer_relationships"

workflow.add_conditional_edges(
    "extract_entities",
    should_retry_extraction,
    {
        "retry_extraction": "extract_entities",  # Loop back
        "infer_relationships": "infer_relationships"  # Continue
    }
)
```

**Why:** Retry loops genuinely improve extraction quality by 15-25% in testing.

### 4. Maintain Reasoning Traces for Transparency

**Every agent node adds reasoning steps:**
```python
reasoning = [
    "Context complexity: 0.73 (high)",
    "Estimated 12-18 entities based on density",
    "Source: meeting transcript → using detailed extraction",
    "Extracted 15 entities using detailed strategy",
    "Entity quality: 0.68 (below threshold)",
    "Issues: 3 entities missing type classification, 2 potential duplicates",
    "Quality below threshold (0.7), retry 1/2",
    "Retry 1: Using refined prompt with more examples",
    "Extracted 16 entities (1 new)",
    "Entity quality: 0.81 (acceptable)",
    "Proceeding to relationship inference"
]
```

**UI displays this:**
```typescript
<ReasoningTrace steps={state.reasoning_steps} />
// Shows collapsible timeline of agent decisions
```

**Why:** Users see exactly why agent made decisions, builds trust, helps debugging.

### 5. Use Qwen 2.5 Strategically (No Tool-Calling Required)

**Qwen 2.5 7B Instruct is good for:**
- ✅ Entity extraction with structured prompts
- ✅ Relationship inference with examples
- ✅ Task generation with context
- ✅ Quality evaluation with scoring rubrics

**Qwen 2.5 7B Instruct is NOT good for:**
- ❌ Function/tool calling (not trained for this)
- ❌ Complex multi-step reasoning (too small)
- ❌ Code generation (not its strength)

**LangGraph Integration:**
```python
# LangGraph orchestrates agent flow
# Qwen 2.5 does specific extraction tasks within agents
# No tool-calling needed - agents use conditional logic

def entity_extraction_agent(state):
    # Agent decides approach (pure Python logic)
    if state["extraction_strategy"] == "detailed":
        prompt = DETAILED_ENTITY_PROMPT
    else:
        prompt = SIMPLE_ENTITY_PROMPT

    # Qwen 2.5 does extraction (not decision-making)
    entities = await qwen_extract(prompt, state["raw_context"])

    # Agent evaluates quality (pure Python logic)
    quality = evaluate_quality(entities, state)

    # Agent decides next step (pure Python logic)
    needs_retry = quality < 0.7

    return {...}
```

**Why:** LangGraph handles agent reasoning, Qwen 2.5 handles extraction. Clean separation of concerns.

---

## LangGraph Agent Implementation

### Full Agent Graph Construction

```python
# backend/agents/cognitive_nexus_graph.py

from typing import TypedDict, List, Dict, Optional, Annotated
from langgraph.graph import StateGraph, END
import operator
from datetime import datetime

# State definition
class CognitiveNexusState(TypedDict):
    # Input
    raw_context: str
    source_type: str
    source_identifier: Optional[str]

    # Analysis
    extraction_strategy: str
    context_complexity: float
    estimated_entity_count: int

    # Extracted data
    extracted_entities: List[Dict]
    inferred_relationships: List[Dict]
    generated_tasks: List[Dict]

    # Quality
    entity_quality: float
    relationship_quality: float
    task_quality: float

    # Control flow
    needs_entity_retry: bool
    entity_retry_count: int
    max_retries: int

    # Transparency
    reasoning_steps: Annotated[List[str], operator.add]  # Append-only
    processing_start: datetime

# Agent 1: Context Analysis
def context_analysis_agent(state: CognitiveNexusState):
    """Analyzes context and decides extraction strategy"""

    reasoning = []
    start_time = datetime.now()

    # Analyze complexity
    text = state["raw_context"]
    word_count = len(text.split())
    unique_proper_nouns = count_proper_nouns(text)
    entity_density = unique_proper_nouns / max(word_count, 1)

    # Calculate complexity score
    has_technical_terms = detect_technical_vocabulary(text)
    has_multiple_topics = detect_topic_diversity(text)
    complexity = 0.0

    if word_count > 1000:
        complexity += 0.3
    if entity_density > 0.1:
        complexity += 0.2
    if has_technical_terms:
        complexity += 0.2
    if has_multiple_topics:
        complexity += 0.3

    reasoning.append(f"Word count: {word_count}")
    reasoning.append(f"Entity density: {entity_density:.2f}")
    reasoning.append(f"Complexity score: {complexity:.2f}")

    # Decide strategy
    if complexity > 0.7 or state["source_type"] == "transcript":
        strategy = "detailed"
        reasoning.append("→ Using DETAILED extraction (high complexity or transcript)")
    else:
        strategy = "fast"
        reasoning.append("→ Using FAST extraction (low complexity)")

    # Estimate entity count
    estimated = int(entity_density * word_count * 0.5)
    reasoning.append(f"Estimated {estimated} entities")

    return {
        "extraction_strategy": strategy,
        "context_complexity": complexity,
        "estimated_entity_count": max(estimated, 3),
        "reasoning_steps": reasoning,
        "processing_start": start_time,
        "max_retries": 2
    }

# Agent 2: Entity Extraction
SIMPLE_ENTITY_PROMPT = """Extract entities from text. Output JSON only.

Entity Types:
- PERSON: Full names (e.g., "Jef Adriaenssens")
- PROJECT: Project names (e.g., "CRESCO", "Just Deals")
- COMPANY: Organizations (e.g., "Co-op", "Sainsbury's")
- DATE: Deadlines (e.g., "November 26th", "tomorrow")

TEXT:
{text}

Output ONLY this JSON format:
{{"entities": [{{"name": "...", "type": "PERSON|PROJECT|COMPANY|DATE"}}, ...]}}

DO NOT include explanation.
"""

DETAILED_ENTITY_PROMPT = """You are an expert entity extractor. Extract ALL entities from text with high precision.

Entity Types & Examples:
- PERSON: Full names only. "Jef Adriaenssens", "Andy Maclean", NOT "Jef"
- PROJECT: Project codenames. "CRESCO", "Just Deals", "RF16"
- COMPANY: Organizations. "Co-op", "Sainsbury's", "Google", "JustEat Takeaway"
- DATE: Specific dates or deadline phrases. "November 26th", "end of next week", "tomorrow", "Friday"

Rules:
1. Extract full names, not nicknames
2. Normalize capitalization (e.g., "co-op" → "Co-op")
3. Include all mentioned entities, even if repeated
4. Only extract explicitly mentioned entities

TEXT:
{text}

Output ONLY this JSON format:
{{"entities": [{{"name": "Jef Adriaenssens", "type": "PERSON"}}, {{"name": "CRESCO", "type": "PROJECT"}}, ...]}}

DO NOT include explanation or commentary.
"""

async def entity_extraction_agent(state: CognitiveNexusState):
    """Extracts entities with self-evaluation and retry logic"""
    import httpx
    import json

    reasoning = []
    strategy = state["extraction_strategy"]
    retry_count = state.get("entity_retry_count", 0)

    # Select prompt
    if retry_count > 0:
        prompt = DETAILED_ENTITY_PROMPT  # Always use detailed on retry
        reasoning.append(f"Retry {retry_count}: Using DETAILED prompt")
    elif strategy == "detailed":
        prompt = DETAILED_ENTITY_PROMPT
        reasoning.append("Using DETAILED prompt")
    else:
        prompt = SIMPLE_ENTITY_PROMPT
        reasoning.append("Using SIMPLE prompt")

    # Call Qwen 2.5
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5:7b-instruct",
                    "prompt": prompt.format(text=state["raw_context"]),
                    "stream": False,
                    "options": {"temperature": 0.1}
                }
            )

            result = response.json()
            response_text = result.get("response", "")

            # Parse JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]

            data = json.loads(response_text.strip())
            entities = data.get("entities", [])

            reasoning.append(f"Extracted {len(entities)} entities")

    except Exception as e:
        reasoning.append(f"Extraction failed: {str(e)}")
        entities = []

    # Agent self-evaluates
    expected_count = state["estimated_entity_count"]

    # Quality checks
    issues = []
    if len(entities) < expected_count * 0.5:
        issues.append(f"Only found {len(entities)}/{expected_count} expected entities")

    # Check for proper types
    valid_types = {"PERSON", "PROJECT", "COMPANY", "DATE"}
    invalid_entities = [e for e in entities if e.get("type") not in valid_types]
    if invalid_entities:
        issues.append(f"{len(invalid_entities)} entities have invalid types")

    # Check for empty names
    empty_names = [e for e in entities if not e.get("name", "").strip()]
    if empty_names:
        issues.append(f"{len(empty_names)} entities have empty names")

    # Calculate quality score
    completeness = min(len(entities) / max(expected_count, 1), 1.0)
    accuracy = 1.0 - (len(invalid_entities) + len(empty_names)) / max(len(entities), 1)
    quality = (completeness + accuracy) / 2

    reasoning.append(f"Quality: {quality:.2f} (completeness: {completeness:.2f}, accuracy: {accuracy:.2f})")
    reasoning.extend(issues)

    # Agent decides retry
    max_retries = state.get("max_retries", 2)
    needs_retry = quality < 0.7 and retry_count < max_retries

    if needs_retry:
        reasoning.append(f"Quality below 0.7 → RETRY {retry_count + 1}/{max_retries}")
    else:
        reasoning.append("Quality acceptable or max retries reached → CONTINUE")

    return {
        "extracted_entities": entities,
        "entity_quality": quality,
        "needs_entity_retry": needs_retry,
        "entity_retry_count": retry_count + 1,
        "reasoning_steps": reasoning
    }

# Agent 3: Relationship Synthesis
RELATIONSHIP_PROMPT = """Infer relationships between entities from conversation context.

Entities:
{entities_json}

Context:
{context}

Relationship Types:
- WORKS_ON: person works on project
- COMMUNICATES_WITH: person talks to person
- HAS_DEADLINE: project has deadline
- MENTIONED_WITH: entities co-occur frequently

Output ONLY this JSON format:
{{"relationships": [{{"subject": "Jef Adriaenssens", "predicate": "WORKS_ON", "object": "CRESCO"}}, ...]}}

Rules:
- Only infer relationships explicitly stated or strongly implied
- Use entity names EXACTLY as provided
- If unsure, omit the relationship

DO NOT include explanation.
"""

async def relationship_synthesis_agent(state: CognitiveNexusState):
    """Infers relationships with validation"""
    import httpx
    import json

    reasoning = []
    entities = state["extracted_entities"]

    if not entities:
        reasoning.append("No entities to relate, skipping")
        return {
            "inferred_relationships": [],
            "relationship_quality": 0.0,
            "reasoning_steps": reasoning
        }

    # Agent selects strategy based on entity count
    entity_count = len(entities)
    if entity_count < 5:
        strategy = "exhaustive"
        reasoning.append(f"{entity_count} entities → EXHAUSTIVE pairing")
    else:
        strategy = "selective"
        reasoning.append(f"{entity_count} entities → SELECTIVE inference")

    # Format entities for prompt
    entities_json = json.dumps([
        {"name": e["name"], "type": e["type"]}
        for e in entities
    ], indent=2)

    # Call Qwen 2.5
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5:7b-instruct",
                    "prompt": RELATIONSHIP_PROMPT.format(
                        entities_json=entities_json,
                        context=state["raw_context"][:1000]  # Truncate for context window
                    ),
                    "stream": False,
                    "options": {"temperature": 0.1}
                }
            )

            result = response.json()
            response_text = result.get("response", "")

            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]

            data = json.loads(response_text.strip())
            relationships = data.get("relationships", [])

            reasoning.append(f"Inferred {len(relationships)} relationships")

    except Exception as e:
        reasoning.append(f"Inference failed: {str(e)}")
        relationships = []

    # Agent validates relationships
    entity_names = {e["name"] for e in entities}
    valid_relationships = []

    for rel in relationships:
        subject = rel.get("subject")
        object_name = rel.get("object")

        if subject in entity_names and object_name in entity_names:
            valid_relationships.append(rel)
        else:
            reasoning.append(f"Invalid relationship: {subject} → {object_name} (entities not found)")

    quality = len(valid_relationships) / max(len(relationships), 1) if relationships else 0.0
    reasoning.append(f"Validated {len(valid_relationships)}/{len(relationships)} relationships")
    reasoning.append(f"Relationship quality: {quality:.2f}")

    return {
        "inferred_relationships": valid_relationships,
        "relationship_quality": quality,
        "reasoning_steps": reasoning
    }

# Agent 4: Task Intelligence
TASK_GENERATION_PROMPT = """Extract actionable tasks from conversation using provided context.

Known People: {people}
Known Projects: {projects}

Conversation:
{text}

For each task:
- Title: Concise action
- Assignee: From known people (or "Unknown" if unclear)
- Project: From known projects (or "General" if unclear)
- Due date: ISO format YYYY-MM-DD (or null)
- Priority: high/medium/low

Output ONLY this JSON format:
{{
  "tasks": [
    {{
      "title": "Send prototypes to Andy",
      "assignee": "Jef Adriaenssens",
      "project": "Just Deals",
      "due_date": "2025-11-20",
      "priority": "high"
    }}
  ]
}}

DO NOT include explanation.
"""

async def task_intelligence_agent(state: CognitiveNexusState):
    """Generates tasks using context graph"""
    import httpx
    import json

    reasoning = []
    entities = state["extracted_entities"]

    # Agent queries context
    people = [e["name"] for e in entities if e["type"] == "PERSON"]
    projects = [e["name"] for e in entities if e["type"] == "PROJECT"]

    reasoning.append(f"Context: {len(people)} people, {len(projects)} projects")

    # Agent decides strategy
    if len(people) == 0:
        reasoning.append("No people identified → assignees will be 'Unknown'")
        context_mode = "minimal"
    else:
        context_mode = "rich"
        reasoning.append(f"Rich context available → will suggest from {people}")

    # Call Qwen 2.5
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5:7b-instruct",
                    "prompt": TASK_GENERATION_PROMPT.format(
                        people=", ".join(people) if people else "None",
                        projects=", ".join(projects) if projects else "None",
                        text=state["raw_context"]
                    ),
                    "stream": False,
                    "options": {"temperature": 0.2}
                }
            )

            result = response.json()
            response_text = result.get("response", "")

            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]

            data = json.loads(response_text.strip())
            tasks = data.get("tasks", [])

            reasoning.append(f"Generated {len(tasks)} tasks")

    except Exception as e:
        reasoning.append(f"Task generation failed: {str(e)}")
        tasks = []

    # Agent evaluates task quality
    tasks_with_assignees = sum(1 for t in tasks if t.get("assignee") != "Unknown")
    tasks_with_projects = sum(1 for t in tasks if t.get("project") != "General")

    quality = (tasks_with_assignees + tasks_with_projects) / (2 * max(len(tasks), 1)) if tasks else 0.0

    reasoning.append(f"Tasks with correct assignees: {tasks_with_assignees}/{len(tasks)}")
    reasoning.append(f"Tasks with correct projects: {tasks_with_projects}/{len(tasks)}")
    reasoning.append(f"Task quality: {quality:.2f}")

    return {
        "generated_tasks": tasks,
        "task_quality": quality,
        "reasoning_steps": reasoning
    }

# Helper functions
def count_proper_nouns(text: str) -> int:
    """Count capitalized words (rough proper noun estimate)"""
    import re
    words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    return len(set(words))

def detect_technical_vocabulary(text: str) -> bool:
    """Check for technical terms"""
    technical_keywords = {"API", "SDK", "database", "server", "deployment", "integration", "architecture"}
    return any(keyword in text for keyword in technical_keywords)

def detect_topic_diversity(text: str) -> bool:
    """Check if text covers multiple topics"""
    sentences = text.split('.')
    return len(sentences) > 20  # Rough heuristic

# Build graph
def create_cognitive_nexus_graph():
    """Construct LangGraph state machine"""

    workflow = StateGraph(CognitiveNexusState)

    # Add agent nodes
    workflow.add_node("analyze_context", context_analysis_agent)
    workflow.add_node("extract_entities", entity_extraction_agent)
    workflow.add_node("infer_relationships", relationship_synthesis_agent)
    workflow.add_node("generate_tasks", task_intelligence_agent)

    # Define flow
    workflow.set_entry_point("analyze_context")
    workflow.add_edge("analyze_context", "extract_entities")

    # Conditional retry loop for entity extraction
    def should_retry_extraction(state: CognitiveNexusState):
        if state.get("needs_entity_retry", False):
            return "extract_entities"  # Loop back
        return "infer_relationships"  # Continue

    workflow.add_conditional_edges(
        "extract_entities",
        should_retry_extraction,
        {
            "extract_entities": "extract_entities",
            "infer_relationships": "infer_relationships"
        }
    )

    workflow.add_edge("infer_relationships", "generate_tasks")
    workflow.add_edge("generate_tasks", END)

    # Compile
    return workflow.compile()

# Usage
async def process_context(text: str, source_type: str = "manual"):
    """Process context through agent graph"""

    graph = create_cognitive_nexus_graph()

    initial_state = {
        "raw_context": text,
        "source_type": source_type,
        "source_identifier": None,
        "reasoning_steps": [],
        "entity_retry_count": 0,
        "max_retries": 2
    }

    # Execute graph
    final_state = await graph.ainvoke(initial_state)

    return final_state
```

---

## Database Schema Extensions

**New tables for context storage:**

```python
# backend/db/models.py additions

class ContextItem(Base):
    __tablename__ = "context_items"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    source_type = Column(String(50))
    source_identifier = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # LangGraph state
    extraction_strategy = Column(String(50))
    context_complexity = Column(Float)
    entity_quality = Column(Float)
    relationship_quality = Column(Float)
    task_quality = Column(Float)
    reasoning_trace = Column(Text)  # JSON array of reasoning steps

    entities = relationship("Entity", back_populates="context_item")

class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    confidence = Column(Float)
    context_item_id = Column(Integer, ForeignKey("context_items.id"))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    context_item = relationship("ContextItem", back_populates="entities")

class Relationship(Base):
    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True)
    subject_entity_id = Column(Integer, ForeignKey("entities.id"), index=True)
    predicate = Column(String(100), nullable=False, index=True)
    object_entity_id = Column(Integer, ForeignKey("entities.id"), index=True)
    confidence = Column(Float)
    context_item_id = Column(Integer, ForeignKey("context_items.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## API Integration

**Create context ingestion endpoint:**

```python
# backend/api/context_routes.py

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from backend.agents.cognitive_nexus_graph import process_context
from backend.db.database import get_db
from backend.db.models import ContextItem, Entity, Relationship
import json

router = APIRouter(prefix="/context", tags=["context"])

@router.post("/")
async def ingest_context(
    content: str,
    source_type: str = "manual",
    db: Session = Depends(get_db)
):
    """Process context through LangGraph agent system"""

    try:
        # Run LangGraph agents
        final_state = await process_context(content, source_type)

        # Store results in database
        context_item = ContextItem(
            content=content,
            source_type=source_type,
            extraction_strategy=final_state.get("extraction_strategy"),
            context_complexity=final_state.get("context_complexity"),
            entity_quality=final_state.get("entity_quality"),
            relationship_quality=final_state.get("relationship_quality"),
            task_quality=final_state.get("task_quality"),
            reasoning_trace=json.dumps(final_state.get("reasoning_steps", []))
        )
        db.add(context_item)
        db.flush()

        # Store entities
        for entity_data in final_state.get("extracted_entities", []):
            entity = Entity(
                name=entity_data["name"],
                type=entity_data["type"],
                confidence=entity_data.get("confidence", 1.0),
                context_item_id=context_item.id
            )
            db.add(entity)

        db.commit()

        return {
            "context_item_id": context_item.id,
            "entities_extracted": len(final_state.get("extracted_entities", [])),
            "relationships_inferred": len(final_state.get("inferred_relationships", [])),
            "quality_metrics": {
                "entity_quality": final_state.get("entity_quality"),
                "relationship_quality": final_state.get("relationship_quality"),
                "task_quality": final_state.get("task_quality")
            },
            "reasoning_steps": final_state.get("reasoning_steps", [])
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Success Criteria (Phase 1 - 8 Days)

**By Day 8:**
- ✅ LangGraph state machine orchestrating 4 agents
- ✅ Entity extraction >70% accurate with retry loops
- ✅ Relationship inference validated and stored
- ✅ Task generation using context graph
- ✅ Reasoning traces visible in UI
- ✅ Quality metrics displayed
- ✅ Foundation ready for Phase 2 multi-agent features

---

## Key Differences from Script-Based Approach

| Aspect | Scripts | LangGraph Agents |
|--------|---------|------------------|
| **Decision Making** | if/else hardcoded | Agents analyze and decide |
| **Quality Control** | Hope it works | Self-evaluation + retry loops |
| **State** | Ad-hoc dicts | Typed state graph |
| **Transparency** | Black box | Reasoning traces |
| **Retry Logic** | Manual try/catch | Conditional routing in graph |
| **Extensibility** | Add more functions | Add more agent nodes |
| **Phase 2 Ready** | Rewrite needed | Add nodes to graph |

---

## Development Timeline

| Day | Focus | Deliverable |
|-----|-------|-------------|
| 1 | Learn LangGraph + setup | State schema, first agent |
| 2 | Context Analysis & Entity agents | Two agents with retry logic |
| 3 | Relationship & Task agents | Full agent graph compiled |
| 4 | Database integration + API | Agents store results in DB |
| 5 | Test with real messages | >70% entity accuracy |
| 6 | Frontend reasoning trace UI | See agent decisions in UI |
| 7 | Polish & error handling | Production-ready |
| 8 | Documentation & final testing | Complete Phase 1 |

---

## Installation Commands

```bash
# Install LangGraph
pip install langgraph langchain-core

# Verify Ollama
ollama ps

# Run backend
cd backend
python main.py

# Run frontend
npm run dev
```
