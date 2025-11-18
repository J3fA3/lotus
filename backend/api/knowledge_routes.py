"""
Knowledge Graph API Routes - Cross-Context Knowledge Queries

These endpoints provide access to the living knowledge graph that evolves over time:
1. Query entity knowledge across all contexts
2. View discovered team structures
3. Get graph statistics
4. Track knowledge evolution
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict

from db.database import get_db
from services.knowledge_graph_service import KnowledgeGraphService


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class EntityKnowledgeResponse(BaseModel):
    """Response schema for entity knowledge query."""
    entity: str
    type: str
    aliases: List[str]
    mentioned_in: int
    first_seen: str
    last_seen: str
    average_confidence: float
    metadata: Optional[Dict]
    relationships: Dict[str, List[Dict]]

    class Config:
        json_schema_extra = {
            "example": {
                "entity": "Jef Adriaenssens",
                "type": "PERSON",
                "aliases": ["jef", "jef adriaenssens"],
                "mentioned_in": 12,
                "first_seen": "2025-11-10T10:30:00",
                "last_seen": "2025-11-16T15:45:00",
                "average_confidence": 0.95,
                "metadata": {},
                "relationships": {
                    "outgoing": [
                        {
                            "type": "WORKS_ON",
                            "target": "CRESCO",
                            "target_type": "PROJECT",
                            "strength": 0.95,
                            "mentioned_in": 8,
                            "contexts": 5
                        }
                    ],
                    "incoming": []
                }
            }
        }


class TeamStructuresResponse(BaseModel):
    """Response schema for discovered team structures."""
    structures: List[Dict]
    total_pillars: int
    total_teams: int
    total_roles: int

    class Config:
        json_schema_extra = {
            "example": {
                "structures": [
                    {
                        "name": "Customer Pillar",
                        "type": "pillar",
                        "mentioned": 15,
                        "contexts": 8,
                        "first_seen": "2025-11-10T10:00:00",
                        "teams": [
                            {
                                "name": "Menu Team",
                                "type": "team",
                                "mentioned": 12,
                                "contexts": 6,
                                "roles": [
                                    {
                                        "name": "Engineering",
                                        "mentioned": 10,
                                        "contexts": 5
                                    }
                                ]
                            }
                        ]
                    }
                ],
                "total_pillars": 3,
                "total_teams": 8,
                "total_roles": 12
            }
        }


class GraphStatsResponse(BaseModel):
    """Response schema for graph statistics."""
    total_nodes: int
    total_edges: int
    nodes_by_type: Dict[str, int]
    top_mentioned: List[Dict]
    timestamp: str


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(prefix="/knowledge", tags=["Knowledge Graph"])


@router.get("/entity/{entity_name}", response_model=EntityKnowledgeResponse)
async def get_entity_knowledge(
    entity_name: str,
    entity_type: Optional[str] = Query(None, description="Filter by entity type (PERSON, PROJECT, TEAM, DATE)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all knowledge about an entity across all contexts.

    This endpoint shows:
    - How many times the entity was mentioned
    - When it was first and last seen
    - All relationships (who works on what, who communicates with whom)
    - Relationship strength based on evidence
    - Team structure associations

    Example queries:
    - /api/knowledge/entity/Jef%20Adriaenssens
    - /api/knowledge/entity/CRESCO?entity_type=PROJECT
    """
    kg_service = KnowledgeGraphService(db)
    result = await kg_service.get_entity_knowledge(entity_name, entity_type)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No knowledge found for entity '{entity_name}'" +
                   (f" of type {entity_type}" if entity_type else "")
        )

    return EntityKnowledgeResponse(**result)


@router.get("/structures", response_model=TeamStructuresResponse)
async def get_team_structures(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all discovered team structures.

    This endpoint shows the organizational hierarchy that the system
    has learned from actual context, including:
    - Pillars (e.g., Customer Pillar, Partner Pillar)
    - Teams (e.g., Menu Team, Search Team)
    - Roles (e.g., Engineering, Product, Research)

    The system dynamically discovers these from context - nothing is hardcoded.

    Returns hierarchical structure showing:
    - How many times each structure was mentioned
    - In how many different contexts
    - When first discovered
    - Parent-child relationships
    """
    kg_service = KnowledgeGraphService(db)
    result = await kg_service.get_discovered_team_structures()

    return TeamStructuresResponse(**result)


@router.get("/stats", response_model=GraphStatsResponse)
async def get_graph_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Get current knowledge graph statistics.

    Shows:
    - Total number of nodes (canonical entities)
    - Total number of edges (relationships)
    - Breakdown by entity type
    - Top mentioned entities
    - Most recent update time

    Useful for:
    - Monitoring knowledge graph growth
    - Understanding what the system knows
    - Debugging and analytics
    """
    kg_service = KnowledgeGraphService(db)
    stats = await kg_service.compute_graph_stats()

    return GraphStatsResponse(**stats)


@router.get("/search")
async def search_entities(
    query: str = Query(..., min_length=2, description="Search query"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for entities by name (fuzzy matching).

    This endpoint allows searching the knowledge graph with partial names.
    For example:
    - "jef" -> finds "Jef Adriaenssens"
    - "cresc" -> finds "CRESCO"
    - "menu" -> finds "Menu Team"

    Returns matches sorted by:
    1. Relevance (string similarity)
    2. Mention count (more mentioned = more important)
    3. Recency (recently seen = more relevant)
    """
    from db.knowledge_graph_models import KnowledgeNode
    from sqlalchemy import select, func, or_

    # Build query
    search_query = select(KnowledgeNode).where(
        or_(
            func.lower(KnowledgeNode.canonical_name).contains(query.lower()),
            KnowledgeNode.aliases.contains(query.lower())
        )
    )

    if entity_type:
        search_query = search_query.where(KnowledgeNode.entity_type == entity_type)

    search_query = search_query.order_by(
        KnowledgeNode.mention_count.desc(),
        KnowledgeNode.last_seen.desc()
    ).limit(limit)

    result = await db.execute(search_query)
    nodes = result.scalars().all()

    return [
        {
            "name": node.canonical_name,
            "type": node.entity_type,
            "aliases": node.aliases,
            "mentioned": node.mention_count,
            "last_seen": node.last_seen.isoformat()
        }
        for node in nodes
    ]


@router.get("/evolution/{entity_name}")
async def get_entity_evolution(
    entity_name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the evolution history of an entity's knowledge over time.

    Shows:
    - When the entity was first discovered
    - How its canonical name changed
    - How metadata was enriched over time
    - Timeline of contexts where it was mentioned

    This demonstrates how knowledge "grows smarter" as more context is processed.
    """
    from db.knowledge_graph_models import KnowledgeNode, EntityKnowledgeLink
    from db.models import Entity, ContextItem
    from sqlalchemy import select, or_, func

    # Find the knowledge node
    node_result = await db.execute(
        select(KnowledgeNode).where(
            or_(
                func.lower(KnowledgeNode.canonical_name) == func.lower(entity_name),
                KnowledgeNode.aliases.contains(entity_name.lower())
            )
        )
    )
    node = node_result.scalar_one_or_none()

    if not node:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_name}' not found")

    # Get all entity mentions linked to this node
    links_result = await db.execute(
        select(EntityKnowledgeLink, Entity, ContextItem)
        .join(Entity, EntityKnowledgeLink.entity_id == Entity.id)
        .join(ContextItem, Entity.context_item_id == ContextItem.id)
        .where(EntityKnowledgeLink.knowledge_node_id == node.id)
        .order_by(Entity.created_at.asc())
    )

    timeline = []
    for link, entity, context in links_result.all():
        timeline.append({
            "timestamp": entity.created_at.isoformat(),
            "name_variant": entity.name,
            "confidence": entity.confidence,
            "similarity_to_canonical": link.similarity_score,
            "context_source": context.source_type,
            "context_id": context.id
        })

    return {
        "entity": node.canonical_name,
        "type": node.entity_type,
        "first_seen": node.first_seen.isoformat(),
        "last_seen": node.last_seen.isoformat(),
        "total_mentions": node.mention_count,
        "aliases": node.aliases,
        "current_metadata": node.metadata,
        "timeline": timeline
    }
