/**
 * API client for task management backend
 */
import { Task } from "@/types/task";

// Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
const DEFAULT_ASSIGNEE = "You";

/**
 * API response for task inference
 */
export interface InferenceResponse {
  tasks: Task[];
  inference_time_ms: number;
  model_used: string;
  tasks_inferred: number;
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
    const response = await fetch(`${API_BASE_URL}/tasks`);

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
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to delete task");
    }
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while deleting task");
  }
}

/**
 * Infer tasks from text using AI
 */
export async function inferTasksFromText(
  text: string,
  assignee: string = DEFAULT_ASSIGNEE
): Promise<InferenceResponse> {
  if (!text.trim()) {
    throw new Error("Text cannot be empty");
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/infer-tasks`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text, assignee }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to infer tasks");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred during task inference");
  }
}

/**
 * Infer tasks from PDF file using AI
 */
export async function inferTasksFromPDF(
  file: File,
  assignee: string = DEFAULT_ASSIGNEE
): Promise<InferenceResponse> {
  if (!file) {
    throw new Error("File is required");
  }
  
  if (file.type !== "application/pdf") {
    throw new Error("Only PDF files are supported");
  }
  
  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("assignee", assignee);

    const response = await fetch(`${API_BASE_URL}/infer-tasks-pdf`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to infer tasks from PDF");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred during PDF processing");
  }
}

/**
 * Check backend health
 */
export async function checkHealth(): Promise<HealthResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

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
