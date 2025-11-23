/**
 * Question Drawer - Phase 6 Stage 4
 *
 * Slide-out drawer displaying question batches for user clarification.
 *
 * Design Decisions:
 * 1. Slide-out from right - non-blocking, familiar pattern
 * 2. Progressive disclosure - First batch expanded, others collapsed
 * 3. Backdrop blur - maintains context awareness
 * 4. Batch priority - Highest priority batch shown first
 * 5. Completion tracking - Progress bar + counter per batch
 * 6. Smooth animations - Professional, polished feel
 *
 * Architectural Integration:
 * - Fetches batches from /questions/batches/ready
 * - Uses QuestionBatchCard for individual batches
 * - Manages global drawer state (open/close)
 * - Re-fetches after batch completion
 */

import React, { useState, useEffect } from "react";
import { QuestionBatchCard } from "./QuestionBatchCard";

interface Batch {
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
  questions: any[];
}

interface QuestionDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  apiBaseUrl?: string;
}

export function QuestionDrawer({
  isOpen,
  onClose,
  apiBaseUrl = "http://localhost:8001"
}: QuestionDrawerProps) {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedBatchId, setExpandedBatchId] = useState<string | null>(null);

  // Fetch batches when drawer opens
  useEffect(() => {
    if (isOpen) {
      fetchBatches();
    }
  }, [isOpen]);

  async function fetchBatches() {
    try {
      setLoading(true);
      const response = await fetch(`${apiBaseUrl}/questions/batches/ready?limit=20`);

      if (!response.ok) {
        throw new Error(`Failed to fetch batches: ${response.statusText}`);
      }

      const data: Batch[] = await response.json();
      setBatches(data);

      // Auto-expand first batch
      if (data.length > 0 && !expandedBatchId) {
        setExpandedBatchId(data[0].batch.id);
      }
    } catch (error) {
      console.error("Failed to fetch batches:", error);
    } finally {
      setLoading(false);
    }
  }

  async function handleBatchComplete(batchId: string) {
    // Mark batch as completed
    try {
      await fetch(`${apiBaseUrl}/questions/batches/${batchId}/completed`, {
        method: "POST"
      });
    } catch (error) {
      console.error("Failed to mark batch as completed:", error);
    }

    // Re-fetch batches
    await fetchBatches();

    // Close drawer if no more batches
    if (batches.length <= 1) {
      onClose();
    }
  }

  function handleBatchExpand(batchId: string) {
    setExpandedBatchId(expandedBatchId === batchId ? null : batchId);
  }

  // Don't render if closed
  if (!isOpen) {
    return null;
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black bg-opacity-30 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 z-50 flex h-full w-full max-w-2xl flex-col bg-white shadow-2xl transition-transform">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Pending Questions</h2>
            <p className="text-sm text-gray-500">
              {batches.length} batch{batches.length !== 1 ? "es" : ""} ready
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Close drawer"
          >
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-gray-500">Loading questions...</div>
            </div>
          ) : batches.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <svg
                className="mb-4 h-16 w-16 text-gray-300"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <p className="text-lg font-medium text-gray-900">All caught up!</p>
              <p className="text-sm text-gray-500">No pending questions at this time</p>
            </div>
          ) : (
            <div className="space-y-4">
              {batches.map((batch, index) => (
                <QuestionBatchCard
                  key={batch.batch.id}
                  batch={batch}
                  isExpanded={expandedBatchId === batch.batch.id}
                  isFirst={index === 0}
                  onExpand={() => handleBatchExpand(batch.batch.id)}
                  onComplete={() => handleBatchComplete(batch.batch.id)}
                  apiBaseUrl={apiBaseUrl}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 px-6 py-4">
          <button
            onClick={onClose}
            className="w-full rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200"
          >
            Close
          </button>
        </div>
      </div>
    </>
  );
}
