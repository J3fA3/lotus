# 🏗️ Architecture & Setup Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Your MacBook Pro                       │
│                                                                 │
│  ┌────────────────────┐         ┌─────────────────────────┐   │
│  │   Ollama Server    │         │      Web Browser        │   │
│  │  localhost:11434   │         │   localhost:5173        │   │
│  │                    │         │                         │   │
│  │  🤖 Qwen 2.5 7B    │         │  🎨 Your Kanban App     │   │
│  │     Instruct       │         │                         │   │
│  └────────────────────┘         └─────────────────────────┘   │
│           ▲                                  │                 │
│           │                                  │                 │
│           │                                  ▼                 │
│  ┌────────┴──────────────────────────────────────────────┐    │
│  │           Docker Dev Container (VS Code)              │    │
│  │                                                        │    │
│  │  ┌──────────────────┐      ┌──────────────────────┐  │    │
│  │  │   Backend API    │      │   Frontend (Vite)    │  │    │
│  │  │ localhost:8000   │◄─────┤  localhost:5173      │  │    │
│  │  │                  │      │                      │  │    │
│  │  │  FastAPI Server  │      │  React + TypeScript  │  │    │
│  │  │  SQLite Database │      │  Tailwind + shadcn   │  │    │
│  │  └──────────────────┘      └──────────────────────┘  │    │
│  │           ▲                                            │    │
│  │           │ HTTP via host.docker.internal:11434       │    │
│  │           └────────────────────────────────────────────┘    │
│  │                                                              │
│  └──────────────────────────────────────────────────────────────┘
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### AI Task Inference Flow

```
1. User pastes text in browser
   └─► POST /api/infer-tasks

2. Frontend → Backend
   └─► { text: "Meeting notes...", assignee: "You" }

3. Backend → Ollama (via host.docker.internal)
   └─► { model: "qwen2.5:7b-instruct", prompt: "..." }

4. Ollama (AI processing 10-30s)
   └─► { tasks: [...] }

5. Backend → SQLite Database
   └─► INSERT tasks

6. Backend → Frontend
   └─► { tasks: [...] }

7. Frontend renders tasks on Kanban board
   └─► ✨ Tasks appear!
```

### Port Configuration

| Service    | Port  | URL                                        | Accessible From    |
|------------|-------|--------------------------------------------|--------------------|
| Ollama     | 11434 | http://localhost:11434                     | Mac only           |
| Ollama     | 11434 | http://host.docker.internal:11434          | Dev container      |
| Backend    | 8000  | http://localhost:8000                      | Mac & Dev container|
| Frontend   | 5173  | http://localhost:5173                      | Mac & Dev container|

## Network Configuration

### Mac to Dev Container

Your Mac can access services in the dev container via `localhost`:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

### Dev Container to Mac

The dev container accesses your Mac's Ollama via `host.docker.internal`:
- Ollama: `http://host.docker.internal:11434`

This is configured in `backend/.env`:
```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

## File Structure

```
task-crate/
├── 📄 README.md                    # Main documentation
├── 📄 GETTING_STARTED.md           # ⭐ Quick setup guide
├── 📄 QUICKSTART.md                # Streamlined instructions
├── 📄 SETUP.md                     # Complete guide
├── 📄 ARCHITECTURE.md              # This file
│
├── 🛠️ start-backend.sh             # Backend startup script
├── 🛠️ start-frontend.sh            # Frontend startup script
├── 🛠️ health-check.sh              # System health check
│
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── requirements.txt           # Python dependencies
│   ├── .env                       # Environment config
│   │
│   ├── agents/                    # AI task extraction
│   │   ├── task_extractor.py     # Core AI logic
│   │   ├── pdf_processor.py      # PDF handling
│   │   └── prompts.py            # AI prompts
│   │
│   ├── api/                       # FastAPI routes
│   │   ├── routes.py             # API endpoints
│   │   └── schemas.py            # Pydantic models
│   │
│   └── db/                        # Database
│       ├── database.py           # SQLite setup
│       └── models.py             # SQLAlchemy models
│
└── src/
    ├── main.tsx                   # React entry point
    ├── App.tsx                    # Main app component
    │
    ├── components/
    │   ├── KanbanBoard.tsx       # Kanban UI
    │   ├── TaskCard.tsx          # Task display
    │   ├── AIInferenceDialog.tsx # AI input dialog
    │   └── ui/                   # shadcn components
    │
    ├── api/
    │   └── tasks.ts              # API client
    │
    └── types/
        └── task.ts               # TypeScript types
```

## Technology Stack

### Frontend
- **Framework:** React 18 with TypeScript
- **Build Tool:** Vite (fast dev server)
- **UI Library:** shadcn/ui (Radix UI + Tailwind)
- **Drag & Drop:** @hello-pangea/dnd
- **State Management:** TanStack Query (React Query)
- **Routing:** React Router v6
- **Styling:** Tailwind CSS

### Backend
- **Framework:** FastAPI (Python 3.12+)
- **Database:** SQLite with SQLAlchemy ORM
- **Async:** async/await with aiosqlite
- **AI Integration:** Ollama Python SDK
- **PDF Processing:** PyMuPDF (fitz)
- **Validation:** Pydantic v2

### AI/LLM
- **Server:** Ollama (local LLM server)
- **Model:** Qwen 2.5 7B Instruct
  - Parameters: ~7 billion
  - Size: ~4.7GB
  - Speed: 10-30s per inference
  - RAM: ~6GB during inference
- **Alternative Models:**
  - Qwen 2.5 3B (faster, less RAM)
  - Llama 3.1 8B
  - Mistral 7B

## Development Workflow

### 1. Initial Setup (One Time)

```bash
# On Mac
ollama serve  # Terminal 1

# In dev container
./health-check.sh  # Verify environment
./start-backend.sh  # Terminal 1
./start-frontend.sh  # Terminal 2
```

### 2. Daily Development

```bash
# On Mac (once per day)
ollama serve

# In dev container (Terminal 1)
cd backend
source venv/bin/activate
python main.py

# In dev container (Terminal 2)
npm run dev
```

### 3. Making Changes

**Frontend changes:**
- Edit files in `src/`
- Vite hot-reloads automatically
- Check browser console for errors

**Backend changes:**
- Edit files in `backend/`
- FastAPI auto-reloads with `reload=True`
- Check terminal logs for errors

**AI prompt changes:**
- Edit `backend/agents/prompts.py`
- Restart backend to apply changes

### 4. Testing AI

1. Make change to prompt or logic
2. Restart backend (`Ctrl+C` then `python main.py`)
3. In browser: Click "AI Infer Tasks"
4. Test with sample text
5. Check results and iterate

## Database Schema

### Tasks Table

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,  -- 'todo', 'inprogress', 'done'
    assignee TEXT,
    priority TEXT,         -- 'low', 'medium', 'high'
    due_date TEXT,         -- ISO format date string
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Example Task JSON

```json
{
  "id": 1,
  "title": "Update API documentation",
  "description": "Before Friday release",
  "status": "todo",
  "assignee": "john",
  "priority": "high",
  "due_date": "2025-11-15",
  "created_at": "2025-11-13T10:30:00Z",
  "updated_at": "2025-11-13T10:30:00Z"
}
```

## API Endpoints

### Task CRUD

```http
GET    /api/tasks           # List all tasks
POST   /api/tasks           # Create task
GET    /api/tasks/{id}      # Get task by ID
PUT    /api/tasks/{id}      # Update task
DELETE /api/tasks/{id}      # Delete task
```

### AI Inference

```http
POST   /api/infer-tasks          # Infer from text
POST   /api/infer-tasks-pdf      # Infer from PDF
GET    /api/health               # Health check
```

### Health Check Response

```json
{
  "status": "healthy",
  "ollama_connected": true,
  "ollama_model": "qwen2.5:7b-instruct",
  "database_ok": true
}
```

## Security Considerations

### Current Setup (Local Development)

✅ **Pros:**
- 100% local - no data leaves your machine
- No API keys or credentials needed
- No cloud costs
- Works offline (after initial setup)

⚠️ **Limitations:**
- CORS allows all origins in dev mode
- No authentication/authorization
- SQLite database has no access control
- Suitable for personal use only

### Production Considerations (If Deploying)

If you deploy this, consider:
- ❗ Add authentication (JWT tokens)
- ❗ Implement user accounts
- ❗ Switch to PostgreSQL or MySQL
- ❗ Add rate limiting
- ❗ Secure CORS configuration
- ❗ HTTPS/TLS encryption
- ❗ Input sanitization
- ❗ API key for Ollama access

## Performance Tuning

### Model Selection

| Model           | RAM  | Speed      | Accuracy | Use Case              |
|-----------------|------|------------|----------|-----------------------|
| Qwen 2.5 3B     | ~3GB | 5-15s      | ⭐⭐⭐⭐ | Fast prototyping      |
| **Qwen 2.5 7B** | ~6GB | **10-30s** | ⭐⭐⭐⭐⭐ | **Recommended**       |
| Llama 3.1 8B    | ~8GB | 15-40s     | ⭐⭐⭐⭐⭐ | High accuracy needed  |

### Optimization Tips

1. **Reduce inference time:**
   - Use smaller model (3B instead of 7B)
   - Close background apps
   - Ensure sufficient RAM

2. **Improve accuracy:**
   - Use larger model (7B or 8B)
   - Improve prompts in `prompts.py`
   - Provide more context in input

3. **Scale for multiple users:**
   - Use FastAPI worker processes
   - Queue inference requests
   - Cache common results
   - Consider GPU acceleration

## Troubleshooting Guide

### Connection Issues

**Problem:** Backend can't reach Ollama

**Diagnosis:**
```bash
# In dev container
curl http://host.docker.internal:11434/api/tags
```

**Solutions:**
1. Ensure Ollama is running on Mac
2. Check firewall settings
3. Verify Docker networking

### Performance Issues

**Problem:** AI inference is slow

**Diagnosis:**
```bash
# On Mac
top  # Check CPU/RAM usage
ollama list  # Check loaded models
```

**Solutions:**
1. Use smaller model
2. Close heavy applications
3. Add more RAM if possible

### Database Issues

**Problem:** Tasks not persisting

**Diagnosis:**
```bash
# In dev container
ls -la backend/tasks.db  # Check if exists
```

**Solutions:**
1. Check file permissions
2. Delete and recreate: `rm backend/tasks.db`
3. Restart backend to auto-create

## Contributing

### Adding New Features

1. **New API endpoint:**
   - Add route in `backend/api/routes.py`
   - Add schema in `backend/api/schemas.py`
   - Update API docs

2. **New UI component:**
   - Create in `src/components/`
   - Use shadcn/ui patterns
   - Add to appropriate page

3. **Improve AI:**
   - Edit prompts in `backend/agents/prompts.py`
   - Test with various inputs
   - Document changes

### Code Style

- **Frontend:** ESLint + TypeScript strict mode
- **Backend:** PEP 8 Python style
- **Commits:** Conventional commits format

---

## Additional Resources

- **Ollama Documentation:** https://ollama.com/docs
- **FastAPI Documentation:** https://fastapi.tiangolo.com
- **React Documentation:** https://react.dev
- **shadcn/ui:** https://ui.shadcn.com
- **Qwen Model Card:** https://ollama.com/library/qwen2.5

---

**Last Updated:** November 2025
