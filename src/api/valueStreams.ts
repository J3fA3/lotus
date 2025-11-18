/**
 * API client for value stream management
 */
import { ValueStream } from "@/types/task";

// Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

/**
 * Fetch all value streams from backend
 */
export async function fetchValueStreams(): Promise<ValueStream[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/value-streams`);

    if (!response.ok) {
      throw new Error(`Failed to fetch value streams: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while fetching value streams");
  }
}

/**
 * Create a new value stream
 */
export async function createValueStream(data: { name: string; color?: string }): Promise<ValueStream> {
  if (!data.name?.trim()) {
    throw new Error("Value stream name is required");
  }

  try {
    const response = await fetch(`${API_BASE_URL}/value-streams`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to create value stream");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while creating value stream");
  }
}

/**
 * Delete a value stream
 */
export async function deleteValueStream(valueStreamId: string): Promise<void> {
  if (!valueStreamId) {
    throw new Error("Value stream ID is required");
  }

  try {
    const response = await fetch(`${API_BASE_URL}/value-streams/${valueStreamId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to delete value stream");
    }
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while deleting value stream");
  }
}
