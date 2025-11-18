/**
 * API client for Cognitive Nexus - LangGraph Agentic System
 */
import {
  ContextIngestResponse,
  ReasoningTrace,
  Entity,
  Relationship,
  ContextSummary,
} from "@/types/cognitivenexus";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

/**
 * Ingest context and process through LangGraph agents
 */
export async function ingestContext(
  content: string,
  sourceType: "slack" | "transcript" | "manual" = "manual",
  sourceIdentifier?: string
): Promise<ContextIngestResponse> {
  if (!content.trim()) {
    throw new Error("Context content cannot be empty");
  }

  try {
    const response = await fetch(`${API_BASE_URL}/context/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        content,
        source_type: sourceType,
        source_identifier: sourceIdentifier,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to process context");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred during context processing");
  }
}

/**
 * Get reasoning trace for a context item
 */
export async function getReasoningTrace(contextItemId: number): Promise<ReasoningTrace> {
  try {
    const response = await fetch(`${API_BASE_URL}/context/${contextItemId}/reasoning`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to fetch reasoning trace");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while fetching reasoning trace");
  }
}

/**
 * Get entities extracted from a context item
 */
export async function getEntities(contextItemId: number): Promise<Entity[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/context/${contextItemId}/entities`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to fetch entities");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while fetching entities");
  }
}

/**
 * Get relationships inferred from a context item
 */
export async function getRelationships(contextItemId: number): Promise<Relationship[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/context/${contextItemId}/relationships`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to fetch relationships");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while fetching relationships");
  }
}

/**
 * Get recently processed context items
 */
export async function getRecentContexts(limit: number = 10): Promise<ContextSummary[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/context/recent?limit=${limit}`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to fetch recent contexts");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while fetching recent contexts");
  }
}

/**
 * Delete a context item and all associated data
 */
export async function deleteContext(contextItemId: number): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/context/${contextItemId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to delete context");
    }
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while deleting context");
  }
}
