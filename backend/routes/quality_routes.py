"""
Quality Evaluation API Routes - Phase 6 Stage 6

Provides REST API endpoints for quality evaluation and trust index.

Endpoints:
- GET  /api/quality/trust-index - Calculate trust index
- GET  /api/quality/trends - Get quality trends over time
- GET  /api/quality/task/{task_id} - Get task quality score
- POST /api/quality/evaluate/{task_id} - Evaluate task quality
- GET  /api/quality/recent - Get recent quality scores
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timedelta

from db.database import get_db
from services.task_quality_evaluator_service import get_task_quality_evaluator
from services.trust_index_service import get_trust_index_service
from db.task_quality_models import TaskQualityScore, QualityTrend
from sqlalchemy import select, and_, desc

router = APIRouter(prefix="/quality", tags=["quality"])


# ============================================================================
# TRUST INDEX
# ============================================================================

@router.get("/trust-index")
async def get_trust_index(
    window_days: int = Query(default=30, ge=1, le=365),
    project_id: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate and return trust index for a given scope.

    Args:
        window_days: Number of days to analyze (default: 30)
        project_id: Filter by project (optional)
        user_id: Filter by user (optional)

    Returns:
        Trust index data with components, metrics, and insights
    """
    try:
        trust_service = await get_trust_index_service(db)

        # Determine scope
        scope = "global"
        scope_id = None

        if user_id:
            scope = "user"
            scope_id = user_id
        elif project_id:
            scope = "project"
            scope_id = project_id

        # Calculate trust index
        trust_data = await trust_service.calculate_trust_index(
            scope=scope,
            scope_id=scope_id,
            window_days=window_days
        )

        if not trust_data:
            raise HTTPException(
                status_code=404,
                detail="No quality data available for the specified period"
            )

        return trust_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate trust index: {str(e)}")


# ============================================================================
# QUALITY TRENDS
# ============================================================================

@router.get("/trends")
async def get_quality_trends(
    window_days: int = Query(default=30, ge=1, le=365),
    period: str = Query(default="daily", regex="^(daily|weekly|monthly)$"),
    project_id: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get quality trends over time.

    Args:
        window_days: Number of days to analyze (default: 30)
        period: Aggregation period (daily, weekly, monthly)
        project_id: Filter by project (optional)
        user_id: Filter by user (optional)

    Returns:
        List of quality trend data points
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=window_days)

        # Determine scope
        scope = "global"
        scope_id = None

        if user_id:
            scope = "user"
            scope_id = user_id
        elif project_id:
            scope = "project"
            scope_id = project_id

        # Query quality trends
        query = select(QualityTrend).where(
            and_(
                QualityTrend.period_type == period,
                QualityTrend.period_start >= start_date,
                QualityTrend.scope == scope
            )
        )

        if scope_id:
            query = query.where(QualityTrend.scope_id == scope_id)

        query = query.order_by(QualityTrend.period_start)

        result = await db.execute(query)
        trends = result.scalars().all()

        # Format for frontend
        trend_data = []
        for trend in trends:
            trend_data.append({
                "date": trend.period_start.isoformat(),
                "quality": trend.avg_overall_score,
                "excellent": trend.excellent_count,
                "good": trend.good_count,
                "fair": trend.fair_count,
                "needs_improvement": trend.needs_improvement_count
            })

        return trend_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch quality trends: {str(e)}")


# ============================================================================
# TASK QUALITY SCORES
# ============================================================================

@router.get("/task/{task_id}")
async def get_task_quality(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get quality score for a specific task.

    Args:
        task_id: Task ID

    Returns:
        Task quality score with metrics and suggestions
    """
    try:
        # Query latest quality score for task
        result = await db.execute(
            select(TaskQualityScore)
            .where(TaskQualityScore.task_id == task_id)
            .order_by(desc(TaskQualityScore.evaluated_at))
            .limit(1)
        )

        quality_score = result.scalar_one_or_none()

        if not quality_score:
            raise HTTPException(status_code=404, detail=f"No quality score found for task {task_id}")

        # Format response
        return {
            "task_id": quality_score.task_id,
            "overall_score": quality_score.overall_score,
            "quality_tier": quality_score.quality_tier,
            "completeness_score": quality_score.completeness_score,
            "clarity_score": quality_score.clarity_score,
            "actionability_score": quality_score.actionability_score,
            "relevance_score": quality_score.relevance_score,
            "confidence_score": quality_score.confidence_score,
            "quality_metrics": quality_score.quality_metrics,
            "suggestions": quality_score.suggestions,
            "strengths": quality_score.strengths,
            "evaluated_at": quality_score.evaluated_at.isoformat(),
            "user_id": quality_score.user_id,
            "project_id": quality_score.project_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch task quality: {str(e)}")


@router.post("/evaluate/{task_id}")
async def evaluate_task_quality(
    task_id: str,
    user_id: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger quality evaluation for a task.

    Args:
        task_id: Task ID
        user_id: User who created the task (optional)
        project_id: Project context (optional)

    Returns:
        Quality evaluation result
    """
    try:
        evaluator = await get_task_quality_evaluator(db)

        # Evaluate task quality
        evaluation = await evaluator.evaluate_task_quality(
            task_id=task_id,
            user_id=user_id,
            project_id=project_id
        )

        if not evaluation:
            raise HTTPException(
                status_code=404,
                detail=f"No task description found for task {task_id}"
            )

        return evaluation

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate task quality: {str(e)}")


@router.get("/recent")
async def get_recent_quality_scores(
    limit: int = Query(default=20, ge=1, le=100),
    project_id: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    min_quality: Optional[float] = Query(default=None, ge=0, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent quality scores.

    Args:
        limit: Number of scores to return (default: 20, max: 100)
        project_id: Filter by project (optional)
        user_id: Filter by user (optional)
        min_quality: Minimum quality score filter (optional)

    Returns:
        List of recent quality scores
    """
    try:
        # Build query
        query = select(TaskQualityScore).order_by(desc(TaskQualityScore.evaluated_at))

        # Apply filters
        conditions = []

        if project_id:
            conditions.append(TaskQualityScore.project_id == project_id)
        if user_id:
            conditions.append(TaskQualityScore.user_id == user_id)
        if min_quality is not None:
            conditions.append(TaskQualityScore.overall_score >= min_quality)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.limit(limit)

        # Execute query
        result = await db.execute(query)
        quality_scores = result.scalars().all()

        # Format response
        scores = []
        for qs in quality_scores:
            scores.append({
                "task_id": qs.task_id,
                "overall_score": qs.overall_score,
                "quality_tier": qs.quality_tier,
                "completeness_score": qs.completeness_score,
                "clarity_score": qs.clarity_score,
                "actionability_score": qs.actionability_score,
                "relevance_score": qs.relevance_score,
                "confidence_score": qs.confidence_score,
                "suggestions": qs.suggestions,
                "strengths": qs.strengths,
                "evaluated_at": qs.evaluated_at.isoformat(),
                "user_id": qs.user_id,
                "project_id": qs.project_id
            })

        return scores

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch recent quality scores: {str(e)}")
