/**
 * Shortcut Settings Panel - Visual editor for customizing keyboard shortcuts
 */
import { useState, useCallback, useMemo } from 'react';
import { useShortcuts } from '@/contexts/ShortcutContext';
import { ShortcutConfig, ShortcutCategory, Modifier } from '@/types/shortcuts';
import { getShortcutDisplay } from '@/hooks/useKeyboardHandler';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import {
  Search,
  Download,
  Upload,
  RotateCcw,
  Check,
  X,
  Keyboard,
  AlertCircle,
  Settings2,
} from 'lucide-react';
import { toast } from 'sonner';

interface ShortcutSettingsProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface EditingShortcut {
  id: string;
  recording: boolean;
  tempKey: string;
  tempModifiers: Modifier[];
}

export function ShortcutSettings({ open, onOpenChange }: ShortcutSettingsProps) {
  const {
    shortcuts,
    loading,
    updateShortcut,
    resetShortcuts,
    exportShortcuts,
    importShortcuts,
  } = useShortcuts();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<'all' | ShortcutCategory>('all');
  const [editing, setEditing] = useState<EditingShortcut | null>(null);
  const [conflicts, setConflicts] = useState<Map<string, string[]>>(new Map());

  // Filter shortcuts based on search and category
  const filteredShortcuts = useMemo(() => {
    let filtered = shortcuts;

    if (selectedCategory !== 'all') {
      filtered = filtered.filter((s) => s.category === selectedCategory);
    }

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (s) =>
          s.action.toLowerCase().includes(query) ||
          s.description.toLowerCase().includes(query) ||
          s.key.toLowerCase().includes(query)
      );
    }

    return filtered;
  }, [shortcuts, selectedCategory, searchQuery]);

  // Group shortcuts by category
  const groupedShortcuts = useMemo(() => {
    const grouped = new Map<ShortcutCategory, ShortcutConfig[]>();
    filteredShortcuts.forEach((shortcut) => {
      if (!grouped.has(shortcut.category)) {
        grouped.set(shortcut.category, []);
      }
      grouped.get(shortcut.category)!.push(shortcut);
    });
    return grouped;
  }, [filteredShortcuts]);

  // Detect conflicts
  const detectConflicts = useCallback((shortcuts: ShortcutConfig[]) => {
    const conflictMap = new Map<string, string[]>();
    const keyMap = new Map<string, string[]>();

    shortcuts.forEach((shortcut) => {
      if (!shortcut.enabled) return;

      const keyCombo = `${shortcut.modifiers.sort().join('+')}+${shortcut.key.toLowerCase()}`;
      if (!keyMap.has(keyCombo)) {
        keyMap.set(keyCombo, []);
      }
      keyMap.get(keyCombo)!.push(shortcut.id);
    });

    keyMap.forEach((ids, keyCombo) => {
      if (ids.length > 1) {
        ids.forEach((id) => {
          conflictMap.set(id, ids.filter((otherId) => otherId !== id));
        });
      }
    });

    setConflicts(conflictMap);
  }, []);

  // Recalculate conflicts when shortcuts change
  useMemo(() => {
    detectConflicts(shortcuts);
  }, [shortcuts, detectConflicts]);

  // Start editing a shortcut
  const startEditing = useCallback((shortcut: ShortcutConfig) => {
    setEditing({
      id: shortcut.id,
      recording: true,
      tempKey: shortcut.key,
      tempModifiers: shortcut.modifiers,
    });
  }, []);

  // Cancel editing
  const cancelEditing = useCallback(() => {
    setEditing(null);
  }, []);

  // Handle key recording
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!editing?.recording) return;

      e.preventDefault();
      e.stopPropagation();

      // Don't record modifier keys alone
      if (['Control', 'Shift', 'Alt', 'Meta'].includes(e.key)) {
        return;
      }

      const modifiers: Modifier[] = [];
      if (e.ctrlKey) modifiers.push('ctrl');
      if (e.shiftKey) modifiers.push('shift');
      if (e.altKey) modifiers.push('alt');
      if (e.metaKey) modifiers.push('meta');

      setEditing({
        ...editing,
        tempKey: e.key,
        tempModifiers: modifiers,
        recording: false,
      });
    },
    [editing]
  );

  // Save edited shortcut
  const saveShortcut = useCallback(
    async (shortcutId: string) => {
      if (!editing) return;

      try {
        await updateShortcut(shortcutId, {
          key: editing.tempKey,
          modifiers: editing.tempModifiers,
        });
        setEditing(null);
        toast.success('Shortcut updated');
      } catch (err) {
        toast.error('Failed to update shortcut');
      }
    },
    [editing, updateShortcut]
  );

  // Toggle shortcut enabled state
  const toggleShortcut = useCallback(
    async (shortcut: ShortcutConfig) => {
      try {
        await updateShortcut(shortcut.id, {
          enabled: !shortcut.enabled,
        });
        toast.success(shortcut.enabled ? 'Shortcut disabled' : 'Shortcut enabled');
      } catch (err) {
        toast.error('Failed to toggle shortcut');
      }
    },
    [updateShortcut]
  );

  // Reset all shortcuts
  const handleReset = useCallback(async () => {
    if (!confirm('Reset all shortcuts to defaults? This cannot be undone.')) {
      return;
    }

    try {
      await resetShortcuts();
      toast.success('Shortcuts reset to defaults');
    } catch (err) {
      toast.error('Failed to reset shortcuts');
    }
  }, [resetShortcuts]);

  // Export shortcuts
  const handleExport = useCallback(async () => {
    try {
      const config = await exportShortcuts();
      const blob = new Blob([JSON.stringify(config, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `shortcuts-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Shortcuts exported');
    } catch (err) {
      toast.error('Failed to export shortcuts');
    }
  }, [exportShortcuts]);

  // Import shortcuts
  const handleImport = useCallback(() => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/json';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      try {
        const text = await file.text();
        const config = JSON.parse(text);
        await importShortcuts(config);
        toast.success('Shortcuts imported');
      } catch (err) {
        toast.error('Failed to import shortcuts');
      }
    };
    input.click();
  }, [importShortcuts]);

  // Category icons
  const categoryIcons: Record<ShortcutCategory, string> = {
    global: '🌐',
    board: '📋',
    task: '✓',
    dialog: '💬',
    message: '📨',
    bulk: '📦',
  };

  // Category labels
  const categoryLabels: Record<ShortcutCategory, string> = {
    global: 'Global',
    board: 'Board Navigation',
    task: 'Task Actions',
    dialog: 'Dialog',
    message: 'Messages',
    bulk: 'Bulk Operations',
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            Keyboard Shortcuts
          </DialogTitle>
          <DialogDescription>
            Customize keyboard shortcuts to match your workflow. Click on any shortcut to change it.
          </DialogDescription>
        </DialogHeader>

        {/* Toolbar */}
        <div className="flex items-center gap-2 pb-4 border-b">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search shortcuts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button variant="outline" size="sm" onClick={handleImport}>
            <Upload className="h-4 w-4 mr-2" />
            Import
          </Button>
          <Button variant="outline" size="sm" onClick={handleReset}>
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset
          </Button>
        </div>

        {/* Category Tabs */}
        <Tabs
          value={selectedCategory}
          onValueChange={(value) => setSelectedCategory(value as any)}
          className="flex-1 flex flex-col overflow-hidden"
        >
          <TabsList className="grid grid-cols-7 w-full">
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="global">Global</TabsTrigger>
            <TabsTrigger value="board">Board</TabsTrigger>
            <TabsTrigger value="task">Task</TabsTrigger>
            <TabsTrigger value="dialog">Dialog</TabsTrigger>
            <TabsTrigger value="message">Message</TabsTrigger>
            <TabsTrigger value="bulk">Bulk</TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-y-auto mt-4">
            <TabsContent value={selectedCategory} className="mt-0 space-y-6">
              {selectedCategory === 'all' ? (
                // Show all categories grouped
                Array.from(groupedShortcuts.entries()).map(([category, categoryShortcuts]) => (
                  <div key={category}>
                    <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                      <span>{categoryIcons[category]}</span>
                      {categoryLabels[category]}
                      <Badge variant="secondary" className="ml-auto">
                        {categoryShortcuts.length}
                      </Badge>
                    </h3>
                    <div className="space-y-2">
                      {categoryShortcuts.map((shortcut) => (
                        <ShortcutRow
                          key={shortcut.id}
                          shortcut={shortcut}
                          editing={editing?.id === shortcut.id ? editing : null}
                          conflict={conflicts.get(shortcut.id)}
                          onStartEdit={startEditing}
                          onCancelEdit={cancelEditing}
                          onSave={saveShortcut}
                          onToggle={toggleShortcut}
                          onKeyDown={handleKeyDown}
                        />
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                // Show selected category
                <div className="space-y-2">
                  {filteredShortcuts.map((shortcut) => (
                    <ShortcutRow
                      key={shortcut.id}
                      shortcut={shortcut}
                      editing={editing?.id === shortcut.id ? editing : null}
                      conflict={conflicts.get(shortcut.id)}
                      onStartEdit={startEditing}
                      onCancelEdit={cancelEditing}
                      onSave={saveShortcut}
                      onToggle={toggleShortcut}
                      onKeyDown={handleKeyDown}
                    />
                  ))}
                </div>
              )}

              {filteredShortcuts.length === 0 && (
                <div className="text-center py-12 text-muted-foreground">
                  <Keyboard className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No shortcuts found</p>
                </div>
              )}
            </TabsContent>
          </div>
        </Tabs>

        {/* Stats */}
        <div className="flex items-center justify-between pt-4 border-t text-xs text-muted-foreground">
          <div className="flex items-center gap-4">
            <span>{shortcuts.length} total shortcuts</span>
            <span>{shortcuts.filter((s) => s.enabled).length} enabled</span>
            <span>{conflicts.size} conflicts</span>
          </div>
          <div>
            <kbd className="px-2 py-1 bg-muted rounded text-[10px]">Esc</kbd> to close
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Individual shortcut row component
interface ShortcutRowProps {
  shortcut: ShortcutConfig;
  editing: EditingShortcut | null;
  conflict?: string[];
  onStartEdit: (shortcut: ShortcutConfig) => void;
  onCancelEdit: () => void;
  onSave: (id: string) => void;
  onToggle: (shortcut: ShortcutConfig) => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
}

function ShortcutRow({
  shortcut,
  editing,
  conflict,
  onStartEdit,
  onCancelEdit,
  onSave,
  onToggle,
  onKeyDown,
}: ShortcutRowProps) {
  const isEditing = editing !== null;
  const hasConflict = conflict && conflict.length > 0;

  return (
    <div
      className={`
        flex items-center gap-4 p-3 rounded-lg border transition-all
        ${!shortcut.enabled ? 'opacity-50' : ''}
        ${hasConflict ? 'border-yellow-500/50 bg-yellow-500/5' : 'border-border'}
        ${isEditing ? 'ring-2 ring-primary' : ''}
      `}
    >
      {/* Toggle */}
      <Switch
        checked={shortcut.enabled}
        onCheckedChange={() => onToggle(shortcut)}
        className="shrink-0"
      />

      {/* Description */}
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-foreground truncate">
          {shortcut.description}
        </div>
        <div className="text-xs text-muted-foreground truncate">
          {shortcut.action}
        </div>
      </div>

      {/* Shortcut Display/Editor */}
      <div className="flex items-center gap-2">
        {isEditing ? (
          <>
            <div
              className="px-3 py-1.5 bg-primary/10 border-2 border-primary rounded-md text-sm font-mono min-w-[120px] text-center cursor-text"
              tabIndex={0}
              onKeyDown={onKeyDown}
              autoFocus
            >
              {editing.recording ? (
                <span className="text-muted-foreground animate-pulse">Press a key...</span>
              ) : (
                <span className="font-semibold">
                  {editing.tempModifiers.map((m) => m.charAt(0).toUpperCase() + m.slice(1)).join('+')}
                  {editing.tempModifiers.length > 0 ? '+' : ''}
                  {editing.tempKey}
                </span>
              )}
            </div>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onSave(shortcut.id)}
              disabled={editing.recording}
            >
              <Check className="h-4 w-4 text-green-600" />
            </Button>
            <Button size="sm" variant="ghost" onClick={onCancelEdit}>
              <X className="h-4 w-4 text-red-600" />
            </Button>
          </>
        ) : (
          <button
            onClick={() => onStartEdit(shortcut)}
            className="px-3 py-1.5 bg-muted hover:bg-muted/80 border border-border rounded-md text-sm font-mono min-w-[120px] text-center transition-colors"
          >
            {getShortcutDisplay(shortcut)}
          </button>
        )}
      </div>

      {/* Conflict indicator */}
      {hasConflict && (
        <div className="flex items-center gap-1 text-yellow-600">
          <AlertCircle className="h-4 w-4" />
          <span className="text-xs">Conflict</span>
        </div>
      )}
    </div>
  );
}
