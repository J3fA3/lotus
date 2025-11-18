# Task Crate

AI-powered task management with intelligent context analysis. Built with React, FastAPI, and local LLM processing.

## Features

- **Kanban Board** - Drag-and-drop task management with multiple view modes
- **Cognitive Nexus AI** - 4-agent LangGraph system for intelligent context processing
  - Extracts people, projects, teams, and deadlines from conversations
  - Infers relationships and builds cross-context knowledge graph
  - Automatically creates, updates, or enriches tasks based on context
- **Knowledge Graph** - Remembers entities and relationships across all contexts
- **45+ Keyboard Shortcuts** - Configurable shortcuts with conflict detection
- **100% Local & Private** - All processing happens on your machine via Ollama

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- [Ollama](https://ollama.com/download) with `qwen2.5:7b-instruct` model

```bash
# Install Ollama
brew install ollama  # macOS
# or download from https://ollama.com/download

# Pull the model
ollama pull qwen2.5:7b-instruct

# Start Ollama
ollama serve
```

### Installation

```bash
# Clone and install dependencies
git clone <repository-url>
cd task-crate
npm install
cd backend && pip install -r requirements.txt && cd ..

# Start the application
./start.sh

# Open http://localhost:8080
```

### Try It Out

1. Click **"Context Analysis"** button (brain icon)
2. Paste sample text:
   ```
   Meeting notes: Jef needs to share CRESCO data with Andy by Friday.
   Sarah from Product should review the specs before we ship.
   ```
3. Click **"Analyze with AI Agents"**
4. Watch agents extract entities, infer relationships, and create tasks!

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│              (TypeScript + Vite) :5173                  │
│  • Kanban Board  • Task Views  • AI Dialogs            │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP REST API
                        ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                       │
│                  (Python 3.12) :8000                    │
│                                                          │
│  ┌────────────────┐  ┌───────────────────────────┐     │
│  │  Task CRUD API │  │  Cognitive Nexus API      │     │
│  │  • Tasks       │  │  • Context Ingestion      │     │
│  │  • Comments    │  │  • Entity Extraction      │     │
│  │  • Shortcuts   │  │  • Relationship Inference │     │
│  └────────────────┘  │  • Task Integration       │     │
│                      └───────────┬───────────────┘     │
│                                  │                       │
│  ┌──────────────────────────────┴───────────────────┐  │
│  │         LangGraph Agentic System                 │  │
│  │  ┌─────────────────────────────────────────┐     │  │
│  │  │ 1. Context Analysis Agent               │     │  │
│  │  │ 2. Entity Extraction Agent (w/ retry)   │     │  │
│  │  │ 3. Relationship Synthesis Agent         │     │  │
│  │  │ 4. Task Integration Agent               │     │  │
│  │  └─────────────────────────────────────────┘     │  │
│  └──────────────────────────────────────────────────┘  │
│                                  │                       │
│  ┌──────────────────────────────┴───────────────────┐  │
│  │         Knowledge Graph Service                  │  │
│  │  • Fuzzy Entity Deduplication                    │  │
│  │  • Relationship Aggregation                      │  │
│  │  • Team Structure Learning                       │  │
│  │  • Semantic Similarity (Optional)                │  │
│  └──────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┴──────────────┐
        │                               │
        ▼                               ▼
┌──────────────┐              ┌──────────────────┐
│    SQLite    │              │  Ollama :11434   │
│  (tasks.db)  │              │  Qwen 2.5 7B     │
│              │              │  (Local LLM)     │
│  • Tasks     │              └──────────────────┘
│  • Context   │
│  • Entities  │
│  • Knowledge │
│  • Relations │
└──────────────┘
```

## 🛠️ Tech Stack

**Frontend:**
- React 18 + TypeScript
- Vite (build tool)
- shadcn/ui + Radix UI (components)
- Tailwind CSS (styling)
- React Router (navigation)

**Backend:**
- FastAPI (Python web framework)
- SQLAlchemy 2.0 (async ORM)
- SQLite + aiosqlite (database)
- Ollama (LLM interface)
- PyMuPDF (PDF processing)

**AI/ML:**
- Ollama 0.3.3
- Qwen 2.5 7B Instruct (local LLM)

## Documentation

- **[DEVELOPMENT.md](./DEVELOPMENT.md)** - Setup, architecture, and development guide
- **[COGNITIVE_NEXUS.md](./COGNITIVE_NEXUS.md)** - AI system and knowledge graph details
- **[CHANGELOG.md](./CHANGELOG.md)** - Version history and migrations
- **[docs/](./docs/)** - Additional guides and setup instructions
- **API Docs** - http://localhost:8000/docs (interactive Swagger UI)

## Development

See [DEVELOPMENT.md](./DEVELOPMENT.md) for:
- Project structure
- Code style guidelines  
- Testing strategy
- Deployment checklist

```bash
# Run backend tests
cd backend && pytest tests/ -v

# Check API health
curl http://localhost:8000/api/health

# View reasoning traces
curl http://localhost:8000/api/context/{id}/reasoning
```

## Contributing

1. Create feature branch: `git checkout -b feature/your-feature`
2. Follow code style in [DEVELOPMENT.md](./DEVELOPMENT.md)
3. Add tests for new features
4. Commit with conventional commits: `feat:`, `fix:`, `docs:`
5. Create pull request

## License

MIT License
