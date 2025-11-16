/**
 * Keyboard shortcuts types
 */

export type ShortcutCategory = 'global' | 'board' | 'task' | 'dialog' | 'message' | 'bulk';
export type Modifier = 'ctrl' | 'shift' | 'alt' | 'meta';

export interface ShortcutConfig {
  id: string;
  category: ShortcutCategory;
  action: string;
  key: string;
  modifiers: Modifier[];
  enabled: boolean;
  description: string;
  userId?: number | null;
  isDefault: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ShortcutHandler {
  action: string;
  callback: (event: KeyboardEvent) => void;
  category?: ShortcutCategory;
  priority?: number; // Higher priority runs first (for conflict resolution)
}

export interface KeyboardEventMatch {
  key: string;
  modifiers: Modifier[];
}

export interface ShortcutContextValue {
  shortcuts: ShortcutConfig[];
  loading: boolean;
  error: string | null;
  registerHandler: (handler: ShortcutHandler) => () => void;
  unregisterHandler: (action: string) => void;
  updateShortcut: (id: string, updates: Partial<ShortcutConfig>) => Promise<void>;
  resetShortcuts: (userId?: number) => Promise<void>;
  exportShortcuts: (userId?: number) => Promise<any>;
  importShortcuts: (config: any) => Promise<void>;
  getShortcutByAction: (action: string) => ShortcutConfig | undefined;
  isShortcutPressed: (event: KeyboardEvent, action: string) => boolean;
}

export interface ShortcutPreset {
  id: string;
  name: string;
  description: string;
  shortcuts: Partial<ShortcutConfig>[];
}

// Preset configurations
export const SHORTCUT_PRESETS: ShortcutPreset[] = [
  {
    id: 'default',
    name: 'Default',
    description: 'Standard keyboard shortcuts',
    shortcuts: []
  },
  {
    id: 'vim',
    name: 'Vim Mode',
    description: 'Vim-inspired navigation',
    shortcuts: []
  },
  {
    id: 'minimal',
    name: 'Minimal',
    description: 'Only essential shortcuts',
    shortcuts: []
  }
];
