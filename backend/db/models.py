"""
Database Models for Lotus v2 Task Management

SQLAlchemy ORM models with relationships and cascade deletes.
All models use async-compatible patterns for use with aiosqlite.

Important: When querying tasks, use selectinload() to eager-load
relationships (comments, attachments) to avoid greenlet errors.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Boolean, JSON
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

    # Case memory fields (Intelligence Flywheel)
    completed_at = Column(DateTime, nullable=True)
    case_study_slug = Column(String, nullable=True)

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


class ValueStream(Base):
    """Value stream categories for organizing tasks"""
    __tablename__ = "value_streams"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    color = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ShortcutConfig(Base):
    """Keyboard shortcut configuration with remote sync support"""
    __tablename__ = "shortcut_configs"

    id = Column(String, primary_key=True)
    category = Column(String, nullable=False)
    action = Column(String, nullable=False)
    key = Column(String, nullable=False)
    modifiers = Column(JSON, default=list)
    enabled = Column(Boolean, default=True)
    description = Column(Text, nullable=False)
    user_id = Column(Integer, nullable=True)
    is_default = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
