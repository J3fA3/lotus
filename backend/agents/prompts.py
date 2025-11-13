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
