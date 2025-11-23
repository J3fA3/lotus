"""
Gemini Prompt Templates - Phase 3

Optimized prompts for Gemini 2.0 Flash to:
1. Improve output quality vs Qwen
2. Reduce latency through concise, focused prompts
3. Generate natural, human-like comments
4. Score task relevance accurately

Prompt Engineering Best Practices:
- Keep prompts under 500 tokens when possible
- Use structured output schemas
- Provide clear examples
- Avoid unnecessary verbosity
"""

from typing import Dict, List, Any


def get_relevance_scoring_prompt(
    task_title: str,
    task_description: str,
    context: str,
    user_profile: Dict[str, Any]
) -> str:
    """Generate prompt for relevance scoring.

    Scores 0-100: Is this task relevant for the user?

    Args:
        task_title: Proposed task title
        task_description: Proposed task description
        context: Original input context
        user_profile: User profile dict with name, role, projects, etc.

    Returns:
        Prompt string
    """
    return f"""You are an AI assistant helping {user_profile.get('name', 'the user')} manage their tasks.

USER PROFILE:
- Name: {user_profile.get('name', 'Unknown')}
- Role: {user_profile.get('role', 'Unknown')}
- Projects: {', '.join(user_profile.get('projects', []))}
- Markets: {', '.join(user_profile.get('markets', []))}

CONTEXT: {context}

PROPOSED TASK:
Title: {task_title}
Description: {task_description}

Score this task's relevance to {user_profile.get('name', 'the user')} (0-100):

SCORING RULES:
- 100: Directly mentions user's name or uses "I/me"
- 80-90: Relates to user's projects or responsibilities
- 60-70: Team task where user involvement is likely, OR message addressed to "everyone"/"you all" with action items
- 30-50: Generic team context, unclear if relevant
- 0-20: Explicitly for someone else or unrelated

IMPORTANT: If the context contains phrases like "everyone", "you all", "please prepare", "please review", or similar group-directed language with clear action items, score at least 60 (likely relevant to the user as part of the group).

Return JSON:
{{
  "score": 0-100,
  "is_for_user": true/false,
  "reasoning": "Brief explanation (1 sentence)"
}}"""


def get_task_enrichment_prompt(
    existing_task: Dict[str, Any],
    new_context: str,
    entities: List[Dict]
) -> str:
    """Generate prompt for task enrichment decision.

    Decides if an existing task should be updated based on new context.

    Args:
        existing_task: Existing task dict
        new_context: New context that might relate to the task
        entities: Entities extracted from new context

    Returns:
        Prompt string
    """
    entity_names = ', '.join([e.get('name', '') for e in entities])

    return f"""You are helping update existing tasks with new information.

EXISTING TASK:
Title: {existing_task.get('title', 'Unknown')}
Description: {existing_task.get('description', 'None')}
Due Date: {existing_task.get('due_date', 'Not set')}
Status: {existing_task.get('status', 'todo')}

NEW CONTEXT: {new_context}
ENTITIES IN CONTEXT: {entity_names}

Should this task be updated? If yes, what should change?

Return JSON:
{{
  "should_update": true/false,
  "confidence": 0-100,
  "changes": {{
    "due_date": "new date or null",
    "note_to_add": "text to add or null",
    "priority_change": "high/medium/low or null",
    "status_change": "todo/doing/done or null"
  }},
  "reasoning": "Why update (1-2 sentences)"
}}"""


def get_comment_generation_prompt(
    task: Dict[str, Any],
    context: str,
    decision_factors: Dict[str, Any],
    comment_type: str = "creation"
) -> str:
    """Generate prompt for natural language comment generation.

    Creates human-like comments explaining AI decisions.

    Args:
        task: Task dict
        context: Original context
        decision_factors: Dict with confidence, entities, matches, etc.
        comment_type: "creation" or "enrichment"

    Returns:
        Prompt string
    """
    if comment_type == "creation":
        return f"""You are Lotus, an AI assistant helping with task management.

CONTEXT: {context}

TASK CREATED:
Title: {task.get('title', 'Unknown')}
Assignee: {task.get('assignee', 'Unassigned')}
Due Date: {task.get('due_date', 'Not set')}
Project: {task.get('value_stream', 'None')}

Write a brief, natural comment (2-3 sentences) explaining:
1. WHO requested this or what triggered it
2. WHY you created this task
3. Any relevant context (people, markets, projects mentioned)

STYLE:
- Professional but conversational
- Like a helpful colleague
- DON'T mention: confidence scores, technical metrics
- DO mention: people's names, markets, projects

Example good comment:
"Alberto (Spain market) asked about pinning position 3 for pharmacies. This relates to your Spanish vertical work, so I've tagged it accordingly."

Generate comment:"""

    else:  # enrichment
        return f"""You are Lotus, an AI assistant helping with task management.

EXISTING TASK: {task.get('title', 'Unknown')}

NEW CONTEXT: {context}

CHANGES MADE:
{decision_factors.get('changes_summary', 'Updated task based on new information')}

Write a brief, natural comment (2-3 sentences) explaining:
1. WHAT new information came in
2. HOW the task was updated
3. WHY this update makes sense

STYLE: Professional but conversational, like a helpful colleague.

Example good comment:
"Updated deadline to Dec 3 based on Sarah's message. The Co-op presentation got moved, so I adjusted this accordingly."

Generate comment:"""


def get_request_classification_prompt(context: str) -> str:
    """Generate prompt for request classification.

    Classifies input as question, task_creation, or context_only.

    Args:
        context: User input

    Returns:
        Prompt string
    """
    return f"""Classify this user input into ONE category:

INPUT: {context}

CATEGORIES:
1. question - User asking a question that needs an answer (e.g., "What's my highest priority?", "Who is working on X?")
2. task_creation - User wants to create/update tasks (e.g., "Andy needs the dashboard by Friday", "Create task for...")
3. context_only - Just providing information to store (e.g., "FYI: meeting moved", "Note: project on hold")

Return JSON:
{{
  "classification": "question" | "task_creation" | "context_only",
  "confidence": 0-100,
  "reasoning": "Brief explanation (1 sentence)"
}}"""


def get_clarifying_questions_prompt(
    context: str,
    entities: List[Dict],
    confidence_factors: Dict[str, Any]
) -> str:
    """Generate prompt for clarifying questions.

    Used when confidence is low and AI needs more information.

    Args:
        context: User input
        entities: Extracted entities
        confidence_factors: Why confidence is low

    Returns:
        Prompt string
    """
    entity_list = ', '.join([e.get('name', '') for e in entities])

    return f"""The user provided unclear context. Generate 2-3 specific clarifying questions.

CONTEXT: {context}
ENTITIES FOUND: {entity_list}

LOW CONFIDENCE FACTORS:
{confidence_factors.get('issues', 'Missing key information')}

Generate questions to clarify:
- Who should be assigned?
- When is the deadline?
- What are the specific action items?

Return JSON:
{{
  "questions": [
    "Who should be assigned to this task?",
    "When is this due?",
    "What is the specific deliverable?"
  ]
}}"""


def get_answer_question_prompt(
    question: str,
    tasks: List[Dict[str, Any]]
) -> str:
    """Generate prompt for answering user questions about tasks.

    Args:
        question: User's question
        tasks: List of relevant tasks

    Returns:
        Prompt string
    """
    task_summaries = []
    for task in tasks[:20]:  # Limit to 20 tasks
        summary = f"- {task.get('title', 'Untitled')} (Status: {task.get('status', 'unknown')}, "
        summary += f"Assignee: {task.get('assignee', 'Unassigned')}"

        if task.get('due_date'):
            summary += f", Due: {task['due_date']}"
        if task.get('value_stream'):
            summary += f", Project: {task['value_stream']}"

        summary += ")"
        task_summaries.append(summary)

    task_context = '\n'.join(task_summaries) if task_summaries else "No tasks found."

    return f"""You are a helpful task management assistant. Answer the user's question based on their current tasks.

QUESTION: {question}

CURRENT TASKS:
{task_context}

Provide a clear, concise answer.

GUIDANCE:
- "highest priority": Look for tasks with high priority or urgent status
- "who's working on": Look at assignees
- "deadlines": Check due dates
- "what tasks": List relevant tasks

Answer:"""
