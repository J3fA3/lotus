# Keyboard Shortcuts Settings - User Guide

## Overview

The Shortcuts Settings panel provides a comprehensive visual interface for customizing all keyboard shortcuts directly in the app. No need to manually edit configuration files or use API calls!

## Opening the Settings

There are **3 ways** to open the Shortcuts Settings:

1. **Keyboard**: Press `Ctrl+,` (or `Cmd+,` on Mac)
2. **Toolbar**: Click the **Settings** button in the top-right corner
3. **Shortcuts Help**: Press `?` to show shortcuts, then click **"Customize Shortcuts"**

## Features

### 🎨 Visual Editor
- Click on any shortcut's key combination to edit it
- Press the new key combination you want to use
- Click ✓ to save or ✗ to cancel
- Changes are saved immediately to the backend

### 🔍 Search & Filter
- **Search bar**: Find shortcuts by name, action, or key
- **Category tabs**: Filter by category (Global, Board, Task, etc.)
- **All tab**: View all shortcuts grouped by category

### ⚠️ Conflict Detection
- Automatically detects conflicting shortcuts
- Shows a warning indicator for conflicts
- Helps you avoid assigning the same key to multiple actions

### 🔄 Enable/Disable Shortcuts
- Toggle individual shortcuts on/off with the switch
- Disabled shortcuts won't trigger their actions
- Useful for temporarily disabling conflicting shortcuts

### 📦 Import/Export
- **Export**: Download your shortcuts as a JSON file
- **Import**: Upload a previously saved configuration
- **Share**: Share your shortcut config with team members

### 🔁 Reset to Defaults
- Click **Reset** to restore all shortcuts to default values
- Requires confirmation to prevent accidental resets

## Using the Settings Panel

### Editing a Shortcut

1. **Find the shortcut** you want to change
   - Use search or category tabs

2. **Click on the key combination** (e.g., `Ctrl+N`)
   - The shortcut will enter "recording mode"
   - Shows "Press a key..." message

3. **Press your desired key combination**
   - Example: Hold `Ctrl` and press `K`
   - The new combination will be shown

4. **Click the green checkmark** (✓) to save
   - Or click the red X to cancel
   - Changes sync to backend immediately

### Categories

The shortcuts are organized into 6 categories:

| Category | Description | Example Shortcuts |
|----------|-------------|-------------------|
| **Global** | App-wide shortcuts | `?` (help), `/` (search), `Ctrl+,` (settings) |
| **Board** | Column navigation | `1/2/3` (quick add), `h/l` (navigate columns) |
| **Task** | Task actions | `j/k` (navigate), `e` (edit), `d` (delete) |
| **Dialog** | Dialog-specific | `Ctrl+Enter` (save), `Escape` (close) |
| **Message** | Message menu | Navigate and manage messages |
| **Bulk** | Multi-task operations | `Ctrl+A` (select all), `Shift+D` (bulk delete) |

### Tips & Best Practices

#### ✅ Good Shortcut Choices
- **Single keys**: `n`, `e`, `d` for common actions
- **Ctrl/Cmd combos**: `Ctrl+S`, `Ctrl+K` for important actions
- **Vim-style**: `h`, `j`, `k`, `l` for navigation
- **Mnemonic**: `n` for **N**ew, `e` for **E**dit, `d` for **D**elete

#### ❌ Avoid
- **Browser shortcuts**: `Ctrl+T`, `Ctrl+W` (conflict with browser)
- **System shortcuts**: `Ctrl+Alt+Delete`, `Alt+Tab`
- **Single modifier keys**: Just pressing `Ctrl` alone
- **Overloading common keys**: Multiple actions on `Enter`

#### 🎯 Conflict Resolution
When you see a conflict warning:

1. **Decide which action is more important**
2. **Disable** the less important shortcut, or
3. **Change one** to a different key combination
4. Conflicts are highlighted in yellow

### Keyboard Navigation in Settings

While the settings panel is open:

- **Tab**: Move between elements
- **Enter**: Start editing focused shortcut
- **Escape**: Close the settings panel
- **Arrow keys**: Navigate through the list

## Import/Export Workflows

### Exporting Your Configuration

1. Click the **Export** button
2. Choose where to save the JSON file
3. File is named: `shortcuts-YYYY-MM-DD.json`

**Use cases:**
- Backup your custom shortcuts
- Share with team members
- Version control your shortcuts
- Migrate to a new device

### Importing a Configuration

1. Click the **Import** button
2. Select your JSON file
3. Shortcuts are loaded and synced immediately

**Use cases:**
- Restore from backup
- Apply team standard shortcuts
- Try different shortcut schemes

### Example Export File

```json
{
  "version": "1.0",
  "exported_at": "2025-01-15T10:30:00.000Z",
  "user_id": null,
  "shortcuts": [
    {
      "id": "task_new",
      "category": "task",
      "action": "new_task",
      "key": "n",
      "modifiers": [],
      "enabled": true,
      "description": "Create new task in current column"
    }
    // ... more shortcuts
  ]
}
```

## API Integration

The settings panel uses these API endpoints:

- `GET /api/shortcuts` - Fetch all shortcuts
- `PUT /api/shortcuts/{id}` - Update a shortcut
- `POST /api/shortcuts/reset` - Reset to defaults
- `GET /api/shortcuts/export` - Export configuration
- `POST /api/shortcuts/import` - Import configuration

## Troubleshooting

### Shortcut not working?

1. **Check if enabled**: Look for the toggle switch
2. **Check for conflicts**: Yellow warning indicator
3. **Verify the key**: Make sure you recorded it correctly
4. **Check context**: Some shortcuts only work in specific contexts

### Changes not saving?

1. **Click the checkmark**: Must confirm edits
2. **Check backend**: Make sure backend is running
3. **Check console**: Look for error messages
4. **Try export/import**: As a workaround

### Conflicts appearing?

1. **Review both shortcuts**: Decide which to keep
2. **Disable one**: Or change its key combination
3. **Use modifiers**: Add Ctrl, Shift, or Alt to differentiate

### Reset not working?

1. **Confirm the dialog**: Must click "OK" in confirmation
2. **Check permissions**: Make sure you have write access
3. **Reload page**: If needed, refresh the browser

## Advanced Usage

### Creating Shortcut Presets

1. **Configure** your ideal shortcuts
2. **Export** to a JSON file
3. **Name it** (e.g., `vim-mode.json`, `emacs-mode.json`)
4. **Share** with others or keep for different workflows

### Per-User Customization

The system supports user-specific overrides:

- Default shortcuts apply to all users
- Individual users can override defaults
- User overrides are stored with `user_id`
- Export includes both defaults and overrides

### Bulk Editing

To change multiple shortcuts at once:

1. **Export** current configuration
2. **Edit** the JSON file with your text editor
3. **Import** the modified file
4. All changes applied instantly

## Examples

### Setting Up Vim-Style Navigation

1. Open Settings (`Ctrl+,`)
2. Go to "Task" category
3. Edit shortcuts:
   - Next task: `j`
   - Previous task: `k`
   - Next column: `l`
   - Previous column: `h`
   - First task: `g g` (press g twice)
   - Last task: `Shift+G`

### Creating a Minimal Setup

1. Open Settings
2. **Disable** all non-essential shortcuts
3. **Keep only**:
   - Quick add (1, 2, 3)
   - Navigate (arrows)
   - Open task (Enter)
4. Export as `minimal.json`

### Team Standard Shortcuts

1. **Team lead** creates ideal config
2. **Export** to `team-shortcuts.json`
3. **Share** via Git or shared drive
4. **Team members** import the file
5. Everyone has consistent shortcuts!

## Accessibility

The settings panel is designed with accessibility in mind:

- **Keyboard navigation**: Full support
- **Screen readers**: ARIA labels (can be enhanced)
- **Visual feedback**: Clear focus states
- **Large click targets**: Easy to interact with
- **Color contrast**: Follows design system

## Future Enhancements

Planned features for future versions:

- [ ] **Shortcut presets**: One-click Vim/Emacs modes
- [ ] **Shortcut suggestions**: Based on usage patterns
- [ ] **Conflict auto-resolution**: Suggest alternatives
- [ ] **Shortcut analytics**: See most-used shortcuts
- [ ] **Custom categories**: Create your own groups
- [ ] **Shortcut macros**: Record action sequences

---

## Quick Reference

| Action | Shortcut |
|--------|----------|
| Open Settings | `Ctrl+,` (or Cmd+,) |
| Close Settings | `Escape` |
| Edit Shortcut | Click on key combination |
| Save Edit | Click green checkmark (✓) |
| Cancel Edit | Click red X |
| Toggle Enabled | Click switch |
| Search | Type in search box |
| Filter Category | Click category tab |
| Export | Click Export button |
| Import | Click Import button |
| Reset All | Click Reset button |

---

**Need Help?** Press `?` anywhere in the app to see all available shortcuts!

**Pro Tip:** Start with the defaults, customize gradually as you discover your workflow patterns.
