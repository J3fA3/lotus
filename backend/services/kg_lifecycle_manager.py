"""
Knowledge Graph Lifecycle Manager - Phase 6 Cognitive Nexus

Manages KG health and prevents explosion beyond target size (<5000 nodes).

Key Operations:
1. Archive old data (concepts, conversations older than threshold)
2. Prune weak relationships (strength < threshold)
3. Merge duplicate concepts (similarity > threshold)
4. Rebuild task similarity index (for fast lookups)
5. Monitor KG health metrics

Design Principles:
- Configurable thresholds (not hardcoded)
- Dry-run mode for safe testing
- Audit logging of all operations
- Performance limits (max operations per run)
- Graceful degradation on errors

Scheduling:
- Weekly: Archive, prune, merge (Sunday 3am)
- Daily: Rebuild similarity index (every day 3am)
- On-demand: Health checks, forced cleanup

Usage:
    manager = KGLifecycleManager(db)

    # Dry run (safe testing)
    report = await manager.run_cleanup(dry_run=True)

    # Production run
    report = await manager.run_cleanup(dry_run=False)
"""

from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, and_, or_, update, desc
from datetime import datetime, timedelta
from pydantic import BaseModel
import logging

from db.knowledge_graph_models_v2 import (
    ConceptNode,
    ConversationThreadNode,
    TaskOutcomeNode,
    ConceptRelationship,
    TaskSimilarityIndex,
    ConceptTaskLink
)
from db.models import Task

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

class KGLifecycleConfig(BaseModel):
    """Configuration for KG lifecycle management.

    All thresholds are configurable to allow tuning based on actual usage patterns.
    """
    # Archival thresholds
    archive_concepts_days: int = 180  # 6 months
    archive_conversations_days: int = 180  # 6 months
    keep_archived_days: int = 30  # Keep archived data for 30 days before deletion

    # Pruning thresholds
    weak_relationship_threshold: float = 0.3  # Prune edges with strength < 0.3
    min_concept_mentions: int = 3  # Delete concepts with < 3 total mentions

    # Merging thresholds
    concept_similarity_threshold: float = 0.9  # Merge concepts with similarity > 0.9

    # Performance limits
    max_operations_per_run: int = 1000  # Prevent runaway operations

    # Similarity index
    rebuild_index_if_stale_days: int = 7  # Rebuild if > 7 days old
    similarity_index_top_n: int = 10  # Store top 10 similar tasks


class CleanupReport(BaseModel):
    """Report of cleanup operations performed."""
    dry_run: bool
    started_at: datetime
    completed_at: datetime

    # Operations performed
    concepts_archived: int = 0
    conversations_archived: int = 0
    relationships_pruned: int = 0
    concepts_merged: int = 0
    concepts_deleted: int = 0
    similarity_entries_rebuilt: int = 0

    # Errors
    errors: List[str] = []

    # KG stats before/after
    nodes_before: int = 0
    nodes_after: int = 0
    edges_before: int = 0
    edges_after: int = 0


# ============================================================================
# KG LIFECYCLE MANAGER
# ============================================================================

class KGLifecycleManager:
    """Manages knowledge graph lifecycle and health."""

    def __init__(self, db: AsyncSession, config: Optional[KGLifecycleConfig] = None):
        self.db = db
        self.config = config or KGLifecycleConfig()

    # ========================================================================
    # MAIN CLEANUP ORCHESTRATION
    # ========================================================================

    async def run_cleanup(self, dry_run: bool = True) -> CleanupReport:
        """Run full KG cleanup cycle.

        Operations (in order):
        1. Archive old concepts and conversations
        2. Prune weak relationships
        3. Merge duplicate concepts
        4. Delete low-quality concepts
        5. Rebuild task similarity index

        Args:
            dry_run: If True, only simulate (don't commit changes)

        Returns:
            CleanupReport with details of operations
        """
        report = CleanupReport(
            dry_run=dry_run,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()  # Will be updated at end
        )

        logger.info(f"Starting KG cleanup (dry_run={dry_run})")

        try:
            # Get baseline stats
            report.nodes_before, report.edges_before = await self._get_kg_stats()
            logger.info(f"KG stats: {report.nodes_before} nodes, {report.edges_before} edges")

            # 1. Archive old concepts
            archived_concepts = await self.archive_old_concepts(dry_run=dry_run)
            report.concepts_archived = len(archived_concepts)
            logger.info(f"Archived {len(archived_concepts)} concepts")

            # 2. Archive old conversations
            archived_convos = await self.archive_old_conversations(dry_run=dry_run)
            report.conversations_archived = len(archived_convos)
            logger.info(f"Archived {len(archived_convos)} conversations")

            # 3. Prune weak relationships
            pruned_rels = await self.prune_weak_relationships(dry_run=dry_run)
            report.relationships_pruned = len(pruned_rels)
            logger.info(f"Pruned {len(pruned_rels)} weak relationships")

            # 4. Merge duplicate concepts
            merged_concepts = await self.merge_duplicate_concepts(dry_run=dry_run)
            report.concepts_merged = len(merged_concepts)
            logger.info(f"Merged {len(merged_concepts)} duplicate concepts")

            # 5. Delete low-quality concepts
            deleted_concepts = await self.delete_low_quality_concepts(dry_run=dry_run)
            report.concepts_deleted = len(deleted_concepts)
            logger.info(f"Deleted {len(deleted_concepts)} low-quality concepts")

            # 6. Rebuild similarity index (always do this, even in dry run for testing)
            if not dry_run:
                rebuilt = await self.rebuild_similarity_index()
                report.similarity_entries_rebuilt = rebuilt
                logger.info(f"Rebuilt {rebuilt} similarity index entries")

            # Get final stats
            report.nodes_after, report.edges_after = await self._get_kg_stats()

            # Commit if not dry run
            if not dry_run:
                await self.db.commit()
                logger.info("KG cleanup committed successfully")
            else:
                await self.db.rollback()
                logger.info("KG cleanup rolled back (dry run)")

        except Exception as e:
            logger.error(f"KG cleanup failed: {e}")
            report.errors.append(str(e))
            await self.db.rollback()

        report.completed_at = datetime.utcnow()
        return report

    # ========================================================================
    # ARCHIVAL OPERATIONS
    # ========================================================================

    async def archive_old_concepts(self, dry_run: bool = True) -> List[int]:
        """Archive concepts not mentioned in X months.

        Archival strategy:
        - Set archived_at timestamp (soft delete)
        - Keep data for 30 days before hard delete
        - Only archive if mention_count_30d == 0 (not actively used)

        Args:
            dry_run: If True, only identify (don't update)

        Returns:
            List of archived concept IDs
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.config.archive_concepts_days)

        # Find concepts to archive
        result = await self.db.execute(
            select(ConceptNode.id).where(
                and_(
                    ConceptNode.last_mentioned < cutoff_date,
                    ConceptNode.mention_count_30d == 0,  # Not actively used
                    ConceptNode.archived_at.is_(None)  # Not already archived
                )
            ).limit(self.config.max_operations_per_run)
        )
        concept_ids = [row[0] for row in result.fetchall()]

        if not dry_run and concept_ids:
            # Archive concepts (soft delete)
            await self.db.execute(
                update(ConceptNode)
                .where(ConceptNode.id.in_(concept_ids))
                .values(archived_at=datetime.utcnow())
            )

        return concept_ids

    async def archive_old_conversations(self, dry_run: bool = True) -> List[int]:
        """Archive conversations older than X months.

        Args:
            dry_run: If True, only identify (don't update)

        Returns:
            List of archived conversation IDs
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.config.archive_conversations_days)

        # Find conversations to archive
        result = await self.db.execute(
            select(ConversationThreadNode.id).where(
                and_(
                    ConversationThreadNode.last_updated < cutoff_date,
                    ConversationThreadNode.is_archived == False
                )
            ).limit(self.config.max_operations_per_run)
        )
        conversation_ids = [row[0] for row in result.fetchall()]

        if not dry_run and conversation_ids:
            # Archive conversations
            await self.db.execute(
                update(ConversationThreadNode)
                .where(ConversationThreadNode.id.in_(conversation_ids))
                .values(
                    is_archived=True,
                    is_active=False,
                    archived_at=datetime.utcnow()
                )
            )

        return conversation_ids

    # ========================================================================
    # PRUNING OPERATIONS
    # ========================================================================

    async def prune_weak_relationships(self, dry_run: bool = True) -> List[int]:
        """Prune relationships with strength below threshold.

        Weak relationships are likely noise or outdated connections.

        Args:
            dry_run: If True, only identify (don't delete)

        Returns:
            List of pruned relationship IDs
        """
        # Find weak relationships
        result = await self.db.execute(
            select(ConceptRelationship.id).where(
                ConceptRelationship.strength < self.config.weak_relationship_threshold
            ).limit(self.config.max_operations_per_run)
        )
        relationship_ids = [row[0] for row in result.fetchall()]

        if not dry_run and relationship_ids:
            # Delete weak relationships
            await self.db.execute(
                delete(ConceptRelationship).where(
                    ConceptRelationship.id.in_(relationship_ids)
                )
            )

        return relationship_ids

    async def delete_low_quality_concepts(self, dry_run: bool = True) -> List[int]:
        """Delete concepts with very low mention counts.

        Concepts mentioned < 3 times are likely noise.

        Args:
            dry_run: If True, only identify (don't delete)

        Returns:
            List of deleted concept IDs
        """
        # Find low-quality concepts
        result = await self.db.execute(
            select(ConceptNode.id).where(
                and_(
                    ConceptNode.mention_count_total < self.config.min_concept_mentions,
                    ConceptNode.confidence_tier == "TENTATIVE"  # Only delete tentative ones
                )
            ).limit(self.config.max_operations_per_run)
        )
        concept_ids = [row[0] for row in result.fetchall()]

        if not dry_run and concept_ids:
            # Delete concepts (cascade will delete relationships)
            await self.db.execute(
                delete(ConceptNode).where(
                    ConceptNode.id.in_(concept_ids)
                )
            )

        return concept_ids

    # ========================================================================
    # MERGING OPERATIONS
    # ========================================================================

    async def merge_duplicate_concepts(self, dry_run: bool = True) -> List[Tuple[int, int]]:
        """Merge concepts with very high similarity.

        Strategy:
        1. Find concept pairs with similarity > threshold
        2. Merge less-important concept into more-important one
        3. Update all relationships and task links

        Args:
            dry_run: If True, only identify (don't merge)

        Returns:
            List of (merged_from_id, merged_into_id) tuples
        """
        # TODO: Implement semantic similarity comparison
        # For now, just find exact duplicates (case-insensitive)

        merged_pairs = []

        # Find duplicate concept names (simple case)
        result = await self.db.execute(
            select(
                func.lower(ConceptNode.name).label('name_lower'),
                func.array_agg(ConceptNode.id).label('concept_ids')
            )
            .where(ConceptNode.archived_at.is_(None))
            .group_by(func.lower(ConceptNode.name))
            .having(func.count(ConceptNode.id) > 1)
        )

        for row in result.fetchall():
            concept_ids = row.concept_ids
            if len(concept_ids) > 1:
                # Merge all but the most important one
                # Get full concepts to determine which to keep
                concepts_result = await self.db.execute(
                    select(ConceptNode).where(ConceptNode.id.in_(concept_ids))
                    .order_by(desc(ConceptNode.importance_score))
                )
                concepts = list(concepts_result.scalars().all())

                # Keep the most important, merge others into it
                keep_concept = concepts[0]
                merge_concepts = concepts[1:]

                for merge_concept in merge_concepts:
                    if not dry_run:
                        await self._merge_concept_into(merge_concept.id, keep_concept.id)
                    merged_pairs.append((merge_concept.id, keep_concept.id))

        return merged_pairs[:self.config.max_operations_per_run]

    async def _merge_concept_into(self, from_id: int, into_id: int):
        """Merge one concept into another.

        Updates:
        - ConceptTaskLinks: Point to new concept
        - ConceptRelationships: Update references
        - Delete old concept
        """
        # Update concept task links
        await self.db.execute(
            update(ConceptTaskLink)
            .where(ConceptTaskLink.concept_id == from_id)
            .values(concept_id=into_id)
        )

        # Update concept relationships (both subject and object)
        await self.db.execute(
            update(ConceptRelationship)
            .where(ConceptRelationship.concept_id == from_id)
            .values(concept_id=into_id)
        )
        await self.db.execute(
            update(ConceptRelationship)
            .where(ConceptRelationship.related_to_id == from_id)
            .values(related_to_id=into_id)
        )

        # Delete old concept
        await self.db.execute(
            delete(ConceptNode).where(ConceptNode.id == from_id)
        )

    # ========================================================================
    # SIMILARITY INDEX REBUILD
    # ========================================================================

    async def rebuild_similarity_index(self) -> int:
        """Rebuild task similarity index for fast lookups.

        This is computationally expensive, so only rebuild stale entries.

        Strategy:
        1. Find tasks without index or stale index (>7 days)
        2. Compute top N similar tasks for each
        3. Store in TaskSimilarityIndex

        Returns:
            Number of entries rebuilt
        """
        # Find tasks needing index rebuild
        cutoff_date = datetime.utcnow() - timedelta(days=self.config.rebuild_index_if_stale_days)

        # Get all tasks
        result = await self.db.execute(
            select(Task.id, Task.title, Task.description)
        )
        all_tasks = list(result.fetchall())

        # Find tasks without index or stale index
        result = await self.db.execute(
            select(TaskSimilarityIndex.task_id).where(
                or_(
                    TaskSimilarityIndex.computed_at >= cutoff_date,
                    TaskSimilarityIndex.is_stale == False
                )
            )
        )
        indexed_task_ids = {row[0] for row in result.fetchall()}

        # Tasks needing rebuild
        tasks_to_index = [
            t for t in all_tasks
            if t.id not in indexed_task_ids
        ][:self.config.max_operations_per_run]

        rebuilt_count = 0

        for task in tasks_to_index:
            # TODO: Implement semantic similarity
            # For now, create empty index entry

            # Check if index exists
            existing = await self.db.execute(
                select(TaskSimilarityIndex).where(
                    TaskSimilarityIndex.task_id == task.id
                )
            )
            index_entry = existing.scalar_one_or_none()

            if index_entry:
                # Update existing
                index_entry.similar_task_ids = []
                index_entry.similar_task_titles = []
                index_entry.similarity_scores = []
                index_entry.similarity_explanations = []
                index_entry.computed_at = datetime.utcnow()
                index_entry.is_stale = False
            else:
                # Create new
                index_entry = TaskSimilarityIndex(
                    task_id=task.id,
                    similar_task_ids=[],
                    similar_task_titles=[],
                    similarity_scores=[],
                    similarity_explanations=[],
                    computed_at=datetime.utcnow(),
                    is_stale=False
                )
                self.db.add(index_entry)

            rebuilt_count += 1

        return rebuilt_count

    # ========================================================================
    # HEALTH MONITORING
    # ========================================================================

    async def get_health_report(self) -> Dict:
        """Get KG health metrics.

        Returns:
            Dict with health metrics
        """
        # Get counts
        nodes_count, edges_count = await self._get_kg_stats()

        # Get concept stats
        result = await self.db.execute(
            select(
                func.count(ConceptNode.id).label('total'),
                func.avg(ConceptNode.importance_score).label('avg_importance'),
                func.count(ConceptNode.id).filter(
                    ConceptNode.confidence_tier == "ESTABLISHED"
                ).label('established_count')
            )
        )
        concept_stats = result.fetchone()

        # Get relationship stats
        result = await self.db.execute(
            select(
                func.count(ConceptRelationship.id).label('total'),
                func.avg(ConceptRelationship.strength).label('avg_strength')
            )
        )
        relationship_stats = result.fetchone()

        # Get outcome stats
        result = await self.db.execute(
            select(
                func.count(TaskOutcomeNode.task_id).label('total'),
                func.avg(TaskOutcomeNode.completion_quality).label('avg_quality'),
                func.count(TaskOutcomeNode.task_id).filter(
                    TaskOutcomeNode.outcome == "COMPLETED"
                ).label('completed_count')
            )
        )
        outcome_stats = result.fetchone()

        return {
            "kg_size": {
                "total_nodes": nodes_count,
                "total_edges": edges_count,
                "target": 5000,
                "health": "healthy" if nodes_count < 5000 else "warning"
            },
            "concepts": {
                "total": concept_stats.total,
                "avg_importance": float(concept_stats.avg_importance) if concept_stats.avg_importance else 0.0,
                "established_count": concept_stats.established_count,
                "established_percentage": (concept_stats.established_count / concept_stats.total * 100) if concept_stats.total else 0
            },
            "relationships": {
                "total": relationship_stats.total,
                "avg_strength": float(relationship_stats.avg_strength) if relationship_stats.avg_strength else 0.0
            },
            "outcomes": {
                "total": outcome_stats.total,
                "avg_quality": float(outcome_stats.avg_quality) if outcome_stats.avg_quality else 0.0,
                "completed_count": outcome_stats.completed_count
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _get_kg_stats(self) -> Tuple[int, int]:
        """Get node and edge counts.

        Returns:
            (node_count, edge_count)
        """
        # Count nodes (concepts + conversations + outcomes)
        concept_count = await self.db.scalar(
            select(func.count(ConceptNode.id)).where(
                ConceptNode.archived_at.is_(None)
            )
        ) or 0

        conversation_count = await self.db.scalar(
            select(func.count(ConversationThreadNode.id)).where(
                ConversationThreadNode.is_archived == False
            )
        ) or 0

        outcome_count = await self.db.scalar(
            select(func.count(TaskOutcomeNode.task_id))
        ) or 0

        total_nodes = concept_count + conversation_count + outcome_count

        # Count edges
        edge_count = await self.db.scalar(
            select(func.count(ConceptRelationship.id))
        ) or 0

        return total_nodes, edge_count


async def get_kg_lifecycle_manager(
    db: AsyncSession,
    config: Optional[KGLifecycleConfig] = None
) -> KGLifecycleManager:
    """Factory function to get KG lifecycle manager.

    Args:
        db: Database session
        config: Optional custom configuration

    Returns:
        KGLifecycleManager instance
    """
    return KGLifecycleManager(db, config)
