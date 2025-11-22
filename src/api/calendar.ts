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
    // Pass task_id to backend so it only schedules this specific task
    const response = await fetch(
      `${API_BASE_URL}/calendar/schedule-tasks?user_id=${userId}&days_ahead=${daysAhead}&max_suggestions=5&task_id=${encodeURIComponent(taskId)}`,
      {
        method: "POST",
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to generate scheduling suggestions");
    }

    const data = await response.json();
    
    // Backend now filters by task_id, so all suggestions should be for this task
    // But keep filter as safety check
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

/**
 * Scheduled block information
 */
export interface ScheduledBlockInfo {
  id: number;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  calendar_event_id: string | null;
  quality_score: number | null;
  confidence_score: number | null;
}

/**
 * Task scheduled status response
 */
export interface TaskScheduledResponse {
  scheduled: boolean;
  block: ScheduledBlockInfo | null;
}

/**
 * Check if a task is already scheduled
 */
export async function checkTaskScheduled(
  taskId: string,
  userId: number = 1
): Promise<TaskScheduledResponse> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/calendar/task-scheduled?task_id=${encodeURIComponent(taskId)}&user_id=${userId}`
    );

    if (!response.ok) {
      throw new Error(`Failed to check task scheduled status: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while checking task scheduled status");
  }
}

/**
 * Cancel a scheduled block for a task (removes calendar event but keeps task)
 */
export async function cancelScheduledBlock(
  taskId: string,
  userId: number = 1
): Promise<{ success: boolean; message: string; deleted_calendar_events: number }> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/calendar/cancel-block/${encodeURIComponent(taskId)}?user_id=${userId}`,
      {
        method: "DELETE",
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to cancel scheduled block");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while cancelling scheduled block");
  }
}

/**
 * Sync calendar events from Google Calendar
 */
export async function syncCalendar(
  userId: number = 1,
  daysAhead: number = 14
): Promise<{ success: boolean; events_count: number; synced_at: string }> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/calendar/sync?user_id=${userId}&days_ahead=${daysAhead}`,
      {
        method: "POST",
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to sync calendar");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while syncing calendar");
  }
}
