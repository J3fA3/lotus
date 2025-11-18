"""
Knowledge Graph Service - Best-in-Class Cross-Context Knowledge Management

This service provides:
1. **Fuzzy Entity Deduplication** - Intelligently merge similar entities
2. **Relationship Aggregation** - Track relationship strength over time
3. **Dynamic Structure Learning** - Discover team structures from context
4. **Temporal Evolution** - Knowledge that grows smarter over time
5. **Quality-Based Merging** - Use confidence scores to improve canonical names

Key Principles:
- No hardcoded structures - learns from data
- Gracefully handles ambiguity
- Evolves with new information
- Maintains historical context
"""

from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update
from datetime import datetime, timedelta
import difflib
import re
import json
import math

from db.models import Entity, Relationship
from db.knowledge_graph_models import (
    KnowledgeNode,
    KnowledgeEdge,
    EntityKnowledgeLink,
    TeamStructureEvolution,
    KnowledgeGraphStats
)
from services.knowledge_graph_config import config
from services.knowledge_graph_embeddings import embedding_service


class KnowledgeGraphService:
    """Manages the living knowledge graph that evolves over time."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # ENTITY DEDUPLICATION
    # ========================================================================

    async def merge_entity_to_knowledge_graph(self, entity: Entity) -> KnowledgeNode:
        """Merge a newly extracted entity into the knowledge graph.

        This is the core deduplication algorithm. It:
        1. Finds candidate matches using fuzzy matching
        2. Evaluates similarity scores
        3. Either merges with existing node or creates new one
        4. Updates metadata and statistics
        5. Learns new team structures if applicable

        Args:
            entity: The raw extracted entity

        Returns:
            The knowledge node (existing or new) that this entity maps to
        """
        # Find candidate matches
        candidates = await self._find_candidate_nodes(entity)

        if candidates:
            # Evaluate which candidate is the best match
            best_match, similarity = await self._select_best_match(entity, candidates)

            if similarity >= 0.75:  # High confidence match
                # Merge with existing node
                node = await self._merge_with_existing_node(entity, best_match, similarity, "fuzzy")
            elif similarity >= 0.60:  # Medium confidence - could be same entity
                # For now, merge but track lower confidence
                # Future: could ask user for confirmation
                node = await self._merge_with_existing_node(entity, best_match, similarity, "fuzzy_low_conf")
            else:
                # Too low - create new node
                node = await self._create_new_knowledge_node(entity)
        else:
            # No candidates - definitely new
            node = await self._create_new_knowledge_node(entity)

        # Link entity to knowledge node
        await self._create_entity_link(entity, node, similarity if candidates else 1.0)

        # Learn team structures if this is a TEAM entity
        if entity.type == "TEAM" and entity.entity_metadata:
            await self._learn_team_structure(entity, node)

        return node

    async def _find_candidate_nodes(self, entity: Entity) -> List[KnowledgeNode]:
        """Find potential matching knowledge nodes for an entity.

        Uses multiple strategies:
        1. Exact name match (case-insensitive)
        2. Alias match
        3. Fuzzy name match (for similar strings)
        4. Type-specific matching (e.g., date normalization)
        """
        candidates = []

        # Strategy 1: Exact match (case-insensitive)
        result = await self.db.execute(
            select(KnowledgeNode).where(
                and_(
                    func.lower(KnowledgeNode.canonical_name) == func.lower(entity.name),
                    KnowledgeNode.entity_type == entity.type
                )
            )
        )
        exact_match = result.scalar_one_or_none()
        if exact_match:
            return [exact_match]  # Perfect match, no need to look further

        # Strategy 2: Alias match
        result = await self.db.execute(
            select(KnowledgeNode).where(
                and_(
                    KnowledgeNode.entity_type == entity.type,
                    KnowledgeNode.aliases.contains(entity.name.lower())
                )
            )
        )
        alias_matches = result.scalars().all()
        if alias_matches:
            candidates.extend(alias_matches)

        # Strategy 3: Fuzzy match on same type
        # Get all nodes of the same type for fuzzy comparison
        result = await self.db.execute(
            select(KnowledgeNode).where(
                KnowledgeNode.entity_type == entity.type
            )
        )
        same_type_nodes = result.scalars().all()

        for node in same_type_nodes:
            if node not in candidates:
                # Use difflib for fuzzy string matching
                similarity = self._calculate_string_similarity(
                    entity.name.lower(),
                    node.canonical_name.lower()
                )
                if similarity >= 0.60:  # Threshold for considering as candidate
                    candidates.append(node)

        return candidates

    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings.

        Uses multiple algorithms:
        1. Sequence matcher for edit distance
        2. Token overlap for multi-word names
        3. Abbreviation detection

        Returns:
            Similarity score from 0.0 to 1.0
        """
        # Basic sequence matcher
        base_similarity = difflib.SequenceMatcher(None, str1, str2).ratio()

        # Token-based matching (handles "jef adriaenssens" vs "adriaenssens jef")
        tokens1 = set(str1.split())
        tokens2 = set(str2.split())
        if tokens1 and tokens2:
            token_overlap = len(tokens1 & tokens2) / max(len(tokens1), len(tokens2))
        else:
            token_overlap = 0.0

        # Abbreviation matching ("Jef A" vs "Jef Adriaenssens")
        abbrev_score = 0.0
        if len(str1) < len(str2):
            short, long = str1, str2
        else:
            short, long = str2, str1

        if all(c in long for c in short if c.isalnum()):
            abbrev_score = 0.3  # Bonus for potential abbreviation

        # Weighted combination
        final_score = max(
            base_similarity,
            token_overlap,
            base_similarity + abbrev_score
        )

        return final_score

    async def _select_best_match(
        self,
        entity: Entity,
        candidates: List[KnowledgeNode]
    ) -> Tuple[KnowledgeNode, float]:
        """Select the best matching candidate from a list.

        Considers:
        - String similarity
        - Mention count (more mentioned = more canonical)
        - Recency (recently seen = more relevant)
        - Confidence scores

        Returns:
            (best_node, similarity_score)
        """
        best_node = None
        best_score = 0.0

        for candidate in candidates:
            # Calculate similarity
            similarity = self._calculate_string_similarity(
                entity.name.lower(),
                candidate.canonical_name.lower()
            )

            # Boost score based on candidate's mention count (more mentions = more canonical)
            mention_boost = min(candidate.mention_count / 100.0, 0.1)  # Up to +0.1

            # Boost score based on recency (recently seen = more relevant)
            days_since_seen = (datetime.utcnow() - candidate.last_seen).days
            recency_boost = max(0, 0.1 - (days_since_seen / 100.0))  # Up to +0.1

            # Combined score
            combined_score = similarity + mention_boost + recency_boost

            if combined_score > best_score:
                best_score = combined_score
                best_node = candidate

        return best_node, min(best_score, 1.0)  # Cap at 1.0

    async def _merge_with_existing_node(
        self,
        entity: Entity,
        node: KnowledgeNode,
        similarity: float,
        match_method: str
    ) -> KnowledgeNode:
        """Merge an entity into an existing knowledge node.

        Updates:
        - mention_count
        - last_seen
        - aliases (if new name variant)
        - metadata (enriches with new information)
        - canonical_name (if new name is better)
        - average_confidence
        """
        # Update mention count
        node.mention_count += 1

        # Update timestamps
        node.last_seen = datetime.utcnow()

        # Add name as alias if not already present
        entity_name_lower = entity.name.lower()
        if entity_name_lower not in node.aliases:
            if node.aliases is None:
                node.aliases = []
            node.aliases.append(entity_name_lower)

        # Update canonical name if this entity has higher confidence
        if entity.confidence > node.average_confidence:
            # Better name found - update canonical
            old_canonical = node.canonical_name
            node.canonical_name = entity.name

            # Add old canonical to aliases
            if old_canonical.lower() not in node.aliases:
                node.aliases.append(old_canonical.lower())

        # Update average confidence (running average)
        total_confidence = node.average_confidence * (node.mention_count - 1) + entity.confidence
        node.average_confidence = total_confidence / node.mention_count

        # Merge metadata (for TEAM entities)
        if entity.type == "TEAM" and entity.entity_metadata:
            node.entity_metadata = self._merge_metadata(node.entity_metadata, entity.entity_metadata)

        # For PERSON entities, track teams they're mentioned with
        if entity.type == "PERSON":
            # This will be enriched by relationship data later
            pass

        await self.db.flush()
        return node

    def _merge_metadata(self, existing: Optional[Dict], new: Dict) -> Dict:
        """Intelligently merge metadata, accumulating seen values.

        For TEAM entities:
        - Accumulates all seen pillars, teams, roles
        - Tracks confidence per field
        - Preserves historical values
        """
        if not existing:
            existing = {}

        # Initialize structure if needed
        if "pillars" not in existing:
            existing["pillars"] = []
        if "team_names" not in existing:
            existing["team_names"] = []
        if "roles" not in existing:
            existing["roles"] = []

        # Add new values
        if "pillar" in new and new["pillar"] not in existing["pillars"]:
            existing["pillars"].append(new["pillar"])

        if "team_name" in new and new["team_name"] not in existing["team_names"]:
            existing["team_names"].append(new["team_name"])

        if "role" in new and new["role"] not in existing["roles"]:
            existing["roles"].append(new["role"])

        return existing

    async def _create_new_knowledge_node(self, entity: Entity) -> KnowledgeNode:
        """Create a new knowledge node for a truly new entity."""
        node = KnowledgeNode(
            canonical_name=entity.name,
            entity_type=entity.type,
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            mention_count=1,
            metadata=self._initialize_metadata(entity),
            aliases=[entity.name.lower()],
            average_confidence=entity.confidence
        )

        self.db.add(node)
        await self.db.flush()
        return node

    def _initialize_metadata(self, entity: Entity) -> Optional[Dict]:
        """Initialize metadata structure for a new knowledge node."""
        if entity.type == "TEAM" and entity.entity_metadata:
            return {
                "pillars": [entity.entity_metadata.get("pillar")] if entity.entity_metadata.get("pillar") else [],
                "team_names": [entity.entity_metadata.get("team_name")] if entity.entity_metadata.get("team_name") else [],
                "roles": [entity.entity_metadata.get("role")] if entity.entity_metadata.get("role") else []
            }
        return {}

    async def _create_entity_link(
        self,
        entity: Entity,
        node: KnowledgeNode,
        similarity: float
    ):
        """Create a link between raw entity and knowledge node."""
        link = EntityKnowledgeLink(
            entity_id=entity.id,
            knowledge_node_id=node.id,
            similarity_score=similarity,
            match_method="exact" if similarity == 1.0 else "fuzzy"
        )
        self.db.add(link)
        await self.db.flush()

    # ========================================================================
    # TEAM STRUCTURE LEARNING
    # ========================================================================

    async def _learn_team_structure(self, entity: Entity, node: KnowledgeNode):
        """Dynamically learn and record team structure from entity metadata.

        This is the key to making the system adapt to organizational reality.
        Instead of hardcoding "Customer Pillar" or "Menu Team", we discover
        these from actual usage and track their evolution.
        """
        if not entity.entity_metadata:
            return

        # Learn pillar
        if "pillar" in entity.entity_metadata:
            await self._record_structure_element(
                structure_type="pillar",
                structure_name=entity.entity_metadata["pillar"],
                parent_id=None,
                node_id=node.id
            )

        # Learn team
        if "team_name" in entity.entity_metadata:
            parent_id = None
            # If pillar is also specified, link team to pillar
            if "pillar" in entity.entity_metadata:
                parent_id = await self._get_structure_id("pillar", entity.entity_metadata["pillar"])

            await self._record_structure_element(
                structure_type="team",
                structure_name=entity.entity_metadata["team_name"],
                parent_id=parent_id,
                node_id=node.id
            )

        # Learn role
        if "role" in entity.entity_metadata:
            parent_id = None
            # Roles can be under teams if specified
            if "team_name" in entity.entity_metadata:
                parent_id = await self._get_structure_id("team", entity.entity_metadata["team_name"])

            await self._record_structure_element(
                structure_type="role",
                structure_name=entity.entity_metadata["role"],
                parent_id=parent_id,
                node_id=node.id
            )

    async def _record_structure_element(
        self,
        structure_type: str,
        structure_name: str,
        parent_id: Optional[int],
        node_id: int
    ):
        """Record or update a structure element in the org chart."""
        # Check if this structure element already exists
        result = await self.db.execute(
            select(TeamStructureEvolution).where(
                and_(
                    TeamStructureEvolution.structure_type == structure_type,
                    TeamStructureEvolution.structure_name == structure_name
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            existing.mention_count += 1
            existing.last_seen = datetime.utcnow()
            existing.context_count += 1

            # Add node to associated nodes if not already there
            if existing.associated_nodes is None:
                existing.associated_nodes = []
            if node_id not in existing.associated_nodes:
                existing.associated_nodes.append(node_id)

        else:
            # Create new
            structure = TeamStructureEvolution(
                structure_type=structure_type,
                structure_name=structure_name,
                parent_structure_id=parent_id,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                mention_count=1,
                context_count=1,
                associated_nodes=[node_id]
            )
            self.db.add(structure)

        await self.db.flush()

    async def _get_structure_id(self, structure_type: str, structure_name: str) -> Optional[int]:
        """Get the ID of a structure element."""
        result = await self.db.execute(
            select(TeamStructureEvolution.id).where(
                and_(
                    TeamStructureEvolution.structure_type == structure_type,
                    TeamStructureEvolution.structure_name == structure_name
                )
            )
        )
        return result.scalar_one_or_none()

    # ========================================================================
    # RELATIONSHIP AGGREGATION
    # ========================================================================

    async def aggregate_relationship(
        self,
        subject_entity: Entity,
        predicate: str,
        object_entity: Entity,
        confidence: float,
        context_item_id: int
    ) -> KnowledgeEdge:
        """Aggregate a relationship into the knowledge graph.

        Takes a relationship from a specific context and merges it into
        the aggregate knowledge graph, updating strength scores.
        """
        # Get or create knowledge nodes for subject and object
        subject_node = await self._get_or_create_node_for_entity(subject_entity)
        object_node = await self._get_or_create_node_for_entity(object_entity)

        # Find existing edge
        result = await self.db.execute(
            select(KnowledgeEdge).where(
                and_(
                    KnowledgeEdge.subject_node_id == subject_node.id,
                    KnowledgeEdge.predicate == predicate,
                    KnowledgeEdge.object_node_id == object_node.id
                )
            )
        )
        edge = result.scalar_one_or_none()

        if edge:
            # Update existing edge
            edge.mention_count += 1
            edge.context_count += 1  # Assuming different context
            edge.last_seen = datetime.utcnow()

            # Update average confidence (running average)
            total_confidence = edge.average_confidence * (edge.mention_count - 1) + confidence
            edge.average_confidence = total_confidence / edge.mention_count

            # Recalculate strength
            edge.strength = self._calculate_edge_strength(
                edge.mention_count,
                edge.context_count,
                edge.average_confidence
            )

        else:
            # Create new edge
            edge = KnowledgeEdge(
                subject_node_id=subject_node.id,
                predicate=predicate,
                object_node_id=object_node.id,
                strength=confidence,  # Initial strength = confidence
                mention_count=1,
                context_count=1,
                average_confidence=confidence,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow()
            )
            self.db.add(edge)

        await self.db.flush()
        return edge

    def _calculate_edge_strength(
        self,
        mention_count: int,
        context_count: int,
        average_confidence: float
    ) -> float:
        """Calculate relationship strength (0.0 to 1.0).

        Formula:
        strength = (mention_weight * confidence_weight * diversity_weight)^0.5

        Where:
        - mention_weight = min(mention_count / 10, 1.0)  # Caps at 10 mentions
        - confidence_weight = average_confidence
        - diversity_weight = min(context_count / 5, 1.0)  # Caps at 5 contexts

        Square root to prevent over-weighting
        """
        mention_weight = min(mention_count / 10.0, 1.0)
        confidence_weight = average_confidence
        diversity_weight = min(context_count / 5.0, 1.0)

        strength = (mention_weight * confidence_weight * diversity_weight) ** 0.5

        return min(strength, 1.0)  # Cap at 1.0

    async def _get_or_create_node_for_entity(self, entity: Entity) -> KnowledgeNode:
        """Get the knowledge node for an entity (assumes already merged)."""
        # Check if entity already linked to a node
        result = await self.db.execute(
            select(EntityKnowledgeLink).where(
                EntityKnowledgeLink.entity_id == entity.id
            )
        )
        link = result.scalar_one_or_none()

        if link:
            # Get the linked node
            result = await self.db.execute(
                select(KnowledgeNode).where(
                    KnowledgeNode.id == link.knowledge_node_id
                )
            )
            return result.scalar_one()
        else:
            # Entity not yet merged - merge it now
            return await self.merge_entity_to_knowledge_graph(entity)

    # ========================================================================
    # QUERY API
    # ========================================================================

    async def get_entity_knowledge(self, entity_name: str, entity_type: Optional[str] = None) -> Optional[Dict]:
        """Get all knowledge about an entity.

        Returns comprehensive information:
        - Canonical name and aliases
        - Mention statistics
        - All relationships (incoming and outgoing)
        - Team structure associations
        - Temporal evolution
        """
        # Find the node
        query = select(KnowledgeNode).where(
            or_(
                func.lower(KnowledgeNode.canonical_name) == func.lower(entity_name),
                KnowledgeNode.aliases.contains(entity_name.lower())
            )
        )
        if entity_type:
            query = query.where(KnowledgeNode.entity_type == entity_type)

        result = await self.db.execute(query)
        node = result.scalar_one_or_none()

        if not node:
            return None

        # Get outgoing relationships
        outgoing = await self.db.execute(
            select(KnowledgeEdge, KnowledgeNode).join(
                KnowledgeNode, KnowledgeEdge.object_node_id == KnowledgeNode.id
            ).where(KnowledgeEdge.subject_node_id == node.id)
        )
        outgoing_rels = [
            {
                "type": edge.predicate,
                "target": target.canonical_name,
                "target_type": target.entity_type,
                "strength": edge.strength,
                "mentioned_in": edge.mention_count,
                "contexts": edge.context_count
            }
            for edge, target in outgoing.all()
        ]

        # Get incoming relationships
        incoming = await self.db.execute(
            select(KnowledgeEdge, KnowledgeNode).join(
                KnowledgeNode, KnowledgeEdge.subject_node_id == KnowledgeNode.id
            ).where(KnowledgeEdge.object_node_id == node.id)
        )
        incoming_rels = [
            {
                "type": edge.predicate,
                "source": source.canonical_name,
                "source_type": source.entity_type,
                "strength": edge.strength,
                "mentioned_in": edge.mention_count,
                "contexts": edge.context_count
            }
            for edge, source in incoming.all()
        ]

        return {
            "entity": node.canonical_name,
            "type": node.entity_type,
            "aliases": node.aliases,
            "mentioned_in": node.mention_count,
            "first_seen": node.first_seen.isoformat(),
            "last_seen": node.last_seen.isoformat(),
            "average_confidence": node.average_confidence,
            "metadata": node.entity_metadata,
            "relationships": {
                "outgoing": outgoing_rels,
                "incoming": incoming_rels
            }
        }

    async def get_discovered_team_structures(self) -> Dict:
        """Get all discovered team structures organized hierarchically."""
        # Get all pillars
        pillars_result = await self.db.execute(
            select(TeamStructureEvolution).where(
                TeamStructureEvolution.structure_type == "pillar"
            ).order_by(TeamStructureEvolution.mention_count.desc())
        )
        pillars = pillars_result.scalars().all()

        structures = []
        for pillar in pillars:
            # Get teams under this pillar
            teams_result = await self.db.execute(
                select(TeamStructureEvolution).where(
                    TeamStructureEvolution.parent_structure_id == pillar.id
                ).order_by(TeamStructureEvolution.mention_count.desc())
            )
            teams = teams_result.scalars().all()

            pillar_data = {
                "name": pillar.structure_name,
                "type": "pillar",
                "mentioned": pillar.mention_count,
                "contexts": pillar.context_count,
                "first_seen": pillar.first_seen.isoformat(),
                "teams": []
            }

            for team in teams:
                # Get roles under this team
                roles_result = await self.db.execute(
                    select(TeamStructureEvolution).where(
                        TeamStructureEvolution.parent_structure_id == team.id
                    ).order_by(TeamStructureEvolution.mention_count.desc())
                )
                roles = roles_result.scalars().all()

                team_data = {
                    "name": team.structure_name,
                    "type": "team",
                    "mentioned": team.mention_count,
                    "contexts": team.context_count,
                    "roles": [
                        {
                            "name": role.structure_name,
                            "mentioned": role.mention_count,
                            "contexts": role.context_count
                        }
                        for role in roles
                    ]
                }
                pillar_data["teams"].append(team_data)

            structures.append(pillar_data)

        # Get standalone teams (no pillar parent)
        standalone_teams = await self.db.execute(
            select(TeamStructureEvolution).where(
                and_(
                    TeamStructureEvolution.structure_type == "team",
                    TeamStructureEvolution.parent_structure_id == None
                )
            ).order_by(TeamStructureEvolution.mention_count.desc())
        )

        for team in standalone_teams.scalars().all():
            structures.append({
                "name": team.structure_name,
                "type": "team",
                "mentioned": team.mention_count,
                "contexts": team.context_count,
                "parent": None
            })

        # Get standalone roles
        standalone_roles = await self.db.execute(
            select(TeamStructureEvolution).where(
                and_(
                    TeamStructureEvolution.structure_type == "role",
                    TeamStructureEvolution.parent_structure_id == None
                )
            ).order_by(TeamStructureEvolution.mention_count.desc())
        )

        for role in standalone_roles.scalars().all():
            structures.append({
                "name": role.structure_name,
                "type": "role",
                "mentioned": role.mention_count,
                "contexts": role.context_count,
                "parent": None
            })

        return {
            "structures": structures,
            "total_pillars": len(pillars),
            "total_teams": len(teams) + len(list(standalone_teams.scalars().all())),
            "total_roles": sum(len(p.get("teams", [])) for p in structures if p["type"] == "pillar") + len(list(standalone_roles.scalars().all()))
        }

    async def compute_graph_stats(self) -> Dict:
        """Compute current knowledge graph statistics."""
        # Count nodes
        total_nodes_result = await self.db.execute(
            select(func.count(KnowledgeNode.id))
        )
        total_nodes = total_nodes_result.scalar()

        # Nodes by type
        nodes_by_type_result = await self.db.execute(
            select(
                KnowledgeNode.entity_type,
                func.count(KnowledgeNode.id)
            ).group_by(KnowledgeNode.entity_type)
        )
        nodes_by_type = {row[0]: row[1] for row in nodes_by_type_result.all()}

        # Count edges
        total_edges_result = await self.db.execute(
            select(func.count(KnowledgeEdge.id))
        )
        total_edges = total_edges_result.scalar()

        # Top mentioned nodes
        top_nodes_result = await self.db.execute(
            select(KnowledgeNode).order_by(
                KnowledgeNode.mention_count.desc()
            ).limit(10)
        )
        top_nodes = [
            {"name": n.canonical_name, "type": n.entity_type, "mentions": n.mention_count}
            for n in top_nodes_result.scalars().all()
        ]

        # Strongest relationships
        strongest_rels_result = await self.db.execute(
            select(KnowledgeEdge, KnowledgeNode.column("canonical_name")).join(
                KnowledgeNode, KnowledgeEdge.subject_node_id == KnowledgeNode.id
            ).order_by(KnowledgeEdge.strength.desc()).limit(10)
        )

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "nodes_by_type": nodes_by_type,
            "top_mentioned": top_nodes,
            "timestamp": datetime.utcnow().isoformat()
        }

    # ========================================================================
    # ADVANCED FEATURE 1: CONFIDENCE DECAY OVER TIME
    # ========================================================================

    def calculate_decayed_strength(
        self,
        original_strength: float,
        last_seen: datetime,
        current_time: Optional[datetime] = None,
        half_life_days: Optional[float] = None
    ) -> float:
        """Calculate strength with temporal decay applied.

        Uses exponential decay based on half-life:
        strength_decayed = strength * (0.5 ^ (days_elapsed / half_life))

        Args:
            original_strength: Original relationship strength (0.0-1.0)
            last_seen: When relationship was last observed
            current_time: Current time (defaults to now)
            half_life_days: Half-life in days (defaults to config)

        Returns:
            Decayed strength (0.0-1.0)
        """
        if not config.DECAY_ENABLED:
            return original_strength

        if current_time is None:
            current_time = datetime.utcnow()

        if half_life_days is None:
            half_life_days = config.DECAY_HALF_LIFE_DAYS

        # Calculate days elapsed
        days_elapsed = (current_time - last_seen).total_seconds() / 86400.0

        if days_elapsed <= 0:
            return original_strength

        # Apply exponential decay
        decay_factor = math.pow(0.5, days_elapsed / half_life_days)
        decayed_strength = original_strength * decay_factor

        # Apply minimum threshold
        return max(decayed_strength, 0.0)

    async def apply_decay_to_edge(self, edge: KnowledgeEdge) -> Dict[str, float]:
        """Apply temporal decay to a single edge.

        Returns:
            Dict with original_strength, decayed_strength, decay_amount
        """
        original_strength = edge.strength
        decayed_strength = self.calculate_decayed_strength(
            original_strength,
            edge.last_seen
        )

        decay_amount = original_strength - decayed_strength

        # Update edge if significant decay occurred
        if decay_amount > 0.01:  # More than 1% decay
            edge.strength = decayed_strength
            await self.db.flush()

        return {
            "edge_id": edge.id,
            "original_strength": original_strength,
            "decayed_strength": decayed_strength,
            "decay_amount": decay_amount,
            "days_since_seen": (datetime.utcnow() - edge.last_seen).days
        }

    async def apply_decay_to_all_edges(self) -> Dict[str, Any]:
        """Apply temporal decay to all edges in the knowledge graph.

        This should be run periodically (e.g., daily) to keep strength scores current.

        Returns:
            Statistics about decay operation
        """
        # Get all edges
        result = await self.db.execute(select(KnowledgeEdge))
        edges = result.scalars().all()

        stats = {
            "total_edges": len(edges),
            "edges_decayed": 0,
            "edges_below_threshold": 0,
            "total_decay_amount": 0.0,
            "avg_decay_per_edge": 0.0,
            "timestamp": datetime.utcnow().isoformat()
        }

        decay_results = []

        for edge in edges:
            decay_info = await self.apply_decay_to_edge(edge)
            decay_results.append(decay_info)

            if decay_info["decay_amount"] > 0.01:
                stats["edges_decayed"] += 1
                stats["total_decay_amount"] += decay_info["decay_amount"]

            if decay_info["decayed_strength"] < config.DECAY_MIN_STRENGTH:
                stats["edges_below_threshold"] += 1

        if stats["edges_decayed"] > 0:
            stats["avg_decay_per_edge"] = stats["total_decay_amount"] / stats["edges_decayed"]

        await self.db.commit()

        stats["decay_results"] = decay_results[:10]  # Return first 10 for inspection

        return stats

    async def get_stale_relationships(
        self,
        threshold: Optional[float] = None,
        days_inactive: Optional[int] = None
    ) -> List[Dict]:
        """Get relationships that have decayed below threshold or are inactive.

        Args:
            threshold: Strength threshold (defaults to config)
            days_inactive: Days since last seen (defaults to 2x half-life)

        Returns:
            List of stale relationships with details
        """
        if threshold is None:
            threshold = config.DECAY_MIN_STRENGTH

        if days_inactive is None:
            days_inactive = int(config.DECAY_HALF_LIFE_DAYS * 2)

        cutoff_date = datetime.utcnow() - timedelta(days=days_inactive)

        # Query edges below threshold or inactive
        result = await self.db.execute(
            select(KnowledgeEdge, KnowledgeNode.canonical_name.label("subject_name"))
            .join(KnowledgeNode, KnowledgeEdge.subject_node_id == KnowledgeNode.id)
            .where(
                or_(
                    KnowledgeEdge.strength < threshold,
                    KnowledgeEdge.last_seen < cutoff_date
                )
            )
            .order_by(KnowledgeEdge.strength.asc())
        )

        stale_rels = []
        for edge, subject_name in result.all():
            # Get object name
            obj_result = await self.db.execute(
                select(KnowledgeNode.canonical_name)
                .where(KnowledgeNode.id == edge.object_node_id)
            )
            object_name = obj_result.scalar_one()

            # Calculate decayed strength
            decayed_strength = self.calculate_decayed_strength(
                edge.strength,
                edge.last_seen
            )

            stale_rels.append({
                "subject": subject_name,
                "predicate": edge.predicate,
                "object": object_name,
                "original_strength": edge.strength,
                "decayed_strength": decayed_strength,
                "last_seen": edge.last_seen.isoformat(),
                "days_inactive": (datetime.utcnow() - edge.last_seen).days,
                "is_stale": decayed_strength < threshold
            })

        return stale_rels

    async def prune_stale_relationships(
        self,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """Remove relationships that have decayed below threshold.

        Args:
            threshold: Strength threshold for removal (defaults to config)

        Returns:
            Statistics about pruning operation
        """
        if threshold is None:
            threshold = config.DECAY_MIN_STRENGTH

        # First apply decay to all edges
        await self.apply_decay_to_all_edges()

        # Count edges to be removed
        count_result = await self.db.execute(
            select(func.count(KnowledgeEdge.id))
            .where(KnowledgeEdge.strength < threshold)
        )
        edges_to_remove = count_result.scalar()

        # Delete edges below threshold
        await self.db.execute(
            update(KnowledgeEdge)
            .where(KnowledgeEdge.strength < threshold)
            .values(strength=0.0)  # Mark as pruned rather than deleting
        )

        await self.db.commit()

        return {
            "edges_pruned": edges_to_remove,
            "threshold": threshold,
            "timestamp": datetime.utcnow().isoformat()
        }

    # ========================================================================
    # ADVANCED FEATURE 2: SEMANTIC SIMILARITY WITH EMBEDDINGS
    # ========================================================================

    async def _find_candidates_with_embeddings(
        self,
        entity: Entity,
        same_type_nodes: List[KnowledgeNode]
    ) -> List[Tuple[KnowledgeNode, float]]:
        """Find candidate nodes using semantic similarity.

        Args:
            entity: The entity to match
            same_type_nodes: List of nodes of the same type

        Returns:
            List of (node, similarity_score) tuples
        """
        if not embedding_service.is_available():
            return []

        candidates = []

        # Generate embedding for entity name
        entity_emb = embedding_service.generate_embedding(entity.name)
        if entity_emb is None:
            return candidates

        # Calculate similarity with each candidate
        for node in same_type_nodes:
            node_emb = embedding_service.generate_embedding(node.canonical_name)
            if node_emb is None:
                continue

            similarity = embedding_service.calculate_similarity(entity_emb, node_emb)

            if similarity >= config.SEMANTIC_SIMILARITY_THRESHOLD:
                candidates.append((node, similarity))

        # Sort by similarity descending
        candidates.sort(key=lambda x: x[1], reverse=True)

        return candidates

    def _calculate_combined_similarity(
        self,
        entity: Entity,
        node: KnowledgeNode,
        string_similarity: float,
        semantic_similarity: Optional[float] = None
    ) -> float:
        """Combine string and semantic similarity scores.

        Uses weighted average:
        - If semantic similarity available: 60% string, 40% semantic
        - Otherwise: 100% string

        Args:
            entity: Entity to match
            node: Candidate node
            string_similarity: String-based similarity score
            semantic_similarity: Optional semantic similarity score

        Returns:
            Combined similarity score
        """
        if semantic_similarity is None:
            return string_similarity

        # Weighted average: prioritize string similarity but boost with semantic
        combined = (0.6 * string_similarity) + (0.4 * semantic_similarity)

        return min(combined, 1.0)
