"""
Knowledge Graph GraphQL Schema

Provides a GraphQL API for complex knowledge graph queries.
Supports nested queries, filtering, sorting, and aggregations.
"""

from typing import List, Optional
import strawberry
from strawberry.fastapi import GraphQLRouter
from datetime import datetime

from db.database import AsyncSessionLocal
from services.knowledge_graph_service import KnowledgeGraphService
from services.knowledge_graph_config import config


# ============================================================================
# GRAPHQL TYPES
# ============================================================================

@strawberry.type
class TeamMetadata:
    """Team hierarchy metadata"""
    pillars: Optional[List[str]] = None
    team_names: Optional[List[str]] = None
    roles: Optional[List[str]] = None


@strawberry.type
class KnowledgeNodeType:
    """Represents a canonical entity in the knowledge graph"""
    id: int
    canonical_name: str
    entity_type: str
    first_seen: str
    last_seen: str
    mention_count: int
    average_confidence: float
    aliases: List[str]

    @strawberry.field
    def metadata(self) -> Optional[TeamMetadata]:
        """Get team metadata if available"""
        # This will be populated by resolver
        return None


@strawberry.type
class RelationshipType:
    """Represents a relationship between entities"""
    type: str
    target: str
    target_type: str
    strength: float
    mentioned_in: int
    contexts: int


@strawberry.type
class EntityKnowledge:
    """Complete knowledge about an entity"""
    entity: str
    type: str
    aliases: List[str]
    mentioned_in: int
    first_seen: str
    last_seen: str
    average_confidence: float
    outgoing_relationships: List[RelationshipType]
    incoming_relationships: List[RelationshipType]


@strawberry.type
class TeamRole:
    """A role within a team"""
    name: str
    mentioned: int
    contexts: int


@strawberry.type
class Team:
    """A team within the organization"""
    name: str
    type: str
    mentioned: int
    contexts: int
    roles: List[TeamRole]


@strawberry.type
class TeamStructure:
    """Organizational team structure"""
    name: str
    type: str
    mentioned: int
    contexts: int
    first_seen: str
    teams: List[Team]


@strawberry.type
class GraphStats:
    """Knowledge graph statistics"""
    total_nodes: int
    total_edges: int
    nodes_by_type: strawberry.scalars.JSON
    timestamp: str


@strawberry.type
class DecayStats:
    """Confidence decay statistics"""
    total_edges: int
    edges_decayed: int
    edges_below_threshold: int
    avg_decay_per_edge: float
    timestamp: str


@strawberry.type
class StaleRelationship:
    """A relationship that has decayed"""
    subject: str
    predicate: str
    object: str
    original_strength: float
    decayed_strength: float
    last_seen: str
    days_inactive: int
    is_stale: bool


# ============================================================================
# INPUT TYPES
# ============================================================================

@strawberry.input
class EntitySearchInput:
    """Input for searching entities"""
    query: str
    entity_type: Optional[str] = None
    limit: int = 10


@strawberry.input
class RelationshipFilter:
    """Filter for relationships"""
    predicate: Optional[str] = None
    min_strength: Optional[float] = None
    max_strength: Optional[float] = None


# ============================================================================
# QUERIES
# ============================================================================

@strawberry.type
class Query:
    """Root GraphQL query type"""

    @strawberry.field
    async def entity_knowledge(
        self,
        name: str,
        entity_type: Optional[str] = None
    ) -> Optional[EntityKnowledge]:
        """Get complete knowledge about an entity

        Example:
        ```graphql
        query {
          entityKnowledge(name: "Jef Adriaenssens") {
            entity
            type
            aliases
            mentionedIn
            outgoingRelationships {
              type
              target
              strength
            }
          }
        }
        ```
        """
        async with AsyncSessionLocal() as db:
            kg_service = KnowledgeGraphService(db)
            result = await kg_service.get_entity_knowledge(name, entity_type)

            if not result:
                return None

            return EntityKnowledge(
                entity=result["entity"],
                type=result["type"],
                aliases=result["aliases"],
                mentioned_in=result["mentioned_in"],
                first_seen=result["first_seen"],
                last_seen=result["last_seen"],
                average_confidence=result["average_confidence"],
                outgoing_relationships=[
                    RelationshipType(**rel)
                    for rel in result["relationships"]["outgoing"]
                ],
                incoming_relationships=[
                    RelationshipType(**rel)
                    for rel in result["relationships"]["incoming"]
                ]
            )

    @strawberry.field
    async def search_entities(
        self,
        search_input: EntitySearchInput
    ) -> List[KnowledgeNodeType]:
        """Search for entities by name

        Example:
        ```graphql
        query {
          searchEntities(searchInput: {query: "jef", limit: 5}) {
            id
            canonicalName
            entityType
            aliases
            mentionCount
          }
        }
        ```
        """
        from db.knowledge_graph_models import KnowledgeNode
        from sqlalchemy import select, or_, func

        async with AsyncSessionLocal() as db:
            # Build query
            query = select(KnowledgeNode).where(
                or_(
                    func.lower(KnowledgeNode.canonical_name).contains(search_input.query.lower()),
                    KnowledgeNode.aliases.contains(search_input.query.lower())
                )
            )

            if search_input.entity_type:
                query = query.where(KnowledgeNode.entity_type == search_input.entity_type)

            query = query.order_by(
                KnowledgeNode.mention_count.desc(),
                KnowledgeNode.last_seen.desc()
            ).limit(search_input.limit)

            result = await db.execute(query)
            nodes = result.scalars().all()

            return [
                KnowledgeNodeType(
                    id=node.id,
                    canonical_name=node.canonical_name,
                    entity_type=node.entity_type,
                    first_seen=node.first_seen.isoformat(),
                    last_seen=node.last_seen.isoformat(),
                    mention_count=node.mention_count,
                    average_confidence=node.average_confidence,
                    aliases=node.aliases or []
                )
                for node in nodes
            ]

    @strawberry.field
    async def team_structures(self) -> List[TeamStructure]:
        """Get discovered team structures

        Example:
        ```graphql
        query {
          teamStructures {
            name
            type
            mentioned
            teams {
              name
              roles {
                name
                mentioned
              }
            }
          }
        }
        ```
        """
        async with AsyncSessionLocal() as db:
            kg_service = KnowledgeGraphService(db)
            result = await kg_service.get_discovered_team_structures()

            structures = []
            for structure in result["structures"]:
                teams = []
                if "teams" in structure:
                    for team in structure["teams"]:
                        roles = [
                            TeamRole(
                                name=role["name"],
                                mentioned=role["mentioned"],
                                contexts=role["contexts"]
                            )
                            for role in team.get("roles", [])
                        ]
                        teams.append(Team(
                            name=team["name"],
                            type=team["type"],
                            mentioned=team["mentioned"],
                            contexts=team["contexts"],
                            roles=roles
                        ))

                structures.append(TeamStructure(
                    name=structure["name"],
                    type=structure["type"],
                    mentioned=structure["mentioned"],
                    contexts=structure["contexts"],
                    first_seen=structure["first_seen"],
                    teams=teams
                ))

            return structures

    @strawberry.field
    async def graph_stats(self) -> GraphStats:
        """Get knowledge graph statistics

        Example:
        ```graphql
        query {
          graphStats {
            totalNodes
            totalEdges
            nodesByType
          }
        }
        ```
        """
        async with AsyncSessionLocal() as db:
            kg_service = KnowledgeGraphService(db)
            stats = await kg_service.compute_graph_stats()

            return GraphStats(
                total_nodes=stats["total_nodes"],
                total_edges=stats["total_edges"],
                nodes_by_type=stats["nodes_by_type"],
                timestamp=stats["timestamp"]
            )

    @strawberry.field
    async def stale_relationships(
        self,
        threshold: Optional[float] = None,
        days_inactive: Optional[int] = None
    ) -> List[StaleRelationship]:
        """Get relationships that have decayed below threshold

        Example:
        ```graphql
        query {
          staleRelationships(threshold: 0.1, daysInactive: 180) {
            subject
            predicate
            object
            originalStrength
            decayedStrength
            daysInactive
            isStale
          }
        }
        ```
        """
        async with AsyncSessionLocal() as db:
            kg_service = KnowledgeGraphService(db)
            results = await kg_service.get_stale_relationships(threshold, days_inactive)

            return [
                StaleRelationship(
                    subject=rel["subject"],
                    predicate=rel["predicate"],
                    object=rel["object"],
                    original_strength=rel["original_strength"],
                    decayed_strength=rel["decayed_strength"],
                    last_seen=rel["last_seen"],
                    days_inactive=rel["days_inactive"],
                    is_stale=rel["is_stale"]
                )
                for rel in results
            ]

    @strawberry.field
    async def relationship_path(
        self,
        from_entity: str,
        to_entity: str,
        max_hops: int = 3
    ) -> List[List[str]]:
        """Find relationship paths between two entities

        Example:
        ```graphql
        query {
          relationshipPath(
            fromEntity: "Jef Adriaenssens",
            toEntity: "CRESCO",
            maxHops: 3
          )
        }
        ```

        Returns list of paths, where each path is a list of entity names.
        """
        # This would require implementing BFS/DFS graph traversal
        # For now, return empty list (to be implemented)
        return []


# ============================================================================
# MUTATIONS
# ============================================================================

@strawberry.type
class Mutation:
    """Root GraphQL mutation type"""

    @strawberry.mutation
    async def apply_decay(self) -> DecayStats:
        """Apply confidence decay to all relationships

        Example:
        ```graphql
        mutation {
          applyDecay {
            totalEdges
            edgesDecayed
            edgesBelowThreshold
            avgDecayPerEdge
          }
        }
        ```
        """
        async with AsyncSessionLocal() as db:
            kg_service = KnowledgeGraphService(db)
            stats = await kg_service.apply_decay_to_all_edges()

            return DecayStats(
                total_edges=stats["total_edges"],
                edges_decayed=stats["edges_decayed"],
                edges_below_threshold=stats["edges_below_threshold"],
                avg_decay_per_edge=stats["avg_decay_per_edge"],
                timestamp=stats["timestamp"]
            )

    @strawberry.mutation
    async def prune_stale_relationships(
        self,
        threshold: Optional[float] = None
    ) -> strawberry.scalars.JSON:
        """Remove relationships below strength threshold

        Example:
        ```graphql
        mutation {
          pruneStaleRelationships(threshold: 0.1)
        }
        ```
        """
        async with AsyncSessionLocal() as db:
            kg_service = KnowledgeGraphService(db)
            stats = await kg_service.prune_stale_relationships(threshold)
            return stats


# ============================================================================
# SCHEMA
# ============================================================================

schema = strawberry.Schema(query=Query, mutation=Mutation)


# ============================================================================
# GRAPHQL ROUTER
# ============================================================================

def create_graphql_router() -> GraphQLRouter:
    """Create and configure GraphQL router"""
    if not config.GRAPHQL_ENABLED:
        return None

    router = GraphQLRouter(
        schema,
        path=config.GRAPHQL_PATH,
        graphiql=config.GRAPHQL_PLAYGROUND_ENABLED
    )

    return router
