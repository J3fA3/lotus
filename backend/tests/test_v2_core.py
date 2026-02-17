"""
Lotus v2 Core Integration Tests

Tests for the minimal Kanban API: health, task CRUD, value streams,
shortcuts, case memory creation, and AI endpoints.
"""
import os
import sys
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Use in-memory SQLite for tests
os.environ["DATABASE_URL"] = "sqlite:////:memory:"
os.environ["DEBUG"] = "false"

from main import app
from db.database import init_db, engine
from db.models import Base


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create fresh tables for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    """Async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ============= Health =============

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "Lotus" in data["message"]


# ============= Task CRUD =============

@pytest.mark.asyncio
async def test_create_task(client):
    resp = await client.post("/api/tasks", json={
        "title": "Test Task",
        "status": "todo",
        "assignee": "Alice",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Task"
    assert data["status"] == "todo"
    assert data["assignee"] == "Alice"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_tasks(client):
    # Create two tasks
    await client.post("/api/tasks", json={"title": "Task 1"})
    await client.post("/api/tasks", json={"title": "Task 2"})

    resp = await client.get("/api/tasks")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_task_by_id(client):
    create_resp = await client.post("/api/tasks", json={"title": "Find Me"})
    task_id = create_resp.json()["id"]

    resp = await client.get(f"/api/tasks/{task_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Find Me"


@pytest.mark.asyncio
async def test_update_task(client):
    create_resp = await client.post("/api/tasks", json={"title": "Original"})
    task_id = create_resp.json()["id"]

    resp = await client.put(f"/api/tasks/{task_id}", json={
        "title": "Updated",
        "status": "doing",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Updated"
    assert data["status"] == "doing"
    # Auto-start-date should be set when moving from todo to doing
    assert data["startDate"] is not None


@pytest.mark.asyncio
async def test_delete_task(client):
    create_resp = await client.post("/api/tasks", json={"title": "Delete Me"})
    task_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/tasks/{task_id}")
    assert resp.status_code == 200

    resp = await client.get(f"/api/tasks/{task_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_task_not_found(client):
    resp = await client.get("/api/tasks/nonexistent")
    assert resp.status_code == 404


# ============= Task completion + case study =============

@pytest.mark.asyncio
async def test_complete_task_creates_case_study(client, tmp_path):
    """When a task moves to 'done', a case study directory is created."""
    create_resp = await client.post("/api/tasks", json={
        "title": "Deployable Feature",
        "description": "Ship the new widget",
    })
    task_id = create_resp.json()["id"]

    # Patch CASE_STUDIES_DIR to use tmp_path
    with patch("services.case_memory.CASE_STUDIES_DIR", tmp_path):
        resp = await client.put(f"/api/tasks/{task_id}", json={"status": "done"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "done"

    # Verify case study was created on disk
    case_dirs = list(tmp_path.iterdir())
    assert len(case_dirs) >= 1
    case_dir = case_dirs[0]
    assert (case_dir / "README.md").exists()
    assert (case_dir / "metadata.json").exists()


# ============= Search =============

@pytest.mark.asyncio
async def test_search_tasks(client):
    await client.post("/api/tasks", json={"title": "Deploy microservice"})
    await client.post("/api/tasks", json={"title": "Write tests"})

    resp = await client.get("/api/tasks/search/deploy")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert "deploy" in data["results"][0]["task"]["title"].lower()


# ============= Value Streams =============

@pytest.mark.asyncio
async def test_value_stream_crud(client):
    # Create
    resp = await client.post("/api/value-streams", json={
        "name": "Platform",
        "color": "#3B82F6",
    })
    assert resp.status_code == 200
    vs_id = resp.json()["id"]

    # List
    resp = await client.get("/api/value-streams")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Delete
    resp = await client.delete(f"/api/value-streams/{vs_id}")
    assert resp.status_code == 200

    resp = await client.get("/api/value-streams")
    assert len(resp.json()) == 0


# ============= Shortcuts =============

@pytest.mark.asyncio
async def test_get_shortcuts_seeds_defaults(client):
    resp = await client.get("/api/shortcuts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    ids = [s["id"] for s in data]
    assert "new_task" in ids
    assert "search" in ids


# ============= AI Endpoints =============

@pytest.mark.asyncio
async def test_ai_assist_returns_response(client):
    """AI assist should return a response even without Gemini configured."""
    create_resp = await client.post("/api/tasks", json={"title": "Need help"})
    task_id = create_resp.json()["id"]

    resp = await client.post("/api/ai/assist", json={"task_id": task_id})
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "similar_cases" in data
    assert "model" in data


@pytest.mark.asyncio
async def test_ai_assist_task_not_found(client):
    resp = await client.post("/api/ai/assist", json={"task_id": "nonexistent"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reindex_endpoint(client):
    resp = await client.post("/api/ai/reindex")
    # 200 if sentence-transformers is installed, 503 if not
    assert resp.status_code in (200, 503)
    if resp.status_code == 200:
        data = resp.json()
        assert "count" in data


# ============= Comments =============

@pytest.mark.asyncio
async def test_add_comments_to_task(client):
    create_resp = await client.post("/api/tasks", json={"title": "Commented Task"})
    task_id = create_resp.json()["id"]

    resp = await client.put(f"/api/tasks/{task_id}", json={
        "comments": [
            {"id": "c1", "text": "First comment", "author": "Alice", "createdAt": "2024-01-01T00:00:00Z"},
            {"id": "c2", "text": "Second comment", "author": "Bob", "createdAt": "2024-01-02T00:00:00Z"},
        ]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["comments"]) == 2
    assert data["comments"][0]["text"] == "First comment"
