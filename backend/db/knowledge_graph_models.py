"""
Knowledge Graph Models - Cross-Context Entity & Relationship Persistence

This module implements a living, evolving knowledge graph that:
1. Deduplicates entities across contexts
2. Aggregates relationships with strength scores
3. Tracks entity evolution over time
4. Learns new team structures dynamically
5. Provides historical queries and insights

The knowledge graph is the "memory" of the Cognitive Nexus system.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Boolean, JSON, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from db.models import Base


class KnowledgeNode(Base):
    """Canonical representation of an entity across all contexts.

    A knowledge node represents the "true" entity that may be mentioned
    in multiple contexts. For example, "Jef", "Jef Adriaenssens", and
    "jef adriaenssens" all map to the same knowledge node.

    Knowledge nodes evolve over time:
    - mention_count increases as entity is seen more
    - metadata gets enriched from multiple contexts
    - first_seen/last_seen track temporal bounds
    - canonical_name may be refined as better names are seen
    """
    __tablename__ = "knowledge_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Core identity
    canonical_name = Column(String(255), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # PERSON, PROJECT, TEAM, DATE

    # Temporal tracking
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    mention_count = Column(Integer, default=1, nullable=False)

    # Aggregated metadata (evolves over time)
    # Renamed from 'metadata' to 'entity_metadata' to avoid SQLAlchemy reserved attribute name
    entity_metadata = Column(JSON, nullable=True)
    # For TEAM entities: {
    #   "pillars": ["Customer Pillar", "Partner Pillar"],  # All seen pillars
    #   "team_names": ["Menu Team", "Search Team"],       # All seen team names
    #   "roles": ["Engineering", "Product"],              # All seen roles
    #   "confidence_scores": {...}                        # Track confidence over time
    # }
    # For PERSON entities: {
    #   "aliases": ["Jef", "Jef A", "Jef Adriaenssens"], # All name variations
    #   "teams": ["Menu Team", "CRESCO Team"],           # Teams they're part of
    #   "roles": ["Engineering Lead"]                     # Inferred roles
    # }

    # Alternative names (for fuzzy matching)
    aliases = Column(JSON, default=list)  # List of alternative names seen

    # Quality tracking
    average_confidence = Column(Float, default=1.0)  # Average confidence across mentions

    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (edges in the knowledge graph)
    outgoing_edges = relationship(
        "KnowledgeEdge",
        foreign_keys="[KnowledgeEdge.subject_node_id]",
        back_populates="subject_node",
        cascade="all, delete-orphan"
    )
    incoming_edges = relationship(
        "KnowledgeEdge",
        foreign_keys="[KnowledgeEdge.object_node_id]",
        back_populates="object_node",
        cascade="all, delete-orphan"
    )

    # Entity linkages (which raw entities map to this node)
    entity_links = relationship("EntityKnowledgeLink", back_populates="knowledge_node")

    # Indexes for fast lookup
    __table_args__ = (
        Index('idx_canonical_name_type', 'canonical_name', 'entity_type'),
        Index('idx_last_seen', 'last_seen'),
        Index('idx_mention_count', 'mention_count'),
    )


class KnowledgeEdge(Base):
    """Represents an aggregated relationship between knowledge nodes.

    Edges are relationships that have been seen across multiple contexts.
    They track:
    - Strength (how often seen, how confident)
    - Temporal bounds (when first/last seen)
    - Context diversity (from how many different contexts)

    Example: "Jef WORKS_ON CRESCO" seen in 8 contexts → strength 0.95
    """
    __tablename__ = "knowledge_edges"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Relationship structure
    subject_node_id = Column(Integer, ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    predicate = Column(String(100), nullable=False, index=True)  # WORKS_ON, COMMUNICATES_WITH, etc.
    object_node_id = Column(Integer, ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False, index=True)

    # Strength calculation
    # strength = (mention_count * average_confidence * context_diversity) / normalizing_factor
    strength = Column(Float, default=1.0, nullable=False, index=True)
    mention_count = Column(Integer, default=1, nullable=False)
    context_count = Column(Integer, default=1, nullable=False)  # Number of unique contexts
    average_confidence = Column(Float, default=1.0)

    # Temporal tracking
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Metadata
    # Renamed from 'metadata' to 'relationship_metadata' to avoid SQLAlchemy reserved attribute name
    relationship_metadata = Column(JSON, nullable=True)  # Additional relationship metadata

    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subject_node = relationship("KnowledgeNode", foreign_keys=[subject_node_id], back_populates="outgoing_edges")
    object_node = relationship("KnowledgeNode", foreign_keys=[object_node_id], back_populates="incoming_edges")

    # Indexes for fast lookup
    __table_args__ = (
        Index('idx_subject_predicate', 'subject_node_id', 'predicate'),
        Index('idx_object_predicate', 'object_node_id', 'predicate'),
        Index('idx_strength', 'strength'),
    )


class EntityKnowledgeLink(Base):
    """Links raw extracted entities to canonical knowledge nodes.

    This table maintains the mapping between:
    - Raw entities extracted from contexts (may have duplicates)
    - Canonical knowledge nodes (deduplicated)

    This allows us to:
    1. Trace back from knowledge node to source contexts
    2. Update linkages if deduplication improves
    3. Track which entities contributed to which knowledge
    """
    __tablename__ = "entity_knowledge_links"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Links
    entity_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    knowledge_node_id = Column(Integer, ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False, index=True)

    # Matching metadata
    similarity_score = Column(Float, nullable=True)  # How similar was the match (0.0-1.0)
    match_method = Column(String(50), nullable=True)  # exact, fuzzy, semantic, manual

    # Lifecycle
    linked_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    knowledge_node = relationship("KnowledgeNode", back_populates="entity_links")

    # Indexes
    __table_args__ = (
        Index('idx_entity_id', 'entity_id'),
        Index('idx_knowledge_node_id', 'knowledge_node_id'),
    )


class TeamStructureEvolution(Base):
    """Tracks the evolution of discovered team structures over time.

    This table enables the system to learn organizational structure dynamically.
    Instead of hardcoding "Customer Pillar" or "Menu Team", the system discovers
    these from context and tracks when they were first seen, how often, etc.

    This creates a living, breathing org chart that evolves with reality.
    """
    __tablename__ = "team_structure_evolution"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Structure element
    structure_type = Column(String(50), nullable=False, index=True)  # pillar, team, role, other
    structure_name = Column(String(255), nullable=False, index=True)

    # Hierarchy
    parent_structure_id = Column(Integer, ForeignKey("team_structure_evolution.id"), nullable=True)
    parent_structure = relationship("TeamStructureEvolution", remote_side=[id], backref="children")

    # Discovery tracking
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    mention_count = Column(Integer, default=1)
    context_count = Column(Integer, default=1)  # Number of contexts where seen

    # Metadata
    # Renamed from 'metadata' to 'structure_metadata' to avoid SQLAlchemy reserved attribute name
    structure_metadata = Column(JSON, nullable=True)  # Additional discovered metadata

    # Associated knowledge nodes
    # (people and projects associated with this team structure)
    associated_nodes = Column(JSON, default=list)  # List of knowledge_node_ids

    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_structure_type_name', 'structure_type', 'structure_name'),
        Index('idx_mention_count', 'mention_count'),
    )


class KnowledgeGraphStats(Base):
    """Stores aggregate statistics about the knowledge graph for analytics.

    This table provides insights into:
    - How the knowledge graph is growing
    - Which entities/relationships are most important
    - Knowledge quality metrics
    - Temporal patterns
    """
    __tablename__ = "knowledge_graph_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Timestamp
    snapshot_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Node stats
    total_nodes = Column(Integer, default=0)
    nodes_by_type = Column(JSON, default=dict)  # {"PERSON": 45, "PROJECT": 12, ...}
    top_mentioned_nodes = Column(JSON, default=list)  # Top 10 by mention_count

    # Edge stats
    total_edges = Column(Integer, default=0)
    edges_by_predicate = Column(JSON, default=dict)  # {"WORKS_ON": 67, ...}
    strongest_relationships = Column(JSON, default=list)  # Top 10 by strength

    # Team structure stats
    discovered_pillars = Column(JSON, default=list)
    discovered_teams = Column(JSON, default=list)
    discovered_roles = Column(JSON, default=list)

    # Quality metrics
    average_node_confidence = Column(Float, default=1.0)
    average_edge_strength = Column(Float, default=1.0)
    deduplication_savings = Column(Integer, default=0)  # How many entities merged

    # Growth metrics
    new_nodes_last_24h = Column(Integer, default=0)
    new_edges_last_24h = Column(Integer, default=0)

    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow)
