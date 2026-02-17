/**
 * API client for task management backend
 */
import {
  Task,
} from "@/types/task";

// Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";
const DEFAULT_ASSIGNEE = "You";
const FETCH_TIMEOUT = 10000; // 10 seconds

/**
 * Fetch with timeout wrapper
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout: number = FETCH_TIMEOUT
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error(`Request timeout: ${url} took longer than ${timeout}ms`);
    }
    throw error;
  }
}

/**
 * Health check response
 */
export interface HealthResponse {
  status: string;
  ollama_connected: boolean;
  database_connected: boolean;
  model: string;
}

/**
 * Fetch all tasks from backend
 */
export async function fetchTasks(): Promise<Task[]> {
  try {
    const response = await fetchWithTimeout(`${API_BASE_URL}/tasks`);

    if (!response.ok) {
      throw new Error(`Failed to fetch tasks: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while fetching tasks");
  }
}

/**
 * Create a new task
 */
export async function createTask(task: Partial<Task>): Promise<Task> {
  if (!task.title?.trim()) {
    throw new Error("Task title is required");
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/tasks`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(task),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to create task");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while creating task");
  }
}

/**
 * Update an existing task
 */
export async function updateTask(taskId: string, updates: Partial<Task>): Promise<Task> {
  if (!taskId) {
    throw new Error("Task ID is required");
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(updates),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to update task");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while updating task");
  }
}

/**
 * Delete a task
 */
export async function deleteTask(taskId: string): Promise<void> {
  if (!taskId) {
    throw new Error("Task ID is required");
  }

  try {
    const response = await fetchWithTimeout(`${API_BASE_URL}/tasks/${taskId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to delete task");
    }
    
    // Read response body to ensure connection is complete
    await response.json().catch(() => {
      // If response has no body, that's fine - just ensure the request completed
    });
  } catch (error) {
    if (error instanceof Error) {
      // Handle timeout specifically
      if (error.name === 'AbortError' || error.message.includes('aborted')) {
        throw new Error("Request timed out. Please try again.");
      }
      throw error;
    }
    throw new Error("Unknown error occurred while deleting task");
  }
}

/**
 * Search result with similarity score
 */
export interface TaskSearchResult {
  task: Task;
  similarity_score: number;
}

/**
 * Search response
 */
export interface TaskSearchResponse {
  query: string;
  results: TaskSearchResult[];
  total: number;
  threshold: number;
}

/**
 * Search tasks using semantic similarity
 */
export async function searchTasks(
  query: string,
  limit: number = 50,
  threshold: number = 0.3
): Promise<TaskSearchResponse> {
  if (!query.trim()) {
    return {
      query: "",
      results: [],
      total: 0,
      threshold
    };
  }

  try {
    const params = new URLSearchParams();
    params.append("limit", limit.toString());
    params.append("threshold", threshold.toString());

    const url = `${API_BASE_URL}/tasks/search/${encodeURIComponent(query)}?${params.toString()}`;

    const response = await fetch(url);

    if (!response.ok) {
      const errorBody = await response.text();
      console.error('[searchTasks] Error response:', errorBody);

      let errorMessage = `Failed to search tasks: ${response.statusText}`;
      try {
        const errorJson = JSON.parse(errorBody);
        if (errorJson.detail) {
          errorMessage = errorJson.detail;
        }
      } catch (e) {
        // Couldn't parse JSON, use text
        if (errorBody) {
          errorMessage = errorBody;
        }
      }

      throw new Error(errorMessage);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('[searchTasks] Error:', error);
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while searching tasks");
  }
}

/**
 * Check backend health
 */
export async function checkHealth(): Promise<HealthResponse> {
  try {
    const response = await fetchWithTimeout(`${API_BASE_URL}/health`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    }, 5000); // Shorter timeout for health check

    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred during health check");
  }
}

