"""
FastAPI backend for AI-powered task management
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from db.database import init_db
from api.routes import router
from services.knowledge_graph_scheduler import scheduler
from services.knowledge_graph_config import config as kg_config
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
    """Manage application startup and shutdown"""
    # Startup
    print("🚀 Initializing database...")
    await init_db()
    print("✅ Database initialized")

    ollama_model = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    ollama_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL)
    print(f"🤖 AI Model: {ollama_model}")
    print(f"🔗 Ollama URL: {ollama_url}")

    # Start Knowledge Graph scheduler if decay is enabled
    if kg_config.DECAY_ENABLED:
        print(f"⏰ Starting Knowledge Graph scheduler...")
        print(f"   Decay updates every {kg_config.DECAY_UPDATE_INTERVAL_HOURS}h")
        print(f"   Half-life: {kg_config.DECAY_HALF_LIFE_DAYS} days")
        scheduler.start()
        print("✅ Scheduler started")
    else:
        print("⚠️  Knowledge Graph decay disabled")

    yield

    # Shutdown
    if kg_config.DECAY_ENABLED and scheduler.is_running:
        print("⏰ Stopping Knowledge Graph scheduler...")
        scheduler.stop()

    print("👋 Shutting down...")


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

# Include GraphQL endpoint (if enabled)
if kg_config.GRAPHQL_ENABLED:
    graphql_router = create_graphql_router()
    if graphql_router:
        app.include_router(graphql_router, prefix="/api", tags=["GraphQL"])
        print(f"🔷 GraphQL enabled at /api{kg_config.GRAPHQL_PATH}")


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

    print(f"\n🚀 Starting server on {host}:{port}")
    print(f"📚 API Docs: http://localhost:{port}/docs")
    print(f"🏥 Health Check: http://localhost:{port}/api/health")

    if kg_config.GRAPHQL_ENABLED:
        print(f"🔷 GraphQL Playground: http://localhost:{port}/api{kg_config.GRAPHQL_PATH}")

    print()

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug
    )
