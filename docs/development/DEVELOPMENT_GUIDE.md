# Development Guide

## 🚀 Quick Start

### Prerequisites
- **Node.js 18+** and **npm** or **bun**
- **Python 3.11+**
- **Ollama** with `qwen2.5:7b-instruct` model
- **SQLite 3**

### Setup

```bash
# 1. Clone and install dependencies
git clone <repository-url>
cd task-crate
npm install
cd backend && pip install -r requirements.txt && cd ..

# 2. Start Ollama
ollama serve
ollama pull qwen2.5:7b-instruct

# 3. Run the application
./start.sh
```

Visit http://localhost:8080 for the frontend and http://localhost:8000/docs for API documentation.

## 📁 Project Structure

```
task-crate/
├── src/                      # React frontend (TypeScript)
│   ├── components/           # UI components
│   ├── api/                  # API client code
│   ├── pages/                # Route pages
│   └── types/                # TypeScript definitions
│
├── backend/                  # Python FastAPI backend
│   ├── api/                  # API routes and schemas
│   ├── agents/               # AI agents (LangGraph)
│   ├── services/             # Business logic
│   ├── db/                   # Database models and migrations
│   └── config/               # Configuration constants
│
├── docs/                     # Documentation
└── scripts/                  # Utility scripts
```

## 🏗️ Architecture

### Frontend Stack
- **React 18** with TypeScript
- **Vite** for build tooling
- **shadcn/ui** + Radix UI for components
- **Tailwind CSS** for styling
- **React Router** for navigation

### Backend Stack
- **FastAPI** for REST API
- **SQLAlchemy 2.0** with async support
- **SQLite** with aiosqlite
- **LangGraph** for agentic AI workflows
- **Ollama** for local LLM inference

### AI System - Cognitive Nexus

4-agent LangGraph pipeline:

1. **Context Analysis Agent** - Analyzes complexity and selects extraction strategy
2. **Entity Extraction Agent** - Extracts people, projects, teams, dates with self-evaluation and retry loops
3. **Relationship Synthesis Agent** - Infers relationships between entities
4. **Task Integration Agent** - Creates, updates, or enriches tasks intelligently

## 🛠️ Development Workflow

### Running Locally

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
python main.py

# Terminal 2: Frontend
npm run dev

# Terminal 3: Ollama (if not running as service)
ollama serve
```

### Code Style

**Python:**
- Follow PEP 8
- Use type hints
- Add docstrings to public functions
- Use async/await for database operations

**TypeScript:**
- Use functional components with hooks
- Prefer `const` over `let`
- Use TypeScript strict mode
- Define interfaces for all data structures

### Database Migrations

```bash
# Create a new migration
cd backend/db/migrations
cp template.py 00X_description.py

# Run migrations
python backend/db/migrations/00X_description.py migrate

# Check status
python backend/db/migrations/00X_description.py status

# Rollback if needed
python backend/db/migrations/00X_description.py rollback
```

### Testing

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests (when available)
npm run test
```

## 🔧 Configuration

### Environment Variables

Create `backend/.env`:

```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

# Database
DATABASE_URL=sqlite+aiosqlite:///./tasks.db

# API Configuration
API_TITLE="Task Crate API"
API_VERSION="1.0.0"
```

### Constants

All application constants are centralized in `backend/config/constants.py`:

```python
# Entity types
ENTITY_TYPE_PERSON = "PERSON"
ENTITY_TYPE_PROJECT = "PROJECT"

# Quality thresholds
QUALITY_THRESHOLD_HIGH = 0.7
QUALITY_THRESHOLD_MEDIUM = 0.6

# Task statuses
TASK_STATUS_TODO = "todo"
TASK_STATUS_DOING = "doing"
TASK_STATUS_DONE = "done"
```

## 📝 Best Practices

### Backend

1. **Use Constants**: Import from `config.constants` instead of hardcoding values
   ```python
   from config.constants import QUALITY_THRESHOLD_HIGH
   if score >= QUALITY_THRESHOLD_HIGH:
       process()
   ```

2. **Async Operations**: Use async/await for all database operations
   ```python
   async def get_task(task_id: int):
       result = await db.execute(select(Task).where(Task.id == task_id))
       return result.scalar_one_or_none()
   ```

3. **Eager Loading**: Use `selectinload` to prevent N+1 queries
   ```python
   result = await db.execute(
       select(Task)
       .options(selectinload(Task.comments))
       .where(Task.id == task_id)
   )
   ```

4. **Error Handling**: Use FastAPI's HTTPException
   ```python
   if not task:
       raise HTTPException(status_code=404, detail="Task not found")
   ```

### Frontend

1. **API Calls**: Use the centralized API client
   ```typescript
   import { fetchTasks } from '@/api/tasks';
   const tasks = await fetchTasks();
   ```

2. **State Management**: Use React hooks
   ```typescript
   const [tasks, setTasks] = useState<Task[]>([]);
   ```

3. **Error Handling**: Use toast notifications
   ```typescript
   try {
       await createTask(taskData);
       toast.success("Task created");
   } catch (error) {
       toast.error("Failed to create task");
   }
   ```

4. **Keyboard Shortcuts**: Register through ShortcutContext
   ```typescript
   useRegisterShortcut('quick_add', () => {
       // Handler
   });
   ```

## 🧪 Testing Strategy

### Unit Tests
- Test individual functions and components
- Mock external dependencies (database, LLM)
- Use pytest for backend, Jest/Vitest for frontend

### Integration Tests
- Test API endpoints end-to-end
- Use test database
- Verify database state changes

### Agent Tests
- Test LangGraph agent decisions
- Verify reasoning traces
- Check quality metrics

Example:
```python
# backend/tests/test_cognitive_nexus.py
async def test_entity_extraction():
    text = "Jef works on CRESCO"
    result = await process_context(text)
    
    assert len(result["extracted_entities"]) >= 2
    assert any(e["name"] == "Jef" for e in result["extracted_entities"])
    assert any(e["name"] == "CRESCO" for e in result["extracted_entities"])
```

## 🐛 Debugging

### Backend Issues

```bash
# Check backend health
curl http://localhost:8000/api/health

# View logs
tail -f backend.log

# Python debugger
import pdb; pdb.set_trace()
```

### Frontend Issues

```bash
# Check React DevTools
# Check browser console
# Use React Developer Tools extension

# TypeScript errors
npm run type-check
```

### Database Issues

```bash
# Inspect database
sqlite3 backend/tasks.db

# View tables
.tables

# Query data
SELECT * FROM tasks;

# Reset database (careful!)
rm backend/tasks.db
python backend/main.py  # Recreates tables
```

## 📊 Performance Optimization

### Backend
- Use database indexes for frequently queried columns
- Implement pagination for large result sets
- Cache frequently accessed data
- Use connection pooling

### Frontend
- Lazy load components
- Implement virtual scrolling for long lists
- Debounce search inputs
- Use React.memo for expensive components

### AI Inference
- First run is slow (model loading: 30-60s)
- Subsequent runs are faster (10-30s)
- Consider implementing request queuing
- Cache common extractions

## 🚢 Deployment

### Production Checklist

- [ ] Set `DEBUG=False` in backend
- [ ] Use production-grade database (PostgreSQL)
- [ ] Set up proper logging (structured logging)
- [ ] Configure CORS properly
- [ ] Set up monitoring (health checks)
- [ ] Use environment variables for secrets
- [ ] Set up CI/CD pipeline
- [ ] Configure backup strategy
- [ ] Set up SSL/TLS

### Docker Deployment (Future)

```dockerfile
# Dockerfile example for backend
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🤝 Contributing

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: add feature description"

# Push and create PR
git push origin feature/your-feature-name
```

### Commit Message Format

Use conventional commits:

```
feat: add new feature
fix: fix bug
docs: update documentation
refactor: refactor code
test: add tests
chore: update dependencies
```

### Pull Request Guidelines

1. Write clear description of changes
2. Include screenshots for UI changes
3. Ensure all tests pass
4. Update documentation if needed
5. Request review from maintainers

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Ollama Documentation](https://ollama.com/docs)
- [shadcn/ui Components](https://ui.shadcn.com/)

## 🆘 Getting Help

- Check existing documentation in `/docs`
- Review API documentation at http://localhost:8000/docs
- Check GitHub issues
- Read the Knowledge Graph Guide for AI system details

## 🎯 Common Tasks

### Add a New API Endpoint

1. Define schema in `backend/api/schemas.py`
2. Add route in `backend/api/routes.py`
3. Test with `curl` or Postman
4. Update frontend API client in `src/api/`

### Add a New UI Component

1. Create component in `src/components/`
2. Use shadcn/ui primitives where possible
3. Add TypeScript interfaces in `src/types/`
4. Register keyboard shortcuts if needed

### Modify AI Agent Behavior

1. Update prompts in `backend/agents/prompts.py`
2. Modify agent logic in `backend/agents/cognitive_nexus_graph.py`
3. Adjust constants in `backend/config/constants.py`
4. Test with various inputs

---

**Last Updated:** November 2025
**Maintained By:** Task Crate Team
