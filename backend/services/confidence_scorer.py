"""
Confidence Scorer Service

This service calculates confidence scores for AI-proposed tasks based on:
1. Entity quality (how well entities were extracted)
2. Knowledge graph matches (does it match existing context?)
3. Clarity (is the input ambiguous or clear?)
4. Task field completeness (are all fields populated?)

Thresholds:
- >80%: Auto-approve (high confidence)
- 50-80%: Ask for user approval
- <50%: Ask clarifying questions

The confidence score directly influences the orchestrator's decision-making.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


# Confidence thresholds (can be overridden via environment variables)
CONFIDENCE_HIGH_THRESHOLD = 80.0  # Auto-approve above this
CONFIDENCE_LOW_THRESHOLD = 50.0   # Ask clarifying questions below this


@dataclass
class ConfidenceScore:
    """Confidence score with breakdown and recommendation.

    Attributes:
        overall_score: Final confidence score (0-100)
        factors: Breakdown of contributing factors
        recommendation: Decision recommendation ('auto', 'ask', 'clarify')
        reasoning: Human-readable explanation of the score
    """
    overall_score: float  # 0-100
    factors: Dict[str, float]  # Individual factor scores
    recommendation: str  # 'auto', 'ask', or 'clarify'
    reasoning: List[str]  # Explanation of score calculation


class ConfidenceScorer:
    """Calculates confidence scores for AI task operations.

    This service evaluates multiple signals to determine how confident
    the AI should be about a proposed task or enrichment operation.
    """

    def __init__(
        self,
        high_threshold: float = CONFIDENCE_HIGH_THRESHOLD,
        low_threshold: float = CONFIDENCE_LOW_THRESHOLD
    ):
        """Initialize confidence scorer with thresholds.

        Args:
            high_threshold: Auto-approve threshold (default 80.0)
            low_threshold: Clarify threshold (default 50.0)
        """
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold

    def calculate_confidence(
        self,
        entities: List[Dict],
        relationships: List[Dict],
        existing_task_matches: List[Dict],
        context_complexity: float,
        entity_quality: float,
        relationship_quality: float,
        task_quality: float,
        proposed_task: Optional[Dict] = None
    ) -> ConfidenceScore:
        """Calculate overall confidence score for a task operation.

        This method combines multiple signals into a single confidence score:
        1. Entity Quality (30%): How well were entities extracted?
        2. Knowledge Graph Matches (25%): Does this align with existing knowledge?
        3. Clarity (25%): Is the input clear and unambiguous?
        4. Task Field Completeness (20%): Are all important fields populated?

        Args:
            entities: Extracted entities from context
            relationships: Inferred relationships
            existing_task_matches: Tasks that match entities/relationships
            context_complexity: Complexity score from context analysis (0-1)
            entity_quality: Quality score from entity extraction (0-1)
            relationship_quality: Quality score from relationship synthesis (0-1)
            task_quality: Quality score from task integration (0-1)
            proposed_task: Task that will be created/enriched (optional)

        Returns:
            ConfidenceScore with overall score, factor breakdown, and recommendation
        """
        reasoning = []
        factors = {}

        # Factor 1: Entity Quality (30% weight)
        # High quality entity extraction indicates clear, actionable input
        entity_score = self._calculate_entity_quality_score(
            entities, entity_quality, reasoning
        )
        factors["entity_quality"] = entity_score

        # Factor 2: Knowledge Graph Matches (25% weight)
        # Strong matches with existing knowledge increase confidence
        kg_score = self._calculate_kg_match_score(
            existing_task_matches, entities, relationships, reasoning
        )
        factors["kg_matches"] = kg_score

        # Factor 3: Clarity (25% weight)
        # Low complexity + high quality = high clarity
        clarity_score = self._calculate_clarity_score(
            context_complexity, entity_quality, relationship_quality, reasoning
        )
        factors["clarity"] = clarity_score

        # Factor 4: Task Field Completeness (20% weight)
        # More complete task data = higher confidence
        completeness_score = self._calculate_completeness_score(
            proposed_task, task_quality, reasoning
        )
        factors["completeness"] = completeness_score

        # Calculate weighted overall score (0-100)
        overall_score = (
            entity_score * 0.30 +
            kg_score * 0.25 +
            clarity_score * 0.25 +
            completeness_score * 0.20
        )

        reasoning.append(f"→ Overall confidence: {overall_score:.1f}%")

        # Determine recommendation based on thresholds
        if overall_score >= self.high_threshold:
            recommendation = "auto"
            reasoning.append(
                f"→ Recommendation: AUTO-APPROVE (score >= {self.high_threshold}%)"
            )
        elif overall_score >= self.low_threshold:
            recommendation = "ask"
            reasoning.append(
                f"→ Recommendation: ASK USER for approval "
                f"(score between {self.low_threshold}% and {self.high_threshold}%)"
            )
        else:
            recommendation = "clarify"
            reasoning.append(
                f"→ Recommendation: ASK CLARIFYING QUESTIONS (score < {self.low_threshold}%)"
            )

        return ConfidenceScore(
            overall_score=round(overall_score, 1),
            factors={k: round(v, 1) for k, v in factors.items()},
            recommendation=recommendation,
            reasoning=reasoning
        )

    def _calculate_entity_quality_score(
        self,
        entities: List[Dict],
        entity_quality: float,
        reasoning: List[str]
    ) -> float:
        """Calculate entity quality factor score (0-100).

        Considers:
        - Quality score from entity extraction agent
        - Number of entities found (more entities = more context)
        - Entity type diversity (people + projects + dates = better)

        Args:
            entities: Extracted entities
            entity_quality: Quality score from extraction (0-1)
            reasoning: List to append reasoning steps

        Returns:
            Score from 0-100
        """
        # Base score from extraction quality
        base_score = entity_quality * 100

        # Boost for having multiple entities (more context)
        entity_count = len(entities)
        if entity_count >= 5:
            base_score = min(base_score + 10, 100)
            reasoning.append(f"  • Entity quality: {entity_quality:.2f} + bonus for {entity_count} entities → {base_score:.1f}%")
        elif entity_count >= 3:
            base_score = min(base_score + 5, 100)
            reasoning.append(f"  • Entity quality: {entity_quality:.2f} + small bonus for {entity_count} entities → {base_score:.1f}%")
        else:
            reasoning.append(f"  • Entity quality: {entity_quality:.2f} (only {entity_count} entities) → {base_score:.1f}%")

        # Boost for entity type diversity
        entity_types = {e.get("type") for e in entities}
        if len(entity_types) >= 3:  # Person + Project + Date
            base_score = min(base_score + 5, 100)
            reasoning.append(f"  • Entity diversity bonus: {len(entity_types)} types → +5%")

        return min(base_score, 100)

    def _calculate_kg_match_score(
        self,
        existing_task_matches: List[Dict],
        entities: List[Dict],
        relationships: List[Dict],
        reasoning: List[str]
    ) -> float:
        """Calculate knowledge graph match factor score (0-100).

        Considers:
        - Number of matching existing tasks
        - Strength of matches (similarity scores)
        - Whether entities are already in knowledge graph

        Args:
            existing_task_matches: Tasks matching the context
            entities: Extracted entities
            relationships: Inferred relationships
            reasoning: List to append reasoning steps

        Returns:
            Score from 0-100
        """
        score = 0.0

        # Factor 1: Existing task matches
        if existing_task_matches:
            match_count = len(existing_task_matches)
            # Average match strength (if available)
            avg_similarity = sum(
                m.get("similarity", 0.5) for m in existing_task_matches
            ) / match_count

            # High similarity to existing tasks = high confidence
            score = avg_similarity * 100
            reasoning.append(
                f"  • Knowledge graph: {match_count} task matches "
                f"(avg similarity: {avg_similarity:.2f}) → {score:.1f}%"
            )
        else:
            # No existing matches - neutral score (50%)
            # This is okay - new tasks should be created!
            score = 50.0
            reasoning.append("  • Knowledge graph: No existing task matches → 50% (neutral)")

        # Factor 2: Relationship strength
        # More relationships = more connected context = higher confidence
        if relationships:
            rel_boost = min(len(relationships) * 5, 20)  # Max +20%
            score = min(score + rel_boost, 100)
            reasoning.append(f"  • Relationship boost: {len(relationships)} relationships → +{rel_boost}%")

        return min(score, 100)

    def _calculate_clarity_score(
        self,
        context_complexity: float,
        entity_quality: float,
        relationship_quality: float,
        reasoning: List[str]
    ) -> float:
        """Calculate clarity factor score (0-100).

        Clarity = inverse of complexity + quality indicators

        Clear input:
        - Low complexity (simple, straightforward)
        - High entity quality (entities easy to extract)
        - High relationship quality (relationships clear)

        Args:
            context_complexity: Complexity from context analysis (0-1, higher = more complex)
            entity_quality: Entity extraction quality (0-1)
            relationship_quality: Relationship synthesis quality (0-1)
            reasoning: List to append reasoning steps

        Returns:
            Score from 0-100
        """
        # Inverse of complexity (low complexity = high clarity)
        complexity_clarity = (1.0 - context_complexity) * 100

        # Quality indicators
        quality_clarity = ((entity_quality + relationship_quality) / 2) * 100

        # Average of both signals
        clarity_score = (complexity_clarity + quality_clarity) / 2

        reasoning.append(
            f"  • Clarity: complexity={context_complexity:.2f} (inverted={complexity_clarity:.1f}%), "
            f"quality avg={quality_clarity:.1f}% → {clarity_score:.1f}%"
        )

        return clarity_score

    def _calculate_completeness_score(
        self,
        proposed_task: Optional[Dict],
        task_quality: float,
        reasoning: List[str]
    ) -> float:
        """Calculate task field completeness score (0-100).

        Checks if proposed task has all important fields populated:
        - Title (required)
        - Description (important)
        - Assignee (important)
        - Due date (nice to have)
        - Priority (nice to have)
        - Tags/project (nice to have)

        Args:
            proposed_task: Task data that will be created
            task_quality: Quality score from task integration (0-1)
            reasoning: List to append reasoning steps

        Returns:
            Score from 0-100
        """
        if not proposed_task:
            # No task proposed yet - use task quality from integration agent
            score = task_quality * 100
            reasoning.append(f"  • Completeness: Task quality = {score:.1f}%")
            return score

        # Check field presence
        required_fields = ["title"]
        important_fields = ["description", "assignee"]
        nice_to_have_fields = ["due_date", "priority", "tags", "value_stream", "project"]

        required_present = sum(
            1 for field in required_fields if proposed_task.get(field)
        )
        important_present = sum(
            1 for field in important_fields if proposed_task.get(field)
        )
        nice_to_have_present = sum(
            1 for field in nice_to_have_fields if proposed_task.get(field)
        )

        # Calculate weighted score
        # Required: 40%, Important: 40%, Nice-to-have: 20%
        required_score = (required_present / max(len(required_fields), 1)) * 40
        important_score = (important_present / max(len(important_fields), 1)) * 40
        nice_score = (nice_to_have_present / max(len(nice_to_have_fields), 1)) * 20

        completeness_score = required_score + important_score + nice_score

        reasoning.append(
            f"  • Completeness: required={required_present}/{len(required_fields)}, "
            f"important={important_present}/{len(important_fields)}, "
            f"nice={nice_to_have_present}/{len(nice_to_have_fields)} → {completeness_score:.1f}%"
        )

        return completeness_score


def should_auto_approve(confidence_score: ConfidenceScore) -> bool:
    """Helper function to check if a confidence score warrants auto-approval.

    Args:
        confidence_score: ConfidenceScore object

    Returns:
        True if should auto-approve, False otherwise
    """
    return confidence_score.recommendation == "auto"


def should_ask_user(confidence_score: ConfidenceScore) -> bool:
    """Helper function to check if a confidence score requires user approval.

    Args:
        confidence_score: ConfidenceScore object

    Returns:
        True if should ask user, False otherwise
    """
    return confidence_score.recommendation == "ask"


def should_ask_clarification(confidence_score: ConfidenceScore) -> bool:
    """Helper function to check if a confidence score requires clarifying questions.

    Args:
        confidence_score: ConfidenceScore object

    Returns:
        True if should ask for clarification, False otherwise
    """
    return confidence_score.recommendation == "clarify"
