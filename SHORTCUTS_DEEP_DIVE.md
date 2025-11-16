# Keyboard Shortcuts - Deep Dive & Code Reference

## Current Shortcut Implementation

### File Location & Code
**Primary File**: `/home/user/task-crate/src/components/KanbanBoard.tsx`

#### Constants Definition (Lines 20-31)
```typescript
const KEYBOARD_SHORTCUTS = {
  TODO: "1",
  DOING: "2",
  DONE: "3",
  HELP: "?",
} as const;

const TOAST_DURATION = {
  SHORT: 2000,
  MEDIUM: 3000,
  LONG: 5000,
} as const;
```

#### State Variables (Lines 34-42)
```typescript
const [tasks, setTasks] = useState<Task[]>([]);
const [selectedTask, setSelectedTask] = useState<Task | null>(null);
const [isDialogOpen, setIsDialogOpen] = useState(false);
const [draggedTask, setDraggedTask] = useState<Task | null>(null);
const [quickAddColumn, setQuickAddColumn] = useState<TaskStatus | null>(null);
const [showShortcuts, setShowShortcuts] = useState(false);    // Controls shortcuts display
const [isAIDialogOpen, setIsAIDialogOpen] = useState(false);
const [isLoading, setIsLoading] = useState(true);
const [backendConnected, setBackendConnected] = useState(false);
```

#### Keyboard Event Handler (Lines 86-117)
```typescript
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    // Ignore if user is typing in an input
    if (e.target instanceof HTMLInputElement || 
        e.target instanceof HTMLTextAreaElement) {
      return;
    }

    const { key, shiftKey } = e;

    // Quick add shortcuts
    if (key === KEYBOARD_SHORTCUTS.TODO) {
      e.preventDefault();
      setQuickAddColumn("todo");
      toast.success("Quick add: To-Do", { duration: TOAST_DURATION.SHORT });
    } else if (key === KEYBOARD_SHORTCUTS.DOING) {
      e.preventDefault();
      setQuickAddColumn("doing");
      toast.success("Quick add: In Progress", { duration: TOAST_DURATION.SHORT });
    } else if (key === KEYBOARD_SHORTCUTS.DONE) {
      e.preventDefault();
      setQuickAddColumn("done");
      toast.success("Quick add: Done", { duration: TOAST_DURATION.SHORT });
    } else if (key === KEYBOARD_SHORTCUTS.HELP && shiftKey) {
      e.preventDefault();
      setShowShortcuts(!showShortcuts);
    }
  };

  window.addEventListener("keydown", handleKeyDown);
  return () => window.removeEventListener("keydown", handleKeyDown);
}, [showShortcuts]);
```

#### Shortcuts Display UI (Lines 254-274)
```typescript
{showShortcuts && (
  <div className="mb-6 p-4 bg-muted/30 border border-border/30 rounded-xl">
    <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">
      Keyboard Shortcuts
    </h3>
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
      <div className="flex items-center gap-2">
        <kbd className="px-2 py-1 bg-background border border-border rounded text-[10px] font-mono">1</kbd>
        <span className="text-muted-foreground">Quick add to To-Do</span>
      </div>
      <div className="flex items-center gap-2">
        <kbd className="px-2 py-1 bg-background border border-border rounded text-[10px] font-mono">2</kbd>
        <span className="text-muted-foreground">Quick add to In Progress</span>
      </div>
      <div className="flex items-center gap-2">
        <kbd className="px-2 py-1 bg-background border border-border rounded text-[10px] font-mono">3</kbd>
        <span className="text-muted-foreground">Quick add to Done</span>
      </div>
    </div>
  </div>
)}
```

### Secondary Shortcuts: QuickAddTask Component
**File**: `/home/user/task-crate/src/components/QuickAddTask.tsx` (Lines 31-36)

```typescript
const handleKeyDown = (e: React.KeyboardEvent) => {
  if (e.key === "Escape") {
    e.preventDefault();
    onCancel();
  }
};

return (
  <form onSubmit={handleSubmit} className="group">
    <div className="relative bg-card border border-primary/30 rounded-xl p-3 shadow-zen-sm hover:shadow-zen-md transition-all duration-300">
      <Input
        ref={inputRef}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onKeyDown={handleKeyDown}  // Escape handling
        placeholder="Task title, then press Enter..."
        className="border-0 px-0 h-auto text-[15px] focus-visible:ring-0 placeholder:text-muted-foreground/50"
      />
      ...
    </div>
    <p className="text-[10px] text-muted-foreground mt-1.5 ml-1 font-light">
      Press Enter to add • Esc to cancel
    </p>
  </form>
);
```

---

## Keyboard Event Flow Diagram

```
User Press Key
  ↓
window.addEventListener('keydown', handleKeyDown)
  ↓
Check: Is target HTMLInput/HTMLTextArea?
  ├─ YES → Return (ignore)
  └─ NO → Continue
  ↓
Extract: key, shiftKey from event
  ↓
Key Matching Logic:
  ├─ key === "1" → setQuickAddColumn("todo") → toast
  ├─ key === "2" → setQuickAddColumn("doing") → toast
  ├─ key === "3" → setQuickAddColumn("done") → toast
  └─ key === "?" && shiftKey → toggleShowShortcuts()
  ↓
Component Re-renders
  ├─ If quickAddColumn set → Show QuickAddTask form
  ├─ If showShortcuts true → Show shortcuts panel
  └─ Toasts shown via Sonner provider
  ↓
Form Submission (when in QuickAddTask):
  ├─ User types text
  ├─ User presses Enter
  ├─ handleSubmit triggers
  ├─ Calls handleQuickAddTask()
  ├─ POST /api/tasks
  ├─ Update state with new task
  └─ Toast success
```

---

## State Management for Shortcuts

### Related State Variables
```typescript
// UI State
const [quickAddColumn, setQuickAddColumn] = useState<TaskStatus | null>(null);
const [showShortcuts, setShowShortcuts] = useState(false);

// Task State (affected by shortcuts)
const [tasks, setTasks] = useState<Task[]>([]);
const [selectedTask, setSelectedTask] = useState<Task | null>(null);

// Dialog State
const [isDialogOpen, setIsDialogOpen] = useState(false);
const [isAIDialogOpen, setIsAIDialogOpen] = useState(false);
```

### State Transitions
```
Shortcut "1" Pressed
  → setQuickAddColumn("todo")
  → Conditional render shows QuickAddTask for "todo"
  → User types + presses Enter
  → handleQuickAddTask("todo", title)
  → API call creates task
  → setTasks([...prev, newTask])
  → setQuickAddColumn(null)
  → Form disappears, new task card appears
```

---

## Toast Notification System

### Implementation Details
**File**: `src/hooks/use-toast.ts` (Custom implementation)
**Also uses**: `sonner` library for notifications

### Usage in Shortcuts
```typescript
toast.success("Quick add: To-Do", { duration: TOAST_DURATION.SHORT });
toast.success("Quick add: In Progress", { duration: TOAST_DURATION.SHORT });
toast.success("Quick add: Done", { duration: TOAST_DURATION.SHORT });
```

### Toast Durations
- SHORT: 2000ms (2 seconds) - Used for quick feedback
- MEDIUM: 3000ms (3 seconds)
- LONG: 5000ms (5 seconds)

---

## Component Dependencies for Shortcuts

### Imports Required
```typescript
import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { Button } from "./ui/button";
import { Plus, Keyboard, Sparkles, Loader2 } from "lucide-react";
```

### Props/Dependencies
```typescript
// Toast notifications
const toast = require('sonner').toast;

// Types
import { Task, TaskStatus } from "@/types/task";

// API
import * as tasksApi from "@/api/tasks";

// Hooks
useEffect, useState, useCallback
```

---

## Shortcut Testing Checklist

### Manual Testing
- [ ] Press "1" - Should show quick add for To-Do
- [ ] Press "2" - Should show quick add for In Progress
- [ ] Press "3" - Should show quick add for Done
- [ ] Press Shift+? - Should toggle shortcuts panel
- [ ] Press key while in input field - Should NOT trigger shortcut
- [ ] In quick add form, press Escape - Should close form
- [ ] In quick add form, press Enter - Should submit task
- [ ] Toast should appear/disappear at correct times

### Edge Cases
- [ ] Rapidly press same key multiple times
- [ ] Press key while form is already open
- [ ] Press key in different columns
- [ ] Test on mobile (might not have physical keyboard)
- [ ] Test with different keyboard layouts

---

## Accessibility Considerations

### Current Implementation
- Uses semantic keyboard events
- Provides visual feedback (toast + UI)
- Ignores shortcuts in inputs/textareas
- Help panel shows all shortcuts
- kbd HTML elements for visual styling

### Missing Accessibility Features
- No ARIA labels for shortcuts
- No focus management
- No keyboard navigation between elements
- No screen reader announcements
- No visible focus indicators on cards

---

## Integration with Other Features

### Drag & Drop
- Keyboard shortcuts independent of drag-drop
- Different code paths
- Could enhance with keyboard shortcuts for moving items

### AI Inference
- Separate button click (not keyboard)
- Could add Ctrl+I shortcut

### Task Detail Dialog
- Opened by clicking task card
- Could add shortcut to open focused task

### API Calls
- Shortcuts trigger API calls via `handleQuickAddTask`
- All API errors handled with toast notifications
- Backend health checked on component mount

---

## Performance Considerations

### Event Listener Management
```typescript
useEffect(() => {
  window.addEventListener("keydown", handleKeyDown);
  return () => window.removeEventListener("keydown", handleKeyDown);
}, [showShortcuts]);  // Re-registers when showShortcuts changes
```

- Good: Cleanup function removes listener
- Note: Dependency on showShortcuts causes re-registration

### Toast Performance
- Uses Sonner library (optimized)
- Maximum 1 toast at a time (TOAST_LIMIT = 1)
- Auto-dismiss after duration

---

## Browser Compatibility

### Supported
- Modern browsers with KeyboardEvent API
- All major browsers (Chrome, Firefox, Safari, Edge)

### Not Supported
- IE 11 (KeyboardEvent properties differ)
- Mobile browsers (no physical keyboard)

---

## Code Quality Notes

### Strengths
- Clear constant definitions
- Event listener properly cleaned up
- Input field exclusion prevents false triggers
- Toast feedback provides UX feedback
- Help panel is toggleable

### Potential Improvements
- Extract keyboard handling to custom hook
- Create shortcuts configuration file
- Add command palette (cmdk installed)
- Better TypeScript typing for keyboard events
- Centralized shortcut definitions
- Platform-aware shortcuts (Cmd on Mac)
- localStorage persistence for custom shortcuts

