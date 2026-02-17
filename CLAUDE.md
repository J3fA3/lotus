# Claude Code Project Directives — Lotus v2

## Project Context

**What This Project Does:**
Lotus v2 is a personal task management system with an AI backend inspired by MERLIN (Multi-agent Executor for Recursive Logic Iteration and Navigation). The frontend is a clean Kanban task board. The backend implements an Intelligence Flywheel: every completed task becomes a case study that's semantically indexed, making the AI smarter over time.

**Phase 1 Goal:**
Fork current Lotus, strip all bloated backend (LangGraph agents, OAuth, knowledge graph, ChromaDB), strip AI-specific frontend UI, implement MERLIN flywheel foundation: Case Memory + Semantic RAG + minimal AI service.

**Full Vision:**
A task board that works for you. AI learns from every completed task, builds tools to help with future tasks, gets smarter through use. Not a chatbot — a compounding intelligence engine.

---

## Guiding Principles

### 1. Simplicity Over Sophistication
The old Lotus was over-engineered. The new Lotus follows MERLIN: simple infrastructure, compounding intelligence through use. Every service is a plain Python module with clear functions — no state machines, no agent graphs, no orchestrators.

### 2. Output-as-RAG: Every Completion is Learning
When a task is marked "Done", the system creates a structured case study. This is embedded and indexed. Future tasks benefit from past completions. Doing work = getting smarter.

### 3. File-Based Case Memory (No Heavy Infrastructure)
Case studies are directories with markdown and JSON files, NOT database records. Vector index is a single JSON file. No external services. ~3.5KB per case study.

### 4. Local Embeddings, Zero API Cost for Search
sentence-transformers with all-MiniLM-L6-v2. All vector ops local. Only AI generation calls external API. Search <100ms.

### 5. The AI Serves the Task, Not the Other Way Around
UI is a task board first. AI is ambient helper. "Ask Lotus" is small, collapsible — not a chat window, not a command system.

---

## Architecture

```
backend/
  main.py                    # FastAPI app (minimal)
  api/
    routes.py                # Task CRUD + shortcuts + value streams + AI endpoints
    schemas.py               # Pydantic schemas
  db/
    database.py              # SQLite async engine
    models.py                # Task, Comment, Attachment, ValueStream, ShortcutConfig
  services/
    gemini_client.py         # Gemini 2.0 Flash API client
    case_memory.py           # Create case studies from completed tasks
    semantic_rag.py          # Local embeddings + vector search
    ai_service.py            # Search cases → Gemini → response
  case_studies/              # MERLIN-style case memory (file-based)
  config/
    constants.py             # App constants

src/                         # Frontend (React 18 + TypeScript + Vite)
  components/
    KanbanBoard.tsx          # Main board with drag-and-drop
    TaskCard.tsx             # Task card display
    TaskDetailSheet.tsx      # Task detail panel
    AskLotus.tsx             # Collapsible AI assist UI
    ui/                      # shadcn/ui components
  api/
    tasks.ts                 # Task CRUD API client
    ai.ts                    # AI assist API client
```

## Development Workflow

### Commands
```bash
# Backend
cd backend && python main.py                    # Start server on :8000
cd backend && python -m pytest tests/           # Run tests

# Frontend
npm run dev                                      # Start dev server on :5173
npm run build                                    # Type-check + build
```

### Testing
- Backend: pytest with async fixtures
- Frontend: TypeScript compilation via `npm run build`

## Code Style
- **Python:** snake_case files/functions, PascalCase classes
- **TypeScript:** PascalCase components, camelCase utils
- **Commits:** `[Stage X]: Brief description`
