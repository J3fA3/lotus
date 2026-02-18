# Claude Code Project Directives — Lotus v2

## Project Context

**What This Project Does:**
Lotus v2 is a personal task management system with an AI backend inspired by MERLIN (Multi-agent Executor for Recursive Logic Iteration and Navigation). The frontend is a clean Kanban task board. The backend implements an Intelligence Flywheel: every completed task becomes a case study that's semantically indexed, making the AI smarter over time.

**Vision:**
A task board that works for you. AI learns from every completed task, builds tools to help with future tasks, gets smarter through use. Not a chatbot — a compounding intelligence engine.

---

## Guiding Principles

### 1. Simplicity Over Sophistication
Every service is a plain Python module with clear functions — no state machines, no agent graphs, no orchestrators.

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
  scripts/
    export_data.py           # Export all task data to JSON (any schema version)
    import_data.py           # Import task data into v2 database
  config/
    constants.py             # App constants

src/                         # Frontend (React 18 + TypeScript + Vite)
  components/
    KanbanBoard.tsx          # Main board with drag-and-drop
    TaskCard.tsx             # Task card with badges
    TaskDetailSheet.tsx      # Side panel for task editing
    TaskFullPage.tsx         # Full-page task view
    AskLotus.tsx             # Collapsible AI assist UI
    QuickAddTask.tsx         # Inline task creation
    TaskSearchBar.tsx        # Semantic search input
    DeleteTaskDialog.tsx     # Confirmation dialog
    ValueStreamCombobox.tsx  # Value stream picker
    RichTextEditor.tsx       # Tiptap WYSIWYG with slash commands + Word Art
    RichTextEditorMenu.tsx   # Slash command menu with search filtering
    WordArtExtension.tsx     # 8 retro text styles (custom Tiptap node)
    TableMenu.tsx            # Floating table editing toolbar
    rich-text-editor.css     # Editor + Word Art + table styling
    UnifiedAttachments.tsx   # Smart URL attachments with clickable links
    CommentItem.tsx          # Comment display/edit
    LotusIcon.tsx            # Animated Lotus icon
    LotusLoading.tsx         # Loading state component
    ui/                      # shadcn/ui components (keep minimal — only add what you use)
  api/
    tasks.ts                 # Task CRUD + search API client
    ai.ts                    # AI assist API client
    shortcuts.ts             # Keyboard shortcuts API client
    valueStreams.ts           # Value stream API client
  contexts/
    ShortcutContext.tsx       # Global shortcut state management
  hooks/
    useKeyboardHandler.ts    # Keyboard shortcut handling
    use-toast.ts             # Toast notification hook
    use-mobile.tsx           # Mobile detection hook
  types/
    task.ts                  # Task type definitions
    shortcuts.ts             # Shortcut type definitions
  lib/
    utils.ts                 # Utility functions (cn, etc.)
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

### Data Migration
```bash
# Export from existing database (handles old + new schema)
python backend/scripts/export_data.py --db backend/tasks.db

# Import into fresh v2 database
python backend/scripts/import_data.py --input backend/data_export.json
```

### Testing
- Backend: pytest with async fixtures
- Frontend: TypeScript compilation via `npm run build`

## Code Style
- **Python:** snake_case files/functions, PascalCase classes
- **TypeScript:** PascalCase components, camelCase utils
- **shadcn/ui:** Only add components you actually import — do not bulk-install
