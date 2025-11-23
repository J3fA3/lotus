/**
 * Question Card - Phase 6 Stage 4
 *
 * Individual question card with answer input and feedback.
 *
 * Design Decisions:
 * 1. Hybrid input - Suggestion chips + "Other" text field
 * 2. Inline feedback - Thumbs up/down after answering
 * 3. Visual priority - HIGH questions have accent color
 * 4. Confidence display - AI confidence shown with suggestions
 * 5. Field context - Show which task field this relates to
 * 6. Auto-apply toggle - User control over immediate application
 *
 * Architectural Integration:
 * - Calls /questions/{id}/answer endpoint
 * - Tracks feedback for adaptive learning
 * - Updates parent on answer/dismiss
 * - Integrates with task update flow
 */

import React, { useState } from "react";

interface Question {
  id: number;
  task_id: string;
  field_name: string;
  question: string;
  suggested_answer?: string;
  importance: string;
  confidence: number;
  priority_score: number;
  status: string;
  answer?: string;
  semantic_cluster?: string;
}

interface QuestionCardProps {
  question: Question;
  questionNumber: number;
  totalQuestions: number;
  onAnswered: () => void;
  onDismissed: () => void;
  apiBaseUrl?: string;
}

export function QuestionCard({
  question,
  questionNumber,
  totalQuestions,
  onAnswered,
  onDismissed,
  apiBaseUrl = "http://localhost:8001"
}: QuestionCardProps) {
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [customAnswer, setCustomAnswer] = useState("");
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [feedback, setFeedback] = useState<"helpful" | "not_helpful" | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasAnswered, setHasAnswered] = useState(question.status === "answered");
  const [applyToTask, setApplyToTask] = useState(true);

  // Generate answer suggestions based on field type
  const suggestions = generateSuggestions(question.field_name, question.suggested_answer);

  async function handleSubmitAnswer(answer: string, source: string) {
    if (!answer.trim()) return;

    setIsSubmitting(true);

    try {
      const response = await fetch(`${apiBaseUrl}/questions/${question.id}/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answer: answer.trim(),
          answer_source: source,
          feedback: feedback,
          apply_to_task: applyToTask
        })
      });

      if (!response.ok) {
        throw new Error("Failed to submit answer");
      }

      setHasAnswered(true);
      onAnswered();
    } catch (error) {
      console.error("Failed to submit answer:", error);
      alert("Failed to submit answer. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDismiss() {
    setIsSubmitting(true);

    try {
      const response = await fetch(`${apiBaseUrl}/questions/${question.id}/dismiss`, {
        method: "POST"
      });

      if (!response.ok) {
        throw new Error("Failed to dismiss question");
      }

      onDismissed();
    } catch (error) {
      console.error("Failed to dismiss question:", error);
      alert("Failed to dismiss question. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleSuggestionClick(suggestion: string) {
    setSelectedAnswer(suggestion);
    handleSubmitAnswer(suggestion, "selected_suggestion");
  }

  function handleCustomSubmit() {
    if (customAnswer.trim()) {
      handleSubmitAnswer(customAnswer, "user_input");
    }
  }

  // Importance styling
  const importanceColor =
    question.importance === "HIGH"
      ? "border-orange-300 bg-orange-50"
      : question.importance === "MEDIUM"
      ? "border-yellow-300 bg-yellow-50"
      : "border-gray-200 bg-white";

  const importanceBadgeColor =
    question.importance === "HIGH"
      ? "bg-orange-200 text-orange-700"
      : question.importance === "MEDIUM"
      ? "bg-yellow-200 text-yellow-700"
      : "bg-gray-200 text-gray-700";

  // Already answered state
  if (hasAnswered) {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-4">
        <div className="flex items-start gap-3">
          <svg className="h-5 w-5 flex-shrink-0 text-green-600" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
          <div className="flex-1">
            <p className="text-sm font-medium text-green-900">Question answered</p>
            <p className="text-sm text-green-700">{question.question}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`rounded-lg border-2 p-4 ${importanceColor}`}>
      {/* Header */}
      <div className="mb-3 flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-500">
            {questionNumber} of {totalQuestions}
          </span>
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${importanceBadgeColor}`}>
            {question.importance}
          </span>
          <span className="rounded-full bg-gray-200 px-2 py-0.5 text-xs text-gray-600">
            {formatFieldName(question.field_name)}
          </span>
        </div>
      </div>

      {/* Question */}
      <p className="mb-4 text-base font-medium text-gray-900">{question.question}</p>

      {/* Suggestions */}
      {suggestions.length > 0 && !showCustomInput && (
        <div className="mb-3 space-y-2">
          <p className="text-xs font-medium text-gray-600">Quick answers:</p>
          <div className="flex flex-wrap gap-2">
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                onClick={() => handleSuggestionClick(suggestion)}
                disabled={isSubmitting}
                className="rounded-full border border-blue-300 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50"
              >
                {suggestion}
                {question.suggested_answer === suggestion && question.confidence && (
                  <span className="ml-1 text-xs text-blue-600">
                    ({Math.round(question.confidence * 100)}% confident)
                  </span>
                )}
              </button>
            ))}
            <button
              onClick={() => setShowCustomInput(true)}
              className="rounded-full border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Other...
            </button>
          </div>
        </div>
      )}

      {/* Custom input */}
      {showCustomInput && (
        <div className="mb-3 space-y-2">
          <p className="text-xs font-medium text-gray-600">Your answer:</p>
          <input
            type="text"
            value={customAnswer}
            onChange={(e) => setCustomAnswer(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleCustomSubmit()}
            placeholder="Type your answer..."
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            autoFocus
          />
          <div className="flex gap-2">
            <button
              onClick={handleCustomSubmit}
              disabled={!customAnswer.trim() || isSubmitting}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              Submit
            </button>
            <button
              onClick={() => setShowCustomInput(false)}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Back to suggestions
            </button>
          </div>
        </div>
      )}

      {/* Options */}
      <div className="mb-3 flex items-center gap-4 border-t border-gray-200 pt-3">
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={applyToTask}
            onChange={(e) => setApplyToTask(e.target.checked)}
            className="rounded border-gray-300"
          />
          Apply answer to task immediately
        </label>
      </div>

      {/* Feedback (shown after selecting suggestion or submitting custom) */}
      {selectedAnswer && !hasAnswered && (
        <div className="mb-3 space-y-2 rounded-lg bg-white p-3">
          <p className="text-xs font-medium text-gray-600">Was this question helpful?</p>
          <div className="flex gap-2">
            <button
              onClick={() => setFeedback("helpful")}
              className={`flex items-center gap-1 rounded-lg px-3 py-1 text-sm ${
                feedback === "helpful"
                  ? "bg-green-100 text-green-700"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              👍 Helpful
            </button>
            <button
              onClick={() => setFeedback("not_helpful")}
              className={`flex items-center gap-1 rounded-lg px-3 py-1 text-sm ${
                feedback === "not_helpful"
                  ? "bg-red-100 text-red-700"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              👎 Not helpful
            </button>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between border-t border-gray-200 pt-3">
        <button
          onClick={handleDismiss}
          disabled={isSubmitting}
          className="text-sm text-gray-500 hover:text-gray-700 disabled:opacity-50"
        >
          Skip this question
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function generateSuggestions(fieldName: string, suggestedAnswer?: string): string[] {
  const suggestions: string[] = [];

  // Field-specific suggestions
  if (fieldName === "priority") {
    suggestions.push("High", "Medium", "Low");
  } else if (fieldName === "effort_estimate") {
    suggestions.push("15 min", "1 hour", "3 hours", "1 day", "3 days", "1+ week");
  } else if (fieldName === "assignee") {
    suggestions.push("Me", "Team Lead", "Unassigned");
  } else if (fieldName === "project") {
    suggestions.push("Current Sprint", "Backlog", "Research");
  }

  // Add AI suggestion if available and not already in list
  if (suggestedAnswer && !suggestions.includes(suggestedAnswer)) {
    suggestions.unshift(suggestedAnswer);
  }

  return suggestions;
}

function formatFieldName(fieldName: string): string {
  // Convert snake_case to Title Case
  return fieldName
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
