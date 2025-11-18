/**
 * API client for task management backend
 */
import {
  Task,
  Document,
  DocumentUploadResponse,
  DocumentListResponse,
  KnowledgeBaseSummary
} from "@/types/task";

// Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";
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
    console.log('[searchTasks] Calling API:', url);

    const response = await fetch(url);
    console.log('[searchTasks] Response status:', response.status);

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
    console.log('[searchTasks] Response data:', data);
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

// ============= Document Management API =============

/**
 * Supported document file extensions
 */
export const SUPPORTED_DOCUMENT_TYPES = [
  ".pdf",
  ".docx",
  ".doc",
  ".txt",
  ".md",
  ".markdown",
  ".xlsx",
  ".xls",
] as const;

/**
 * MIME types for supported documents
 */
export const DOCUMENT_MIME_TYPES: Record<string, string> = {
  ".pdf": "application/pdf",
  ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ".doc": "application/msword",
  ".txt": "text/plain",
  ".md": "text/markdown",
  ".markdown": "text/markdown",
  ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  ".xls": "application/vnd.ms-excel",
};

/**
 * Check if file type is supported
 */
export function isSupportedDocumentType(filename: string): boolean {
  const extension = filename.toLowerCase().substring(filename.lastIndexOf("."));
  return SUPPORTED_DOCUMENT_TYPES.includes(extension as any);
}

/**
 * Get friendly file type name
 */
export function getFileTypeName(filename: string): string {
  const extension = filename.toLowerCase().substring(filename.lastIndexOf("."));
  const typeNames: Record<string, string> = {
    ".pdf": "PDF",
    ".docx": "Word Document",
    ".doc": "Word Document",
    ".txt": "Text File",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".xlsx": "Excel Spreadsheet",
    ".xls": "Excel Spreadsheet",
  };
  return typeNames[extension] || "Document";
}

/**
 * Upload document to knowledge base
 */
export async function uploadDocument(
  file: File,
  category: "tasks" | "inference" | "knowledge" = "knowledge",
  taskId?: string
): Promise<DocumentUploadResponse> {
  if (!file) {
    throw new Error("File is required");
  }

  if (!isSupportedDocumentType(file.name)) {
    throw new Error(
      `Unsupported file type. Supported types: ${SUPPORTED_DOCUMENT_TYPES.join(", ")}`
    );
  }

  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("category", category);
    if (taskId) {
      formData.append("task_id", taskId);
    }

    const response = await fetch(`${API_BASE_URL}/documents/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to upload document");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred during document upload");
  }
}

/**
 * Infer tasks from any supported document type using AI
 */
export async function inferTasksFromDocument(
  file: File,
  assignee: string = DEFAULT_ASSIGNEE
): Promise<InferenceResponse> {
  if (!file) {
    throw new Error("File is required");
  }

  if (!isSupportedDocumentType(file.name)) {
    throw new Error(
      `Unsupported file type. Supported types: ${SUPPORTED_DOCUMENT_TYPES.join(", ")}`
    );
  }

  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("assignee", assignee);

    const response = await fetch(`${API_BASE_URL}/documents/upload-for-inference`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to infer tasks from document");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred during document processing");
  }
}

/**
 * List documents with optional filtering
 */
export async function listDocuments(
  category?: "tasks" | "inference" | "knowledge",
  taskId?: string
): Promise<DocumentListResponse> {
  try {
    const params = new URLSearchParams();
    if (category) params.append("category", category);
    if (taskId) params.append("task_id", taskId);

    const url = `${API_BASE_URL}/documents${params.toString() ? `?${params.toString()}` : ""}`;
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Failed to list documents: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while listing documents");
  }
}

/**
 * Get document metadata
 */
export async function getDocument(documentId: string): Promise<Document> {
  if (!documentId) {
    throw new Error("Document ID is required");
  }

  try {
    const response = await fetch(`${API_BASE_URL}/documents/${documentId}`);

    if (!response.ok) {
      throw new Error(`Failed to get document: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while fetching document");
  }
}

/**
 * Download document file
 */
export async function downloadDocument(documentId: string, filename: string): Promise<void> {
  if (!documentId) {
    throw new Error("Document ID is required");
  }

  try {
    const response = await fetch(`${API_BASE_URL}/documents/${documentId}/download`);

    if (!response.ok) {
      throw new Error(`Failed to download document: ${response.statusText}`);
    }

    // Create blob and trigger download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while downloading document");
  }
}

/**
 * Delete document
 */
export async function deleteDocument(documentId: string): Promise<void> {
  if (!documentId) {
    throw new Error("Document ID is required");
  }

  try {
    const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to delete document");
    }
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while deleting document");
  }
}

/**
 * Search documents by text content
 */
export async function searchDocuments(
  query: string,
  category?: "tasks" | "inference" | "knowledge",
  limit: number = 10
): Promise<{ query: string; results: Document[]; total: number }> {
  if (!query.trim()) {
    throw new Error("Search query is required");
  }

  try {
    const params = new URLSearchParams();
    if (category) params.append("category", category);
    params.append("limit", limit.toString());

    const url = `${API_BASE_URL}/documents/search/${encodeURIComponent(query)}${
      params.toString() ? `?${params.toString()}` : ""
    }`;
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Failed to search documents: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while searching documents");
  }
}

/**
 * Get knowledge base summary statistics
 */
export async function getKnowledgeBaseSummary(): Promise<KnowledgeBaseSummary> {
  try {
    const response = await fetch(`${API_BASE_URL}/knowledge-base/summary`);

    if (!response.ok) {
      throw new Error(`Failed to get knowledge base summary: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while fetching knowledge base summary");
  }
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}
