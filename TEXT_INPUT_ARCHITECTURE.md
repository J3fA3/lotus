# Text Input Visual Guide & Architecture

## 1. Component Hierarchy for Text Input

```
App (Root)
└── Index.tsx
    └── KanbanBoard.tsx (Main View - Kanban Board)
        ├── QuickAddTask.tsx
        │   └── Input (title)
        │       ├── onChange: Update local state
        │       ├── onKeyDown: Enter/Escape handling
        │       └── Submit: createTask(title)
        │
        ├── TaskCard.tsx (Read-Only Display)
        │   └── Shows task.title, task.dueDate, task.comments.length
        │
        ├── TaskDetailSheet.tsx (Slide-Out Panel)
        │   ├── Input: title (size: 3xl or 4xl based on expanded)
        │   │
        │   ├── Textarea: description (rows: 4 or 6)
        │   │
        │   ├── Textarea: notes (min-h: 300px or 400px)
        │   │   └── Special: Auto-expanding height
        │   │       └── handleNotesChange() → scroll-height calculation
        │   │
        │   ├── Textarea: comments (min-h: 28px)
        │   │   ├── Displays existing comments (immutable)
        │   │   └── Input area for new comments
        │   │       └── Submit on Enter (no Shift)
        │   │
        │   ├── Input: assignee (show in expanded mode)
        │   │
        │   ├── Input: startDate (type="date")
        │   │
        │   ├── Input: dueDate (type="date")
        │   │
        │   ├── Input: newAttachment URL
        │   │   └── Button: Add → handleAddAttachment()
        │   │
        │   └── DocumentUpload (Drag-Drop Zone)
        │
        ├── TaskFullPage.tsx (Full Screen View)
        │   └── [Same inputs as TaskDetailSheet but larger]
        │       ├── title: text-5xl
        │       ├── description: rows=5
        │       └── notes: min-h-[400px]
        │
        ├── AIInferenceDialog.tsx
        │   ├── Textarea: inputText (AI analysis)
        │   └── DocumentUpload
        │       └── inferTasksFromText() / inferTasksFromDocument()
        │
        ├── AIAssistant.tsx
        │   ├── Select: sourceType (manual/slack/transcript/question)
        │   ├── Textarea: inputValue
        │   └── useChat() hook
        │       └── sendMessage()
        │
        └── LotusDialog.tsx
            ├── Textarea: inputValue
            ├── DocumentUpload
            └── useChat() hook
                └── uploadPdfFast() / sendMessage()
```

---

## 2. Data Flow Diagram (Single Task Edit)

```
User Types in Input
        ↓
onChange Event Fired
        ↓
handleUpdate(updates) → TaskDetailSheet.tsx:134-142
        ↓
    setEditedTask(updated)  [Local State]
        ↓
    onUpdate(updated)        [Callback to Parent (KanbanBoard)]
        ↓
KanbanBoard Updates tasks[] State
        ↓
updateTask(taskId, updates) → API Call
        ↓
Backend: PUT /api/tasks/{taskId}
        ↓
Response: Updated Task
        ↓
Task Displayed in UI
```

### Auto-Expanding Notes Special Flow:

```
User Types in Notes Textarea
        ↓
onChange → handleNotesChange()  [TaskDetailSheet:214-221]
        ↓
┌─ handleUpdate({ notes: value })  [Update state + backend]
│
└─ textarea.style.height = "auto"  [Reset height]
        ↓
  textarea.style.height = scrollHeight + "px"  [Set new height]
        ↓
Textarea Grows to Fit Content
```

---

## 3. Comment System Flow

```
User Submits Comment in Textarea
        ↓
onKeyDown → Check if Enter && !Shift
        ↓
handleAddComment()  [TaskDetailSheet:144-159]
        ↓
Create Comment Object {
  id: crypto.randomUUID(),
  text: trimmedComment,
  author: editedTask.assignee,
  createdAt: new Date().toISOString()
}
        ↓
handleUpdate({ comments: [...editedTask.comments, comment] })
        ↓
Comments Array Updated in State
        ↓
setNewComment("")  [Clear input]
        ↓
UI Re-renders with New Comment in List
        ↓
Old Comments Display as Read-Only
New Input Textarea Appears Below
```

---

## 4. Text Input Component Styling Patterns

### Pattern 1: Border-Less Large Title
```
TaskDetailSheet/TaskFullPage Title Input

className="border-0 px-0 focus-visible:ring-0 tracking-tight bg-transparent"
        +
fontSize: 3xl (peek), 4xl (expanded), or 5xl (full page)

Result: Clean, minimal title editing
```

### Pattern 2: Standard Field with Label
```
Description/Dates/Assignee Inputs

<Label>Field Name</Label>
<Input|Textarea>
  className="border-border/50 focus:border-primary/50 transition-all"

Result: Standard form-like appearance
```

### Pattern 3: Auto-Expanding Notes
```
Notes Textarea

className="resize-none min-h-[300px|400px]"
style={{ overflow: "hidden", fontFamily: "'Inter', sans-serif" }}

+ JavaScript Height Calculation:
  textarea.style.height = textarea.scrollHeight + "px"

Result: Growing textarea that expands with content
```

### Pattern 4: Chat-Style Comment Input
```
Comment Textarea

className="border-0 border-b border-border/30 rounded-none px-0"
style={{ minHeight: '28px' }}

Result: Minimal single-line input that grows on demand
```

### Pattern 5: Inline Input + Button
```
Attachment URL Input

<Input value={newAttachment} />
<Button onClick={handleAddAttachment}>Add</Button>

Result: Simple entry + submit pattern
```

---

## 5. State Management Architecture

```
Component: TaskDetailSheet
│
├─ State Variables:
│  ├─ editedTask: Task (full object)
│  ├─ newComment: string
│  ├─ newAttachment: string
│  ├─ isExpanded: boolean
│  ├─ uploadedDocuments: Document[]
│  └─ selectedDocumentFile: File | null
│
├─ Effects:
│  ├─ useEffect → Watch `task` prop
│  │  └─ Update editedTask (sync with parent)
│  │
│  ├─ useEffect → Watch `open` prop
│  │  └─ Keyboard shortcuts setup
│  │
│  └─ useEffect → Watch `open && task.id`
│     └─ Load task documents
│
├─ Event Handlers:
│  ├─ handleUpdate(updates)
│  │  └─ Updates local state + calls onUpdate callback
│  │
│  ├─ handleAddComment()
│  │  └─ Creates Comment object, updates state
│  │
│  ├─ handleAddAttachment()
│  │  └─ Adds URL to attachments array
│  │
│  ├─ handleNotesChange(event)
│  │  └─ Updates state + auto-resize calculation
│  │
│  └─ Document handlers
│     ├─ handleDocumentUpload()
│     ├─ loadTaskDocuments()
│     └─ handleDocumentDeleted()
│
└─ Props (from KanbanBoard):
   ├─ task: Task
   ├─ open: boolean
   ├─ onOpenChange: (open: boolean) => void
   ├─ onUpdate: (task: Task) => void
   ├─ onDelete: (taskId: string) => void
   ├─ isExpanded?: boolean
   ├─ onToggleExpanded?: () => void
   └─ onFullPage?: () => void
```

---

## 6. Keyboard Shortcut Flow

```
User Presses Key
        ↓
Window KeyDown Listener
  [TaskDetailSheet.tsx:88-132]
        ↓
Check Key Combination
│
├─ Escape → onOpenChange(false)  [Close panel]
│
├─ Cmd/Ctrl+E → Toggle Expanded
│   └─ onToggleExpanded() or setIsExpanded(!isExpanded)
│
├─ Cmd/Ctrl+Shift+F → Full Page View
│   └─ onFullPage()
│
├─ Cmd/Ctrl+D → Focus Notes
│   └─ notesRef.current?.focus()
│   └─ scrollIntoView({ behavior: "smooth" })
│
└─ Enter (in Comment/Chat) → Submit
    └─ handleAddComment() / handleSendMessage()
```

---

## 7. AI Text Processing Pipeline

```
User Pastes Text into AIInferenceDialog
        ↓
Click "Analyze" Button
        ↓
inferTasksFromText(inputText)  [api/tasks.ts:146-180]
        ↓
POST /api/infer
  headers: { "Content-Type": "application/json" }
  body: { text: inputText, assignee: DEFAULT_ASSIGNEE }
        ↓
Backend ML Model Analyzes Text
        ↓
Returns InferenceResponse {
  tasks: Task[],
  inference_time_ms: number,
  model_used: string,
  tasks_inferred: number
}
        ↓
Frontend Shows Results
        ↓
User Approves/Rejects Tasks
        ↓
Tasks Added to KanbanBoard
        ↓
Dialog Closes
```

---

## 8. File Upload Pipeline

```
User Drags PDF onto DocumentUpload Component
        ↓
onDrop Handler
  [DocumentUpload.tsx:97-111]
        ↓
handleFileSelection(file)
        ↓
validateFile(file)
  ├─ Check size (max 50MB)
  └─ Check type (PDF/Word/Excel/MD/txt)
        ↓
onFileSelect(file)  [Callback to parent]
        ↓
Parent Component Stores File State
        ↓
User Clicks "Upload Document"
        ↓
uploadDocument(file, "tasks", taskId)
        ↓
FormData {
  file: File,
  category: "tasks",
  id: taskId
}
        ↓
POST /api/documents
        ↓
Backend Processes & Stores File
        ↓
Response: DocumentUploadResponse {
  document: Document,
  message: string
}
        ↓
Frontend Updates uploadedDocuments State
        ↓
Document Appears in "Attached Documents" List
```

---

## 9. Real-Time Sync Flow

```
User Makes Change in TaskDetailSheet
        ↓
handleUpdate(updates) Called
        ↓
setEditedTask(updated)  [Instant local update]
        ↓
UI Updates Immediately
        ↓
onUpdate(updated) Called
        ↓
KanbanBoard Updates tasks[] Array
        ↓
updateTask(taskId, updates) API Call (Fire & Forget)
        ↓
Backend Saves to Database
        ↓
⚠️ No Feedback - Optimistic Update
   (If API fails, user doesn't see an error)
```

---

## 10. Component Size Responsiveness

### Title Input Sizing:
```
QuickAddTask:           text-base (normal)
TaskDetailSheet Peek:   text-3xl
TaskDetailSheet Expand: text-4xl
TaskFullPage:           text-5xl
```

### Description Textarea Rows:
```
TaskDetailSheet Peek:   rows={4}
TaskDetailSheet Expand: rows={6}
TaskFullPage:           rows={5}
```

### Notes Textarea Min Height:
```
TaskDetailSheet Peek:   min-h-[300px]
TaskDetailSheet Expand: min-h-[400px]
TaskFullPage:           min-h-[400px]
```

---

## 11. Input Validation Rules

### Current Implementation:
```javascript
// Title
const trimmedTitle = title.trim();
if (trimmedTitle) { /* Submit */ }
// Rule: Non-empty after trimming

// Comment
const trimmedComment = newComment.trim();
if (!trimmedComment) { return; }
// Rule: Non-empty after trimming

// Attachment
const trimmedUrl = newAttachment.trim();
if (!trimmedUrl) { return; }
// Rule: Non-empty after trimming

// File Upload
validateFile(file) {
  if (file.size > maxSizeBytes) { /* Error */ }
  if (!isSupportedDocumentType(file.name)) { /* Error */ }
  return null; // Valid
}
// Rules: Size limit + type check
```

---

## 12. Task Object State Transition

```
Initial State:
{
  id: "task-123",
  title: "Original Title",
  status: "todo",
  description: null,
  notes: null,
  comments: [],
  attachments: [],
  assignee: "You"
}

User Edits Title
        ↓
Updated State:
{
  ...
  title: "Updated Title",
  updatedAt: "2024-11-18T..." ← Auto-updated
}

User Adds Comment
        ↓
Updated State:
{
  ...
  comments: [
    {
      id: "uuid",
      text: "My comment",
      author: "You",
      createdAt: "2024-11-18T..."
    }
  ]
}

User Adds Attachment
        ↓
Updated State:
{
  ...
  attachments: ["https://example.com/file.pdf"]
}

User Adds Note
        ↓
Updated State:
{
  ...
  notes: "This is a note..."
}
```

---

## 13. Error Handling Patterns

```
User Action
        ↓
Try {
  API Call (fetch, validate, etc.)
} Catch (error) {
  Log to console
  toast.error(error.message)
  Return early or set error state
}

Example:
loadValueStreams() {
  try {
    const streams = await fetchValueStreams();
    setValueStreams(streams);
  } catch (error) {
    console.error("Failed to load:", error);
    toast.error("Failed to load value streams");
  }
}
```

---

## 14. Performance Optimizations

### Current:
- Local state updates are instant (optimistic)
- No debouncing on input changes
- Full re-render on each keystroke

### Potential Improvements:
- Debounce API calls (500ms) during typing
- Use useCallback for handler functions
- Memoize large textarea contents
- Consider virtual scrolling for comment lists

---

## 15. Accessibility Considerations

### Current:
- Input/Textarea have proper focus rings
- Keyboard shortcuts support accessibility
- Labels associated with inputs
- Placeholder text provides context

### Could Improve:
- Add ARIA labels for custom inputs
- Add error announcements for screen readers
- Add skip navigation links
- Test with accessibility tools (axe, WAVE)

---

## 16. Mobile Responsiveness

### TaskDetailSheet:
```
Desktop:  w-full sm:max-w-[600px] (peek)
          w-full sm:max-w-[900px] (expanded)

Mobile:   w-full (full screen)

Layout:   Responsive grid (auto-adjust columns)
```

### DocumentUpload:
```
min-h-[160px] on all sizes
Responsive padding
Touch-friendly button sizes
```

### Comments:
```
flex gap-3 wraps on mobile
User avatar scales
Comment text responsive
```

