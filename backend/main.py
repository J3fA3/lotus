"""
FastAPI backend for Lotus v2 — Intelligence Flywheel Task Board
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from db.database import init_db
from api.routes import router
from config.constants import (
    API_TITLE,
    API_DESCRIPTION,
    API_VERSION,
    DEFAULT_CORS_ORIGINS,
    DEFAULT_API_HOST,
    DEFAULT_API_PORT,
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan,
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


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": API_TITLE,
        "version": API_VERSION,
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", DEFAULT_API_HOST)
    port = int(os.getenv("API_PORT", str(DEFAULT_API_PORT)))
    debug = os.getenv("DEBUG", "true").lower() == "true"

    logger.info(f"\nStarting server on {host}:{port}")
    logger.info(f"API Docs: http://localhost:{port}/docs")
    logger.info(f"Health Check: http://localhost:{port}/api/health")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
    )
