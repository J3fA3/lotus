"""
Database connection and session management
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from .models import Base

# Import knowledge graph models so they're registered with Base.metadata
# This ensures their tables are created when init_db() runs
from .knowledge_graph_models import (  # noqa: F401
    KnowledgeNode,
    KnowledgeEdge,
    EntityKnowledgeLink,
    TeamStructureEvolution,
    KnowledgeGraphStats
)

# Import Phase 4 calendar models
from .models import (  # noqa: F401
    GoogleOAuthToken,
    CalendarEvent,
    ScheduledBlock,
    WorkPreferences,
    TaskTimeLog,
    MeetingPrep
)

# Import Phase 6 models (Cognitive Nexus)
from .knowledge_graph_models_v2 import (  # noqa: F401
    ConceptNode,
    ConversationThreadNode,
    TaskOutcomeNode,
    ConceptRelationship,
    TaskSimilarityIndex,
    ConceptTaskLink
)

from .task_version_models import (  # noqa: F401
    TaskVersion,
    VersionDiff,
    VersionComment
)

from .question_queue_models import (  # noqa: F401
    QuestionQueue,
    QuestionBatch,
    QuestionEngagementMetrics
)

from .implicit_learning_models import (  # noqa: F401
    ImplicitSignal,
    SignalAggregate,
    LearningModel,
    ModelPerformanceLog
)

from .outcome_learning_models import (  # noqa: F401
    OutcomeQualityCorrelation,
    LearningPriorityScore,
    QualityFeatureAnalysis
)

from .task_quality_models import (  # noqa: F401
    TaskQualityScore,
    QualityTrend
)

# Configuration
DEFAULT_DATABASE_URL = "sqlite:///./tasks.db"

def get_database_url() -> str:
    """Get configured database URL with async driver support"""
    url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    
    # Convert sqlite:/// to sqlite+aiosqlite:/// for async support
    if url.startswith("sqlite:///"):
        url = url.replace("sqlite:///", "sqlite+aiosqlite:///")
        # Add timeout parameter for SQLite to prevent hanging
        # Timeout is in seconds (10 seconds)
        if "?" not in url:
            url += "?timeout=10.0"
        elif "timeout" not in url:
            url += "&timeout=10.0"
    
    return url

# Get database URL
DATABASE_URL = get_database_url()

# Create async engine with connection pool settings
# These settings help prevent hanging on SQLite connections
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DEBUG", "false").lower() == "true",
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
    # For aiosqlite, timeout is set via URL query parameter
    # connect_args are handled differently for async SQLite
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency for getting database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
