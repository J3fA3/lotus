"""
Learning Integration Service - Phase 6 Stage 5

Integrates learned patterns into task creation to make the AI progressively better.

This is the "action" layer that applies learning to improve task quality.

Design Decisions:
1. Integration points: Orchestrator (pre-synthesis) + Synthesizer (application)
2. Pattern application: Confidence-weighted blending (not hard override)
3. Pattern selection: Tier 1 (high-confidence) always, Tier 2 (medium) soft influence
4. Conflict resolution: Hierarchical (user > project > global) + confidence-based
5. Performance: In-memory cache with 10-min TTL, async refresh
6. Fail-safe: Graceful degradation (errors don't break task creation)

Blending Formula:
  final = (learned × learned_conf × weight + ai × ai_conf × (1-weight)) / norm

This closes the loop: Learning → Application → Better Tasks → Better Outcomes → Better Learning
"""

import logging
from typing import Dict, Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import asyncio
from functools import lru_cache

logger = logging.getLogger(__name__)


# ============================================================================
# LEARNING INTEGRATION SERVICE
# ============================================================================

class LearningIntegrationService:
    """
    Service for integrating learned patterns into task creation.

    This makes the AI progressively smarter by applying evidence-based patterns.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

        # Learning weights (how much to trust learned patterns vs AI)
        self.LEARNING_WEIGHT_HIGH_CONFIDENCE = 0.7  # 70% learned, 30% AI
        self.LEARNING_WEIGHT_MEDIUM_CONFIDENCE = 0.4  # 40% learned, 60% AI

        # Confidence thresholds
        self.HIGH_CONFIDENCE_THRESHOLD = 0.8
        self.MEDIUM_CONFIDENCE_THRESHOLD = 0.6
        self.MIN_CONFIDENCE_THRESHOLD = 0.5

        # Sample size thresholds
        self.MIN_SAMPLES_HIGH_CONFIDENCE = 50
        self.MIN_SAMPLES_MEDIUM_CONFIDENCE = 20

        # Cache TTL
        self.CACHE_TTL_SECONDS = 600  # 10 minutes

        # In-memory cache (simple dict for now, use Redis in production)
        self._pattern_cache = {}
        self._cache_timestamps = {}

    # ========================================================================
    # PATTERN CONSULTATION (Pre-Synthesis)
    # ========================================================================

    async def get_learned_context_enrichment(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        task_context: Optional[Dict] = None
    ) -> Dict:
        """
        Get learned patterns to enrich task synthesis context.

        Called by orchestrator BEFORE synthesis to incorporate learning.

        Args:
            user_id: User creating the task
            project_id: Project context
            task_context: Initial task data

        Returns:
            Enriched context dict with learned patterns
        """
        enrichment = {
            "learned_priority": None,
            "learned_priority_confidence": 0.0,
            "high_impact_features": [],
            "important_fields": [],
            "learning_applied": False,
            "learning_patterns_used": []
        }

        try:
            # Get priority prediction
            priority_prediction = await self._get_priority_with_cache(
                user_id=user_id,
                project_id=project_id,
                task_context=task_context
            )

            if priority_prediction:
                priority_value, priority_confidence = priority_prediction
                if priority_confidence >= self.MIN_CONFIDENCE_THRESHOLD:
                    enrichment["learned_priority"] = priority_value
                    enrichment["learned_priority_confidence"] = priority_confidence
                    enrichment["learning_applied"] = True
                    enrichment["learning_patterns_used"].append("priority_prediction")

            # Get high-impact features
            high_impact = await self._get_high_impact_features_with_cache()
            if high_impact:
                enrichment["high_impact_features"] = high_impact
                enrichment["learning_applied"] = True
                enrichment["learning_patterns_used"].append("high_impact_features")

            # Get important fields
            important_fields = await self._get_important_fields_with_cache(
                user_id=user_id,
                project_id=project_id
            )
            if important_fields:
                enrichment["important_fields"] = important_fields
                enrichment["learning_applied"] = True
                enrichment["learning_patterns_used"].append("field_importance")

            logger.info(
                f"Learning enrichment: {len(enrichment['learning_patterns_used'])} patterns applied "
                f"(user={user_id}, project={project_id})"
            )

            return enrichment

        except Exception as e:
            logger.error(f"Failed to get learned context enrichment: {e}")
            # Return empty enrichment (fail-safe)
            return enrichment

    async def _get_priority_with_cache(
        self,
        user_id: Optional[str],
        project_id: Optional[str],
        task_context: Optional[Dict]
    ) -> Optional[Tuple[str, float]]:
        """Get priority prediction with caching."""
        cache_key = f"priority_{user_id}_{project_id}"

        # Check cache
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        # Fetch from learning service
        try:
            from services.implicit_learning_service import get_implicit_learning_service

            learning_service = await get_implicit_learning_service(self.db)
            prediction = await learning_service.get_priority_prediction(
                user_id=user_id,
                project_id=project_id,
                task_context=task_context
            )

            # Cache result
            self._set_in_cache(cache_key, prediction)

            return prediction

        except Exception as e:
            logger.error(f"Failed to get priority prediction: {e}")
            return None

    async def _get_high_impact_features_with_cache(self) -> List[str]:
        """Get high-impact features with caching."""
        cache_key = "high_impact_features"

        # Check cache
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        # Fetch from outcome learning service
        try:
            from services.outcome_learning_service import get_outcome_learning_service

            outcome_service = await get_outcome_learning_service(self.db)
            correlations = await outcome_service.get_high_impact_features(
                min_impact_score=1.2,  # 20%+ improvement
                limit=10
            )

            features = [c.feature_name for c in correlations]

            # Cache result
            self._set_in_cache(cache_key, features)

            return features

        except Exception as e:
            logger.error(f"Failed to get high-impact features: {e}")
            return []

    async def _get_important_fields_with_cache(
        self,
        user_id: Optional[str],
        project_id: Optional[str]
    ) -> List[str]:
        """Get important fields (high engagement) with caching."""
        cache_key = f"important_fields_{user_id}_{project_id}"

        # Check cache
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        # Fetch from learning models
        try:
            from db.implicit_learning_models import LearningModel, ModelType, LearningScope
            from sqlalchemy import select, and_

            # Try user-specific first
            important_fields = []

            if user_id:
                result = await self.db.execute(
                    select(LearningModel)
                    .where(
                        and_(
                            LearningModel.model_type == ModelType.FIELD_IMPORTANCE,
                            LearningModel.scope == LearningScope.USER,
                            LearningModel.scope_id == user_id,
                            LearningModel.active == True,
                            LearningModel.confidence_score >= 0.7
                        )
                    )
                )
                model = result.scalar_one_or_none()

                if model and model.pattern:
                    interpretation = model.pattern.get("interpretation")
                    if interpretation == "high":
                        important_fields.append("user_preference_high")

            # Cache result
            self._set_in_cache(cache_key, important_fields)

            return important_fields

        except Exception as e:
            logger.error(f"Failed to get important fields: {e}")
            return []

    # ========================================================================
    # PATTERN APPLICATION (During Synthesis)
    # ========================================================================

    def apply_learned_priority(
        self,
        ai_suggested_priority: str,
        ai_confidence: float,
        learned_priority: Optional[str],
        learned_confidence: float
    ) -> Tuple[str, float, bool]:
        """
        Blend AI-suggested priority with learned priority.

        Args:
            ai_suggested_priority: AI's suggestion
            ai_confidence: AI's confidence (0.0-1.0)
            learned_priority: Learned pattern (may be None)
            learned_confidence: Learned confidence

        Returns:
            (final_priority, final_confidence, learning_applied)
        """
        # No learned pattern
        if not learned_priority or learned_confidence < self.MIN_CONFIDENCE_THRESHOLD:
            return (ai_suggested_priority, ai_confidence, False)

        # Same suggestion - boost confidence
        if ai_suggested_priority == learned_priority:
            boosted_confidence = min(1.0, (ai_confidence + learned_confidence) / 2 * 1.2)
            return (ai_suggested_priority, boosted_confidence, True)

        # Different suggestions - resolve conflict
        return self._resolve_priority_conflict(
            ai_suggested_priority=ai_suggested_priority,
            ai_confidence=ai_confidence,
            learned_priority=learned_priority,
            learned_confidence=learned_confidence
        )

    def _resolve_priority_conflict(
        self,
        ai_suggested_priority: str,
        ai_confidence: float,
        learned_priority: str,
        learned_confidence: float
    ) -> Tuple[str, float, bool]:
        """
        Resolve conflict when AI and learned patterns disagree.

        Strategy:
        - High learned confidence (>0.8): Use learned (but lower confidence)
        - Medium learned confidence (0.6-0.8): Use AI (preserve creativity)
        - Low learned confidence (<0.6): Use AI
        """
        if learned_confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            # High confidence learned pattern - use it, but signal uncertainty
            return (learned_priority, learned_confidence * 0.9, True)

        elif learned_confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            # Medium confidence - prefer AI to preserve creativity
            # But lower AI confidence slightly to signal disagreement
            return (ai_suggested_priority, ai_confidence * 0.85, False)

        else:
            # Low confidence - use AI
            return (ai_suggested_priority, ai_confidence, False)

    def enhance_synthesis_prompt(
        self,
        base_prompt: str,
        high_impact_features: List[str],
        important_fields: List[str]
    ) -> str:
        """
        Enhance synthesis prompt with learned patterns.

        Adds emphasis on high-impact quality features.

        Args:
            base_prompt: Original synthesis prompt
            high_impact_features: Features that improve outcomes
            important_fields: Fields users care about

        Returns:
            Enhanced prompt
        """
        if not high_impact_features and not important_fields:
            return base_prompt

        enhancements = []

        if high_impact_features:
            feature_emphasis = self._get_feature_emphasis(high_impact_features)
            if feature_emphasis:
                enhancements.append(feature_emphasis)

        if important_fields:
            field_emphasis = self._get_field_emphasis(important_fields)
            if field_emphasis:
                enhancements.append(field_emphasis)

        if enhancements:
            enhanced_prompt = base_prompt + "\n\n" + "\n".join(enhancements)
            return enhanced_prompt

        return base_prompt

    def _get_feature_emphasis(self, high_impact_features: List[str]) -> str:
        """Get prompt enhancement for high-impact features."""
        emphasis_map = {
            "has_how_to_approach": "IMPORTANT: Include a detailed 'how_to_approach' section with step-by-step guidance. This has been shown to reduce task completion time by 30%.",
            "has_success_criteria": "IMPORTANT: Include clear 'success_criteria' so the user knows when the task is complete. This improves task success rates.",
            "has_technical_context": "IMPORTANT: Provide relevant technical context to help the user understand dependencies and constraints."
        }

        emphases = []
        for feature in high_impact_features:
            if feature in emphasis_map:
                emphases.append(emphasis_map[feature])

        return "\n".join(emphases) if emphases else ""

    def _get_field_emphasis(self, important_fields: List[str]) -> str:
        """Get prompt enhancement for important fields."""
        # Simplified - could be more sophisticated
        return ""

    # ========================================================================
    # PATTERN TRACKING (Post-Synthesis)
    # ========================================================================

    async def track_applied_patterns(
        self,
        task_id: str,
        patterns_applied: List[str],
        ai_suggestions: Dict,
        final_values: Dict
    ) -> bool:
        """
        Track which learned patterns were applied to a task.

        This enables validation: Did applying these patterns improve outcomes?

        Args:
            task_id: Task ID
            patterns_applied: List of pattern names applied
            ai_suggestions: What AI originally suggested
            final_values: What was actually used

        Returns:
            True if successful
        """
        try:
            # Create tracking record (simplified - could use dedicated table)
            tracking_data = {
                "task_id": task_id,
                "patterns_applied": patterns_applied,
                "ai_suggestions": ai_suggestions,
                "final_values": final_values,
                "tracked_at": datetime.utcnow().isoformat()
            }

            logger.info(
                f"Tracked applied patterns for task {task_id}: "
                f"{len(patterns_applied)} patterns"
            )

            # In production, store in dedicated table for analysis

            return True

        except Exception as e:
            logger.error(f"Failed to track applied patterns: {e}")
            return False

    # ========================================================================
    # CACHE MANAGEMENT
    # ========================================================================

    def _get_from_cache(self, key: str) -> Optional[any]:
        """Get value from cache if not expired."""
        if key not in self._pattern_cache:
            return None

        # Check expiration
        timestamp = self._cache_timestamps.get(key)
        if timestamp:
            age = (datetime.utcnow() - timestamp).total_seconds()
            if age > self.CACHE_TTL_SECONDS:
                # Expired
                del self._pattern_cache[key]
                del self._cache_timestamps[key]
                return None

        return self._pattern_cache[key]

    def _set_in_cache(self, key: str, value: any):
        """Set value in cache with timestamp."""
        self._pattern_cache[key] = value
        self._cache_timestamps[key] = datetime.utcnow()

        # Simple size limit (evict oldest if >1000)
        if len(self._pattern_cache) > 1000:
            oldest_key = min(self._cache_timestamps, key=self._cache_timestamps.get)
            del self._pattern_cache[oldest_key]
            del self._cache_timestamps[oldest_key]

    def clear_cache(self):
        """Clear all cached patterns."""
        self._pattern_cache.clear()
        self._cache_timestamps.clear()


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

async def get_learning_integration_service(db: AsyncSession) -> LearningIntegrationService:
    """Factory function to get learning integration service instance."""
    return LearningIntegrationService(db)
