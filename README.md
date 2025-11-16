# 🚀 Task Crate - AI-Powered Task Management

A modern task management application featuring a Notion-style Kanban board with local AI-powered task extraction, keyboard shortcuts, and multiple view modes.

## ✨ Key Features

- 🎯 **Kanban Board** - Drag-and-drop interface with todo/doing/done columns
- 🤖 **AI Task Extraction** - Extract tasks from text or PDFs using local LLM (Ollama + Qwen 2.5)
- ⌨️ **45 Keyboard Shortcuts** - Configurable shortcuts with conflict detection
- 👁️ **Multiple View Modes** - Peek (side sheet), Extended, and Full Page views
- 💬 **Notion-Style Comments** - Chat interface with Enter to send
- 📎 **Attachments & Notes** - Full task metadata with persistence
- 💾 **SQLite Database** - All data persists across sessions
- 🔒 **100% Local & Free** - No API keys, runs entirely on your machine

## 🚀 Quick Start

### Prerequisites

1. **Install Ollama on your local machine** (not in codespace/dev container):
   ```bash
   # macOS
   brew install ollama
   
   # Or download from https://ollama.com/download
   
   # Linux
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. **Download the AI model**:
   ```bash
   ollama pull qwen2.5:7b-instruct
   ```

3. **Start Ollama server** (keep this running):
   ```bash
   ollama serve
   ```

### Running in GitHub Codespaces

1. **Forward Ollama port** from your local machine:
   ```bash
   # On your LOCAL machine terminal (not in codespace)
   gh codespace ssh -- -R 11434:localhost:11434
   
   # This creates an SSH tunnel that forwards your local Ollama 
   # (port 11434) to the codespace
   ```

2. **Start the application** (in codespace terminal):
   ```bash
   ./start.sh
   ```

3. **Access the app**:
   - Frontend: http://localhost:8080
   - Backend: http://localhost:8000
   - API Docs: http://localhost:8000/docs

4. **Stop the application**:
   ```bash
   ./stop.sh
   ```

### Running Locally (Without Dev Container)

```bash
# 1. Install dependencies
npm install
cd backend && pip install -r requirements.txt && cd ..

# 2. Start Ollama (in separate terminal)
ollama serve

# 3. Start the application
./start.sh

# 4. Open http://localhost:8080
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
┌─────────────────┐
│  React Frontend │ :8080
│  (TypeScript)   │
└────────┬────────┘
         │ HTTP + Proxy
         ▼
┌─────────────────┐
│  FastAPI Server │ :8000
│  (Python 3.12)  │
└────┬───────┬────┘
     │       │
     │       └──────► Ollama :11434 (SSH tunnel)
     │                Qwen 2.5 7B
     ▼
┌─────────────────┐
│ SQLite Database │
│  (tasks.db)     │
└─────────────────┘
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
