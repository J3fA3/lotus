"""
Database Models for Task Management and Cognitive Nexus

SQLAlchemy ORM models with relationships and cascade deletes.
All models use async-compatible patterns for use with aiosqlite.

Important: When querying tasks, use selectinload() to eager-load
relationships (comments, attachments) to avoid greenlet errors.

New in Cognitive Nexus Phase 1:
- ContextItem: Stores context ingestion and agent metrics
- Entity: Stores extracted entities from context
- Relationship: Stores inferred relationships between entities
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Boolean, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Task(Base):
    """Main task entity with support for comments, attachments, and notes.
    
    Relationships:
    - comments: One-to-many with Comment (cascade delete)
    - attachments: One-to-many with Attachment (cascade delete)
    """
    __tablename__ = "tasks"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False)  # todo, doing, done
    assignee = Column(String, nullable=False)
    start_date = Column(String, nullable=True)
    due_date = Column(String, nullable=True)
    value_stream = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="task", cascade="all, delete-orphan")


class Comment(Base):
    """Comment model"""
    __tablename__ = "comments"

    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"))
    text = Column(Text, nullable=False)
    author = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="comments")


class Attachment(Base):
    """Attachment model"""
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"))
    url = Column(String, nullable=False)

    task = relationship("Task", back_populates="attachments")


class InferenceHistory(Base):
    """Track AI inference operations for analytics"""
    __tablename__ = "inference_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    input_text = Column(Text, nullable=False)
    input_type = Column(String, nullable=False)  # text, pdf
    tasks_inferred = Column(Integer, default=0)
    model_used = Column(String, nullable=False)
    inference_time = Column(Integer, nullable=True)  # milliseconds
    created_at = Column(DateTime, default=datetime.utcnow)


class ShortcutConfig(Base):
    """Keyboard shortcut configuration with remote sync support"""
    __tablename__ = "shortcut_configs"

    id = Column(String, primary_key=True)  # unique identifier for the shortcut action
    category = Column(String, nullable=False)  # global, board, task, dialog, message
    action = Column(String, nullable=False)  # new_task, delete_task, etc.
    key = Column(String, nullable=False)  # n, d, Enter, etc.
    modifiers = Column(JSON, default=list)  # ["ctrl", "shift", "alt", "meta"]
    enabled = Column(Boolean, default=True)
    description = Column(Text, nullable=False)
    user_id = Column(Integer, nullable=True)  # NULL = global default, specific user ID for overrides
    is_default = Column(Boolean, default=True)  # True if this is a default config
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# COGNITIVE NEXUS MODELS
# ============================================================================

class ContextItem(Base):
    """Stores context ingestion and LangGraph agent processing results.

    This model tracks each context item processed through the Cognitive Nexus
    agent system, including quality metrics, reasoning traces, and relationships
    to extracted entities.

    Relationships:
    - entities: One-to-many with Entity (cascade delete)
    - relationships: One-to-many with Relationship (cascade delete)
    """
    __tablename__ = "context_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    source_type = Column(String(50), nullable=False)  # slack, transcript, manual
    source_identifier = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # LangGraph agent state and metrics
    extraction_strategy = Column(String(50), nullable=True)  # fast, detailed
    context_complexity = Column(Float, nullable=True)
    entity_quality = Column(Float, nullable=True)
    relationship_quality = Column(Float, nullable=True)
    task_quality = Column(Float, nullable=True)
    reasoning_trace = Column(Text, nullable=True)  # JSON array of reasoning steps

    # Relationships
    entities = relationship("Entity", back_populates="context_item", cascade="all, delete-orphan")
    relationships_from_context = relationship("Relationship", back_populates="context_item", cascade="all, delete-orphan")


class Entity(Base):
    """Stores entities extracted by the Entity Extraction Agent.

    Entities are named entities like people, projects, companies, or dates
    that are extracted from context using the LangGraph agent system.

    Relationships:
    - context_item: Many-to-one with ContextItem
    - subject_relationships: One-to-many with Relationship (as subject)
    - object_relationships: One-to-many with Relationship (as object)
    """
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)  # PERSON, PROJECT, COMPANY, DATE
    confidence = Column(Float, nullable=True, default=1.0)
    context_item_id = Column(Integer, ForeignKey("context_items.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    context_item = relationship("ContextItem", back_populates="entities")
    subject_relationships = relationship("Relationship", foreign_keys="[Relationship.subject_entity_id]", back_populates="subject_entity")
    object_relationships = relationship("Relationship", foreign_keys="[Relationship.object_entity_id]", back_populates="object_entity")


class Relationship(Base):
    """Stores relationships between entities inferred by the Relationship Synthesis Agent.

    Relationships represent connections between entities such as:
    - WORKS_ON: person works on project
    - COMMUNICATES_WITH: person talks to person
    - HAS_DEADLINE: project has deadline
    - MENTIONED_WITH: entities co-occur

    Relationships:
    - subject_entity: Many-to-one with Entity (subject)
    - object_entity: Many-to-one with Entity (object)
    - context_item: Many-to-one with ContextItem
    """
    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_entity_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    predicate = Column(String(100), nullable=False, index=True)  # WORKS_ON, COMMUNICATES_WITH, etc.
    object_entity_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    confidence = Column(Float, nullable=True, default=1.0)
    context_item_id = Column(Integer, ForeignKey("context_items.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    subject_entity = relationship("Entity", foreign_keys=[subject_entity_id], back_populates="subject_relationships")
    object_entity = relationship("Entity", foreign_keys=[object_entity_id], back_populates="object_relationships")
    context_item = relationship("ContextItem", back_populates="relationships_from_context")
