"""
Relevance Filter Agent - Phase 3

Filters proposed tasks to only extract what's relevant for the user.

Key Features:
1. Scores task relevance (0-100)
2. Filters out tasks explicitly for other people
3. Keeps tasks relevant to user's projects, markets, role
4. Uses Gemini for intelligent scoring

Scoring Rules:
- 100: Direct mention of user's name or "I/me"
- 80-90: User's projects or responsibilities
- 60-70: Team task, user involvement likely
- 30-50: Generic team context, unclear
- 0-20: Explicitly for someone else or unrelated

Only creates tasks with score >= 50 (lowered from 70 to improve recall)
"""

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from services.gemini_client import get_gemini_client
from services.user_profile import UserProfile
from config.gemini_prompts import get_relevance_scoring_prompt

logger = logging.getLogger(__name__)


class RelevanceScore(BaseModel):
    """Relevance score result."""
    score: int  # 0-100
    is_for_user: bool
    reasoning: str


class RelevanceFilter:
    """Filters tasks by relevance to the user."""

    def __init__(self, relevance_threshold: int = 50):
        """Initialize relevance filter.

        Args:
            relevance_threshold: Minimum score to keep task (default 50, lowered from 70 for better recall)
        """
        self.gemini = get_gemini_client()
        self.threshold = relevance_threshold

    async def score_relevance(
        self,
        task: Dict[str, Any],
        user_profile: UserProfile,
        context: str
    ) -> RelevanceScore:
        """Score a task's relevance to the user.

        Args:
            task: Proposed task dict
            user_profile: User's profile
            context: Original input context

        Returns:
            RelevanceScore with score, is_for_user, reasoning
        """
        title = task.get("title", "")
        description = task.get("description", "")
        assignee = task.get("assignee", "")

        # Quick check 1: Explicitly assigned to someone else
        if assignee and assignee.lower() not in ["unassigned", "", "you", user_profile.name.lower()]:
            # Check if it's NOT one of user's aliases
            is_alias = any(alias.lower() in assignee.lower() for alias in user_profile.aliases)
            if not is_alias:
                logger.debug(f"Task explicitly for someone else: {assignee}")
                return RelevanceScore(
                    score=0,
                    is_for_user=False,
                    reasoning=f"Task explicitly assigned to {assignee}, not {user_profile.name}"
                )

        # Quick check 2: Direct mention of user's name or first-person
        text = f"{title} {description} {context}".lower()

        # Check name and aliases
        for name_variant in [user_profile.name] + user_profile.aliases:
            if name_variant.lower() in text:
                logger.debug(f"Task mentions user's name: {name_variant}")
                return RelevanceScore(
                    score=100,
                    is_for_user=True,
                    reasoning=f"Task directly mentions {name_variant}"
                )

        # Check first-person pronouns
        first_person = [" i ", " me ", " my ", "i'm", "i'll", "i've", " i'm ", " i'll ", " i've "]
        if any(word in text for word in first_person):
            logger.debug("Task uses first-person pronouns")
            return RelevanceScore(
                score=100,
                is_for_user=True,
                reasoning="Task uses first-person pronouns (I/me/my)"
            )

        # Quick check 3: Group-directed messages with action items
        group_directed = ["everyone", "you all", "please prepare", "please review", "please make sure", 
                         "please complete", "please submit", "you need to", "you should"]
        
        matches = [phrase for phrase in group_directed if phrase in text]
        if matches:
            logger.debug("Task is part of group-directed message with action items")
            return RelevanceScore(
                score=60,
                is_for_user=True,
                reasoning=f"Group-directed message with action items: {', '.join(matches)}"
            )

        # Use Gemini for nuanced scoring
        try:
            prompt = get_relevance_scoring_prompt(
                task_title=title,
                task_description=description,
                context=context,
                user_profile=user_profile.to_dict()
            )

            result = await self.gemini.generate_structured(
                prompt=prompt,
                schema=RelevanceScore,
                temperature=0.1
            )

            logger.debug(f"Gemini relevance score: {result.score} - {result.reasoning}")
            return result

        except Exception as e:
            logger.error(f"Relevance scoring failed: {e}")
            # Fallback: use heuristics
            return self._fallback_scoring(task, user_profile, context)

    def _fallback_scoring(
        self,
        task: Dict[str, Any],
        user_profile: UserProfile,
        context: str
    ) -> RelevanceScore:
        """Fallback heuristic scoring if Gemini fails.

        Args:
            task: Proposed task
            user_profile: User profile
            context: Context text

        Returns:
            RelevanceScore
        """
        score = 50  # Neutral default
        reasoning = "Unclear relevance"

        title = task.get("title", "").lower()
        description = task.get("description", "").lower()
        text = f"{title} {description} {context}".lower()

        # Check project mentions
        for project in user_profile.projects:
            if project.lower() in text:
                score = 80
                reasoning = f"Mentions user's project: {project}"
                break

        # Check market mentions
        if score < 80:
            for market in user_profile.markets:
                if market.lower() in text:
                    score = 75
                    reasoning = f"Mentions user's market: {market}"
                    break

        # Check role context
        if score < 75 and user_profile.role:
            if user_profile.role.lower() in text:
                score = 65
                reasoning = f"Mentions user's role: {user_profile.role}"

        is_for_user = score >= self.threshold

        return RelevanceScore(
            score=score,
            is_for_user=is_for_user,
            reasoning=reasoning
        )

    async def filter_tasks(
        self,
        proposed_tasks: List[Dict[str, Any]],
        user_profile: UserProfile,
        context: str
    ) -> List[Dict[str, Any]]:
        """Filter proposed tasks to only relevant ones.

        Args:
            proposed_tasks: List of proposed tasks
            user_profile: User profile
            context: Original input context

        Returns:
            Filtered list of tasks (only relevant ones)
        """
        if not proposed_tasks:
            return []

        relevant_tasks = []
        filtered_count = 0

        for task in proposed_tasks:
            print(f"DEBUG: Scoring task: {task.get('title')}")
            score_result = await self.score_relevance(task, user_profile, context)

            # Store relevance score in task
            task["relevance_score"] = score_result.score
            task["relevance_reasoning"] = score_result.reasoning

            if score_result.score >= self.threshold:
                relevant_tasks.append(task)
                logger.info(
                    f"✓ Keeping task (score {score_result.score}): {task.get('title', 'Unknown')}"
                )
            else:
                filtered_count += 1
                logger.info(
                    f"✗ Filtering task (score {score_result.score}): {task.get('title', 'Unknown')} - "
                    f"{score_result.reasoning}"
                )

        logger.info(
            f"Relevance filter: Kept {len(relevant_tasks)}/{len(proposed_tasks)} tasks "
            f"(filtered {filtered_count})"
        )

        return relevant_tasks


# Singleton instance
_relevance_filter: Optional[RelevanceFilter] = None


def get_relevance_filter(threshold: int = 70) -> RelevanceFilter:
    """Get or create global RelevanceFilter instance.

    Args:
        threshold: Relevance threshold (default 70)

    Returns:
        RelevanceFilter singleton
    """
    global _relevance_filter
    # Recreate if threshold changed or doesn't exist
    if _relevance_filter is None or _relevance_filter.threshold != threshold:
        _relevance_filter = RelevanceFilter(relevance_threshold=threshold)
    return _relevance_filter
