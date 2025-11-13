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

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("🚀 Initializing database...")
    await init_db()
    print("✅ Database initialized")

    print(f"🤖 AI Model: {os.getenv('OLLAMA_MODEL', 'qwen2.5:7b-instruct')}")
    print(f"🔗 Ollama URL: {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}")

    yield

    # Shutdown
    print("👋 Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="AI Task Inference API",
    description="Backend for AI-powered task management with Qwen 2.5",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

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
    """Root endpoint"""
    return {
        "message": "AI Task Inference API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))

    print(f"\n🚀 Starting server on {host}:{port}")
    print(f"📚 API Docs: http://localhost:{port}/docs\n")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "true") == "true"
    )
