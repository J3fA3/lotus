"""
Task Matcher Service

This service finds related existing tasks based on entities and relationships
from the knowledge graph. It prevents duplicate task creation and enables
intelligent task enrichment.

Matching Strategy:
1. Exact entity match (shared people/projects) → high confidence match
2. Relationship chains (connected entities) → medium confidence match
3. Semantic similarity (optional, deferred to Phase 3) → low confidence match

The matcher ranks results by relevance and returns match metadata for
the orchestrator's decision-making.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from rapidfuzz import fuzz

from db.models import Task, Entity, Relationship


@dataclass
class TaskMatch:
    """A task that matches the current context.

    Attributes:
        task: The matching task dictionary
        similarity: Similarity score (0.0-1.0)
        match_reason: Human-readable explanation of why it matched
        matching_entities: List of entities that overlap
        matching_relationships: List of relationships that connect
    """
    task: Dict
    similarity: float  # 0.0-1.0
    match_reason: str
    matching_entities: List[str]
    matching_relationships: List[str]


class TaskMatcher:
    """Finds related tasks via knowledge graph queries.

    This service queries the database for tasks that share entities or
    relationships with the current context, enabling intelligent task
    enrichment instead of duplication.
    """

    def __init__(self, db: AsyncSession):
        """Initialize task matcher with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def find_related_tasks(
        self,
        entities: List[Dict],
        relationships: List[Dict],
        max_results: int = 10,
        min_similarity: float = 0.3
    ) -> List[TaskMatch]:
        """Find tasks related to the given entities and relationships.

        Strategy:
        1. Find tasks linked to context items that share entities
        2. Calculate similarity based on entity overlap
        3. Boost similarity for relationship chains
        4. Rank by similarity score

        Args:
            entities: Extracted entities from current context
            relationships: Inferred relationships from current context
            max_results: Maximum number of matches to return
            min_similarity: Minimum similarity threshold (0.0-1.0)

        Returns:
            List of TaskMatch objects, sorted by similarity (highest first)
        """
        if not entities:
            return []

        # Extract entity names and types for matching
        entity_names = [e.get("name") for e in entities if e.get("name")]
        entity_types = {e.get("name"): e.get("type") for e in entities if e.get("name")}

        # Get all tasks with their source context
        # We'll match tasks that have context items with overlapping entities
        tasks_query = select(Task).where(
            Task.source_context_id.isnot(None)
        ).limit(100)  # Limit for performance

        result = await self.db.execute(tasks_query)
        tasks = result.scalars().all()

        # Find matches for each task
        matches = []
        for task in tasks:
            match = await self._match_task(
                task, entity_names, entity_types, relationships
            )
            if match and match.similarity >= min_similarity:
                matches.append(match)

        # Sort by similarity (highest first) and limit results
        matches.sort(key=lambda m: m.similarity, reverse=True)
        return matches[:max_results]

    async def _match_task(
        self,
        task: Task,
        context_entity_names: List[str],
        context_entity_types: Dict[str, str],
        context_relationships: List[Dict]
    ) -> Optional[TaskMatch]:
        """Match a single task against context entities and relationships.

        Args:
            task: Task to match against
            context_entity_names: Entity names from current context
            context_entity_types: Entity name -> type mapping
            context_relationships: Relationships from current context

        Returns:
            TaskMatch if similarity > 0, None otherwise
        """
        if not task.source_context_id:
            return None

        # Get entities from the task's source context
        entities_query = select(Entity).where(
            Entity.context_item_id == task.source_context_id
        )
        result = await self.db.execute(entities_query)
        task_entities = result.scalars().all()

        task_entity_names = [e.name for e in task_entities]
        task_entity_types = {e.name: e.type for e in task_entities}

        # Calculate entity overlap
        matching_entities = []
        for context_name in context_entity_names:
            # Exact match
            if context_name in task_entity_names:
                matching_entities.append(context_name)
                continue

            # Fuzzy match (handle "Jef" vs "Jef Adriaenssens")
            for task_name in task_entity_names:
                similarity = fuzz.ratio(context_name.lower(), task_name.lower())
                if similarity > 80:  # 80% similarity threshold
                    matching_entities.append(f"{context_name} ≈ {task_name}")
                    break

        if not matching_entities:
            # No entity overlap - check task fields for fuzzy matches
            task_text = f"{task.title} {task.description or ''} {task.value_stream or ''}".lower()
            fuzzy_matches = [
                name for name in context_entity_names
                if name.lower() in task_text
            ]
            if fuzzy_matches:
                matching_entities = fuzzy_matches
            else:
                return None  # No match

        # Calculate base similarity from entity overlap
        overlap_ratio = len(matching_entities) / max(
            len(context_entity_names),
            len(task_entity_names),
            1
        )
        similarity = overlap_ratio

        # Boost similarity for matching entity types
        # (e.g., both contexts mention the same PROJECT)
        high_value_types = {"PROJECT", "PERSON"}
        for entity_name in matching_entities:
            # Extract actual name if fuzzy match
            actual_name = entity_name.split(" ≈ ")[0] if " ≈ " in entity_name else entity_name
            context_type = context_entity_types.get(actual_name)
            if context_type in high_value_types:
                similarity = min(similarity + 0.1, 1.0)  # +10% per high-value entity

        # Check for relationship chains (connected entities)
        matching_relationships = await self._find_relationship_chains(
            task.source_context_id,
            context_entity_names,
            context_relationships
        )

        if matching_relationships:
            # Boost similarity for relationship matches
            relationship_boost = min(len(matching_relationships) * 0.05, 0.2)  # Max +20%
            similarity = min(similarity + relationship_boost, 1.0)

        # Generate match reason
        match_reason = self._generate_match_reason(
            matching_entities, matching_relationships, task
        )

        # Convert task to dict
        task_dict = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "assignee": task.assignee,
            "due_date": task.due_date,
            "value_stream": task.value_stream,
            "notes": task.notes,
            "confidence_score": task.confidence_score,
            "auto_created": task.auto_created
        }

        return TaskMatch(
            task=task_dict,
            similarity=round(similarity, 2),
            match_reason=match_reason,
            matching_entities=matching_entities,
            matching_relationships=matching_relationships
        )

    async def _find_relationship_chains(
        self,
        task_context_id: int,
        context_entity_names: List[str],
        context_relationships: List[Dict]
    ) -> List[str]:
        """Find relationship chains between task and context.

        Looks for relationships that connect entities from both contexts.

        Args:
            task_context_id: Context ID of the task
            context_entity_names: Entity names from current context
            context_relationships: Relationships from current context

        Returns:
            List of relationship descriptions
        """
        # Get relationships from task's context
        rels_query = select(Relationship).where(
            Relationship.context_item_id == task_context_id
        ).limit(50)  # Limit for performance

        result = await self.db.execute(rels_query)
        task_relationships = result.scalars().all()

        matching_chains = []

        # Build relationship predicates from task
        task_rel_predicates = set()
        for rel in task_relationships:
            # Get entity names via joins
            subject_query = select(Entity.name).where(Entity.id == rel.subject_entity_id)
            object_query = select(Entity.name).where(Entity.id == rel.object_entity_id)

            subject_result = await self.db.execute(subject_query)
            object_result = await self.db.execute(object_query)

            subject_name = subject_result.scalar()
            object_name = object_result.scalar()

            if subject_name and object_name:
                task_rel_predicates.add((subject_name, rel.predicate, object_name))

        # Check for matching relationship patterns in context
        for context_rel in context_relationships:
            subject = context_rel.get("subject")
            predicate = context_rel.get("predicate")
            obj = context_rel.get("object")

            # Exact match
            if (subject, predicate, obj) in task_rel_predicates:
                matching_chains.append(f"{subject} {predicate} {obj}")
                continue

            # Partial match (same predicate, overlapping entities)
            for task_subj, task_pred, task_obj in task_rel_predicates:
                if task_pred == predicate:
                    if task_subj == subject or task_obj == obj:
                        matching_chains.append(
                            f"Similar: {subject} {predicate} {obj} ≈ {task_subj} {task_pred} {task_obj}"
                        )

        return matching_chains

    def _generate_match_reason(
        self,
        matching_entities: List[str],
        matching_relationships: List[str],
        task: Task
    ) -> str:
        """Generate human-readable match reason.

        Args:
            matching_entities: List of entities that matched
            matching_relationships: List of relationships that matched
            task: The matched task

        Returns:
            Human-readable explanation string
        """
        reasons = []

        if matching_entities:
            entity_list = ", ".join(matching_entities[:3])  # First 3
            if len(matching_entities) > 3:
                entity_list += f" (+{len(matching_entities) - 3} more)"
            reasons.append(f"Shared entities: {entity_list}")

        if matching_relationships:
            rel_count = len(matching_relationships)
            reasons.append(f"{rel_count} relationship overlap(s)")

        if not reasons:
            reasons.append("General similarity")

        return "; ".join(reasons)


async def find_duplicate_tasks(
    db: AsyncSession,
    proposed_task: Dict,
    entities: List[Dict],
    relationships: List[Dict],
    similarity_threshold: float = 0.7
) -> Optional[TaskMatch]:
    """Find if proposed task is a duplicate of an existing task.

    This is a convenience function that uses TaskMatcher to find
    high-confidence matches that likely represent the same task.

    Args:
        db: Database session
        proposed_task: Task that might be created
        entities: Entities from context
        relationships: Relationships from context
        similarity_threshold: Minimum similarity to consider duplicate (default 0.7)

    Returns:
        TaskMatch if duplicate found, None otherwise
    """
    matcher = TaskMatcher(db)
    matches = await matcher.find_related_tasks(
        entities=entities,
        relationships=relationships,
        max_results=5,
        min_similarity=similarity_threshold
    )

    if not matches:
        return None

    # Check if top match is likely a duplicate
    top_match = matches[0]

    # Consider duplicate if:
    # 1. High similarity (>= threshold)
    # 2. Same assignee (if specified)
    # 3. Similar title (fuzzy match)

    if top_match.similarity >= similarity_threshold:
        # Check assignee match
        proposed_assignee = proposed_task.get("assignee", "").lower()
        task_assignee = top_match.task.get("assignee", "").lower()

        if proposed_assignee and task_assignee:
            if proposed_assignee not in task_assignee and task_assignee not in proposed_assignee:
                # Different assignees - probably not duplicate
                return None

        # Check title similarity
        proposed_title = proposed_task.get("title", "").lower()
        task_title = top_match.task.get("title", "").lower()

        title_similarity = fuzz.ratio(proposed_title, task_title)
        if title_similarity > 70:  # 70% title match
            return top_match

    return None
