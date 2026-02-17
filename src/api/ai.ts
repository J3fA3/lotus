/**
 * API client for AI assist (Intelligence Flywheel)
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export interface AIAssistResponse {
  response: string;
  similar_cases: number;
  model: string;
}

/**
 * Ask Lotus for AI-powered task assistance
 */
export async function askLotus(
  taskId: string,
  prompt?: string
): Promise<AIAssistResponse> {
  const response = await fetch(`${API_BASE_URL}/ai/assist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_id: taskId, prompt: prompt || undefined }),
  });

  if (!response.ok) {
    throw new Error(`AI assist failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Rebuild the semantic search index
 */
export async function reindexCases(): Promise<{ message: string; count: number }> {
  const response = await fetch(`${API_BASE_URL}/ai/reindex`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`Reindex failed: ${response.statusText}`);
  }

  return response.json();
}
