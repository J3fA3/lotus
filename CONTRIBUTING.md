# Contributing Guide

## Development Setup

1. **Fork and clone** the repository
2. **Install dependencies:**
   ```bash
   npm install
   cd backend && pip install -r requirements.txt
   ```
3. **Set up Ollama** - See [docs/OLLAMA_SETUP.md](docs/OLLAMA_SETUP.md)
4. **Run development servers:**
   ```bash
   # Terminal 1: Backend
   cd backend
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   
   # Terminal 2: Frontend
   npm run dev
   ```

## Code Style

### Python (Backend)
- Follow PEP 8
- Use type hints
- Add docstrings to all functions
- Keep functions focused and small

### TypeScript (Frontend)
- Use functional components with hooks
- Prefer const over let
- Add JSDoc for complex functions
- Keep components under 300 lines

## Git Workflow

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes with clear commits:
   ```bash
   git commit -m "feat: add task filtering"
   git commit -m "fix: resolve comment persistence issue"
   ```

3. Push and create a PR:
   ```bash
   git push origin feature/your-feature-name
   ```

## Commit Message Format

Use conventional commits:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `chore:` - Maintenance tasks

## Testing

```bash
# Backend tests (when available)
cd backend
pytest

# Frontend tests (when available)
npm test
```

## Database Changes

If you modify the database schema:

1. Update `backend/db/models.py`
2. Create migration in `CHANGELOG.md`
3. Test with fresh database
4. Document in PR

## Pull Request Checklist

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] No console errors
- [ ] Backend health check passes

## Questions?

Open an issue for discussion before making large changes.
