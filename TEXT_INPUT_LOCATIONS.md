# Text Input Locations - Quick Reference

## File Locations & Line Numbers

### Task Title Input Locations

| Location | File | Lines | Component |
|----------|------|-------|-----------|
| Quick Add (Inline) | `QuickAddTask.tsx` | 41-48 | Input element |
| Detail Sheet Peek | `TaskDetailSheet.tsx` | 353-362 | Input element (3xl) |
| Detail Sheet Expanded | `TaskDetailSheet.tsx` | 353-362 | Input element (4xl) |
| Full Page | `TaskFullPage.tsx` | 159-166 | Input element (5xl) |

**Code Pattern:**
```tsx
<Input
  value={editedTask.title}
  onChange={(e) => handleUpdate({ title: e.target.value })}
  className="border-0 px-0 focus-visible:ring-0 bg-transparent"
/>
```

---

### Description Input Locations

| Location | File | Lines | Rows |
|----------|------|-------|------|
| Detail Sheet Peek | `TaskDetailSheet.tsx` | 459-470 | 4 |
| Detail Sheet Expanded | `TaskDetailSheet.tsx` | 459-470 | 6 |
| Full Page | `TaskFullPage.tsx` | 244-255 | 5 |

**Code Pattern:**
```tsx
<Textarea
  value={editedTask.description || ""}
  onChange={(e) => handleUpdate({ description: e.target.value })}
  placeholder="Add a detailed description..."
  rows={isExpanded ? 6 : 4}
  className="resize-none"
/>
```

---

### Notes Input Locations (Auto-Expanding)

| Location | File | Lines | Min Height |
|----------|------|-------|-----------|
| Detail Sheet Peek | `TaskDetailSheet.tsx` | 621-637 | 300px |
| Detail Sheet Expanded | `TaskDetailSheet.tsx` | 621-637 | 400px |
| Full Page | `TaskFullPage.tsx` | 355-368 | 400px |

**Special Handler:** `handleNotesChange()` at lines 214-221 in TaskDetailSheet.tsx

**Code Pattern:**
```tsx
const handleNotesChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
  handleUpdate({ notes: e.target.value });
  
  // Auto-resize JavaScript
  const textarea = e.target;
  textarea.style.height = "auto";
  textarea.style.height = textarea.scrollHeight + "px";
};

<Textarea
  ref={notesRef}
  value={editedTask.notes || ""}
  onChange={handleNotesChange}
  style={{ overflow: "hidden" }}
  className="min-h-[300px]"
/>
```

---

### Comments Input Locations

| Location | File | Lines | Style |
|----------|------|-------|-------|
| Detail Sheet | `TaskDetailSheet.tsx` | 600-619 | Chat-style, bottom border |
| Full Page | `TaskFullPage.tsx` | 333-352 | Chat-style, bottom border |

**Special Handler:** `handleAddComment()` at lines 144-159 in TaskDetailSheet.tsx

**Code Pattern:**
```tsx
const handleAddComment = () => {
  const trimmedComment = newComment.trim();
  if (!trimmedComment) return;

  const comment: Comment = {
    id: crypto.randomUUID(),
    text: trimmedComment,
    author: editedTask.assignee,
    createdAt: new Date().toISOString(),
  };

  handleUpdate({ comments: [...editedTask.comments, comment] });
  setNewComment("");
};

<Textarea
  value={newComment}
  onChange={(e) => setNewComment(e.target.value)}
  onKeyDown={(e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAddComment();
    }
  }}
  placeholder="Add a comment..."
  className="border-0 border-b"
  style={{ minHeight: '28px' }}
/>
```

---

### Attachment/Link Input Locations

| Location | File | Lines |
|----------|------|-------|
| Detail Sheet | `TaskDetailSheet.tsx` | 526-541 |
| Full Page | `TaskFullPage.tsx` | 263-277 |

**Special Handler:** `handleAddAttachment()` at lines 161-169 in TaskDetailSheet.tsx

**Code Pattern:**
```tsx
<Input
  value={newAttachment}
  onChange={(e) => setNewAttachment(e.target.value)}
  placeholder="Paste attachment URL..."
/>
<Button onClick={handleAddAttachment}>Add</Button>
```

---

### AI & Chat Inputs

| Name | File | Lines | Purpose |
|------|------|-------|---------|
| AIInferenceDialog | `AIInferenceDialog.tsx` | ~40-100 | Text extraction |
| AIAssistant Chat | `AIAssistant.tsx` | 180-188 | Chat interface |
| LotusDialog Chat | `LotusDialog.tsx` | ~80-150 | Unified management |

---

### Document Upload

| File | Lines | Features |
|------|-------|----------|
| `DocumentUpload.tsx` | Full | Drag-drop + click, 50MB max |

**Supported Types:** PDF, Word, Excel, Markdown, Text

---

### Value Stream Selector

| File | Lines |
|------|-------|
| `ValueStreamCombobox.tsx` | Full (200 lines) |

**Features:** Search, create new, delete existing

---

## Base Components

### Input Component

**File:** `/home/user/task-crate/src/components/ui/input.tsx`

```tsx
const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base",
        className,
      )}
      ref={ref}
      {...props}
    />
  ),
);
```

### Textarea Component

**File:** `/home/user/task-crate/src/components/ui/textarea.tsx`

```tsx
const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => (
    <textarea
      className={cn(
        "flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
        className,
      )}
      ref={ref}
      {...props}
    />
  ),
);
```

---

## Task Data Structure

**File:** `/home/user/task-crate/src/types/task.ts`

```tsx
export interface Task {
  id: string;
  title: string;              // ← Text Input
  status: TaskStatus;
  assignee: string;
  startDate?: string;
  dueDate?: string;
  valueStream?: string;
  description?: string;       // ← Textarea Input
  attachments: string[];      // ← URL Input (multiple)
  comments: Comment[];        // ← Textarea Input (multiple)
  notes?: string;             // ← Textarea Input (auto-expanding)
  createdAt: string;
  updatedAt: string;
}

export interface Comment {
  id: string;
  text: string;              // ← Text from Textarea
  author: string;
  createdAt: string;
}
```

---

## Update Functions

All changes use `handleUpdate()` function:

**In TaskDetailSheet.tsx (Lines 134-142):**
```tsx
const handleUpdate = (updates: Partial<Task>) => {
  const updated = { 
    ...editedTask, 
    ...updates, 
    updatedAt: new Date().toISOString() 
  };
  setEditedTask(updated);
  onUpdate(updated);  // Propagates to parent (KanbanBoard)
};
```

**In TaskFullPage.tsx (Lines 64-72):** Same pattern

---

## Keyboard Shortcuts

### In TaskDetailSheet/TaskFullPage:
- **Escape** → Close panel/page
- **Cmd/Ctrl+E** → Toggle expanded view
- **Cmd/Ctrl+Shift+F** → Open full page view
- **Cmd/Ctrl+D** → Focus notes textarea (line 122-126 in TaskDetailSheet)

### In Text Inputs:
- **Enter** → Submit (QuickAddTask, Comments)
- **Shift+Enter** → New line (Comments, Chat)
- **Escape** → Cancel (QuickAddTask)

---

## API Functions

**File:** `/home/user/task-crate/src/api/tasks.ts`

```tsx
// Create task
export async function createTask(task: Partial<Task>): Promise<Task> {
  // POST /api/tasks
}

// Update task
export async function updateTask(taskId: string, updates: Partial<Task>): Promise<Task> {
  // PUT /api/tasks/{taskId}
}

// Delete task
export async function deleteTask(taskId: string): Promise<void> {
  // DELETE /api/tasks/{taskId}
}

// AI inference
export async function inferTasksFromText(text: string): Promise<InferenceResponse> {
  // POST /api/infer
}

export async function inferTasksFromDocument(file: File): Promise<InferenceResponse> {
  // POST /api/infer/document
}
```

---

## State Management

**Primary State Management:** Local React state in each component

**Zustand Hooks** (in AIAssistant/LotusDialog):
- `useChat()` - Send messages
- `useChatMessages()` - Get chat history
- `useIsProcessing()` - Processing state
- `usePendingProposals()` - Task proposals

---

## File Tree - Text Input Related

```
src/
├── components/
│   ├── QuickAddTask.tsx                    [41-48] Input: task title
│   ├── TaskDetailSheet.tsx                 [353-362] Input: title
│   │                                       [459-470] Textarea: description
│   │                                       [600-619] Textarea: comments
│   │                                       [621-637] Textarea: notes (auto-expand)
│   │                                       [526-541] Input: attachments
│   │                                       [214-221] Handler: auto-resize notes
│   │                                       [144-159] Handler: add comment
│   │                                       [161-169] Handler: add attachment
│   │
│   ├── TaskFullPage.tsx                    [159-166] Input: title (large)
│   │                                       [244-255] Textarea: description
│   │                                       [333-352] Textarea: comments
│   │                                       [355-368] Textarea: notes
│   │                                       [263-277] Input: attachments
│   │                                       [107-114] Handler: auto-resize notes
│   │                                       [74-89] Handler: add comment
│   │                                       [91-99] Handler: add attachment
│   │
│   ├── AIInferenceDialog.tsx               [39-100] Textarea: text for AI
│   ├── AIAssistant.tsx                     [180-188] Textarea: chat input
│   ├── LotusDialog.tsx                     [75-150] Textarea: unified input
│   ├── DocumentUpload.tsx                  [144-187] File drop zone
│   ├── ValueStreamCombobox.tsx             [152-156] CommandInput: search/create
│   ├── ChatMessageComponent.tsx            [75-77] Markdown rendering
│   │
│   └── ui/
│       ├── input.tsx                       [6-18] Base Input component
│       └── textarea.tsx                    [8-18] Base Textarea component
│
├── api/
│   └── tasks.ts                            [59-116] CRUD functions
│
└── types/
    └── task.ts                             [3-16] Task interface with text fields
```

---

## Current Limitations & Future Opportunities

### Current:
- No rich text editor (plain textarea only)
- No markdown editing UI (available as library but not used)
- No syntax highlighting
- No text formatting toolbar
- No drag-resize for textareas
- Limited validation (trim only)

### Opportunities:
1. Add markdown editor (e.g., Slate, ProseMirror, or simple toolbar)
2. Add rich text formatting (bold, italic, links)
3. Add markdown preview mode
4. Add syntax highlighting for code blocks
5. Add spell check integration
6. Add auto-save drafts
7. Add text length limit UI
8. Add mention/tag support (@user)
9. Add emoji picker
10. Add undo/redo support

---

## Component Props & Interfaces

**TaskDetailSheet Props:**
```tsx
interface TaskDetailSheetProps {
  task: Task;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUpdate: (task: Task) => void;
  onDelete: (taskId: string) => void;
  isExpanded?: boolean;
  onToggleExpanded?: () => void;
  onFullPage?: () => void;
}
```

**TaskFullPage Props:**
```tsx
interface TaskFullPageProps {
  task: Task;
  onUpdate: (task: Task) => void;
  onDelete: (taskId: string) => void;
  onClose: () => void;
}
```

**DocumentUpload Props:**
```tsx
interface DocumentUploadProps {
  onFileSelect: (file: File) => void;
  onFileRemove?: () => void;
  maxSizeBytes?: number;
  acceptedTypes?: string[];
  className?: string;
  selectedFile?: File | null;
  disabled?: boolean;
  showFileInfo?: boolean;
}
```

