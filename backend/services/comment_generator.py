"""
Natural Language Comment Generator - Phase 3

Generates human-like comments explaining AI decisions.

Replaces robotic comments like:
❌ "🤖 Confidence: 75%, entity_quality: 83%"

With natural explanations like:
✅ "Alberto (Spain market) asked about pharmacy pinning. Tagged as Spain-specific
    since that's his focus area."

Key Features:
1. Natural, conversational language
2. References people, markets, projects
3. Explains WHY decisions were made
4. Professional but friendly tone
"""

import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

from services.gemini_client import get_gemini_client
from config.gemini_prompts import get_comment_generation_prompt

logger = logging.getLogger(__name__)


class GeneratedComment(BaseModel):
    """Generated comment result."""
    text: str
    confidence: float = 1.0  # How confident we are in the comment


class CommentGenerator:
    """Generates natural language comments for task operations."""

    def __init__(self):
        """Initialize comment generator."""
        self.gemini = get_gemini_client()

    async def generate_creation_comment(
        self,
        task: Dict[str, Any],
        context: str,
        decision_factors: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate comment for task creation.

        Args:
            task: Created task dict
            context: Original input context
            decision_factors: Dict with confidence, entities, etc.

        Returns:
            Natural language comment string
        """
        try:
            prompt = get_comment_generation_prompt(
                task=task,
                context=context,
                decision_factors=decision_factors or {},
                comment_type="creation"
            )

            # Generate natural comment
            comment = await self.gemini.generate(
                prompt=prompt,
                temperature=0.4,  # Slightly higher for natural variation
                max_tokens=200
            )

            # Clean up any markdown or formatting
            comment = comment.strip()
            if comment.startswith('"') and comment.endswith('"'):
                comment = comment[1:-1]

            logger.debug(f"Generated creation comment: {comment[:100]}...")
            return comment

        except Exception as e:
            logger.error(f"Comment generation failed: {e}")
            # Fallback to simple template
            return self._fallback_creation_comment(task, context)

    async def generate_enrichment_comment(
        self,
        task: Dict[str, Any],
        context: str,
        changes: Dict[str, Any]
    ) -> str:
        """Generate comment for task enrichment/update.

        Args:
            task: Existing task dict
            context: New context that triggered enrichment
            changes: Dict describing what changed

        Returns:
            Natural language comment string
        """
        try:
            # Build summary of changes
            changes_summary = self._format_changes(changes)

            prompt = get_comment_generation_prompt(
                task=task,
                context=context,
                decision_factors={"changes_summary": changes_summary},
                comment_type="enrichment"
            )

            # Generate natural comment
            comment = await self.gemini.generate(
                prompt=prompt,
                temperature=0.4,
                max_tokens=200
            )

            # Clean up
            comment = comment.strip()
            if comment.startswith('"') and comment.endswith('"'):
                comment = comment[1:-1]

            logger.debug(f"Generated enrichment comment: {comment[:100]}...")
            return comment

        except Exception as e:
            logger.error(f"Enrichment comment generation failed: {e}")
            # Fallback
            return self._fallback_enrichment_comment(task, context, changes)

    def _format_changes(self, changes: Dict[str, Any]) -> str:
        """Format changes dict into readable summary.

        Args:
            changes: Changes dict

        Returns:
            Human-readable summary
        """
        parts = []

        if changes.get("due_date"):
            parts.append(f"Updated due date to {changes['due_date']}")

        if changes.get("note_to_add"):
            parts.append(f"Added note: {changes['note_to_add'][:50]}")

        if changes.get("priority_change"):
            parts.append(f"Changed priority to {changes['priority_change']}")

        if changes.get("status_change"):
            parts.append(f"Changed status to {changes['status_change']}")

        return ", ".join(parts) if parts else "Updated task details"

    def _fallback_creation_comment(
        self,
        task: Dict[str, Any],
        context: str
    ) -> str:
        """Fallback comment template for task creation.

        Args:
            task: Task dict
            context: Context string

        Returns:
            Simple comment string
        """
        # Extract first sentence from context
        first_sentence = context.split('.')[0][:100]

        assignee = task.get("assignee", "you")
        project = task.get("value_stream", "")

        comment = f"Created based on: {first_sentence}"

        if project:
            comment += f". Tagged with project: {project}"

        if task.get("due_date"):
            comment += f". Due: {task['due_date']}"

        return comment

    def _fallback_enrichment_comment(
        self,
        task: Dict[str, Any],
        context: str,
        changes: Dict[str, Any]
    ) -> str:
        """Fallback comment template for enrichment.

        Args:
            task: Task dict
            context: Context string
            changes: Changes dict

        Returns:
            Simple comment string
        """
        changes_summary = self._format_changes(changes)
        first_sentence = context.split('.')[0][:100]

        return f"Updated based on new information: {first_sentence}. {changes_summary}"


# Singleton instance
_comment_generator: Optional[CommentGenerator] = None


def get_comment_generator() -> CommentGenerator:
    """Get or create global CommentGenerator instance.

    Returns:
        CommentGenerator singleton
    """
    global _comment_generator
    if _comment_generator is None:
        _comment_generator = CommentGenerator()
    return _comment_generator
