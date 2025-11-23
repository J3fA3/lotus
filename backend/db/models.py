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

    Phase 2 Additions:
    - confidence_score: AI confidence when task was created (0.0-1.0)
    - source_context_id: Links to ContextItem that generated this task
    - auto_created: Whether task was auto-created by AI (vs user approval)

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

    # Phase 2: AI Assistant fields
    confidence_score = Column(Float, nullable=True)  # 0.0-1.0 confidence when created
    source_context_id = Column(Integer, ForeignKey("context_items.id", ondelete="SET NULL"), nullable=True)
    auto_created = Column(Boolean, default=False)  # True if AI auto-created without user approval

    # Relationships
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="task", cascade="all, delete-orphan")
    source_context = relationship("ContextItem", backref="generated_tasks")
    versions = relationship("TaskVersion", back_populates="task", cascade="all, delete-orphan")


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


class ValueStream(Base):
    """Value stream categories for organizing tasks"""
    __tablename__ = "value_streams"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    color = Column(String, nullable=True)  # Optional color for UI display
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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


class Document(Base):
    """
    Document storage model

    Tracks uploaded documents with their metadata and relationships.
    Physical files are stored on disk using DocumentStorage.
    """
    __tablename__ = "documents"

    id = Column(String, primary_key=True)  # UUID
    file_id = Column(String, nullable=False, unique=True)  # Storage file ID
    original_filename = Column(String, nullable=False)
    file_extension = Column(String, nullable=False)  # .pdf, .docx, etc.
    mime_type = Column(String, nullable=True)
    file_hash = Column(String, nullable=False)  # SHA-256 hash
    size_bytes = Column(Integer, nullable=False)
    storage_path = Column(String, nullable=False)  # Relative path in storage
    category = Column(String, nullable=False)  # tasks, inference, knowledge

    # Extracted content for search and AI
    extracted_text = Column(Text, nullable=True)
    text_preview = Column(String, nullable=True)  # First 500 chars

    # Metadata
    page_count = Column(Integer, nullable=True)  # For PDFs
    document_metadata = Column(JSON, default=dict)  # Additional metadata

    # Relationships
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    inference_history_id = Column(Integer, ForeignKey("inference_history.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships - using selectinload for async compatibility
    task = relationship("Task", backref="documents")
    inference_history = relationship("InferenceHistory", backref="documents")


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

    Entities are named entities like people, projects, teams, or dates
    that are extracted from context using the LangGraph agent system.

    Entity Types:
    - PERSON: People (e.g., "Jef Adriaenssens", "Andy Maclean")
    - PROJECT: Projects (e.g., "CRESCO", "Just Deals")
    - TEAM: Organizational teams with hierarchical metadata
      * Pillar level: "Customer Pillar", "Partner Pillar", "Ventures Pillar"
      * Team level: "Menu Team", "Search Team", "Platform Team"
      * Role/Context: "Engineering", "Product", "Research", "Sales"
    - DATE: Deadlines and dates (e.g., "November 26th", "Friday")

    Team Metadata (JSON):
    {
        "pillar": "Customer Pillar",  # Optional
        "team_name": "Menu Team",     # Optional
        "role": "Engineering"          # Optional: engineering, product, research, sales, etc.
    }

    Relationships:
    - context_item: Many-to-one with ContextItem
    - subject_relationships: One-to-many with Relationship (as subject)
    - object_relationships: One-to-many with Relationship (as object)
    """
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)  # PERSON, PROJECT, TEAM, DATE
    confidence = Column(Float, nullable=True, default=1.0)
    entity_metadata = Column(JSON, nullable=True)  # Team metadata: pillar, team_name, role
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


# ============================================================================
# PHASE 2: AI ASSISTANT MODELS
# ============================================================================

class ChatMessage(Base):
    """Stores chat messages between user and AI Assistant.

    This model tracks the conversation history in the AI Assistant interface,
    including user messages and assistant responses with embedded task proposals.

    Metadata JSON Format:
    {
        "task_ids": ["task-123", "task-456"],  # Tasks mentioned/proposed in message
        "confidence_scores": [0.85, 0.92],     # Confidence for each proposed task
        "proposed_tasks": [                     # Full task proposals for assistant messages
            {
                "id": "temp_123",
                "title": "...",
                "confidence": 0.85,
                "auto_approved": true
            }
        ],
        "enriched_tasks": [                     # Tasks that were enriched (not created)
            {
                "task_id": "task-456",
                "task_title": "...",
                "added_note": "..."
            }
        ],
        "source_type": "slack",                 # For user messages
        "context_item_id": 123                  # Link to ContextItem if processed
    }

    Relationships:
    - No explicit relationships, uses session_id for grouping
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)  # UUID for chat session
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)  # Message text
    message_metadata = Column(JSON, nullable=True)  # Task IDs, confidence scores, proposals, etc.
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class FeedbackEvent(Base):
    """Tracks user feedback events for AI learning (Phase 3).

    This model captures how users interact with AI-proposed tasks:
    - Approved without changes
    - Edited before approval (what fields changed?)
    - Rejected (why?)
    - Deleted after creation (was AI wrong?)

    This data will be used in Phase 3 to improve confidence scoring
    and task generation quality.

    Event Types:
    - 'approved': User approved task without changes
    - 'edited': User edited task before/after approval
    - 'rejected': User rejected AI-proposed task
    - 'deleted': User deleted AI-created task

    original_data and modified_data are JSON objects containing:
    {
        "title": "...",
        "description": "...",
        "assignee": "...",
        "due_date": "...",
        "priority": "...",
        "tags": [...]
    }

    Relationships:
    - task: Many-to-one with Task (nullable for rejected tasks)
    - context_item: Many-to-one with ContextItem (which context led to this)
    """
    __tablename__ = "feedback_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)  # NULL for rejected tasks
    event_type = Column(String(50), nullable=False, index=True)  # approved, edited, rejected, deleted
    original_data = Column(JSON, nullable=True)  # Task data as proposed by AI
    modified_data = Column(JSON, nullable=True)  # Task data after user edits
    context_item_id = Column(Integer, ForeignKey("context_items.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    task = relationship("Task", backref="feedback_events")
    context_item = relationship("ContextItem", backref="feedback_events")


# ============================================================================
# PHASE 3: USER PROFILE & PERSONALIZATION
# ============================================================================

class UserProfile(Base):
    """Stores user profile information for personalized task management.

    This model enables context-aware AI by storing information about:
    - User's name and aliases (for name correction like "Jeff" → "Jef")
    - Role and company
    - Projects and markets they work on
    - Colleagues and their roles
    - Personal preferences

    Used by:
    - Relevance Filter: Only extract tasks relevant to this user
    - Task Enrichment: Auto-tag tasks with correct projects/markets
    - Comment Generator: Reference people and projects naturally

    Example Profile:
    {
        "name": "Jef Adriaenssens",
        "aliases": ["Jeff", "Jef", "jef"],  # Auto-correct spelling
        "role": "Product Manager",
        "company": "JustEat Takeaway",
        "projects": ["CRESCO", "RF16", "Just Deals"],
        "markets": ["Spain", "UK", "Netherlands"],
        "colleagues": {
            "Andy": "Andy Maclean",
            "Alberto": "Alberto Moraleda Fernandez - Spain market",
            "Maran": "Maran Vleems"
        }
    }

    Relationships:
    - No explicit relationships (user_id links to future User model)
    """
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, default=1, index=True)  # Default user ID for single-user mode

    # Basic info
    name = Column(String(255), nullable=False)
    aliases = Column(JSON, default=list)  # ["Jeff", "Jef"] for name correction
    role = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)

    # Work context
    projects = Column(JSON, default=list)  # ["CRESCO", "RF16"]
    markets = Column(JSON, default=list)  # ["Spain", "UK"]
    colleagues = Column(JSON, default=dict)  # {"Andy": "Andy Maclean"}

    # Preferences
    preferences = Column(JSON, default=dict)  # Future: time zones, work hours, etc.

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaskEnrichment(Base):
    """Tracks task enrichments (auto-updates to existing tasks).

    When new context arrives that relates to existing tasks, the AI can:
    - Update deadlines
    - Add notes/comments
    - Change priority
    - Link related tasks

    This model tracks these enrichment operations for:
    - User visibility (what changed and why)
    - Learning (did enrichment improve quality?)
    - Rollback (undo if needed)

    Relationships:
    - task: Many-to-one with Task
    - context_item: Many-to-one with ContextItem (what triggered the enrichment)
    """
    __tablename__ = "task_enrichments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    context_item_id = Column(Integer, ForeignKey("context_items.id", ondelete="SET NULL"), nullable=True)

    # What changed
    enrichment_type = Column(String(50), nullable=False)  # deadline_update, note_added, priority_change, etc.
    before_value = Column(JSON, nullable=True)  # State before enrichment
    after_value = Column(JSON, nullable=True)  # State after enrichment

    # Why it changed
    reasoning = Column(Text, nullable=True)  # AI explanation
    confidence_score = Column(Float, nullable=True)  # Confidence in enrichment (0.0-1.0)
    auto_applied = Column(Boolean, default=False)  # True if applied without user approval

    # User feedback
    user_approved = Column(Boolean, nullable=True)  # NULL = pending, True = approved, False = rejected

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    task = relationship("Task", backref="enrichments")
    context_item = relationship("ContextItem", backref="enrichments")


# ============================================================================
# PHASE 4: GOOGLE CALENDAR INTEGRATION
# ============================================================================

class GoogleOAuthToken(Base):
    """Stores Google OAuth tokens for calendar integration.

    This model manages OAuth credentials for accessing Google Calendar API.
    Tokens are refreshed automatically when expired.

    Security Notes:
    - access_token: Short-lived token (typically 1 hour)
    - refresh_token: Long-lived token for getting new access tokens
    - Tokens should be encrypted in production

    Relationships:
    - No explicit relationships (user_id links to future User model)
    """
    __tablename__ = "google_oauth_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, default=1, index=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_expiry = Column(DateTime, nullable=False)
    scopes = Column(JSON, nullable=False)  # List of granted scopes
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CalendarEvent(Base):
    """Cached Google Calendar events.

    This model caches calendar events from Google Calendar for:
    - Fast availability analysis (no API calls needed)
    - Offline access to schedule
    - Meeting context extraction
    - Related task linking

    Events are synced every 15 minutes via background scheduler.

    Event Types:
    - Meetings: Multiple attendees
    - Focus blocks: Single attendee (user)
    - Task blocks: Created by Lotus (🪷 prefix)

    Relationships:
    - No explicit relationships to Task (uses related_task_ids JSON)
    """
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, default=1, index=True)
    google_event_id = Column(String(255), unique=True, nullable=False, index=True)

    # Event details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(500), nullable=True)

    # Timing
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    timezone = Column(String(100), nullable=True, default="Europe/Amsterdam")
    all_day = Column(Boolean, default=False)

    # Participants
    attendees = Column(JSON, default=list)  # List of email addresses
    organizer = Column(String(255), nullable=True)
    is_meeting = Column(Boolean, default=True)  # False for personal blocks

    # Context extraction (from MeetingParserAgent)
    importance_score = Column(Integer, nullable=True)  # 0-100
    related_projects = Column(JSON, default=list)  # ["CRESCO", "RF16"]
    related_task_ids = Column(JSON, default=list)  # Task IDs mentioned in meeting
    prep_needed = Column(Boolean, default=False)
    prep_checklist = Column(JSON, default=list)  # List of prep items

    # Sync metadata
    last_synced = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScheduledBlock(Base):
    """Scheduled time blocks for task work.

    This model tracks scheduling suggestions and approved time blocks:
    - AI suggests optimal times for tasks
    - User approves/reschedules/dismisses
    - Approved blocks create Google Calendar events

    Status Flow:
    1. 'suggested': SchedulingAgent proposed this time
    2. 'approved': User approved, calendar event created
    3. 'rescheduled': User requested different time
    4. 'dismissed': User rejected suggestion
    5. 'completed': Task work finished
    6. 'cancelled': Block cancelled (meeting conflict, etc.)

    Relationships:
    - task: Many-to-one with Task (which task to work on)
    """
    __tablename__ = "scheduled_blocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, default=1, index=True)

    # Timing
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=False)

    # Google Calendar integration
    calendar_event_id = Column(String(255), nullable=True)  # Google Calendar event ID (when approved)

    # AI scheduling metadata
    status = Column(String(50), nullable=False, default='suggested', index=True)
    confidence_score = Column(Integer, nullable=True)  # 0-100
    reasoning = Column(Text, nullable=True)  # Why this time was suggested
    quality_score = Column(Integer, nullable=True)  # Time block quality (0-100)

    # User feedback
    user_feedback = Column(JSON, nullable=True)  # Why rescheduled/dismissed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    task = relationship("Task", backref="scheduled_blocks")


class WorkPreferences(Base):
    """User work preferences for scheduling.

    This model stores user preferences used by SchedulingAgent:
    - Best time for deep work (morning/afternoon/evening)
    - Meeting preferences (back-to-back vs spaced out)
    - Work hours (no meetings before 9am)
    - Task block sizes (30min, 1hr, 2hr)

    Example Preferences (Jef):
    {
        "deep_work_time": "afternoon_evening",
        "preferred_task_time": "afternoon",
        "no_meetings_before": "09:00",
        "meeting_style": "back_to_back",
        "meeting_buffer": 0,
        "min_task_block": 30,
        "preferred_block_sizes": [30, 60, 90, 120],
        "task_event_prefix": "🪷 ",
        "task_event_color": "9",
        "auto_create_blocks": false
    }

    Relationships:
    - No explicit relationships (user_id links to future User model)
    """
    __tablename__ = "work_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, default=1, unique=True, index=True)

    # Time preferences
    deep_work_time = Column(String(50), default="afternoon")  # morning, afternoon, evening, afternoon_evening
    preferred_task_time = Column(String(50), default="afternoon")
    no_meetings_before = Column(String(10), default="09:00")  # HH:MM format
    no_meetings_after = Column(String(10), default="18:00")

    # Meeting style
    meeting_style = Column(String(50), default="back_to_back")  # back_to_back, spaced_out
    meeting_buffer = Column(Integer, default=0)  # Minutes between meetings

    # Task scheduling
    min_task_block = Column(Integer, default=30)  # Minimum minutes for task block
    preferred_block_sizes = Column(JSON, default=list)  # [30, 60, 90, 120]

    # Calendar preferences
    task_event_prefix = Column(String(50), default="🪷 ")  # Prefix for task events
    task_event_color = Column(String(10), default="9")  # Google Calendar color ID

    # Automation
    auto_create_blocks = Column(Boolean, default=False)  # Phase 4: Always false (needs approval)
    high_confidence_threshold = Column(Integer, default=90)  # Future: auto-create if >90%

    # Additional preferences
    preferences_json = Column(JSON, default=dict)  # Extensible preferences

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaskTimeLog(Base):
    """Track actual time spent on tasks vs estimated.

    This model enables pattern learning:
    - How long do tasks actually take?
    - Which time blocks are most productive?
    - Does Jef work better in afternoon vs morning?

    Used for:
    - Improving scheduling suggestions (learn from history)
    - Better time estimates
    - Productivity analytics

    Relationships:
    - task: Many-to-one with Task
    - scheduled_block: Many-to-one with ScheduledBlock (optional)
    """
    __tablename__ = "task_time_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    scheduled_block_id = Column(Integer, ForeignKey("scheduled_blocks.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, nullable=False, default=1, index=True)

    # Time tracking
    estimated_duration = Column(Integer, nullable=True)  # Minutes (from AI estimate)
    actual_duration = Column(Integer, nullable=True)  # Minutes (actual time spent)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Productivity metrics
    time_of_day = Column(String(50), nullable=True)  # morning, afternoon, evening
    productivity_rating = Column(Integer, nullable=True)  # 1-5 (optional user rating)
    interruptions = Column(Integer, default=0)  # Number of interruptions

    # Context
    work_location = Column(String(50), nullable=True)  # office, home, etc.
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    task = relationship("Task", backref="time_logs")
    scheduled_block = relationship("ScheduledBlock", backref="time_logs")


class MeetingPrep(Base):
    """Meeting preparation suggestions.

    This model tracks meeting prep needs:
    - Which meetings need preparation?
    - What tasks should be completed before?
    - What materials to review?

    Generated by MeetingPrepAssistant and displayed in dashboard.

    Urgency Levels:
    - 'critical': Meeting in <4 hours
    - 'high': Meeting in <24 hours
    - 'medium': Meeting in <48 hours
    - 'low': Meeting in >48 hours

    Relationships:
    - calendar_event: Many-to-one with CalendarEvent
    """
    __tablename__ = "meeting_prep"

    id = Column(Integer, primary_key=True, autoincrement=True)
    calendar_event_id = Column(Integer, ForeignKey("calendar_events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, default=1, index=True)

    # Prep details
    prep_needed = Column(Boolean, default=True)
    prep_checklist = Column(JSON, default=list)  # List of prep items
    incomplete_task_ids = Column(JSON, default=list)  # Tasks to finish before meeting
    estimated_prep_time = Column(Integer, nullable=True)  # Minutes

    # Urgency
    urgency = Column(String(50), nullable=False, default='medium')  # critical, high, medium, low
    priority_score = Column(Integer, nullable=True)  # 0-100

    # AI reasoning
    reasoning = Column(Text, nullable=True)  # Why prep is needed

    # User status
    prep_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    calendar_event = relationship("CalendarEvent", backref="prep_suggestions")


# ============================================================================
# Phase 5: Gmail Integration Models
# ============================================================================


class EmailAccount(Base):
    """Gmail account for email ingestion.

    Stores account credentials and sync settings.
    Uses shared OAuth from GoogleOAuthToken.

    Relationships:
    - email_messages: One-to-many with EmailMessage
    - email_threads: One-to-many with EmailThread
    """
    __tablename__ = "email_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, default=1, index=True)
    email_address = Column(String(255), nullable=False, unique=True)
    provider = Column(String(50), nullable=False, default='gmail')

    # Auth (uses shared GoogleOAuthToken, this is for future encryption)
    auth_token_encrypted = Column(Text, nullable=True)

    # Sync settings
    last_sync_at = Column(DateTime, nullable=True)
    sync_enabled = Column(Boolean, default=True)
    sync_interval_minutes = Column(Integer, default=20)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    email_messages = relationship("EmailMessage", back_populates="account", cascade="all, delete-orphan")
    email_threads = relationship("EmailThread", back_populates="account", cascade="all, delete-orphan")


class EmailMessage(Base):
    """Processed email message.

    Stores email content, classification, and links to tasks.

    Classification Types:
    - 'actionable': Email requires action → create task
    - 'meeting_invite': Calendar invitation
    - 'fyi': Informational only
    - 'automated': Automated/system email
    - 'unprocessed': Not yet classified

    Relationships:
    - account: Many-to-one with EmailAccount
    - task: Many-to-one with Task (primary task created from email)
    - thread: Many-to-one with EmailThread
    - task_links: Many-to-many with Task via EmailTaskLink
    """
    __tablename__ = "email_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Gmail identifiers
    gmail_message_id = Column(String(255), nullable=False, unique=True, index=True)
    thread_id = Column(String(255), nullable=False, index=True)

    # Relationships
    account_id = Column(Integer, ForeignKey("email_accounts.id", ondelete="CASCADE"), nullable=False)

    # Email content
    subject = Column(Text, nullable=True)
    sender = Column(String(500), nullable=True)  # Full "Name <email>" format
    sender_name = Column(String(255), nullable=True)
    sender_email = Column(String(255), nullable=True, index=True)
    recipient_to = Column(Text, nullable=True)
    recipient_cc = Column(Text, nullable=True)
    recipient_bcc = Column(Text, nullable=True)

    # Body
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    snippet = Column(Text, nullable=True)

    # Metadata
    labels = Column(JSON, default=list)
    has_attachments = Column(Boolean, default=False)
    links = Column(JSON, default=list)
    action_phrases = Column(JSON, default=list)
    is_meeting_invite = Column(Boolean, default=False)

    # Timestamps
    received_at = Column(DateTime, nullable=True, index=True)
    processed_at = Column(DateTime, nullable=True, index=True)

    # Classification
    classification = Column(String(50), nullable=True, index=True)  # actionable, meeting_invite, fyi, automated
    classification_confidence = Column(Float, nullable=True)

    # Task relationship
    task_id = Column(String, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    account = relationship("EmailAccount", back_populates="email_messages")
    task = relationship("Task", foreign_keys=[task_id], backref="source_emails")
    task_links = relationship("EmailTaskLink", back_populates="email", cascade="all, delete-orphan")


class EmailThread(Base):
    """Email thread consolidation.

    Groups related emails and optionally creates consolidated task.

    When thread has 5+ messages, create single consolidated task
    instead of individual tasks.

    Relationships:
    - account: Many-to-one with EmailAccount
    - messages: One-to-many with EmailMessage (via thread_id)
    - consolidated_task: Many-to-one with Task
    """
    __tablename__ = "email_threads"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Gmail identifiers
    gmail_thread_id = Column(String(255), nullable=False, unique=True, index=True)

    # Relationship
    account_id = Column(Integer, ForeignKey("email_accounts.id", ondelete="CASCADE"), nullable=False)

    # Thread metadata
    subject = Column(Text, nullable=True)
    participant_emails = Column(JSON, default=list)
    message_count = Column(Integer, default=1)

    # Timestamps
    first_message_at = Column(DateTime, nullable=True)
    last_message_at = Column(DateTime, nullable=True, index=True)

    # Consolidation
    is_consolidated = Column(Boolean, default=False)
    consolidated_task_id = Column(String, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    account = relationship("EmailAccount", back_populates="email_threads")
    consolidated_task = relationship("Task", foreign_keys=[consolidated_task_id], backref="consolidated_from_thread")


class EmailTaskLink(Base):
    """Many-to-many relationship between emails and tasks.

    Links emails to tasks they created or are related to.

    Relationship Types:
    - 'created_from': Task created from this email
    - 'related_to': Email mentions existing task
    - 'thread_member': Part of thread that created task
    - 'meeting_prep': Email for meeting with prep task

    Unique constraint ensures no duplicate links.

    Relationships:
    - email: Many-to-one with EmailMessage
    - task: Many-to-one with Task
    """
    __tablename__ = "email_task_links"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Relationships
    email_id = Column(Integer, ForeignKey("email_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)

    # Link metadata
    relationship_type = Column(String(50), default='created_from')

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    email = relationship("EmailMessage", back_populates="task_links")
    task = relationship("Task", backref="email_links")
