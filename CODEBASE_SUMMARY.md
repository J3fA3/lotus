# AI Task Inference - Complete Codebase Summary

## Quick Overview

This is a **Notion-like Kanban task management application** with **AI-powered task extraction**. It's a full-stack application with:

- **Frontend**: React 18 + TypeScript + Vite + shadcn/ui
- **Backend**: FastAPI (Python) + SQLite + Ollama (Qwen 2.5)
- **AI Integration**: Local LLM for extracting tasks from text/PDFs
- **UI Pattern**: 3-column Kanban board (To-Do, In Progress, Done)

---

## 1. TECH STACK AT A GLANCE

### Frontend Stack
```
React 18.3 (UI library)
├── TypeScript 5.8 (type safety)
├── Vite 5.4 (build tool)
├── React Router v6 (routing)
├── Tailwind CSS 3.4 (styling)
├── shadcn/ui (components - 50+)
├── Sonner 1.7 (toast notifications)
├── React Hook Form 7.61 (form handling)
├── TanStack Query 5.83 (data fetching - installed but minimal use)
├── date-fns 3.6 (date utilities)
├── cmdk 1.1 (command palette - installed, not used yet)
└── Lucide React 0.462 (icons)
```

### Backend Stack
```
FastAPI (web framework)
├── Python 3.x
├── SQLAlchemy (ORM, async support)
├── SQLite (database)
├── Ollama (local LLM server)
│   └── Qwen 2.5 7B Instruct (model)
├── PyMuPDF (PDF processing)
└── Uvicorn (ASGI server)
```

### Design System
- **Color Scheme**: "Zen" palette (warm neutrals + green accent)
- **CSS Variables**: HSL-based color definitions
- **Component Library**: Radix UI + Tailwind CSS
- **Icons**: Lucide React
- **Animations**: Smooth transitions (0.3s cubic-bezier)

---

## 2. CURRENT KEYBOARD SHORTCUTS

### Main Shortcuts (KanbanBoard.tsx)
| Key | Action | Effect |
|-----|--------|--------|
| **1** | Quick add To-Do | Opens form in "todo" column |
| **2** | Quick add In Progress | Opens form in "doing" column |
| **3** | Quick add Done | Opens form in "done" column |
| **Shift+?** | Toggle help | Shows/hides shortcuts panel |

### Form Shortcuts (QuickAddTask.tsx)
| Key | Action |
|-----|--------|
| **Enter** | Submit task |
| **Escape** | Cancel & close form |

### Total: 6 keyboard shortcuts currently implemented

---

## 3. MAIN UI COMPONENTS

### Component Hierarchy
```
App
└── BrowserRouter + QueryClientProvider + Sonner
    └── Index (page)
        └── KanbanBoard (main component)
            ├── 3-column grid layout
            │   ├── Column 1: To-Do
            │   │   ├── TaskCard × N
            │   │   └── QuickAddTask (when active)
            │   ├── Column 2: In Progress
            │   └── Column 3: Done
            ├── TaskDetailDialog (modal)
            └── AIInferenceDialog (modal)
```

### Component Files & Responsibilities

| Component | File | Purpose |
|-----------|------|---------|
| **KanbanBoard** | `src/components/KanbanBoard.tsx` | Main board, shortcuts, CRUD |
| **TaskCard** | `src/components/TaskCard.tsx` | Task display, click to edit |
| **TaskDetailDialog** | `src/components/TaskDetailDialog.tsx` | Full task editor (modal) |
| **QuickAddTask** | `src/components/QuickAddTask.tsx` | Inline task creation form |
| **AIInferenceDialog** | `src/components/AIInferenceDialog.tsx` | AI extraction UI (text/PDF) |
| **App** | `src/App.tsx` | Root component, routing, providers |
| **Index** | `src/pages/Index.tsx` | Page wrapper |
| **UI Components** | `src/components/ui/*` | 50+ shadcn/ui components |

---

## 4. CONFIGURATION SYSTEM

### Environment Configuration

**Frontend (.env)**
```env
VITE_API_BASE_URL=/api
```

**Backend (main.py constants)**
```python
OLLAMA_MODEL = "qwen2.5:7b-instruct"
OLLAMA_BASE_URL = "http://localhost:11434"
API_HOST = "0.0.0.0"
API_PORT = 8000
DEBUG = true
CORS_ORIGINS = "http://localhost:5173"
```

### Build Configuration

**Vite (vite.config.ts)**
- Frontend server: port 8080
- API proxy: /api → http://localhost:8000
- Path alias: @/ → src/
- Code splitting: vendor & UI bundles

**Tailwind (tailwind.config.ts)**
- Dark mode: class-based
- Custom colors: HSL variables
- Custom shadows: zen-sm, zen-md
- Extended theme with sidebar colors

**shadcn/ui (components.json)**
- Component aliases configured
- Tailwind & CSS variables enabled

---

## 5. OVERALL ARCHITECTURE

### 3-Tier Architecture

```
┌─────────────────────────────────────┐
│     PRESENTATION TIER               │
│  React Components (shadcn/ui)       │
│  - KanbanBoard                      │
│  - TaskCard                         │
│  - Dialogs & Forms                  │
│  - Notifications (Sonner)           │
└────────────┬────────────────────────┘
             │ REST API (/api/...)
             ↓
┌─────────────────────────────────────┐
│     APPLICATION TIER                │
│  FastAPI Routes                     │
│  - /tasks (CRUD)                    │
│  - /infer-tasks (text)              │
│  - /infer-tasks-pdf (file)          │
│  - /health (status)                 │
└────────────┬────────────────────────┘
             │ HTTP Client
             ↓
┌─────────────────────────────────────┐
│     SERVICE TIER                    │
│  TaskExtractor (Ollama integration) │
│  PDFProcessor (text extraction)     │
│  Database (SQLAlchemy async)        │
└────────────┬────────────────────────┘
             │ HTTP
             ↓
┌─────────────────────────────────────┐
│     EXTERNAL SERVICES               │
│  Ollama (LLM server)                │
│  SQLite (persistent storage)        │
└─────────────────────────────────────┘
```

### Data Flow: Task Creation via Shortcut

```
1. User presses "1" key
2. KanbanBoard.handleKeyDown() triggered
3. setQuickAddColumn("todo")
4. QuickAddTask component renders
5. User types task title + Enter
6. handleQuickAddTask() called
7. POST /api/tasks
8. Backend: FastAPI creates task
9. Backend: SQLAlchemy saves to SQLite
10. Response: Task with ID
11. Frontend: setTasks([...prev, newTask])
12. UI: New TaskCard appears
13. Toast: Success notification
```

### Data Flow: AI Task Inference

```
1. User clicks "AI Infer Tasks" button
2. AIInferenceDialog opens
3. User pastes text OR uploads PDF
4. User clicks "Infer Tasks"
5. POST /api/infer-tasks (or /api/infer-tasks-pdf)
6. Backend: Receives request
7. Backend: PDFProcessor extracts text (if PDF)
8. Backend: TaskExtractor sends to Ollama
9. Ollama: Qwen 2.5 processes with prompt
10. Ollama: Returns task list
11. Backend: Parses & formats response
12. Response: InferenceResponse with tasks
13. Frontend: Adds tasks to state
14. UI: New TaskCards appear
15. Toast: Shows results & performance metrics
```

---

## 6. KEY FILES REFERENCE

### Critical Files for Enhancement

| File | Purpose | Lines |
|------|---------|-------|
| **KanbanBoard.tsx** | Main component + shortcuts | 360 lines |
| **QuickAddTask.tsx** | Quick add form | 62 lines |
| **TaskDetailDialog.tsx** | Task editor | 281 lines |
| **vite.config.ts** | Dev server & build config | 44 lines |
| **tailwind.config.ts** | Design system config | 104 lines |
| **src/types/task.ts** | Type definitions | 24 lines |
| **src/api/tasks.ts** | API client functions | 234 lines |

### Supporting Files

| File | Purpose |
|------|---------|
| `src/App.tsx` | Root component, routing, providers |
| `src/pages/Index.tsx` | Main page wrapper |
| `src/hooks/use-toast.ts` | Custom toast system |
| `src/hooks/use-mobile.tsx` | Mobile detection |
| `src/lib/utils.ts` | Utility functions (cn()) |
| `src/components/ui/*` | 50+ pre-built components |

---

## 7. EXPANSION OPPORTUNITIES

### Recommended Shortcut Enhancements

**Phase 1: Basic Shortcuts**
- Ctrl+N: New task dialog
- Ctrl+F: Search/filter
- Ctrl+E: Edit selected task
- Tab: Navigate columns
- Arrow keys: Navigate cards

**Phase 2: Command Palette**
- Use installed `cmdk` library
- Ctrl+K / Cmd+K to open
- Fuzzy search commands
- Command categories
- Recent commands

**Phase 3: Advanced Features**
- Custom shortcut mapping
- localStorage persistence
- Shortcut profiles (Vim, Emacs, etc.)
- Platform-aware shortcuts (Mac Cmd vs Ctrl)
- Shortcut discoverer/help modal
- Keyboard navigation between all UI elements

### File Structure for Enhancement

```
src/lib/shortcuts.ts                  # Shortcut definitions
src/hooks/useKeyboard.ts             # Reusable keyboard hook
src/hooks/useShortcuts.ts            # Shortcuts-specific hook
src/components/CommandPalette.tsx    # Command palette
src/config/keybindings.ts            # Preset bindings
src/lib/keyboard-utils.ts            # Keyboard utilities
```

---

## 8. DEVELOPMENT SETUP

### Installation
```bash
# Frontend
npm install
npm run dev           # http://localhost:8080

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py        # http://localhost:8000
```

### Scripts Available
```bash
npm run dev           # Development server
npm run build         # Production build
npm run build:dev     # Development build
npm run lint          # ESLint check
npm run preview       # Preview build
```

### API Documentation
- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

---

## 9. QUICK START FOR SHORTCUTS ENHANCEMENT

### Step 1: Understand Current Implementation
- File: `/home/user/task-crate/src/components/KanbanBoard.tsx`
- Focus on: Lines 20-25 (constants), 86-117 (handler)

### Step 2: Identify Enhancement Points
- Extract shortcuts to separate configuration file
- Create reusable keyboard hooks
- Add command palette using `cmdk`
- Enhance shortcuts help UI

### Step 3: Implementation Pattern
```typescript
// 1. Define shortcuts
const SHORTCUTS = {
  QUICK_ADD_TODO: "1",
  // ... more
}

// 2. Create handler
const handleKeyDown = (e) => {
  // Check & dispatch
}

// 3. Add to useEffect
useEffect(() => {
  window.addEventListener("keydown", handleKeyDown);
  return () => window.removeEventListener("keydown", handleKeyDown);
}, [dependencies]);
```

### Step 4: Test
- Manual testing with different keys
- Edge cases (modifiers, input focus)
- Performance (no lag on rapid presses)
- Accessibility (focus management, ARIA)

---

## 10. CODEBASE STATISTICS

### Code Distribution
- **Frontend**: ~2,000 lines of TypeScript/TSX
- **Backend**: ~500 lines of Python
- **Configuration**: ~300 lines
- **Total**: ~2,800 lines of code

### Dependencies
- **Frontend**: 30+ npm packages
- **Backend**: 10+ Python packages
- **Total**: 40+ external dependencies

### Component Count
- **Custom Components**: 5 main components
- **UI Components**: 50+ shadcn/ui components
- **Total Reusable Components**: 55+

---

## 11. KEY INSIGHTS FOR SHORTCUTS ENHANCEMENT

### Strengths of Current Implementation
- Clean separation of concerns
- Proper event listener cleanup
- Input field exclusion prevents false triggers
- Toast feedback for UX
- Help panel for discoverability
- Simple, maintainable code

### Improvement Opportunities
- Extract keyboard logic to custom hook
- Centralize shortcut definitions
- Add command palette (library ready)
- Better TypeScript types for keyboard events
- localStorage for custom shortcuts
- Platform detection (Mac Cmd vs Ctrl)
- Keyboard navigation between all elements
- ARIA labels for accessibility

### Best Practices Already in Place
- React hooks usage
- Event cleanup in useEffect
- Error handling with try/catch
- Toast notifications for feedback
- Component composition
- Type safety with TypeScript

---

## 12. FILE LOCATIONS - QUICK REFERENCE

```
Primary Shortcut File:
  /home/user/task-crate/src/components/KanbanBoard.tsx

Secondary Files:
  /home/user/task-crate/src/components/QuickAddTask.tsx

Configuration:
  /home/user/task-crate/vite.config.ts
  /home/user/task-crate/tailwind.config.ts
  /home/user/task-crate/.env

API Layer:
  /home/user/task-crate/src/api/tasks.ts

Type Definitions:
  /home/user/task-crate/src/types/task.ts

UI Components:
  /home/user/task-crate/src/components/ui/ (50+ files)

App Root:
  /home/user/task-crate/src/App.tsx
```

---

## Summary

This is a well-architected **full-stack task management app** with:
- Modern React architecture with TypeScript
- Clean UI using shadcn/ui components
- FastAPI backend with async/await
- Local AI integration via Ollama
- Basic keyboard shortcuts (1, 2, 3, Shift+?)
- Ready-to-enhance with more shortcuts & command palette

**Next Steps for Enhancement:**
1. Extract shortcuts to `src/lib/shortcuts.ts`
2. Create `src/hooks/useKeyboard.ts` hook
3. Implement command palette with `cmdk`
4. Add more shortcuts (Ctrl+N, Ctrl+F, etc.)
5. Build shortcut configuration UI

All required libraries are already installed. The codebase is clean and ready for enhancement!

