# Project Structure

```
task-crate/
├── README.md                    # Project overview and quick start
├── CHANGELOG.md                 # Recent changes and migrations
├── CONTRIBUTING.md              # Development guidelines
├── package.json                 # Frontend dependencies
├── vite.config.ts              # Vite build configuration
├── tailwind.config.ts          # Tailwind CSS setup
│
├── docs/                        # Documentation
│   ├── SETUP.md                # Detailed setup guide
│   ├── ARCHITECTURE.md         # System design docs
│   ├── GETTING_STARTED.md      # Quick start tutorial
│   └── OLLAMA_SETUP.md         # Ollama + SSH tunnel guide
│
├── src/                         # Frontend source
│   ├── main.tsx                # App entry point
│   ├── App.tsx                 # Root component
│   ├── api/
│   │   └── tasks.ts            # Backend API client
│   ├── components/
│   │   ├── KanbanBoard.tsx     # Main board with shortcuts
│   │   ├── TaskCard.tsx        # Task list item
│   │   ├── TaskDetailSheet.tsx # Peek/extended view
│   │   ├── TaskFullPage.tsx    # Full page view
│   │   ├── AIInferenceDialog.tsx  # AI extraction UI
│   │   ├── QuickAddTask.tsx    # Quick task creation
│   │   └── ui/                 # shadcn/ui components
│   ├── pages/
│   │   ├── Index.tsx           # Home page
│   │   └── NotFound.tsx        # 404 page
│   └── types/
│       └── task.ts             # TypeScript interfaces
│
├── backend/                     # Python backend
│   ├── main.py                 # FastAPI entry point
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example            # Environment template
│   ├── tasks.db                # SQLite database (gitignored)
│   ├── README.md               # Backend documentation
│   │
│   ├── config/                 # Configuration (NEW)
│   │   └── constants.py        # Centralized constants
│   │
│   ├── api/                    # API layer
│   │   ├── routes.py           # Task CRUD endpoints
│   │   ├── context_routes.py  # Cognitive Nexus API
│   │   ├── knowledge_routes.py # Knowledge Graph API
│   │   ├── knowledge_graphql_schema.py  # GraphQL (optional)
│   │   ├── schemas.py          # Pydantic models
│   │   └── utils.py            # Common utilities (NEW)
│   │
│   ├── db/                     # Database layer
│   │   ├── database.py         # Async SQLite connection
│   │   ├── models.py           # Core SQLAlchemy models
│   │   ├── knowledge_graph_models.py  # KG models
│   │   ├── default_shortcuts.py  # 45 default shortcuts
│   │   └── migrations/         # Database migrations
│   │       └── 001_add_knowledge_graph_tables.py
│   │
│   ├── agents/                 # AI agents
│   │   ├── cognitive_nexus_graph.py  # LangGraph agent system
│   │   ├── task_extractor.py  # Legacy Ollama integration
│   │   ├── pdf_processor.py   # PDF parsing
│   │   └── prompts.py          # LLM prompts
│   │
│   ├── services/               # Business logic services
│   │   ├── knowledge_graph_service.py      # KG operations
│   │   ├── knowledge_graph_embeddings.py   # Semantic similarity
│   │   ├── knowledge_graph_scheduler.py    # Decay scheduler
│   │   └── knowledge_graph_config.py       # KG configuration
│   │
│   └── tests/                  # Test suite
│       └── test_cognitive_nexus.py
│
└── scripts/                    # Utility scripts
    ├── health-check.sh         # System health check
    ├── start-backend.sh        # Backend launcher
    └── start-frontend.sh       # Frontend launcher
```

## Key Files

### Configuration
- `vite.config.ts` - Frontend server on :8080, proxies /api to :8000
- `backend/.env` - Ollama URL, model name, database config
- `components.json` - shadcn/ui component configuration
- `tailwind.config.ts` - Tailwind CSS with custom animations

### Entry Points
- `src/main.tsx` - Frontend React app
- `backend/main.py` - FastAPI server with CORS and startup logic

### Core Features
- `src/components/KanbanBoard.tsx` - 45 shortcuts, 3 view modes, conflict detection
- `backend/api/routes.py` - Task CRUD with eager loading, AI inference endpoints
- `backend/db/models.py` - Task, Comment, Attachment, ShortcutConfig models

## Documentation Structure

1. **README.md** - Start here for overview
2. **docs/OLLAMA_SETUP.md** - SSH tunnel configuration
3. **docs/SETUP.md** - Complete installation guide
4. **backend/README.md** - API reference
5. **CHANGELOG.md** - What changed recently
6. **CONTRIBUTING.md** - How to contribute

## Git Ignored

- `node_modules/`
- `backend/venv/`
- `backend/tasks.db`
- `backend/__pycache__/`
- `.env` files
- Build outputs (`dist/`)
