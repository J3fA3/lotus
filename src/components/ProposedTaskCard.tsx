/**
 * Proposed Task Card Component
 *
 * Displays a proposed task with Lotus aesthetic matching the main TaskCard design.
 * Includes individual approve/reject actions for smoother workflow.
 */

import React from "react";
import { Calendar, Check, X, Sparkles } from "lucide-react";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import type { TaskProposal } from "../api/assistant";
import { format } from "date-fns";
import "./rich-text-editor.css";

interface ProposedTaskCardProps {
  task: TaskProposal;
  onApprove?: (task: TaskProposal) => void;
  onReject?: (task: TaskProposal) => void;
  onClick?: (task: TaskProposal) => void;
  isProcessing?: boolean;
}

const ProposedTaskCard: React.FC<ProposedTaskCardProps> = ({
  task,
  onApprove,
  onReject,
  onClick,
  isProcessing = false
}) => {
  const isHighConfidence = task.confidence >= 80;
  const isMediumConfidence = task.confidence >= 50 && task.confidence < 80;

  const handleCardClick = (e: React.MouseEvent) => {
    // Don't trigger onClick if clicking on action buttons
    if ((e.target as HTMLElement).closest('button')) {
      return;
    }
    onClick?.(task);
  };

  const handleApprove = (e: React.MouseEvent) => {
    e.stopPropagation();
    onApprove?.(task);
  };

  const handleReject = (e: React.MouseEvent) => {
    e.stopPropagation();
    onReject?.(task);
  };

  return (
    <Card
      className="p-4 cursor-pointer bg-card border transition-zen group relative overflow-hidden"
      onClick={handleCardClick}
      style={{
        borderColor: isHighConfidence
          ? 'hsl(var(--lotus-green-medium) / 0.4)'
          : isMediumConfidence
          ? 'hsl(var(--lotus-green-medium) / 0.2)'
          : 'hsl(var(--border) / 0.5)',
        backgroundColor: isHighConfidence
          ? 'hsl(var(--lotus-green-light) / 0.1)'
          : 'hsl(var(--card))'
      }}
    >
      {/* Subtle confidence indicator on left edge */}
      <div
        className="absolute left-0 top-0 bottom-0 w-1 transition-zen"
        style={{
          backgroundColor: isHighConfidence
            ? 'hsl(var(--lotus-green-medium))'
            : isMediumConfidence
            ? 'hsl(var(--lotus-green-medium) / 0.5)'
            : 'hsl(var(--muted-foreground) / 0.3)'
        }}
      />

      {/* Main content */}
      <div className="pl-3">
        <div className="flex items-start justify-between gap-3 mb-3">
          <h3
            className="font-medium text-[15px] text-card-foreground leading-snug tracking-tight group-hover:text-lotus-green transition-colors duration-300 flex-1"
            dangerouslySetInnerHTML={{ __html: task.title }}
          />

          {/* Confidence indicator */}
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <Sparkles
              className="h-3.5 w-3.5 transition-colors"
              style={{
                color: isHighConfidence
                  ? 'hsl(var(--lotus-green-medium))'
                  : isMediumConfidence
                  ? 'hsl(var(--lotus-green-medium) / 0.6)'
                  : 'hsl(var(--muted-foreground) / 0.5)'
              }}
            />
            <span className="text-[11px] font-medium text-muted-foreground">
              {task.confidence.toFixed(0)}%
            </span>
          </div>
        </div>

        {/* Description */}
        {task.description && (
          <p className="text-sm text-muted-foreground mb-3 line-clamp-2 leading-relaxed">
            {task.description}
          </p>
        )}

        <div className="space-y-2.5">
          {/* Value Stream */}
          {task.value_stream && (
            <Badge
              variant="secondary"
              className="text-[11px] px-2.5 py-0.5 font-medium bg-accent text-accent-foreground border-0"
            >
              {task.value_stream}
            </Badge>
          )}

          {/* Metadata row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
              {task.assignee && (
                <span className="font-normal">{task.assignee}</span>
              )}
              {task.due_date && (
                <div className="flex items-center gap-1.5">
                  <Calendar className="h-3 w-3 opacity-60" />
                  <span className="font-normal">
                    {(() => {
                      try {
                        const date = new Date(task.due_date);
                        return isNaN(date.getTime())
                          ? task.due_date
                          : format(date, "MMM d");
                      } catch {
                        return task.due_date;
                      }
                    })()}
                  </span>
                </div>
              )}
              {task.priority && (
                <Badge
                  variant={
                    task.priority === "high"
                      ? "destructive"
                      : task.priority === "medium"
                      ? "default"
                      : "secondary"
                  }
                  className="text-[10px] px-1.5 py-0"
                >
                  {task.priority}
                </Badge>
              )}
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 pt-2 border-t border-border/30">
            <Button
              size="sm"
              variant="ghost"
              onClick={handleReject}
              disabled={isProcessing}
              className="flex-1 h-8 text-xs hover:bg-destructive/10 hover:text-destructive transition-zen"
            >
              <X className="h-3.5 w-3.5 mr-1.5" />
              Decline
            </Button>
            <Button
              size="sm"
              onClick={handleApprove}
              disabled={isProcessing}
              className="flex-1 h-8 text-xs bg-lotus-green-medium hover:bg-[hsl(var(--lotus-green-dark))] transition-zen"
            >
              <Check className="h-3.5 w-3.5 mr-1.5" />
              Create Task
            </Button>
          </div>

          {/* Optional: Show reasoning on hover or as subtle text */}
          {task.reasoning && (
            <p className="text-[10px] text-muted-foreground italic opacity-70 leading-relaxed">
              {task.reasoning}
            </p>
          )}
        </div>
      </div>
    </Card>
  );
};

export default ProposedTaskCard;
