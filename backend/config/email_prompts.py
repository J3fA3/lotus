"""
Email Classification Prompts - Phase 5

Gemini-optimized prompts for email classification, action detection, and processing.

Uses structured output with Pydantic schemas for reliable parsing.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


# ==============================================================================
# Pydantic Output Schemas
# ==============================================================================


class EmailClassification(BaseModel):
    """Email classification result with confidence scoring."""

    is_actionable: bool = Field(
        description="True if email requires action from the user (task creation needed)"
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for this classification (0.0-1.0)"
    )

    action_type: str = Field(
        description="Type of action needed: 'task', 'meeting_prep', 'fyi', 'automated', 'unprocessed'"
    )

    urgency: str = Field(
        description="Urgency level: 'low', 'medium', 'high'"
    )

    reasoning: str = Field(
        description="Brief explanation of why email was classified this way"
    )

    detected_deadline: Optional[str] = Field(
        default=None,
        description="Detected deadline or due date (natural language or ISO format)"
    )

    detected_project: Optional[str] = Field(
        default=None,
        description="Detected project name (CRESCO, RF16, Just Deals, etc.)"
    )

    suggested_title: Optional[str] = Field(
        default=None,
        description="Suggested task title if creating a task"
    )

    key_action_items: List[str] = Field(
        default_factory=list,
        description="List of key action items extracted from email"
    )


# ==============================================================================
# Classification Prompt Templates
# ==============================================================================


EMAIL_CLASSIFICATION_SYSTEM_PROMPT = """You are an email classification assistant for Jef Adriaenssens.

**User Context (Jef):**
- **Name:** Jef Adriaenssens
- **Role:** Product Manager / Business Analyst
- **Projects:** CRESCO (main), RF16, Just Deals
- **Markets:** Spain, UK, Netherlands
- **Colleagues:** Alberto (Spain), Andy, Sarah (Product), Maran (auto-ignore)

**Your Task:**
Analyze emails and determine:
1. Is this email actionable? (requires a task)
2. What type of action? (task, meeting prep, FYI, automated)
3. How urgent is it?
4. What are the key action items?

**Classification Rules:**

**Actionable Emails (create task):**
- Direct requests: "Can you...", "Please review...", "Need you to..."
- Action verbs: review, send, share, update, prepare, create, fix
- Deadlines: "by Friday", "before tomorrow", "ASAP"
- Meeting prep: emails about upcoming meetings requiring preparation

**FYI Emails (no task):**
- Status updates: "Just letting you know..."
- Informational: newsletters, announcements, "FYI"
- Already completed: "This is done", "Completed yesterday"

**Automated Emails (no task):**
- System notifications: "no-reply@", automated reports
- Calendar notifications (unless prep needed)
- Automated workflows: build notifications, CI/CD

**Meeting Invites:**
- Classify as 'meeting_prep' if preparation needed
- Otherwise classify as 'fyi' (just attend)

**Urgency Scoring:**
- **High:** "ASAP", "urgent", "today", deadline <24h
- **Medium:** "this week", deadline 1-7 days, "when you can"
- **Low:** "eventually", "no rush", deadline >7 days

**Confidence Scoring:**
- **0.9-1.0:** Very clear action, explicit request
- **0.7-0.9:** Implied action, deadline present
- **0.5-0.7:** Possible action, needs context
- **0.0-0.5:** Unclear, FYI, or automated

**Project Detection:**
Match these exact names:
- CRESCO (most common)
- RF16
- Just Deals
- Co-op (related to CRESCO)

**Important:**
- Emails from "Maran" → always FYI (not relevant to Jef)
- Emails about Spain/Alberto → HIGH relevance (Jef's market)
- Newsletters/automated → confidence <0.3
- Thread responses → check if NEW action or just continuation
"""


def get_email_classification_prompt(
    email_subject: str,
    email_sender: str,
    email_body: str,
    email_snippet: str,
    action_phrases: List[str],
    is_meeting_invite: bool,
    thread_context: Optional[str] = None
) -> str:
    """Generate email classification prompt with email content.

    Args:
        email_subject: Email subject line
        email_sender: Sender name/email
        email_body: Full email body text
        email_snippet: Email snippet (preview)
        action_phrases: Detected action phrases
        is_meeting_invite: Whether email is a meeting invitation
        thread_context: Optional context from email thread

    Returns:
        Formatted prompt for Gemini
    """

    # Build thread context section
    thread_section = ""
    if thread_context:
        thread_section = f"""
**Thread Context:**
{thread_context}
"""

    # Build action phrases section
    action_section = ""
    if action_phrases:
        action_section = f"""
**Detected Action Phrases:**
{chr(10).join(f'- {phrase}' for phrase in action_phrases[:5])}
"""

    # Build meeting invite flag
    meeting_flag = ""
    if is_meeting_invite:
        meeting_flag = "**NOTE:** This email contains a meeting invitation."

    prompt = f"""Classify this email:

**From:** {email_sender}
**Subject:** {email_subject}

**Email Content:**
{email_body[:1500]}  <!-- Truncated to 1500 chars -->

**Snippet:** {email_snippet}
{action_section}{thread_section}{meeting_flag}

**Instructions:**
1. Determine if this email is actionable for Jef
2. Classify the action type
3. Assess urgency
4. Extract key action items and deadline
5. Provide confidence score

**Output Format:**
Return a JSON object matching the EmailClassification schema with:
- is_actionable (bool)
- confidence (float 0.0-1.0)
- action_type (str)
- urgency (str)
- reasoning (str)
- detected_deadline (str or null)
- detected_project (str or null)
- suggested_title (str or null)
- key_action_items (list of strings)

Be specific and concise. Focus on what Jef needs to DO, not just what the email says.
"""

    return prompt


# ==============================================================================
# Example Classifications for Prompt Engineering
# ==============================================================================


CLASSIFICATION_EXAMPLES = [
    {
        "email": {
            "from": "Alberto <alberto@spain.com>",
            "subject": "CRESCO - Pharmacy pinning position 3?",
            "body": "Hi Jef, can you check if we can pin position 3 for pharmacies in Spain? Need this by Friday for the launch. Thanks!"
        },
        "classification": {
            "is_actionable": True,
            "confidence": 0.92,
            "action_type": "task",
            "urgency": "high",
            "reasoning": "Direct request from Alberto (Spain market) with clear action and deadline",
            "detected_deadline": "Friday",
            "detected_project": "CRESCO",
            "suggested_title": "Check pharmacy pinning position 3 for Spain",
            "key_action_items": [
                "Check if position 3 can be pinned for pharmacies",
                "Apply to Spain market specifically",
                "Complete by Friday for launch"
            ]
        }
    },
    {
        "email": {
            "from": "Sarah Product <sarah@company.com>",
            "subject": "FYI: RF16 Specs Updated",
            "body": "Just letting you know I updated the RF16 specs in Confluence. No action needed, just keeping you in the loop."
        },
        "classification": {
            "is_actionable": False,
            "confidence": 0.85,
            "action_type": "fyi",
            "urgency": "low",
            "reasoning": "Explicitly states 'no action needed', pure informational update",
            "detected_deadline": None,
            "detected_project": "RF16",
            "suggested_title": None,
            "key_action_items": []
        }
    },
    {
        "email": {
            "from": "Calendar <calendar-notification@google.com>",
            "subject": "Invitation: CRESCO Weekly Sync @ Mon Nov 20, 2024 2pm",
            "body": "You have been invited to CRESCO Weekly Sync. When: Monday, November 20, 2024 2:00pm - 3:00pm. Join with Google Meet."
        },
        "classification": {
            "is_actionable": True,
            "confidence": 0.75,
            "action_type": "meeting_prep",
            "urgency": "medium",
            "reasoning": "Meeting invitation for CRESCO sync - may need prep tasks",
            "detected_deadline": "Monday, November 20, 2024 2:00pm",
            "detected_project": "CRESCO",
            "suggested_title": "Prepare for CRESCO Weekly Sync",
            "key_action_items": [
                "Review CRESCO updates before meeting",
                "Prepare status report"
            ]
        }
    },
    {
        "email": {
            "from": "GitHub <notifications@github.com>",
            "subject": "[repo/project] Build #1234 failed",
            "body": "Build #1234 failed on main branch. See details at..."
        },
        "classification": {
            "is_actionable": False,
            "confidence": 0.25,
            "action_type": "automated",
            "urgency": "low",
            "reasoning": "Automated build notification - not directly actionable by Jef",
            "detected_deadline": None,
            "detected_project": None,
            "suggested_title": None,
            "key_action_items": []
        }
    },
    {
        "email": {
            "from": "Maran <maran@company.com>",
            "subject": "Netherlands Market Update",
            "body": "Hey, quick update on Netherlands market metrics..."
        },
        "classification": {
            "is_actionable": False,
            "confidence": 0.15,
            "action_type": "fyi",
            "urgency": "low",
            "reasoning": "Email from Maran - auto-ignore per user preferences. Netherlands market updates not relevant to Jef's focus areas.",
            "detected_deadline": None,
            "detected_project": None,
            "suggested_title": None,
            "key_action_items": []
        }
    },
    {
        "email": {
            "from": "Andy <andy@company.com>",
            "subject": "Re: Just Deals Co-op deadline change",
            "body": "Following up on this - the Co-op team pushed the deadline to next Tuesday. Can you update the spec by Monday so we have time to review?"
        },
        "classification": {
            "is_actionable": True,
            "confidence": 0.88,
            "action_type": "task",
            "urgency": "high",
            "reasoning": "Clear action request with updated deadline in thread context",
            "detected_deadline": "Monday",
            "detected_project": "Just Deals",
            "suggested_title": "Update Just Deals spec for Co-op deadline",
            "key_action_items": [
                "Update spec document",
                "Complete by Monday for review",
                "Note: Final deadline is Tuesday (Co-op)"
            ]
        }
    }
]


# ==============================================================================
# Thread Consolidation Prompts
# ==============================================================================


def get_thread_consolidation_prompt(
    thread_emails: List[dict],
    thread_subject: str
) -> str:
    """Generate prompt for consolidating email thread into single action.

    Args:
        thread_emails: List of email dicts with subject, sender, body, date
        thread_subject: Thread subject line

    Returns:
        Prompt for thread consolidation
    """

    # Build email list
    email_list = []
    for i, email in enumerate(thread_emails, 1):
        email_list.append(f"""
**Email {i}:**
From: {email.get('sender', 'Unknown')}
Date: {email.get('date', 'Unknown')}
Body: {email.get('body', '')[:500]}
---
""")

    emails_text = "\n".join(email_list)

    prompt = f"""Consolidate this email thread into a single actionable task.

**Thread Subject:** {thread_subject}

**Thread has {len(thread_emails)} messages:**
{emails_text}

**Instructions:**
1. Read the entire thread to understand the conversation
2. Identify the FINAL action item that emerged (not intermediate discussion)
3. Extract the most recent deadline
4. Determine who needs to do what
5. Discard redundant/irrelevant messages

**Output:**
Provide a consolidated task description that captures:
- The final action Jef needs to take
- The latest deadline
- Key context from the thread
- Any important decisions made

Be concise but include critical details. Focus on what's needed NOW, not the back-and-forth.
"""

    return prompt
