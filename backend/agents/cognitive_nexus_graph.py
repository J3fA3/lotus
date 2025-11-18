"""
Cognitive Nexus - LangGraph Agentic System for Context-Aware Task Management

This module implements a true agentic system using LangGraph that:
1. Analyzes context complexity and decides extraction strategy
2. Extracts entities with self-evaluation and retry loops
3. Infers relationships with validation
4. Generates context-aware tasks with intelligent assignee suggestions

Key Features:
- Autonomous agent decision-making (not script-based)
- Quality-based retry loops that improve extraction accuracy
- Reasoning traces for transparency
- Typed state management with LangGraph
- Integration with local Qwen 2.5 7B via Ollama
"""

from typing import TypedDict, List, Dict, Optional, Annotated
from langgraph.graph import StateGraph, END
import operator
from datetime import datetime
import httpx
import json
import re

from config.constants import (
    ENTITY_TYPE_PERSON,
    ENTITY_TYPE_PROJECT,
    ENTITY_TYPE_TEAM,
    ENTITY_TYPE_DATE,
    VALID_ENTITY_TYPES,
    TASK_OP_CREATE,
    TASK_OP_UPDATE,
    TASK_OP_COMMENT,
    TASK_OP_ENRICH,
    QUALITY_THRESHOLD_HIGH,
    QUALITY_THRESHOLD_MEDIUM,
    DEFAULT_MAX_RETRIES,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_URL,
    EXTRACTION_STRATEGY_FAST,
    EXTRACTION_STRATEGY_DETAILED
)


# ============================================================================
# STATE DEFINITION
# ============================================================================

class CognitiveNexusState(TypedDict):
    """Typed state for LangGraph agent orchestration.

    State flows through all agents, with each agent contributing data
    and reasoning steps. The state is immutable except for specific
    updates defined by each agent.
    """
    # Input
    raw_context: str
    source_type: str  # "slack", "transcript", "manual"
    source_identifier: Optional[str]

    # Analysis (from Context Analysis Agent)
    extraction_strategy: str  # "fast" or "detailed"
    context_complexity: float
    estimated_entity_count: int

    # Extracted data (from agents)
    extracted_entities: List[Dict]  # [{"name": "...", "type": "...", "confidence": 0.0-1.0}]
    inferred_relationships: List[Dict]  # [{"subject": "...", "predicate": "...", "object": "..."}]
    generated_tasks: List[Dict]  # DEPRECATED: Use task_operations instead

    # NEW: Task Integration (from Task Integration Agent)
    existing_tasks: List[Dict]  # Tasks from database for matching
    task_operations: List[Dict]  # [{"operation": "CREATE|UPDATE|COMMENT|ENRICH", "task_id": ..., "data": {...}}]

    # Quality metrics (from agent self-evaluation)
    entity_quality: float
    relationship_quality: float
    task_quality: float

    # Control flow (for retry logic)
    needs_entity_retry: bool
    entity_retry_count: int
    max_retries: int

    # Transparency (reasoning trace for UI)
    reasoning_steps: Annotated[List[str], operator.add]  # Append-only
    processing_start: datetime


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def count_proper_nouns(text: str) -> int:
    """Count capitalized words as a rough estimate of proper nouns.

    This is used to estimate entity density in the context.
    """
    words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    return len(set(words))


# Technical vocabulary for complexity detection
TECHNICAL_KEYWORDS = {
    "API", "SDK", "database", "server", "deployment",
    "integration", "architecture", "backend", "frontend",
    "authentication", "authorization", "endpoint", "microservice"
}


def detect_technical_vocabulary(text: str) -> bool:
    """Check if text contains technical terminology.

    Technical content may require more detailed extraction.
    """
    return any(keyword in text for keyword in TECHNICAL_KEYWORDS)


def detect_topic_diversity(text: str) -> bool:
    """Check if text covers multiple topics.

    More diverse topics may benefit from detailed extraction.
    """
    sentences = text.split('.')
    return len(sentences) > 20  # Rough heuristic


# ============================================================================
# AGENT 1: CONTEXT ANALYSIS
# ============================================================================

def context_analysis_agent(state: CognitiveNexusState) -> Dict:
    """Agent 1: Analyzes context complexity and decides extraction strategy.

    This agent examines the input context and makes strategic decisions about
    how to extract entities. It uses multiple signals (word count, entity density,
    technical terms, topic diversity) to calculate complexity and choose between
    "fast" and "detailed" extraction strategies.

    Returns:
        State updates with strategy, complexity score, and estimated entity count
    """
    reasoning = []
    start_time = datetime.now()

    # Analyze context characteristics
    text = state["raw_context"]
    word_count = len(text.split())
    unique_proper_nouns = count_proper_nouns(text)
    entity_density = unique_proper_nouns / max(word_count, 1)

    # Calculate complexity score (0.0 to 1.0)
    has_technical_terms = detect_technical_vocabulary(text)
    has_multiple_topics = detect_topic_diversity(text)
    complexity = 0.0

    if word_count > 1000:
        complexity += 0.3
        reasoning.append(f"Long text ({word_count} words) → +0.3 complexity")

    if entity_density > 0.1:
        complexity += 0.2
        reasoning.append(f"High entity density ({entity_density:.2f}) → +0.2 complexity")

    if has_technical_terms:
        complexity += 0.2
        reasoning.append("Technical vocabulary detected → +0.2 complexity")

    if has_multiple_topics:
        complexity += 0.3
        reasoning.append("Multiple topics detected → +0.3 complexity")

    reasoning.append(f"→ Final complexity score: {complexity:.2f}")

    # Agent decision: choose extraction strategy
    if complexity > 0.7 or state["source_type"] == "transcript":
        strategy = "detailed"
        reasoning.append("→ Decision: DETAILED extraction (high complexity or transcript)")
    else:
        strategy = "fast"
        reasoning.append("→ Decision: FAST extraction (low complexity)")

    # Estimate expected entity count for quality evaluation
    estimated = int(entity_density * word_count * 0.5)
    estimated = max(estimated, 3)  # At least 3 entities expected
    reasoning.append(f"→ Estimated {estimated} entities based on density")

    return {
        "extraction_strategy": strategy,
        "context_complexity": complexity,
        "estimated_entity_count": estimated,
        "reasoning_steps": reasoning,
        "processing_start": start_time,
        "max_retries": 2
    }


# ============================================================================
# AGENT 2: ENTITY EXTRACTION
# ============================================================================

SIMPLE_ENTITY_PROMPT = """Extract entities from text. Output JSON only.

Entity Types:
- PERSON: Full names (e.g., "Jef Adriaenssens")
- PROJECT: Project names (e.g., "CRESCO", "Just Deals")
- TEAM: Organizational teams/pillars/roles (e.g., "Customer Pillar", "Menu Team", "Engineering")
- DATE: Deadlines (e.g., "November 26th", "tomorrow")

TEXT:
{text}

Output ONLY this JSON format:
{{"entities": [{{"name": "Menu Team", "type": "TEAM"}}, {{"name": "Jef", "type": "PERSON"}}, ...]}}

DO NOT include explanation.
"""

DETAILED_ENTITY_PROMPT = """You are an expert entity extractor. Extract ALL entities from text with high precision.

Entity Types & Examples:
- PERSON: Full names only. "Jef Adriaenssens", "Andy Maclean", NOT "Jef"
- PROJECT: Project codenames. "CRESCO", "Just Deals", "RF16"
- TEAM: Organizational teams with hierarchy metadata
  * Pillars: "Customer Pillar", "Partner Pillar", "Ventures Pillar"
  * Teams: "Menu Team", "Search Team", "Platform Team", "Growth Team"
  * Roles/Contexts: "Engineering", "Product", "Research", "Sales", "Design"
  * Can include metadata: {{"pillar": "Customer Pillar", "team_name": "Menu Team", "role": "Engineering"}}
- DATE: Specific dates or deadline phrases. "November 26th", "end of next week", "tomorrow", "Friday"

Rules:
1. Extract full names, not nicknames
2. For TEAM entities, capture hierarchy when mentioned:
   - If "Customer Pillar's Menu Team" → extract "Menu Team" with pillar metadata
   - If "Engineering team" → extract "Engineering" as TEAM with role metadata
   - If "Product" → extract as TEAM with role="Product"
3. Normalize capitalization
4. Include all mentioned entities, even if repeated
5. Only extract explicitly mentioned entities

TEXT:
{text}

Output ONLY this JSON format with optional metadata:
{{
  "entities": [
    {{"name": "Jef Adriaenssens", "type": "PERSON"}},
    {{"name": "CRESCO", "type": "PROJECT"}},
    {{"name": "Menu Team", "type": "TEAM", "metadata": {{"pillar": "Customer Pillar", "team_name": "Menu Team"}}}},
    {{"name": "Engineering", "type": "TEAM", "metadata": {{"role": "Engineering"}}}}
  ]
}}

DO NOT include explanation or commentary.
"""


async def entity_extraction_agent(state: CognitiveNexusState) -> Dict:
    """Agent 2: Extracts entities with self-evaluation and retry logic.

    This agent uses the strategy determined by the Context Analysis Agent
    to extract entities. After extraction, it self-evaluates quality and
    decides whether a retry is needed. On retry, it uses a more detailed
    prompt to improve results.

    Returns:
        State updates with entities, quality score, and retry decision
    """
    reasoning = []
    strategy = state["extraction_strategy"]
    retry_count = state.get("entity_retry_count", 0)

    # Agent selects prompt based on strategy and retry count
    if retry_count > 0:
        prompt = DETAILED_ENTITY_PROMPT  # Always use detailed on retry
        reasoning.append(f"→ Retry {retry_count}: Using DETAILED prompt for better results")
    elif strategy == "detailed":
        prompt = DETAILED_ENTITY_PROMPT
        reasoning.append("→ Using DETAILED prompt")
    else:
        prompt = SIMPLE_ENTITY_PROMPT
        reasoning.append("→ Using SIMPLE prompt")

    # Call Qwen 2.5 via Ollama
    entities = []
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

            # Parse JSON from response (may be wrapped in markdown)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]

            data = json.loads(response_text.strip())
            entities = data.get("entities", [])

            reasoning.append(f"→ Extracted {len(entities)} entities from LLM")

    except Exception as e:
        reasoning.append(f"→ Extraction failed: {str(e)}")
        entities = []

    # Agent self-evaluates extraction quality
    expected_count = state["estimated_entity_count"]

    # Quality checks
    issues = []
    if len(entities) < expected_count * 0.5:
        issues.append(f"Only found {len(entities)}/{expected_count} expected entities")

    # Check for proper entity types
    invalid_entities = [e for e in entities if e.get("type") not in VALID_ENTITY_TYPES]
    if invalid_entities:
        issues.append(f"{len(invalid_entities)} entities have invalid types")

    # Check for empty names
    empty_names = [e for e in entities if not e.get("name", "").strip()]
    if empty_names:
        issues.append(f"{len(empty_names)} entities have empty names")

    # Calculate quality score (0.0 to 1.0)
    completeness = min(len(entities) / max(expected_count, 1), 1.0)
    accuracy = 1.0 - (len(invalid_entities) + len(empty_names)) / max(len(entities), 1)
    quality = (completeness + accuracy) / 2

    reasoning.append(f"→ Quality: {quality:.2f} (completeness: {completeness:.2f}, accuracy: {accuracy:.2f})")
    if issues:
        reasoning.extend([f"  - {issue}" for issue in issues])

    # Agent decides whether retry is needed
    max_retries = state.get("max_retries", DEFAULT_MAX_RETRIES)
    needs_retry = quality < QUALITY_THRESHOLD_HIGH and retry_count < max_retries

    if needs_retry:
        reasoning.append(f"→ Quality below threshold ({QUALITY_THRESHOLD_HIGH}) → RETRY {retry_count + 1}/{max_retries}")
    else:
        if quality >= QUALITY_THRESHOLD_HIGH:
            reasoning.append("→ Quality acceptable → CONTINUE to next agent")
        else:
            reasoning.append(f"→ Max retries reached ({max_retries}) → CONTINUE despite low quality")

    return {
        "extracted_entities": entities,
        "entity_quality": quality,
        "needs_entity_retry": needs_retry,
        "entity_retry_count": retry_count + 1,
        "reasoning_steps": reasoning
    }


# ============================================================================
# AGENT 3: RELATIONSHIP SYNTHESIS
# ============================================================================

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


async def relationship_synthesis_agent(state: CognitiveNexusState) -> Dict:
    """Agent 3: Infers relationships between extracted entities.

    This agent uses the entities from the previous step to identify
    relationships in the context. It validates that both subject and
    object entities exist before creating relationships.

    Returns:
        State updates with relationships and quality score
    """
    reasoning = []
    entities = state["extracted_entities"]

    if not entities:
        reasoning.append("→ No entities to relate, skipping relationship inference")
        return {
            "inferred_relationships": [],
            "relationship_quality": 0.0,
            "reasoning_steps": reasoning
        }

    # Agent selects strategy based on entity count
    entity_count = len(entities)
    if entity_count < 5:
        strategy = "exhaustive"
        reasoning.append(f"→ {entity_count} entities → EXHAUSTIVE pairing strategy")
    else:
        strategy = "selective"
        reasoning.append(f"→ {entity_count} entities → SELECTIVE inference strategy")

    # Format entities for prompt
    entities_json = json.dumps([
        {"name": e["name"], "type": e["type"]}
        for e in entities
    ], indent=2)

    # Call Qwen 2.5 via Ollama
    relationships = []
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

            # Parse JSON from response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]

            data = json.loads(response_text.strip())
            relationships = data.get("relationships", [])

            reasoning.append(f"→ Inferred {len(relationships)} relationships from LLM")

    except Exception as e:
        reasoning.append(f"→ Relationship inference failed: {str(e)}")
        relationships = []

    # Agent validates relationships (both entities must exist)
    entity_names = {e["name"] for e in entities}
    valid_relationships = []

    for rel in relationships:
        subject = rel.get("subject")
        object_name = rel.get("object")

        if subject in entity_names and object_name in entity_names:
            valid_relationships.append(rel)
        else:
            reasoning.append(f"  - Invalid: {subject} → {object_name} (entities not found)")

    # Calculate quality (% of valid relationships)
    quality = len(valid_relationships) / max(len(relationships), 1) if relationships else 0.0
    reasoning.append(f"→ Validated {len(valid_relationships)}/{len(relationships)} relationships")
    reasoning.append(f"→ Relationship quality: {quality:.2f}")

    return {
        "inferred_relationships": valid_relationships,
        "relationship_quality": quality,
        "reasoning_steps": reasoning
    }


# ============================================================================
# AGENT 4: TASK INTEGRATION (UNIFIED CONTEXT-TO-TASK SYSTEM)
# ============================================================================

TASK_INTEGRATION_PROMPT = """Analyze this conversation and determine how it should integrate with existing tasks.

**CONTEXT TO ANALYZE:**
{text}

**EXTRACTED ENTITIES:**
People: {people}
Projects: {projects}
Dates: {dates}

**EXISTING TASKS:**
{existing_tasks}

**YOUR JOB:**
For each piece of actionable content or context in the conversation, decide ONE operation:

1. **CREATE** - New task needed (actionable item not covered by existing tasks)
2. **UPDATE** - Updates existing task (new deadline, scope change, status update)
3. **COMMENT** - Adds context to existing task (progress update, discussion, clarification)
4. **ENRICH** - Just knowledge graph enrichment (no task action needed)

**DECISION CRITERIA:**
- CREATE if: Clear new action item not covered by existing tasks
- UPDATE if: Changes core task properties (deadline, assignee, description, status)
- COMMENT if: Related discussion/update but doesn't change task core
- ENRICH if: Just contextual information with no task implications

Output ONLY this JSON format:
{{
  "operations": [
    {{
      "operation": "CREATE",
      "task_id": null,
      "reasoning": "New action item: send prototypes to Andy by Friday",
      "data": {{
        "title": "Send prototypes to Andy",
        "assignee": "Jef Adriaenssens",
        "project": "Just Deals",
        "due_date": "2025-11-20",
        "priority": "high",
        "description": "Send design prototypes for review"
      }}
    }},
    {{
      "operation": "COMMENT",
      "task_id": "task-123",
      "reasoning": "Progress update on CRESCO data pipeline task",
      "data": {{
        "text": "Jef mentioned the API integration is 80% complete",
        "author": "Cognitive Nexus"
      }}
    }},
    {{
      "operation": "UPDATE",
      "task_id": "task-456",
      "reasoning": "Deadline moved from Nov 20 to Nov 26",
      "data": {{
        "due_date": "2025-11-26",
        "notes": "Deadline extended per meeting discussion"
      }}
    }},
    {{
      "operation": "ENRICH",
      "task_id": null,
      "reasoning": "General discussion about team structure, no task action needed",
      "data": {{}}
    }}
  ]
}}

**CRITICAL RULES:**
- If no actionable content: return ENRICH operation only
- Match task_id carefully based on project/person/topic
- Don't create duplicate tasks for same action
- Prefer COMMENT/UPDATE over CREATE when task exists
- Be conservative: when in doubt, use ENRICH

DO NOT include explanation outside JSON.
"""


def calculate_task_similarity(context_project: str, context_person: str, task: Dict) -> float:
    """Calculate similarity between context and existing task.

    Considers project name, assignee, and topic overlap.

    Returns:
        Similarity score 0.0-1.0
    """
    score = 0.0

    # Project match (40% weight)
    task_project = task.get("value_stream", "") or task.get("description", "")
    if context_project and context_project.lower() in task_project.lower():
        score += 0.4
    elif context_project and task.get("title", ""):
        # Check title for project mention
        if context_project.lower() in task["title"].lower():
            score += 0.2

    # Assignee match (30% weight)
    task_assignee = task.get("assignee", "")
    if context_person and context_person.lower() in task_assignee.lower():
        score += 0.3

    # Title/description keyword overlap (30% weight)
    # This would benefit from semantic similarity but keeping it simple for now
    context_keywords = set(context_project.lower().split() if context_project else [])
    task_keywords = set((task.get("title", "") + " " + task.get("description", "")).lower().split())
    if context_keywords and task_keywords:
        overlap = len(context_keywords & task_keywords) / max(len(context_keywords), 1)
        score += 0.3 * overlap

    return min(score, 1.0)


async def task_integration_agent(state: CognitiveNexusState) -> Dict:
    """Agent 4: Unified Task Integration Agent - Creates OR updates tasks intelligently.

    This is the critical agent that makes the system "living" - it doesn't just
    create tasks, it understands when to:
    - CREATE new tasks
    - UPDATE existing tasks with new information
    - ADD COMMENTS to existing tasks
    - Just ENRICH knowledge graph without task action

    The agent analyzes:
    1. Extracted entities (people, projects, dates)
    2. Existing tasks from database
    3. Relationships between entities
    4. Context implications

    Then decides the best operations to perform.

    Returns:
        State updates with task_operations and quality score
    """
    reasoning = []
    entities = state["extracted_entities"]
    relationships = state["inferred_relationships"]
    existing_tasks = state.get("existing_tasks", [])

    # Extract context elements
    people = [e["name"] for e in entities if e["type"] == "PERSON"]
    projects = [e["name"] for e in entities if e["type"] == "PROJECT"]
    dates = [e["name"] for e in entities if e["type"] == "DATE"]

    reasoning.append(f"→ Analyzing context: {len(people)} people, {len(projects)} projects, {len(dates)} dates")
    reasoning.append(f"→ Found {len(existing_tasks)} existing tasks to consider")

    # Build existing tasks summary for LLM
    existing_tasks_summary = ""
    if existing_tasks:
        task_summaries = []
        for task in existing_tasks[:10]:  # Limit to 10 most recent for context
            summary = f"ID:{task['id'][:8]} | {task['title']} | Assignee:{task.get('assignee', 'None')} | Project:{task.get('value_stream', 'None')}"
            task_summaries.append(summary)
        existing_tasks_summary = "\n".join(task_summaries)
        reasoning.append(f"→ Including {len(task_summaries)} recent tasks in analysis")
    else:
        existing_tasks_summary = "No existing tasks"
        reasoning.append("→ No existing tasks → any actionable items will be CREATE operations")

    # Call Qwen 2.5 for intelligent task integration
    operations = []
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5:7b-instruct",
                    "prompt": TASK_INTEGRATION_PROMPT.format(
                        text=state["raw_context"],
                        people=", ".join(people) if people else "None",
                        projects=", ".join(projects) if projects else "None",
                        dates=", ".join(dates) if dates else "None",
                        existing_tasks=existing_tasks_summary
                    ),
                    "stream": False,
                    "options": {"temperature": 0.3}  # Slightly higher for creative task matching
                }
            )

            result = response.json()
            response_text = result.get("response", "")

            # Parse JSON from response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]

            data = json.loads(response_text.strip())
            operations = data.get("operations", [])

            reasoning.append(f"→ LLM proposed {len(operations)} operations")

            # Log operation breakdown
            op_counts = {}
            for op in operations:
                op_type = op.get("operation", "UNKNOWN")
                op_counts[op_type] = op_counts.get(op_type, 0) + 1

            for op_type, count in op_counts.items():
                reasoning.append(f"  • {op_type}: {count}")

    except Exception as e:
        reasoning.append(f"→ Task integration failed: {str(e)}")
        operations = [{"operation": "ENRICH", "task_id": None, "reasoning": "Error in processing", "data": {}}]

    # Validate and enhance operations
    validated_operations = []
    for op in operations:
        operation_type = op.get("operation", "ENRICH")

        # Validate task_id exists if UPDATE or COMMENT
        if operation_type in ["UPDATE", "COMMENT"]:
            task_id = op.get("task_id")
            if task_id and not any(t["id"] == task_id for t in existing_tasks):
                reasoning.append(f"⚠ Task ID {task_id} not found, converting {operation_type} to ENRICH")
                operation_type = "ENRICH"
                op["operation"] = "ENRICH"
                op["reasoning"] = f"Task ID not found: {op.get('reasoning', '')}"

        validated_operations.append(op)

    # Calculate quality based on operation appropriateness
    create_count = sum(1 for op in validated_operations if op["operation"] == "CREATE")
    update_count = sum(1 for op in validated_operations if op["operation"] == "UPDATE")
    comment_count = sum(1 for op in validated_operations if op["operation"] == "COMMENT")
    enrich_count = sum(1 for op in validated_operations if op["operation"] == "ENRICH")

    # Quality: reward appropriate mix of operations
    # If all ENRICH with entities present -> low quality (missed opportunities)
    # If balanced operations -> high quality
    has_entities = len(people) + len(projects) > 0
    total_ops = len(validated_operations)

    if total_ops == 0:
        quality = 0.0
    elif has_entities and enrich_count == total_ops:
        quality = 0.3  # Low quality: missed task opportunities
    elif create_count + update_count + comment_count > 0:
        quality = min(0.7 + (0.3 * (create_count + update_count + comment_count) / total_ops), 1.0)
    else:
        quality = 0.5

    reasoning.append(f"→ Task integration quality: {quality:.2f}")

    return {
        "task_operations": validated_operations,
        "generated_tasks": [],  # Deprecated, kept for compatibility
        "task_quality": quality,
        "reasoning_steps": reasoning
    }


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def create_cognitive_nexus_graph():
    """Construct the LangGraph state machine for cognitive nexus.

    This creates a state graph with 4 agent nodes:
    1. Context Analysis Agent - decides strategy
    2. Entity Extraction Agent - extracts entities with retry logic
    3. Relationship Synthesis Agent - infers relationships
    4. Task Integration Agent - intelligently creates OR updates tasks

    The graph includes conditional routing for entity extraction retry loops.

    Returns:
        Compiled LangGraph state machine
    """
    workflow = StateGraph(CognitiveNexusState)

    # Add agent nodes
    workflow.add_node("analyze_context", context_analysis_agent)
    workflow.add_node("extract_entities", entity_extraction_agent)
    workflow.add_node("infer_relationships", relationship_synthesis_agent)
    workflow.add_node("integrate_tasks", task_integration_agent)

    # Define linear flow
    workflow.set_entry_point("analyze_context")
    workflow.add_edge("analyze_context", "extract_entities")

    # Conditional routing for entity extraction retry loop
    def should_retry_extraction(state: CognitiveNexusState) -> str:
        """Routing function: retry extraction if quality is low."""
        if state.get("needs_entity_retry", False):
            return "extract_entities"  # Loop back for retry
        return "infer_relationships"  # Continue to next agent

    workflow.add_conditional_edges(
        "extract_entities",
        should_retry_extraction,
        {
            "extract_entities": "extract_entities",  # Retry loop
            "infer_relationships": "infer_relationships"  # Next agent
        }
    )

    # Continue linear flow
    workflow.add_edge("infer_relationships", "integrate_tasks")
    workflow.add_edge("integrate_tasks", END)

    # Compile and return
    return workflow.compile()


# ============================================================================
# PUBLIC API
# ============================================================================

async def process_context(
    text: str,
    source_type: str = "manual",
    source_identifier: Optional[str] = None,
    existing_tasks: Optional[List[Dict]] = None
) -> Dict:
    """Process context through the cognitive nexus agent graph.

    This is the main entry point for the unified task management system.
    It creates the initial state, runs all agents through the graph, and
    returns the final state with entities, relationships, task operations,
    and reasoning.

    Args:
        text: The raw context to process
        source_type: Type of source ("slack", "transcript", "manual")
        source_identifier: Optional identifier for the source
        existing_tasks: List of existing tasks for smart integration

    Returns:
        Final state dictionary with:
        - extracted_entities: Entities found in context
        - inferred_relationships: Relationships between entities
        - task_operations: CREATE/UPDATE/COMMENT/ENRICH operations
        - reasoning_steps: Transparent agent decision-making
    """
    graph = create_cognitive_nexus_graph()

    initial_state = {
        "raw_context": text,
        "source_type": source_type,
        "source_identifier": source_identifier,
        "reasoning_steps": [],
        "entity_retry_count": 0,
        "max_retries": DEFAULT_MAX_RETRIES,
        # Initialize optional fields
        "extracted_entities": [],
        "inferred_relationships": [],
        "generated_tasks": [],  # Deprecated
        "existing_tasks": existing_tasks or [],  # NEW: For task integration
        "task_operations": [],  # NEW: Smart task operations
        "entity_quality": 0.0,
        "relationship_quality": 0.0,
        "task_quality": 0.0,
        "needs_entity_retry": False,
        "extraction_strategy": "",
        "context_complexity": 0.0,
        "estimated_entity_count": 0,
        "processing_start": datetime.now()
    }

    # Execute graph (runs all agents)
    final_state = await graph.ainvoke(initial_state)

    return final_state
