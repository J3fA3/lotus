/**
 * API client for task management backend
 */
import { Task } from "@/types/task";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

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
  const response = await fetch(`${API_BASE_URL}/tasks`);

  if (!response.ok) {
    throw new Error(`Failed to fetch tasks: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Create a new task
 */
export async function createTask(task: Partial<Task>): Promise<Task> {
  const response = await fetch(`${API_BASE_URL}/tasks`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(task),
  });

  if (!response.ok) {
    throw new Error(`Failed to create task: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Update an existing task
 */
export async function updateTask(taskId: string, updates: Partial<Task>): Promise<Task> {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(updates),
  });

  if (!response.ok) {
    throw new Error(`Failed to update task: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Delete a task
 */
export async function deleteTask(taskId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(`Failed to delete task: ${response.statusText}`);
  }
}

/**
 * Infer tasks from text using AI
 */
export async function inferTasksFromText(
  text: string,
  assignee: string = "You"
): Promise<InferenceResponse> {
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
}

/**
 * Infer tasks from PDF file using AI
 */
export async function inferTasksFromPDF(
  file: File,
  assignee: string = "You"
): Promise<InferenceResponse> {
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
}

/**
 * Check backend health
 */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`);
  }

  return response.json();
}
