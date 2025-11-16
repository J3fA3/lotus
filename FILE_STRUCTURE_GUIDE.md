# Complete File Structure & Quick Reference Guide

## Project Directory Tree

```
task-crate/
├── 📄 package.json                    # Frontend dependencies & scripts
├── 📄 tsconfig.json                   # TypeScript configuration
├── 📄 vite.config.ts                  # Vite build config (port 8080, proxy to :8000)
├── 📄 tailwind.config.ts              # Tailwind CSS config with Zen design system
├── 📄 components.json                 # shadcn/ui component configuration
├── 📄 eslint.config.js                # ESLint rules
├── 📄 postcss.config.js               # PostCSS config
├── 📄 .env                            # Frontend environment variables (API_BASE_URL)
├── 📄 .env.example                    # Example env file
├── 📄 .gitignore                      # Git ignore rules
├── 📄 README.md                       # Project README
├── 📄 index.html                      # HTML entry point
│
├── 📁 public/                         # Static assets
├── 📁 scripts/                        # Shell scripts (start-backend.sh, etc.)
├── 📁 .devcontainer/                  # Dev container configuration
├── 📁 docs/                           # Documentation files
│
├── 📁 src/                            # FRONTEND SOURCE CODE
│   ├── 📄 main.tsx                    # React entry point (ReactDOM.createRoot)
│   ├── 📄 index.css                   # Global styles + CSS variable definitions
│   ├── 📄 vite-env.d.ts               # Vite type definitions
│   │
│   ├── 📄 App.tsx                     # Root app component ⭐
│   │   └── Contains: QueryClientProvider, BrowserRouter, Routes
│   │
│   ├── 📁 pages/
│   │   ├── 📄 Index.tsx               # Main page (renders KanbanBoard)
│   │   └── 📄 NotFound.tsx            # 404 page
│   │
│   ├── 📁 components/                 # MAIN UI COMPONENTS
│   │   ├── 📄 KanbanBoard.tsx         # ⭐ PRIMARY - Kanban board + KEYBOARD SHORTCUTS
│   │   │   ├─ Global keyboard event listener
│   │   │   ├─ Shortcuts: 1, 2, 3, Shift+?
│   │   │   ├─ 3-column layout (Todo, Doing, Done)
│   │   │   ├─ Drag & drop support
│   │   │   ├─ AI inference integration
│   │   │   └─ Task CRUD operations
│   │   │
│   │   ├── 📄 TaskCard.tsx            # Individual task card display
│   │   │   └─ Click opens TaskDetailDialog
│   │   │
│   │   ├── 📄 TaskDetailDialog.tsx    # Task editor dialog (modal)
│   │   │   ├─ Title, description, dates
│   │   │   ├─ Status dropdown
│   │   │   ├─ Comments & attachments
│   │   │   └─ Delete functionality
│   │   │
│   │   ├── 📄 QuickAddTask.tsx        # Quick add form
│   │   │   ├─ Enter: Submit
│   │   │   └─ Esc: Cancel
│   │   │
│   │   ├── 📄 AIInferenceDialog.tsx   # AI task extraction dialog
│   │   │   ├─ Text paste tab
│   │   │   └─ PDF upload tab
│   │   │
│   │   ├── 📄 NavLink.tsx             # Navigation link component
│   │   │
│   │   └── 📁 ui/                    # shadcn/ui COMPONENTS (50+ files)
│   │       ├── 📄 button.tsx
│   │       ├── 📄 card.tsx
│   │       ├── 📄 dialog.tsx
│   │       ├── 📄 input.tsx
│   │       ├── 📄 select.tsx
│   │       ├── 📄 tabs.tsx
│   │       ├── 📄 badge.tsx
│   │       ├── 📄 toast.tsx
│   │       ├── 📄 tooltip.tsx
│   │       ├── 📄 dropdown-menu.tsx
│   │       ├── 📄 context-menu.tsx
│   │       ├── 📄 command.tsx          # NOT CURRENTLY USED (installed via cmdk)
│   │       └── ... (40+ more UI components)
│   │
│   ├── 📁 hooks/                     # CUSTOM HOOKS
│   │   ├── 📄 use-toast.ts           # Custom toast management hook
│   │   └── 📄 use-mobile.tsx         # Mobile detection hook
│   │
│   ├── 📁 types/                     # TypeScript type definitions
│   │   └── 📄 task.ts                # Task & Comment interfaces
│   │
│   ├── 📁 api/                       # API CLIENT LAYER
│   │   └── 📄 tasks.ts               # API functions (fetch, create, update, delete)
│   │
│   └── 📁 lib/                       # UTILITIES
│       └── 📄 utils.ts               # Helper functions (cn() for tailwind merging)
│
└── 📁 backend/                        # BACKEND SOURCE CODE (Python FastAPI)
    ├── 📄 main.py                     # FastAPI app setup + config ⭐
    │   ├─ Server: http://0.0.0.0:8000
    │   ├─ CORS configuration
    │   ├─ Lifespan management
    │   └─ Ollama model configuration
    │
    ├── 📁 api/
    │   ├── 📄 routes.py               # API endpoints ⭐
    │   │   ├─ GET /health
    │   │   ├─ GET/POST /tasks
    │   │   ├─ PUT/DELETE /tasks/{id}
    │   │   ├─ POST /infer-tasks
    │   │   └─ POST /infer-tasks-pdf
    │   │
    │   └── 📄 schemas.py              # Request/response schemas (Pydantic)
    │
    ├── 📁 db/
    │   ├── 📄 database.py             # SQLAlchemy setup + async session
    │   ├── 📄 models.py               # Task, Comment, Attachment, InferenceHistory models
    │   └── 📄 __init__.py
    │
    ├── 📁 agents/
    │   ├── 📄 task_extractor.py       # Calls Ollama for task extraction
    │   ├── 📄 pdf_processor.py        # PyMuPDF for PDF text extraction
    │   ├── 📄 prompts.py              # Prompts for Ollama
    │   └── 📄 __init__.py
    │
    └── 📄 __init__.py

```

---

## Important File Paths for Shortcuts Enhancement

### Most Important Files

1. **KEYBOARD SHORTCUTS MAIN FILE**
   - Path: `/home/user/task-crate/src/components/KanbanBoard.tsx`
   - What: Contains all current shortcuts (1, 2, 3, Shift+?)
   - Lines: 20-25 (constants), 86-117 (handler), 254-274 (UI)

2. **QUICK ADD FORM SHORTCUTS**
   - Path: `/home/user/task-crate/src/components/QuickAddTask.tsx`
   - What: Enter to submit, Esc to cancel
   - Lines: 31-36 (handler)

3. **CONFIGURATION FILES**
   - Vite: `/home/user/task-crate/vite.config.ts`
   - Tailwind: `/home/user/task-crate/tailwind.config.ts`
   - Env: `/home/user/task-crate/.env`

4. **API INTEGRATION**
   - Path: `/home/user/task-crate/src/api/tasks.ts`
   - What: All API call functions

5. **TYPE DEFINITIONS**
   - Path: `/home/user/task-crate/src/types/task.ts`
   - What: Task & Comment interfaces

### Files to Create for Enhancement

Suggested new files:
```
src/lib/shortcuts.ts              # Shortcut configuration & constants
src/hooks/useKeyboard.ts          # Reusable keyboard handling hook
src/hooks/useShortcuts.ts         # Shortcuts-specific hook
src/components/CommandPalette.tsx # Command palette component
src/config/keybindings.ts         # Keyboard binding presets
src/lib/keyboard-utils.ts         # Keyboard event utilities
```

---

## Code Snippets Quick Reference

### Getting Toast Notifications
```typescript
import { toast } from "sonner";

// Show success
toast.success("Message", { duration: 2000 });

// Show error
toast.error("Error message");

// Show info
toast.info("Info message");

// Show warning
toast.warning("Warning message");
```

### Creating State for UI
```typescript
const [state, setState] = useState<Type>(initialValue);

// Usage in keyboard handler
const [quickAddColumn, setQuickAddColumn] = useState<TaskStatus | null>(null);
```

### Keyboard Event Listener
```typescript
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter") {
      // Handle
    }
  };

  window.addEventListener("keydown", handleKeyDown);
  return () => window.removeEventListener("keydown", handleKeyDown);
}, [dependencies]);
```

### Component Conditional Rendering
```typescript
{condition && (
  <Component />
)}
```

### API Calls
```typescript
import * as tasksApi from "@/api/tasks";

// Fetch
const tasks = await tasksApi.fetchTasks();

// Create
const newTask = await tasksApi.createTask({
  title: "Task",
  status: "todo",
  assignee: "You"
});

// Update
await tasksApi.updateTask(taskId, { status: "done" });

// Delete
await tasksApi.deleteTask(taskId);
```

### Styling with Tailwind
```typescript
// Classes can be combined
className="bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary/90"

// Using cn() utility for dynamic classes
import { cn } from "@/lib/utils";

const buttonClass = cn(
  "base-classes",
  isActive && "active-classes",
  isDisabled && "disabled-classes"
);
```

### Task Type Definition
```typescript
export type TaskStatus = "todo" | "doing" | "done";

export interface Task {
  id: string;
  title: string;
  status: TaskStatus;
  assignee: string;
  startDate?: string;
  dueDate?: string;
  valueStream?: string;
  description?: string;
  attachments: string[];
  comments: Comment[];
  createdAt: string;
  updatedAt: string;
}
```

---

## Key Constants & Configurations

### Toast Durations
```typescript
const TOAST_DURATION = {
  SHORT: 2000,    // 2 seconds
  MEDIUM: 3000,   // 3 seconds
  LONG: 5000,     // 5 seconds
}
```

### Task Statuses
```typescript
const COLUMNS: { id: TaskStatus; title: string }[] = [
  { id: "todo", title: "To-Do" },
  { id: "doing", title: "In Progress" },
  { id: "done", title: "Done" },
];
```

### API Base URL
```typescript
// Frontend uses environment variable
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

// In .env
VITE_API_BASE_URL=/api

// In vite.config.ts - proxy forwards to
target: "http://localhost:8000"
```

### Server Ports
- Frontend: 8080 (Vite dev server)
- Backend: 8000 (FastAPI)
- Ollama: 11434 (default)

---

## Dependencies Installed for Shortcuts

### Already Available (Use These!)
- `cmdk` (1.1.1) - Command palette library - NOT YET IMPLEMENTED
- `react-router-dom` (6.30.1) - Navigation
- `sonner` (1.7.4) - Toast notifications
- `lucide-react` (0.462.0) - Icons
- `@radix-ui/*` - Base UI components
- `tailwindcss` (3.4.17) - Styling

### Package.json Entry
```json
"dependencies": {
  "cmdk": "^1.1.1",
  "sonner": "^1.7.4",
  "react": "^18.3.1",
  "react-dom": "^18.3.1",
  ...
}
```

---

## Environment Setup

### Frontend Environment
```env
# .env file
VITE_API_BASE_URL=/api
```

### Backend Environment
```python
# Defaults in main.py
OLLAMA_MODEL = "qwen2.5:7b-instruct"
OLLAMA_BASE_URL = "http://localhost:11434"
API_HOST = "0.0.0.0"
API_PORT = 8000
DEBUG = true
CORS_ORIGINS = "http://localhost:5173"
```

---

## Testing & Development Commands

```bash
# Frontend
npm install          # Install dependencies
npm run dev         # Start dev server (port 8080)
npm run build       # Build for production
npm run lint        # Run ESLint

# Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py      # Start backend (port 8000)

# Full Stack
./start-backend.sh  # Terminal 1
./start-frontend.sh # Terminal 2
```

