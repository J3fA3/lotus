export type TaskStatus = "todo" | "doing" | "done";

export interface Task {
  id: string;
  title: string;
  status: TaskStatus;
  assignee: string;
  startDate?: string;
  dueDate?: string;
  valueStream?: string;
  description?: string;
  attachments: string[];
  comments: Comment[];
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Comment {
  id: string;
  text: string;
  author: string;
  createdAt: string;
}

export interface Document {
  id: string;
  file_id: string;
  original_filename: string;
  file_extension: string;
  mime_type?: string;
  file_hash: string;
  size_bytes: number;
  storage_path: string;
  category: "tasks" | "inference" | "knowledge";
  text_preview?: string;
  page_count?: number;
  task_id?: string;
  inference_history_id?: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResponse {
  document: Document;
  message: string;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
  category?: string;
}

export interface KnowledgeBaseSummary {
  total_documents: number;
  total_size_bytes: number;
  total_size_mb: number;
  by_category: Record<string, number>;
  by_extension: Record<string, number>;
  last_updated: string;
}
