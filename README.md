# 🚀 Task Crate - AI-Powered Task Management

A modern task management application featuring a Notion-style Kanban board with local AI-powered task extraction, keyboard shortcuts, and multiple view modes.

## ✨ Key Features

### Core Task Management
- 🎯 **Kanban Board** - Drag-and-drop interface with todo/doing/done columns
- 👁️ **Multiple View Modes** - Peek (side sheet), Extended, and Full Page views
- 💬 **Notion-Style Comments** - Chat interface with Enter to send
- 📎 **Attachments & Notes** - Full task metadata with persistence
- ⌨️ **45 Keyboard Shortcuts** - Configurable shortcuts with conflict detection

### AI-Powered Features
- 🤖 **AI Task Extraction** - Extract tasks from text or PDFs using local LLM (Ollama + Qwen 2.5)
- 🧠 **Cognitive Nexus** - LangGraph-based agentic system for context-aware task management
  - **Context Analysis Agent** - Analyzes complexity and chooses extraction strategy
  - **Entity Extraction Agent** - Extracts entities with self-evaluation and retry loops
  - **Relationship Synthesis Agent** - Infers relationships between entities
  - **Task Integration Agent** - Intelligently creates, updates, or enriches tasks
- 🔗 **Knowledge Graph** - Cross-context knowledge persistence with fuzzy entity matching
- 📊 **Quality Metrics** - Transparent reasoning traces and quality scores

### Infrastructure
- 💾 **SQLite Database** - All data persists across sessions
- 🔒 **100% Local & Free** - No API keys, runs entirely on your machine

## 🚀 Quick Start

### Prerequisites

1. **Install Ollama on your host machine** (not in dev container):
   ```bash
   # macOS/Linux
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Pull the model
   ollama pull qwen2.5:7b-instruct
   ```

2. **Set up SSH tunnel** (for dev container access):
   ```bash
   # On host machine, create ~/.ssh/config entry:
   Host devcontainer
       HostName localhost
       Port 2222
       User vscode
       RemoteForward 11434 127.0.0.1:11434
   
   # Start Ollama service
   ollama serve
   ```

### Running the Application

```bash
# Terminal 1: Start backend
cd /workspaces/task-crate/backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start frontend
cd /workspaces/task-crate
npm run dev

# Open http://localhost:8080 in your browser
```

### Option 2: Running Locally (Without Dev Container)

```bash
# 1. Install Ollama (on your Mac)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b-instruct
ollama serve  # Keep this running

# 2. Start backend (new terminal)
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py

# 3. Start frontend (new terminal)
npm install
npm run dev

# Open http://localhost:5173
```

## 🎬 Demo Flow

1. Open the app → See your Kanban board
2. Click **"AI Infer Tasks"** button
3. Paste this example:
   ```
   Meeting notes:
   - @john needs to update API docs before Friday
   - @sarah will review the auth PR tomorrow
   - Schedule Q4 roadmap meeting next week
   ```
4. Click **"Infer Tasks"**
5. Wait 10-30 seconds
6. 3 tasks automatically added to your board! ✨

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

## 📚 Documentation

- **[docs/SETUP.md](./docs/SETUP.md)** - Complete setup guide
- **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)** - System design and data models
- **[backend/README.md](./backend/README.md)** - Backend API documentation
- **API Docs** - http://localhost:8000/docs (interactive Swagger UI)

### Recent Changes
- **Data Persistence** - Fixed comments, attachments, and notes persistence
- **Keyboard Shortcuts** - 45 configurable shortcuts with conflict detection
- **View Modes** - Added peek, extended, and full-page task views

## 🔧 Development

```bash
# Install frontend dependencies
npm install

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Run tests (when available)
pytest backend/tests

# Check backend health
curl http://localhost:8000/api/health
```

## 📦 Database Schema

```sql
-- Core tables
tasks              # Main task data with notes
comments           # Task comments (1-to-many)
attachments        # Task attachments (1-to-many)
inference_history  # AI inference logs
shortcut_config    # User keyboard shortcuts
```

## 🤝 Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Test thoroughly
4. Commit: `git commit -m "feat: description"`
5. Push and create PR

## 📝 License

MIT License - See LICENSE file for details
