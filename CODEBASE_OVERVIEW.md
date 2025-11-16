# AI Task Inference Codebase - Comprehensive Overview

## 1. TECH STACK & FRAMEWORK

### Frontend
- **Framework**: React 18.3 with TypeScript 5.8
- **Build Tool**: Vite 5.4
- **Routing**: React Router v6.30
- **UI Component Library**: shadcn/ui (Radix UI + Tailwind CSS)
- **Styling**: Tailwind CSS 3.4 with custom design system (HSL-based)
- **Form Management**: React Hook Form 7.61
- **Data Fetching**: TanStack React Query 5.83
- **Notifications**: Sonner 1.7 & Custom Toast System
- **Date Handling**: date-fns 3.6
- **Command Palette**: cmdk 1.1 (installed but not currently used)
- **Drag & Drop**: @hello-pangea/dnd 18.0 (installed, basic drag-drop implemented)
- **Icons**: Lucide React 0.462
- **Dev Tools**: Lovable Tagger, ESLint 9.32, TypeScript ESLint

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLite with async support (SQLAlchemy ORM)
- **AI Integration**: Ollama with Qwen 2.5 (7B Instruct model)
- **PDF Processing**: PyMuPDF
- **Server**: Uvicorn with async context management

### Infrastructure
- **API Communication**: REST API with CORS support
- **Dev Container**: Devcontainer configuration included
- **Environment**: .env configuration support

---

## 2. EXISTING SHORTCUTS & IMPLEMENTATION

### Current Keyboard Shortcuts (in KanbanBoard.tsx)
```typescript
KEYBOARD_SHORTCUTS = {
  TODO: "1",      // Quick add to To-Do column
  DOING: "2",     // Quick add to In Progress column
  DONE: "3",      // Quick add to Done column
  HELP: "?",      // Toggle shortcuts help (Shift+?)
}
```

### Implementation Details
**Location**: `/home/user/task-crate/src/components/KanbanBoard.tsx` (lines 20-25, 86-117)

- Global keyboard event listener using `useEffect`
- Ignores input when user is typing in inputs/textareas
- Uses `window.addEventListener('keydown', handleKeyDown)`
- Toast notifications for feedback (via Sonner)
- Shortcuts help display (collapsible UI panel)

### QuickAddTask Component Keyboard Handling
**Location**: `/home/user/task-crate/src/components/QuickAddTask.tsx` (lines 31-36)
- **Escape**: Cancel quick add and close form
- **Enter**: Submit task (from form submit handler)

### No Command Palette Yet
- `cmdk` library is installed but **not currently implemented**
- No command/palette system exists yet
- This is a good opportunity to enhance shortcuts with a command palette

---

## 3. MAIN UI COMPONENTS

### Core Components Layout
```
Frontend (src/components/)
├── KanbanBoard.tsx          - Main Kanban board component
│   ├── 3-column layout (To-Do, In Progress, Done)
│   ├── Drag-drop functionality
│   ├── Global keyboard shortcuts
│   ├── AI inference integration
│   └── Task management (CRUD)
│
├── TaskCard.tsx             - Individual task card
│   ├── Title, status badge
│   ├── Due dates, value stream
│   ├── Comment/attachment indicators
│   └── Drag-drop support
│
├── TaskDetailDialog.tsx      - Full task editor dialog
│   ├── Title, description
│   ├── Status (select dropdown)
│   ├── Dates (start, due)
│   ├── Value stream, assignee
│   ├── Comments section
│   ├── Attachments section
│   └── Delete button
│
├── QuickAddTask.tsx         - Quick task creation form
│   ├── Auto-focused input
│   ├── Enter to submit, Esc to cancel
│   └── Minimal UI for inline adding
│
├── AIInferenceDialog.tsx    - AI task extraction dialog
│   ├── Text paste tab
│   ├── PDF upload tab
│   ├── Processing UI with loader
│   └── Result display
│
└── ui/                      - shadcn/ui components (50+ components)
    ├── Dialog, Button, Input, Textarea
    ├── Select, Tabs, Badge, Card
    ├── Toast, Alert, Skeleton
    └── And 40+ more...
```

### Component Hierarchy
```
App (src/App.tsx)
└── QueryClientProvider + TooltipProvider + Sonner Toaster
    └── BrowserRouter
        └── Routes
            └── Index (src/pages/Index.tsx)
                └── KanbanBoard
                    ├── 3-column layout
                    │   ├── TaskCard (multiple)
                    │   │   └── onClick -> TaskDetailDialog
                    │   └── QuickAddTask (when adding)
                    ├── AIInferenceDialog
                    └── TaskDetailDialog (modal)
```

### Key UI Properties
- **Design System**: "Zen" palette with warm neutrals + subtle green accent
- **Color Scheme**: HSL-based (CSS variables)
- **Responsive**: Mobile-first, Tailwind CSS breakpoints
- **Shadows**: Custom zen-sm, zen-md shadow utilities
- **Border Radius**: 0.875rem default
- **Transitions**: Smooth 0.3s cubic-bezier transitions

---

## 4. CONFIGURATION SYSTEM

### Frontend Configuration

#### Environment Variables
**File**: `/home/user/task-crate/.env`
```env
VITE_API_BASE_URL=/api
```

#### Vite Configuration
**File**: `vite.config.ts`
- Server port: 8080
- API proxy: Forwards `/api` requests to `http://localhost:8000`
- Development sourcemaps enabled
- Code splitting for vendor & UI bundles
- Path alias: `@` → `./src`

#### Tailwind Configuration
**File**: `tailwind.config.ts`
- Dark mode: Class-based
- Custom color palette (HSL variables)
- Custom shadows: `shadow-zen-sm`, `shadow-zen-md`
- Extended theme with sidebar colors
- Transition utilities
- Accordion animations

#### Components Configuration
**File**: `components.json` (shadcn/ui config)
- Style: Default (Radix UI)
- Aliases:
  - `@/components` → components dir
  - `@/ui` → ui components
  - `@/hooks` → custom hooks
  - `@/utils` → utilities
  - `@/lib` → library

### Backend Configuration

#### Environment Variables
**Default values** in `backend/main.py`:
```python
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b-instruct"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_CORS_ORIGINS = "http://localhost:5173"
API_HOST = "0.0.0.0"
API_PORT = 8000
DEBUG = true
```

#### Configuration Constants
**File**: `backend/main.py`
- API Title, Description, Version
- CORS origins configuration
- Lifespan management (startup/shutdown hooks)
- Ollama model and URL setup

---

## 5. OVERALL ARCHITECTURE

### Full Architecture Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                     WEB BROWSER                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ React Application (Vite Dev Server @ :8080)             ││
│  │                                                           ││
│  │  App.tsx                                                 ││
│  │  ├── React Router                                        ││
│  │  ├── TanStack Query Client                              ││
│  │  ├── Tooltip Provider                                   ││
│  │  └── Toast Provider (Sonner)                            ││
│  │      │                                                  ││
│  │      └── Index (/)                                      ││
│  │          └── KanbanBoard (Main Component)               ││
│  │              ├── Global Keyboard Shortcuts              ││
│  │              ├── 3-Column Kanban                        ││
│  │              │   └── TaskCard × N                       ││
│  │              ├── TaskDetailDialog (Modal)               ││
│  │              ├── QuickAddTask (Form)                    ││
│  │              └── AIInferenceDialog (Modal)              ││
│  │                                                          ││
│  └──────────────────────────────────────────────────────────┘│
│                                                               │
│  HTTP/REST API (via /api proxy)                             │
│  ↓                                                            │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Backend (Port 8000)                                │
│  ├── CORS Middleware                                        │
│  └── API Routes (/api prefix)                              │
│      ├── GET /health                                       │
│      ├── GET /tasks                                        │
│      ├── POST /tasks                                       │
│      ├── GET /tasks/{id}                                   │
│      ├── PUT /tasks/{id}                                   │
│      ├── DELETE /tasks/{id}                                │
│      ├── POST /infer-tasks (text)                         │
│      └── POST /infer-tasks-pdf (file upload)              │
│          ↓                                                  │
│      ┌─────────────────────────────────────────┐          │
│      │  AI Task Extraction Layer                │          │
│      │  ├── TaskExtractor                      │          │
│      │  │   └── Calls Ollama API              │          │
│      │  └── PDFProcessor                       │          │
│      │      └── Extracts text from PDF        │          │
│      │          └── Sends to TaskExtractor    │          │
│      └─────────────────────────────────────────┘          │
│          ↓                                                  │
│      ┌─────────────────────────────────────────┐          │
│      │  Ollama (LLM Server)                    │          │
│      │  Model: qwen2.5:7b-instruct            │          │
│      │  URL: http://localhost:11434           │          │
│      └─────────────────────────────────────────┘          │
│                                                             │
│  Database Layer                                            │
│  └── SQLAlchemy ORM (async)                               │
│      ├── Task Model                                        │
│      ├── Comment Model                                     │
│      ├── Attachment Model                                 │
│      └── InferenceHistory Model                           │
│          ↓                                                 │
│      SQLite Database                                      │
│      (File-based persistence)                             │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow for Task Creation
```
1. User presses "1" key (keyboard shortcut)
2. KanbanBoard.handleKeyDown() triggers
3. Shows QuickAddTask form for "todo" column
4. User types task title + presses Enter
5. handleQuickAddTask() called
6. POST /api/tasks with task data
7. Backend creates task in SQLite
8. Response returns created task with ID
9. Frontend updates state
10. UI re-renders with new card
```

### Data Flow for AI Task Inference
```
1. User clicks "AI Infer Tasks" button
2. AIInferenceDialog opens
3. User pastes text or uploads PDF
4. User clicks "Infer Tasks"
5. Frontend POST /api/infer-tasks (or /api/infer-tasks-pdf)
6. Backend PDFProcessor extracts text (if PDF)
7. Backend TaskExtractor sends to Ollama
8. Ollama (Qwen 2.5) processes text
9. Returns extracted tasks (with titles, descriptions)
10. Backend returns InferenceResponse to frontend
11. Frontend adds tasks to board
12. UI updates with new cards
13. Toast notification shows results
```

### Component Integration Points

#### State Management
- **React local state** (useState in components)
- **TanStack Query** (planned/installed but minimal use)
- **Context**: TooltipProvider, QueryClientProvider

#### API Integration
- **File**: `src/api/tasks.ts`
- **Functions**: 
  - `fetchTasks()` - GET all tasks
  - `createTask()` - POST new task
  - `updateTask()` - PUT task updates
  - `deleteTask()` - DELETE task
  - `inferTasksFromText()` - POST text for inference
  - `inferTasksFromPDF()` - POST file for inference
  - `checkHealth()` - GET health status

#### Notifications
- **Sonner Toast**: Success/error messages
- **Toast Hook**: Fallback system
- **Duration**: SHORT (2s), MEDIUM (3s), LONG (5s)

---

## 6. KEY FILES REFERENCE

### Frontend Core
- `/src/App.tsx` - Root app component
- `/src/pages/Index.tsx` - Main page wrapper
- `/src/types/task.ts` - Task & Comment interfaces
- `/src/api/tasks.ts` - API client functions
- `/src/lib/utils.ts` - Utility functions (cn() for class merging)

### Main Components
- `/src/components/KanbanBoard.tsx` - **PRIMARY - Main board & shortcuts**
- `/src/components/TaskDetailDialog.tsx` - Full task editor
- `/src/components/TaskCard.tsx` - Individual task display
- `/src/components/QuickAddTask.tsx` - Quick add form
- `/src/components/AIInferenceDialog.tsx` - AI inference UI

### Hooks
- `/src/hooks/use-toast.ts` - Custom toast system
- `/src/hooks/use-mobile.tsx` - Mobile detection hook

### UI Components (shadcn/ui)
- `/src/components/ui/` - 50+ pre-built components
  - button, card, dialog, input, select, tabs, etc.
  - All Radix UI based with Tailwind styling

### Configuration
- `/vite.config.ts` - Vite build & dev config
- `/tailwind.config.ts` - Tailwind CSS config
- `/tsconfig.json` - TypeScript config
- `/components.json` - shadcn/ui config
- `.env` - Environment variables

### Backend
- `/backend/main.py` - FastAPI app setup & config
- `/backend/api/routes.py` - API endpoint definitions
- `/backend/api/schemas.py` - Request/response schemas
- `/backend/db/database.py` - Database setup
- `/backend/db/models.py` - SQLAlchemy models
- `/backend/agents/task_extractor.py` - Ollama integration
- `/backend/agents/pdf_processor.py` - PDF text extraction

---

## 7. EXPANSION OPPORTUNITIES FOR SHORTCUTS

### Current Limitations
- Only 4 shortcuts (1, 2, 3, Shift+?)
- No command palette
- No shortcut configuration UI
- No shortcut discovery/help dialog
- Limited keyboard navigation
- No modifier key support beyond Shift

### Recommended Enhancements
1. **Command Palette** (use installed `cmdk` library)
   - Ctrl+K / Cmd+K to open
   - Fuzzy search commands
   - Recent commands
   - Command categories

2. **More Shortcuts**
   - Ctrl+N: New task dialog
   - Ctrl+F: Search/filter tasks
   - Ctrl+E: Edit selected task
   - Tab: Navigate between columns
   - Arrow keys: Navigate cards
   - D: Delete task
   - M: Move task
   - C: Add comment

3. **Configuration System**
   - Store in localStorage
   - Custom shortcut mapping UI
   - Preset profiles (Vim mode, Emacs mode, etc.)

4. **Shortcut Help UI**
   - Better formatted help modal
   - Categories (Navigation, Creation, Editing, etc.)
   - Search help text
   - Platform-aware (Mac Cmd vs Ctrl)

### Code Architecture for Shortcuts
```typescript
// Suggested structure
src/lib/shortcuts.ts          - Shortcut configuration
src/hooks/useKeyboard.ts      - Reusable keyboard hook
src/components/CommandPalette.tsx - New command palette
src/config/keybindings.ts     - Default & custom bindings
```

