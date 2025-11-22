/**
 * API client for Quality Evaluation & Trust Index
 * Phase 6 Stage 6 - Quality Dashboard
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

// Trust Index data structure
export interface TrustIndexData {
  trust_index: number;
  trust_level: "high" | "medium" | "low" | "very_low";
  scope: string;
  scope_id?: string;
  window_days: number;
  components: {
    quality_consistency: {
      score: number;
      metrics: {
        sample_size: number;
        avg_quality: number;
        quality_variance: number;
        excellent_pct: number;
        good_or_better_pct: number;
      };
    };
    user_engagement: {
      score: number;
      metrics: {
        sample_size: number;
        acceptance_rate: number;
        edit_rate: number;
        question_answer_rate: number;
        auto_fill_acceptance_rate: number;
      };
    };
    outcome_success: {
      score: number;
      metrics: {
        sample_size: number;
        completion_rate: number;
        avg_time_to_complete: number;
        fast_completion_pct: number;
      };
    };
    system_performance: {
      score: number;
      metrics: {
        sample_size: number;
        avg_evaluation_time_ms: number;
        fast_evaluation_pct: number;
      };
    };
  };
  insights: {
    overall: string;
    strengths: string[];
    weaknesses: string[];
    recommendations: string[];
  };
  calculated_at: string;
}

// Quality trend data
export interface QualityTrendPoint {
  date: string;
  quality: number;
  excellent: number;
  good: number;
  fair: number;
  needs_improvement: number;
}

// Task quality score
export interface TaskQualityScore {
  task_id: string;
  overall_score: number;
  quality_tier: "excellent" | "good" | "fair" | "needs_improvement";
  completeness_score: number;
  clarity_score: number;
  actionability_score: number;
  relevance_score: number;
  confidence_score: number;
  quality_metrics: {
    completeness: any;
    clarity: any;
    actionability: any;
    relevance: any;
    confidence: any;
  };
  suggestions: Array<{
    category: string;
    severity: "high" | "medium" | "low";
    message: string;
    impact: string;
  }>;
  strengths: string[];
  evaluated_at: string;
  user_id?: string;
  project_id?: string;
}

/**
 * Get trust index for a scope
 */
export async function getTrustIndex(params: {
  windowDays?: number;
  projectId?: string;
  userId?: string;
}): Promise<TrustIndexData> {
  try {
    const queryParams = new URLSearchParams();

    if (params.windowDays) {
      queryParams.append("window_days", params.windowDays.toString());
    }
    if (params.projectId) {
      queryParams.append("project_id", params.projectId);
    }
    if (params.userId) {
      queryParams.append("user_id", params.userId);
    }

    const response = await fetch(
      `${API_BASE_URL}/quality/trust-index?${queryParams}`
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to fetch trust index");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while fetching trust index");
  }
}

/**
 * Get quality trends over time
 */
export async function getQualityTrends(params: {
  windowDays?: number;
  period?: "daily" | "weekly" | "monthly";
  projectId?: string;
  userId?: string;
}): Promise<QualityTrendPoint[]> {
  try {
    const queryParams = new URLSearchParams();

    if (params.windowDays) {
      queryParams.append("window_days", params.windowDays.toString());
    }
    if (params.period) {
      queryParams.append("period", params.period);
    }
    if (params.projectId) {
      queryParams.append("project_id", params.projectId);
    }
    if (params.userId) {
      queryParams.append("user_id", params.userId);
    }

    const response = await fetch(
      `${API_BASE_URL}/quality/trends?${queryParams}`
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to fetch quality trends");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while fetching quality trends");
  }
}

/**
 * Get quality score for a specific task
 */
export async function getTaskQualityScore(taskId: string): Promise<TaskQualityScore> {
  try {
    const response = await fetch(`${API_BASE_URL}/quality/task/${taskId}`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to fetch task quality score");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while fetching task quality score");
  }
}

/**
 * Evaluate task quality (trigger evaluation for a task)
 */
export async function evaluateTaskQuality(taskId: string): Promise<TaskQualityScore> {
  try {
    const response = await fetch(`${API_BASE_URL}/quality/evaluate/${taskId}`, {
      method: "POST",
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to evaluate task quality");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while evaluating task quality");
  }
}

/**
 * Get recent quality scores
 */
export async function getRecentQualityScores(params: {
  limit?: number;
  projectId?: string;
  userId?: string;
  minQuality?: number;
}): Promise<TaskQualityScore[]> {
  try {
    const queryParams = new URLSearchParams();

    if (params.limit) {
      queryParams.append("limit", params.limit.toString());
    }
    if (params.projectId) {
      queryParams.append("project_id", params.projectId);
    }
    if (params.userId) {
      queryParams.append("user_id", params.userId);
    }
    if (params.minQuality !== undefined) {
      queryParams.append("min_quality", params.minQuality.toString());
    }

    const response = await fetch(
      `${API_BASE_URL}/quality/recent?${queryParams}`
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to fetch recent quality scores");
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while fetching recent quality scores");
  }
}
