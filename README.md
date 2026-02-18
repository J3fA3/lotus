# Lotus v2 — Intelligence Flywheel Task Board

A personal task management system where completing tasks makes the AI smarter. Kanban board frontend with a MERLIN-inspired backend: every completed task becomes a semantically indexed case study, building compounding intelligence over time.

## Features

- **Kanban Board** — Drag-and-drop across To Do / Doing / Done columns
- **Task Management** — CRUD with comments, attachments, notes, and value stream categorization
- **Keyboard Shortcuts** — 45+ configurable shortcuts with conflict detection
- **Search** — Semantic search across all tasks
- **Intelligence Flywheel** — Completed tasks automatically become case studies indexed for future AI context
- **Ask Lotus** — Collapsible AI assistant powered by Gemini 2.0 Flash + local semantic RAG

## Quick Start

### One-command local start (recommended)

```bash
./start-local.sh
```

What this does:
- Ensures `backend/.env` exists (copies from `backend/.env.example` if missing)
- Creates `backend/venv` and installs backend dependencies if needed
- Installs frontend dependencies if needed
- Starts backend and frontend for local development

Your Gemini key stays local: `backend/.env` is git-ignored and will not be committed.

### Backend

```bash
cd backend
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Add your GOOGLE_AI_API_KEY
python main.py              # Starts on :8000
```

### Frontend

```bash
npm install
npm run dev                 # Starts on :5173
```

Open http://localhost:5173 in your browser.

If port `5173` is already in use, Vite automatically selects the next available port.

## Architecture

```
backend/
  main.py                    # FastAPI app
  api/
    routes.py                # Task CRUD + shortcuts + value streams + AI endpoints
    schemas.py               # Pydantic models
  db/
    database.py              # SQLite async engine (aiosqlite)
    models.py                # Task, Comment, Attachment, ValueStream, ShortcutConfig
  services/
    gemini_client.py         # Gemini 2.0 Flash API client
    case_memory.py           # Create case studies from completed tasks
    semantic_rag.py          # Local embeddings + vector search (all-MiniLM-L6-v2)
    ai_service.py            # Search cases + Gemini = contextual response
  case_studies/              # File-based case memory (~3.5KB each)
  scripts/
    export_data.py           # Export all task data to JSON
    import_data.py           # Import task data into fresh DB

src/                         # React 18 + TypeScript + Vite
  components/
    KanbanBoard.tsx          # Main board with drag-and-drop
    TaskCard.tsx             # Task card with badges
    TaskDetailSheet.tsx      # Side panel for task editing
    TaskFullPage.tsx         # Full-page task view
    AskLotus.tsx             # Collapsible AI assist
    QuickAddTask.tsx         # Inline task creation
    TaskSearchBar.tsx        # Semantic search input
    DeleteTaskDialog.tsx     # Confirmation dialog
    ValueStreamCombobox.tsx  # Value stream picker
    CommentItem.tsx          # Comment display/edit
    ui/                      # shadcn/ui primitives
  api/
    tasks.ts                 # Task CRUD + search client
    ai.ts                    # AI assist client
    shortcuts.ts             # Keyboard shortcuts client
    valueStreams.ts           # Value stream client
  contexts/
    ShortcutContext.tsx       # Global shortcut state
  types/
    task.ts                  # Task type definitions
    shortcuts.ts             # Shortcut type definitions
```

## Intelligence Flywheel

The core innovation: **doing work = getting smarter.**

1. User completes a task (moves to "Done")
2. System creates a structured case study (markdown + JSON)
3. Case study is embedded locally using sentence-transformers (all-MiniLM-L6-v2)
4. Vector index updated (single JSON file, no external services)
5. Future "Ask Lotus" queries find relevant past case studies via semantic search
6. Gemini generates responses with real context from your completed work

All vector operations are local. Only AI generation calls the external Gemini API. Search runs in <100ms.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_AI_API_KEY` | Gemini API key | (required for AI features) |
| `GEMINI_MODEL` | Gemini model ID | `gemini-2.0-flash-exp` |
| `DATABASE_URL` | SQLite connection | `sqlite:///./tasks.db` |
| `API_HOST` | Backend host | `0.0.0.0` |
| `API_PORT` | Backend port | `8000` |
| `CORS_ORIGINS` | Allowed origins | `http://localhost:5173` |
| `DEBUG` | Debug logging | `true` |

## Data Migration

If you have existing task data from a previous version:

```bash
# Export from old database (handles any schema version)
python backend/scripts/export_data.py --db backend/tasks.db

# Import into fresh v2 database
python backend/scripts/import_data.py --input backend/data_export.json
```

## Development

```bash
# Frontend type-check + build
npm run build

# Backend tests
cd backend && python -m pytest tests/ -v

# API docs (when backend is running)
open http://localhost:8000/docs
```

## Tech Stack

- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Query
- **Backend:** FastAPI, SQLAlchemy 2.0 (async), aiosqlite
- **AI:** Gemini 2.0 Flash, sentence-transformers (local embeddings)
- **Database:** SQLite
