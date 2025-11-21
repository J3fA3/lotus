/**
 * Calendar API Client
 * 
 * Provides functions for calendar integration and task scheduling
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

/**
 * Time block suggestion from scheduling agent
 */
export interface TimeBlockSuggestion {
  id: number;
  task_id: string;
  task_title: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  confidence: number;
  quality_score: number;
  reasoning: string;
  status: string;
}

/**
 * Scheduling response
 */
export interface SchedulingResponse {
  suggestions: TimeBlockSuggestion[];
  total: number;
  message?: string;
}

/**
 * Auth status response
 */
export interface AuthStatusResponse {
  authorized: boolean;
  user_id: number;
}

/**
 * Approve block response
 */
export interface ApproveBlockResponse {
  success: boolean;
  block_id: number;
  event_id: string;
  event_link: string;
  message: string;
}

/**
 * Check if user has authorized Google Calendar
 */
export async function checkCalendarAuth(userId: number = 1): Promise<AuthStatusResponse> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/auth/google/status?user_id=${userId}`
    );

    if (!response.ok) {
      throw new Error(`Failed to check calendar auth: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while checking calendar auth");
  }
}

/**
 * Get authorization URL to start OAuth flow
 */
export async function getAuthorizationUrl(userId: number = 1): Promise<{ authorization_url: string; message: string }> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/auth/google/authorize?user_id=${userId}`
    );

    if (!response.ok) {
      throw new Error(`Failed to get authorization URL: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while getting authorization URL");
  }
}

/**
 * Schedule a specific task - generates time block suggestions
 * Note: Backend schedules all tasks, we filter on frontend
 */
export async function scheduleTask(
  taskId: string,
  userId: number = 1,
  daysAhead: number = 7
): Promise<SchedulingResponse> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/calendar/schedule-tasks?user_id=${userId}&days_ahead=${daysAhead}&max_suggestions=5`,
      {
        method: "POST",
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to generate scheduling suggestions");
    }

    const data = await response.json();
    
    // Filter suggestions for this specific task
    const filteredSuggestions = data.suggestions.filter(
      (s: TimeBlockSuggestion) => s.task_id === taskId
    );

    return {
      suggestions: filteredSuggestions,
      total: filteredSuggestions.length,
      message: data.message
    };
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while scheduling task");
  }
}

/**
 * Schedule all tasks - generates suggestions for all active tasks
 */
export async function scheduleAllTasks(
  userId: number = 1,
  daysAhead: number = 7,
  maxSuggestions: number = 10
): Promise<SchedulingResponse> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/calendar/schedule-tasks?user_id=${userId}&days_ahead=${daysAhead}&max_suggestions=${maxSuggestions}`,
      {
        method: "POST",
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to generate scheduling suggestions");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while scheduling tasks");
  }
}

/**
 * Approve a time block and create calendar event
 */
export async function approveTimeBlock(
  blockId: number,
  userId: number = 1
): Promise<ApproveBlockResponse> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/calendar/approve-block?block_id=${blockId}&user_id=${userId}`,
      {
        method: "POST",
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to approve time block");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while approving time block");
  }
}
