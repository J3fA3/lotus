"""
PR-Style Comment Generator - Phase 6 Stage 3

Generates human-readable explanations of task changes (like GitHub PR comments).

Design Decisions:
1. Hybrid approach: Templates for simple changes, Gemini for complex
2. Synchronous generation (part of version creation transaction)
3. Context-aware (includes why change matters, not just what changed)

Simple changes (template-based, instant):
- Status changes: "Task moved from 'todo' to 'doing'"
- Priority changes: "Priority increased from P2 to P1"
- Single field changes: "Assignee changed from Alice to Bob"

Complex changes (Gemini-based, context-aware):
- Description edits: Understand what was added/removed and why
- Multiple field changes: Explain the relationship between changes
- AI overrides: Explain user's reasoning vs AI suggestion
"""

import logging
from typing import Dict, List, Optional
from agents.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)


# ============================================================================
# TEMPLATES FOR SIMPLE CHANGES
# ============================================================================

STATUS_CHANGE_TEMPLATES = {
    ("todo", "doing"): "🚀 **Started work** - Task moved from backlog to active development",
    ("doing", "done"): "✅ **Completed** - Task finished and ready for review",
    ("todo", "done"): "⚡ **Quick completion** - Task completed without going through 'doing' state",
    ("doing", "todo"): "⏸️ **Paused** - Task moved back to backlog (may need reprioritization)",
    ("done", "doing"): "🔄 **Reopened** - Task reopened for additional work",
}

PRIORITY_CHANGE_TEMPLATES = {
    ("P3_LOW", "P2_MEDIUM"): "📈 **Priority increased** to Medium",
    ("P3_LOW", "P1_HIGH"): "⚠️ **Priority increased** to High",
    ("P3_LOW", "P0_CRITICAL"): "🚨 **Priority escalated** to Critical",
    ("P2_MEDIUM", "P1_HIGH"): "⚠️ **Priority increased** to High",
    ("P2_MEDIUM", "P0_CRITICAL"): "🚨 **Priority escalated** to Critical",
    ("P1_HIGH", "P0_CRITICAL"): "🚨 **Priority escalated** to Critical",
    ("P0_CRITICAL", "P1_HIGH"): "📉 **Priority lowered** to High",
    ("P1_HIGH", "P2_MEDIUM"): "📉 **Priority lowered** to Medium",
    ("P2_MEDIUM", "P3_LOW"): "📉 **Priority lowered** to Low",
}

EFFORT_CHANGE_TEMPLATES = {
    "increase": "📊 **Effort estimate increased** - Task is more complex than initially thought",
    "decrease": "⚡ **Effort estimate decreased** - Task is simpler than expected",
}


# ============================================================================
# PR COMMENT GENERATOR
# ============================================================================

class PRCommentGenerator:
    """
    Generates PR-style comments for task changes.

    Uses hybrid approach: templates for simple, Gemini for complex.
    """

    def __init__(self):
        self.gemini_client = get_gemini_client()

    async def generate_comment(
        self,
        changed_fields: List[str],
        old_values: Dict,
        new_values: Dict,
        change_type: str,
        change_source: str,
        ai_suggestions: Optional[Dict] = None,
        ai_overridden: bool = False,
        overridden_fields: Optional[List[str]] = None
    ) -> str:
        """
        Generate PR-style comment for task changes.

        Args:
            changed_fields: List of field names that changed
            old_values: Previous values
            new_values: New values
            change_type: Type of change (status_change, field_update, etc.)
            change_source: Source (user_edit, ai_enrichment, etc.)
            ai_suggestions: AI-suggested values (for override detection)
            ai_overridden: Whether user overrode AI
            overridden_fields: Which fields were overridden

        Returns:
            PR-style comment string
        """
        # Decision: Use templates for simple changes
        if self._is_simple_change(changed_fields, change_type):
            return self._generate_template_comment(
                changed_fields,
                old_values,
                new_values,
                change_type,
                ai_overridden,
                overridden_fields
            )

        # Decision: Use Gemini for complex changes
        return await self._generate_gemini_comment(
            changed_fields,
            old_values,
            new_values,
            change_type,
            change_source,
            ai_suggestions,
            ai_overridden,
            overridden_fields
        )

    # ========================================================================
    # SIMPLE CHANGES (TEMPLATE-BASED)
    # ========================================================================

    def _is_simple_change(self, changed_fields: List[str], change_type: str) -> bool:
        """
        Determine if change is simple enough for template.

        Simple changes:
        - Single field change (status, priority, effort, assignee)
        - Status change (even with other fields)
        """
        if change_type == "status_change":
            return True

        if len(changed_fields) == 1 and changed_fields[0] in ["priority", "effort", "assignee", "project"]:
            return True

        return False

    def _generate_template_comment(
        self,
        changed_fields: List[str],
        old_values: Dict,
        new_values: Dict,
        change_type: str,
        ai_overridden: bool,
        overridden_fields: Optional[List[str]]
    ) -> str:
        """Generate comment using templates."""
        parts = []

        # Status change (always first if present)
        if "status" in changed_fields:
            old_status = old_values.get("status", "unknown")
            new_status = new_values.get("status", "unknown")
            template_key = (old_status, new_status)

            if template_key in STATUS_CHANGE_TEMPLATES:
                parts.append(STATUS_CHANGE_TEMPLATES[template_key])
            else:
                parts.append(f"📝 **Status updated** from `{old_status}` to `{new_status}`")

        # Priority change
        if "priority" in changed_fields:
            old_priority = old_values.get("priority", "unknown")
            new_priority = new_values.get("priority", "unknown")
            template_key = (old_priority, new_priority)

            if template_key in PRIORITY_CHANGE_TEMPLATES:
                parts.append(PRIORITY_CHANGE_TEMPLATES[template_key])
            else:
                parts.append(f"🎯 **Priority changed** from `{old_priority}` to `{new_priority}`")

        # Effort change
        if "effort" in changed_fields or "effort_estimate" in changed_fields:
            old_effort = old_values.get("effort") or old_values.get("effort_estimate")
            new_effort = new_values.get("effort") or new_values.get("effort_estimate")

            # Determine if increase or decrease (simple heuristic)
            effort_order = ["XS_15MIN", "S_1HR", "M_3HR", "L_1DAY", "XL_3DAYS", "XXL_1WEEK_PLUS"]
            if old_effort in effort_order and new_effort in effort_order:
                if effort_order.index(new_effort) > effort_order.index(old_effort):
                    parts.append(EFFORT_CHANGE_TEMPLATES["increase"])
                else:
                    parts.append(EFFORT_CHANGE_TEMPLATES["decrease"])
            else:
                parts.append(f"⏱️ **Effort estimate changed** from `{old_effort}` to `{new_effort}`")

        # Assignee change
        if "assignee" in changed_fields or "suggested_assignee" in changed_fields:
            old_assignee = old_values.get("assignee") or old_values.get("suggested_assignee", "unassigned")
            new_assignee = new_values.get("assignee") or new_values.get("suggested_assignee", "unassigned")
            parts.append(f"👤 **Assignee changed** from `{old_assignee}` to `{new_assignee}`")

        # Project change
        if "project" in changed_fields or "primary_project" in changed_fields:
            old_project = old_values.get("project") or old_values.get("primary_project", "none")
            new_project = new_values.get("project") or new_values.get("primary_project", "none")
            parts.append(f"📁 **Project changed** from `{old_project}` to `{new_project}`")

        # AI override note
        if ai_overridden and overridden_fields:
            parts.append(f"💡 **User override**: Changed {', '.join(overridden_fields)} from AI suggestion")

        return "\n\n".join(parts) if parts else "📝 Task updated"

    # ========================================================================
    # COMPLEX CHANGES (GEMINI-BASED)
    # ========================================================================

    async def _generate_gemini_comment(
        self,
        changed_fields: List[str],
        old_values: Dict,
        new_values: Dict,
        change_type: str,
        change_source: str,
        ai_suggestions: Optional[Dict],
        ai_overridden: bool,
        overridden_fields: Optional[List[str]]
    ) -> str:
        """Generate context-aware comment using Gemini."""

        prompt = self._build_comment_prompt(
            changed_fields,
            old_values,
            new_values,
            change_type,
            change_source,
            ai_suggestions,
            ai_overridden,
            overridden_fields
        )

        try:
            comment = await self.gemini_client.generate_text(
                prompt=prompt,
                temperature=0.3  # Lower temperature for consistent style
            )
            return comment.strip()
        except Exception as e:
            logger.error(f"Gemini comment generation failed: {e}")
            # Fallback to template
            return self._generate_template_comment(
                changed_fields,
                old_values,
                new_values,
                change_type,
                ai_overridden,
                overridden_fields
            )

    def _build_comment_prompt(
        self,
        changed_fields: List[str],
        old_values: Dict,
        new_values: Dict,
        change_type: str,
        change_source: str,
        ai_suggestions: Optional[Dict],
        ai_overridden: bool,
        overridden_fields: Optional[List[str]]
    ) -> str:
        """Build prompt for Gemini comment generation."""

        # Build field-by-field changes
        changes_text = ""
        for field in changed_fields:
            old_val = old_values.get(field, "not set")
            new_val = new_values.get(field, "not set")

            # Special handling for description (show diff summary, not full text)
            if field == "description":
                old_len = len(str(old_val)) if old_val else 0
                new_len = len(str(new_val)) if new_val else 0
                changes_text += f"- **{field}**: {old_len} → {new_len} characters\n"
            else:
                changes_text += f"- **{field}**: `{old_val}` → `{new_val}`\n"

        # Build AI override context
        override_text = ""
        if ai_overridden and ai_suggestions and overridden_fields:
            override_text = "\n**AI Override Context:**\n"
            for field in overridden_fields:
                ai_suggested = ai_suggestions.get(field)
                user_chose = new_values.get(field)
                override_text += f"- AI suggested `{ai_suggested}`, but user chose `{user_chose}`\n"

        prompt = f"""You are generating a PR-style comment for a task update in a project management system.

**Change Type:** {change_type}
**Change Source:** {change_source}
**Changed Fields:** {', '.join(changed_fields)}

**Changes:**
{changes_text}
{override_text}

**Your Task:**
Write a concise, professional comment explaining what changed and why it matters. Use GitHub PR comment style.

**Guidelines:**
1. Start with an emoji that fits the change (🚀 for starting work, ✅ for completion, ⚠️ for priority increase, etc.)
2. Use bold for section headers (e.g., **Status Update**)
3. Be concise (2-3 sentences max)
4. Focus on WHAT changed and WHY it matters (business context)
5. If AI was overridden, briefly note user's choice
6. Use markdown formatting

**Examples:**

Good: "🚀 **Work started** - Task moved to active development. Priority increased to P1 due to blocking production deployment."

Good: "✅ **Completed ahead of schedule** - Task finished in 2 hours instead of estimated 1 day. Simpler implementation path was found."

Good: "💡 **User override** - Changed priority from AI-suggested P2 to P1. User context indicates this blocks critical release."

Bad: "Task was updated." (too vague)
Bad: "Status changed from todo to doing and priority changed from P2 to P1 and effort changed from M to S." (too mechanical)

Now write the PR comment (just the comment, no preamble):
"""

        return prompt

    # ========================================================================
    # SPECIAL CASES
    # ========================================================================

    def generate_creation_comment(
        self,
        task_data: Dict,
        change_source: str,
        ai_model: Optional[str]
    ) -> str:
        """Generate comment for initial task creation."""
        if ai_model:
            return f"🎯 **Task created by AI** ({ai_model}) - Synthesized from user input with KG context enrichment"
        elif change_source == "user_create":
            return "📝 **Task created** by user"
        else:
            return "📝 **Task created**"


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def get_pr_comment_generator() -> PRCommentGenerator:
    """Factory function to get PR comment generator instance."""
    return PRCommentGenerator()
