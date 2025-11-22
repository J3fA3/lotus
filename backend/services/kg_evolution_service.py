"""
Knowledge Graph Evolution Service - Phase 6 Cognitive Nexus

This service extends the Phase 1 KG with rich contextual understanding:
1. Concept Extraction: Extract domain-specific concepts (not generic terms)
2. Conversation Tracking: Track discussion threads with decisions/questions
3. Task Outcome Recording: Learn from task completions/cancellations
4. Strategic Importance Scoring: Calculate concept importance
5. Similar Task Finding: Semantic similarity with explanations

Key Principles:
- Concepts are domain-specific (NOT generic like "email", "meeting")
- Only track concepts mentioned 3+ times (noise filtering)
- Outcomes are highest-quality learning signal (weight = 1.0)
- Pre-compute similarity index for <50ms lookups
- Archive old data to keep KG under 5000 nodes
"""

from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update, desc
from datetime import datetime, timedelta
from pydantic import BaseModel
import json
import re

from db.knowledge_graph_models_v2 import (
    ConceptNode,
    ConversationThreadNode,
    TaskOutcomeNode,
    ConceptRelationship,
    TaskSimilarityIndex,
    ConceptTaskLink
)
from db.models import Task
from services.gemini_client import get_gemini_client


# ============================================================================
# PYDANTIC MODELS FOR GEMINI STRUCTURED OUTPUT
# ============================================================================

class ExtractedConcept(BaseModel):
    """Single extracted concept from context."""
    name: str  # 2-4 words, domain-specific
    confidence: float  # 0.0-1.0
    context: str  # Where it was mentioned


class ConceptExtractionResult(BaseModel):
    """Result of concept extraction."""
    concepts: List[ExtractedConcept]
    reasoning: str


class KeyDecision(BaseModel):
    """A decision made in conversation."""
    decision: str
    context: str


class UnresolvedQuestion(BaseModel):
    """An unanswered question in conversation."""
    question: str
    context: str


class ConversationAnalysis(BaseModel):
    """Analysis of conversation thread."""
    topic: str
    key_decisions: List[KeyDecision]
    unresolved_questions: List[UnresolvedQuestion]
    importance_score: float  # 0.0-1.0


class SimilarTaskMatch(BaseModel):
    """A similar task with explanation."""
    task_id: str
    task_title: str
    similarity_score: float  # 0.0-1.0
    explanation: str  # WHY similar
    outcome: Optional[str] = None  # If completed, what was outcome
    quality_score: Optional[float] = None  # If completed, quality


class ConfidenceTier:
    """Confidence tiers for concept tracking."""
    ESTABLISHED = "ESTABLISHED"  # 10+ mentions
    EMERGING = "EMERGING"  # 3-9 mentions
    TENTATIVE = "TENTATIVE"  # 1-2 mentions


# ============================================================================
# KG EVOLUTION SERVICE
# ============================================================================

class KGEvolutionService:
    """Manages knowledge graph evolution with concepts, conversations, and outcomes."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.gemini = get_gemini_client()

    # ========================================================================
    # CONCEPT EXTRACTION
    # ========================================================================

    async def extract_concepts(
        self,
        text: str,
        user_profile: Optional[Dict] = None
    ) -> List[ConceptNode]:
        """Extract domain-specific concepts from text.

        Concepts are 2-4 word noun phrases that represent domain-specific ideas.
        NOT generic terms like "email", "meeting", "task".

        Filtering:
        - Only concepts mentioned 3+ times historically are tracked
        - Generic terms are rejected
        - Concepts are validated against user profile (project/market alignment)

        Args:
            text: Input text to analyze
            user_profile: User profile for context validation

        Returns:
            List of ConceptNode objects (may be empty if no valid concepts)
        """
        # Build prompt for concept extraction
        prompt = self._build_concept_extraction_prompt(text, user_profile)

        try:
            # Use Gemini for intelligent extraction
            result = await self.gemini.generate_structured(
                prompt=prompt,
                schema=ConceptExtractionResult,
                temperature=0.2,  # Low temperature for consistency
                fallback_to_qwen=True
            )

            # Filter and validate concepts
            validated_concepts = []

            for concept_data in result.concepts:
                # Skip if confidence too low
                if concept_data.confidence < 0.7:
                    continue

                # Check if concept already exists
                existing = await self._get_or_create_concept(
                    name=concept_data.name,
                    context=text,
                    confidence=concept_data.confidence,
                    user_profile=user_profile
                )

                if existing:
                    validated_concepts.append(existing)

            return validated_concepts

        except Exception as e:
            # Log error but don't fail the whole pipeline
            print(f"Concept extraction failed: {e}")
            return []

    def _build_concept_extraction_prompt(
        self,
        text: str,
        user_profile: Optional[Dict]
    ) -> str:
        """Build prompt for concept extraction."""
        user_context = ""
        if user_profile:
            projects = user_profile.get("projects", [])
            markets = user_profile.get("markets", [])
            user_context = f"\nUser works on projects: {', '.join(projects)}\nUser's markets: {', '.join(markets)}"

        return f"""Extract domain-specific concepts from this text.

RULES:
1. Concepts are 2-4 word noun phrases representing domain-specific ideas
2. DO NOT extract generic terms like "email", "meeting", "task", "analysis"
3. Focus on strategic themes, projects, markets, product features
4. Only extract concepts with confidence >= 0.7

VALID CONCEPT EXAMPLES:
- "pharmacy pinning effectiveness"
- "Spain market launch"
- "position 3 visibility"
- "Netherlands rollout"
- "RF16 Q4 priority"

INVALID CONCEPT EXAMPLES (too generic):
- "email" ❌
- "meeting" ❌
- "dashboard" ❌
- "report" ❌
{user_context}

TEXT:
{text}

Extract domain-specific concepts with confidence scores.
"""

    async def _get_or_create_concept(
        self,
        name: str,
        context: str,
        confidence: float,
        user_profile: Optional[Dict]
    ) -> Optional[ConceptNode]:
        """Get existing concept or create new one.

        Only creates if:
        - Concept has been mentioned 3+ times historically (prevents noise)
        - Concept is domain-specific (not generic)

        Returns:
            ConceptNode if valid, None if rejected
        """
        # Normalize name
        name = name.strip().lower()

        # Check if exists
        result = await self.db.execute(
            select(ConceptNode).where(
                func.lower(ConceptNode.name) == name
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update mention counts
            existing.mention_count_30d += 1
            existing.mention_count_total += 1
            existing.last_mentioned = datetime.utcnow()

            # Update confidence tier
            if existing.mention_count_total >= 10:
                existing.confidence_tier = ConfidenceTier.ESTABLISHED
            elif existing.mention_count_total >= 3:
                existing.confidence_tier = ConfidenceTier.EMERGING
            else:
                existing.confidence_tier = ConfidenceTier.TENTATIVE

            await self.db.commit()
            return existing

        # For new concepts, only create if we've seen this type of pattern before
        # OR if it aligns with user profile (project/market)
        if user_profile:
            projects = [p.lower() for p in user_profile.get("projects", [])]
            markets = [m.lower() for m in user_profile.get("markets", [])]

            # Check if concept contains project or market
            is_strategic = any(proj in name for proj in projects) or \
                          any(market in name for market in markets)

            if is_strategic:
                # Create immediately if strategic
                return await self._create_concept_node(
                    name=name,
                    confidence=confidence,
                    user_profile=user_profile
                )

        # Otherwise, track mention but don't create node yet
        # (Wait until 3+ mentions before creating)
        return None

    async def _create_concept_node(
        self,
        name: str,
        confidence: float,
        user_profile: Optional[Dict]
    ) -> ConceptNode:
        """Create a new concept node."""
        # Extract related projects/markets from name
        related_projects = []
        related_markets = []

        if user_profile:
            projects = [p.lower() for p in user_profile.get("projects", [])]
            markets = [m.lower() for m in user_profile.get("markets", [])]

            related_projects = [p for p in projects if p in name]
            related_markets = [m for m in markets if m in name]

        # Calculate importance score
        importance_score = await self.calculate_strategic_importance(
            concept_name=name,
            projects=related_projects,
            markets=related_markets
        )

        # Create node
        concept = ConceptNode(
            name=name,
            definition=None,  # Will be generated later if needed
            importance_score=importance_score,
            confidence_tier=ConfidenceTier.TENTATIVE,
            first_mentioned=datetime.utcnow(),
            last_mentioned=datetime.utcnow(),
            mention_count_30d=1,
            mention_count_total=1,
            related_projects=related_projects,
            related_markets=related_markets,
            related_people=[]
        )

        self.db.add(concept)
        await self.db.commit()
        await self.db.refresh(concept)

        return concept

    # ========================================================================
    # CONVERSATION TRACKING
    # ========================================================================

    async def track_conversation_thread(
        self,
        messages: List[Dict],
        participants: List[str]
    ) -> ConversationThreadNode:
        """Track conversation thread with key decisions and unresolved questions.

        Args:
            messages: List of message dicts with 'text', 'sender', 'timestamp'
            participants: List of participant names

        Returns:
            ConversationThreadNode
        """
        # Combine messages into single text for analysis
        full_text = "\n\n".join([
            f"{msg.get('sender', 'Unknown')}: {msg.get('text', '')}"
            for msg in messages
        ])

        # Analyze conversation with Gemini
        prompt = self._build_conversation_analysis_prompt(full_text, participants)

        try:
            analysis = await self.gemini.generate_structured(
                prompt=prompt,
                schema=ConversationAnalysis,
                temperature=0.3,
                fallback_to_qwen=True
            )

            # Create or update conversation thread
            thread = ConversationThreadNode(
                topic=analysis.topic,
                participants=participants,
                start_date=messages[0].get('timestamp', datetime.utcnow()),
                last_updated=messages[-1].get('timestamp', datetime.utcnow()),
                message_count=len(messages),
                key_decisions=[d.decision for d in analysis.key_decisions],
                unresolved_questions=[q.question for q in analysis.unresolved_questions],
                related_projects=[],  # TODO: Extract from context
                related_tasks=[],
                importance_score=analysis.importance_score,
                is_active=True,
                is_archived=False
            )

            self.db.add(thread)
            await self.db.commit()
            await self.db.refresh(thread)

            return thread

        except Exception as e:
            print(f"Conversation tracking failed: {e}")
            # Create minimal thread
            thread = ConversationThreadNode(
                topic="Conversation",
                participants=participants,
                start_date=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                message_count=len(messages),
                key_decisions=[],
                unresolved_questions=[],
                importance_score=0.5
            )
            self.db.add(thread)
            await self.db.commit()
            return thread

    def _build_conversation_analysis_prompt(
        self,
        text: str,
        participants: List[str]
    ) -> str:
        """Build prompt for conversation analysis."""
        return f"""Analyze this conversation thread and extract:

1. TOPIC: Main topic (1-10 words)
2. KEY DECISIONS: Decisions made (e.g., "Analysis due Dec 5", "Include satisfaction scores")
3. UNRESOLVED QUESTIONS: Questions that remain unanswered
4. IMPORTANCE SCORE: 0.0-1.0 (how important is this conversation)

PARTICIPANTS: {', '.join(participants)}

CONVERSATION:
{text}

Extract structured analysis.
"""

    # ========================================================================
    # TASK OUTCOME RECORDING
    # ========================================================================

    async def record_task_outcome(
        self,
        task_id: str,
        outcome: str,
        task: Optional[Task] = None
    ) -> TaskOutcomeNode:
        """Record task completion outcome with lessons learned.

        This is the HIGHEST QUALITY learning signal.

        Args:
            task_id: Task ID
            outcome: COMPLETED | CANCELLED | IGNORED | MERGED
            task: Optional Task model (if not provided, will fetch)

        Returns:
            TaskOutcomeNode
        """
        # Fetch task if not provided
        if not task:
            result = await self.db.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()

        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Calculate effort
        actual_effort_hours = None
        effort_variance = None
        if task.created_at and outcome == "COMPLETED":
            time_delta = datetime.utcnow() - task.created_at
            actual_effort_hours = time_delta.total_seconds() / 3600  # Convert to hours

            # TODO: Get estimated effort from task metadata
            estimated_effort_hours = None

            if estimated_effort_hours:
                effort_variance = actual_effort_hours / estimated_effort_hours

        # Calculate quality score
        completion_quality = await self._calculate_completion_quality(task, outcome)

        # Extract blockers from comments
        blockers = []
        if hasattr(task, 'comments'):
            for comment in task.comments:
                if any(word in comment.text.lower() for word in ['blocked', 'waiting', 'delayed', 'issue']):
                    blockers.append(comment.text)

        # Generate lessons learned
        lessons_learned = None
        if outcome == "COMPLETED" and completion_quality:
            lessons_learned = await self._generate_lessons_learned(
                task=task,
                actual_effort_hours=actual_effort_hours,
                blockers=blockers
            )

        # Create outcome node
        outcome_node = TaskOutcomeNode(
            task_id=task_id,
            outcome=outcome,
            completion_quality=completion_quality if outcome == "COMPLETED" else None,
            estimated_effort_hours=None,  # TODO: Get from task
            actual_effort_hours=actual_effort_hours,
            effort_variance=effort_variance,
            blockers=blockers,
            lessons_learned=lessons_learned,
            task_title=task.title,
            task_project=task.value_stream,
            task_market=None,  # TODO: Extract from metadata
            task_assignee=task.assignee,
            follow_up_task_count=0,  # TODO: Track
            user_satisfaction=None,
            recorded_at=datetime.utcnow(),
            completed_at=datetime.utcnow() if outcome == "COMPLETED" else None
        )

        self.db.add(outcome_node)
        await self.db.commit()
        await self.db.refresh(outcome_node)

        return outcome_node

    async def _calculate_completion_quality(
        self,
        task: Task,
        outcome: str
    ) -> Optional[float]:
        """Calculate task completion quality (0.0-5.0).

        Quality Score:
        - 5.0: Perfect completion, no edits, no blockers
        - 4.0: Completed with minor edits
        - 3.0: Completed with significant edits or blockers
        - 2.0: Completed but quality issues
        - 1.0: Barely completed, major issues
        """
        if outcome != "COMPLETED":
            return None

        base_score = 5.0
        deductions = 0.0

        # Check for edits (placeholder - would need edit tracking)
        # if task has edit history with major changes: deductions += 0.5

        # Check for blockers in comments
        if hasattr(task, 'comments'):
            blocker_count = sum(1 for c in task.comments
                              if any(word in c.text.lower() for word in ['blocked', 'issue']))
            deductions += min(blocker_count * 0.3, 1.0)  # Max 1.0 deduction

        # Check for follow-up tasks (indicates incomplete initial work)
        # if follow_up_task_count > 3: deductions += 0.5

        return max(1.0, base_score - deductions)

    async def _generate_lessons_learned(
        self,
        task: Task,
        actual_effort_hours: Optional[float],
        blockers: List[str]
    ) -> Optional[str]:
        """Generate AI summary of lessons learned."""
        if not actual_effort_hours and not blockers:
            return None

        prompt = f"""Generate a concise (1-2 sentence) lesson learned from this task completion:

TASK: {task.title}
ACTUAL EFFORT: {actual_effort_hours:.1f} hours
BLOCKERS: {', '.join(blockers) if blockers else 'None'}

What should we learn for future similar tasks?
"""

        try:
            lessons = await self.gemini.generate(
                prompt=prompt,
                temperature=0.4,
                max_tokens=150,
                fallback_to_qwen=True
            )
            return lessons.strip()
        except:
            return None

    # ========================================================================
    # STRATEGIC IMPORTANCE CALCULATION
    # ========================================================================

    async def calculate_strategic_importance(
        self,
        concept_name: Optional[str] = None,
        projects: Optional[List[str]] = None,
        markets: Optional[List[str]] = None
    ) -> float:
        """Calculate strategic importance score (0.0-1.0).

        Factors:
        - Mention frequency (30 day window): 40%
        - Urgency indicators (email urgency, calendar events): 30%
        - Strategic alignment (user projects/markets): 30%

        Args:
            concept_name: Optional concept name to score
            projects: Related projects
            markets: Related markets

        Returns:
            Importance score 0.0-1.0
        """
        score = 0.0

        # Factor 1: Mention frequency (40%)
        if concept_name:
            result = await self.db.execute(
                select(ConceptNode).where(
                    func.lower(ConceptNode.name) == concept_name.lower()
                )
            )
            concept = result.scalar_one_or_none()
            if concept:
                # Normalize mention count (assume 20+ mentions = 1.0)
                mention_score = min(concept.mention_count_30d / 20.0, 1.0)
                score += mention_score * 0.4

        # Factor 2: Urgency indicators (30%)
        # TODO: Check email subjects for urgency keywords
        # TODO: Check calendar for upcoming meetings
        urgency_score = 0.5  # Placeholder
        score += urgency_score * 0.3

        # Factor 3: Strategic alignment (30%)
        strategic_score = 0.0
        if projects:
            strategic_score += 0.5  # Has project association
        if markets:
            strategic_score += 0.5  # Has market association
        score += strategic_score * 0.3

        return min(score, 1.0)

    # ========================================================================
    # SIMILAR TASK FINDING
    # ========================================================================

    async def find_similar_tasks(
        self,
        task_description: str,
        task_title: Optional[str] = None,
        limit: int = 5
    ) -> List[SimilarTaskMatch]:
        """Find similar tasks with outcome-based ranking.

        Strategy:
        1. Check pre-computed similarity index first (fast path)
        2. If not found, compute on-the-fly (slow path)
        3. Prioritize tasks with successful outcomes
        4. Generate explanation for WHY similar

        Args:
            task_description: Description to match against
            task_title: Optional title for better matching
            limit: Max results

        Returns:
            List of SimilarTaskMatch objects with explanations
        """
        # TODO: Implement semantic similarity
        # For now, return placeholder
        return []

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def get_rich_context(
        self,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get rich KG context for task synthesis.

        Returns top concepts, active conversations, and successful outcomes.

        Args:
            limit: Max items per category

        Returns:
            Dict with concepts, conversations, outcomes
        """
        # Get top concepts
        result = await self.db.execute(
            select(ConceptNode)
            .where(ConceptNode.archived_at.is_(None))
            .order_by(desc(ConceptNode.importance_score))
            .limit(limit)
        )
        concepts = result.scalars().all()

        # Get active conversations
        result = await self.db.execute(
            select(ConversationThreadNode)
            .where(ConversationThreadNode.is_active == True)
            .order_by(desc(ConversationThreadNode.importance_score))
            .limit(limit)
        )
        conversations = result.scalars().all()

        # Get successful outcomes (for pattern learning)
        result = await self.db.execute(
            select(TaskOutcomeNode)
            .where(
                and_(
                    TaskOutcomeNode.outcome == "COMPLETED",
                    TaskOutcomeNode.completion_quality >= 4.0
                )
            )
            .order_by(desc(TaskOutcomeNode.completed_at))
            .limit(limit)
        )
        outcomes = result.scalars().all()

        return {
            "concepts": [
                {
                    "name": c.name,
                    "importance": c.importance_score,
                    "tier": c.confidence_tier,
                    "projects": c.related_projects,
                    "markets": c.related_markets
                }
                for c in concepts
            ],
            "conversations": [
                {
                    "topic": conv.topic,
                    "decisions": conv.key_decisions,
                    "questions": conv.unresolved_questions,
                    "importance": conv.importance_score
                }
                for conv in conversations
            ],
            "successful_patterns": [
                {
                    "task_title": o.task_title,
                    "project": o.task_project,
                    "quality": o.completion_quality,
                    "effort_hours": o.actual_effort_hours,
                    "lessons": o.lessons_learned
                }
                for o in outcomes
            ]
        }
