"""
Knowledge Graph Models V2 - Phase 6 Cognitive Nexus Enhancements

This module extends the Phase 1 knowledge graph with new node types and relationships
to support intelligent task synthesis, contextual understanding, and outcome-based learning.

New Phase 6 Additions:
1. ConceptNode: Domain-specific concepts extracted from context (not generic terms)
2. ConversationThreadNode: Grouped messages with key decisions and unresolved questions
3. TaskOutcomeNode: Task completion outcomes with lessons learned
4. Enhanced relationships: SIMILAR_TO, PREREQUISITE_OF, DISCUSSED_IN, OUTCOME_INFORMED_BY

These extensions transform the KG from simple entity tracking to a rich contextual
memory system that learns from outcomes and builds strategic understanding.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Boolean, JSON, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from db.models import Base


# ============================================================================
# PHASE 6: CONCEPT TRACKING
# ============================================================================

class ConceptNode(Base):
    """Tracks domain-specific concepts mentioned in context.

    Concepts are 2-4 word noun phrases that represent domain-specific ideas,
    NOT generic terms like "email", "meeting", "task".

    Examples of valid concepts:
    - "pharmacy pinning effectiveness"
    - "Spain market launch"
    - "position 3 visibility"
    - "Netherlands rollout"

    Examples of INVALID concepts (too generic):
    - "email"
    - "meeting"
    - "analysis"
    - "report"

    Concepts are tracked with:
    - Importance score (0-1): Based on mention frequency, urgency, calendar meetings
    - Confidence tier: ESTABLISHED (10+ mentions), EMERGING (3-9), TENTATIVE (1-2)
    - Temporal tracking: When first/last mentioned
    - Definition: AI-generated explanation of what this concept means

    Lifecycle:
    - Concepts mentioned <3 times historically are NOT tracked (noise filtering)
    - Concepts not mentioned in 6 months are archived
    - Similar concepts (similarity >0.9) are merged

    Relationships:
    - No explicit relationships (uses JSON fields for flexibility)
    """
    __tablename__ = "concept_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Core identity
    name = Column(String(255), nullable=False, unique=True, index=True)
    definition = Column(Text, nullable=True)  # AI-generated explanation

    # Importance scoring
    importance_score = Column(Float, default=0.0, nullable=False, index=True)  # 0.0-1.0
    # Importance factors:
    # - Mention frequency (30 day window)
    # - Urgency indicators (email subject lines, calendar events)
    # - Strategic context (user projects/markets)

    # Confidence tier
    confidence_tier = Column(String(50), default="TENTATIVE", nullable=False)  # ESTABLISHED, EMERGING, TENTATIVE

    # Temporal tracking
    first_mentioned = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_mentioned = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    mention_count_30d = Column(Integer, default=1, nullable=False)  # Rolling 30-day count
    mention_count_total = Column(Integer, default=1, nullable=False)  # All-time count

    # Context linkages
    related_projects = Column(JSON, default=list)  # ["CRESCO", "RF16"]
    related_markets = Column(JSON, default=list)  # ["Spain", "Netherlands"]
    related_people = Column(JSON, default=list)  # ["Alberto", "Andy"]

    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    archived_at = Column(DateTime, nullable=True)  # Set when archived (6 months inactive)

    # Indexes for fast lookup
    __table_args__ = (
        Index('idx_concept_importance', 'importance_score'),
        Index('idx_concept_tier', 'confidence_tier'),
        Index('idx_concept_last_mentioned', 'last_mentioned'),
    )


# ============================================================================
# PHASE 6: CONVERSATION TRACKING
# ============================================================================

class ConversationThreadNode(Base):
    """Tracks conversation threads with key decisions and unresolved questions.

    A conversation thread is a group of related messages (emails, chats, meetings)
    on a specific topic. This enables Lotus to:
    - Remember what was discussed
    - Track decisions made
    - Surface unresolved questions
    - Link conversations to tasks

    Example:
    Topic: "Spain pharmacy pinning analysis"
    Participants: ["Alberto Moraleda", "Jef Adriaenssens", "Andy Maclean"]
    Key Decisions: ["Analysis due Dec 5", "Include position 3 visibility metrics"]
    Unresolved Questions: ["Should we include UK data for comparison?"]

    Lifecycle:
    - Threads inactive for 60 days are marked as closed
    - Threads older than 6 months are archived

    Relationships:
    - No explicit relationships (uses JSON for flexibility)
    """
    __tablename__ = "conversation_threads"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Core identity
    topic = Column(String(500), nullable=False, index=True)
    participants = Column(JSON, default=list, nullable=False)  # ["Alberto Moraleda", "Jef Adriaenssens"]

    # Temporal tracking
    start_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    message_count = Column(Integer, default=1, nullable=False)

    # Context extraction
    key_decisions = Column(JSON, default=list, nullable=False)
    # Example: ["Analysis due Dec 5", "Include satisfaction scores", "Compare to Netherlands rollout"]

    unresolved_questions = Column(JSON, default=list, nullable=False)
    # Example: ["Should we include UK pharmacy data?", "Who will review final dashboard?"]

    # Strategic context
    related_projects = Column(JSON, default=list)  # ["RF16", "CRESCO"]
    related_tasks = Column(JSON, default=list)  # Task IDs linked to this conversation
    importance_score = Column(Float, default=0.5, nullable=False)  # 0.0-1.0

    # Status
    is_active = Column(Boolean, default=True, nullable=False)  # False if inactive >60 days
    is_archived = Column(Boolean, default=False, nullable=False)  # True if >6 months old

    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    archived_at = Column(DateTime, nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_conversation_last_updated', 'last_updated'),
        Index('idx_conversation_active', 'is_active'),
    )


# ============================================================================
# PHASE 6: TASK OUTCOME TRACKING
# ============================================================================

class TaskOutcomeNode(Base):
    """Records task completion outcomes with lessons learned.

    This is the HIGHEST QUALITY signal for learning. When a task completes
    (or is cancelled/ignored), we record:
    - Outcome type (COMPLETED, CANCELLED, IGNORED)
    - Actual effort vs estimated
    - Completion quality (5.0 = perfect, lower if issues)
    - Blockers encountered
    - Lessons learned

    These outcomes are used to:
    - Improve future task estimates
    - Learn what works (reinforce successful patterns)
    - Adjust confidence scoring
    - Provide context for similar tasks

    Outcome Types:
    - COMPLETED: Task finished successfully
    - COMPLETED_WITH_ISSUES: Finished but had blockers/quality issues
    - CANCELLED: User explicitly cancelled
    - IGNORED: Created but never acted on (>7 days in todo)
    - MERGED: Merged into another task (duplicate)

    Quality Score (0.0-5.0):
    - 5.0: Perfect completion, no edits, no blockers
    - 4.0: Completed with minor edits
    - 3.0: Completed with significant edits or blockers
    - 2.0: Completed but quality issues
    - 1.0: Barely completed, major issues

    Relationships:
    - task_id: Foreign key to tasks.id (which task this outcome is for)
    """
    __tablename__ = "task_outcomes"

    # Primary key is task_id (one outcome per task)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)

    # Outcome classification
    outcome = Column(String(50), nullable=False, index=True)  # COMPLETED, CANCELLED, IGNORED, MERGED
    completion_quality = Column(Float, nullable=True)  # 0.0-5.0 (only for COMPLETED)

    # Effort tracking
    estimated_effort_hours = Column(Float, nullable=True)  # Original AI estimate
    actual_effort_hours = Column(Float, nullable=True)  # Time from created to completed
    effort_variance = Column(Float, nullable=True)  # actual / estimated (1.0 = perfect, >1.0 = took longer)

    # Blockers and issues
    blockers = Column(JSON, default=list, nullable=False)
    # Example: ["Waiting on data from Andy", "API documentation incomplete", "Spain market access delayed"]

    # Lessons learned (AI-generated summary)
    lessons_learned = Column(Text, nullable=True)
    # Example: "Position 3 analysis took 6 hours (estimated 4) due to data access delays.
    #           Similar tasks should include 2-hour buffer for data retrieval."

    # Context for pattern learning
    task_title = Column(String(500), nullable=True)  # Denormalized for fast querying
    task_project = Column(String(255), nullable=True)  # Which project
    task_market = Column(String(255), nullable=True)  # Which market
    task_assignee = Column(String(255), nullable=True)  # Who completed it

    # Follow-up tasks created
    follow_up_task_count = Column(Integer, default=0, nullable=False)  # Did this spawn more work?

    # User feedback (optional)
    user_satisfaction = Column(Integer, nullable=True)  # 1-5 star rating (if provided)
    user_notes = Column(Text, nullable=True)

    # Temporal
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)  # When task was actually completed

    # Indexes
    __table_args__ = (
        Index('idx_outcome_type', 'outcome'),
        Index('idx_outcome_quality', 'completion_quality'),
        Index('idx_outcome_project', 'task_project'),
    )


# ============================================================================
# PHASE 6: CONCEPT RELATIONSHIPS
# ============================================================================

class ConceptRelationship(Base):
    """Tracks relationships between concepts.

    Examples:
    - "pharmacy pinning" SIMILAR_TO "pharmacy visibility"
    - "Spain market launch" PREREQUISITE_OF "Spain pharmacy analysis"
    - "Netherlands rollout" SIMILAR_TO "Spain market launch"

    Relationship Types:
    - SIMILAR_TO: Concepts are semantically similar (similarity >0.7)
    - PREREQUISITE_OF: One concept must happen before another
    - PART_OF: Concept is a component of larger concept
    - RELATED_TO: General relationship

    Strength:
    - 0.0-1.0 score
    - Higher = stronger relationship
    - Weakens over time if not reinforced

    Lifecycle:
    - Relationships with strength <0.3 are pruned monthly
    - Similar concepts (>0.9 similarity) are merged
    """
    __tablename__ = "concept_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Relationship structure
    concept_id = Column(Integer, ForeignKey("concept_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    related_to_id = Column(Integer, ForeignKey("concept_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String(100), nullable=False, index=True)  # SIMILAR_TO, PREREQUISITE_OF, etc.

    # Strength
    strength = Column(Float, default=1.0, nullable=False, index=True)  # 0.0-1.0
    confidence = Column(Float, default=1.0, nullable=False)  # Confidence in this relationship

    # Reasoning
    reason = Column(Text, nullable=True)  # Why this relationship exists

    # Temporal
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_reinforced = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_concept_relationship', 'concept_id', 'related_to_id'),
        Index('idx_relationship_type', 'relationship_type'),
        Index('idx_relationship_strength', 'strength'),
    )


# ============================================================================
# PHASE 6: TASK SIMILARITY INDEX (for fast lookups)
# ============================================================================

class TaskSimilarityIndex(Base):
    """Pre-computed task similarity index for fast "find similar tasks" queries.

    Computing semantic similarity on-the-fly is expensive (500ms+ per query).
    This index pre-computes similarity scores for all task pairs nightly,
    enabling <50ms lookups.

    Structure:
    - task_id: The task we're finding similar tasks for
    - similar_task_ids: Top 10 most similar task IDs (JSON array)
    - similarity_scores: Corresponding similarity scores (JSON array)
    - computed_at: When this index was computed

    The index is rebuilt nightly by a background job that:
    1. Gets all tasks
    2. Computes pairwise semantic similarity
    3. Stores top 10 matches per task
    4. Prunes outdated entries

    This trades storage (modest) for speed (10x+ faster).
    """
    __tablename__ = "task_similarity_index"

    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)

    # Pre-computed similar tasks
    similar_task_ids = Column(JSON, default=list, nullable=False)
    # Example: ["task-123", "task-456", "task-789", ...]

    similar_task_titles = Column(JSON, default=list, nullable=False)
    # Denormalized for display without JOIN

    similarity_scores = Column(JSON, default=list, nullable=False)
    # Example: [0.92, 0.87, 0.81, ...] (same order as similar_task_ids)

    similarity_explanations = Column(JSON, default=list, nullable=False)
    # Example: ["Both analyze pharmacy metrics", "Same market (Spain)", ...]

    # Metadata
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_stale = Column(Boolean, default=False, nullable=False)  # True if task updated since computation

    # Lifecycle
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Index for fast lookup
    __table_args__ = (
        Index('idx_similarity_computed', 'computed_at'),
        Index('idx_similarity_stale', 'is_stale'),
    )


# ============================================================================
# PHASE 6: CONCEPT-TASK LINKAGE
# ============================================================================

class ConceptTaskLink(Base):
    """Links concepts to tasks they're mentioned in.

    This enables queries like:
    - "Find all tasks related to 'pharmacy pinning'"
    - "What concepts are associated with high-quality completed tasks?"
    - "Which concepts predict task success?"

    Strength:
    - How strongly is this concept related to this task?
    - 1.0 = mentioned in title
    - 0.7 = mentioned in description
    - 0.5 = mentioned in related context
    - 0.3 = weakly related

    This is similar to EntityKnowledgeLink but for concepts instead of entities.
    """
    __tablename__ = "concept_task_links"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Links
    concept_id = Column(Integer, ForeignKey("concept_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)

    # Strength
    strength = Column(Float, default=1.0, nullable=False)  # How strongly related (0.0-1.0)

    # Context
    mention_location = Column(String(50), nullable=True)  # title, description, comment, related_context

    # Lifecycle
    linked_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_concept_task', 'concept_id', 'task_id'),
        Index('idx_task_concepts', 'task_id'),
    )
