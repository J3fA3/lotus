/**
 * Shortcut Context - Manages keyboard shortcuts with remote configuration
 */
import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { ShortcutConfig, ShortcutContextValue, ShortcutHandler } from '@/types/shortcuts';
import * as shortcutApi from '@/api/shortcuts';
import { useKeyboardHandler } from '@/hooks/useKeyboardHandler';
import { toast } from 'sonner';

const ShortcutContext = createContext<ShortcutContextValue | undefined>(undefined);

interface ShortcutProviderProps {
  children: React.ReactNode;
  userId?: number; // Optional user ID for per-user shortcuts
}

export function ShortcutProvider({ children, userId }: ShortcutProviderProps) {
  const [shortcuts, setShortcuts] = useState<ShortcutConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const handlersRef = useRef<Map<string, ShortcutHandler>>(new Map());

  // Load shortcuts from backend
  const loadShortcuts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await shortcutApi.fetchShortcuts(userId);
      setShortcuts(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load shortcuts';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  // Initial load
  useEffect(() => {
    loadShortcuts();
  }, [loadShortcuts]);

  // Register keyboard handler
  useKeyboardHandler(shortcuts, handlersRef.current);

  /**
   * Register a shortcut handler
   */
  const registerHandler = useCallback((handler: ShortcutHandler): (() => void) => {
    handlersRef.current.set(handler.action, handler);

    // Return unregister function
    return () => {
      handlersRef.current.delete(handler.action);
    };
  }, []);

  /**
   * Unregister a shortcut handler
   */
  const unregisterHandler = useCallback((action: string) => {
    handlersRef.current.delete(action);
  }, []);

  /**
   * Update a shortcut configuration
   */
  const updateShortcut = useCallback(
    async (id: string, updates: Partial<ShortcutConfig>) => {
      try {
        const updated = await shortcutApi.updateShortcut(
          id,
          {
            key: updates.key,
            modifiers: updates.modifiers as string[],
            enabled: updates.enabled,
          },
          userId
        );

        // Update local state with the full updated object
        setShortcuts((prev) =>
          prev.map((s) => (s.id === id ? { ...s, ...updated } : s))
        );

        toast.success('Shortcut updated', { duration: 2000 });
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update shortcut';
        console.error('Shortcut update error:', err);
        toast.error(message);
        throw err;
      }
    },
    [userId]
  );

  /**
   * Reset shortcuts to defaults
   */
  const resetShortcuts = useCallback(
    async (resetUserId?: number) => {
      try {
        await shortcutApi.resetShortcuts(resetUserId ?? userId);
        await loadShortcuts();
        toast.success('Shortcuts reset to defaults');
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to reset shortcuts';
        toast.error(message);
        throw err;
      }
    },
    [userId, loadShortcuts]
  );

  /**
   * Export shortcuts configuration
   */
  const exportShortcuts = useCallback(
    async (exportUserId?: number) => {
      try {
        const config = await shortcutApi.exportShortcuts(exportUserId ?? userId);
        return config;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to export shortcuts';
        toast.error(message);
        throw err;
      }
    },
    [userId]
  );

  /**
   * Import shortcuts configuration
   */
  const importShortcuts = useCallback(
    async (config: any) => {
      try {
        await shortcutApi.importShortcuts(config);
        await loadShortcuts();
        toast.success('Shortcuts imported successfully');
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to import shortcuts';
        toast.error(message);
        throw err;
      }
    },
    [loadShortcuts]
  );

  /**
   * Get shortcut by action name
   */
  const getShortcutByAction = useCallback(
    (action: string): ShortcutConfig | undefined => {
      return shortcuts.find((s) => s.action === action);
    },
    [shortcuts]
  );

  /**
   * Check if a keyboard event matches a specific action
   */
  const isShortcutPressed = useCallback(
    (event: KeyboardEvent, action: string): boolean => {
      const shortcut = getShortcutByAction(action);
      if (!shortcut || !shortcut.enabled) {
        return false;
      }

      const key = event.key.toLowerCase();
      const shortcutKey = shortcut.key.toLowerCase();

      if (key !== shortcutKey) {
        return false;
      }

      const modifiers = shortcut.modifiers || [];
      return (
        event.ctrlKey === modifiers.includes('ctrl') &&
        event.shiftKey === modifiers.includes('shift') &&
        event.altKey === modifiers.includes('alt') &&
        event.metaKey === modifiers.includes('meta')
      );
    },
    [getShortcutByAction]
  );

  const value: ShortcutContextValue = {
    shortcuts,
    loading,
    error,
    registerHandler,
    unregisterHandler,
    updateShortcut,
    resetShortcuts,
    exportShortcuts,
    importShortcuts,
    getShortcutByAction,
    isShortcutPressed,
  };

  return <ShortcutContext.Provider value={value}>{children}</ShortcutContext.Provider>;
}

/**
 * Hook to use shortcut context
 */
export function useShortcuts() {
  const context = useContext(ShortcutContext);
  if (!context) {
    throw new Error('useShortcuts must be used within a ShortcutProvider');
  }
  return context;
}

/**
 * Hook to register a keyboard shortcut
 */
export function useRegisterShortcut(
  action: string,
  callback: (event: KeyboardEvent) => void,
  options?: {
    category?: string;
    priority?: number;
  }
) {
  const { registerHandler, unregisterHandler } = useShortcuts();
  const callbackRef = useRef(callback);

  // Update callback ref
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    const handler: ShortcutHandler = {
      action,
      callback: (event) => callbackRef.current(event),
      category: options?.category as any,
      priority: options?.priority,
    };

    const unregister = registerHandler(handler);

    return () => {
      unregister();
    };
  }, [action, registerHandler, options?.category, options?.priority]);
}
