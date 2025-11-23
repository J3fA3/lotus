"""
Contextual Task Synthesizer - Phase 6 Stage 2

Transforms raw user input into intelligent task descriptions using:
1. Knowledge Graph context (concepts, conversations, outcomes)
2. Similar task matching
3. Gemini-powered synthesis with structured output
4. Confidence-based auto-fill with gap detection

Auto-fill Confidence Thresholds:
- Priority (urgency): 0.8 (HIGH)
- Effort (similar tasks): 0.75 (MEDIUM+)
- Project (concepts): 0.7 (MEDIUM+)
- Assignee (relationships): 0.6 (MEDIUM+)
"""

import logging
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from datetime import datetime, timedelta

from models.intelligent_task import (
    IntelligentTaskDescription,
    TaskSynthesisResult,
    ContextGap,
    SimilarTaskMatch,
    AutoFillMetadata,
    ConfidenceTier,
    PriorityLevel,
    EffortEstimate,
    WhyItMattersSection,
    WhatWasDiscussedSection,
    HowToApproachSection,
    RelatedWorkSection,
    Stakeholder,
    RelatedTask,
    TaskDescriptionQuality
)
from services.kg_evolution_service import KGEvolutionService
from db.knowledge_graph_models_v2 import (
    ConceptNode,
    ConversationThreadNode,
    TaskOutcomeNode,
    TaskSimilarityIndex
)
from db.models import Task
from services.gemini_client import get_gemini_client
from prompts.synthesis_prompts import get_synthesis_prompt

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIDENCE THRESHOLDS
# ============================================================================

CONFIDENCE_THRESHOLDS = {
    "priority": 0.8,  # High bar - priority is critical
    "effort_estimate": 0.75,  # Medium+ - effort impacts planning
    "primary_project": 0.7,  # Medium+ - project alignment matters
    "suggested_assignee": 0.6,  # Medium - assignee can be adjusted later
}


def get_confidence_tier(confidence: float) -> ConfidenceTier:
    """Map confidence score to tier."""
    if confidence >= 0.8:
        return ConfidenceTier.HIGH
    elif confidence >= 0.6:
        return ConfidenceTier.MEDIUM
    else:
        return ConfidenceTier.LOW


# ============================================================================
# TASK SYNTHESIZER SERVICE
# ============================================================================

class TaskSynthesizerService:
    """
    Synthesizes intelligent task descriptions from raw input + KG context.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.kg_service = KGEvolutionService(db)
        self.gemini_client = get_gemini_client()

    async def synthesize_task(
        self,
        raw_input: str,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> TaskSynthesisResult:
        """
        Synthesize intelligent task description from raw input.

        Args:
            raw_input: User's original input
            user_id: User ID for personalization (optional)
            conversation_id: Conversation thread ID (optional)

        Returns:
            TaskSynthesisResult with intelligent task description

        Raises:
            Exception if synthesis fails completely
        """
        try:
            # Step 1: Assemble rich context from KG
            logger.info(f"Assembling context for synthesis: '{raw_input[:100]}...'")
            context = await self._assemble_rich_context(
                raw_input,
                user_id,
                conversation_id
            )

            # Step 2: Find similar tasks
            similar_tasks = await self._find_similar_tasks(raw_input)

            # Step 3: Build synthesis prompt
            prompt = self._build_synthesis_prompt(
                raw_input,
                context,
                similar_tasks
            )

            # Step 4: Call Gemini with structured output
            logger.info("Calling Gemini for task synthesis...")
            result = await self._call_gemini_synthesis(prompt)

            # Step 5: Apply confidence thresholds and generate context gaps
            result = self._apply_confidence_thresholds(result)

            # Step 6: Calculate quality metrics
            quality = self._calculate_quality_metrics(result.task_description)

            logger.info(
                f"Synthesis complete. Quality: {quality.overall_quality:.2f}, "
                f"Gaps: {len(result.task_description.context_gaps)}"
            )

            return result

        except Exception as e:
            logger.error(f"Task synthesis failed: {e}", exc_info=True)
            # Fallback: Create basic task with all fields as context gaps
            return self._create_fallback_task(raw_input)

    # ========================================================================
    # CONTEXT ASSEMBLY
    # ========================================================================

    async def _assemble_rich_context(
        self,
        raw_input: str,
        user_id: Optional[str],
        conversation_id: Optional[str]
    ) -> Dict:
        """
        Assemble rich context from Knowledge Graph.

        Returns:
            Dict with:
            - top_concepts: Recent high-importance concepts
            - active_conversations: Recent conversation threads
            - successful_outcomes: Recent completed tasks with high quality
            - user_preferences: User-specific context (if available)
        """
        context = {}

        # Get top concepts (ESTABLISHED + EMERGING, recent mentions)
        result = await self.db.execute(
            select(ConceptNode)
            .where(
                and_(
                    ConceptNode.confidence_tier.in_(["ESTABLISHED", "EMERGING"]),
                    ConceptNode.mention_count_30d > 0
                )
            )
            .order_by(ConceptNode.importance_score.desc())
            .limit(10)
        )
        concepts = result.scalars().all()
        context["top_concepts"] = [
            {
                "name": c.name,
                "importance": c.importance_score,
                "tier": c.confidence_tier,
                "projects": c.related_projects,
                "markets": c.related_markets
            }
            for c in concepts
        ]

        # Get active conversations (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        result = await self.db.execute(
            select(ConversationThreadNode)
            .where(ConversationThreadNode.last_updated >= seven_days_ago)
            .order_by(ConversationThreadNode.last_updated.desc())
            .limit(5)
        )
        conversations = result.scalars().all()
        context["active_conversations"] = [
            {
                "summary": c.summary,
                "decisions": c.decisions_made,
                "open_questions": c.open_questions
            }
            for c in conversations
        ]

        # Get successful outcomes (COMPLETED, quality >= 4.0, last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        result = await self.db.execute(
            select(TaskOutcomeNode)
            .where(
                and_(
                    TaskOutcomeNode.outcome == "COMPLETED",
                    TaskOutcomeNode.completion_quality >= 4.0,
                    TaskOutcomeNode.completed_at >= thirty_days_ago
                )
            )
            .order_by(TaskOutcomeNode.completion_quality.desc())
            .limit(5)
        )
        outcomes = result.scalars().all()
        context["successful_outcomes"] = [
            {
                "task_id": o.task_id,
                "quality": o.completion_quality,
                "lessons": o.lessons_learned
            }
            for o in outcomes
        ]

        # TODO: Add user preferences when user service is available
        context["user_preferences"] = {}

        logger.info(
            f"Context assembled: {len(context['top_concepts'])} concepts, "
            f"{len(context['active_conversations'])} conversations, "
            f"{len(context['successful_outcomes'])} outcomes"
        )

        return context

    async def _find_similar_tasks(
        self,
        raw_input: str,
        limit: int = 5
    ) -> List[SimilarTaskMatch]:
        """
        Find similar tasks using task similarity index.

        Note: This is a simplified version. In production, you'd use
        vector similarity search with embeddings.
        """
        # TODO: Implement proper vector similarity search
        # For now, return empty list - will be enhanced in later phase

        # Placeholder: Query similarity index
        # This would use pgvector or similar for semantic search
        similar_tasks = []

        logger.info(f"Found {len(similar_tasks)} similar tasks")
        return similar_tasks

    # ========================================================================
    # PROMPT ENGINEERING
    # ========================================================================

    def _build_synthesis_prompt(
        self,
        raw_input: str,
        context: Dict,
        similar_tasks: List[SimilarTaskMatch]
    ) -> str:
        """
        Build comprehensive synthesis prompt for Gemini.

        Uses production-grade prompts from prompts.synthesis_prompts module.
        """
        return get_synthesis_prompt(raw_input, context, similar_tasks)

    # ========================================================================
    # GEMINI INTEGRATION
    # ========================================================================

    async def _call_gemini_synthesis(self, prompt: str) -> TaskSynthesisResult:
        """
        Call Gemini with structured output for task synthesis.

        Uses TaskSynthesisResult schema for type-safe response.
        """
        try:
            response = await self.gemini_client.generate_structured_output(
                prompt=prompt,
                response_schema=TaskSynthesisResult,
                temperature=0.3  # Lower temperature for more consistent synthesis
            )

            return response

        except Exception as e:
            logger.error(f"Gemini synthesis failed: {e}")
            raise

    # ========================================================================
    # CONFIDENCE THRESHOLDS & GAP DETECTION
    # ========================================================================

    def _apply_confidence_thresholds(
        self,
        result: TaskSynthesisResult
    ) -> TaskSynthesisResult:
        """
        Apply confidence thresholds to auto-filled fields.

        For each auto-filled field:
        - If confidence >= threshold: Keep auto-filled value
        - If confidence < threshold: Clear value and create ContextGap

        This ensures we only auto-fill when confident enough.
        """
        task_desc = result.task_description
        new_gaps = []

        # Check priority
        if task_desc.priority:
            priority_meta = next(
                (m for m in task_desc.auto_fill_metadata if m.field_name == "priority"),
                None
            )
            if priority_meta and priority_meta.confidence < CONFIDENCE_THRESHOLDS["priority"]:
                # Confidence too low - create gap
                new_gaps.append(ContextGap(
                    field_name="priority",
                    question="What is the priority of this task? (P0_CRITICAL, P1_HIGH, P2_MEDIUM, P3_LOW)",
                    importance="HIGH",
                    suggested_answer=task_desc.priority.value,
                    confidence=priority_meta.confidence
                ))
                task_desc.priority = None  # Clear auto-filled value

        # Check effort_estimate
        if task_desc.effort_estimate:
            effort_meta = next(
                (m for m in task_desc.auto_fill_metadata if m.field_name == "effort_estimate"),
                None
            )
            if effort_meta and effort_meta.confidence < CONFIDENCE_THRESHOLDS["effort_estimate"]:
                new_gaps.append(ContextGap(
                    field_name="effort_estimate",
                    question="How much effort will this take? (XS_15MIN, S_1HR, M_3HR, L_1DAY, XL_3DAYS, XXL_1WEEK_PLUS)",
                    importance="MEDIUM",
                    suggested_answer=task_desc.effort_estimate.value,
                    confidence=effort_meta.confidence
                ))
                task_desc.effort_estimate = None

        # Check primary_project
        if task_desc.primary_project:
            project_meta = next(
                (m for m in task_desc.auto_fill_metadata if m.field_name == "primary_project"),
                None
            )
            if project_meta and project_meta.confidence < CONFIDENCE_THRESHOLDS["primary_project"]:
                new_gaps.append(ContextGap(
                    field_name="primary_project",
                    question=f"Which project does this belong to? (Suggested: {task_desc.primary_project})",
                    importance="MEDIUM",
                    suggested_answer=task_desc.primary_project,
                    confidence=project_meta.confidence
                ))
                task_desc.primary_project = None

        # Check suggested_assignee
        if task_desc.suggested_assignee:
            assignee_meta = next(
                (m for m in task_desc.auto_fill_metadata if m.field_name == "suggested_assignee"),
                None
            )
            if assignee_meta and assignee_meta.confidence < CONFIDENCE_THRESHOLDS["suggested_assignee"]:
                new_gaps.append(ContextGap(
                    field_name="suggested_assignee",
                    question=f"Who should work on this? (Suggested: {task_desc.suggested_assignee})",
                    importance="LOW",
                    suggested_answer=task_desc.suggested_assignee,
                    confidence=assignee_meta.confidence
                ))
                task_desc.suggested_assignee = None

        # Add new gaps to existing context_gaps
        task_desc.context_gaps.extend(new_gaps)

        return result

    # ========================================================================
    # QUALITY METRICS
    # ========================================================================

    def _calculate_quality_metrics(
        self,
        task_desc: IntelligentTaskDescription
    ) -> TaskDescriptionQuality:
        """
        Calculate quality metrics for synthesized task description.

        Metrics:
        - Completeness: % of Tier 2 sections populated
        - Richness: Total word count in expandable sections
        - Actionability: Has focus areas
        - Context depth: Has related tasks/stakeholders
        - Auto-fill success: % auto-filled vs questions
        """

        # Count populated sections
        sections_populated = 0
        sections_total = 4  # why_it_matters, what_was_discussed, how_to_approach, related_work

        if task_desc.why_it_matters:
            sections_populated += 1
        if task_desc.what_was_discussed:
            sections_populated += 1
        if task_desc.how_to_approach:
            sections_populated += 1
        if task_desc.related_work:
            sections_populated += 1

        # Calculate total word count
        total_words = 0
        if task_desc.why_it_matters:
            total_words += len(task_desc.why_it_matters.business_value.split())
            total_words += len(task_desc.why_it_matters.user_impact.split())
            if task_desc.why_it_matters.urgency_reason:
                total_words += len(task_desc.why_it_matters.urgency_reason.split())

        if task_desc.how_to_approach:
            for focus in task_desc.how_to_approach.focus_areas:
                total_words += len(focus.split())
            if task_desc.how_to_approach.lessons_from_similar:
                total_words += len(task_desc.how_to_approach.lessons_from_similar.split())

        # Check actionability
        has_focus_areas = (
            task_desc.how_to_approach is not None and
            len(task_desc.how_to_approach.focus_areas) > 0
        )

        # Check context depth
        has_related_tasks = (
            task_desc.related_work is not None and
            (len(task_desc.related_work.similar_tasks) > 0 or
             len(task_desc.related_work.blocking_tasks) > 0)
        )
        has_stakeholders = (
            task_desc.related_work is not None and
            len(task_desc.related_work.stakeholders) > 0
        )

        # Count auto-fill success
        fields_auto_filled = sum(
            1 for m in task_desc.auto_fill_metadata
            if m.auto_filled
        )
        fields_with_questions = len([
            gap for gap in task_desc.context_gaps
            if gap.field_name in ["priority", "effort_estimate", "primary_project", "suggested_assignee"]
        ])

        auto_fill_success_rate = 0.0
        total_fillable_fields = fields_auto_filled + fields_with_questions
        if total_fillable_fields > 0:
            auto_fill_success_rate = fields_auto_filled / total_fillable_fields

        # Create quality object (validators will auto-calculate scores)
        quality = TaskDescriptionQuality(
            task_id="",  # Will be set when task is created
            sections_populated=sections_populated,
            sections_total=sections_total,
            completeness_score=0.0,  # Auto-calculated by validator
            total_word_count=total_words,
            richness_score=0.0,  # Auto-calculated
            has_focus_areas=has_focus_areas,
            actionability_score=1.0 if has_focus_areas else 0.0,
            has_related_tasks=has_related_tasks,
            has_stakeholders=has_stakeholders,
            context_depth_score=0.0,  # Auto-calculated
            fields_auto_filled=fields_auto_filled,
            fields_with_questions=fields_with_questions,
            auto_fill_success_rate=auto_fill_success_rate,
            overall_quality=0.0  # Auto-calculated
        )

        return quality

    # ========================================================================
    # FALLBACK
    # ========================================================================

    def _create_fallback_task(self, raw_input: str) -> TaskSynthesisResult:
        """
        Create basic task description when synthesis fails.

        This ensures we always return something usable, even if AI fails.
        All fields become context gaps.
        """
        logger.warning("Using fallback task creation")

        # Create basic summary from raw input (truncate if too long)
        words = raw_input.split()
        if len(words) > 75:
            summary = " ".join(words[:75]) + "..."
        else:
            summary = raw_input

        # Pad summary if too short
        if len(words) < 50:
            summary += " (Please provide more details about this task.)"

        # Create basic task with all fields as gaps
        task_desc = IntelligentTaskDescription(
            title=raw_input[:100] if len(raw_input) > 100 else raw_input,
            summary=summary,
            context_gaps=[
                ContextGap(
                    field_name="priority",
                    question="What is the priority of this task?",
                    importance="HIGH",
                    confidence=0.0
                ),
                ContextGap(
                    field_name="effort_estimate",
                    question="How much effort will this take?",
                    importance="MEDIUM",
                    confidence=0.0
                ),
                ContextGap(
                    field_name="primary_project",
                    question="Which project does this belong to?",
                    importance="MEDIUM",
                    confidence=0.0
                ),
                ContextGap(
                    field_name="details",
                    question="Can you provide more details about what needs to be done and why?",
                    importance="HIGH",
                    confidence=0.0
                )
            ]
        )

        return TaskSynthesisResult(
            task_description=task_desc,
            synthesis_reasoning="Fallback mode: AI synthesis failed, created basic task with context gaps",
            confidence_overall=0.1
        )


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

async def get_task_synthesizer(db: AsyncSession) -> TaskSynthesizerService:
    """Factory function to get task synthesizer instance."""
    return TaskSynthesizerService(db)
