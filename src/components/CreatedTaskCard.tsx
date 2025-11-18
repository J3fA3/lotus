/**
 * Created Task Card Component
 *
 * Displays an auto-created task in the chat interface matching TaskCard design.
 * Clickable to open task details.
 */

import React from "react";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { Calendar, CheckCircle2 } from "lucide-react";
import { format } from "date-fns";
import type { Task } from "../types/task";
import "./rich-text-editor.css";

interface CreatedTaskCardProps {
  task: Task;
  onClick?: (task: Task) => void;
}

export const CreatedTaskCard: React.FC<CreatedTaskCardProps> = ({
  task,
  onClick
}) => {
  return (
    <Card
      className="p-4 cursor-pointer bg-card border border-[hsl(var(--lotus-green-medium)/0.3)] hover:border-[hsl(var(--lotus-green-medium)/0.5)] hover:shadow-zen-md transition-zen group relative overflow-hidden"
      onClick={() => onClick?.(task)}
    >
      {/* Success indicator on left edge */}
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-lotus-green-medium" />

      {/* Main content */}
      <div className="pl-3">
        <div className="flex items-start justify-between gap-3 mb-2">
          <h3
            className="font-medium text-[15px] text-card-foreground leading-snug tracking-tight group-hover:text-lotus-green transition-colors duration-300 flex-1"
            dangerouslySetInnerHTML={{ __html: task.title }}
          />

          {/* Success checkmark */}
          <CheckCircle2
            className="h-4 w-4 flex-shrink-0 text-lotus-green"
          />
        </div>

        <div className="space-y-2.5">
          {/* Value Stream */}
          {task.valueStream && (
            <Badge
              variant="secondary"
              className="text-[11px] px-2.5 py-0.5 font-medium bg-accent text-accent-foreground border-0"
            >
              {task.valueStream}
            </Badge>
          )}

          {/* Metadata row */}
          <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
            {task.assignee && (
              <span className="font-normal">{task.assignee}</span>
            )}
            {task.dueDate && (
              <div className="flex items-center gap-1.5">
                <Calendar className="h-3 w-3 opacity-60" />
                <span className="font-normal">
                  {(() => {
                    try {
                      const date = new Date(task.dueDate);
                      return isNaN(date.getTime())
                        ? task.dueDate
                        : format(date, "MMM d");
                    } catch {
                      return task.dueDate;
                    }
                  })()}
                </span>
              </div>
            )}
            <Badge
              variant="secondary"
              className="text-[10px] px-1.5 py-0 capitalize"
            >
              {task.status}
            </Badge>
          </div>

          {/* Click to view hint */}
          <p className="text-[10px] text-muted-foreground italic opacity-0 group-hover:opacity-70 transition-opacity">
            Click to view details
          </p>
        </div>
      </div>
    </Card>
  );
};
