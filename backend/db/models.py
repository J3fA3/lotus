"""
Database models for task management
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Task(Base):
    """Task model matching frontend Task interface"""
    __tablename__ = "tasks"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False)  # todo, doing, done
    assignee = Column(String, nullable=False)
    start_date = Column(String, nullable=True)
    due_date = Column(String, nullable=True)
    value_stream = Column(String, nullable=True)
    description = Column(Text, nullable=True)
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
