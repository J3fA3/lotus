# Troubleshooting Guide

Common issues and their solutions for Task Crate.

## 🔍 Quick Diagnostics

### Check System Health

```bash
# Check all services
curl http://localhost:8000/api/health

# Expected response:
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "ollama": {"status": "connected"},
    "gemini": {"status": "connected"}
  }
}
```

---

## 🚨 Common Issues

### Backend Connection Issues

#### Problem: "Backend not connected"

**Symptoms:**
- Frontend shows connection error
- Tasks don't load
- API requests fail

**Diagnosis:**
```bash
# Test backend directly
curl http://localhost:8000/api/health

# Check if backend is running
ps aux | grep "python main.py"
```

**Solutions:**

1. **Start the backend:**
   ```bash
   cd backend
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   python main.py
   ```

2. **Check the port:**
   ```bash
   # Make sure port 8000 isn't in use
   lsof -ti:8000
   # If something is using it, kill the process or use a different port
   ```

3. **Check environment variables:**
   ```bash
   cd backend
   cat .env
   # Verify OLLAMA_BASE_URL and other settings
   ```

---

### Ollama Connection Issues

#### Problem: "Ollama is not connected"

**Symptoms:**
- AI inference fails
- Health check shows Ollama disconnected
- Tasks can't be processed

**Diagnosis:**
```bash
# Test Ollama directly
curl http://localhost:11434/api/tags

# For dev containers:
curl http://host.docker.internal:11434/api/tags
```

**Solutions:**

1. **Start Ollama (on your local machine):**
   ```bash
   ollama serve
   ```

2. **Verify model is pulled:**
   ```bash
   ollama list
   # Should show qwen2.5:7b-instruct
   
   # If not:
   ollama pull qwen2.5:7b-instruct
   ```

3. **Check backend configuration:**
   ```bash
   # In backend/.env
   OLLAMA_BASE_URL=http://localhost:11434  # Local
   # or
   OLLAMA_BASE_URL=http://host.docker.internal:11434  # Dev container
   ```

4. **Test from backend:**
   ```bash
   cd backend
   python -c "
   import requests
   r = requests.get('http://localhost:11434/api/tags')
   print(r.status_code, r.json())
   "
   ```

---

### Gemini API Issues

#### Problem: "Gemini not available" or API errors

**Symptoms:**
- Phase 3 features slow or failing
- Falls back to Ollama
- Cost tracking shows $0

**Diagnosis:**
```bash
# Check API key is set
echo $GOOGLE_AI_API_KEY

# Test Gemini directly
cd backend
python -c "
from services.gemini_client import get_gemini_client
client = get_gemini_client()
print(f'Available: {client.available}')
print(f'Model: {client.model_name}')
"
```

**Solutions:**

1. **Set API key:**
   ```bash
   cd backend
   # Edit .env
   GOOGLE_AI_API_KEY=your_actual_api_key_here
   ```

2. **Get API key:**
   - Visit: https://aistudio.google.com/app/apikey
   - Create new API key
   - Copy to .env file

3. **Check quota:**
   - Visit: https://aistudio.google.com/app/apikey
   - Check rate limits and usage

4. **Verify internet connection:**
   ```bash
   ping gemini-api.googleapis.com
   ```

---

### Database Issues

#### Problem: Tasks not persisting or database errors

**Symptoms:**
- Tasks disappear on refresh
- "Database error" messages
- Can't create/update tasks

**Diagnosis:**
```bash
# Check if database file exists
ls -la backend/tasks.db

# Check file permissions
ls -l backend/tasks.db

# Try to open database
sqlite3 backend/tasks.db ".tables"
```

**Solutions:**

1. **Reset database:**
   ```bash
   cd backend
   rm tasks.db
   python main.py  # Recreates database
   ```

2. **Run migrations:**
   ```bash
   cd backend
   python -m db.migrations.003_add_phase3_tables
   ```

3. **Check disk space:**
   ```bash
   df -h
   ```

4. **Fix permissions:**
   ```bash
   chmod 644 backend/tasks.db
   ```

---

### Performance Issues

#### Problem: AI inference is slow (>30 seconds)

**Symptoms:**
- Task extraction takes too long
- UI freezes during processing
- Timeout errors

**Diagnosis:**
```bash
# Check CPU usage during inference
top

# Check RAM usage
free -h  # Linux
vm_stat  # macOS

# Check which model is being used
curl http://localhost:11434/api/tags | grep qwen
```

**Solutions:**

1. **Use smaller model:**
   ```bash
   # On local machine
   ollama pull qwen2.5:3b-instruct
   
   # Update backend/.env
   OLLAMA_MODEL=qwen2.5:3b-instruct
   
   # Restart backend
   ```

2. **Enable Gemini (much faster):**
   ```bash
   # In backend/.env
   GOOGLE_AI_API_KEY=your_api_key
   # Gemini processes in 1-2s vs 10-30s with Ollama
   ```

3. **Close other applications:**
   - Free up RAM for model
   - Close browser tabs
   - Stop other services

4. **Enable caching:**
   ```bash
   # In backend/.env
   ENABLE_CACHE=true
   CACHE_TTL_SECONDS=300
   ```

5. **Install Redis for better caching:**
   ```bash
   # macOS
   brew install redis
   redis-server
   
   # In backend/.env
   REDIS_URL=redis://localhost:6379
   ```

---

### Frontend Issues

#### Problem: Frontend not loading or showing errors

**Symptoms:**
- White screen
- Console errors
- Components not rendering

**Diagnosis:**
```bash
# Check frontend logs
npm run dev
# Look for errors in terminal

# Check browser console
# F12 → Console tab
```

**Solutions:**

1. **Clear node_modules and reinstall:**
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   npm run dev
   ```

2. **Check Node version:**
   ```bash
   node --version
   # Should be 18+ or 20+
   
   # If wrong version, use nvm:
   nvm install 20
   nvm use 20
   ```

3. **Clear browser cache:**
   - Hard refresh: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R`
   - Or clear cache in browser settings

4. **Check environment variables:**
   ```bash
   cat .env
   # Verify VITE_API_BASE_URL=http://localhost:8000/api
   ```

---

### PDF Processing Issues

#### Problem: PDF upload fails or extracts no tasks

**Symptoms:**
- Upload button doesn't work
- "Failed to process PDF" error
- PDF uploads but no tasks created

**Diagnosis:**
```bash
# Test PDF processing manually
curl -X POST http://localhost:8000/api/assistant/process-pdf \
  -F "file=@test.pdf"
```

**Solutions:**

1. **Check PDF file:**
   - Make sure it's a valid PDF
   - Not password protected
   - Not scanned images (OCR needed)
   - Size under 10MB

2. **Test with text-based PDF:**
   - Use a PDF with actual text (not just images)
   - Try with a different PDF

3. **Check PyMuPDF installation:**
   ```bash
   cd backend
   pip install --upgrade pymupdf
   ```

4. **Increase timeout for large PDFs:**
   ```bash
   # In frontend, increase timeout
   # Or use fast endpoint: /api/assistant/process-pdf-fast
   ```

---

### Task Relevance Issues

#### Problem: Wrong tasks filtered out or too many irrelevant tasks

**Symptoms:**
- Important tasks not created
- Tasks for other people appearing
- Relevance scores seem wrong

**Diagnosis:**
```bash
# Check user profile
curl http://localhost:8000/api/profiles/1

# Test relevance scoring
curl -X POST http://localhost:8000/api/assistant/message \
  -H "Content-Type: application/json" \
  -d '{"content":"Alberto asked about Spain"}' \
  -v
```

**Solutions:**

1. **Update user profile:**
   ```bash
   curl -X PUT http://localhost:8000/api/profiles/1 \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Your Name",
       "projects": ["Your Project 1", "Your Project 2"],
       "markets": ["Your Market 1"],
       "colleagues": ["Colleague 1", "Colleague 2"]
     }'
   ```

2. **Adjust relevance threshold:**
   ```python
   # In backend/agents/relevance_filter.py
   RELEVANCE_THRESHOLD = 60  # Lower = more tasks
   # or
   RELEVANCE_THRESHOLD = 80  # Higher = fewer tasks
   ```

3. **Check name normalization:**
   ```bash
   # Make sure your name is spelled consistently
   # "Jeff" vs "Jef" → System normalizes automatically
   ```

---

### Knowledge Graph Issues

#### Problem: Duplicate entities or wrong relationships

**Symptoms:**
- Same person appears multiple times
- Relationships not connecting properly
- Entity names inconsistent

**Diagnosis:**
```bash
# Check knowledge graph for an entity
curl http://localhost:8000/api/knowledge/entity/Jef%20Adriaenssens

# Get graph statistics
curl http://localhost:8000/api/knowledge/stats
```

**Solutions:**

1. **Check fuzzy matching threshold:**
   ```python
   # In backend/services/knowledge_graph_service.py
   ENTITY_SIMILARITY_THRESHOLD = 0.75  # Default
   # Lower = more aggressive merging
   # Higher = less merging (more duplicates)
   ```

2. **Manual entity merge (future feature):**
   ```bash
   # Coming soon: UI for merging duplicate entities
   ```

3. **Reset knowledge graph:**
   ```bash
   cd backend
   # Backup first!
   cp tasks.db tasks.db.backup
   
   # Reset knowledge graph tables
   sqlite3 tasks.db "DELETE FROM knowledge_nodes; DELETE FROM knowledge_edges;"
   
   # Reprocess contexts
   # (Will rebuild from existing contexts)
   ```

---

## 🔧 Advanced Troubleshooting

### Enable Debug Logging

```bash
# In backend/.env
LOG_LEVEL=DEBUG

# Or in code:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Database Integrity

```bash
cd backend
sqlite3 tasks.db "PRAGMA integrity_check;"
```

### View Recent Errors

```bash
# Backend logs
tail -f backend/logs/app.log

# Or check console output
```

### Test Individual Components

```bash
# Test Gemini client
cd backend
python -c "
from services.gemini_client import get_gemini_client
client = get_gemini_client()
result = client.generate_content('Say hello')
print(result)
"

# Test knowledge graph
python -c "
from services.knowledge_graph_service import KnowledgeGraphService
service = KnowledgeGraphService()
# Test operations
"
```

---

## 💡 Getting Help

If you're still stuck:

1. **Check the logs** - Backend logs show detailed errors
2. **Review recent changes** - Check git log for what changed
3. **Test with minimal example** - Isolate the issue
4. **Check GitHub issues** - Someone may have had the same problem
5. **Create a new issue** with:
   - System info (OS, Python version, Node version)
   - Error messages (full text)
   - Steps to reproduce
   - What you've already tried

---

## 📊 System Requirements Check

```bash
# Check all requirements at once
echo "=== Node.js ==="
node --version  # Should be 18+ or 20+
echo "=== Python ==="
python --version  # Should be 3.11+
echo "=== Ollama ==="
ollama --version  # Should be 0.3.3+
echo "=== Disk Space ==="
df -h | grep -E '^Filesystem|/$'  # Should have 10GB+ free
echo "=== RAM ==="
free -h || vm_stat  # Should have 8GB+ total
```

---

## 🔄 Clean Reinstall

If all else fails, start fresh:

```bash
# 1. Backup your data
cp backend/tasks.db tasks.db.backup

# 2. Clean everything
rm -rf node_modules backend/venv backend/tasks.db
rm -rf backend/__pycache__ backend/**/__pycache__

# 3. Reinstall dependencies
npm install
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Restart services
ollama serve &  # In separate terminal
python main.py &  # In separate terminal
cd ..
npm run dev
```

---

**Last Updated:** November 2025  
**If you find a solution not listed here, please contribute!**
