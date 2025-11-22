"""
API Routes for Knowledge Graph Lifecycle Management - Phase 6

Provides endpoints for:
1. Manual KG cleanup (with dry-run mode)
2. Health monitoring
3. Scheduled task management

These endpoints allow admins to:
- Run dry-run cleanup to see what would be pruned
- Execute production cleanup
- Monitor KG health metrics
- View cleanup history
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from db.database import get_db
from services.kg_lifecycle_manager import (
    get_kg_lifecycle_manager,
    KGLifecycleConfig,
    CleanupReport
)

router = APIRouter(prefix="/api/kg-lifecycle", tags=["kg-lifecycle"])


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class CleanupRequest(BaseModel):
    """Request to run KG cleanup."""
    dry_run: bool = True
    config: Optional[KGLifecycleConfig] = None


class HealthResponse(BaseModel):
    """KG health metrics response."""
    kg_size: dict
    concepts: dict
    relationships: dict
    outcomes: dict
    timestamp: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/cleanup", response_model=CleanupReport)
async def run_cleanup(
    request: CleanupRequest,
    db: AsyncSession = Depends(get_db)
):
    """Run KG cleanup cycle.

    This endpoint allows manual triggering of KG maintenance.

    **Dry Run Mode (Recommended First)**:
    ```json
    {
        "dry_run": true
    }
    ```

    **Production Run**:
    ```json
    {
        "dry_run": false
    }
    ```

    **Custom Configuration**:
    ```json
    {
        "dry_run": true,
        "config": {
            "archive_concepts_days": 180,
            "weak_relationship_threshold": 0.3,
            "concept_similarity_threshold": 0.9
        }
    }
    ```

    Returns:
        CleanupReport with details of operations performed
    """
    try:
        manager = await get_kg_lifecycle_manager(db, config=request.config)
        report = await manager.run_cleanup(dry_run=request.dry_run)
        return report

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"KG cleanup failed: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse)
async def get_health(db: AsyncSession = Depends(get_db)):
    """Get KG health metrics.

    Returns current state of the knowledge graph including:
    - Total nodes and edges
    - Concept quality metrics
    - Relationship strength
    - Task outcome statistics

    Use this to monitor KG growth and identify when cleanup is needed.

    Returns:
        HealthResponse with current KG metrics
    """
    try:
        manager = await get_kg_lifecycle_manager(db)
        health = await manager.get_health_report()
        return HealthResponse(**health)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )


@router.post("/rebuild-similarity-index")
async def rebuild_similarity_index(db: AsyncSession = Depends(get_db)):
    """Manually trigger similarity index rebuild.

    This is computationally expensive and normally runs on a schedule.
    Use this endpoint only when:
    - Many new tasks have been created
    - Index appears stale
    - Testing similarity queries

    Returns:
        Number of entries rebuilt
    """
    try:
        manager = await get_kg_lifecycle_manager(db)
        count = await manager.rebuild_similarity_index()
        await db.commit()

        return {
            "status": "success",
            "entries_rebuilt": count,
            "message": f"Rebuilt similarity index for {count} tasks"
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Similarity index rebuild failed: {str(e)}"
        )
