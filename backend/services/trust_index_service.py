"""
Trust Index Service - Phase 6 Stage 6

Calculates and tracks user trust in the AI system.

Design Decisions:
1. Trust definition: User confidence in AI's ability to provide valuable, accurate, useful output
2. Four components: Quality (35%) + Engagement (30%) + Outcomes (25%) + Performance (10%)
3. Scope: Global, project, and user-level trust measurement
4. Trend tracking: Daily/weekly to identify trust improvements or degradation
5. Actionable insights: Why trust is high/low, what to improve

Trust Formula:
  trust_index = 0.35×quality + 0.30×engagement + 0.25×outcomes + 0.10×performance

Trust Categories:
  - High (80-100): System consistently delivers value
  - Medium (60-79): Generally good, some improvements needed
  - Low (40-59): Inconsistent quality/engagement
  - Very Low (<40): System underperforming

This provides a single, actionable metric for AI system health.
"""

import logging
from typing import Dict, Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger(__name__)


# ============================================================================
# TRUST INDEX SERVICE
# ============================================================================

class TrustIndexService:
    """
    Service for calculating and tracking user trust in the AI system.

    Trust = Consistent quality + User engagement + Outcome success + System reliability
    """

    def __init__(self, db: AsyncSession):
        self.db = db

        # Trust component weights
        self.QUALITY_WEIGHT = 0.35  # Most important - is output good?
        self.ENGAGEMENT_WEIGHT = 0.30  # Do users trust enough to use it?
        self.OUTCOMES_WEIGHT = 0.25  # Does it help users succeed?
        self.PERFORMANCE_WEIGHT = 0.10  # Is it reliable?

        # Thresholds
        self.HIGH_TRUST_THRESHOLD = 80.0
        self.MEDIUM_TRUST_THRESHOLD = 60.0
        self.LOW_TRUST_THRESHOLD = 40.0

        # Data windows (days)
        self.DEFAULT_WINDOW_DAYS = 30

    # ========================================================================
    # TRUST INDEX CALCULATION
    # ========================================================================

    async def calculate_trust_index(
        self,
        scope: str = "global",
        scope_id: Optional[str] = None,
        window_days: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Calculate trust index for given scope.

        Args:
            scope: "global", "project", or "user"
            scope_id: Scope identifier (project_id or user_id)
            window_days: Data window (default: 30 days)

        Returns:
            Trust index result with scores, metrics, insights
        """
        window_days = window_days or self.DEFAULT_WINDOW_DAYS
        start_date = datetime.utcnow() - timedelta(days=window_days)

        try:
            # Calculate each component
            quality_result = await self._calculate_quality_consistency(
                scope, scope_id, start_date
            )

            engagement_result = await self._calculate_user_engagement(
                scope, scope_id, start_date
            )

            outcomes_result = await self._calculate_outcome_success(
                scope, scope_id, start_date
            )

            performance_result = await self._calculate_system_performance(
                scope, scope_id, start_date
            )

            # Calculate overall trust index
            trust_index = (
                self.QUALITY_WEIGHT * quality_result["score"] +
                self.ENGAGEMENT_WEIGHT * engagement_result["score"] +
                self.OUTCOMES_WEIGHT * outcomes_result["score"] +
                self.PERFORMANCE_WEIGHT * performance_result["score"]
            )

            # Classify trust level
            trust_level = self._classify_trust_level(trust_index)

            # Generate insights
            insights = self._generate_trust_insights(
                quality_result,
                engagement_result,
                outcomes_result,
                performance_result,
                trust_index
            )

            result = {
                "trust_index": round(trust_index, 2),
                "trust_level": trust_level,
                "scope": scope,
                "scope_id": scope_id,
                "window_days": window_days,
                "components": {
                    "quality_consistency": quality_result,
                    "user_engagement": engagement_result,
                    "outcome_success": outcomes_result,
                    "system_performance": performance_result
                },
                "insights": insights,
                "calculated_at": datetime.utcnow().isoformat()
            }

            logger.info(
                f"Trust index calculated: {trust_index:.2f} ({trust_level}) "
                f"for {scope}={scope_id or 'global'}"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to calculate trust index: {e}")
            return None

    # ========================================================================
    # COMPONENT CALCULATORS
    # ========================================================================

    async def _calculate_quality_consistency(
        self,
        scope: str,
        scope_id: Optional[str],
        start_date: datetime
    ) -> Dict:
        """
        Calculate quality consistency component (35% weight).

        Factors:
        - Average quality score
        - Quality variance (low variance = consistent)
        - % of excellent/good quality tasks
        """
        try:
            from db.task_quality_models import TaskQualityScore

            # Build query
            query = select(TaskQualityScore).where(
                TaskQualityScore.evaluated_at >= start_date
            )

            if scope == "user" and scope_id:
                query = query.where(TaskQualityScore.user_id == scope_id)
            elif scope == "project" and scope_id:
                query = query.where(TaskQualityScore.project_id == scope_id)

            result = await self.db.execute(query)
            quality_scores = result.scalars().all()

            if not quality_scores:
                return {
                    "score": 50.0,  # Neutral default
                    "metrics": {
                        "sample_size": 0,
                        "avg_quality": 0.0,
                        "quality_variance": 0.0,
                        "excellent_pct": 0.0,
                        "good_or_better_pct": 0.0
                    }
                }

            # Extract scores
            scores = [qs.overall_score for qs in quality_scores]

            # Calculate metrics
            avg_quality = statistics.mean(scores)
            quality_variance = statistics.variance(scores) if len(scores) > 1 else 0.0

            # Tier distribution
            excellent_count = sum(1 for qs in quality_scores if qs.quality_tier == "excellent")
            good_count = sum(1 for qs in quality_scores if qs.quality_tier == "good")
            total_count = len(quality_scores)

            excellent_pct = (excellent_count / total_count * 100) if total_count > 0 else 0.0
            good_or_better_pct = ((excellent_count + good_count) / total_count * 100) if total_count > 0 else 0.0

            # Scoring logic
            # Base score from average quality
            base_score = avg_quality

            # Consistency bonus (low variance)
            if quality_variance < 50:
                consistency_bonus = 10  # Very consistent
            elif quality_variance < 100:
                consistency_bonus = 5  # Consistent
            else:
                consistency_bonus = 0  # Inconsistent (no penalty, but no bonus)

            # High quality percentage bonus
            if good_or_better_pct >= 80:
                quality_pct_bonus = 10
            elif good_or_better_pct >= 60:
                quality_pct_bonus = 5
            else:
                quality_pct_bonus = 0

            # Final component score
            component_score = min(100.0, base_score + consistency_bonus + quality_pct_bonus)

            return {
                "score": round(component_score, 2),
                "metrics": {
                    "sample_size": total_count,
                    "avg_quality": round(avg_quality, 2),
                    "quality_variance": round(quality_variance, 2),
                    "excellent_pct": round(excellent_pct, 2),
                    "good_or_better_pct": round(good_or_better_pct, 2),
                    "consistency_bonus": consistency_bonus,
                    "quality_pct_bonus": quality_pct_bonus
                }
            }

        except Exception as e:
            logger.error(f"Failed to calculate quality consistency: {e}")
            return {"score": 50.0, "metrics": {}}

    async def _calculate_user_engagement(
        self,
        scope: str,
        scope_id: Optional[str],
        start_date: datetime
    ) -> Dict:
        """
        Calculate user engagement component (30% weight).

        Factors:
        - AI suggestion acceptance rate
        - Edit rate (lower = higher trust)
        - Question answer rate
        - Auto-fill acceptance rate
        """
        try:
            from db.implicit_learning_models import ImplicitSignal, SignalType

            # Build query
            query = select(ImplicitSignal).where(
                and_(
                    ImplicitSignal.created_at >= start_date,
                    ImplicitSignal.signal_type.in_([
                        SignalType.AI_OVERRIDE,
                        SignalType.QUESTION_ANSWERED,
                        SignalType.QUESTION_DISMISSED,
                        SignalType.AUTO_FILL_ACCEPTED,
                        SignalType.AUTO_FILL_REJECTED,
                        SignalType.FIELD_EDITED
                    ])
                )
            )

            if scope == "user" and scope_id:
                query = query.where(ImplicitSignal.user_id == scope_id)
            elif scope == "project" and scope_id:
                query = query.where(ImplicitSignal.project_id == scope_id)

            result = await self.db.execute(query)
            signals = result.scalars().all()

            if not signals:
                return {
                    "score": 50.0,  # Neutral default
                    "metrics": {
                        "sample_size": 0,
                        "acceptance_rate": 0.0,
                        "edit_rate": 0.0,
                        "question_answer_rate": 0.0,
                        "auto_fill_acceptance_rate": 0.0
                    }
                }

            # Count signal types
            override_count = sum(1 for s in signals if s.signal_type == SignalType.AI_OVERRIDE)
            total_ai_interactions = sum(
                1 for s in signals if s.signal_type in [
                    SignalType.AI_OVERRIDE, SignalType.AUTO_FILL_ACCEPTED, SignalType.AUTO_FILL_REJECTED
                ]
            )

            questions_answered = sum(1 for s in signals if s.signal_type == SignalType.QUESTION_ANSWERED)
            questions_dismissed = sum(1 for s in signals if s.signal_type == SignalType.QUESTION_DISMISSED)
            total_questions = questions_answered + questions_dismissed

            auto_fill_accepted = sum(1 for s in signals if s.signal_type == SignalType.AUTO_FILL_ACCEPTED)
            auto_fill_rejected = sum(1 for s in signals if s.signal_type == SignalType.AUTO_FILL_REJECTED)
            total_auto_fill = auto_fill_accepted + auto_fill_rejected

            field_edits = sum(1 for s in signals if s.signal_type == SignalType.FIELD_EDITED)

            # Calculate rates
            # Acceptance rate (inverse of override rate)
            acceptance_rate = (1 - (override_count / total_ai_interactions)) * 100 if total_ai_interactions > 0 else 50.0

            # Edit rate (lower is better)
            edit_rate = (field_edits / len(signals)) * 100 if signals else 0.0

            # Question answer rate (higher is better - engagement)
            question_answer_rate = (questions_answered / total_questions * 100) if total_questions > 0 else 50.0

            # Auto-fill acceptance rate
            auto_fill_acceptance_rate = (auto_fill_accepted / total_auto_fill * 100) if total_auto_fill > 0 else 50.0

            # Scoring logic
            # Acceptance rate: direct contribution (0-100)
            acceptance_score = acceptance_rate

            # Edit rate: inverse (low edit = high trust)
            # 0% edits = 100 points, 50% edits = 50 points, 100% edits = 0 points
            edit_score = max(0, 100 - edit_rate)

            # Question answer rate: direct contribution
            question_score = question_answer_rate

            # Auto-fill acceptance rate: direct contribution
            auto_fill_score = auto_fill_acceptance_rate

            # Weighted combination
            component_score = (
                0.35 * acceptance_score +
                0.25 * edit_score +
                0.25 * question_score +
                0.15 * auto_fill_score
            )

            return {
                "score": round(component_score, 2),
                "metrics": {
                    "sample_size": len(signals),
                    "acceptance_rate": round(acceptance_rate, 2),
                    "edit_rate": round(edit_rate, 2),
                    "question_answer_rate": round(question_answer_rate, 2),
                    "auto_fill_acceptance_rate": round(auto_fill_acceptance_rate, 2)
                }
            }

        except Exception as e:
            logger.error(f"Failed to calculate user engagement: {e}")
            return {"score": 50.0, "metrics": {}}

    async def _calculate_outcome_success(
        self,
        scope: str,
        scope_id: Optional[str],
        start_date: datetime
    ) -> Dict:
        """
        Calculate outcome success component (25% weight).

        Factors:
        - Task completion rate
        - Average time to completion
        - Tasks completed faster than average
        """
        try:
            from db.outcome_learning_models import QualityFeatureAnalysis

            # Build query
            query = select(QualityFeatureAnalysis).where(
                QualityFeatureAnalysis.created_at >= start_date
            )

            # Note: QualityFeatureAnalysis doesn't have user_id/project_id directly
            # In production, join with tasks table for proper filtering
            # For now, calculate globally

            result = await self.db.execute(query)
            analyses = result.scalars().all()

            if not analyses:
                return {
                    "score": 50.0,  # Neutral default
                    "metrics": {
                        "sample_size": 0,
                        "completion_rate": 0.0,
                        "avg_time_to_complete": 0.0,
                        "fast_completion_pct": 0.0
                    }
                }

            # Filter by outcome
            completed_tasks = [a for a in analyses if a.outcome_status == "completed"]
            total_tasks = len(analyses)

            # Completion rate
            completion_rate = (len(completed_tasks) / total_tasks * 100) if total_tasks > 0 else 0.0

            # Average time to completion (for completed tasks)
            completion_times = [a.time_to_complete for a in completed_tasks if a.time_to_complete]

            if completion_times:
                avg_time = statistics.mean(completion_times)
                median_time = statistics.median(completion_times)

                # Fast completion: completed faster than median
                fast_completions = sum(1 for t in completion_times if t < median_time)
                fast_completion_pct = (fast_completions / len(completion_times) * 100) if completion_times else 0.0
            else:
                avg_time = 0.0
                fast_completion_pct = 0.0

            # Scoring logic
            # Completion rate: direct contribution (target 80%+)
            if completion_rate >= 80:
                completion_score = 100
            elif completion_rate >= 60:
                completion_score = 80
            else:
                completion_score = completion_rate

            # Time score: assume baseline is better than manual (>50% fast = good)
            if fast_completion_pct >= 60:
                time_score = 100
            elif fast_completion_pct >= 40:
                time_score = 80
            else:
                time_score = 60

            # Weighted combination
            component_score = (
                0.70 * completion_score +
                0.30 * time_score
            )

            return {
                "score": round(component_score, 2),
                "metrics": {
                    "sample_size": total_tasks,
                    "completion_rate": round(completion_rate, 2),
                    "avg_time_to_complete": round(avg_time, 2) if completion_times else 0.0,
                    "fast_completion_pct": round(fast_completion_pct, 2)
                }
            }

        except Exception as e:
            logger.error(f"Failed to calculate outcome success: {e}")
            return {"score": 50.0, "metrics": {}}

    async def _calculate_system_performance(
        self,
        scope: str,
        scope_id: Optional[str],
        start_date: datetime
    ) -> Dict:
        """
        Calculate system performance component (10% weight).

        Factors:
        - Synthesis success rate
        - Average evaluation time
        - Error rate
        """
        try:
            from db.task_quality_models import TaskQualityScore

            # Get quality scores (proxy for successful syntheses)
            query = select(TaskQualityScore).where(
                TaskQualityScore.evaluated_at >= start_date
            )

            if scope == "user" and scope_id:
                query = query.where(TaskQualityScore.user_id == scope_id)
            elif scope == "project" and scope_id:
                query = query.where(TaskQualityScore.project_id == scope_id)

            result = await self.db.execute(query)
            quality_scores = result.scalars().all()

            if not quality_scores:
                return {
                    "score": 50.0,  # Neutral default
                    "metrics": {
                        "sample_size": 0,
                        "avg_evaluation_time_ms": 0,
                        "fast_evaluation_pct": 0.0
                    }
                }

            # Evaluation times
            eval_times = [qs.evaluation_time_ms for qs in quality_scores if qs.evaluation_time_ms]

            if eval_times:
                avg_eval_time = statistics.mean(eval_times)

                # Fast evaluations (<50ms target)
                fast_evals = sum(1 for t in eval_times if t < 50)
                fast_eval_pct = (fast_evals / len(eval_times) * 100) if eval_times else 0.0
            else:
                avg_eval_time = 0.0
                fast_eval_pct = 0.0

            # Scoring logic
            # Success rate: if we have scores, synthesis succeeded (assume 100%)
            success_score = 100

            # Performance: based on speed
            if avg_eval_time < 50:
                speed_score = 100  # Excellent
            elif avg_eval_time < 100:
                speed_score = 85  # Good
            elif avg_eval_time < 200:
                speed_score = 70  # Acceptable
            else:
                speed_score = 60  # Slow

            # Weighted combination
            component_score = (
                0.50 * success_score +
                0.50 * speed_score
            )

            return {
                "score": round(component_score, 2),
                "metrics": {
                    "sample_size": len(quality_scores),
                    "avg_evaluation_time_ms": round(avg_eval_time, 2) if eval_times else 0.0,
                    "fast_evaluation_pct": round(fast_eval_pct, 2)
                }
            }

        except Exception as e:
            logger.error(f"Failed to calculate system performance: {e}")
            return {"score": 50.0, "metrics": {}}

    # ========================================================================
    # CLASSIFICATION & INSIGHTS
    # ========================================================================

    def _classify_trust_level(self, trust_index: float) -> str:
        """Classify trust index into level."""
        if trust_index >= self.HIGH_TRUST_THRESHOLD:
            return "high"
        elif trust_index >= self.MEDIUM_TRUST_THRESHOLD:
            return "medium"
        elif trust_index >= self.LOW_TRUST_THRESHOLD:
            return "low"
        else:
            return "very_low"

    def _generate_trust_insights(
        self,
        quality_result: Dict,
        engagement_result: Dict,
        outcomes_result: Dict,
        performance_result: Dict,
        trust_index: float
    ) -> Dict:
        """
        Generate actionable insights about trust.

        Returns:
            Insights dict with strengths, weaknesses, recommendations
        """
        strengths = []
        weaknesses = []
        recommendations = []

        # Analyze each component
        components = {
            "Quality Consistency": quality_result,
            "User Engagement": engagement_result,
            "Outcome Success": outcomes_result,
            "System Performance": performance_result
        }

        for name, result in components.items():
            score = result["score"]

            if score >= 80:
                strengths.append(f"{name} is excellent ({score:.1f}/100)")
            elif score < 60:
                weaknesses.append(f"{name} needs improvement ({score:.1f}/100)")

        # Specific recommendations
        if quality_result["score"] < 70:
            recommendations.append("Focus on improving description quality - add more complete sections")

        if engagement_result["score"] < 70:
            metrics = engagement_result.get("metrics", {})
            edit_rate = metrics.get("edit_rate", 0)
            if edit_rate > 50:
                recommendations.append("High edit rate indicates low trust - improve AI accuracy")

        if outcomes_result["score"] < 70:
            metrics = outcomes_result.get("metrics", {})
            completion_rate = metrics.get("completion_rate", 0)
            if completion_rate < 70:
                recommendations.append("Low task completion rate - ensure tasks are actionable and clear")

        # Overall recommendation
        trust_level = self._classify_trust_level(trust_index)
        if trust_level == "high":
            overall = "Trust is high - maintain current quality and engagement levels"
        elif trust_level == "medium":
            overall = "Trust is moderate - focus on areas scoring below 70"
        elif trust_level == "low":
            overall = "Trust is low - prioritize quality consistency and user engagement"
        else:
            overall = "Trust is very low - immediate attention needed across all components"

        return {
            "overall": overall,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": recommendations
        }


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

async def get_trust_index_service(db: AsyncSession) -> TrustIndexService:
    """Factory function to get trust index service instance."""
    return TrustIndexService(db)
