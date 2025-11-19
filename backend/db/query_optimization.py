"""
Database Query Optimization Patterns - Phase 5

Best practices and utilities for optimizing database queries in Lotus.

Key Optimizations:
1. Eager loading to prevent N+1 queries
2. Index-aware query construction
3. Batch loading for related entities
4. Query result caching (via kg_cache)
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    Task, Entity, Relationship, Comment,
    EmailMessage, EmailThread, EmailTaskLink,
    CalendarEvent, ContextItem
)


# ==============================================================================
# Eager Loading Helpers (Prevent N+1 Queries)
# ==============================================================================


async def get_tasks_with_relationships(
    db: AsyncSession,
    task_ids: Optional[List[str]] = None,
    limit: int = 50
) -> List[Task]:
    """Get tasks with eagerly loaded relationships.

    Prevents N+1 queries by loading entities, relationships, and comments
    in a single query using joinedload.

    Args:
        db: Database session
        task_ids: Optional list of specific task IDs
        limit: Maximum tasks to return

    Returns:
        List of tasks with relationships loaded

    Performance:
        - Without eager loading: 1 + N queries (1 for tasks, N for each relationship)
        - With eager loading: 1-3 queries total
    """
    query = select(Task).options(
        selectinload(Task.entities),       # Load related entities
        selectinload(Task.relationships),  # Load related relationships
        selectinload(Task.comments)        # Load related comments
    )

    if task_ids:
        query = query.where(Task.id.in_(task_ids))

    query = query.limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_emails_with_tasks(
    db: AsyncSession,
    limit: int = 50
) -> List[EmailMessage]:
    """Get emails with eagerly loaded task relationships.

    Prevents N+1 queries when accessing email.task_id or email.linked_tasks.

    Args:
        db: Database session
        limit: Maximum emails to return

    Returns:
        List of emails with task relationships loaded
    """
    query = (
        select(EmailMessage)
        .options(
            selectinload(EmailMessage.linked_tasks)  # Load EmailTaskLink relationships
        )
        .order_by(EmailMessage.received_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_context_items_with_entities(
    db: AsyncSession,
    limit: int = 50
) -> List[ContextItem]:
    """Get context items with eagerly loaded entities and relationships.

    Args:
        db: Database session
        limit: Maximum context items to return

    Returns:
        List of context items with entities/relationships loaded
    """
    query = (
        select(ContextItem)
        .options(
            selectinload(ContextItem.entities),
            selectinload(ContextItem.relationships)
        )
        .order_by(ContextItem.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    return list(result.scalars().all())


# ==============================================================================
# Batch Loading Utilities
# ==============================================================================


async def get_tasks_by_ids_batch(
    db: AsyncSession,
    task_ids: List[str]
) -> dict[str, Task]:
    """Batch load tasks by IDs (single query).

    Args:
        db: Database session
        task_ids: List of task IDs

    Returns:
        Dict mapping task_id -> Task object
    """
    if not task_ids:
        return {}

    query = select(Task).where(Task.id.in_(task_ids))
    result = await db.execute(query)
    tasks = result.scalars().all()

    return {task.id: task for task in tasks}


async def get_entities_by_names_batch(
    db: AsyncSession,
    entity_names: List[str],
    entity_type: Optional[str] = None
) -> dict[str, Entity]:
    """Batch load entities by names (single query).

    Args:
        db: Database session
        entity_names: List of entity names
        entity_type: Optional entity type filter

    Returns:
        Dict mapping entity_name -> Entity object
    """
    if not entity_names:
        return {}

    query = select(Entity).where(Entity.name.in_(entity_names))

    if entity_type:
        query = query.where(Entity.type == entity_type)

    result = await db.execute(query)
    entities = result.scalars().all()

    return {entity.name: entity for entity in entities}


# ==============================================================================
# Index-Aware Query Patterns
# ==============================================================================


async def get_emails_by_classification_optimized(
    db: AsyncSession,
    classification: str,
    limit: int = 50
) -> List[EmailMessage]:
    """Get emails by classification using optimized index query.

    Uses idx_email_messages_classification index for fast lookup.

    Args:
        db: Database session
        classification: Classification type to filter
        limit: Maximum emails to return

    Returns:
        List of emails matching classification
    """
    # This query uses idx_email_messages_classification index
    query = (
        select(EmailMessage)
        .where(EmailMessage.classification == classification)
        .order_by(EmailMessage.received_at.desc())  # Uses idx_email_messages_received_at
        .limit(limit)
    )

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_unprocessed_emails_optimized(
    db: AsyncSession,
    limit: int = 50
) -> List[EmailMessage]:
    """Get unprocessed emails using index-optimized query.

    Uses idx_email_messages_processed_at index.

    Args:
        db: Database session
        limit: Maximum emails to return

    Returns:
        List of unprocessed emails
    """
    # This query uses idx_email_messages_processed_at index
    query = (
        select(EmailMessage)
        .where(EmailMessage.processed_at.is_(None))
        .order_by(EmailMessage.received_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_recent_threads_optimized(
    db: AsyncSession,
    limit: int = 20
) -> List[EmailThread]:
    """Get recent email threads using index-optimized query.

    Uses idx_email_threads_last_message_at index.

    Args:
        db: Database session
        limit: Maximum threads to return

    Returns:
        List of recent email threads
    """
    query = (
        select(EmailThread)
        .order_by(EmailThread.last_message_at.desc())  # Uses index
        .limit(limit)
    )

    result = await db.execute(query)
    return list(result.scalars().all())


# ==============================================================================
# Query Performance Monitoring
# ==============================================================================


class QueryPerformanceMonitor:
    """Monitor query performance and detect N+1 issues.

    Usage:
        async with QueryPerformanceMonitor(db) as monitor:
            tasks = await get_tasks_with_relationships(db)
            # ... use tasks

        print(monitor.get_stats())  # Shows query count, duration
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.query_count = 0
        self.total_duration_ms = 0

    async def __aenter__(self):
        # Enable query counting (if supported by SQLAlchemy event system)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def get_stats(self) -> dict:
        """Get performance statistics.

        Returns:
            Dict with query_count, total_duration_ms, avg_duration_ms
        """
        return {
            "query_count": self.query_count,
            "total_duration_ms": self.total_duration_ms,
            "avg_duration_ms": (
                self.total_duration_ms / self.query_count
                if self.query_count > 0
                else 0
            )
        }


# ==============================================================================
# Best Practices Documentation
# ==============================================================================

"""
DATABASE QUERY OPTIMIZATION BEST PRACTICES

1. **Use Eager Loading for Related Data**
   - BAD:  tasks = await db.execute(select(Task))
           for task in tasks:
               entities = task.entities  # N+1 query!

   - GOOD: query = select(Task).options(selectinload(Task.entities))
           tasks = await db.execute(query)
           for task in tasks:
               entities = task.entities  # Already loaded!

2. **Batch Load by IDs**
   - BAD:  for task_id in task_ids:
               task = await db.get(Task, task_id)  # N queries!

   - GOOD: tasks = await db.execute(select(Task).where(Task.id.in_(task_ids)))

3. **Use Indexes for Common Queries**
   - Phase 5 created 12 indexes on email tables
   - Always filter/sort by indexed columns when possible
   - Check migration 004 for list of all indexes

4. **Limit Result Sets**
   - Always use .limit() for potentially large queries
   - Default to 50 items for list endpoints
   - Allow max 200 for user-facing APIs

5. **Cache Expensive Queries**
   - Use kg_cache for knowledge graph queries (60s TTL)
   - Cache user profiles, team structures
   - Invalidate cache on writes

6. **Use selectinload vs joinedload**
   - selectinload: Better for one-to-many (tasks -> entities)
   - joinedload: Better for one-to-one or many-to-one

7. **Monitor Query Performance**
   - Use QueryPerformanceMonitor in dev/staging
   - Log slow queries (>100ms)
   - Profile with SQLAlchemy query logging

INDEXES IN PHASE 5 (Migration 004):

Email Messages:
  - idx_email_messages_gmail_id (gmail_message_id)
  - idx_email_messages_thread_id (thread_id)
  - idx_email_messages_processed_at (processed_at)
  - idx_email_messages_classification (classification)
  - idx_email_messages_task_id (task_id)
  - idx_email_messages_received_at (received_at)

Email Threads:
  - idx_email_threads_gmail_thread_id (gmail_thread_id)
  - idx_email_threads_consolidated_task_id (consolidated_task_id)
  - idx_email_threads_last_message_at (last_message_at)

Email-Task Links:
  - idx_email_task_links_email_id (email_id)
  - idx_email_task_links_task_id (task_id)

Email Accounts:
  - idx_email_accounts_user_id (user_id)
  - idx_email_accounts_email_address (email_address)

COMMON QUERY PATTERNS:

# Get recent emails (uses idx_email_messages_received_at)
SELECT * FROM email_messages ORDER BY received_at DESC LIMIT 50;

# Get emails by classification (uses idx_email_messages_classification)
SELECT * FROM email_messages WHERE classification = 'task' LIMIT 50;

# Get tasks for email (uses idx_email_task_links_email_id)
SELECT tasks.* FROM tasks
JOIN email_task_links ON tasks.id = email_task_links.task_id
WHERE email_task_links.email_id = ?;

# Get unprocessed emails (uses idx_email_messages_processed_at)
SELECT * FROM email_messages WHERE processed_at IS NULL;
"""
