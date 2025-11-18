"""
Orchestrator Agent - Phase 2 AI Assistant

This is the main orchestrator that coordinates all Phase 1 agents and adds
confidence-based decision-making for autonomous task management.

Flow:
1. Run Phase 1 Cognitive Nexus agents (context → entities → relationships → task operations)
2. Find related existing tasks (TaskMatcher)
3. Extract additional task fields (FieldExtractor)
4. Calculate confidence scores (ConfidenceScorer)
5. Decide action based on confidence:
   - >80%: Auto-create/enrich task
   - 50-80%: Propose task, ask user approval
   - <50%: Ask clarifying questions
6. Execute action or return proposal

This orchestrator preserves Phase 1 agents as-is and adds a coordination
layer on top for intelligent decision-making.
"""

from typing import TypedDict, List, Dict, Optional, Annotated
from langgraph.graph import StateGraph, END
import operator
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import json
import uuid

from agents.cognitive_nexus_graph import process_context
from agents.advanced_pdf_processor import AdvancedPDFProcessor
from services.confidence_scorer import ConfidenceScorer, ConfidenceScore
from services.task_matcher import TaskMatcher, TaskMatch, find_duplicate_tasks
from services.field_extractor import FieldExtractor
from services.assistant_db_operations import (
    create_tasks_from_proposals,
    enrich_existing_tasks,
    store_context_item,
    store_chat_message
)
from db.models import Task, ChatMessage, ContextItem, Entity, Relationship


# ============================================================================
# STATE DEFINITION
# ============================================================================

class OrchestratorState(TypedDict):
    """Typed state for orchestrator LangGraph.

    This state flows through all orchestrator nodes, building up context
    and decisions as it progresses through the pipeline.
    """
    # Input
    input_context: str
    source_type: str  # "slack", "transcript", "manual", "question", "pdf"
    source_identifier: Optional[str]
    pdf_bytes: Optional[bytes]  # For document uploads
    session_id: str  # Chat session ID
    user_id: Optional[str]

    # Phase 1 agent results
    entities: List[Dict]
    relationships: List[Dict]
    task_operations: List[Dict]  # CREATE/UPDATE/COMMENT/ENRICH operations
    context_complexity: float
    entity_quality: float
    relationship_quality: float
    task_quality: float
    reasoning_trace: Annotated[List[str], operator.add]  # Append-only

    # Task matching results
    existing_task_matches: List[TaskMatch]
    duplicate_task: Optional[TaskMatch]

    # Enriched task proposals
    proposed_tasks: List[Dict]  # Enriched with fields from FieldExtractor
    enrichment_operations: List[Dict]  # Operations to enrich existing tasks

    # Confidence scoring
    confidence_scores: List[ConfidenceScore]  # One per proposed task
    overall_confidence: float

    # Decision
    recommended_action: str  # 'auto', 'ask', 'clarify', 'store_only'
    needs_approval: bool
    clarifying_questions: List[str]

    # Execution results (if auto-approved)
    created_tasks: List[Dict]
    enriched_tasks: List[Dict]
    context_item_id: Optional[int]  # ID of stored ContextItem

    # Metadata
    processing_start: datetime
    processing_end: Optional[datetime]


# ============================================================================
# NODE 1: RUN PHASE 1 AGENTS
# ============================================================================

async def run_phase1_agents(state: OrchestratorState) -> Dict:
    """Node 1: Run Phase 1 Cognitive Nexus agents.

    This node calls the existing Phase 1 agent pipeline:
    - (Optional) PDF Processing - if document uploaded
    - Context Analysis Agent
    - Entity Extraction Agent
    - Relationship Synthesis Agent
    - Task Integration Agent

    Returns:
        State updates with entities, relationships, task operations, and quality metrics
    """
    reasoning = ["\n=== PHASE 1: Cognitive Nexus Agents ==="]

    # Process PDF if uploaded
    context_text = state["input_context"]
    if state.get("pdf_bytes") and state["source_type"] == "pdf":
        reasoning.append("→ Processing uploaded PDF document...")
        try:
            processed_doc = await AdvancedPDFProcessor.process_document(state["pdf_bytes"])
            # Extract text from processed document
            context_text = processed_doc.raw_text
            reasoning.append(f"→ Extracted {len(context_text)} characters from PDF")
            reasoning.append(f"→ Found {len(processed_doc.tables)} tables")
            reasoning.append(f"→ Document has {processed_doc.metadata.page_count} pages")

            # Add table data to context if present
            if processed_doc.tables:
                context_text += "\n\n### Tables Found:\n"
                for i, table in enumerate(processed_doc.tables[:3], 1):  # First 3 tables
                    context_text += f"\nTable {i}:\n{table.get('text', '')}\n"
        except Exception as e:
            reasoning.append(f"⚠ PDF processing failed: {str(e)}")
            reasoning.append("→ Falling back to input context")

    # Call Phase 1 agent graph
    # Note: We need to get existing tasks from database first
    db = state.get("db")  # Database session passed in initial state
    existing_tasks = []

    if db:
        # Get recent tasks for context
        tasks_query = select(Task).order_by(Task.created_at.desc()).limit(20)
        result = await db.execute(tasks_query)
        task_models = result.scalars().all()
        existing_tasks = [
            {
                "id": t.id,
                "title": t.title,
                "assignee": t.assignee,
                "value_stream": t.value_stream,
                "description": t.description,
                "status": t.status,
                "due_date": t.due_date
            }
            for t in task_models
        ]
        reasoning.append(f"→ Loaded {len(existing_tasks)} recent tasks for matching")

    # Run Phase 1 agents
    reasoning.append("→ Running Cognitive Nexus agent pipeline...")
    phase1_result = await process_context(
        text=context_text,
        source_type=state["source_type"],
        source_identifier=state.get("source_identifier"),
        existing_tasks=existing_tasks
    )

    reasoning.append(f"→ Extracted {len(phase1_result['extracted_entities'])} entities")
    reasoning.append(f"→ Inferred {len(phase1_result['inferred_relationships'])} relationships")
    reasoning.append(f"→ Generated {len(phase1_result['task_operations'])} task operations")

    # Extract quality metrics
    reasoning.extend([f"  Phase 1: {step}" for step in phase1_result.get("reasoning_steps", [])])

    return {
        "entities": phase1_result["extracted_entities"],
        "relationships": phase1_result["inferred_relationships"],
        "task_operations": phase1_result["task_operations"],
        "context_complexity": phase1_result.get("context_complexity", 0.0),
        "entity_quality": phase1_result.get("entity_quality", 0.0),
        "relationship_quality": phase1_result.get("relationship_quality", 0.0),
        "task_quality": phase1_result.get("task_quality", 0.0),
        "reasoning_trace": reasoning
    }


# ============================================================================
# NODE 2: FIND RELATED TASKS
# ============================================================================

async def find_related_tasks(state: OrchestratorState) -> Dict:
    """Node 2: Find related existing tasks via knowledge graph.

    Uses TaskMatcher to find tasks that share entities or relationships
    with the current context. This prevents duplicate creation and enables
    intelligent enrichment.

    Returns:
        State updates with existing_task_matches and duplicate_task
    """
    reasoning = ["\n=== TASK MATCHING ==="]

    db = state.get("db")
    if not db:
        reasoning.append("⚠ No database session, skipping task matching")
        return {"reasoning_trace": reasoning, "existing_task_matches": [], "duplicate_task": None}

    entities = state["entities"]
    relationships = state["relationships"]

    # Use TaskMatcher to find related tasks
    matcher = TaskMatcher(db)
    matches = await matcher.find_related_tasks(
        entities=entities,
        relationships=relationships,
        max_results=5,
        min_similarity=0.3
    )

    reasoning.append(f"→ Found {len(matches)} related tasks (similarity >= 30%)")
    for match in matches[:3]:  # Log top 3
        reasoning.append(
            f"  • {match.task['title'][:50]}... "
            f"(similarity: {match.similarity:.0%}, reason: {match.match_reason})"
        )

    # Check for potential duplicates (high-similarity matches)
    duplicate = None
    if matches and matches[0].similarity >= 0.7:
        duplicate = matches[0]
        reasoning.append(
            f"⚠ Potential duplicate detected: {duplicate.task['title']} "
            f"(similarity: {duplicate.similarity:.0%})"
        )

    return {
        "existing_task_matches": matches,
        "duplicate_task": duplicate,
        "reasoning_trace": reasoning
    }


# ============================================================================
# NODE 3: ENRICH TASK PROPOSALS
# ============================================================================

async def enrich_task_proposals(state: OrchestratorState) -> Dict:
    """Node 3: Enrich task proposals with extracted fields.

    Takes task operations from Phase 1 and enriches them with:
    - Extracted dates (FieldExtractor)
    - Extracted priorities (FieldExtractor)
    - Extracted tags/value_stream (FieldExtractor)
    - Assigned assignees (from PERSON entities)

    Returns:
        State updates with proposed_tasks (enriched) and enrichment_operations
    """
    reasoning = ["\n=== FIELD EXTRACTION & ENRICHMENT ==="]

    db = state.get("db")
    field_extractor = FieldExtractor(db=db)

    entities = state["entities"]
    relationships = state["relationships"]
    task_operations = state["task_operations"]
    context = state["input_context"]

    proposed_tasks = []
    enrichment_ops = []

    for operation in task_operations:
        op_type = operation.get("operation")
        op_data = operation.get("data", {})

        if op_type == "CREATE":
            # Extract fields for new task
            extracted_fields = await field_extractor.extract_fields(
                context=context,
                entities=entities,
                proposed_task=op_data
            )

            # Merge with operation data (operation data takes precedence)
            enriched_task = {
                "id": f"temp_{uuid.uuid4().hex[:8]}",  # Temporary ID
                "title": op_data.get("title", "Untitled Task"),
                "description": op_data.get("description", ""),
                "assignee": op_data.get("assignee") or extracted_fields.get("assignee") or "Unassigned",
                "due_date": op_data.get("due_date") or extracted_fields.get("due_date"),
                "priority": op_data.get("priority") or extracted_fields.get("priority") or "medium",
                "value_stream": op_data.get("project") or op_data.get("value_stream") or extracted_fields.get("value_stream"),
                "tags": extracted_fields.get("tags", []),
                "status": extracted_fields.get("status", "todo"),
                "operation": "CREATE",
                "reasoning": operation.get("reasoning", "")
            }

            proposed_tasks.append(enriched_task)
            reasoning.append(
                f"→ Enriched task: {enriched_task['title']} "
                f"(due: {enriched_task['due_date']}, priority: {enriched_task['priority']})"
            )

        elif op_type in ["UPDATE", "COMMENT", "ENRICH"]:
            # Create enrichment operation
            enrichment_ops.append({
                "operation": op_type,
                "task_id": operation.get("task_id"),
                "data": op_data,
                "reasoning": operation.get("reasoning", "")
            })
            reasoning.append(
                f"→ {op_type} operation for task {operation.get('task_id', 'unknown')}"
            )

    return {
        "proposed_tasks": proposed_tasks,
        "enrichment_operations": enrichment_ops,
        "reasoning_trace": reasoning
    }


# ============================================================================
# NODE 4: CALCULATE CONFIDENCE
# ============================================================================

async def calculate_confidence(state: OrchestratorState) -> Dict:
    """Node 4: Calculate confidence scores for each proposed task.

    Uses ConfidenceScorer to evaluate:
    - Entity quality
    - Knowledge graph matches
    - Clarity
    - Task field completeness

    Returns:
        State updates with confidence_scores, overall_confidence, and recommended_action
    """
    reasoning = ["\n=== CONFIDENCE SCORING ==="]

    scorer = ConfidenceScorer(high_threshold=80.0, low_threshold=50.0)

    entities = state["entities"]
    relationships = state["relationships"]
    existing_matches = state["existing_task_matches"]
    proposed_tasks = state["proposed_tasks"]
    enrichment_ops = state["enrichment_operations"]

    confidence_scores = []

    # Calculate confidence for each proposed task
    for task in proposed_tasks:
        score = scorer.calculate_confidence(
            entities=entities,
            relationships=relationships,
            existing_task_matches=existing_matches,
            context_complexity=state["context_complexity"],
            entity_quality=state["entity_quality"],
            relationship_quality=state["relationship_quality"],
            task_quality=state["task_quality"],
            proposed_task=task
        )

        confidence_scores.append(score)
        task["confidence"] = score.overall_score
        task["confidence_factors"] = score.factors

        reasoning.extend([f"  Task '{task['title']}': {step}" for step in score.reasoning])

    # Calculate overall confidence (average if multiple tasks)
    if confidence_scores:
        overall_confidence = sum(s.overall_score for s in confidence_scores) / len(confidence_scores)
    else:
        # No tasks proposed - just context storage
        overall_confidence = 50.0  # Neutral

    reasoning.append(f"→ Overall confidence: {overall_confidence:.1f}%")

    # Determine recommended action based on overall confidence
    if not proposed_tasks and not enrichment_ops:
        # No tasks - check if this is a question or just context
        if "?" in state["input_context"]:
            recommended_action = "answer_question"
            reasoning.append("→ Recommendation: ANSWER QUESTION (no tasks, contains '?')")
        else:
            recommended_action = "store_only"
            reasoning.append("→ Recommendation: STORE CONTEXT ONLY (no actionable tasks)")
    elif overall_confidence >= 80.0:
        recommended_action = "auto"
        reasoning.append("→ Recommendation: AUTO-APPROVE (high confidence)")
    elif overall_confidence >= 50.0:
        recommended_action = "ask"
        reasoning.append("→ Recommendation: ASK USER (medium confidence)")
    else:
        recommended_action = "clarify"
        reasoning.append("→ Recommendation: ASK CLARIFYING QUESTIONS (low confidence)")

    return {
        "confidence_scores": confidence_scores,
        "overall_confidence": overall_confidence,
        "recommended_action": recommended_action,
        "needs_approval": recommended_action in ["ask", "clarify"],
        "reasoning_trace": reasoning
    }


# ============================================================================
# NODE 5: GENERATE CLARIFYING QUESTIONS (if needed)
# ============================================================================

async def generate_clarifying_questions(state: OrchestratorState) -> Dict:
    """Node 5: Generate clarifying questions for low-confidence scenarios.

    Uses LLM to generate questions that will help improve confidence.

    Returns:
        State updates with clarifying_questions
    """
    reasoning = ["\n=== CLARIFYING QUESTIONS ==="]

    if state["recommended_action"] != "clarify":
        return {"clarifying_questions": [], "reasoning_trace": reasoning}

    # Build prompt for LLM
    entities = state["entities"]
    context = state["input_context"]

    entity_list = ", ".join([e.get("name", "") for e in entities])

    prompt = f"""The user provided unclear context. Generate 2-3 specific clarifying questions.

Context: {context}

Entities found: {entity_list}

What's unclear:
- Who should be assigned to tasks?
- When are deadlines?
- What are the specific action items?

Generate ONLY 2-3 questions in JSON format:
{{"questions": ["Who should be assigned to this task?", "When is this due?", "What is the specific deliverable?"]}}

DO NOT include explanation.
"""

    questions = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5:7b-instruct",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3}
                }
            )

            result = response.json()
            response_text = result.get("response", "")

            # Parse JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]

            data = json.loads(response_text.strip())
            questions = data.get("questions", [])

            reasoning.append(f"→ Generated {len(questions)} clarifying questions")

    except Exception as e:
        reasoning.append(f"⚠ Failed to generate questions: {str(e)}")
        # Fallback questions
        questions = [
            "Who should be assigned to this task?",
            "When should this be completed?",
            "What are the specific action items?"
        ]

    return {
        "clarifying_questions": questions,
        "reasoning_trace": reasoning
    }


# ============================================================================
# NODE 6: EXECUTE ACTIONS (if auto-approved)
# ============================================================================

async def execute_actions(state: OrchestratorState) -> Dict:
    """Node 6: Execute task creation/enrichment if auto-approved.

    This node persists tasks to the database and updates the knowledge graph.

    Returns:
        State updates with created_tasks, enriched_tasks, context_item_id
    """
    reasoning = ["\n=== EXECUTION ==="]

    db = state.get("db")
    if not db:
        reasoning.append("⚠ No database session, cannot execute")
        return {
            "created_tasks": [],
            "enriched_tasks": [],
            "context_item_id": None,
            "reasoning_trace": reasoning,
            "processing_end": datetime.now()
        }

    # ALWAYS store context item (for knowledge graph)
    context_item_id = await store_context_item(
        db=db,
        content=state["input_context"],
        source_type=state["source_type"],
        entities=state["entities"],
        relationships=state["relationships"],
        quality_metrics={
            "extraction_strategy": "fast",  # TODO: Get from Phase 1 results
            "context_complexity": state["context_complexity"],
            "entity_quality": state["entity_quality"],
            "relationship_quality": state["relationship_quality"],
            "task_quality": state["task_quality"]
        },
        reasoning_trace=state["reasoning_trace"],
        source_identifier=state.get("source_identifier")
    )
    reasoning.append(f"→ Stored context item (ID: {context_item_id})")

    created_tasks = []
    enriched_tasks = []

    # If auto-approved, create/enrich tasks
    if state["recommended_action"] == "auto":
        reasoning.append("→ AUTO-APPROVED: Creating/enriching tasks")

        # Create new tasks
        if state["proposed_tasks"]:
            created_tasks = await create_tasks_from_proposals(
                db=db,
                proposed_tasks=state["proposed_tasks"],
                context_item_id=context_item_id,
                auto_created=True
            )
            reasoning.append(f"→ Created {len(created_tasks)} tasks")

        # Enrich existing tasks
        if state["enrichment_operations"]:
            enriched_tasks = await enrich_existing_tasks(
                db=db,
                enrichment_operations=state["enrichment_operations"],
                context_item_id=context_item_id
            )
            reasoning.append(f"→ Enriched {len(enriched_tasks)} existing tasks")
    else:
        reasoning.append(f"→ Not auto-approved ({state['recommended_action']}), skipping task creation")

    return {
        "created_tasks": created_tasks,
        "enriched_tasks": enriched_tasks,
        "context_item_id": context_item_id,
        "reasoning_trace": reasoning,
        "processing_end": datetime.now()
    }


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def create_orchestrator_graph():
    """Construct the orchestrator LangGraph state machine.

    This creates a sequential pipeline:
    1. Run Phase 1 agents
    2. Find related tasks
    3. Enrich task proposals
    4. Calculate confidence
    5. Generate clarifying questions (conditional)
    6. Execute actions (conditional)

    Returns:
        Compiled LangGraph state machine
    """
    workflow = StateGraph(OrchestratorState)

    # Add nodes
    workflow.add_node("run_phase1", run_phase1_agents)
    workflow.add_node("find_tasks", find_related_tasks)
    workflow.add_node("enrich_proposals", enrich_task_proposals)
    workflow.add_node("calculate_confidence", calculate_confidence)
    workflow.add_node("generate_questions", generate_clarifying_questions)
    workflow.add_node("execute", execute_actions)

    # Define flow
    workflow.set_entry_point("run_phase1")
    workflow.add_edge("run_phase1", "find_tasks")
    workflow.add_edge("find_tasks", "enrich_proposals")
    workflow.add_edge("enrich_proposals", "calculate_confidence")
    workflow.add_edge("calculate_confidence", "generate_questions")
    workflow.add_edge("generate_questions", "execute")
    workflow.add_edge("execute", END)

    return workflow.compile()


# ============================================================================
# PUBLIC API
# ============================================================================

async def process_assistant_message(
    content: str,
    source_type: str,
    session_id: str,
    db: AsyncSession,
    source_identifier: Optional[str] = None,
    user_id: Optional[str] = None,
    pdf_bytes: Optional[bytes] = None
) -> Dict:
    """Process a message through the AI Assistant orchestrator.

    This is the main entry point for the Phase 2 AI Assistant (Lotus).

    Args:
        content: User message content
        source_type: Type of source ("slack", "transcript", "manual", "question", "pdf")
        session_id: Chat session ID
        db: Database session
        source_identifier: Optional source identifier
        user_id: Optional user ID
        pdf_bytes: Optional PDF document bytes for processing

    Returns:
        Final state dictionary with:
        - proposed_tasks: Tasks ready for approval/creation
        - enrichment_operations: Operations to enrich existing tasks
        - confidence_scores: Confidence for each task
        - recommended_action: 'auto', 'ask', 'clarify', 'store_only', 'answer_question'
        - clarifying_questions: Questions to ask user (if needed)
        - reasoning_trace: Full decision-making trace
        - created_tasks: Tasks created (if auto-approved)
    """
    graph = create_orchestrator_graph()

    initial_state = {
        "input_context": content,
        "source_type": source_type,
        "source_identifier": source_identifier,
        "pdf_bytes": pdf_bytes,
        "session_id": session_id,
        "user_id": user_id,
        "db": db,  # Pass database session through state
        "reasoning_trace": [],
        "processing_start": datetime.now(),
        # Initialize empty fields
        "entities": [],
        "relationships": [],
        "task_operations": [],
        "context_complexity": 0.0,
        "entity_quality": 0.0,
        "relationship_quality": 0.0,
        "task_quality": 0.0,
        "existing_task_matches": [],
        "duplicate_task": None,
        "proposed_tasks": [],
        "enrichment_operations": [],
        "confidence_scores": [],
        "overall_confidence": 0.0,
        "recommended_action": "",
        "needs_approval": False,
        "clarifying_questions": [],
        "created_tasks": [],
        "enriched_tasks": [],
        "context_item_id": None,
        "processing_end": None
    }

    # Execute graph
    final_state = await graph.ainvoke(initial_state)

    return final_state
