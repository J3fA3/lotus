"""
Default keyboard shortcuts configuration
"""
from typing import List, Dict, Any


DEFAULT_SHORTCUTS: List[Dict[str, Any]] = [
    # ============= Global Shortcuts =============
    {
        "id": "global_help",
        "category": "global",
        "action": "toggle_help",
        "key": "?",
        "modifiers": [],
        "enabled": True,
        "description": "Toggle keyboard shortcuts help dialog",
    },
    {
        "id": "global_search",
        "category": "global",
        "action": "focus_search",
        "key": "f",
        "modifiers": ["ctrl"],
        "enabled": True,
        "description": "Focus search bar",
    },
    {
        "id": "global_lotus",
        "category": "global",
        "action": "toggle_lotus",
        "key": "l",
        "modifiers": ["ctrl", "shift"],
        "enabled": True,
        "description": "Toggle Lotus chat dialog",
    },

    # ============= Board Navigation Shortcuts =============
    {
        "id": "board_quick_add_todo",
        "category": "board",
        "action": "quick_add_todo",
        "key": "1",
        "modifiers": [],
        "enabled": True,
        "description": "Quick add task to To-Do column",
    },
    {
        "id": "board_quick_add_doing",
        "category": "board",
        "action": "quick_add_doing",
        "key": "2",
        "modifiers": [],
        "enabled": True,
        "description": "Quick add task to In Progress column",
    },
    {
        "id": "board_quick_add_done",
        "category": "board",
        "action": "quick_add_done",
        "key": "3",
        "modifiers": [],
        "enabled": True,
        "description": "Quick add task to Done column",
    },
    {
        "id": "board_prev_column",
        "category": "board",
        "action": "prev_column",
        "key": "ArrowLeft",
        "modifiers": [],
        "enabled": True,
        "description": "Move focus to previous column",
    },
    {
        "id": "board_next_column",
        "category": "board",
        "action": "next_column",
        "key": "ArrowRight",
        "modifiers": [],
        "enabled": True,
        "description": "Move focus to next column",
    },
    {
        "id": "board_next_column_tab",
        "category": "board",
        "action": "next_column",
        "key": "Tab",
        "modifiers": [],
        "enabled": True,
        "description": "Tab to next column",
    },
    {
        "id": "board_prev_column_shift_tab",
        "category": "board",
        "action": "prev_column",
        "key": "Tab",
        "modifiers": ["shift"],
        "enabled": True,
        "description": "Shift+Tab to previous column",
    },

    # ============= Task Selection & Navigation =============
    {
        "id": "task_next",
        "category": "task",
        "action": "next_task",
        "key": "ArrowDown",
        "modifiers": [],
        "enabled": True,
        "description": "Select next task in column",
    },
    {
        "id": "task_prev",
        "category": "task",
        "action": "prev_task",
        "key": "ArrowUp",
        "modifiers": [],
        "enabled": True,
        "description": "Select previous task in column",
    },
    {
        "id": "task_last",
        "category": "task",
        "action": "last_task",
        "key": "G",
        "modifiers": ["shift"],
        "enabled": True,
        "description": "Jump to last task in column",
    },
    {
        "id": "task_open",
        "category": "task",
        "action": "open_task",
        "key": "Enter",
        "modifiers": [],
        "enabled": True,
        "description": "Open selected task details",
    },

    # ============= Task Quick Actions =============
    {
        "id": "task_new",
        "category": "task",
        "action": "new_task",
        "key": "n",
        "modifiers": [],
        "enabled": True,
        "description": "Create new task in current column",
    },
    {
        "id": "task_delete",
        "category": "task",
        "action": "delete_task",
        "key": "d",
        "modifiers": [],
        "enabled": True,
        "description": "Delete selected task",
    },
    {
        "id": "task_duplicate",
        "category": "task",
        "action": "duplicate_task",
        "key": "y",
        "modifiers": [],
        "enabled": True,
        "description": "Duplicate selected task",
    },
    {
        "id": "task_move",
        "category": "task",
        "action": "move_task",
        "key": "m",
        "modifiers": [],
        "enabled": True,
        "description": "Move task to next column (cycles through all)",
    },

    # ============= Task Detail Dialog Shortcuts =============
    {
        "id": "dialog_close",
        "category": "dialog",
        "action": "close_dialog",
        "key": "Escape",
        "modifiers": [],
        "enabled": True,
        "description": "Close dialog",
    },
    {
        "id": "dialog_toggle_peek_expanded",
        "category": "dialog",
        "action": "toggle_peek_expanded",
        "key": "e",
        "modifiers": ["ctrl"],
        "enabled": True,
        "description": "Toggle between peek and expanded view",
    },
    {
        "id": "dialog_toggle_fullscreen",
        "category": "dialog",
        "action": "toggle_fullscreen",
        "key": "e",
        "modifiers": ["ctrl", "shift"],
        "enabled": True,
        "description": "Toggle fullscreen view",
    },
    {
        "id": "dialog_focus_notes",
        "category": "dialog",
        "action": "focus_notes",
        "key": "d",
        "modifiers": ["ctrl"],
        "enabled": True,
        "description": "Focus and scroll to notes section",
    },
    {
        "id": "dialog_tab_section",
        "category": "dialog",
        "action": "tab_section",
        "key": "Tab",
        "modifiers": ["ctrl"],
        "enabled": True,
        "description": "Tab to next section in task dialog",
    },
]


def get_default_shortcuts() -> List[Dict[str, Any]]:
    """Get default shortcuts configuration"""
    return DEFAULT_SHORTCUTS.copy()


def get_shortcuts_by_category(category: str) -> List[Dict[str, Any]]:
    """Get shortcuts filtered by category"""
    return [s for s in DEFAULT_SHORTCUTS if s["category"] == category]
