# Keyboard Shortcuts Reference Card

## Current Shortcuts (6 Total)

### Column Quick-Add
| Shortcut | Column | File | Line |
|----------|--------|------|------|
| `1` | To-Do | KanbanBoard.tsx | 97 |
| `2` | In Progress | KanbanBoard.tsx | 101 |
| `3` | Done | KanbanBoard.tsx | 105 |

### UI Controls
| Shortcut | Action | File | Line |
|----------|--------|------|------|
| `Shift + ?` | Toggle shortcuts help | KanbanBoard.tsx | 109 |
| `Enter` | Submit quick-add form | QuickAddTask.tsx | 21 |
| `Escape` | Cancel quick-add form | QuickAddTask.tsx | 31 |

---

## Keyboard Shortcut Code Locations

### KanbanBoard Component
```
File: src/components/KanbanBoard.tsx
├── Constants (Lines 20-31)
│   └── KEYBOARD_SHORTCUTS object
│   └── TOAST_DURATION object
├── State (Lines 34-42)
│   └── quickAddColumn
│   └── showShortcuts
├── Event Handler (Lines 86-117)
│   └── useEffect with keyboard listener
├── Render UI (Lines 254-274)
│   └── Shortcuts help panel
└── Handler Functions (Lines 86-117)
    └── handleKeyDown
```

### QuickAddTask Component
```
File: src/components/QuickAddTask.tsx
├── Event Handler (Lines 31-36)
│   └── handleKeyDown (Escape handling)
└── Render (Lines 38-62)
    └── Form with input & help text
```

---

## Architecture for Shortcuts

### Current Implementation Flow
```
Window KeyDown Event
    ↓
handleKeyDown in KanbanBoard
    ↓
Check: Is user typing?
    ├─ YES: Ignore
    └─ NO: Continue
    ↓
Match key to KEYBOARD_SHORTCUTS
    ├─ "1": setQuickAddColumn("todo")
    ├─ "2": setQuickAddColumn("doing")
    ├─ "3": setQuickAddColumn("done")
    └─ "?" + Shift: toggleShowShortcuts()
    ↓
Show Toast (Sonner)
    ↓
Update UI (Conditional Render)
```

### State Dependencies
```
quickAddColumn (null | "todo" | "doing" | "done")
    └─ Triggers: QuickAddTask form visibility
    
showShortcuts (boolean)
    └─ Triggers: Help panel visibility
```

---

## Toast Notifications (Sonner)

### Usage in Shortcuts
```typescript
import { toast } from "sonner";

// Success messages (short duration)
toast.success("Quick add: To-Do", { duration: 2000 });
toast.success("Quick add: In Progress", { duration: 2000 });
toast.success("Quick add: Done", { duration: 2000 });

// Other toast types (for future use)
toast.error("Error message");
toast.info("Info message");
toast.warning("Warning message");
```

### Toast Durations
```typescript
TOAST_DURATION.SHORT = 2000ms   // Used for quick feedback
TOAST_DURATION.MEDIUM = 3000ms  // Used for task updates
TOAST_DURATION.LONG = 5000ms    // Used for important messages
```

---

## Component Integration Points

### Keyboard Shortcuts ↔ UI Components

```
Shortcut "1" Pressed
    ↓
setQuickAddColumn("todo")
    ↓
QuickAddTask appears (conditional render)
    ↓
User types + Enter
    ↓
handleQuickAddTask()
    ↓
POST /api/tasks
    ↓
setTasks([...prev, newTask])
    ↓
TaskCard appears
    ↓
Toast.success() notification
```

---

## KeyboardEvent API Properties

### Used in Current Implementation
```typescript
e.key          // "1", "2", "3", "?"
e.shiftKey     // true/false (for "?" modifier)
e.target       // DOM element that triggered event
e.preventDefault()  // Stop default behavior
```

### Available for Future Use
```typescript
e.ctrlKey      // Ctrl key pressed
e.metaKey      // Cmd (Mac) or Win key pressed
e.altKey       // Alt key pressed
e.code         // Physical key code ("KeyA", etc.)
```

---

## Type Definitions

### TaskStatus Type
```typescript
type TaskStatus = "todo" | "doing" | "done";
```

### Shortcuts Object Type
```typescript
const KEYBOARD_SHORTCUTS = {
  TODO: "1",
  DOING: "2",
  DONE: "3",
  HELP: "?",
} as const;
```

### Toast Duration Type
```typescript
const TOAST_DURATION = {
  SHORT: 2000,
  MEDIUM: 3000,
  LONG: 5000,
} as const;
```

---

## API Calls from Shortcuts

### Task Creation (via handleQuickAddTask)
```typescript
const newTask = await tasksApi.createTask({
  title: string,
  status: "todo" | "doing" | "done",
  assignee: "You"
});
```

### Response Structure
```typescript
{
  id: string,
  title: string,
  status: "todo" | "doing" | "done",
  assignee: string,
  createdAt: string,
  updatedAt: string,
  attachments: [],
  comments: [],
  startDate?: string,
  dueDate?: string,
  valueStream?: string,
  description?: string
}
```

---

## Configuration Files Involved

### Environment Variables
```env
VITE_API_BASE_URL=/api
```

### Build Configuration (Vite)
```typescript
// vite.config.ts
server: {
  port: 8080,
  proxy: {
    "/api": {
      target: "http://localhost:8000"
    }
  }
}
```

### Design System (Tailwind)
```typescript
// tailwind.config.ts
colors: {
  primary: "hsl(var(--primary))",
  background: "hsl(var(--background))",
  // ... 40+ colors via CSS variables
}
```

---

## Testing Shortcuts

### Manual Test Cases
- [ ] Press "1" → See "Quick add: To-Do" toast
- [ ] Press "2" → See "Quick add: In Progress" toast
- [ ] Press "3" → See "Quick add: Done" toast
- [ ] Press Shift+? → Toggle shortcuts panel
- [ ] Type in input → Key press should NOT trigger shortcut
- [ ] In form: Press Enter → Submit task
- [ ] In form: Press Escape → Close form
- [ ] Press keys rapidly → No lag or multiple triggers

### Edge Cases to Test
- [ ] Disabled form field (can't type)
- [ ] Focus on different UI elements
- [ ] Different keyboard layouts
- [ ] Mobile device (no keyboard)
- [ ] Browser extensions affecting keyboard

---

## Shortcuts Help Panel UI

### Location
```
KanbanBoard.tsx, Lines 254-274
```

### Content Display
```
┌─────────────────────────────────────┐
│ KEYBOARD SHORTCUTS                  │
├─────────────────────────────────────┤
│ [1]  Quick add to To-Do             │
│ [2]  Quick add to In Progress       │
│ [3]  Quick add to Done              │
└─────────────────────────────────────┘
```

### Styling
- Background: `bg-muted/30`
- Border: `border-border/30`
- Radius: `rounded-xl`
- Grid: 3 columns on desktop, 1 on mobile

---

## Performance Notes

### Event Listener Cleanup
```typescript
useEffect(() => {
  window.addEventListener("keydown", handleKeyDown);
  return () => window.removeEventListener("keydown", handleKeyDown);
}, [showShortcuts]);  // Re-registers when state changes
```

**Potential Issue**: Listener re-registers every time `showShortcuts` changes
**Optimization**: Could memoize handler or separate concerns

### Toast Performance
- Maximum 1 toast visible at a time
- Auto-dismiss after duration
- Sonner library is optimized

---

## Browser Support

### Supported
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (touch only, no physical keyboard)

### Not Supported
- IE 11 (KeyboardEvent API differences)
- Very old browsers

---

## Accessibility Considerations

### Current Status
- Shortcuts work with keyboard only (good)
- Ignores input fields (prevents false triggers)
- Shows help panel with shortcut keys
- Uses `<kbd>` HTML elements (semantic)

### Missing Features
- No ARIA announcements
- No focus management for shortcuts
- No keyboard navigation between elements
- No visual focus indicators
- No screen reader support

---

## Next Steps for Enhancement

### Priority 1: Extract & Organize
```typescript
// Create src/lib/shortcuts.ts
export const KEYBOARD_SHORTCUTS = { ... }
export const TOAST_DURATION = { ... }
export const createShortcutHandler = (callbacks) => { ... }
```

### Priority 2: Create Custom Hook
```typescript
// Create src/hooks/useKeyboard.ts
export function useKeyboard(shortcuts) {
  useEffect(() => { ... })
}
```

### Priority 3: Add Command Palette
```typescript
// Create src/components/CommandPalette.tsx
// Use installed 'cmdk' library
// Ctrl+K / Cmd+K to open
```

### Priority 4: Enhance Help UI
```typescript
// Improve shortcuts help display
// Add search
// Add categories
// Add platform detection (Mac vs Windows)
```

---

## File Summary for Shortcuts

| File | Purpose | Size |
|------|---------|------|
| KanbanBoard.tsx | Main shortcuts handler | 360 lines |
| QuickAddTask.tsx | Form keyboard handling | 62 lines |
| use-toast.ts | Toast notifications | 187 lines |
| tasks.ts (API) | createTask() function | 234 lines |
| vite.config.ts | Build & server config | 44 lines |

---

## Quick Command Reference

### Start Development
```bash
npm run dev              # Frontend on port 8080
python main.py          # Backend on port 8000 (in backend/ dir)
```

### Debugging
```typescript
// Add to handleKeyDown to debug
console.log("Key pressed:", e.key, "Shift:", e.shiftKey);
console.log("Current quickAddColumn:", quickAddColumn);
```

### Testing Keyboard Events
```javascript
// In browser console
window.dispatchEvent(new KeyboardEvent('keydown', { key: '1' }));
```

---

## References

### Main Files
- Primary: `/home/user/task-crate/src/components/KanbanBoard.tsx`
- Secondary: `/home/user/task-crate/src/components/QuickAddTask.tsx`

### Documentation
- Complete Overview: `CODEBASE_OVERVIEW.md`
- Deep Dive: `SHORTCUTS_DEEP_DIVE.md`
- File Structure: `FILE_STRUCTURE_GUIDE.md`
- Summary: `CODEBASE_SUMMARY.md`

### External Resources
- React Hooks: https://react.dev/reference/react
- Sonner Toasts: https://sonner.emilkowal.ski/
- Shadcn/UI: https://ui.shadcn.com/
- Tailwind CSS: https://tailwindcss.com/

