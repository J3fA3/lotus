"""
Task Synthesis Prompts - Phase 6 Stage 2

Production-ready prompts for contextual task synthesis with Gemini.

Prompt Design Principles:
1. Few-shot examples for calibration
2. Clear output format instructions
3. Confidence calibration guidelines
4. Edge case handling
5. Version control for prompt iteration

Versions:
- v1.0: Initial synthesis prompt with basic context
- v1.1: Added few-shot examples and confidence calibration
- v1.2: Enhanced edge case handling
"""

from typing import Dict, List, Optional
from models.intelligent_task import SimilarTaskMatch


# ============================================================================
# FEW-SHOT EXAMPLES
# ============================================================================

SYNTHESIS_EXAMPLES = """
**EXAMPLE 1: Clear, Detailed Input**

Input: "The Gmail OAuth token refresh is failing for 15 users. We need to fix the token refresh logic in the email polling service and add a retry mechanism. This is blocking our sales demo next week."

Context:
- Recent concepts: Gmail API, OAuth 2.0, Email Polling
- Active conversation: Discussion about Gmail integration bugs
- Similar task: "Fix Outlook OAuth refresh" (completed, quality=4.5)

Good Synthesis:
- Title: "Fix Gmail OAuth token refresh bug affecting 15 users"
- Summary (62 words): "Gmail service is failing to refresh OAuth tokens, causing authentication errors for 15+ users. The email polling service needs updated token refresh logic with retry mechanism. This is blocking production Gmail integration for new clients and a critical sales demo scheduled next week. Similar OAuth issues were successfully resolved for Outlook integration."
- Priority: P1_HIGH (confidence=0.9, source="urgency_keywords: 'blocking', 'sales demo next week', '15 users'")
- Effort: M_3HR (confidence=0.8, source="similar_tasks: Outlook OAuth fix took 2.5hr")
- Project: "Lotus Email Integration" (confidence=0.85, source="concepts: Gmail API mentioned frequently in this project")
- Why It Matters: "Gmail integration is a key selling point. Current failures prevent demos and affect sales pipeline."
- How to Approach: ["Update token refresh logic in email polling service", "Add retry mechanism with exponential backoff", "Test with affected user accounts", "Monitor OAuth flow for 24hr post-fix"]

---

**EXAMPLE 2: Vague Input (Needs Context Gaps)**

Input: "improve the dashboard"

Context:
- Recent concepts: Analytics Dashboard, User Experience
- No active conversations
- No similar tasks

Good Synthesis:
- Title: "Improve dashboard performance and usability"
- Summary (51 words): "The dashboard needs improvements, but specific areas and success criteria are not yet defined. This could involve performance optimization, UI/UX enhancements, or feature additions. More context is needed to determine scope, priority, and approach."
- Priority: None (confidence=0.2 → generate ContextGap)
- Effort: None (confidence=0.1 → generate ContextGap)
- Project: "Analytics Dashboard" (confidence=0.6, source="concepts: Analytics Dashboard mentioned")
- Context Gaps:
  - "What specific aspects of the dashboard need improvement? (performance, UI, features, etc.)"
  - "What problem are users experiencing with the current dashboard?"
  - "What would success look like for this improvement?"
  - "How urgent is this - is it blocking anything?"

---

**EXAMPLE 3: Complex, Multi-Part Input**

Input: "We need to migrate the user authentication system from JWT to OAuth 2.0, update all client apps, and ensure backward compatibility during the transition. Several teams are waiting on this, and we have security audit next month."

Context:
- Recent concepts: OAuth 2.0, JWT, Authentication, Security Audit
- Active conversation: Discussion about security improvements
- Similar tasks: "Migrate payment system to new provider" (completed, quality=3.8, lessons="Plan backward compatibility carefully, communicate migration timeline clearly")

Good Synthesis:
- Title: "Migrate authentication from JWT to OAuth 2.0 with backward compatibility"
- Summary (68 words): "Complete migration of user authentication system from JWT tokens to OAuth 2.0 protocol. This involves updating server-side authentication logic, migrating all client applications (web, mobile, API), and maintaining backward compatibility during transition. Multiple teams depend on this, and security audit next month requires modern auth standards. Previous migration experience suggests careful planning for backward compatibility and clear communication."
- Priority: P1_HIGH (confidence=0.9, source="urgency: 'security audit next month', 'teams waiting'")
- Effort: XXL_1WEEK_PLUS (confidence=0.9, source="scope: multiple components, backward compatibility, similar migration took 1.5 weeks")
- Project: "Security Infrastructure" (confidence=0.8, source="concepts: Authentication, Security Audit")
- Why It Matters: "Security audit compliance requires modern auth standards. Multiple teams are blocked waiting for this migration."
- How to Approach:
  - "Phase 1: Implement OAuth 2.0 server-side with JWT fallback"
  - "Phase 2: Update client apps one by one (test thoroughly)"
  - "Phase 3: Monitor dual-auth period (2 weeks)"
  - "Phase 4: Deprecate JWT, switch to OAuth-only"
  - "Lessons from similar migration: Plan backward compatibility, communicate timeline clearly"
- Stakeholders:
  - Frontend Team (blocked on migration for new features)
  - Mobile Team (needs to update mobile apps)
  - Security Team (audit compliance)
"""


# ============================================================================
# SYNTHESIS PROMPT TEMPLATES
# ============================================================================

def build_synthesis_prompt_v1_2(
    raw_input: str,
    context: Dict,
    similar_tasks: List[SimilarTaskMatch]
) -> str:
    """
    Build task synthesis prompt (version 1.2).

    Enhanced with:
    - Few-shot examples for calibration
    - Confidence scoring guidelines
    - Edge case handling
    - Clear output format

    Args:
        raw_input: User's raw input
        context: KG context (concepts, conversations, outcomes)
        similar_tasks: Pre-computed similar tasks

    Returns:
        Complete synthesis prompt
    """

    # Build context sections
    concept_context = _build_concept_context(context.get("top_concepts", []))
    conversation_context = _build_conversation_context(context.get("active_conversations", []))
    outcome_context = _build_outcome_context(context.get("successful_outcomes", []))
    similar_context = _build_similar_tasks_context(similar_tasks)

    prompt = f"""You are an expert task synthesizer for the Lotus task management system. Your job is to transform raw user input into rich, intelligent task descriptions that help users work more effectively.

# ROLE AND OBJECTIVE

Transform the user's raw input into an IntelligentTaskDescription with:
1. Clear, actionable title and summary
2. Auto-filled fields (priority, effort, project, assignee) with confidence tracking
3. Rich expandable sections (why it matters, how to approach, related work)
4. Context gaps for missing critical information

Your synthesis should be **concise but informative** - avoid generic statements, provide specific, actionable guidance.

---

# AVAILABLE CONTEXT

## Strategic Concepts (from Knowledge Graph)
{concept_context}

## Recent Conversations
{conversation_context}

## Lessons from Recent Successes
{outcome_context}

## Similar Past Tasks
{similar_context}

---

# USER INPUT

{raw_input}

---

# FEW-SHOT EXAMPLES

{SYNTHESIS_EXAMPLES}

---

# OUTPUT FORMAT

Return a TaskSynthesisResult with:

## 1. task_description (IntelligentTaskDescription)

### Tier 1: Always Visible

**title** (string, 5-200 chars):
- Clear and actionable
- Specific outcome or deliverable
- Example: "Fix Gmail OAuth token refresh bug" ✅
- Avoid: "Gmail issue" ❌

**summary** (string, 50-75 words TARGET, 50-150 max):
- WHAT needs to be done (specific)
- WHY it matters (user/business impact)
- WHO it affects (if known)
- CRITICAL: Must be 50+ words minimum, target 50-75 words
- Count your words carefully!

**Auto-fillable fields** (with confidence tracking):

- **priority** (PriorityLevel enum or null):
  - P0_CRITICAL: System down, data loss, security breach
  - P1_HIGH: Blocking users, blocking sales, urgent deadline
  - P2_MEDIUM: Important but not urgent
  - P3_LOW: Nice to have
  - Set to null if confidence < 0.8

- **effort_estimate** (EffortEstimate enum or null):
  - XS_15MIN: Trivial change
  - S_1HR: Simple fix or feature
  - M_3HR: Moderate complexity
  - L_1DAY: Complex feature or refactor
  - XL_3DAYS: Large feature or migration
  - XXL_1WEEK_PLUS: Major project
  - Set to null if confidence < 0.75

- **primary_project** (string or null):
  - Infer from concepts with related_projects
  - Set to null if confidence < 0.7

- **related_markets** (List[string]):
  - Infer from concepts with related_markets
  - Can be empty list

- **suggested_assignee** (string or null):
  - Infer from skill requirements (backend-team, frontend-team, etc.)
  - Set to null if confidence < 0.6

### Tier 2: Expandable Sections

**why_it_matters** (WhyItMattersSection or null):
- business_value: Why this matters to business/user (specific, not generic)
- user_impact: Who benefits and how
- urgency_reason: Why time-sensitive (if applicable)
- related_concepts: Strategic concepts from KG

**what_was_discussed** (WhatWasDiscussedSection or null):
- key_decisions: Major decisions made in conversation
- open_questions: Unresolved questions
- conversation_thread_id: Link to KG conversation (if available)
- Only populate if input came from conversation

**how_to_approach** (HowToApproachSection):
- focus_areas: 2-4 specific, actionable items (REQUIRED, min 1 item)
- potential_blockers: Known obstacles
- success_criteria: What "done" looks like
- lessons_from_similar: Lessons from similar tasks (if available)
- Make focus areas SPECIFIC, not generic

**related_work** (RelatedWorkSection or null):
- similar_tasks: Similar tasks with explanations
- blocking_tasks: Tasks blocking this one
- stakeholders: People/teams affected

### Metadata

**context_gaps** (List[ContextGap]):
- Generate for any field with confidence < threshold
- field_name: Which field needs clarification
- question: Specific, actionable question
- importance: HIGH/MEDIUM/LOW
- suggested_answer: Your best guess (if any)
- confidence: Your confidence in suggestion (0.0-1.0)

**auto_fill_metadata** (List[AutoFillMetadata]):
- For EVERY auto-filled field, provide:
  - field_name: Which field
  - confidence: 0.0-1.0 (be honest!)
  - confidence_tier: HIGH (>0.8), MEDIUM (0.6-0.8), LOW (<0.6)
  - source: Where you got this (urgency_keywords, concepts, similar_tasks, etc.)
  - auto_filled: true if you filled it, false if you generated context gap
  - reasoning: Brief explanation

## 2. synthesis_reasoning (string)

Explain your synthesis process:
- How you interpreted the input
- What context you leveraged
- Why you made certain inferences
- What assumptions you made
- Be concise (2-3 sentences)

## 3. confidence_overall (float, 0.0-1.0)

Your overall confidence in the synthesis:
- 0.9-1.0: Input was clear, rich context, high confidence
- 0.7-0.9: Good input, some context, confident
- 0.5-0.7: Decent input, limited context, moderate confidence
- 0.3-0.5: Vague input, missing context, low confidence
- 0.0-0.3: Very vague input, no context, mostly gaps

---

# CONFIDENCE CALIBRATION GUIDELINES

**Be conservative with confidence scores:**

- **Priority confidence:**
  - 0.9-1.0: Explicit urgency ("ASAP", "critical", "blocking X users")
  - 0.7-0.9: Strong urgency signals ("important", "should prioritize")
  - 0.5-0.7: Mild urgency signals ("when you get a chance")
  - <0.5: No urgency signals

- **Effort confidence:**
  - 0.9-1.0: Very similar task exists with outcome data
  - 0.7-0.9: Similar task exists, similar scope
  - 0.5-0.7: Similar domain, different scope
  - <0.5: No similar tasks, guessing from keywords

- **Project confidence:**
  - 0.9-1.0: Concept explicitly tied to project
  - 0.7-0.9: Concept frequently mentioned in project context
  - 0.5-0.7: Concept loosely related to project
  - <0.5: Guessing from keywords

**When in doubt, generate a context gap instead of auto-filling!**

---

# EDGE CASE HANDLING

**Very Short Input (1-5 words):**
- Create basic summary by expanding on input
- Generate context gaps for ALL auto-fillable fields
- Set confidence_overall < 0.3
- Example: "fix bug" → Summary: "A bug needs to be fixed, but specific details about which component, what the bug is, and why it needs fixing are needed."

**Very Long Input (>500 words):**
- Extract key points for summary (still 50-75 words!)
- Use rich context to populate all expandable sections
- Higher confidence (0.7-0.9)
- Create how_to_approach with clear focus areas

**Vague Input ("improve X", "look into Y"):**
- Acknowledge vagueness in summary
- Generate HIGH importance context gaps for details
- Set confidence_overall < 0.5
- Example: "improve dashboard" → Multiple gaps about what, why, who, when

**Multiple Tasks in One Input:**
- Synthesize for the PRIMARY task mentioned first
- Add other tasks as related_work or blockers
- Note in synthesis_reasoning that input contained multiple tasks

---

# CRITICAL REQUIREMENTS

1. **Summary MUST be 50+ words** (minimum, strict)
2. **Summary should be 50-75 words** (target)
3. **how_to_approach.focus_areas REQUIRED** (min 1 item, max 5)
4. **Be specific, not generic** ("reduce API latency from 500ms to 100ms" vs "improve performance")
5. **Generate context gaps for low-confidence fields** (better to ask than guess wrong)
6. **Track confidence for EVERY auto-filled field**
7. **Leverage context when available** (concepts, conversations, similar tasks)

---

# NOW SYNTHESIZE THE TASK

Return a complete TaskSynthesisResult based on the user input and context above.
Remember: Be honest about confidence, generate gaps when uncertain, be specific not generic.
"""

    return prompt


# ============================================================================
# CONTEXT BUILDERS
# ============================================================================

def _build_concept_context(concepts: List[Dict]) -> str:
    """Build concept context section."""
    if not concepts:
        return "*No strategic concepts available*"

    lines = []
    for c in concepts:
        lines.append(f"- **{c['name']}** ({c['tier']}, importance={c['importance']:.2f})")
        if c.get('projects'):
            lines.append(f"  - Projects: {', '.join(c['projects'])}")
        if c.get('markets'):
            lines.append(f"  - Markets: {', '.join(c['markets'])}")

    return "\n".join(lines)


def _build_conversation_context(conversations: List[Dict]) -> str:
    """Build conversation context section."""
    if not conversations:
        return "*No recent conversations*"

    lines = []
    for conv in conversations:
        lines.append(f"- {conv['summary']}")
        if conv.get('decisions'):
            lines.append(f"  - Decisions: {'; '.join(conv['decisions'])}")
        if conv.get('open_questions'):
            lines.append(f"  - Open Questions: {'; '.join(conv['open_questions'])}")

    return "\n".join(lines)


def _build_outcome_context(outcomes: List[Dict]) -> str:
    """Build outcome context section."""
    if not outcomes:
        return "*No recent successful outcomes with lessons*"

    lines = []
    for outcome in outcomes:
        if outcome.get('lessons'):
            lines.append(f"- {outcome['lessons']} (quality={outcome['quality']:.1f}/5.0)")

    return "\n".join(lines) if lines else "*No recent successful outcomes with lessons*"


def _build_similar_tasks_context(similar_tasks: List[SimilarTaskMatch]) -> str:
    """Build similar tasks context section."""
    if not similar_tasks:
        return "*No similar tasks found*"

    lines = []
    for task in similar_tasks:
        lines.append(f"- **{task.task_title}** (similarity={task.similarity_score:.2f})")
        lines.append(f"  - {task.explanation}")
        if task.outcome:
            lines.append(f"  - Outcome: {task.outcome} (quality={task.completion_quality:.1f}/5.0)")

    return "\n".join(lines)


# ============================================================================
# PROMPT VERSIONING
# ============================================================================

PROMPT_VERSIONS = {
    "v1.0": "Initial basic synthesis prompt",
    "v1.1": "Added few-shot examples and confidence calibration",
    "v1.2": "Enhanced edge case handling, stricter confidence thresholds",
}

CURRENT_VERSION = "v1.2"


def get_synthesis_prompt(
    raw_input: str,
    context: Dict,
    similar_tasks: List[SimilarTaskMatch],
    version: str = CURRENT_VERSION
) -> str:
    """
    Get synthesis prompt by version.

    Args:
        raw_input: User's raw input
        context: KG context
        similar_tasks: Similar tasks
        version: Prompt version (default: current)

    Returns:
        Synthesis prompt string
    """
    if version == "v1.2" or version == CURRENT_VERSION:
        return build_synthesis_prompt_v1_2(raw_input, context, similar_tasks)
    else:
        raise ValueError(f"Unknown prompt version: {version}")
