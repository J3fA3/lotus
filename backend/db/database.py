"""
Database connection and session management
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .models import Base

# Configuration
DEFAULT_DATABASE_URL = "sqlite:///./tasks.db"


def get_database_url() -> str:
    """Get configured database URL with async driver support"""
    url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

    # Convert sqlite:/// to sqlite+aiosqlite:/// for async support
    if url.startswith("sqlite:///"):
        url = url.replace("sqlite:///", "sqlite+aiosqlite:///")
        if "?" not in url:
            url += "?timeout=10.0"
        elif "timeout" not in url:
            url += "&timeout=10.0"

    return url


# Get database URL
DATABASE_URL = get_database_url()

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DEBUG", "false").lower() == "true",
    pool_pre_ping=True,
    pool_recycle=3600,
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
