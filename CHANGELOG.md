# Changelog

## Recent Changes (Nov 2025)

### Data Persistence Fix
**Problem:** Comments, attachments, and notes were not persisting across sessions.

**Root Causes:**
1. Missing `notes` column in database schema
2. Update endpoint didn't handle comments/attachments
3. Response serialization returned empty arrays
4. Missing eager loading caused async errors

**Solutions:**
- Added `notes` field to Task model, schemas, and API
- Implemented comment/attachment replacement logic in update endpoint
- Fixed `_task_to_schema()` to properly load relationships
- Added `selectinload()` for eager loading in all task queries

**Files Modified:**
- `backend/db/models.py` - Added notes column
- `backend/api/schemas.py` - Updated all task schemas
- `backend/api/routes.py` - Fixed update logic and serialization

### Keyboard Shortcuts System
**Added:** 45 configurable keyboard shortcuts with conflict detection

**Features:**
- Click-to-edit shortcut keys
- Real-time conflict detection
- Backend-driven configuration
- Persistent storage in database

**New Shortcuts:**
- `Ctrl+E` - Toggle between peek and extended view
- `Ctrl+Shift+F` - Open task in full page mode
- Plus 43 other task management shortcuts

**Files Modified:**
- `backend/db/default_shortcuts.py` - Removed 4 duplicates (49→45)
- `src/components/KanbanBoard.tsx` - Added conflict detection
- Multiple component files for view mode integration

### View Modes Enhancement
**Added:** Three task viewing modes

1. **Peek View** (default) - Side sheet, quick access
2. **Extended View** - Wider side sheet, more detail
3. **Full Page View** - Immersive full-screen mode

**Features:**
- Smooth transitions between modes
- Notion-style chat comments in all views
- Consistent UI/UX across all modes
- Keyboard shortcuts for quick switching

**Files Modified:**
- `src/components/TaskDetailSheet.tsx` - Extended view support
- `src/components/TaskFullPage.tsx` - New full page component
- `src/components/KanbanBoard.tsx` - View mode orchestration

### UI/UX Improvements
**Changes:**
- Redesigned comments to Notion-style chat interface
- Enter to send, Shift+Enter for new line
- Full-width comments section with avatars
- Unified design across all view modes
- Removed visual clutter (dividers, excess buttons)

**Files Modified:**
- `src/components/TaskDetailSheet.tsx`
- `src/components/TaskFullPage.tsx`

## Database Migrations

### Manual Migration Required
If upgrading from a version before Nov 16, 2025:

```bash
sqlite3 backend/tasks.db "ALTER TABLE tasks ADD COLUMN notes TEXT;"
```

This adds the notes field to existing databases.

## Breaking Changes

None - all changes are backward compatible.

## Upgrade Notes

1. Pull latest changes
2. Run database migration (if needed)
3. Restart backend: `cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000`
4. Restart frontend: `npm run dev`
5. Verify health: `curl http://localhost:8000/api/health`
