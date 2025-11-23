"""
FastAPI backend for AI-powered task management
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

from db.database import init_db
from api.routes import router
from api.assistant_routes import router as assistant_router
from api.calendar_routes import router as calendar_router
from services.knowledge_graph_scheduler import scheduler
from services.knowledge_graph_config import config as kg_config
from services.calendar_scheduler import get_calendar_scheduler
from services.phase6_learning_scheduler import get_phase6_learning_scheduler
from api.knowledge_graphql_schema import create_graphql_router
from config.constants import (
    API_TITLE,
    API_DESCRIPTION,
    API_VERSION,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_URL,
    DEFAULT_CORS_ORIGINS,
    DEFAULT_API_HOST,
    DEFAULT_API_PORT
)

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    # Startup
    logger.info("🚀 Initializing database...")
    await init_db()
    logger.info("✅ Database initialized")

    # Initialize work preferences (Phase 4)
    logger.info("📋 Initializing user preferences...")
    from services.work_preferences import ensure_preferences_exist
    from db.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await ensure_preferences_exist(db, user_id=1)
    logger.info("✅ Preferences initialized")

    ollama_model = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    ollama_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL)
    logger.info(f"🤖 AI Model: {ollama_model}")
    logger.info(f"🔗 Ollama URL: {ollama_url}")

    # Start Knowledge Graph scheduler if decay is enabled
    if kg_config.DECAY_ENABLED:
        logger.info(f"⏰ Starting Knowledge Graph scheduler...")
        logger.info(f"   Decay updates every {kg_config.DECAY_UPDATE_INTERVAL_HOURS}h")
        logger.info(f"   Half-life: {kg_config.DECAY_HALF_LIFE_DAYS} days")
        scheduler.start()
        logger.info("✅ Scheduler started")
    else:
        logger.warning("⚠️  Knowledge Graph decay disabled")

    # Start Calendar scheduler (Phase 4)
    logger.info("📅 Starting Calendar scheduler...")
    calendar_scheduler = get_calendar_scheduler()
    calendar_scheduler.start()

    # Start Email Polling Service (Phase 5)
    logger.info("📧 Starting Email Polling Service...")
    from services.email_polling_service import get_email_polling_service
    email_polling_service = get_email_polling_service()
    try:
        await email_polling_service.start()
        logger.info(f"✅ Email polling started (every {email_polling_service.poll_interval_minutes} minutes)")
    except Exception as e:
        logger.error(f"⚠️  Failed to start email polling: {e}")
        logger.warning("   Email polling disabled - check OAuth configuration")

    # Start Phase 6 Learning scheduler
    logger.info("🧠 Starting Phase 6 Learning scheduler...")
    phase6_scheduler = get_phase6_learning_scheduler()
    phase6_scheduler.start()

    yield

    # Shutdown
    if kg_config.DECAY_ENABLED and scheduler.is_running:
        logger.info("⏰ Stopping Knowledge Graph scheduler...")
        scheduler.stop()

    logger.info("📅 Stopping Calendar scheduler...")
    calendar_scheduler.stop()

    # Stop Phase 6 Learning scheduler
    logger.info("🧠 Stopping Phase 6 Learning scheduler...")
    phase6_scheduler.stop()

    # Stop Email Polling Service (Phase 5)
    logger.info("📧 Stopping Email Polling Service...")
    try:
        await email_polling_service.stop()
        logger.info("✅ Email polling stopped")
    except Exception as e:
        logger.error(f"Failed to stop email polling: {e}")

    logger.info("👋 Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan
)

# Configure CORS
origins = os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api")
app.include_router(assistant_router, prefix="/api")
app.include_router(calendar_router, prefix="/api")

# Include Phase 6 quality routes
from routes.quality_routes import router as quality_router
app.include_router(quality_router, prefix="/api")

# Include GraphQL endpoint (if enabled)
if kg_config.GRAPHQL_ENABLED:
    graphql_router = create_graphql_router()
    if graphql_router:
        app.include_router(graphql_router, prefix="/api", tags=["GraphQL"])
        logger.info(f"🔷 GraphQL enabled at /api{kg_config.GRAPHQL_PATH}")


@app.get("/")
async def root():
    """Root endpoint with API information"""
    response = {
        "message": API_TITLE,
        "version": API_VERSION,
        "docs": "/docs",
        "health": "/api/health"
    }

    if kg_config.GRAPHQL_ENABLED:
        response["graphql"] = f"/api{kg_config.GRAPHQL_PATH}"
        response["graphql_playground"] = f"/api{kg_config.GRAPHQL_PATH}"

    return response


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", DEFAULT_API_HOST)
    port = int(os.getenv("API_PORT", str(DEFAULT_API_PORT)))
    debug = os.getenv("DEBUG", "true").lower() == "true"

    logger.info(f"\n🚀 Starting server on {host}:{port}")
    logger.info(f"📚 API Docs: http://localhost:{port}/docs")
    logger.info(f"🏥 Health Check: http://localhost:{port}/api/health")

    if kg_config.GRAPHQL_ENABLED:
        logger.info(f"🔷 GraphQL Playground: http://localhost:{port}/api{kg_config.GRAPHQL_PATH}")

    logger.info("")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug
    )
