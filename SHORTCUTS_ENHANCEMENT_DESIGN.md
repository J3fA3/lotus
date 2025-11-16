# Shortcuts Enhancement Design

## Overview
This document outlines the comprehensive keyboard shortcut system with remote configuration capabilities.

## Shortcut Categories

### 1. Global Shortcuts (Available anywhere)
| Shortcut | Action | Description |
|----------|--------|-------------|
| `?` or `Shift+/` | Toggle Help | Show/hide keyboard shortcuts help |
| `/` | Search/Command Palette | Open command palette |
| `Escape` | Close/Cancel | Close dialogs, cancel operations |
| `Ctrl+K` | Command Palette | Alternative command palette trigger |
| `Ctrl+,` | Settings | Open settings panel |

### 2. Board Navigation Shortcuts
| Shortcut | Action | Description |
|----------|--------|-------------|
| `1` | Focus To-Do Column | Quick add in To-Do |
| `2` | Focus In Progress Column | Quick add in In Progress |
| `3` | Focus Done Column | Quick add in Done |
| `h` or `←` | Previous Column | Move focus to previous column |
| `l` or `→` | Next Column | Move focus to next column |
| `Tab` | Next Column | Tab through columns |
| `Shift+Tab` | Previous Column | Reverse tab through columns |

### 3. Task Selection & Navigation
| Shortcut | Action | Description |
|----------|--------|-------------|
| `j` or `↓` | Next Task | Select next task in column |
| `k` or `↑` | Previous Task | Select previous task in column |
| `g g` | First Task | Jump to first task in column |
| `Shift+G` | Last Task | Jump to last task in column |
| `Enter` | Open Task | Open selected task details |
| `Space` | Quick Preview | Quick preview task without full dialog |

### 4. Task Quick Actions
| Shortcut | Action | Description |
|----------|--------|-------------|
| `n` | New Task | Create new task in current column |
| `e` | Edit Task | Edit selected task |
| `d` | Delete Task | Delete selected task (with confirmation) |
| `c` | Toggle Complete | Mark task as done/undone |
| `x` | Archive Task | Archive selected task |
| `y` | Duplicate Task | Duplicate selected task |
| `m` | Move Task | Open move dialog to change column |
| `p` | Set Priority | Cycle priority (low → medium → high) |

### 5. Task Detail Dialog Shortcuts
| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+Enter` | Save & Close | Save changes and close dialog |
| `Ctrl+S` | Save | Save changes |
| `Escape` | Close | Close dialog without saving |
| `t` | Focus Title | Jump to title field |
| `d` | Focus Description | Jump to description field |
| `Ctrl+D` | Add Due Date | Open date picker |
| `Ctrl+P` | Set Priority | Open priority selector |
| `Ctrl+T` | Add Tag | Focus tag input |
| `Ctrl+Delete` | Delete Task | Delete current task |

### 6. Message Menu Shortcuts
| Shortcut | Action | Description |
|----------|--------|-------------|
| `m` | Toggle Messages | Open/close message menu |
| `↑` / `↓` | Navigate Messages | Move between messages |
| `Enter` | Select Message | Select/apply message |
| `Delete` | Delete Message | Delete selected message |
| `Escape` | Close Messages | Close message menu |

### 7. Quick Add Form Shortcuts
| Shortcut | Action | Description |
|----------|--------|-------------|
| `Enter` | Submit | Create task |
| `Escape` | Cancel | Cancel quick add |
| `Tab` | Next Field | Move to next field |
| `Shift+Tab` | Previous Field | Move to previous field |

### 8. Bulk Operations
| Shortcut | Action | Description |
|----------|--------|-------------|
| `Shift+Click` | Multi-Select | Select multiple tasks |
| `Ctrl+A` | Select All | Select all tasks in column |
| `Shift+D` | Bulk Delete | Delete all selected tasks |
| `Shift+M` | Bulk Move | Move all selected tasks |

## Architecture

### Backend Components

#### 1. Database Model (`backend/models/shortcut_config.py`)
```python
class ShortcutConfig(Base):
    __tablename__ = "shortcut_configs"

    id: int
    user_id: Optional[int]  # NULL = global default
    category: str  # "global", "board", "task", etc.
    action: str  # "new_task", "delete_task", etc.
    key: str  # "n", "d", "ctrl+s", etc.
    modifiers: List[str]  # ["ctrl", "shift", etc.]
    enabled: bool
    description: str
    created_at: datetime
    updated_at: datetime
```

#### 2. API Endpoints (`backend/routers/shortcuts.py`)
- `GET /api/shortcuts` - Get all shortcuts (with user overrides)
- `GET /api/shortcuts/defaults` - Get default shortcuts
- `PUT /api/shortcuts/{action}` - Update specific shortcut
- `POST /api/shortcuts/reset` - Reset to defaults
- `POST /api/shortcuts/import` - Import shortcut configuration
- `GET /api/shortcuts/export` - Export shortcut configuration

### Frontend Components

#### 1. Types (`src/types/shortcuts.ts`)
```typescript
interface ShortcutConfig {
  id: string;
  category: ShortcutCategory;
  action: string;
  key: string;
  modifiers: Modifier[];
  enabled: boolean;
  description: string;
}

type ShortcutCategory = 'global' | 'board' | 'task' | 'dialog' | 'message';
type Modifier = 'ctrl' | 'shift' | 'alt' | 'meta';
```

#### 2. Context & Hook (`src/contexts/ShortcutContext.tsx`)
- `ShortcutProvider` - Manages shortcut state
- `useShortcuts()` - Hook to access shortcuts
- `useKeyboardShortcut(action, callback)` - Register shortcut handler

#### 3. Keyboard Handler (`src/hooks/useKeyboardHandler.ts`)
- Listen to keyboard events
- Match key combinations to actions
- Handle conflicts and priorities
- Support sequence shortcuts (e.g., "g g")

#### 4. Settings UI (`src/components/ShortcutSettings.tsx`)
- Display all shortcuts in organized categories
- Allow customization with conflict detection
- Import/export functionality
- Reset to defaults

#### 5. Command Palette (`src/components/CommandPalette.tsx`)
- Fuzzy search for actions
- Execute actions via keyboard
- Display assigned shortcuts

## Implementation Plan

### Phase 1: Backend Infrastructure
1. Create database model for shortcuts
2. Seed default shortcuts
3. Create API endpoints
4. Add migration script

### Phase 2: Frontend Infrastructure
5. Create TypeScript types
6. Implement ShortcutContext and provider
7. Create useKeyboardHandler hook
8. Build keyboard event system

### Phase 3: Board & Navigation
9. Implement board navigation shortcuts
10. Add task selection/navigation
11. Update KanbanBoard component

### Phase 4: Task Actions
12. Implement task quick actions
13. Add task detail dialog shortcuts
14. Update TaskDetailDialog component

### Phase 5: Additional Features
15. Implement message menu shortcuts
16. Add bulk operations
17. Build command palette

### Phase 6: Settings & UI
18. Create shortcut settings panel
19. Build conflict detection
20. Add import/export functionality

### Phase 7: Testing & Documentation
21. Test all shortcuts
22. Update help dialog
23. Create user documentation

## Conflict Resolution

### Priority Order (Highest to Lowest)
1. Input fields (native browser shortcuts)
2. Dialog-specific shortcuts
3. Component-specific shortcuts
4. Global shortcuts

### Conflict Detection
- Warn when assigning conflicting shortcuts
- Show which component/action uses the shortcut
- Suggest alternative keys

## Accessibility Considerations
- All shortcuts have mouse alternatives
- Visual indicators for focused elements
- Screen reader announcements for actions
- Configurable shortcuts for accessibility needs

## Remote Configuration Features

### User Preferences
- Per-user shortcut overrides
- Sync across devices via backend
- Profile-based configurations (Vim mode, Emacs mode, etc.)

### Preset Configurations
- **Default**: Standard shortcuts
- **Vim Mode**: Vim-inspired navigation
- **Emacs Mode**: Emacs-inspired shortcuts
- **Minimal**: Only essential shortcuts
- **Custom**: User-defined

### Cloud Sync
- Save configurations to backend
- Restore on new device/browser
- Version history
- Share configurations with team

## Future Enhancements
- Macro recording
- Shortcut sequences (e.g., "g t" = go to task)
- Context-aware shortcuts
- Shortcut suggestions based on usage
- Analytics on shortcut usage
