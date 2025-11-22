# Task Crate

**AI-powered task management with intelligent context analysis.** Transform conversations, meeting notes, and messages into actionable tasks automatically.

[![Made with React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Ollama](https://img.shields.io/badge/Ollama-Local_AI-000000)](https://ollama.com)
[![Gemini 2.0](https://img.shields.io/badge/Gemini-2.0_Flash-4285F4?logo=google)](https://ai.google.dev)

## ✨ Key Features

### 🤖 **Lotus AI Assistant** - Phase 3
Your personal AI task manager powered by Gemini 2.0 Flash and local LLMs:
- **Natural conversation** - Ask questions about your tasks naturally
- **Smart task extraction** - Automatically creates tasks from Slack, emails, PDFs
- **Personal awareness** - Knows your name, role, projects, and markets
- **Relevance filtering** - Only creates tasks relevant to you (70+ score)
- **Auto-enrichment** - Updates existing tasks when new info arrives
- **Natural comments** - No more robot emojis, just helpful context
- **Fast & affordable** - 2-3x faster, $8/mo → $0.18/mo with Gemini

### 🧠 **Cognitive Nexus** - Multi-Agent AI System
4-agent LangGraph pipeline for intelligent context processing:
- **Context Analysis** - Determines complexity and extraction strategy
- **Entity Extraction** - Identifies people, projects, teams, dates
- **Relationship Synthesis** - Infers connections between entities
- **Task Integration** - Intelligently creates, updates, or enriches tasks

### 📊 **Knowledge Graph** - Cross-Context Memory
Learns and remembers across all your conversations:
- **Entity deduplication** - "Jef", "jef adriaenssens", "Jef A" → one person
- **Relationship tracking** - Remembers who works on what
- **Dynamic org learning** - Discovers team structures automatically
- **Fuzzy matching** - Smart name and project recognition

### 📝 **Rich Text Editing**
Best-in-class formatting for tasks and notes:
- **Slash commands** (`/`) - Quick formatting menu
- **Markdown shortcuts** - `*` bullets, `-` lists, auto-links
- **Word Art** - 8 retro text effects (Ocean Wave, Rainbow, Fire, etc.)
- **Advanced formatting** - Code blocks, tables, blockquotes
- **Table editing** - Add/delete rows and columns intuitively
- **Slack-style links** - Select text + paste URL = instant link

### ⌨️ **45+ Keyboard Shortcuts**
Fully configurable with conflict detection:
- `Ctrl+E` - Toggle peek/extended view
- `Ctrl+Shift+F` - Open full page mode
- Quick add shortcuts for all columns
- Customizable per-user preferences

### 🎯 **Smart Task Management**
- **Kanban board** - Drag-and-drop between columns
- **Multiple view modes** - Peek, extended, full-page
- **Persistent storage** - SQLite with full audit trail
- **Comments & attachments** - Rich task context

### 🔒 **Privacy First**
- 100% local processing (Ollama)
- Optional cloud AI (Gemini) for speed
- No data collection or tracking
- Works offline after setup

## 🚀 Quick Start

### Prerequisites

- **Node.js 18+** and npm
- **Python 3.11+**
- **Ollama** with `qwen2.5:7b-instruct` model
- **Gemini API key** (optional, for Phase 3 features)

### Installation

```bash
# 1. Install Ollama (for local AI)
brew install ollama  # macOS
# or download from https://ollama.com/download

# Pull the model
ollama pull qwen2.5:7b-instruct

# Start Ollama (keep running)
ollama serve

# 2. Clone and install dependencies
git clone https://github.com/yourusername/task-crate.git
cd task-crate
npm install
cd backend && pip install -r requirements.txt && cd ..

# 3. Configure Gemini (optional)
cd backend
cp .env.example .env
# Edit .env and add your GOOGLE_AI_API_KEY

# 4. Run database migrations
python -m db.migrations.003_add_phase3_tables

# 5. Start the application
cd ..
./start.sh
```

### First Run

1. Open http://localhost:8080 in your browser
2. Click the **"Lotus"** button (✨ emerald sparkles icon)
3. Try this example:
   ```
   Meeting notes: Jef needs to share CRESCO data with Andy by Friday.
   Sarah from Product should review the specs before we ship.
   ```
4. Watch Lotus automatically:
   - Extract entities (Jef, Andy, Sarah, CRESCO, Friday)
   - Infer relationships (who works on what)
   - Create relevant tasks
   - Add natural comments with context

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 React Frontend (:8080)                   │
│    • Kanban Board  • Rich Text Editor  • AI Dialogs    │
└───────────────────────┬─────────────────────────────────┘
                        │ REST API
┌───────────────────────▼─────────────────────────────────┐
│              FastAPI Backend (:8000)                     │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Phase 3 Orchestrator (11 nodes)                │  │
│  │  1. load_profile    → Loads user context        │  │
│  │  2. classify        → Routes requests            │  │
│  │  3. answer_question → Gemini Q&A                │  │
│  │  4. run_phase1      → Cognitive Nexus agents    │  │
│  │  5. find_tasks      → Match existing tasks      │  │
│  │  6. check_enrichments → Find update opportunities│  │
│  │  7. enrich_proposals → Add task metadata        │  │
│  │  8. filter_relevance → Score 0-100, keep 70+   │  │
│  │  9. calculate_confidence → Auto-apply threshold │  │
│  │  10. generate_questions → Clarify if needed     │  │
│  │  11. execute_actions → Create/update tasks      │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Knowledge Graph + Services                      │  │
│  │  • Entity deduplication (fuzzy matching)         │  │
│  │  • Relationship tracking (strength scoring)      │  │
│  │  • Performance cache (LRU + Redis)               │  │
│  │  • User profile manager (5min TTL)               │  │
│  └──────────────────────────────────────────────────┘  │
└───────────────────┬──────────────────┬──────────────────┘
                    │                  │
        ┌───────────▼────────┐    ┌───▼──────────────┐
        │  SQLite (tasks.db) │    │  AI Models       │
        │  • Tasks           │    │  • Ollama (Qwen) │
        │  • Knowledge nodes │    │  • Gemini 2.0    │
        │  • Relationships   │    └──────────────────┘
        │  • User profiles   │
        └────────────────────┘
```

### Data Flow Example

```
User: "Alberto asked about pinning position 3 for pharmacies in Spain"
  │
  ├─> load_profile: Get Jef's context (Spain market, projects)
  ├─> classify: Identifies as task creation request
  ├─> run_phase1: Extract entities (Alberto, Spain, pharmacies)
  ├─> filter_relevance: Score = 85 (Spain is your market ✓)
  ├─> enrich_proposals: Add market tag, assignee
  ├─> calculate_confidence: 90% → auto-create
  └─> execute_actions: Create task + natural comment
      "Alberto (Spain market) asked about pharmacy pinning..."
```

## 🛠️ Tech Stack

### Frontend
- **React 18** + TypeScript + Vite
- **UI:** shadcn/ui, Radix UI, Tailwind CSS
- **Editor:** Tiptap (ProseMirror-based)
- **State:** TanStack Query, React hooks

### Backend
- **FastAPI** + Python 3.11+
- **Database:** SQLite + SQLAlchemy 2.0 (async)
- **AI:** Ollama SDK, Gemini SDK
- **PDF:** PyMuPDF (fitz)
- **Graph:** LangGraph for agent orchestration

### AI Models
- **Ollama + Qwen 2.5 7B** - Local processing, 100% private
- **Gemini 2.0 Flash** - Fast cloud processing, $0.18/month

## 📚 Documentation

### 🚀 Quick Start
- **[Getting Started](./docs/GETTING_STARTED.md)** ⭐ - 5-minute setup guide
- **[Setup Guide](./docs/SETUP.md)** - Complete installation
- **[Ollama Setup](./docs/OLLAMA_SETUP.md)** - Dev container configuration

### 🤖 Core Features
- **[Lotus AI Assistant](./docs/guides/LOTUS_ASSISTANT.md)** - Phase 2 & 3 features
- **[Cognitive Nexus](./docs/architecture/COGNITIVE_NEXUS.md)** - 4-agent AI system
- **[Knowledge Graph](./docs/architecture/KNOWLEDGE_GRAPH.md)** - Cross-context memory
- **[Task Management](./docs/guides/TASK_MANAGEMENT.md)** - Unified intelligence

### 💻 Development
- **[Development Guide](./docs/development/DEVELOPMENT_GUIDE.md)** - Architecture & workflow
- **[Phase 3 Guide](./docs/development/PHASE3_GUIDE.md)** - Phase 3 improvements
- **[Phase 4 Guide](./docs/development/PHASE4_GUIDE.md)** - Calendar integration & scheduling
- **[API Reference](./docs/api/API_REFERENCE.md)** - Complete endpoint docs
- **[Project Structure](./docs/PROJECT_STRUCTURE.md)** - File organization

### 📖 More
- **[Documentation Index](./docs/INDEX.md)** - Complete navigation
- **[Changelog](./CHANGELOG.md)** - Version history
- **[Contributing](./CONTRIBUTING.md)** - How to contribute
- **[API Docs (Live)](http://localhost:8000/docs)** - Swagger UI when running

## 🚦 Development

### Running Tests
```bash
# Backend tests
cd backend && pytest tests/ -v

# Specific test suites
pytest tests/test_phase3_comprehensive.py -v  # Phase 3 features
pytest tests/test_cognitive_nexus.py -v      # AI agents
```

### Health Checks
```bash
# System health
curl http://localhost:8000/api/health

# View AI reasoning
curl http://localhost:8000/api/context/{id}/reasoning

# Check Gemini usage
curl http://localhost:8000/api/assistant/usage-stats
```

### Code Style
- **Python:** PEP 8, type hints, async/await
- **TypeScript:** Strict mode, functional components
- **Commits:** Conventional commits (`feat:`, `fix:`, `docs:`)

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for:
- Development setup
- Code style guidelines
- Testing requirements
- Pull request process

### Quick Contribution Guide
1. Fork and create feature branch: `git checkout -b feature/amazing-feature`
2. Make changes following code style guidelines
3. Add tests and ensure all pass
4. Commit: `git commit -m "feat: add amazing feature"`
5. Push and create Pull Request

## 📊 Performance

### Metrics (Phase 3)
- **Latency:** 20-30s → **8-12s** (2-3x faster)
- **Cost:** $8/mo → **$0.18/mo** (45x reduction)
- **Accuracy:** 95% task extraction, 90% relevance filtering
- **Cache hit rate:** >60% after warm-up

### System Requirements
- **RAM:** 8GB minimum (16GB recommended)
- **Disk:** 10GB free space
- **CPU:** Modern multi-core processor
- **Network:** Internet for Gemini (optional)

## 🔒 Privacy & Security

- ✅ **100% local processing** with Ollama (Qwen 2.5)
- ✅ **Optional cloud AI** with Gemini (user choice)
- ✅ **No data collection** or tracking
- ✅ **SQLite encryption** support ready
- ✅ **Works offline** after initial setup
- ⚠️ **Development mode** - Not production-hardened

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details

## 🙏 Acknowledgments

- **Ollama** - Local LLM infrastructure
- **LangGraph** - Agent orchestration framework
- **shadcn/ui** - Beautiful component library
- **FastAPI** - Modern Python web framework

---

**Built with ❤️ for better task management**
