/**
 * AI Assistant API Client
 *
 * This module provides TypeScript client functions for the AI Assistant API.
 */

import { toast } from "sonner";

const API_BASE = "/api/assistant";

// ============================================================================
// TYPES
// ============================================================================

export interface TaskProposal {
  id: string;
  title: string;
  description: string | null;
  assignee: string;
  due_date: string | null;
  priority: string | null;
  value_stream: string | null;
  tags: string[];
  status: string;
  confidence: number;
  confidence_factors: Record<string, number>;
  operation: string;
  reasoning: string;
}

export interface EnrichmentOperation {
  operation: string;
  task_id: string;
  data: Record<string, any>;
  reasoning: string;
}

export interface ProcessMessageRequest {
  content: string;
  source_type?: string;
  session_id?: string;
  source_identifier?: string;
  user_id?: string;
}

export interface ProcessMessageResponse {
  message: string;
  session_id: string;
  recommended_action: "auto" | "ask" | "clarify" | "store_only" | "answer_question";
  needs_approval: boolean;
  answer_text: string | null;  // For question responses
  proposed_tasks: TaskProposal[];
  enrichment_operations: EnrichmentOperation[];
  created_tasks: any[];
  enriched_tasks: any[];
  clarifying_questions: string[];
  overall_confidence: number;
  reasoning_trace: string[];
  context_item_id: number | null;
}

export interface ApproveTasksRequest {
  session_id: string;
  task_proposals: any[];
  enrichment_operations?: any[];
  context_item_id?: number | null;
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  metadata: Record<string, any> | null;
  created_at: string;
}

// ============================================================================
// API FUNCTIONS
// ============================================================================

export async function processMessage(
  request: ProcessMessageRequest
): Promise<ProcessMessageResponse> {
  try {
    const response = await fetch(`${API_BASE}/process`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to process message");
    }

    return await response.json();
  } catch (error) {
    console.error("Error processing message:", error);
    toast.error("Failed to process message");
    throw error;
  }
}

export async function processMessageWithFile(
  request: ProcessMessageRequest & { file: File }
): Promise<ProcessMessageResponse> {
  try {
    const formData = new FormData();
    formData.append("content", request.content);
    formData.append("source_type", request.source_type || "pdf");
    if (request.session_id) {
      formData.append("session_id", request.session_id);
    }
    if (request.source_identifier) {
      formData.append("source_identifier", request.source_identifier);
    }
    if (request.user_id) {
      formData.append("user_id", request.user_id);
    }
    formData.append("file", request.file);

    const response = await fetch(`${API_BASE}/process-with-file`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to process message with file");
    }

    return await response.json();
  } catch (error) {
    console.error("Error processing message with file:", error);
    toast.error("Failed to process file");
    throw error;
  }
}

export async function processPdfFast(
  file: File,
  session_id?: string
): Promise<{
  message: string;
  session_id: string;
  created_tasks: any[];
  entities_found: number;
  relationships_found: number;
  context_item_id: number;
  filename: string;
}> {
  try {
    const formData = new FormData();
    formData.append("file", file);
    if (session_id) {
      formData.append("session_id", session_id);
    }

    const response = await fetch(`${API_BASE}/process-pdf-fast`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to process PDF");
    }

    toast.success("PDF processed successfully!");
    return await response.json();
  } catch (error) {
    console.error("Error processing PDF:", error);
    toast.error("Failed to process PDF");
    throw error;
  }
}

export async function approveTasks(
  request: ApproveTasksRequest
): Promise<{ created_tasks: any[]; enriched_tasks: any[]; message: string }> {
  try {
    const response = await fetch(`${API_BASE}/approve`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to approve tasks");
    }

    const result = await response.json();
    toast.success(result.message);
    return result;
  } catch (error) {
    console.error("Error approving tasks:", error);
    toast.error("Failed to approve tasks");
    throw error;
  }
}

export async function rejectTasks(
  session_id: string,
  task_ids: string[],
  reason?: string,
  context_item_id?: number | null
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/reject`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        session_id,
        task_ids,
        reason,
        context_item_id,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to reject tasks");
    }

    toast.success("Tasks rejected");
  } catch (error) {
    console.error("Error rejecting tasks:", error);
    toast.error("Failed to reject tasks");
    throw error;
  }
}

export async function recordFeedback(
  task_id: string,
  event_type: "approved" | "edited" | "rejected" | "deleted",
  original_data?: any,
  modified_data?: any,
  context_item_id?: number | null
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/feedback`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        task_id,
        event_type,
        original_data,
        modified_data,
        context_item_id,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to record feedback");
    }
  } catch (error) {
    console.error("Error recording feedback:", error);
    // Don't show toast for feedback errors (silent tracking)
  }
}

export async function getChatHistory(
  session_id: string,
  limit: number = 50
): Promise<ChatMessage[]> {
  try {
    const response = await fetch(
      `${API_BASE}/history/${session_id}?limit=${limit}`
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to get chat history");
    }

    const result = await response.json();
    return result.messages;
  } catch (error) {
    console.error("Error getting chat history:", error);
    toast.error("Failed to load chat history");
    throw error;
  }
}
