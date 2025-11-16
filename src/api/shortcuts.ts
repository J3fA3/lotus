/**
 * API client for keyboard shortcuts configuration
 */
import { ShortcutConfig } from "@/types/shortcuts";

// Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

/**
 * Fetch all shortcuts from backend
 */
export async function fetchShortcuts(userId?: number): Promise<ShortcutConfig[]> {
  try {
    const url = new URL(`${API_BASE_URL}/shortcuts`);
    if (userId) {
      url.searchParams.append('user_id', userId.toString());
    }

    const response = await fetch(url.toString());

    if (!response.ok) {
      throw new Error(`Failed to fetch shortcuts: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while fetching shortcuts");
  }
}

/**
 * Fetch default shortcuts
 */
export async function fetchDefaultShortcuts(): Promise<ShortcutConfig[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/shortcuts/defaults`);

    if (!response.ok) {
      throw new Error(`Failed to fetch default shortcuts: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while fetching default shortcuts");
  }
}

/**
 * Update a specific shortcut
 */
export async function updateShortcut(
  shortcutId: string,
  updates: {
    key?: string;
    modifiers?: string[];
    enabled?: boolean;
  },
  userId?: number
): Promise<ShortcutConfig> {
  try {
    const url = new URL(`${API_BASE_URL}/shortcuts/${shortcutId}`);
    if (userId) {
      url.searchParams.append('user_id', userId.toString());
    }

    const response = await fetch(url.toString(), {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(updates),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to update shortcut");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while updating shortcut");
  }
}

/**
 * Bulk update shortcuts
 */
export async function bulkUpdateShortcuts(shortcuts: Partial<ShortcutConfig>[]): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/shortcuts/bulk-update`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ shortcuts }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to bulk update shortcuts");
    }
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while bulk updating shortcuts");
  }
}

/**
 * Reset shortcuts to defaults
 */
export async function resetShortcuts(userId?: number): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/shortcuts/reset`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ user_id: userId }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to reset shortcuts");
    }
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while resetting shortcuts");
  }
}

/**
 * Export shortcuts configuration
 */
export async function exportShortcuts(userId?: number): Promise<any> {
  try {
    const url = new URL(`${API_BASE_URL}/shortcuts/export`);
    if (userId) {
      url.searchParams.append('user_id', userId.toString());
    }

    const response = await fetch(url.toString());

    if (!response.ok) {
      throw new Error(`Failed to export shortcuts: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while exporting shortcuts");
  }
}

/**
 * Import shortcuts configuration
 */
export async function importShortcuts(config: any): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/shortcuts/import`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(config),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to import shortcuts");
    }
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while importing shortcuts");
  }
}
