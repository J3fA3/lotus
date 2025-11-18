# Task-Crate Text Input Analysis - Executive Summary

## Quick Overview

This project is a **React 18 + Vite + Shadcn UI** task management application with comprehensive text input capabilities across multiple interfaces. All text content (tasks, descriptions, notes, comments) is stored as plain text in a PostgreSQL/SQLite backend.

## Key Findings

### 1. Frontend Framework
- **React 18.3.1** with TypeScript
- **Vite 5** as build tool
- **Shadcn/UI** component library (Radix UI + TailwindCSS)
- **React Router** for navigation
- **Zustand** for state management (minimal)
- **React Markdown** available but only used for AI responses

### 2. Text Input Locations (11 Total)

| # | Field | Components | Type | Auto-Expand |
|---|-------|-----------|------|------------|
| 1 | Task Title | QuickAddTask, TaskDetailSheet, TaskFullPage | Input | No |
| 2 | Description | TaskDetailSheet, TaskFullPage | Textarea | No |
| 3 | Notes | TaskDetailSheet, TaskFullPage | Textarea | Yes (JS) |
| 4 | Comments | TaskDetailSheet, TaskFullPage | Textarea | No (1-row) |
| 5 | Assignee | TaskDetailSheet, TaskFullPage | Input | No |
| 6 | Attachment URLs | TaskDetailSheet, TaskFullPage | Input | No |
| 7 | Start Date | TaskDetailSheet, TaskFullPage | Input (date) | No |
| 8 | Due Date | TaskDetailSheet, TaskFullPage | Input (date) | No |
| 9 | AI Text Input | AIInferenceDialog | Textarea | No |
| 10 | Chat Input | AIAssistant, LotusDialog | Textarea | No |
| 11 | Value Stream | ValueStreamCombobox | CommandInput | No |

### 3. Three Main Views

**QuickAddTask** (Inline)
- Single-line title input
- Enter to create, Escape to cancel
- Minimal styling

**TaskDetailSheet** (Side Panel)
- Peek mode: 600px wide, compact layouts
- Expanded mode: 900px wide, extra fields visible
- All fields editable
- Auto-expanding notes textarea

**TaskFullPage** (Full Screen)
- Larger fonts (title: 5xl vs 3xl)
- Larger textareas
- Same fields as detail sheet

### 4. Special Features

**Auto-Expanding Notes:**
```tsx
// Lines 214-221 in TaskDetailSheet.tsx
const handleNotesChange = (e) => {
  handleUpdate({ notes: e.target.value });
  const textarea = e.target;
  textarea.style.height = "auto";
  textarea.style.height = textarea.scrollHeight + "px";
};
```

**Chat-Style Comments:**
- Enter to submit, Shift+Enter for new line
- Immutable comment display
- User avatar, timestamp, author
- New comment textarea appears below

**Document Upload:**
- Drag-and-drop + click support
- Supports: PDF, Word, Excel, Markdown, Text
- Max 50MB per file
- Files associated with tasks

### 5. Data Model

**Task Interface:**
```typescript
interface Task {
  id: string;
  title: string;              // Text Input
  status: "todo" | "doing" | "done";
  assignee: string;           // Text Input
  startDate?: string;         // Date Input
  dueDate?: string;           // Date Input
  valueStream?: string;       // Selection
  description?: string;       // Textarea
  attachments: string[];      // URL Input (multiple)
  comments: Comment[];        // Textarea Input (thread)
  notes?: string;             // Textarea Input (auto-expand)
  createdAt: string;
  updatedAt: string;
}

interface Comment {
  id: string;
  text: string;               // Textarea Input
  author: string;
  createdAt: string;
}
```

### 6. Update Flow

```
User Types → onChange Event
         ↓
    handleUpdate(changes)
         ↓
    setEditedTask(updated) [Instant UI update]
         ↓
    onUpdate(task) [Callback to parent]
         ↓
    KanbanBoard updates tasks[]
         ↓
    updateTask(id, changes) [API call]
         ↓
    Backend saves to database
```

**Note:** Updates are optimistic - no error feedback if API fails.

### 7. Keyboard Shortcuts

**Task Detail View:**
- `Escape` → Close panel/page
- `Cmd/Ctrl+E` → Toggle expanded mode
- `Cmd/Ctrl+Shift+F` → Open full page view
- `Cmd/Ctrl+D` → Focus notes textarea

**Text Input:**
- `Enter` → Submit (QuickAddTask, Comments)
- `Shift+Enter` → New line (Comments, Chat)
- `Escape` → Cancel (QuickAddTask)

### 8. Base Components

**Input Component** (`ui/input.tsx`):
```tsx
// Single-line text input
// Default height: 40px
// Focus ring: 2px offset
// Inherits form styling from TailwindCSS
```

**Textarea Component** (`ui/textarea.tsx`):
```tsx
// Multi-line text input
// Min height: 80px
// Focus ring: 2px offset
// Inherits form styling from TailwindCSS
```

### 9. Rich Text Support

**Current State:**
- Plain text only (no markdown editing)
- React Markdown available but unused for editing
- HTML auto-escaped in database

**Available for Future Use:**
- `react-markdown` (10.1.0) installed
- Could add markdown editor (Slate, ProseMirror, etc.)
- Could add toolbar for formatting
- Could add preview mode

### 10. API Integration

**Endpoints:**
- `POST /api/tasks` - Create task
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task
- `POST /api/infer` - AI text analysis
- `POST /api/documents` - File upload

**State:**
- Tasks stored in component state (local)
- API calls use optimistic updates
- No caching layer

### 11. Key Files

| File | Lines | Purpose |
|------|-------|---------|
| TaskDetailSheet.tsx | 645 | Main edit interface (side panel) |
| TaskFullPage.tsx | 373 | Full screen task view |
| QuickAddTask.tsx | 62 | Quick inline creation |
| DocumentUpload.tsx | 232 | File upload + validation |
| ValueStreamCombobox.tsx | 201 | Value stream selector |
| ui/input.tsx | 22 | Base text input |
| ui/textarea.tsx | 21 | Base textarea |
| api/tasks.ts | 200+ | API client |
| types/task.ts | 70 | TypeScript interfaces |

### 12. Styling Patterns

**Pattern 1: Borderless Title**
```tsx
className="border-0 px-0 focus-visible:ring-0 bg-transparent text-3xl"
```
Used for main task title in detail views

**Pattern 2: Standard Field**
```tsx
className="border-border/50 focus:border-primary/50 transition-all"
```
Used for description, dates, assignee

**Pattern 3: Auto-Expanding**
```tsx
style={{ overflow: "hidden" }}
className="resize-none min-h-[300px]"
```
Used for notes field with JS height calculation

**Pattern 4: Chat-Style**
```tsx
className="border-0 border-b resize-none px-0"
style={{ minHeight: '28px' }}
```
Used for comment input (minimal, grows on type)

### 13. Component Hierarchy

```
KanbanBoard (Main)
├── QuickAddTask [title input]
├── TaskDetailSheet [all editable fields]
│   ├── Input [title]
│   ├── Textarea [description]
│   ├── Textarea [notes]
│   ├── Textarea [comments]
│   ├── Input [assignee, dates]
│   ├── DocumentUpload [file upload]
│   └── Input [attachment URL]
├── TaskFullPage [larger version]
└── AIInferenceDialog [text analysis]

Separate Dialogs:
├── AIAssistant [chat interface]
└── LotusDialog [unified management]
```

### 14. Current Limitations

1. **No Rich Text Editor** - Plain text only
2. **No Markdown Editing UI** - React Markdown not used for input
3. **No Syntax Highlighting** - Code blocks render as plain text
4. **No Text Formatting Toolbar** - No bold, italic, links UI
5. **No Drag-Resize** - Textareas not resizable by user
6. **Minimal Validation** - Only trimming, no length limits
7. **No Undo/Redo** - Changes are immediate and permanent
8. **No Spell Check** - No spell checking integration
9. **No Mentions** - No @user or #tag support
10. **No Auto-Save** - Must submit changes manually

### 15. Future Enhancement Opportunities

**Quick Wins:**
- Add character count display
- Add max length validation UI
- Add debounced auto-save
- Add "unsaved changes" warning

**Medium Effort:**
- Add markdown preview mode
- Add simple formatting toolbar
- Add spell check (Grammarly API)
- Add @mention support with user lookup

**Advanced:**
- Add rich text editor (Slate, ProseMirror)
- Add collaborative editing (Yjs)
- Add real-time multiplayer updates
- Add version history/time travel
- Add media embedding (images, videos)
- Add table support in notes

### 16. Developer Notes

**To Add a New Text Input:**
1. Create state variable: `const [newField, setNewField] = useState("");`
2. Create handler: `const handleNewFieldChange = (e) => setNewField(e.target.value);`
3. Add to Task interface in `types/task.ts`
4. Add JSX: `<Input value={newField} onChange={handleNewFieldChange} />`
5. Update `handleUpdate()` call with new field
6. Add to API update payload

**To Add Rich Text:**
1. Install editor: `npm install slate react-markdown`
2. Replace Textarea with editor component
3. Store as JSON/markdown instead of plain text
4. Update rendering to parse markdown
5. Update API to handle markdown

**To Add Auto-Save:**
1. Add debounce to handleUpdate (500ms)
2. Show "Saving..." indicator
3. Show "Saved" on success
4. Show error toast on failure
5. Consider adding version history

### 17. Testing Checklist

- [ ] Type in title field → Updates display
- [ ] Type in description → Trim whitespace works
- [ ] Type in notes → Auto-expand height works
- [ ] Add comment → Enter submits, Shift+Enter new line
- [ ] Add attachment → URL trimmed and added
- [ ] Upload file → Drag-drop and click both work
- [ ] Change date → Calendar picker or text input works
- [ ] Change status → Dropdown updates
- [ ] Create new value stream → Inline creation works
- [ ] Keyboard shortcuts → Escape/Ctrl+D/Ctrl+E work
- [ ] On mobile → Responsive layouts work

### 18. File Locations (at a Glance)

```
/home/user/task-crate/
├── src/
│   ├── components/
│   │   ├── TaskDetailSheet.tsx          ← Main edit interface
│   │   ├── TaskFullPage.tsx             ← Full screen view
│   │   ├── QuickAddTask.tsx             ← Quick add
│   │   ├── DocumentUpload.tsx           ← File upload
│   │   ├── ValueStreamCombobox.tsx      ← Selector
│   │   ├── AIAssistant.tsx              ← Chat input
│   │   ├── LotusDialog.tsx              ← Unified dialog
│   │   └── ui/
│   │       ├── input.tsx                ← Base input
│   │       └── textarea.tsx             ← Base textarea
│   ├── api/
│   │   └── tasks.ts                     ← API client
│   └── types/
│       └── task.ts                      ← Data models
└── [Documentation Files]
    ├── TEXT_INPUT_ANALYSIS.md           ← Comprehensive guide
    ├── TEXT_INPUT_LOCATIONS.md          ← Quick reference
    └── TEXT_INPUT_ARCHITECTURE.md       ← Visual diagrams
```

---

## How to Use This Analysis

1. **TEXT_INPUT_ANALYSIS.md** - Start here for comprehensive details
2. **TEXT_INPUT_LOCATIONS.md** - Use for quick file lookups
3. **TEXT_INPUT_ARCHITECTURE.md** - Use for understanding data flows

---

## Summary

The Task-Crate application uses a modern React stack with Shadcn UI components for text input. Text is stored as plain text in a backend database with optimistic UI updates. The architecture is clean and extensible, with clear separation between data models, components, and API calls. There's significant opportunity to enhance the text editing experience with rich text support, markdown editing, and collaborative features.

**Total Text Input Interfaces:** 11
**Main Components:** TaskDetailSheet, TaskFullPage, QuickAddTask
**Key Feature:** Auto-expanding notes textarea with JavaScript height calculation
**Rich Text Support:** Available (React Markdown) but not actively used

---

Generated: 2024-11-18
Framework: React 18.3.1 + Vite 5.4.19
UI Library: Shadcn/UI (Radix UI + TailwindCSS 3.4.17)
State Management: Zustand 5.0.8 (minimal), React hooks
Backend Integration: REST API on port 8000
