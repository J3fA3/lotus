/**
 * Proposed Task Card Component
 *
 * Displays a proposed task from the AI with confidence indicators
 * and action buttons (approve/edit/reject).
 */

import React from "react";
import { Calendar, User, Tag, AlertCircle, CheckCircle } from "lucide-react";
import { Card, CardContent, CardHeader } from "./ui/card";
import { Badge } from "./ui/badge";
import { Progress } from "./ui/progress";
import type { TaskProposal } from "../api/assistant";

interface ProposedTaskCardProps {
  task: TaskProposal;
}

const ProposedTaskCard: React.FC<ProposedTaskCardProps> = ({ task }) => {
  const isHighConfidence = task.confidence >= 80;
  const isMediumConfidence = task.confidence >= 50 && task.confidence < 80;

  const getPriorityColor = (priority: string | null) => {
    switch (priority) {
      case "high":
        return "destructive";
      case "medium":
        return "default";
      case "low":
        return "secondary";
      default:
        return "outline";
    }
  };

  return (
    <Card
      className={`transition-all ${
        isHighConfidence
          ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-950"
          : isMediumConfidence
          ? "border-emerald-300 bg-emerald-50/50 dark:bg-emerald-950/50"
          : "border-orange-400 bg-orange-50 dark:bg-orange-950"
      }`}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <h4 className="font-semibold">{task.title}</h4>
            {task.description && (
              <p className="text-sm text-muted-foreground mt-1">
                {task.description}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {isHighConfidence && (
              <CheckCircle className="h-5 w-5 text-emerald-600" />
            )}
            {!isHighConfidence && (
              <AlertCircle className="h-5 w-5 text-orange-500" />
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Task Details */}
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="flex items-center gap-2">
            <User className="h-4 w-4 text-muted-foreground" />
            <span>{task.assignee}</span>
          </div>
          {task.due_date && (
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span>{new Date(task.due_date).toLocaleDateString()}</span>
            </div>
          )}
          {task.priority && (
            <div className="flex items-center gap-2">
              <Badge variant={getPriorityColor(task.priority)} className="text-xs">
                {task.priority}
              </Badge>
            </div>
          )}
          {task.value_stream && (
            <div className="flex items-center gap-2">
              <Tag className="h-4 w-4 text-muted-foreground" />
              <span>{task.value_stream}</span>
            </div>
          )}
        </div>

        {/* Tags */}
        {task.tags && task.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {task.tags.map((tag, index) => (
              <Badge key={index} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}

        {/* Confidence Indicator */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Confidence</span>
            <span className="font-medium">{task.confidence.toFixed(0)}%</span>
          </div>
          <Progress
            value={task.confidence}
            className={`h-2 ${
              isHighConfidence
                ? "bg-emerald-200 dark:bg-emerald-900"
                : isMediumConfidence
                ? "bg-emerald-100 dark:bg-emerald-900/50"
                : "bg-orange-200 dark:bg-orange-900"
            }`}
          />
          {task.reasoning && (
            <p className="text-xs text-muted-foreground italic mt-1">
              {task.reasoning}
            </p>
          )}
        </div>

        {/* Confidence Factors Breakdown */}
        {task.confidence_factors && (
          <details className="text-xs">
            <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
              View confidence breakdown
            </summary>
            <div className="mt-2 space-y-1 pl-4">
              {Object.entries(task.confidence_factors).map(([factor, value]) => (
                <div key={factor} className="flex justify-between">
                  <span className="capitalize">{factor.replace(/_/g, " ")}:</span>
                  <span>{value.toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </details>
        )}
      </CardContent>
    </Card>
  );
};

export default ProposedTaskCard;
