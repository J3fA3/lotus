/**
 * Task History Timeline - Phase 6 Stage 3
 *
 * Displays version history for a task in GitHub/GitLab-style timeline format.
 *
 * Features:
 * - Visual timeline with connector lines
 * - PR-style comments as primary content
 * - Milestone indicators (snapshots vs deltas)
 * - AI override highlighting (learning signals)
 * - Expandable metadata sections
 * - Version comparison modal
 * - Pagination with "Load More"
 *
 * Design Decisions:
 * 1. Timeline layout (visual chronology, proven UX pattern)
 * 2. PR comments prominent (what users care about)
 * 3. Modal for comparisons (cleaner, focused)
 * 4. Distinct styling for milestones (visual hierarchy)
 * 5. AI overrides highlighted (high-value learning signals)
 */

import React, { useState, useEffect } from "react";
import {
  TaskVersion,
  TaskVersionHistoryResponse,
  VersionComparison,
  getChangeTypeIcon,
  getChangeTypeColor,
  getChangeSourceLabel
} from "../types/intelligent-task";
import { formatDistanceToNow } from "date-fns";

// ============================================================================
// PROPS
// ============================================================================

interface TaskHistoryTimelineProps {
  taskId: string;
  apiBaseUrl?: string;
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function TaskHistoryTimeline({
  taskId,
  apiBaseUrl = "http://localhost:8001"
}: TaskHistoryTimelineProps) {
  const [history, setHistory] = useState<TaskVersionHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [comparisonOpen, setComparisonOpen] = useState(false);
  const [comparison, setComparison] = useState<VersionComparison | null>(null);
  const [comparingVersions, setComparingVersions] = useState<[number, number] | null>(null);

  // Load initial history
  useEffect(() => {
    loadHistory(0);
  }, [taskId]);

  async function loadHistory(offset: number) {
    try {
      if (offset === 0) {
        setLoading(true);
      } else {
        setLoadingMore(true);
      }

      const response = await fetch(
        `${apiBaseUrl}/tasks/${taskId}/versions?limit=20&offset=${offset}`
      );

      if (!response.ok) {
        throw new Error(`Failed to load version history: ${response.statusText}`);
      }

      const data: TaskVersionHistoryResponse = await response.json();

      if (offset === 0) {
        setHistory(data);
      } else {
        setHistory((prev) =>
          prev
            ? {
                ...data,
                versions: [...prev.versions, ...data.versions]
              }
            : data
        );
      }

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load history");
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }

  async function compareVersions(versionA: number, versionB: number) {
    try {
      setComparingVersions([versionA, versionB]);
      const response = await fetch(
        `${apiBaseUrl}/tasks/${taskId}/versions/compare?version_a=${versionA}&version_b=${versionB}`
      );

      if (!response.ok) {
        throw new Error(`Failed to compare versions: ${response.statusText}`);
      }

      const data: VersionComparison = await response.json();
      setComparison(data);
      setComparisonOpen(true);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to compare versions");
    } finally {
      setComparingVersions(null);
    }
  }

  function handleLoadMore() {
    if (history) {
      loadHistory(history.versions.length);
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500">Loading version history...</div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-700">{error}</p>
      </div>
    );
  }

  // Empty state
  if (!history || history.versions.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
        <p className="text-gray-500">No version history available</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          Version History
          <span className="ml-2 text-sm font-normal text-gray-500">
            {history.total_versions} version{history.total_versions !== 1 ? "s" : ""}
          </span>
        </h3>
      </div>

      {/* Timeline */}
      <div className="space-y-0">
        {history.versions.map((version, index) => (
          <TimelineEntry
            key={version.id}
            version={version}
            isFirst={index === 0}
            isLast={index === history.versions.length - 1}
            onCompare={(otherVersion) => compareVersions(version.version_number, otherVersion)}
            comparingVersions={comparingVersions}
          />
        ))}
      </div>

      {/* Load More */}
      {history.has_more && (
        <div className="flex justify-center pt-4">
          <button
            onClick={handleLoadMore}
            disabled={loadingMore}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {loadingMore ? "Loading..." : "Load More"}
          </button>
        </div>
      )}

      {/* Comparison Modal */}
      {comparisonOpen && comparison && (
        <VersionComparisonModal
          comparison={comparison}
          onClose={() => setComparisonOpen(false)}
        />
      )}
    </div>
  );
}

// ============================================================================
// TIMELINE ENTRY
// ============================================================================

interface TimelineEntryProps {
  version: TaskVersion;
  isFirst: boolean;
  isLast: boolean;
  onCompare: (otherVersion: number) => void;
  comparingVersions: [number, number] | null;
}

function TimelineEntry({
  version,
  isFirst,
  isLast,
  onCompare,
  comparingVersions
}: TimelineEntryProps) {
  const [showMetadata, setShowMetadata] = useState(false);
  const [showChangedFields, setShowChangedFields] = useState(false);

  const icon = getChangeTypeIcon(version.change_type);
  const colorClass = getChangeTypeColor(version.change_type);
  const timeAgo = formatDistanceToNow(new Date(version.created_at), { addSuffix: true });

  return (
    <div className="relative flex gap-4">
      {/* Timeline connector line */}
      {!isLast && (
        <div className="absolute left-[15px] top-[40px] h-full w-[2px] bg-gray-200" />
      )}

      {/* Icon/Indicator */}
      <div className="relative flex-shrink-0 pt-1">
        <div
          className={`flex h-8 w-8 items-center justify-center rounded-full border-2 ${
            version.is_milestone
              ? "border-blue-300 bg-blue-50"
              : "border-gray-300 bg-white"
          }`}
        >
          <span className="text-base">{icon}</span>
        </div>

        {/* Milestone star badge */}
        {version.is_milestone && (
          <div className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-yellow-400 text-xs">
            ⭐
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 pb-8">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-md border px-2 py-1 text-xs font-medium ${colorClass}`}>
              v{version.version_number}
            </span>
            <span className="text-sm text-gray-500">{timeAgo}</span>
            {version.ai_suggestion_overridden && (
              <span className="rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700">
                💡 AI Override
              </span>
            )}
          </div>

          <button
            onClick={() => setShowMetadata(!showMetadata)}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            {showMetadata ? "Hide" : "Show"} details
          </button>
        </div>

        {/* PR Comment (Primary Content) */}
        {version.pr_comment && (
          <div
            className="prose prose-sm mt-2 rounded-md border border-gray-200 bg-white p-3"
            dangerouslySetInnerHTML={{
              __html: renderMarkdown(version.pr_comment)
            }}
          />
        )}

        {/* Metadata (Expandable) */}
        {showMetadata && (
          <div className="mt-3 space-y-2 rounded-md border border-gray-200 bg-gray-50 p-3 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <span className="font-medium text-gray-700">Source:</span>{" "}
                <span className="text-gray-600">
                  {getChangeSourceLabel(version.change_source)}
                </span>
              </div>
              {version.changed_by && (
                <div>
                  <span className="font-medium text-gray-700">Changed by:</span>{" "}
                  <span className="text-gray-600">{version.changed_by}</span>
                </div>
              )}
              {version.ai_model && (
                <div>
                  <span className="font-medium text-gray-700">AI Model:</span>{" "}
                  <span className="text-gray-600">{version.ai_model}</span>
                </div>
              )}
              <div>
                <span className="font-medium text-gray-700">Type:</span>{" "}
                <span className="text-gray-600">
                  {version.is_snapshot ? "Snapshot" : "Delta"}
                  {version.is_milestone && " (Milestone)"}
                </span>
              </div>
            </div>

            {/* Changed Fields */}
            {version.changed_fields.length > 0 && (
              <div>
                <button
                  onClick={() => setShowChangedFields(!showChangedFields)}
                  className="font-medium text-gray-700 hover:text-gray-900"
                >
                  {showChangedFields ? "▼" : "▶"} Changed fields ({version.changed_fields.length})
                </button>
                {showChangedFields && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {version.changed_fields.map((field) => (
                      <span
                        key={field}
                        className="rounded bg-gray-200 px-2 py-0.5 text-xs text-gray-700"
                      >
                        {field}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* AI Override Info */}
            {version.ai_suggestion_overridden && version.overridden_fields.length > 0 && (
              <div className="rounded border border-amber-200 bg-amber-50 p-2">
                <div className="font-medium text-amber-800">User overrode AI suggestions:</div>
                <div className="mt-1 flex flex-wrap gap-1">
                  {version.overridden_fields.map((field) => (
                    <span
                      key={field}
                      className="rounded bg-amber-200 px-2 py-0.5 text-xs text-amber-800"
                    >
                      {field}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Compare button */}
            {version.version_number > 1 && (
              <div className="pt-1">
                <button
                  onClick={() => onCompare(version.version_number - 1)}
                  disabled={comparingVersions !== null}
                  className="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
                >
                  {comparingVersions && comparingVersions.includes(version.version_number)
                    ? "Comparing..."
                    : `Compare with v${version.version_number - 1}`}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// VERSION COMPARISON MODAL
// ============================================================================

interface VersionComparisonModalProps {
  comparison: VersionComparison;
  onClose: () => void;
}

function VersionComparisonModal({ comparison, onClose }: VersionComparisonModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="max-h-[80vh] w-full max-w-4xl overflow-auto rounded-lg bg-white p-6 shadow-xl">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            Version Comparison: v{comparison.version_a} → v{comparison.version_b}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            ✕
          </button>
        </div>

        {/* Timestamps */}
        <div className="mb-4 flex gap-4 text-sm text-gray-600">
          <div>
            <span className="font-medium">v{comparison.version_a}:</span>{" "}
            {new Date(comparison.created_at_a).toLocaleString()}
          </div>
          <div>
            <span className="font-medium">v{comparison.version_b}:</span>{" "}
            {new Date(comparison.created_at_b).toLocaleString()}
          </div>
        </div>

        {/* Changed Fields */}
        {comparison.changed_fields.length === 0 ? (
          <p className="text-gray-500">No differences found</p>
        ) : (
          <div className="space-y-4">
            {comparison.changed_fields.map((field) => {
              const diff = comparison.diff[field];
              return (
                <div key={field} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                  <h4 className="mb-2 font-medium text-gray-900">{field}</h4>
                  <div className="grid grid-cols-2 gap-4">
                    {/* Old value */}
                    <div>
                      <div className="mb-1 text-xs font-medium text-red-700">
                        v{comparison.version_a} (Old)
                      </div>
                      <div className="rounded border border-red-200 bg-red-50 p-2 text-sm">
                        <pre className="whitespace-pre-wrap break-words font-mono text-xs">
                          {formatValue(diff.old)}
                        </pre>
                      </div>
                    </div>
                    {/* New value */}
                    <div>
                      <div className="mb-1 text-xs font-medium text-green-700">
                        v{comparison.version_b} (New)
                      </div>
                      <div className="rounded border border-green-200 bg-green-50 p-2 text-sm">
                        <pre className="whitespace-pre-wrap break-words font-mono text-xs">
                          {formatValue(diff.new)}
                        </pre>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Close button */}
        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function renderMarkdown(markdown: string): string {
  // Simple markdown-to-HTML converter
  // In production, use a library like marked or react-markdown
  return markdown
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, "<code>$1</code>")
    .replace(/\n\n/g, "<br/><br/>")
    .replace(/\n/g, "<br/>");
}

function formatValue(value: any): string {
  if (value === null || value === undefined) {
    return "(not set)";
  }
  if (typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}
