# Task-Crate: Text Input & Content Management Analysis

## 1. Frontend Framework Stack

**Framework:** React 18.3.1 with Vite
**UI Framework:** Shadcn/UI (built on Radix UI primitives)
**Styling:** TailwindCSS 3.4.17
**Form Handling:** React Hook Form 7.61.1
**State Management:** Zustand 5.0.8
**Routing:** React Router DOM 6.30.1
**Markdown Support:** React Markdown 10.1.0
**Data Fetching:** TanStack React Query 5.83.0
**Validation:** Zod 3.25.76
**Build Tool:** Vite 5.4.19
**TypeScript:** 5.8.3

## 2. Project Structure Overview

```
src/
├── components/
│   ├── KanbanBoard.tsx          # Main board - task viewing & drag/drop
│   ├── QuickAddTask.tsx         # Quick inline task creation (minimal input)
│   ├── TaskCard.tsx             # Task card display (read-only)
│   ├── TaskDetailSheet.tsx      # Side panel: peek view with full editing
│   ├── TaskFullPage.tsx         # Full page view with expanded UI
│   ├── AIInferenceDialog.tsx    # AI task extraction from text/files
│   ├── AIAssistant.tsx          # Chat-based AI interface
│   ├── LotusDialog.tsx          # Unified task management dialog
│   ├── ChatMessageComponent.tsx # Chat message display (markdown)
│   ├── DocumentUpload.tsx       # Drag-and-drop file upload
│   ├── ValueStreamCombobox.tsx  # Value stream selector/creator
│   └── ui/                      # Shadcn UI components
│       ├── input.tsx            # Base text input
│       ├── textarea.tsx         # Base textarea
│       └── ... (other UI primitives)
├── pages/
│   ├── Index.tsx                # Main page (renders KanbanBoard)
│   └── NotFound.tsx
├── api/
│   └── tasks.ts                 # Backend API client
├── types/
│   └── task.ts                  # TypeScript interfaces
└── hooks/
    └── useChat.ts              # Chat logic hook

```

## 3. Text Input Locations & Components

### 3.1 Task Title Input (Inline Quick Add)

**File:** `/home/user/task-crate/src/components/QuickAddTask.tsx`

```tsx
// Minimal input component for rapid task creation
<Input
  ref={inputRef}
  value={title}
  onChange={(e) => setTitle(e.target.value)}
  onKeyDown={handleKeyDown}
  placeholder="Task title, then press Enter..."
  className="border-0 px-0 h-auto text-[15px] focus-visible:ring-0"
/>
```

**Features:**
- Lightweight single-line input
- Auto-focus on mount
- Enter to submit, Escape to cancel
- Input trimming validation
- Styled as a card with hover effects

---

### 3.2 Task Title Input (Task Detail Sheet & Full Page)

**Files:** 
- `/home/user/task-crate/src/components/TaskDetailSheet.tsx` (Lines 353-362)
- `/home/user/task-crate/src/components/TaskFullPage.tsx` (Lines 159-166)

```tsx
// In TaskDetailSheet - Peek mode
<Input
  value={editedTask.title}
  onChange={(e) => handleUpdate({ title: e.target.value })}
  className={`font-semibold border-0 px-0 focus-visible:ring-0 tracking-tight bg-transparent 
    ${isExpanded ? "text-4xl" : "text-3xl"}`}
  placeholder="Task title"
/>

// In TaskFullPage - Full page view
<Input
  value={editedTask.title}
  onChange={(e) => handleUpdate({ title: e.target.value })}
  className="text-5xl font-bold border-0 px-0 focus-visible:ring-0 tracking-tight bg-transparent h-auto py-2"
  placeholder="Task title"
/>
```

**Features:**
- Border-less input for clean appearance
- Responsive sizing (4xl in expanded, 3xl in peek, 5xl in full page)
- Direct task object update on change
- Auto-formatting and styling

---

### 3.3 Task Description Input

**Files:**
- `/home/user/task-crate/src/components/TaskDetailSheet.tsx` (Lines 459-470)
- `/home/user/task-crate/src/components/TaskFullPage.tsx` (Lines 244-255)

```tsx
// TaskDetailSheet
<Textarea
  value={editedTask.description || ""}
  onChange={(e) => handleUpdate({ description: e.target.value })}
  placeholder="Add a detailed description..."
  rows={isExpanded ? 6 : 4}
  className="resize-none border-border/50 focus:border-primary/50 transition-all duration-500"
/>

// TaskFullPage
<Textarea
  value={editedTask.description || ""}
  onChange={(e) => handleUpdate({ description: e.target.value })}
  placeholder="Add a detailed description..."
  rows={5}
  className="resize-none border-border/50 focus:border-primary/50 transition-all"
/>
```

**Features:**
- Multi-line textarea
- Responsive row count (6 expanded, 4 peek, 5 full page)
- No resizing allowed (resize-none)
- Optional field (uses `||""` fallback)
- Smooth transition effects

---

### 3.4 Task Notes Input (Auto-Expanding Textarea)

**Files:**
- `/home/user/task-crate/src/components/TaskDetailSheet.tsx` (Lines 621-637)
- `/home/user/task-crate/src/components/TaskFullPage.tsx` (Lines 355-368)

```tsx
// TaskDetailSheet - With auto-resize
const handleNotesChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
  handleUpdate({ notes: e.target.value });
  
  // Auto-resize
  const textarea = e.target;
  textarea.style.height = "auto";
  textarea.style.height = textarea.scrollHeight + "px";
};

<Textarea
  ref={notesRef}
  value={editedTask.notes || ""}
  onChange={handleNotesChange}
  placeholder="Write your notes, thoughts, or documentation here..."
  className={`resize-none border-border/30 focus:border-primary/50 
    ${isExpanded ? "min-h-[400px]" : "min-h-[300px]"}`}
  style={{ 
    overflow: "hidden",
    fontFamily: "'Inter', sans-serif"
  }}
/>
```

**Features:**
- Large dedicated area for rich notes
- **Auto-expanding height** based on content
- Keyboard shortcut: `Cmd/Ctrl+D` to focus
- Responsive minimum height (400px expanded, 300px peek)
- Custom font styling (Inter sans-serif)
- Scroll area scrolling handled via JavaScript

---

### 3.5 Comments Input (Chat-Style)

**Files:**
- `/home/user/task-crate/src/components/TaskDetailSheet.tsx` (Lines 600-619)
- `/home/user/task-crate/src/components/TaskFullPage.tsx` (Lines 333-352)

```tsx
// Comment input with Enter to submit
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
  rows={1}
  className="flex-1 resize-none border-0 border-b border-border/30 focus:border-primary/50 
    rounded-none px-0 focus-visible:ring-0 focus-visible:ring-offset-0"
  style={{ minHeight: '28px' }}
/>
```

**Features:**
- Single-line comment input
- Enter to submit, Shift+Enter for new line
- Minimal styling (only bottom border)
- Part of chat-style comment thread
- User avatar + name + timestamp display for each comment
- Comments are immutable (rendered as read-only)

**Comment Structure (Type Definition):**
```tsx
export interface Comment {
  id: string;
  text: string;
  author: string;
  createdAt: string;
}
```

---

### 3.6 Attachment/Link Input

**Files:**
- `/home/user/task-crate/src/components/TaskDetailSheet.tsx` (Lines 526-541)
- `/home/user/task-crate/src/components/TaskFullPage.tsx` (Lines 263-277)

```tsx
// Add attachment URL input
<Input
  value={newAttachment}
  onChange={(e) => setNewAttachment(e.target.value)}
  placeholder="Paste attachment URL..."
  className="h-10 border-border/50 focus:border-primary/50 transition-all"
/>
<Button
  onClick={handleAddAttachment}
  size="sm"
  className="h-10 px-5"
>
  Add
</Button>
```

**Features:**
- Single-line URL input
- Button-based submission
- URL validation (trimming)
- Attachment list display below with delete buttons

---

### 3.7 AI Inference Dialog - Text Input

**File:** `/home/user/task-crate/src/components/AIInferenceDialog.tsx`

```tsx
<Textarea
  value={inputText}
  onChange={(e) => setInputText(e.target.value)}
  placeholder={PLACEHOLDER_TEXT}
  // ... Analysis of text for task extraction
/>
```

**Purpose:** Paste Slack messages, emails, meeting notes for AI to extract tasks

**Placeholder Example:**
```
Paste Slack messages, meeting notes, emails, etc.

Example:
@john We need to update the API docs before Friday.
@sarah Can someone review the auth PR?
Let's schedule a meeting to discuss Q4 roadmap.
```

---

### 3.8 AI Assistant Chat - Text Input

**File:** `/home/user/task-crate/src/components/AIAssistant.tsx`

```tsx
<Textarea
  value={inputValue}
  onChange={(e) => setInputValue(e.target.value)}
  onKeyDown={handleKeyDown}
  placeholder="Paste Slack messages, meeting notes, or tell me what needs to be done..."
  className="min-h-[80px] resize-none"
  disabled={isProcessing}
/>
```

**Features:**
- Source type selector (Manual, Slack, Meeting Transcript, Question)
- Enter to send, Shift+Enter for new line
- Disabled during processing
- Minimum height with no resizing

---

### 3.9 Lotus Dialog - Unified Task Management

**File:** `/home/user/task-crate/src/components/LotusDialog.tsx`

```tsx
const handleSendMessage = async () => {
  if ((!inputValue.trim() && !uploadedFile) || isProcessing) return;

  const content = inputValue.trim();
  setInputValue("");

  // Handle file upload
  if (uploadedFile) {
    await uploadPdfFast(uploadedFile);
  } else {
    // Send as manual message with source type
    await sendMessage(content, sourceType);
  }
};

<Textarea
  value={inputValue}
  onChange={(e) => setInputValue(e.target.value)}
  onKeyDown={handleKeyDown}
  placeholder="Describe tasks, paste messages, or upload documents..."
/>
```

**Features:**
- Combined text + file upload interface
- Source type selection
- Chat-like interaction
- Markdown rendering of responses

---

### 3.10 Document Upload Component

**File:** `/home/user/task-crate/src/components/DocumentUpload.tsx`

```tsx
// Drag-and-drop + click-to-upload
<input
  ref={fileInputRef}
  type="file"
  accept={acceptAttribute}
  onChange={handleFileInput}
  className="hidden"
  disabled={disabled}
/>

<div
  onClick={handleClick}
  onDragOver={handleDragOver}
  onDragLeave={handleDragLeave}
  onDrop={handleDrop}
  className="... drop-zone styling ..."
>
  {/* Visual feedback */}
</div>
```

**Supported File Types:**
- PDF (.pdf)
- Word (.docx, .doc)
- Excel (.xlsx, .xls)
- Markdown (.md)
- Text (.txt)

**Max Size:** 50MB

---

### 3.11 Value Stream Selector/Creator

**File:** `/home/user/task-crate/src/components/ValueStreamCombobox.tsx`

```tsx
// Combobox with inline creation
<Command>
  <CommandInput
    placeholder="Search or create..."
    value={searchValue}
    onValueChange={setSearchValue}
  />
  <CommandList>
    {/* Existing options */}
    {/* Create new option if searchValue doesn't exist */}
  </CommandList>
</Command>
```

**Features:**
- Search existing value streams
- Create new value stream on-the-fly
- Delete value streams with hover action
- Selection persists to task object

---

## 4. Input Component Implementations

### 4.1 Base Input Component

**File:** `/home/user/task-crate/src/components/ui/input.tsx`

```tsx
const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background 
        file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground 
        placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 
        focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 
        md:text-sm",
        className,
      )}
      ref={ref}
      {...props}
    />
  ),
);
```

**Default Styling:**
- Height: 10 units (40px)
- Rounded corners with border
- 2px focus ring with offset
- Placeholder text in muted-foreground color
- Disabled state with reduced opacity

---

### 4.2 Base Textarea Component

**File:** `/home/user/task-crate/src/components/ui/textarea.tsx`

```tsx
const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => (
    <textarea
      className={cn(
        "flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm 
        ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none 
        focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 
        disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      ref={ref}
      {...props}
    />
  ),
);
```

**Default Styling:**
- Minimum height: 80px
- Rounded corners with border
- 2px focus ring with offset
- Placeholder text styling
- Disabled state handling

---

## 5. Task Data Structure

**File:** `/home/user/task-crate/src/types/task.ts`

```tsx
export interface Task {
  id: string;
  title: string;                    // Main task title
  status: TaskStatus;               // "todo" | "doing" | "done"
  assignee: string;                 // Person responsible
  startDate?: string;               // ISO date string
  dueDate?: string;                 // ISO date string
  valueStream?: string;             // Lean value stream
  description?: string;             // Detailed description (textarea)
  attachments: string[];            // URLs to documents/links
  comments: Comment[];              // Thread of comments
  notes?: string;                   // Rich notes field (large textarea)
  createdAt: string;
  updatedAt: string;
}

export interface Comment {
  id: string;
  text: string;                     // Comment content
  author: string;                   // Commenter name
  createdAt: string;
}
```

---

## 6. Text Input Hierarchy & Flow

```
KanbanBoard (Main View)
├── QuickAddTask
│   └── Input (title only)
│
├── TaskCard (Display)
│   └── Read-only display
│
├── TaskDetailSheet (Peek/Extended View)
│   ├── Input (title)
│   ├── Select (status)
│   ├── ValueStreamCombobox (value stream)
│   ├── Input (assignee - expanded only)
│   ├── Input (startDate)
│   ├── Input (dueDate)
│   ├── Textarea (description)
│   ├── DocumentUpload (file upload)
│   ├── Input (attachment URL)
│   ├── Textarea (comments) - Enter to submit
│   └── Textarea (notes) - Auto-expanding, Ctrl+D
│
├── TaskFullPage (Full Screen View)
│   ├── Input (title - large)
│   ├── Select (status)
│   ├── ValueStreamCombobox (value stream)
│   ├── Input (assignee)
│   ├── Input (startDate)
│   ├── Input (dueDate)
│   ├── Textarea (description - large)
│   ├── Input (attachment URL)
│   ├── Textarea (comments) - Enter to submit
│   └── Textarea (notes) - Auto-expanding
│
├── LotusDialog (Unified Management)
│   ├── Textarea (natural language input)
│   └── DocumentUpload (file support)
│
├── AIInferenceDialog (AI Extraction)
│   ├── Textarea (text input for analysis)
│   └── DocumentUpload (file input)
│
└── AIAssistant (Chat Interface)
    ├── Select (source type)
    └── Textarea (message input)
```

---

## 7. Keyboard Shortcuts for Text Editing

### Global Shortcuts in TaskDetailSheet/TaskFullPage:
- **Escape** - Close sheet/page
- **Cmd/Ctrl+E** - Toggle expanded view
- **Cmd/Ctrl+Shift+F** - Full page view
- **Cmd/Ctrl+D** - Focus notes textarea

### Input-Specific Shortcuts:
- **Enter** - Submit (QuickAddTask, Comments)
- **Shift+Enter** - New line (Comments, Chat inputs)
- **Escape** - Cancel QuickAddTask

---

## 8. Backend Integration

**API Endpoint:** `/api` (proxied from backend on port 8000)

### Key API Functions:

```tsx
// Create task
export async function createTask(task: Partial<Task>): Promise<Task>

// Update task
export async function updateTask(taskId: string, updates: Partial<Task>): Promise<Task>

// Delete task
export async function deleteTask(taskId: string): Promise<void>

// AI inference
export async function inferTasksFromText(text: string): Promise<InferenceResponse>
export async function inferTasksFromDocument(file: File): Promise<InferenceResponse>

// Documents
export async function uploadDocument(file: File, category: string, id: string)
export async function listDocuments(category: string, id: string)
```

---

## 9. State Management

**State Management:** Zustand (lightweight React state)

**Key Hooks:**
- `useChat()` - Chat message management
- `useChatMessages()` - Get chat history
- `useIsProcessing()` - Processing state
- `usePendingProposals()` - Task proposals

---

## 10. Current Input Styling & Customizations

### TaskDetailSheet Title Input (Peek Mode):
```tsx
className="font-semibold border-0 px-0 focus-visible:ring-0 tracking-tight bg-transparent text-3xl"
```
- No border (border-0)
- Transparent background
- Large text (3xl)
- No focus ring

### Notes Textarea (Auto-Expanding):
```tsx
style={{ 
  overflow: "hidden",
  fontFamily: "'Inter', sans-serif"
}}
className="resize-none border-border/30 focus:border-primary/50 min-h-[300px]"
```
- Hidden overflow for auto-expansion
- Custom font (Inter)
- No manual resizing
- Minimum 300px height

### Comment Textarea (Chat-Style):
```tsx
className="flex-1 resize-none border-0 border-b border-border/30 focus:border-primary/50 
  rounded-none px-0 focus-visible:ring-0"
style={{ minHeight: '28px' }}
```
- Bottom border only
- Minimal styling
- Tiny min-height (grows as you type)

---

## 11. Markdown & Rich Text Support

**Current Implementation:**
- React Markdown is available (`react-markdown` package)
- Used in ChatMessageComponent for rendering AI responses
- NOT currently used for task notes/descriptions editing
- Comments and notes are plain text only

**Future Enhancement Opportunity:**
- Add markdown preview mode for notes
- Add markdown toolbar for descriptions
- Add markdown syntax highlighting

---

## 12. Summary of Text Input Fields

| Field | Location | Type | Editable | Rich Text | Auto-Expand | Max Size |
|-------|----------|------|----------|-----------|-------------|----------|
| Title | All | Input | Yes | No | No | Unlimited |
| Description | Detail/Full | Textarea | Yes | No | No | 4-6 rows |
| Notes | Detail/Full | Textarea | Yes | No | Yes (JS) | 300-400px min |
| Comments | Detail/Full | Textarea | Yes | No | No (1 row) | 28px min |
| Assignee | Detail/Full | Input | Yes | No | No | Unlimited |
| Start Date | Detail/Full | Input | Yes | No | No | Date format |
| Due Date | Detail/Full | Input | Yes | No | No | Date format |
| Attachments | Detail/Full | Input | Yes | No | No | URL |
| Value Stream | Detail/Full | Combobox | Yes | No | No | Selection |

---

## 13. Files to Modify for Rich Text Support

If you want to add rich text/markdown editing, these are the key files:

1. **TaskDetailSheet.tsx** - Description and Notes textareas
2. **TaskFullPage.tsx** - Description and Notes textareas
3. **ui/textarea.tsx** - Base textarea component
4. **types/task.ts** - Task interface (if adding markdown metadata)

---

## 14. Key Observations

1. **No Rich Text Editor Currently** - Using plain textarea with HTML-escaped content
2. **Markdown Support Available** - `react-markdown` is installed but only used for AI responses
3. **Auto-Expanding Notes** - Custom JavaScript height calculation for notes field
4. **Chat-Style Comments** - Comments are immutable once created, new comments are appended
5. **Responsive Layouts** - Different input sizes for peek vs. expanded vs. full page views
6. **Keyboard-Centric** - Multiple shortcuts for power users
7. **Validation Minimal** - Mostly relies on trimming, no format validation
8. **Async Updates** - All changes immediately update local state and sync with backend

