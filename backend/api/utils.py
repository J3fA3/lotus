"""
Common utility functions for API routes.

Provides shared functionality across different API route modules.
"""

from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import Entity


async def get_entity_by_id(db: AsyncSession, entity_id: int) -> Entity:
    """
    Get entity by ID.
    
    Args:
        db: Database session
        entity_id: Entity ID
        
    Returns:
        Entity model instance
        
    Raises:
        ValueError: If entity not found
    """
    result = await db.execute(
        select(Entity).where(Entity.id == entity_id)
    )
    entity = result.scalar_one_or_none()
    
    if not entity:
        raise ValueError(f"Entity with ID {entity_id} not found")
    
    return entity


async def get_entity_map_by_names(db: AsyncSession, entity_names: list[str]) -> Dict[str, Entity]:
    """
    Get a mapping of entity names to entity objects.
    
    Args:
        db: Database session
        entity_names: List of entity names
        
    Returns:
        Dictionary mapping entity names to Entity objects
    """
    if not entity_names:
        return {}
    
    result = await db.execute(
        select(Entity).where(Entity.name.in_(entity_names))
    )
    entities = result.scalars().all()
    
    return {entity.name: entity for entity in entities}


def calculate_quality_score(
    completeness: float,
    accuracy: float,
    weights: tuple[float, float] = (0.5, 0.5)
) -> float:
    """
    Calculate a quality score from completeness and accuracy metrics.
    
    Args:
        completeness: Completeness score (0.0 to 1.0)
        accuracy: Accuracy score (0.0 to 1.0)
        weights: Tuple of (completeness_weight, accuracy_weight)
        
    Returns:
        Combined quality score (0.0 to 1.0)
    """
    w_completeness, w_accuracy = weights
    return (completeness * w_completeness + accuracy * w_accuracy) / sum(weights)
