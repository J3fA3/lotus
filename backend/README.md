# AI Task Inference Backend

FastAPI backend with Qwen 2.5 for AI-powered task extraction from text and PDFs.

## Setup

### 1. Install Ollama (on your MacBook Pro)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull Qwen 2.5 7B Instruct model
ollama pull qwen2.5:7b-instruct

# Start Ollama server (runs in background)
ollama serve
```

### 2. Install Python Dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and adjust if needed:

```bash
cp .env.example .env
```

### 4. Run the Backend

```bash
# Make sure Ollama is running first!
python main.py
```

Server will start on http://localhost:8000

API Documentation: http://localhost:8000/docs

## API Endpoints

### Task Management
- `GET /api/tasks` - Get all tasks
- `POST /api/tasks` - Create a task
- `GET /api/tasks/{id}` - Get specific task
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task

### AI Inference
- `POST /api/infer-tasks` - Infer tasks from text
  ```json
  {
    "text": "Meeting notes: John will update the docs by Friday...",
    "assignee": "You"
  }
  ```

- `POST /api/infer-tasks-pdf` - Infer tasks from PDF
  - Form data: `file` (PDF), `assignee` (string)

### Health Check
- `GET /api/health` - Check API, Ollama, and database status

## Architecture

```
backend/
├── main.py              # FastAPI app entry
├── api/
│   ├── routes.py        # API endpoints
│   └── schemas.py       # Pydantic models
├── agents/
│   ├── task_extractor.py   # AI task extraction
│   ├── pdf_processor.py    # PDF parsing
│   └── prompts.py          # LLM prompts
├── db/
│   ├── database.py      # SQLite connection
│   └── models.py        # SQLAlchemy models
└── requirements.txt
```

## Testing

### Test Ollama Connection

```bash
curl http://localhost:11434/api/tags
```

### Test Task Inference

```bash
curl -X POST http://localhost:8000/api/infer-tasks \
  -H "Content-Type: application/json" \
  -d '{
    "text": "We need to update the documentation before the release next Friday. Also, someone should review the auth PR.",
    "assignee": "You"
  }'
```

### Test PDF Inference

```bash
curl -X POST http://localhost:8000/api/infer-tasks-pdf \
  -F "file=@meeting-notes.pdf" \
  -F "assignee=You"
```

## Troubleshooting

### Ollama not connecting

1. Check if Ollama is running: `ps aux | grep ollama`
2. Start Ollama: `ollama serve`
3. Verify model is pulled: `ollama list`

### Database errors

- Delete `tasks.db` and restart the server to recreate database

### Model too slow

- Use smaller model: `ollama pull qwen2.5:3b-instruct`
- Update `.env`: `OLLAMA_MODEL=qwen2.5:3b-instruct`

## Performance

**Expected inference times on 16-core CPU:**
- Qwen 2.5 7B: 10-30 seconds per inference
- Qwen 2.5 3B: 5-15 seconds per inference

**RAM usage:**
- 7B model: ~6GB
- 3B model: ~3GB
