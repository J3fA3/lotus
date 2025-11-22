/**
 * TypeScript types for Question Queue System - Phase 6 Stage 4
 *
 * Mirrors backend Pydantic schemas from backend/api/schemas.py
 */

// ============================================================================
// QUESTION TYPES
// ============================================================================

export interface Question {
  id: number;
  task_id: string;
  field_name: string;
  question: string;
  suggested_answer?: string;
  importance: "HIGH" | "MEDIUM" | "LOW";
  confidence: number; // 0.0-1.0
  priority_score: number;
  status: "queued" | "ready" | "shown" | "answered" | "dismissed" | "snoozed";
  created_at: string;
  ready_at?: string;
  shown_at?: string;
  answered_at?: string;
  answer?: string;
  answer_source?: "user_input" | "selected_suggestion" | "dismissed";
  answer_applied: boolean;
  user_feedback?: "helpful" | "not_helpful";
  semantic_cluster?: string;
}

export interface QuestionListResponse {
  total: number;
  questions: Question[];
}

export interface QuestionAnswerRequest {
  answer: string;
  answer_source?: string;
  feedback?: "helpful" | "not_helpful";
  feedback_comment?: string;
  apply_to_task?: boolean;
}

export interface QuestionSnoozeRequest {
  snooze_hours?: number;
}

// ============================================================================
// BATCH TYPES
// ============================================================================

export interface QuestionBatch {
  id: string;
  batch_type: "task_specific" | "semantic_cluster" | "time_based";
  semantic_cluster?: string;
  question_count: number;
  question_ids: number[];
  task_ids: string[];
  shown_to_user: boolean;
  shown_at?: string;
  completed: boolean;
  completed_at?: string;
  answered_count: number;
  dismissed_count: number;
  snoozed_count: number;
  created_at: string;
}

export interface QuestionBatchWithQuestions {
  batch: QuestionBatch;
  questions: Question[];
}

export interface BatchProcessResponse {
  batches_created: number;
  questions_woken: number;
  processed_at: string;
  error?: string;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

export function getImportanceColor(importance: string): string {
  const colors: Record<string, string> = {
    HIGH: "border-orange-300 bg-orange-50",
    MEDIUM: "border-yellow-300 bg-yellow-50",
    LOW: "border-gray-200 bg-white"
  };
  return colors[importance] || colors.LOW;
}

export function getImportanceBadgeColor(importance: string): string {
  const colors: Record<string, string> = {
    HIGH: "bg-orange-200 text-orange-700",
    MEDIUM: "bg-yellow-200 text-yellow-700",
    LOW: "bg-gray-200 text-gray-700"
  };
  return colors[importance] || colors.LOW;
}

export function formatFieldName(fieldName: string): string {
  // Convert snake_case to Title Case
  return fieldName
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function getBatchTypeLabel(batchType: string): string {
  const labels: Record<string, string> = {
    task_specific: "Same Task",
    semantic_cluster: "Related Fields",
    time_based: "Time-Based"
  };
  return labels[batchType] || "Mixed";
}

export function generateSuggestions(fieldName: string, suggestedAnswer?: string): string[] {
  const suggestions: string[] = [];

  // Field-specific suggestions
  const fieldSuggestions: Record<string, string[]> = {
    priority: ["High", "Medium", "Low"],
    effort_estimate: ["15 min", "1 hour", "3 hours", "1 day", "3 days", "1+ week"],
    assignee: ["Me", "Team Lead", "Unassigned"],
    project: ["Current Sprint", "Backlog", "Research"],
    status: ["Todo", "In Progress", "Done"],
    tags: ["Bug", "Feature", "Enhancement", "Documentation"]
  };

  if (fieldName in fieldSuggestions) {
    suggestions.push(...fieldSuggestions[fieldName]);
  }

  // Add AI suggestion if available and not already in list
  if (suggestedAnswer && !suggestions.includes(suggestedAnswer)) {
    suggestions.unshift(suggestedAnswer);
  }

  return suggestions;
}
