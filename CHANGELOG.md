# Changelog

## [3.0.0] - Phase 3: Speed & Intelligence with Gemini (Nov 18, 2024)

### 🚀 Major Features

**Gemini 2.0 Flash Integration** - 45x cost reduction ($8/mo → $0.18/mo)
- Gemini API client with structured output and automatic Qwen fallback
- Built-in cost tracking and usage monitoring
- Improved classification accuracy and natural language generation

**User Profile System** - Personalization and context awareness
- User profile management with name normalization ("Jeff" → "Jef")
- Role, project, market tracking for intelligent task filtering
- New `user_profiles` database table with caching (5-min TTL)

**Relevance Filtering** - Only extract what's relevant
- 0-100 scoring algorithm with 70+ threshold for task creation
- Filters tasks for other people (e.g., "Maran needs to review...")
- Context-aware using user's projects, markets, and role

**Task Enrichment Engine** - Smart auto-updates
- Auto-updates existing tasks with new information
- Example: "Co-op moved to Dec 3" updates Co-op task deadline
- Confidence-based: >80% auto-apply, 50-80% ask approval

**Natural Language Comments** - No more robot speak
- Replaces "🤖 Confidence: 75%" with human-like explanations
- References people, markets, projects in context
- Comments persisted to database

**Performance Cache** - 2-3x faster response times
- LRU cache with TTL support (in-memory + optional Redis)
- 20-30s → 8-12s for simple messages
- Cache hit rate tracking and monitoring

### 🔧 Orchestrator Integration (11 nodes total)

**New Nodes:**
- `load_user_profile` - Loads user context at start
- `check_task_enrichments` - Finds enrichment opportunities
- `filter_relevant_tasks` - Filters by relevance score

**Migrated to Gemini:**
- `classify_request` - Request classification
- `answer_question` - Question answering
- `generate_clarifying_questions` - Better questions

**Graph Flow:** `load_profile → classify → ... → filter_relevance → execute`

### 📝 New Files (2,451 total lines)
- `backend/services/gemini_client.py` (330 lines)
- `backend/services/performance_cache.py` (395 lines)
- `backend/services/user_profile.py` (292 lines)
- `backend/agents/relevance_filter.py` (248 lines)
- `backend/agents/enrichment_engine.py` (276 lines)
- `backend/services/comment_generator.py` (225 lines)
- `backend/config/gemini_prompts.py` (298 lines)
- `backend/utils/singleton.py` (173 lines)
- `backend/db/migrations/003_add_phase3_tables.py` (214 lines)

### 📊 Performance Improvements
- **Latency**: 20-30s → 8-12s (2-3x faster)
- **Cost**: $8/mo → $0.18/mo (45x cheaper)
- **Tests**: 100% pass rate (6/6 tests)
- **Cache hit rate**: >60% after warm-up

### 🔄 Modified Files
- `backend/agents/orchestrator.py` (+455 lines) - Full integration
- `backend/db/models.py` - UserProfile & TaskEnrichment tables
- `backend/requirements.txt` - Added Phase 3 dependencies

### 🗑️ Cleanup
- Removed `PHASE3_ORCHESTRATOR_STATUS.md` (merged into guide)
- Moved test file to proper location
- Cleaned up all `__pycache__/` directories
- Fixed return type inconsistencies

### 📦 Migration
```bash
pip install -r backend/requirements.txt
# Add GOOGLE_AI_API_KEY to backend/.env
python -m db.migrations.003_add_phase3_tables
```

### ⚠️ Breaking Changes
None - fully backwards compatible with Phase 2.

---

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
