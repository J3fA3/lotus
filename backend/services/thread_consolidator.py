"""
Thread Consolidation Service - Phase 5

Consolidates email threads (5+ messages) into single tasks.

Extracts final action from back-and-forth conversations.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from services.gemini_client import get_gemini_client
from config.email_prompts import get_thread_consolidation_prompt

logger = logging.getLogger(__name__)


@dataclass
class ConsolidatedThread:
    """Result of thread consolidation."""
    thread_id: str
    should_consolidate: bool
    consolidated_action: Optional[str]
    final_deadline: Optional[str]
    key_participants: List[str]
    reasoning: str
    message_count: int


class ThreadConsolidator:
    """Service for consolidating email threads into single tasks."""

    def __init__(self):
        """Initialize thread consolidator."""
        self.min_messages_for_consolidation = 5
        self.gemini = None
        logger.info("Thread consolidator initialized")

    async def consolidate_thread(
        self,
        thread_id: str,
        thread_emails: List[Dict[str, Any]],
        thread_subject: str
    ) -> ConsolidatedThread:
        """Consolidate email thread into single action.

        Args:
            thread_id: Gmail thread ID
            thread_emails: List of email dicts (subject, sender, body, date)
            thread_subject: Thread subject

        Returns:
            ConsolidatedThread with consolidation result
        """
        message_count = len(thread_emails)

        # Check if consolidation needed
        if message_count < self.min_messages_for_consolidation:
            logger.info(
                f"Thread {thread_id} has only {message_count} messages - "
                f"no consolidation needed (min={self.min_messages_for_consolidation})"
            )
            return ConsolidatedThread(
                thread_id=thread_id,
                should_consolidate=False,
                consolidated_action=None,
                final_deadline=None,
                key_participants=[],
                reasoning=f"Thread has only {message_count} messages (min={self.min_messages_for_consolidation})",
                message_count=message_count
            )

        # Sort emails by date (oldest first)
        sorted_emails = sorted(thread_emails, key=lambda e: e.get('received_at', datetime.min))

        # Get Gemini client
        if not self.gemini:
            self.gemini = get_gemini_client()

        # Build consolidation prompt
        prompt = get_thread_consolidation_prompt(sorted_emails, thread_subject)

        try:
            # Call Gemini
            response = await self.gemini.ainvoke(prompt, temperature=0.4)
            response_text = response.content if hasattr(response, 'content') else str(response)

            # Extract key participants
            participants = set()
            for email in sorted_emails:
                sender_email = email.get('sender_email', '')
                if sender_email:
                    participants.add(sender_email)

            logger.info(
                f"Thread {thread_id} consolidated: {message_count} messages → single action"
            )

            return ConsolidatedThread(
                thread_id=thread_id,
                should_consolidate=True,
                consolidated_action=response_text.strip(),
                final_deadline=self._extract_deadline(sorted_emails),
                key_participants=list(participants),
                reasoning=f"Consolidated {message_count} messages into final action",
                message_count=message_count
            )

        except Exception as e:
            logger.error(f"Thread consolidation failed for {thread_id}: {e}")
            return ConsolidatedThread(
                thread_id=thread_id,
                should_consolidate=False,
                consolidated_action=None,
                final_deadline=None,
                key_participants=[],
                reasoning=f"Consolidation failed: {e}",
                message_count=message_count
            )

    def should_create_single_task(self, thread: ConsolidatedThread) -> bool:
        """Determine if thread should create single consolidated task.

        Args:
            thread: Consolidated thread result

        Returns:
            True if should create single task for whole thread
        """
        return (
            thread.should_consolidate and
            thread.consolidated_action is not None and
            thread.message_count >= self.min_messages_for_consolidation
        )

    def _extract_deadline(self, emails: List[Dict[str, Any]]) -> Optional[str]:
        """Extract final deadline from email thread.

        Takes the most recent deadline mentioned.

        Args:
            emails: List of emails (sorted by date)

        Returns:
            Deadline string or None
        """
        # Simple heuristic: look for date-like patterns in most recent emails
        # In production, this would use more sophisticated extraction

        deadline_keywords = ["deadline", "due", "by", "before", "until"]

        # Check last 3 emails for deadlines
        for email in reversed(emails[-3:]):
            body = email.get('body_text', '').lower()

            for keyword in deadline_keywords:
                if keyword in body:
                    # Found deadline mention - extract context
                    # This is simplified; production would use NER
                    sentences = body.split('.')
                    for sentence in sentences:
                        if keyword in sentence:
                            return sentence.strip()[:100]

        return None

    def extract_final_action(self, thread: ConsolidatedThread) -> str:
        """Extract final action from consolidated thread.

        Args:
            thread: Consolidated thread

        Returns:
            Final action description
        """
        if thread.consolidated_action:
            return thread.consolidated_action

        return f"Review thread: {thread.thread_id}"


# Singleton instance
_thread_consolidator = None


def get_thread_consolidator() -> ThreadConsolidator:
    """Get singleton ThreadConsolidator instance.

    Returns:
        ThreadConsolidator instance
    """
    global _thread_consolidator
    if _thread_consolidator is None:
        _thread_consolidator = ThreadConsolidator()
    return _thread_consolidator
