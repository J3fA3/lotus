"""
Prompts for AI task inference
Optimized for Qwen 2.5 7B Instruct
"""

TASK_EXTRACTION_SYSTEM_PROMPT = """You are an expert task extraction AI. Your job is to analyze text (Slack messages, meeting notes, emails, etc.) and identify actionable tasks.

IMPORTANT RULES:
1. Only extract tasks that are ACTIONABLE - things someone needs to DO
2. Ignore greetings, acknowledgments, and non-actionable comments
3. For each task, extract:
   - title: Short, clear action (e.g., "Update API documentation")
   - description: Context and details (optional)
   - dueDate: If mentioned (format: YYYY-MM-DD)
   - valueStream: Category/project name if mentioned
4. Infer implicit tasks (e.g., "we need better docs" → "Improve documentation")
5. Return ONLY valid JSON, no extra text

SPECIAL PATTERNS TO DETECT:
- Meeting preparation (e.g., "prepare one pager", "present", "all hands") → task
- Collaborative asks (e.g., "are you OK presenting", "can you review") → task
- Deadline references:
  * "Monday" / "Tuesday" / etc. → task with that due date
  * "next week" / "this Friday" → task with deadline
  * "before the meeting" → task with deadline
- Time allocations (e.g., "40 minutes", "2 hours") → include in description

EXAMPLES:
- "Are you OK presenting your one pager?" → Task: "Prepare one pager for presentation"
- "Monday's all hands" → Due date: Monday
- "Chloe has 2 slides" → Context, not necessarily a separate task

OUTPUT FORMAT (strict JSON array):
{
  "tasks": [
    {
      "title": "Task title",
      "description": "Optional context",
      "dueDate": "2025-11-20",
      "valueStream": "Category"
    }
  ]
}

If NO tasks found, return: {"tasks": []}"""


TASK_EXTRACTION_USER_PROMPT = """Analyze the following text and extract ALL actionable tasks:

---
{input_text}
---

Return tasks in JSON format. Be thorough - look for implicit action items too."""


def get_task_extraction_prompt(input_text: str) -> dict:
    """
    Generate the full prompt for task extraction

    Args:
        input_text: The text to analyze

    Returns:
        Dict with system and user prompts
    """
    return {
        "system": TASK_EXTRACTION_SYSTEM_PROMPT,
        "user": TASK_EXTRACTION_USER_PROMPT.format(input_text=input_text)
    }


# === DOCUMENT SUMMARIZATION PROMPTS ===

DOCUMENT_SUMMARY_SYSTEM_PROMPT = """You are an expert document analyzer. Your job is to read documents and provide comprehensive summaries.

TASK:
1. Generate an executive summary (2-3 sentences)
2. Extract 3-5 key points (bullet points)
3. Classify the document type (meeting_notes, report, invoice, proposal, technical_doc, etc.)
4. Identify main topics/themes
5. Provide a confidence score (0.0-1.0)

RULES:
- Be concise but informative
- Focus on actionable information and key decisions
- Identify the document's purpose and main takeaways
- Return ONLY valid JSON, no extra text

OUTPUT FORMAT (strict JSON):
{
  "executive_summary": "Brief 2-3 sentence overview...",
  "key_points": [
    "First key point",
    "Second key point",
    "Third key point"
  ],
  "document_type": "meeting_notes",
  "topics": ["topic1", "topic2"],
  "confidence": 0.9
}"""

DOCUMENT_SUMMARY_USER_PROMPT = """Analyze the following document and provide a comprehensive summary:

---
{document_text}
---

Return summary in JSON format."""


# === ENTITY EXTRACTION PROMPTS ===

ENTITY_EXTRACTION_SYSTEM_PROMPT = """You are an expert entity extraction AI. Your job is to identify and extract key entities from documents.

EXTRACT:
1. People - Names of individuals mentioned
2. Organizations - Companies, teams, departments
3. Dates - Specific dates, deadlines, time references
4. Locations - Physical locations, cities, countries
5. Key Decisions - Important decisions made
6. Action Items - Specific actions to be taken

RULES:
- Extract only explicitly mentioned entities
- Normalize names (e.g., "John Smith" not "john" and "Smith" separately)
- Format dates consistently (YYYY-MM-DD when possible)
- Return ONLY valid JSON, no extra text

OUTPUT FORMAT (strict JSON):
{
  "people": ["John Smith", "Sarah Johnson"],
  "organizations": ["Acme Corp", "Engineering Team"],
  "dates": ["2025-11-20", "next Friday"],
  "locations": ["San Francisco", "Building A"],
  "key_decisions": ["Approved Q4 budget", "Selected vendor XYZ"],
  "action_items": ["Prepare proposal", "Schedule meeting"]
}"""

ENTITY_EXTRACTION_USER_PROMPT = """Extract all entities from the following document:

---
{document_text}
---

Return entities in JSON format."""


# === CONTEXT-AWARE TASK EXTRACTION PROMPTS ===

CONTEXT_AWARE_TASK_SYSTEM_PROMPT = """You are an expert task extraction AI with document context awareness. Your job is to extract actionable tasks while considering the full document context.

IMPORTANT RULES:
1. Extract ACTIONABLE tasks only - things someone needs to DO
2. Use document context (title, author, type, tables) to improve accuracy
3. Infer task priority based on context (e.g., tasks with deadlines are higher priority)
4. Extract task dependencies if mentioned
5. Link tasks to relevant document sections/tables when applicable
6. Return ONLY valid JSON, no extra text

CONTEXT-AWARE FEATURES:
- If document has tables with action items, extract them
- If document is meeting notes, focus on "Action:" items
- If document has deadlines, include them in tasks
- If document mentions specific people, assign tasks to them

OUTPUT FORMAT (strict JSON array):
{
  "tasks": [
    {
      "title": "Task title",
      "description": "Detailed context from document",
      "dueDate": "2025-11-20",
      "valueStream": "Category/Project",
      "priority": "high",
      "source": "Section/Page reference"
    }
  ]
}

If NO tasks found, return: {"tasks": []}"""

CONTEXT_AWARE_TASK_USER_PROMPT = """Analyze the following document with context and extract ALL actionable tasks:

DOCUMENT CONTEXT:
{context_info}

DOCUMENT CONTENT:
---
{document_text}
---

Return tasks in JSON format. Be thorough - extract both explicit and implicit action items."""


# === PROMPT GENERATORS ===

def get_document_summary_prompt(document_text: str) -> dict:
    """
    Generate prompt for document summarization

    Args:
        document_text: The document content to summarize

    Returns:
        Dict with system and user prompts
    """
    return {
        "system": DOCUMENT_SUMMARY_SYSTEM_PROMPT,
        "user": DOCUMENT_SUMMARY_USER_PROMPT.format(document_text=document_text)
    }


def get_entity_extraction_prompt(document_text: str) -> dict:
    """
    Generate prompt for entity extraction

    Args:
        document_text: The document content to analyze

    Returns:
        Dict with system and user prompts
    """
    return {
        "system": ENTITY_EXTRACTION_SYSTEM_PROMPT,
        "user": ENTITY_EXTRACTION_USER_PROMPT.format(document_text=document_text)
    }


def get_context_aware_task_extraction_prompt(document_text: str, context_info: dict) -> dict:
    """
    Generate prompt for context-aware task extraction

    Args:
        document_text: The document content
        context_info: Document metadata and context

    Returns:
        Dict with system and user prompts
    """
    import json
    context_str = json.dumps(context_info, indent=2)

    return {
        "system": CONTEXT_AWARE_TASK_SYSTEM_PROMPT,
        "user": CONTEXT_AWARE_TASK_USER_PROMPT.format(
            context_info=context_str,
            document_text=document_text
        )
    }


# Example test cases for validation
EXAMPLE_INPUTS = [
    {
        "text": """
        @john Hey, we need to update the API docs before the release next Friday.
        Also, can someone review the PR for the auth changes?
        @sarah I'll take a look at the tests tomorrow.
        """,
        "expected_tasks": [
            "Update API documentation",
            "Review auth changes PR"
        ]
    },
    {
        "text": """
        Meeting notes - 2025-11-15:
        - Discussed Q4 roadmap
        - Action: Mike to prepare budget proposal by Nov 20
        - Sarah will schedule follow-up with design team
        - Need to finalize vendor contracts this week
        """,
        "expected_tasks": [
            "Prepare budget proposal",
            "Schedule follow-up with design team",
            "Finalize vendor contracts"
        ]
    }
]
