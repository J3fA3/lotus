/**
 * Question Queue Badge - Phase 6 Stage 4
 *
 * Floating badge that shows pending question count and opens drawer.
 *
 * Design Decisions:
 * 1. Floating position (top-right) - visible but non-intrusive
 * 2. Badge count with animation - draws attention to new questions
 * 3. Click to open drawer - user-controlled engagement
 * 4. Pulse animation when new questions arrive - subtle notification
 * 5. Auto-hide when zero questions - clean UI when not needed
 *
 * Architectural Integration:
 * - Polls API every 30 seconds for new batches
 * - Opens QuestionDrawer on click (passed as prop)
 * - Can be placed in app header or as floating widget
 */

import React, { useState, useEffect } from "react";

interface QuestionQueueBadgeProps {
  apiBaseUrl?: string;
  onOpenDrawer: () => void;
  className?: string;
}

export function QuestionQueueBadge({
  apiBaseUrl = "http://localhost:8001",
  onOpenDrawer,
  className = ""
}: QuestionQueueBadgeProps) {
  const [questionCount, setQuestionCount] = useState(0);
  const [isNewBatch, setIsNewBatch] = useState(false);
  const [loading, setLoading] = useState(false);

  // Poll for new batches
  useEffect(() => {
    fetchBatchCount();
    const interval = setInterval(fetchBatchCount, 30000); // Every 30 seconds
    return () => clearInterval(interval);
  }, []);

  async function fetchBatchCount() {
    try {
      setLoading(true);
      const response = await fetch(`${apiBaseUrl}/questions/batches/ready?limit=50`);
      if (!response.ok) return;

      const batches = await response.json();
      const totalQuestions = batches.reduce(
        (sum: number, batch: any) => sum + batch.batch.question_count,
        0
      );

      // Detect new questions
      if (totalQuestions > questionCount) {
        setIsNewBatch(true);
        setTimeout(() => setIsNewBatch(false), 3000); // Pulse for 3 seconds
      }

      setQuestionCount(totalQuestions);
    } catch (error) {
      console.error("Failed to fetch question count:", error);
    } finally {
      setLoading(false);
    }
  }

  // Don't show badge if no questions
  if (questionCount === 0) {
    return null;
  }

  return (
    <button
      onClick={onOpenDrawer}
      className={`group relative ${className}`}
      aria-label={`${questionCount} pending questions`}
    >
      {/* Badge container */}
      <div
        className={`flex items-center gap-2 rounded-full bg-blue-600 px-4 py-2 text-white shadow-lg transition-all hover:bg-blue-700 hover:shadow-xl ${
          isNewBatch ? "animate-pulse" : ""
        }`}
      >
        {/* Question icon */}
        <svg
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>

        {/* Count */}
        <span className="font-semibold">{questionCount}</span>

        {/* Tooltip on hover */}
        <div className="pointer-events-none absolute -bottom-10 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded bg-gray-900 px-2 py-1 text-xs text-white group-hover:block">
          {questionCount} question{questionCount !== 1 ? "s" : ""} pending
        </div>
      </div>

      {/* New badge indicator */}
      {isNewBatch && (
        <div className="absolute -right-1 -top-1 flex h-3 w-3 items-center justify-center">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75"></span>
          <span className="relative inline-flex h-3 w-3 rounded-full bg-red-500"></span>
        </div>
      )}
    </button>
  );
}
