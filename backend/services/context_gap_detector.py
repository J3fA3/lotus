"""
Context Gap Detector - Phase 6 Stage 2

Advanced gap detection and prioritization for intelligent task synthesis.

Key Features:
1. Gap Analysis: Identify missing critical information
2. Smart Prioritization: Rank gaps by importance and impact
3. Gap Clustering: Group related gaps for batched questions
4. Contextual Questions: Generate better questions using conversation history
5. Gap Resolution Tracking: Learn from how users fill gaps

Gap Priority Scoring:
- Field criticality (priority > project > assignee)
- User pattern analysis (frequently skipped fields = lower priority)
- Task complexity (complex tasks need more context)
- Time sensitivity (urgent tasks need fewer questions)
"""

import logging
from typing import List, Dict, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from datetime import datetime, timedelta

from models.intelligent_task import (
    ContextGap,
    IntelligentTaskDescription,
    AutoFillMetadata
)
from db.knowledge_graph_models_v2 import ConversationThreadNode
from agents.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)


# ============================================================================
# GAP PRIORITY WEIGHTS
# ============================================================================

FIELD_CRITICALITY = {
    "priority": 1.0,  # Most critical - affects task ordering
    "effort_estimate": 0.9,  # High - affects capacity planning
    "primary_project": 0.7,  # Medium - affects organization
    "suggested_assignee": 0.5,  # Lower - can be adjusted later
    "details": 0.8,  # High - affects understanding
    "stakeholders": 0.6,  # Medium - affects communication
}

IMPORTANCE_WEIGHTS = {
    "HIGH": 1.0,
    "MEDIUM": 0.6,
    "LOW": 0.3
}


# ============================================================================
# GAP CLUSTER TYPES
# ============================================================================

class GapCluster:
    """
    Represents a cluster of related context gaps.

    Clustering allows batching related questions together:
    - "Project and assignee" cluster
    - "Timeline and effort" cluster
    - "Stakeholders and impact" cluster
    """

    def __init__(self, cluster_type: str, gaps: List[ContextGap]):
        self.cluster_type = cluster_type
        self.gaps = gaps
        self.combined_question: Optional[str] = None
        self.priority_score: float = 0.0

    def calculate_priority(self):
        """Calculate cluster priority as max of gap priorities."""
        if not self.gaps:
            self.priority_score = 0.0
            return

        max_priority = max(
            FIELD_CRITICALITY.get(gap.field_name, 0.5) *
            IMPORTANCE_WEIGHTS.get(gap.importance, 0.5)
            for gap in self.gaps
        )
        self.priority_score = max_priority


# ============================================================================
# CONTEXT GAP DETECTOR
# ============================================================================

class ContextGapDetector:
    """
    Detects and prioritizes context gaps in task descriptions.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.gemini_client = get_gemini_client()

    async def analyze_gaps(
        self,
        task_desc: IntelligentTaskDescription,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> Dict:
        """
        Analyze context gaps and return prioritized, clustered gaps.

        Args:
            task_desc: Task description to analyze
            user_id: User ID for personalization
            conversation_id: Conversation thread for context

        Returns:
            Dict with:
            - prioritized_gaps: Gaps sorted by priority
            - gap_clusters: Clustered related gaps
            - recommended_batch_size: How many questions to ask at once
            - total_gap_score: Overall completeness score (0.0-1.0)
        """

        # Step 1: Extract gaps from task description
        gaps = task_desc.context_gaps

        if not gaps:
            return {
                "prioritized_gaps": [],
                "gap_clusters": [],
                "recommended_batch_size": 0,
                "total_gap_score": 1.0  # No gaps = complete
            }

        # Step 2: Enhance gaps with user patterns (if user_id available)
        if user_id:
            gaps = await self._enhance_with_user_patterns(gaps, user_id)

        # Step 3: Enhance gaps with conversation context
        if conversation_id:
            gaps = await self._enhance_with_conversation(gaps, conversation_id)

        # Step 4: Calculate priority scores
        prioritized_gaps = self._prioritize_gaps(gaps, task_desc)

        # Step 5: Cluster related gaps
        clusters = self._cluster_gaps(prioritized_gaps)

        # Step 6: Calculate total gap score
        total_gap_score = self._calculate_total_gap_score(
            prioritized_gaps,
            task_desc
        )

        # Step 7: Recommend batch size
        batch_size = self._recommend_batch_size(
            prioritized_gaps,
            task_desc
        )

        logger.info(
            f"Gap analysis: {len(gaps)} gaps, {len(clusters)} clusters, "
            f"batch_size={batch_size}, gap_score={total_gap_score:.2f}"
        )

        return {
            "prioritized_gaps": prioritized_gaps,
            "gap_clusters": clusters,
            "recommended_batch_size": batch_size,
            "total_gap_score": total_gap_score
        }

    # ========================================================================
    # GAP ENHANCEMENT
    # ========================================================================

    async def _enhance_with_user_patterns(
        self,
        gaps: List[ContextGap],
        user_id: str
    ) -> List[ContextGap]:
        """
        Enhance gaps with user-specific patterns.

        Learn from user behavior:
        - If user frequently skips a field → lower priority
        - If user always fills a field → higher priority
        - If user has default values → suggest them
        """

        # TODO: Implement user pattern analysis
        # This would query user's task history to find:
        # - Fields they frequently leave empty
        # - Fields they always fill
        # - Common values they use (projects, assignees, etc.)

        # For now, return gaps as-is
        return gaps

    async def _enhance_with_conversation(
        self,
        gaps: List[ContextGap],
        conversation_id: str
    ) -> List[ContextGap]:
        """
        Enhance gap questions with conversation context.

        Make questions more natural by referencing conversation history:
        - "You mentioned X earlier, should this task use the same approach?"
        - "This seems related to your question about Y - is that right?"
        """

        # Fetch conversation thread
        result = await self.db.execute(
            select(ConversationThreadNode).where(
                ConversationThreadNode.id == conversation_id
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            return gaps

        # Use Gemini to enhance questions with conversation context
        enhanced_gaps = []
        for gap in gaps:
            try:
                enhanced_question = await self._generate_contextual_question(
                    gap,
                    conversation
                )
                gap.question = enhanced_question
                enhanced_gaps.append(gap)
            except Exception as e:
                logger.warning(f"Failed to enhance gap question: {e}")
                enhanced_gaps.append(gap)  # Keep original

        return enhanced_gaps

    async def _generate_contextual_question(
        self,
        gap: ContextGap,
        conversation: ConversationThreadNode
    ) -> str:
        """
        Generate contextual question using conversation history.
        """

        prompt = f"""You are enhancing a question to make it more contextual and natural.

**Conversation Context:**
Summary: {conversation.summary}
Key Decisions: {', '.join(conversation.decisions_made) if conversation.decisions_made else 'None'}
Open Questions: {', '.join(conversation.open_questions) if conversation.open_questions else 'None'}

**Original Question:**
{gap.question}

**Field:** {gap.field_name}
**Suggested Answer:** {gap.suggested_answer if gap.suggested_answer else 'None'}

**Your Task:**
Rewrite the question to be more conversational and reference the conversation context where relevant.

Guidelines:
- Keep it concise (1-2 sentences)
- Reference conversation context naturally ("You mentioned X...", "This seems related to...")
- Include suggested answer if confidence > 0.5
- Make it feel like a natural follow-up question

Return ONLY the enhanced question text, nothing else.
"""

        response = await self.gemini_client.generate_text(
            prompt=prompt,
            temperature=0.5
        )

        return response.strip()

    # ========================================================================
    # GAP PRIORITIZATION
    # ========================================================================

    def _prioritize_gaps(
        self,
        gaps: List[ContextGap],
        task_desc: IntelligentTaskDescription
    ) -> List[ContextGap]:
        """
        Prioritize gaps by importance and impact.

        Priority Score = Field Criticality × Importance Weight × Context Modifier

        Context Modifiers:
        - Urgent task (priority=P0/P1) → boost priority field, reduce others
        - Complex task (effort=L/XL/XXL) → boost details field
        - Has stakeholders → boost stakeholder field
        """

        scored_gaps = []

        for gap in gaps:
            # Base score
            field_crit = FIELD_CRITICALITY.get(gap.field_name, 0.5)
            importance_weight = IMPORTANCE_WEIGHTS.get(gap.importance, 0.5)
            base_score = field_crit * importance_weight

            # Context modifiers
            context_modifier = 1.0

            # If task is urgent, prioritize priority field
            if gap.field_name == "priority":
                # Check for urgency keywords in summary
                urgency_keywords = ["urgent", "asap", "critical", "blocking", "production"]
                if any(kw in task_desc.summary.lower() for kw in urgency_keywords):
                    context_modifier = 1.5

            # If task seems complex, prioritize details
            if gap.field_name == "details":
                if task_desc.effort_estimate and task_desc.effort_estimate.value in ["L_1DAY", "XL_3DAYS", "XXL_1WEEK_PLUS"]:
                    context_modifier = 1.3

            # Final score
            final_score = base_score * context_modifier

            # Add score to gap (using a custom attribute)
            gap_dict = gap.dict()
            gap_dict["priority_score"] = final_score
            scored_gaps.append((ContextGap(**gap_dict), final_score))

        # Sort by score (descending)
        scored_gaps.sort(key=lambda x: x[1], reverse=True)

        return [gap for gap, score in scored_gaps]

    # ========================================================================
    # GAP CLUSTERING
    # ========================================================================

    def _cluster_gaps(self, gaps: List[ContextGap]) -> List[GapCluster]:
        """
        Cluster related gaps for batched questions.

        Clusters:
        - "Planning" cluster: priority, effort_estimate
        - "Organization" cluster: primary_project, suggested_assignee
        - "Details" cluster: details, stakeholders, success_criteria
        """

        clusters = []

        # Planning cluster
        planning_gaps = [
            g for g in gaps
            if g.field_name in ["priority", "effort_estimate"]
        ]
        if planning_gaps:
            cluster = GapCluster("planning", planning_gaps)
            cluster.calculate_priority()
            cluster.combined_question = self._generate_combined_question(
                "Planning",
                planning_gaps
            )
            clusters.append(cluster)

        # Organization cluster
        org_gaps = [
            g for g in gaps
            if g.field_name in ["primary_project", "suggested_assignee", "related_markets"]
        ]
        if org_gaps:
            cluster = GapCluster("organization", org_gaps)
            cluster.calculate_priority()
            cluster.combined_question = self._generate_combined_question(
                "Organization",
                org_gaps
            )
            clusters.append(cluster)

        # Details cluster
        detail_gaps = [
            g for g in gaps
            if g.field_name in ["details", "stakeholders", "success_criteria", "blockers"]
        ]
        if detail_gaps:
            cluster = GapCluster("details", detail_gaps)
            cluster.calculate_priority()
            cluster.combined_question = self._generate_combined_question(
                "Details",
                detail_gaps
            )
            clusters.append(cluster)

        # Sort clusters by priority
        clusters.sort(key=lambda c: c.priority_score, reverse=True)

        return clusters

    def _generate_combined_question(
        self,
        cluster_name: str,
        gaps: List[ContextGap]
    ) -> str:
        """
        Generate a combined question for a cluster of gaps.

        Example:
        Instead of:
        - "What is the priority?"
        - "What is the effort?"

        Combined:
        "Let's plan this task - what priority level should it have, and how much effort will it take?"
        """

        if len(gaps) == 1:
            return gaps[0].question

        questions = [g.question for g in gaps]

        # Create combined question based on cluster type
        if cluster_name == "Planning":
            return f"Let's plan this task: {' '.join(questions)}"
        elif cluster_name == "Organization":
            return f"Help me organize this task: {' '.join(questions)}"
        elif cluster_name == "Details":
            return f"I need more details: {' '.join(questions)}"
        else:
            return " ".join(questions)

    # ========================================================================
    # GAP SCORING
    # ========================================================================

    def _calculate_total_gap_score(
        self,
        gaps: List[ContextGap],
        task_desc: IntelligentTaskDescription
    ) -> float:
        """
        Calculate overall gap score (0.0 = many gaps, 1.0 = no gaps).

        Score factors:
        - Number of gaps
        - Criticality of missing fields
        - Confidence in suggested answers
        """

        if not gaps:
            return 1.0

        # Count critical gaps (HIGH importance)
        critical_gaps = sum(1 for g in gaps if g.importance == "HIGH")

        # Average confidence of suggested answers
        avg_confidence = sum(g.confidence for g in gaps) / len(gaps)

        # Penalize for critical gaps
        critical_penalty = critical_gaps * 0.15

        # Penalize for low-confidence suggestions
        confidence_penalty = (1.0 - avg_confidence) * 0.2

        # Base score from gap count (max 10 gaps = 0.0, 0 gaps = 1.0)
        gap_count_score = max(0.0, 1.0 - (len(gaps) / 10.0))

        # Final score
        score = max(0.0, gap_count_score - critical_penalty - confidence_penalty)

        return round(score, 2)

    # ========================================================================
    # BATCH SIZE RECOMMENDATION
    # ========================================================================

    def _recommend_batch_size(
        self,
        gaps: List[ContextGap],
        task_desc: IntelligentTaskDescription
    ) -> int:
        """
        Recommend how many questions to ask at once.

        Strategy:
        - Urgent tasks (P0/P1): Ask only critical questions (max 2)
        - Normal tasks (P2/P3): Ask more questions (3-5)
        - Complex tasks: Spread questions across multiple batches
        - User patience: Don't overwhelm with too many questions
        """

        if not gaps:
            return 0

        # Check urgency
        is_urgent = False
        if task_desc.priority:
            is_urgent = task_desc.priority.value in ["P0_CRITICAL", "P1_HIGH"]

        # Count critical gaps
        critical_gaps = sum(1 for g in gaps if g.importance == "HIGH")

        # Recommend batch size
        if is_urgent:
            # For urgent tasks, only ask critical questions
            return min(critical_gaps, 2)
        else:
            # For normal tasks, ask 3-5 questions
            # But don't exceed total gaps
            return min(len(gaps), 5)


# ============================================================================
# GAP RESOLUTION TRACKER
# ============================================================================

class GapResolutionTracker:
    """
    Tracks how users resolve context gaps to improve future gap detection.

    Learning signals:
    - Which gaps users answer vs skip
    - How long users take to answer
    - Common values for certain gap types
    - Gaps that correlate with task success/failure
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def track_resolution(
        self,
        task_id: str,
        gap: ContextGap,
        user_answer: Optional[str],
        resolution_time_seconds: float
    ):
        """
        Track how a gap was resolved.

        Args:
            task_id: Task ID
            gap: The context gap
            user_answer: User's answer (None if skipped)
            resolution_time_seconds: How long user took to answer
        """

        # TODO: Store gap resolution data for learning
        # This would go in a new table: gap_resolutions
        # Fields:
        # - task_id
        # - field_name
        # - original_question
        # - suggested_answer
        # - confidence
        # - user_answer (actual)
        # - was_skipped (bool)
        # - resolution_time_seconds
        # - created_at

        logger.info(
            f"Gap resolved for task {task_id}, field {gap.field_name}: "
            f"{'skipped' if user_answer is None else 'answered'}"
        )

    async def get_user_gap_patterns(self, user_id: str) -> Dict:
        """
        Get user's gap resolution patterns for personalization.

        Returns:
            Dict with:
            - frequently_skipped_fields: Fields user usually skips
            - frequently_filled_fields: Fields user always fills
            - average_resolution_time: How long user typically takes
            - common_values: Common values user provides for certain fields
        """

        # TODO: Implement pattern analysis from gap_resolutions table

        return {
            "frequently_skipped_fields": [],
            "frequently_filled_fields": [],
            "average_resolution_time": 0.0,
            "common_values": {}
        }


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

async def get_context_gap_detector(db: AsyncSession) -> ContextGapDetector:
    """Factory function to get context gap detector instance."""
    return ContextGapDetector(db)


async def get_gap_resolution_tracker(db: AsyncSession) -> GapResolutionTracker:
    """Factory function to get gap resolution tracker instance."""
    return GapResolutionTracker(db)
