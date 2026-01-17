# Task Crate Quick Reference

Essential commands and information for daily use.

## 🚀 Starting the Application

```bash
# One command to start everything
./start.sh

# Or manually:
# Terminal 1: Ollama (on local machine)
ollama serve

# Terminal 2: Backend
cd backend && python main.py

# Terminal 3: Frontend  
npm run dev
```

**Access:**
- Frontend: http://localhost:8080
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 🛑 Stopping the Application

```bash
./stop.sh

# Or manually: Ctrl+C in each terminal
```

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+E` | Toggle peek/extended view |
| `Ctrl+Shift+F` | Open full page mode |
| `1` | Quick add to To-Do |
| `2` | Quick add to In Progress |
| `3` | Quick add to Done |
| `/` | Slash commands (in editor) |
| `Cmd+>` | Blockquote (macOS) |

[Complete shortcut list →](./docs/guides/KEYBOARD_SHORTCUTS.md)

## 🤖 Using Lotus AI

### Quick Task Creation
```
Click Lotus button (✨) → Paste text → Click "Infer Tasks"
```

### Sample Input
```
Meeting notes: Jef needs to share CRESCO data with Andy by Friday.
Sarah from Product should review the specs before we ship.
```

### PDF Processing
```
Click Lotus button → Upload PDF tab → Select file → Process
```

## 📊 API Quick Reference

### Get All Tasks
```bash
curl http://localhost:8000/api/tasks
```

### Create Task
```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"New task","status":"todo"}'
```

### Process with Lotus
```bash
curl -X POST http://localhost:8000/api/assistant/message \
  -H "Content-Type: application/json" \
  -d '{"content":"Your text here","source_type":"manual"}'
```

### Health Check
```bash
curl http://localhost:8000/api/health
```

[Complete API reference →](./docs/api/API_REFERENCE.md)

## 🔧 Common Tasks

### Update Your Profile
```bash
curl -X PUT http://localhost:8000/api/profiles/1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Your Name",
    "projects": ["Project 1", "Project 2"],
    "markets": ["Market 1"]
  }'
```

### View Knowledge Graph
```bash
# Get entity info
curl http://localhost:8000/api/knowledge/entity/Jef%20Adriaenssens

# Search entities
curl http://localhost:8000/api/knowledge/search?query=cresco

# Get statistics
curl http://localhost:8000/api/knowledge/stats
```

### Check AI Usage & Costs
```bash
curl http://localhost:8000/api/assistant/usage-stats
```

## 🐛 Quick Troubleshooting

### Backend won't start
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Ollama not connecting
```bash
# Start Ollama
ollama serve

# Verify
curl http://localhost:11434/api/tags
```

### Database issues
```bash
cd backend
rm tasks.db
python main.py  # Recreates database
```

### Clear browser cache
- Hard refresh: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)

[Complete troubleshooting →](./docs/guides/TROUBLESHOOTING.md)

## 📁 Project Structure

```
task-crate/
├── src/              # Frontend (React + TypeScript)
├── backend/          # Backend (FastAPI + Python)
│   ├── agents/       # AI agents
│   ├── api/          # API routes
│   ├── db/           # Database models
│   └── services/     # Business logic
├── docs/             # Documentation
└── start.sh          # Start script
```

[Detailed structure →](./docs/PROJECT_STRUCTURE.md)

## 🔑 Environment Variables

### Backend (.env)
```bash
# Ollama (Local AI)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

# Gemini (Cloud AI - Optional)
GOOGLE_AI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash-exp

# Performance
ENABLE_CACHE=true
CACHE_TTL_SECONDS=300
```

### Frontend (.env)
```bash
VITE_API_BASE_URL=http://localhost:8000/api
```

## 🧪 Testing

```bash
# Backend tests
cd backend && pytest tests/ -v

# Specific test
pytest tests/test_phase3_comprehensive.py -v

# With coverage
pytest --cov=. tests/
```

## 📦 Dependencies

### Update All Dependencies
```bash
# Frontend
npm update

# Backend
cd backend
pip install --upgrade -r requirements.txt
```

### Install New Dependency

**Frontend:**
```bash
npm install package-name
```

**Backend:**
```bash
cd backend
source venv/bin/activate
pip install package-name
echo "package-name==version" >> requirements.txt
```

## 🌐 Deployment Checklist

- [ ] Update environment variables
- [ ] Run database migrations
- [ ] Build frontend: `npm run build`
- [ ] Set up reverse proxy (nginx)
- [ ] Configure SSL/TLS
- [ ] Set up monitoring
- [ ] Configure backups
- [ ] Test all endpoints

[Deployment guide →](./docs/development/DEPLOYMENT.md)

## 📚 Documentation Links

- [Getting Started](./docs/GETTING_STARTED.md) - 5-minute setup
- [Lotus Assistant](./docs/guides/LOTUS_ASSISTANT.md) - AI features
- [API Reference](./docs/api/API_REFERENCE.md) - All endpoints
- [Development Guide](./docs/development/DEVELOPMENT_GUIDE.md) - Dev setup
- [Troubleshooting](./docs/guides/TROUBLESHOOTING.md) - Common issues
- [Contributing](./CONTRIBUTING.md) - How to contribute

## 💡 Tips & Tricks

### Faster AI with Gemini
Get API key from https://aistudio.google.com/app/apikey
- 2-3x faster than Ollama
- $0.18/month (vs $8/month with cloud LLMs)

### Use Relevance Filtering
Update your profile to only see relevant tasks:
```bash
curl -X PUT http://localhost:8000/api/profiles/1 \
  -d '{"projects":["Your Projects"]}'
```

### Enable Redis Caching
```bash
brew install redis  # macOS
redis-server
# Add to backend/.env: REDIS_URL=redis://localhost:6379
```

### Quick PDF Testing
Use `/api/assistant/process-pdf-fast` for 2-3s processing (vs 10s+)

## 🆘 Get Help

1. Check [Troubleshooting Guide](./docs/guides/TROUBLESHOOTING.md)
2. Search [Documentation Index](./docs/INDEX.md)
3. Review [API Docs](http://localhost:8000/docs)
4. Open GitHub issue with details

## 📊 System Requirements

- **Node.js:** 18+ or 20+
- **Python:** 3.11+
- **RAM:** 8GB minimum (16GB recommended)
- **Disk:** 10GB free space
- **Ollama:** Latest version
- **OS:** macOS, Linux, or Windows with WSL

---

**Quick Link:** http://localhost:8080 (Frontend)

**Last Updated:** November 2025
