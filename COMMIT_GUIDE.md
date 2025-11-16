# Commit Guide for Recent Changes

## Summary
Major refactoring with data persistence fixes, keyboard shortcuts cleanup, view modes enhancement, and documentation consolidation.

## Suggested Commit Structure

### Option 1: Single Commit (Simple)
```bash
git add -A
git commit -m "feat: add data persistence, shortcuts system, and view modes

- Fix: Comments, attachments, and notes now persist across sessions
- Fix: Removed 4 duplicate shortcuts (49→45 total)
- Feat: Added peek, extended, and full-page task views
- Feat: Keyboard shortcuts with conflict detection (Ctrl+E, Ctrl+Shift+F)
- Refactor: Consolidated documentation, removed bloat files
- Docs: Added OLLAMA_SETUP.md for SSH tunnel configuration
- Docs: Updated README with proper architecture diagrams

Backend changes:
- Added notes column to Task model
- Implemented comment/attachment replacement logic
- Added selectinload for eager loading relationships
- Updated all schemas to support new fields

Frontend changes:
- Notion-style chat comments (Enter to send)
- Three view modes with smooth transitions
- 45 configurable shortcuts with real-time conflict detection
- Unified UI/UX across all views"
```

### Option 2: Multiple Commits (Detailed)

```bash
# 1. Data persistence fix
git add backend/db/models.py backend/api/schemas.py backend/api/routes.py
git commit -m "fix: implement full data persistence for comments, attachments, and notes

- Add notes column to Task model and database
- Update TaskUpdateRequest schema to accept comments/attachments
- Implement replacement strategy for comments/attachments
- Fix _task_to_schema to load relationships properly
- Add selectinload for eager loading to prevent greenlet errors"

# 2. Shortcuts cleanup
git add backend/db/default_shortcuts.py src/components/KanbanBoard.tsx src/contexts/ShortcutContext.tsx
git commit -m "refactor: clean up keyboard shortcuts and add conflict detection

- Remove 4 duplicate shortcuts (49→45 total)
- Add real-time conflict detection on shortcut edit
- Implement click-to-edit for shortcut configuration
- Prevent saving conflicting key combinations"

# 3. View modes
git add src/components/TaskDetailSheet.tsx src/components/TaskFullPage.tsx src/components/KanbanBoard.tsx
git commit -m "feat: add multiple task view modes with keyboard shortcuts

- Implement peek view (default side sheet)
- Add extended view (wider side sheet, Ctrl+E toggle)
- Create full-page view (immersive mode, Ctrl+Shift+F)
- Add Notion-style chat comments to all views
- Unified UI/UX with consistent transitions"

# 4. Documentation
git add README.md CHANGELOG.md CONTRIBUTING.md PROJECT_STRUCTURE.md docs/ backend/README.md
git rm CODEBASE_OVERVIEW.md SHORTCUTS_*.md DOCUMENTATION_INDEX.md FILE_STRUCTURE_GUIDE.md REFACTORING_SUMMARY.md CODEBASE_SUMMARY.md
git commit -m "docs: consolidate and improve documentation

- Rewrite README with clear architecture and setup
- Add CHANGELOG.md for tracking changes
- Create CONTRIBUTING.md for development guidelines
- Add PROJECT_STRUCTURE.md for codebase overview
- Create OLLAMA_SETUP.md for SSH tunnel configuration
- Remove 10+ redundant documentation files
- Add inline code comments to critical files"
```

## Pre-Commit Checklist

- [x] Backend health check passes (ollama_connected: true)
- [x] No TypeScript/Python errors
- [x] Database migrations documented in CHANGELOG.md
- [x] README updated with current features
- [x] Removed redundant documentation files
- [x] Added inline code comments
- [x] All modified files use consistent style

## What Changed

### Backend (Python)
- `backend/db/models.py` - Added notes field to Task
- `backend/api/schemas.py` - Updated all schemas for persistence
- `backend/api/routes.py` - Fixed update logic, added eager loading
- `backend/db/default_shortcuts.py` - Removed duplicates
- `backend/README.md` - Updated API documentation

### Frontend (TypeScript)
- `src/components/KanbanBoard.tsx` - Added conflict detection, view modes
- `src/components/TaskDetailSheet.tsx` - Extended view, Notion UI
- `src/components/TaskFullPage.tsx` - **NEW** Full-page view
- `src/contexts/ShortcutContext.tsx` - Enhanced shortcut management

### Documentation
- **Added:** CHANGELOG.md, CONTRIBUTING.md, PROJECT_STRUCTURE.md, docs/OLLAMA_SETUP.md
- **Deleted:** 10 redundant markdown files
- **Updated:** README.md, backend/README.md

## Migration Notes

Users upgrading need to run:
```sql
ALTER TABLE tasks ADD COLUMN notes TEXT;
```

This is documented in CHANGELOG.md.

## Verification Commands

```bash
# Backend health
curl http://localhost:8000/api/health

# Test task update with persistence
curl -X PUT http://localhost:8000/api/tasks/{task_id} \
  -H "Content-Type: application/json" \
  -d '{"notes":"Test","comments":[{"text":"Comment","author":"User"}]}'

# Verify data persists
curl http://localhost:8000/api/tasks/{task_id}
```
