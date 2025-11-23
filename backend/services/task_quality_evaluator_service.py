"""
Task Quality Evaluator Service - Phase 6 Stage 6

Evaluates the quality of AI-generated task descriptions across 5 dimensions.

Design Decisions:
1. Lightweight metrics: No heavy NLP (performance), use rule-based scoring
2. Evidence-based weights: Completeness 30%, Clarity 25%, Actionability 25%, Relevance 15%, Confidence 5%
3. Actionable feedback: Generate specific suggestions with impact estimates
4. Fail-safe evaluation: Errors default to conservative scores (not crashes)
5. Performance target: <50ms per evaluation (no blocking)

Quality Dimensions:
- Completeness: Are critical sections filled? (has_how_to_approach, success_criteria, etc.)
- Clarity: Is it understandable? (word count, structure, readability)
- Actionability: Can user act on it? (has steps, criteria, specificity)
- Relevance: Contextually appropriate? (KG concepts, project alignment)
- Confidence: How confident is the AI? (avg confidence, consistency)

This builds user trust through transparency and measurable quality.
"""

import logging
import re
from typing import Dict, Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import time

logger = logging.getLogger(__name__)


# ============================================================================
# TASK QUALITY EVALUATOR SERVICE
# ============================================================================

class TaskQualityEvaluatorService:
    """
    Service for evaluating task description quality.

    Provides transparent, measurable quality metrics to build user trust.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

        # Quality weights
        self.COMPLETENESS_WEIGHT = 0.30
        self.CLARITY_WEIGHT = 0.25
        self.ACTIONABILITY_WEIGHT = 0.25
        self.RELEVANCE_WEIGHT = 0.15
        self.CONFIDENCE_WEIGHT = 0.05

        # Critical sections (high-impact from outcome learning)
        self.CRITICAL_SECTIONS = {
            "has_how_to_approach": 15,  # Reduces completion time by 30%
            "has_success_criteria": 15,  # Improves success rates
            "has_why_it_matters": 10,
            "has_summary": 10,
            "has_technical_context": 10
        }

        # Optimal ranges
        self.OPTIMAL_WORD_COUNT_MIN = 200
        self.OPTIMAL_WORD_COUNT_MAX = 500
        self.OPTIMAL_STEP_COUNT_MIN = 4
        self.OPTIMAL_STEP_COUNT_MAX = 7
        self.OPTIMAL_CONCEPT_COUNT_MIN = 4
        self.OPTIMAL_CONCEPT_COUNT_MAX = 7

    # ========================================================================
    # MAIN EVALUATION
    # ========================================================================

    async def evaluate_task_quality(
        self,
        task_id: str,
        intelligent_description: Optional[Dict] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Evaluate task description quality across all dimensions.

        Args:
            task_id: Task ID
            intelligent_description: Task description data
            user_id: User who created the task
            project_id: Project context

        Returns:
            Quality evaluation dict with scores, metrics, suggestions
        """
        start_time = time.time()

        try:
            # If no description provided, fetch from database
            if not intelligent_description:
                intelligent_description = await self._fetch_task_description(task_id)

            if not intelligent_description:
                logger.warning(f"No description found for task {task_id}")
                return None

            # Evaluate each dimension
            completeness_result = self._evaluate_completeness(intelligent_description)
            clarity_result = self._evaluate_clarity(intelligent_description)
            actionability_result = self._evaluate_actionability(intelligent_description)
            relevance_result = await self._evaluate_relevance(
                intelligent_description,
                project_id=project_id
            )
            confidence_result = self._evaluate_confidence(intelligent_description)

            # Calculate overall score
            overall_score = self._calculate_overall_score(
                completeness_result["score"],
                clarity_result["score"],
                actionability_result["score"],
                relevance_result["score"],
                confidence_result["score"]
            )

            # Classify quality tier
            from db.task_quality_models import classify_quality_tier
            quality_tier = classify_quality_tier(overall_score)

            # Generate suggestions and strengths
            suggestions = self._generate_suggestions(
                completeness_result,
                clarity_result,
                actionability_result,
                relevance_result,
                confidence_result
            )

            strengths = self._identify_strengths(
                completeness_result,
                clarity_result,
                actionability_result,
                relevance_result,
                confidence_result
            )

            # Compile quality metrics
            quality_metrics = {
                "completeness": completeness_result["metrics"],
                "clarity": clarity_result["metrics"],
                "actionability": actionability_result["metrics"],
                "relevance": relevance_result["metrics"],
                "confidence": confidence_result["metrics"]
            }

            evaluation_time_ms = int((time.time() - start_time) * 1000)

            # Build result
            result = {
                "task_id": task_id,
                "overall_score": overall_score,
                "quality_tier": quality_tier,
                "completeness_score": completeness_result["score"],
                "clarity_score": clarity_result["score"],
                "actionability_score": actionability_result["score"],
                "relevance_score": relevance_result["score"],
                "confidence_score": confidence_result["score"],
                "quality_metrics": quality_metrics,
                "suggestions": suggestions,
                "strengths": strengths,
                "evaluation_time_ms": evaluation_time_ms,
                "user_id": user_id,
                "project_id": project_id
            }

            # Save to database
            await self._save_quality_score(result)

            logger.info(
                f"Evaluated task {task_id}: {quality_tier} ({overall_score:.1f}) "
                f"in {evaluation_time_ms}ms"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to evaluate task quality: {e}")
            return None

    # ========================================================================
    # DIMENSION EVALUATORS
    # ========================================================================

    def _evaluate_completeness(self, description: Dict) -> Dict:
        """
        Evaluate completeness: Are critical sections filled?

        Scoring:
        - Base: field fill rate × 100
        - Bonuses for critical sections (high-impact from outcome learning)
        """
        metrics = {}
        score = 0.0

        # Count filled fields
        fields_to_check = [
            "summary", "why_it_matters", "how_to_approach",
            "success_criteria", "technical_context"
        ]

        filled_count = 0
        total_count = len(fields_to_check)

        for field in fields_to_check:
            field_value = description.get(field, "")
            is_filled = bool(field_value and len(str(field_value).strip()) > 10)
            metrics[f"has_{field}"] = is_filled
            if is_filled:
                filled_count += 1

        fill_rate = filled_count / total_count if total_count > 0 else 0.0
        metrics["fields_filled"] = filled_count
        metrics["fields_total"] = total_count
        metrics["fill_rate"] = fill_rate

        # Base score from fill rate
        score = fill_rate * 60  # 60 points max from fill rate

        # Critical section bonuses (evidence-based from outcome learning)
        for section, bonus in self.CRITICAL_SECTIONS.items():
            if metrics.get(section, False):
                score += bonus

        # Cap at 100
        score = min(100.0, score)

        return {
            "score": round(score, 2),
            "metrics": metrics
        }

    def _evaluate_clarity(self, description: Dict) -> Dict:
        """
        Evaluate clarity: Is it understandable?

        Factors:
        - Word count (optimal: 200-500 words)
        - Structure (uses lists, multiple paragraphs)
        - Readability (average sentence length)
        """
        metrics = {}
        score = 0.0

        # Combine all text
        all_text = " ".join([
            str(description.get("summary", "")),
            str(description.get("why_it_matters", "")),
            str(description.get("how_to_approach", "")),
            str(description.get("success_criteria", "")),
            str(description.get("technical_context", ""))
        ])

        # Word count
        word_count = len(all_text.split())
        metrics["word_count"] = word_count

        # Word count scoring
        if word_count < 100:
            word_score = 40  # Too brief
        elif word_count < 200:
            word_score = 70  # Minimal
        elif word_count <= 500:
            word_score = 100  # Optimal
        elif word_count <= 800:
            word_score = 85  # Verbose
        else:
            word_score = 60  # Too long

        score += word_score * 0.5  # 50% weight for word count

        # Structure analysis
        uses_lists = bool(re.search(r'[•\-\*\d+\.]\s', all_text))
        has_paragraphs = all_text.count('\n\n') > 0 or all_text.count('\n') > 2

        metrics["uses_lists"] = uses_lists
        metrics["has_structure"] = has_paragraphs

        structure_score = 0
        if uses_lists:
            structure_score += 50
        if has_paragraphs:
            structure_score += 50

        score += structure_score * 0.3  # 30% weight for structure

        # Readability (average sentence length)
        sentences = re.split(r'[.!?]+', all_text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            metrics["avg_sentence_length"] = round(avg_sentence_length, 1)

            if avg_sentence_length < 15:
                readability_score = 100  # Clear
            elif avg_sentence_length <= 25:
                readability_score = 85  # Acceptable
            else:
                readability_score = 60  # Complex
        else:
            readability_score = 50
            metrics["avg_sentence_length"] = 0

        score += readability_score * 0.2  # 20% weight for readability

        # Cap at 100
        score = min(100.0, score)

        return {
            "score": round(score, 2),
            "metrics": metrics
        }

    def _evaluate_actionability(self, description: Dict) -> Dict:
        """
        Evaluate actionability: Can user act on it immediately?

        Factors:
        - Has step-by-step approach
        - Number of steps (optimal: 4-7)
        - Has success criteria
        - Has technical context
        - Specificity (low vagueness)
        """
        metrics = {}
        score = 0.0

        # Check for step-by-step approach
        how_to_approach = str(description.get("how_to_approach", ""))
        has_steps = bool(how_to_approach and len(how_to_approach.strip()) > 20)
        metrics["has_steps"] = has_steps

        if has_steps:
            # Count steps (look for numbered/bulleted items)
            step_matches = re.findall(r'(?:^|\n)[\d•\-\*]+[\.\)]\s', how_to_approach, re.MULTILINE)
            step_count = len(step_matches)
            metrics["step_count"] = step_count

            # Step count scoring
            if step_count == 0:
                step_score = 40  # Has approach but no clear steps
            elif step_count <= 3:
                step_score = 60  # Minimal steps
            elif step_count <= 7:
                step_score = 100  # Optimal
            else:
                step_score = 85  # Too granular

            score += step_score * 0.4  # 40% weight for steps
        else:
            metrics["step_count"] = 0
            score += 0  # No steps = 0 points

        # Success criteria
        success_criteria = str(description.get("success_criteria", ""))
        has_criteria = bool(success_criteria and len(success_criteria.strip()) > 10)
        metrics["has_criteria"] = has_criteria

        if has_criteria:
            score += 30  # 30 points for criteria

        # Technical context
        technical_context = str(description.get("technical_context", ""))
        has_context = bool(technical_context and len(technical_context.strip()) > 10)
        metrics["has_context"] = has_context

        if has_context:
            score += 20  # 20 points for context

        # Specificity (check for vague words)
        all_text = " ".join([
            str(description.get("summary", "")),
            how_to_approach,
            success_criteria
        ]).lower()

        vague_words = ["some", "maybe", "might", "could", "possibly", "perhaps", "probably"]
        vague_count = sum(all_text.count(word) for word in vague_words)

        # Specificity scoring (inverse of vagueness)
        if vague_count == 0:
            specificity_score = 100
        elif vague_count <= 2:
            specificity_score = 80
        elif vague_count <= 4:
            specificity_score = 60
        else:
            specificity_score = 40

        metrics["vague_word_count"] = vague_count
        metrics["specificity_score"] = specificity_score

        score += specificity_score * 0.1  # 10% weight for specificity

        # Cap at 100
        score = min(100.0, score)

        return {
            "score": round(score, 2),
            "metrics": metrics
        }

    async def _evaluate_relevance(
        self,
        description: Dict,
        project_id: Optional[str] = None
    ) -> Dict:
        """
        Evaluate relevance: Contextually appropriate?

        Factors:
        - KG concept matches (optimal: 4-7 concepts)
        - Project alignment (if available)
        """
        metrics = {}
        score = 0.0

        # KG concept matches
        related_concepts = description.get("related_concepts", [])
        concept_count = len(related_concepts) if related_concepts else 0
        metrics["concept_match_count"] = concept_count

        # Concept count scoring
        if concept_count == 0:
            concept_score = 40  # No context
        elif concept_count <= 3:
            concept_score = 70  # Minimal context
        elif concept_count <= 7:
            concept_score = 100  # Optimal
        else:
            concept_score = 85  # Over-contextualized

        score = concept_score  # Base score from concepts

        # Project alignment (simplified - could query project metadata)
        if project_id:
            # For now, add moderate score if project_id exists
            metrics["has_project_context"] = True
            score = min(100.0, score * 1.1)  # 10% bonus
        else:
            metrics["has_project_context"] = False

        # Cap at 100
        score = min(100.0, score)

        return {
            "score": round(score, 2),
            "metrics": metrics
        }

    def _evaluate_confidence(self, description: Dict) -> Dict:
        """
        Evaluate confidence: How confident is the AI?

        Factors:
        - Average AI confidence across fields
        - Confidence consistency (low variance = good)
        """
        metrics = {}
        score = 0.0

        # Extract confidence values
        confidences = []

        for field in ["summary", "why_it_matters", "how_to_approach", "success_criteria", "technical_context"]:
            field_data = description.get(field, {})
            if isinstance(field_data, dict):
                confidence = field_data.get("confidence", 0.0)
                if confidence > 0:
                    confidences.append(confidence)

        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            min_confidence = min(confidences)
            max_confidence = max(confidences)

            # Variance calculation
            mean = avg_confidence
            variance = sum((c - mean) ** 2 for c in confidences) / len(confidences)

            metrics["avg_confidence"] = round(avg_confidence, 3)
            metrics["min_confidence"] = round(min_confidence, 3)
            metrics["max_confidence"] = round(max_confidence, 3)
            metrics["confidence_variance"] = round(variance, 3)

            # Score from average confidence
            score = avg_confidence * 100

            # Consistency bonus/penalty
            if variance < 0.05:
                score += 10  # Very consistent
            elif variance < 0.15:
                score += 5  # Consistent
            elif variance > 0.30:
                score -= 10  # Highly inconsistent

        else:
            # No confidence data
            metrics["avg_confidence"] = 0.0
            score = 50  # Neutral score

        # Cap at 100
        score = min(100.0, max(0.0, score))

        return {
            "score": round(score, 2),
            "metrics": metrics
        }

    # ========================================================================
    # SCORING & FEEDBACK
    # ========================================================================

    def _calculate_overall_score(
        self,
        completeness: float,
        clarity: float,
        actionability: float,
        relevance: float,
        confidence: float
    ) -> float:
        """Calculate weighted overall score."""
        from db.task_quality_models import calculate_overall_score
        return calculate_overall_score(
            completeness, clarity, actionability, relevance, confidence
        )

    def _generate_suggestions(
        self,
        completeness_result: Dict,
        clarity_result: Dict,
        actionability_result: Dict,
        relevance_result: Dict,
        confidence_result: Dict
    ) -> List[Dict]:
        """
        Generate actionable improvement suggestions.

        Returns list of suggestions with severity and impact.
        """
        suggestions = []

        # Completeness suggestions
        comp_metrics = completeness_result["metrics"]

        if not comp_metrics.get("has_how_to_approach"):
            suggestions.append({
                "category": "completeness",
                "severity": "high",
                "message": "Add 'how_to_approach' section with step-by-step guidance",
                "impact": "+15 points (reduces completion time by 30%)"
            })

        if not comp_metrics.get("has_success_criteria"):
            suggestions.append({
                "category": "completeness",
                "severity": "high",
                "message": "Add 'success_criteria' to clarify when the task is complete",
                "impact": "+15 points (improves success rates)"
            })

        if not comp_metrics.get("has_why_it_matters"):
            suggestions.append({
                "category": "completeness",
                "severity": "medium",
                "message": "Add 'why_it_matters' to explain the task's importance",
                "impact": "+10 points"
            })

        # Clarity suggestions
        clarity_metrics = clarity_result["metrics"]
        word_count = clarity_metrics.get("word_count", 0)

        if word_count < 100:
            suggestions.append({
                "category": "clarity",
                "severity": "high",
                "message": "Expand descriptions - aim for 200-500 words for clarity",
                "impact": "+20 points"
            })
        elif word_count > 800:
            suggestions.append({
                "category": "clarity",
                "severity": "medium",
                "message": "Condense descriptions - long text can be overwhelming",
                "impact": "+10 points"
            })

        if not clarity_metrics.get("uses_lists"):
            suggestions.append({
                "category": "clarity",
                "severity": "low",
                "message": "Use bullet points or numbered lists to improve readability",
                "impact": "+5 points"
            })

        # Actionability suggestions
        action_metrics = actionability_result["metrics"]

        if not action_metrics.get("has_steps"):
            suggestions.append({
                "category": "actionability",
                "severity": "high",
                "message": "Add step-by-step approach to make task actionable",
                "impact": "+25 points"
            })
        elif action_metrics.get("step_count", 0) < 3:
            suggestions.append({
                "category": "actionability",
                "severity": "medium",
                "message": "Break down approach into 4-7 clear steps",
                "impact": "+10 points"
            })

        vague_count = action_metrics.get("vague_word_count", 0)
        if vague_count > 2:
            suggestions.append({
                "category": "actionability",
                "severity": "low",
                "message": f"Replace vague words ({vague_count} found) with specific language",
                "impact": "+5 points"
            })

        # Relevance suggestions
        rel_metrics = relevance_result["metrics"]
        concept_count = rel_metrics.get("concept_match_count", 0)

        if concept_count < 2:
            suggestions.append({
                "category": "relevance",
                "severity": "medium",
                "message": "Add more project/domain context for better relevance",
                "impact": "+10 points"
            })

        # Sort by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda s: severity_order.get(s["severity"], 3))

        return suggestions

    def _identify_strengths(
        self,
        completeness_result: Dict,
        clarity_result: Dict,
        actionability_result: Dict,
        relevance_result: Dict,
        confidence_result: Dict
    ) -> List[str]:
        """Identify what's working well."""
        strengths = []

        # High scores = strengths
        if completeness_result["score"] >= 85:
            strengths.append("Excellent completeness - all key sections filled")

        if clarity_result["score"] >= 85:
            metrics = clarity_result["metrics"]
            word_count = metrics.get("word_count", 0)
            if 200 <= word_count <= 500:
                strengths.append(f"Optimal length ({word_count} words) - clear and concise")
            if metrics.get("uses_lists"):
                strengths.append("Good structure - uses lists for readability")

        if actionability_result["score"] >= 85:
            metrics = actionability_result["metrics"]
            if metrics.get("has_steps") and metrics.get("step_count", 0) >= 4:
                strengths.append(f"Clear action plan with {metrics['step_count']} steps")
            if metrics.get("specificity_score", 0) >= 80:
                strengths.append("Highly specific - minimal vague language")

        if confidence_result["score"] >= 80:
            metrics = confidence_result["metrics"]
            avg_conf = metrics.get("avg_confidence", 0.0)
            if avg_conf >= 0.8:
                strengths.append(f"High AI confidence (avg {avg_conf:.2f})")

        if relevance_result["score"] >= 85:
            metrics = relevance_result["metrics"]
            concept_count = metrics.get("concept_match_count", 0)
            if concept_count >= 4:
                strengths.append(f"Well-contextualized with {concept_count} related concepts")

        return strengths

    # ========================================================================
    # DATABASE OPERATIONS
    # ========================================================================

    async def _fetch_task_description(self, task_id: str) -> Optional[Dict]:
        """Fetch task description from database."""
        try:
            from db.task_synthesis_models import IntelligentTaskDescription

            result = await self.db.execute(
                select(IntelligentTaskDescription)
                .where(IntelligentTaskDescription.task_id == task_id)
                .order_by(IntelligentTaskDescription.created_at.desc())
            )

            description = result.scalar_one_or_none()

            if description:
                return {
                    "summary": description.summary,
                    "why_it_matters": description.why_it_matters,
                    "how_to_approach": description.how_to_approach,
                    "success_criteria": description.success_criteria,
                    "technical_context": description.technical_context,
                    "related_concepts": description.related_concepts
                }

            return None

        except Exception as e:
            logger.error(f"Failed to fetch task description: {e}")
            return None

    async def _save_quality_score(self, evaluation: Dict) -> bool:
        """Save quality score to database."""
        try:
            from db.task_quality_models import TaskQualityScore

            quality_score = TaskQualityScore(
                task_id=evaluation["task_id"],
                overall_score=evaluation["overall_score"],
                quality_tier=evaluation["quality_tier"],
                completeness_score=evaluation["completeness_score"],
                clarity_score=evaluation["clarity_score"],
                actionability_score=evaluation["actionability_score"],
                relevance_score=evaluation["relevance_score"],
                confidence_score=evaluation["confidence_score"],
                quality_metrics=evaluation["quality_metrics"],
                suggestions=evaluation["suggestions"],
                strengths=evaluation["strengths"],
                evaluation_time_ms=evaluation["evaluation_time_ms"],
                user_id=evaluation.get("user_id"),
                project_id=evaluation.get("project_id"),
                evaluator_version="1.0"
            )

            self.db.add(quality_score)
            await self.db.commit()

            return True

        except Exception as e:
            logger.error(f"Failed to save quality score: {e}")
            await self.db.rollback()
            return False


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

async def get_task_quality_evaluator(db: AsyncSession) -> TaskQualityEvaluatorService:
    """Factory function to get task quality evaluator service instance."""
    return TaskQualityEvaluatorService(db)
