# Contributing to Task Crate

Thank you for your interest in contributing! This guide will help you get started.

## 🚀 Quick Start

### 1. Fork and Clone

```bash
git clone https://github.com/yourusername/task-crate.git
cd task-crate
git checkout -b feature/your-feature-name
```

### 2. Install Dependencies

```bash
# Frontend
npm install

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

### 3. Setup Services

```bash
# Install and start Ollama (on your local machine)
brew install ollama  # macOS
ollama serve
ollama pull qwen2.5:7b-instruct

# Optional: Get Gemini API key for Phase 3 features
# https://aistudio.google.com/app/apikey
```

### 4. Run Development Servers

```bash
# Use the convenient start script
./start.sh

# Or manually:
# Terminal 1: Backend
cd backend && python main.py

# Terminal 2: Frontend
npm run dev
```

### 5. Verify Setup

```bash
# Check health
curl http://localhost:8000/api/health

# Open browser
open http://localhost:8080
```

## 📝 Code Style Guidelines

### Python (Backend)

**Style:**
- Follow [PEP 8](https://pep8.org/)
- Use type hints for all function parameters and returns
- Maximum line length: 100 characters
- Use async/await for database operations

**Naming:**
```python
# Good
async def get_user_profile(user_id: int) -> UserProfile:
    """Get user profile by ID.
    
    Args:
        user_id: The user's database ID
        
    Returns:
        UserProfile object
        
    Raises:
        HTTPException: If user not found
    """
    result = await db.execute(
        select(UserProfile).where(UserProfile.id == user_id)
    )
    return result.scalar_one_or_none()

# Bad
def GetUserProfile(userId):  # Wrong case, no types
    return db.query(UserProfile).filter_by(id=userId).first()
```

**Imports:**
```python
# Standard library
import os
from typing import Optional, List

# Third-party
from fastapi import HTTPException
from sqlalchemy import select

# Local
from db.models import Task
from services.gemini_client import get_gemini_client
```

### TypeScript (Frontend)

**Style:**
- Use TypeScript strict mode
- Functional components with hooks (no class components)
- Maximum line length: 100 characters
- Use `const` over `let`, never use `var`

**Naming:**
```typescript
// Good
const TaskCard: React.FC<TaskCardProps> = ({ task, onUpdate }) => {
  const [isEditing, setIsEditing] = useState(false);
  
  const handleSave = async () => {
    await updateTask(task.id, { status: 'done' });
    onUpdate();
  };
  
  return <div>...</div>;
};

// Bad
function taskcard(props) {  // Wrong case, no types
  var editing = false;  // var instead of const/let
  // ...
}
```

**Interfaces:**
```typescript
// Define interfaces for all data structures
interface Task {
  id: string;
  title: string;
  status: 'todo' | 'doing' | 'done';
  assignee?: string;
  dueDate?: string;
}

// Use type for unions/aliases
type TaskStatus = 'todo' | 'doing' | 'done';
```

## 🔄 Git Workflow

### Branch Naming

```bash
# Feature
git checkout -b feature/add-task-filters

# Bug fix
git checkout -b fix/comment-persistence

# Documentation
git checkout -b docs/update-api-reference

# Refactor
git checkout -b refactor/simplify-knowledge-graph
```

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Format: <type>(<scope>): <description>

# Examples
git commit -m "feat(api): add task filtering endpoint"
git commit -m "fix(ui): resolve comment persistence issue"
git commit -m "docs(readme): update quick start guide"
git commit -m "refactor(kg): simplify entity deduplication"
git commit -m "test(api): add integration tests for tasks"
git commit -m "chore(deps): update fastapi to 0.104.1"
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation only
- `style` - Formatting, missing semi-colons, etc.
- `refactor` - Code restructuring without behavior change
- `test` - Adding or updating tests
- `chore` - Maintenance, dependency updates
- `perf` - Performance improvements

### Pull Request Process

1. **Update from main:**
   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. **Run tests:**
   ```bash
   cd backend && pytest tests/ -v
   npm run type-check
   ```

3. **Push to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create Pull Request** with:
   - Clear description of changes
   - Screenshots for UI changes
   - Link to related issue (if any)
   - Test results

5. **Address review feedback**

6. **Squash commits if needed:**
   ```bash
   git rebase -i origin/main
   ```

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_cognitive_nexus.py -v

# Run with coverage
pytest --cov=. --cov-report=html tests/

# Run only fast tests
pytest -m "not slow" tests/
```

### Frontend Tests

```bash
# Run tests (when available)
npm test

# Type check
npm run type-check

# Lint
npm run lint
```

### Writing Tests

**Backend (pytest):**
```python
# tests/test_relevance_filter.py
import pytest
from agents.relevance_filter import RelevanceFilter

@pytest.mark.asyncio
async def test_relevance_scoring():
    """Test relevance scoring for user's projects."""
    filter = RelevanceFilter()
    
    task = {
        "title": "Update CRESCO dashboard",
        "project": "CRESCO"
    }
    
    user_profile = {
        "projects": ["CRESCO", "Just Deals"]
    }
    
    score = await filter.calculate_relevance(task, user_profile)
    assert score >= 70  # Should be relevant
```

**Frontend (Vitest/Jest):**
```typescript
// src/components/__tests__/TaskCard.test.tsx
import { render, screen } from '@testing-library/react';
import { TaskCard } from '../TaskCard';

describe('TaskCard', () => {
  it('renders task title', () => {
    const task = {
      id: '1',
      title: 'Test Task',
      status: 'todo'
    };
    
    render(<TaskCard task={task} />);
    expect(screen.getByText('Test Task')).toBeInTheDocument();
  });
});
```

## 🗄️ Database Changes

### Creating Migrations

1. **Update models:**
   ```python
   # backend/db/models.py
   class Task(Base):
       __tablename__ = "tasks"
       
       # Add new column
       priority_score = Column(Integer, default=0)
   ```

2. **Create migration script:**
   ```python
   # backend/db/migrations/004_add_priority_score.py
   async def upgrade():
       """Add priority_score column."""
       await db.execute(
           "ALTER TABLE tasks ADD COLUMN priority_score INTEGER DEFAULT 0"
       )
   
   async def downgrade():
       """Remove priority_score column."""
       await db.execute(
           "ALTER TABLE tasks DROP COLUMN priority_score"
       )
   ```

3. **Test migration:**
   ```bash
   # Backup database
   cp backend/tasks.db backend/tasks.db.backup
   
   # Run migration
   python -m db.migrations.004_add_priority_score
   
   # Verify
   sqlite3 backend/tasks.db ".schema tasks"
   ```

4. **Document in CHANGELOG.md**

## 📚 Documentation

### Updating Documentation

- Update relevant docs in `docs/` directory
- Keep code examples tested and current
- Use clear, concise language
- Include examples for complex features

### Documentation Structure

```
docs/
├── INDEX.md                    # Navigation hub
├── guides/                     # User guides
├── architecture/               # Technical design
├── api/                        # API documentation
└── development/                # Dev guides
```

## 🎯 PR Checklist

Before submitting your PR, ensure:

- [ ] Code follows style guidelines (PEP 8 for Python, TypeScript strict)
- [ ] All tests pass (`pytest tests/ -v` and `npm test`)
- [ ] No console errors in browser
- [ ] Type checking passes (`npm run type-check`)
- [ ] Documentation updated if needed
- [ ] Commit messages follow conventional commits
- [ ] PR description is clear and complete
- [ ] Screenshots included for UI changes
- [ ] Backend health check passes (`curl http://localhost:8000/api/health`)
- [ ] No merge conflicts with main branch

## 💡 Development Tips

### Debugging

**Backend:**
```python
# Use Python debugger
import pdb; pdb.set_trace()

# Or use logging
import logging
logging.debug(f"Variable value: {variable}")
```

**Frontend:**
```typescript
// Use console.log strategically
console.log('Task data:', task);

// Use React DevTools browser extension
```

### Hot Reloading

- Backend: Auto-reloads with `--reload` flag
- Frontend: Vite hot-reloads automatically

### Testing AI Features

```bash
# Test with sample data
curl -X POST http://localhost:8000/api/assistant/message \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Test message: Jef needs to review CRESCO by Friday",
    "source_type": "manual"
  }'
```

## 🤝 Community

- **Questions?** Open a GitHub issue with the `question` label
- **Ideas?** Open an issue with the `enhancement` label
- **Bugs?** Open an issue with the `bug` label and include:
  - Steps to reproduce
  - Expected behavior
  - Actual behavior
  - System info (OS, Python version, Node version)

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You!

Every contribution helps make Task Crate better. We appreciate your time and effort!

---

**Questions?** Check out:
- [Development Guide](./docs/development/DEVELOPMENT_GUIDE.md)
- [API Reference](./docs/api/API_REFERENCE.md)
- [Architecture Overview](./docs/architecture/SYSTEM_OVERVIEW.md)

**Last Updated:** November 2025
