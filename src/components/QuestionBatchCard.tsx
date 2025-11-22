/**
 * Question Batch Card - Phase 6 Stage 4
 *
 * Displays a batch of related questions with progress tracking.
 *
 * Design Decisions:
 * 1. Collapsible card - Progressive disclosure, reduce overwhelm
 * 2. Progress bar + counter - Dual progress indicators for motivation
 * 3. Batch metadata visible - Task ID, question count, batch type
 * 4. Auto-complete when all answered - Seamless UX
 * 5. Question cards nested - Clean hierarchy
 *
 * Architectural Integration:
 * - Uses QuestionCard for individual questions
 * - Tracks completion state internally
 * - Calls onComplete callback when batch finished
 * - Marks batch as shown on expand (engagement tracking)
 */

import React, { useState, useEffect } from "react";
import { QuestionCard } from "./QuestionCard";

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

interface BatchData {
  batch: {
    id: string;
    batch_type: string;
    question_count: number;
    task_ids: string[];
    created_at: string;
    answered_count: number;
    dismissed_count: number;
    snoozed_count: number;
  };
  questions: Question[];
}

interface QuestionBatchCardProps {
  batch: BatchData;
  isExpanded: boolean;
  isFirst: boolean;
  onExpand: () => void;
  onComplete: () => void;
  apiBaseUrl?: string;
}

export function QuestionBatchCard({
  batch,
  isExpanded,
  isFirst,
  onExpand,
  onComplete,
  apiBaseUrl = "http://localhost:8001"
}: QuestionBatchCardProps) {
  const [questions, setQuestions] = useState<Question[]>(batch.questions);
  const [hasMarkedShown, setHasMarkedShown] = useState(false);

  // Mark batch as shown when expanded
  useEffect(() => {
    if (isExpanded && !hasMarkedShown) {
      markBatchShown();
      setHasMarkedShown(true);
    }
  }, [isExpanded]);

  async function markBatchShown() {
    try {
      await fetch(`${apiBaseUrl}/questions/batches/${batch.batch.id}/shown`, {
        method: "POST"
      });
    } catch (error) {
      console.error("Failed to mark batch as shown:", error);
    }
  }

  function handleQuestionAnswered(questionId: number) {
    // Update local state
    setQuestions((prev) =>
      prev.map((q) => (q.id === questionId ? { ...q, status: "answered" } : q))
    );

    // Check if all questions answered/dismissed
    const updatedQuestions = questions.map((q) =>
      q.id === questionId ? { ...q, status: "answered" } : q
    );

    const allHandled = updatedQuestions.every(
      (q) => q.status === "answered" || q.status === "dismissed" || q.status === "snoozed"
    );

    if (allHandled) {
      setTimeout(() => {
        onComplete();
      }, 500); // Small delay for UX smoothness
    }
  }

  function handleQuestionDismissed(questionId: number) {
    setQuestions((prev) =>
      prev.map((q) => (q.id === questionId ? { ...q, status: "dismissed" } : q))
    );

    // Check completion (same logic as answered)
    const updatedQuestions = questions.map((q) =>
      q.id === questionId ? { ...q, status: "dismissed" } : q
    );

    const allHandled = updatedQuestions.every(
      (q) => q.status === "answered" || q.status === "dismissed" || q.status === "snoozed"
    );

    if (allHandled) {
      setTimeout(() => {
        onComplete();
      }, 500);
    }
  }

  // Calculate progress
  const completedCount = questions.filter(
    (q) => q.status === "answered" || q.status === "dismissed"
  ).length;
  const totalCount = questions.length;
  const progressPercent = (completedCount / totalCount) * 100;

  // Batch type label
  const batchTypeLabel =
    batch.batch.batch_type === "task_specific"
      ? "Same Task"
      : batch.batch.batch_type === "semantic_cluster"
      ? "Related Fields"
      : "Mixed";

  return (
    <div
      className={`overflow-hidden rounded-lg border-2 ${
        isFirst ? "border-blue-300 bg-blue-50" : "border-gray-200 bg-white"
      } transition-all`}
    >
      {/* Header (always visible) */}
      <button
        onClick={onExpand}
        className="flex w-full items-center justify-between p-4 text-left hover:bg-gray-50"
      >
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-gray-900">
              {totalCount} Question{totalCount !== 1 ? "s" : ""}
            </h3>
            <span className="rounded-full bg-gray-200 px-2 py-0.5 text-xs text-gray-600">
              {batchTypeLabel}
            </span>
            {isFirst && (
              <span className="rounded-full bg-blue-200 px-2 py-0.5 text-xs text-blue-700">
                Priority
              </span>
            )}
          </div>

          {/* Progress */}
          <div className="mt-2">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>
                {completedCount} of {totalCount} complete
              </span>
              <span>{Math.round(progressPercent)}%</span>
            </div>
            <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-gray-200">
              <div
                className="h-full bg-blue-600 transition-all duration-500"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        </div>

        {/* Expand icon */}
        <svg
          className={`ml-4 h-5 w-5 text-gray-400 transition-transform ${
            isExpanded ? "rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Questions (expandable) */}
      {isExpanded && (
        <div className="border-t border-gray-200 bg-white p-4">
          <div className="space-y-3">
            {questions.map((question, index) => (
              <QuestionCard
                key={question.id}
                question={question}
                questionNumber={index + 1}
                totalQuestions={totalCount}
                onAnswered={() => handleQuestionAnswered(question.id)}
                onDismissed={() => handleQuestionDismissed(question.id)}
                apiBaseUrl={apiBaseUrl}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
