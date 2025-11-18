# Task Crate

AI-powered task management with intelligent context analysis. Built with React, FastAPI, and local LLM processing.

## Features

- **Rich Text Editing** - Best-in-class formatting for tasks, notes, and comments
  - **Slash Commands** (`/`) - Search and apply formatting with auto-scroll menu
  - **Markdown Shortcuts** - `*` for bullets, `-` for lists, automatic link detection
  - **Word Art** - 8 retro-styled text effects (Ocean Wave, Rainbow, Fire, etc.) - works in titles and content
  - **Headings** - H1, H2, H3 with automatic styling
  - **Advanced Formatting** - Code blocks with syntax highlighting, tables, blockquotes
  - **Table Editing** - Add/delete rows and columns with intuitive menu that appears when editing tables
  - **Slack-Style Link Paste** - Select text + paste URL = instant link
  - **Keyboard Shortcuts** - Cmd+> for blockquotes, and more
  - **3 Variants** - Title (Word Art only), Minimal (basic formatting), Full (all features with tables)
- **Lotus AI Assistant** - Unified interface for all task management (NEW Phase 2!)
  - Answer questions about your tasks ("What's my highest priority?")
  - Intelligent request classification (questions vs tasks vs context)
  - Confidence-based autonomy (auto-create, ask approval, or clarify)
  - Fast PDF processing for meeting transcripts
  - AI agent comments with reasoning on every task
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

1. Click **"Lotus"** button (emerald sparkles icon)
2. Paste sample text or upload a PDF:
   ```
   Meeting notes: Jef needs to share CRESCO data with Andy by Friday.
   Sarah from Product should review the specs before we ship.
   ```
3. Watch Lotus intelligently:
   - Answer questions about your tasks
   - Extract entities and create tasks
   - Process PDFs and meeting transcripts
   - Provide confidence-based recommendations

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

## 🚀 Phase 2: Lotus AI Assistant

**Lotus** is the unified AI-powered task management interface that combines all cognitive capabilities into one seamless experience.

### Key Features

**🧠 Intelligent Request Classification**
- **Questions** → Direct answers using knowledge graph
- **Slack Messages** → Automatic task extraction (even with questions)
- **Transcripts** → Meeting note processing
- **PDFs** → Fast document analysis
- **Manual Input** → Full orchestrator pipeline

**✨ Confidence-Based Autonomy**
- **>80% confidence** → Auto-creates tasks (high confidence)
- **50-80% confidence** → Asks for approval (medium confidence)
- **<50% confidence** → Requests clarification (low confidence)

**💬 AI Agent Comments**
- Every task includes detailed agent reasoning
- Confidence breakdown and extracted entities
- Source context links and decision rationale
- Priority/due date highlights

**⚡ Performance Optimizations**
- **Fast PDF endpoint** → Bypasses orchestrator for speed (2-3s vs 10s+)
- **Knowledge graph caching** → LRU cache with 5-minute TTL
- **Entity/relationship lookups** → Cached for repeated queries

### Usage

```typescript
// Manual Question
"What is my highest priority task?"
→ Lotus answers directly from knowledge graph

// Slack Message (with question)
"Hi Jef, is the algorithm team using the sheet? We need to exclude chain X."
→ Lotus creates task (doesn't treat as question)

// PDF Upload
Upload meeting transcript PDF
→ Lotus processes via fast endpoint, creates tasks

// Manual Task
"Andy needs dashboard by Friday"
→ Lotus runs full pipeline with confidence scoring
```

### Source Type Selector

Lotus provides toggle buttons to indicate input type:
- **Manual** → LLM-based classification (question vs task)
- **Slack** → Always task creation
- **Transcript** → Always task creation

This prevents misclassification of Slack messages containing questions.

### Architecture Updates

```
┌─────────────────────────────────────────────────────┐
│              Lotus Dialog (Frontend)                 │
│  • Source type selector (Manual/Slack/Transcript)   │
│  • PDF upload with fast processing                  │
│  • Chat interface with message history              │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│           Phase 2 Orchestrator (Backend)             │
│                                                      │
│  1. classify_request() → Route by source type       │
│     ├─ question → answer_question()                 │
│     ├─ slack/transcript → Phase 1 pipeline          │
│     └─ manual → LLM classification                  │
│                                                      │
│  2. Phase 1 Pipeline (for tasks)                    │
│     ├─ run_phase1_agents()                          │
│     ├─ find_related_tasks() [CACHED]                │
│     ├─ enrich_task_proposals()                      │
│     ├─ calculate_confidence()                       │
│     └─ generate_clarifying_questions()              │
│                                                      │
│  3. execute_actions()                               │
│     ├─ Auto-create (>80%)                           │
│     ├─ Propose for approval (50-80%)                │
│     └─ Request clarification (<50%)                 │
└─────────────────────────────────────────────────────┘
```

### Fast PDF Processing

Dedicated endpoint for speed-critical PDF uploads:

```python
POST /api/assistant/process-pdf-fast
→ AdvancedPDFProcessor → Phase 1 agents → Auto-create tasks
   (Skips: classification, confidence, matching, field extraction)
   Result: 2-3 seconds vs 10+ seconds
```

### Testing

```bash
# Run Phase 2 E2E tests
cd backend && pytest tests/test_phase2_assistant_e2e.py -v

# Test scenarios covered:
# 1. Manual questions → Question answering
# 2. Slack messages → Task creation
# 3. Transcripts → Task creation
# 4. PDF uploads → Fast processing
# 5. Manual task creation → Full pipeline
```

## 🛠️ Tech Stack

**Frontend:**
- React 18 + TypeScript
- Vite (build tool)
- shadcn/ui + Radix UI (components)
- Tailwind CSS (styling)
- React Router (navigation)
- Tiptap (rich text editor with ProseMirror)
- Lowlight (syntax highlighting for code blocks)

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
