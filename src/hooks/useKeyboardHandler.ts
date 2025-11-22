/**
 * Keyboard event handler for shortcuts
 */
import { useEffect, useCallback, useRef } from 'react';
import { ShortcutConfig, Modifier, ShortcutHandler } from '@/types/shortcuts';

/**
 * Check if an event matches a shortcut configuration
 */
export function matchesShortcut(event: KeyboardEvent, shortcut: ShortcutConfig): boolean {
  if (!shortcut.enabled) {
    return false;
  }

  // Normalize key for comparison
  const eventKey = normalizeKey(event.key);
  const shortcutKey = normalizeKey(shortcut.key);

  // Check if keys match
  if (eventKey !== shortcutKey) {
    return false;
  }

  // Check modifiers
  const requiredModifiers = shortcut.modifiers || [];
  const ctrl = requiredModifiers.includes('ctrl');
  const shift = requiredModifiers.includes('shift');
  const alt = requiredModifiers.includes('alt');
  const meta = requiredModifiers.includes('meta');

  return (
    event.ctrlKey === ctrl &&
    event.shiftKey === shift &&
    event.altKey === alt &&
    event.metaKey === meta
  );
}

/**
 * Normalize key name for consistent comparison
 */
function normalizeKey(key: string): string {
  // Handle special keys
  const specialKeys: Record<string, string> = {
    ' ': 'Space',
    '/': '/',
    '?': '?',
  };

  if (specialKeys[key]) {
    return specialKeys[key];
  }

  // Normalize case
  if (key.length === 1) {
    return key.toLowerCase();
  }

  return key;
}

/**
 * Check if a dialog or modal is currently open
 * Only checks for blocking dialogs (AlertDialog) that should prevent shortcuts
 */
function isDialogOpen(): boolean {
  // Only check for AlertDialog - these are blocking dialogs that should prevent shortcuts
  // Regular dialogs (like Sheet) should not block shortcuts
  const alertDialog = document.querySelector('[role="alertdialog"]');
  
  if (!alertDialog) {
    return false;
  }
  
  const element = alertDialog as HTMLElement;
  const style = window.getComputedStyle(element);
  const dataState = element.getAttribute('data-state');
  const ariaHidden = element.getAttribute('aria-hidden');
  
  // Dialog is open if:
  // - data-state is 'open' AND
  // - display is not 'none' AND visibility is not 'hidden'
  const isOpen = dataState === 'open' && 
                 style.display !== 'none' && 
                 style.visibility !== 'hidden' &&
                 ariaHidden !== 'true';
  
  return isOpen;
}

/**
 * Check if we should ignore keyboard events (e.g., when typing in inputs)
 */
export function shouldIgnoreEvent(event: KeyboardEvent): boolean {
  // If a dialog is open, ignore all shortcuts except Escape
  if (isDialogOpen() && event.key !== 'Escape') {
    return true;
  }

  const target = event.target as HTMLElement;
  const tagName = target.tagName.toLowerCase();
  const isEditable = target.isContentEditable;

  // Ignore if typing in input fields, textareas, or contentEditable elements
  if (tagName === 'input' || tagName === 'textarea' || isEditable) {
    // Allow Escape key even in input fields
    if (event.key === 'Escape') {
      return false;
    }
    return true;
  }

  return false;
}

/**
 * Hook to register keyboard shortcut handlers
 */
export function useKeyboardHandler(
  shortcuts: ShortcutConfig[],
  handlers: Map<string, ShortcutHandler>
) {
  const handlersRef = useRef(handlers);
  const sequenceRef = useRef<string[]>([]);
  const sequenceTimeoutRef = useRef<NodeJS.Timeout>();

  // Update ref when handlers change
  useEffect(() => {
    handlersRef.current = handlers;
  }, [handlers]);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Ignore if typing in input fields
      if (shouldIgnoreEvent(event)) {
        return;
      }

      // Track key sequence for multi-key shortcuts (like "gg")
      const key = event.key.toLowerCase();
      sequenceRef.current.push(key);

      // Clear sequence after 1 second
      if (sequenceTimeoutRef.current) {
        clearTimeout(sequenceTimeoutRef.current);
      }
      sequenceTimeoutRef.current = setTimeout(() => {
        sequenceRef.current = [];
      }, 1000);

      // Check for sequence shortcuts (e.g., "gg" for go to first)
      const sequence = sequenceRef.current.join('');
      if (sequence === 'gg') {
        const handler = handlersRef.current.get('first_task');
        if (handler) {
          event.preventDefault();
          handler.callback(event);
          sequenceRef.current = [];
          return;
        }
      }

      // Find matching shortcut
      for (const shortcut of shortcuts) {
        if (matchesShortcut(event, shortcut)) {
          const handler = handlersRef.current.get(shortcut.action);
          if (handler) {
            event.preventDefault();
            event.stopPropagation();
            handler.callback(event);
            return;
          }
        }
      }
    },
    [shortcuts]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      if (sequenceTimeoutRef.current) {
        clearTimeout(sequenceTimeoutRef.current);
      }
    };
  }, [handleKeyDown]);
}

/**
 * Hook to register a single shortcut handler
 */
export function useShortcut(
  action: string,
  callback: (event: KeyboardEvent) => void,
  dependencies: any[] = []
) {
  const callbackRef = useRef(callback);

  // Update callback ref
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback, ...dependencies]);

  return useCallback((event: KeyboardEvent) => {
    callbackRef.current(event);
  }, []);
}

/**
 * Get human-readable shortcut display text
 */
export function getShortcutDisplay(shortcut: ShortcutConfig): string {
  const modifiers = shortcut.modifiers || [];
  const parts: string[] = [];

  // Add modifiers
  if (modifiers.includes('ctrl')) parts.push('Ctrl');
  if (modifiers.includes('shift')) parts.push('Shift');
  if (modifiers.includes('alt')) parts.push('Alt');
  if (modifiers.includes('meta')) parts.push('⌘');

  // Add key
  let key = shortcut.key;
  if (key === ' ') key = 'Space';
  if (key === 'ArrowUp') key = '↑';
  if (key === 'ArrowDown') key = '↓';
  if (key === 'ArrowLeft') key = '←';
  if (key === 'ArrowRight') key = '→';

  parts.push(key.length === 1 ? key.toUpperCase() : key);

  return parts.join('+');
}
