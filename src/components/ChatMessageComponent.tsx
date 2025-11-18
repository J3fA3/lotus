/**
 * Chat Message Component
 *
 * Renders a single chat message (user or assistant) with markdown support
 * and embedded task cards when applicable.
 */

import React from "react";
import ReactMarkdown from "react-markdown";
import { User, CheckCircle, AlertTriangle, Info } from "lucide-react";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import type { ChatMessage } from "../hooks/useChat";
import type { Task } from "../types/task";
import ProposedTaskCard from "./ProposedTaskCard";
import { LotusIcon } from "./LotusIcon";
import { CreatedTaskCard } from "./CreatedTaskCard";

interface ChatMessageComponentProps {
  message: ChatMessage;
  onTaskClick?: (task: Task) => void;
}

const ChatMessageComponent: React.FC<ChatMessageComponentProps> = ({ message, onTaskClick }) => {
  const isUser = message.role === "user";
  const metadata = message.metadata;

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-zen ${
          isUser
            ? "bg-gradient-to-br from-[hsl(var(--lotus-earth))] to-[hsl(var(--secondary))]"
            : "bg-gradient-to-br from-[hsl(var(--lotus-green-light))] to-[hsl(var(--lotus-green-medium))]"
        }`}
      >
        {isUser ? (
          <User className="h-5 w-5 text-[hsl(var(--lotus-ink))]" />
        ) : (
          <LotusIcon className="text-[hsl(var(--lotus-paper))]" size={20} />
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 max-w-[80%] ${isUser ? "items-end" : "items-start"}`}>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-lotus-ink">
            {isUser ? "You" : "Lotus"}
          </span>
          <span className="text-xs text-muted-foreground">
            {message.timestamp.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
          {metadata?.confidence !== undefined && (
            <Badge
              variant={
                metadata.confidence >= 80
                  ? "default"
                  : metadata.confidence >= 50
                  ? "secondary"
                  : "destructive"
              }
              className="text-xs"
            >
              {metadata.confidence.toFixed(0)}% confidence
            </Badge>
          )}
        </div>

        <Card
          className={`${
            isUser
              ? "paper-subtle shadow-zen-sm"
              : "bg-muted/50 border-[hsl(var(--border)/0.3)] shadow-zen-sm"
          } p-4 transition-zen hover:shadow-zen-md`}
        >
          {/* Main Message */}
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>

          {/* Recommended Action Badge */}
          {metadata?.recommended_action && (
            <div className="mt-2 flex items-center gap-2">
              {metadata.recommended_action === "auto" && (
                <Badge variant="default" className="flex items-center gap-1">
                  <CheckCircle className="h-3 w-3" />
                  Auto-approved
                </Badge>
              )}
              {metadata.recommended_action === "ask" && (
                <Badge variant="secondary" className="flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  Needs approval
                </Badge>
              )}
              {metadata.recommended_action === "clarify" && (
                <Badge variant="destructive" className="flex items-center gap-1">
                  <Info className="h-3 w-3" />
                  Needs clarification
                </Badge>
              )}
            </div>
          )}

          {/* Auto-Created Tasks */}
          {metadata?.created_tasks && metadata.created_tasks.length > 0 && (
            <div className="mt-3 space-y-3">
              <p className="text-sm font-medium text-lotus-green flex items-center gap-2">
                <CheckCircle className="h-4 w-4" />
                Created {metadata.created_tasks.length} task{metadata.created_tasks.length !== 1 ? 's' : ''}
              </p>
              {metadata.created_tasks.map((task: Task) => (
                <CreatedTaskCard
                  key={task.id}
                  task={task}
                  onClick={onTaskClick}
                />
              ))}
            </div>
          )}

          {/* Clarifying Questions */}
          {metadata?.clarifying_questions && metadata.clarifying_questions.length > 0 && (
            <div className="mt-3 space-y-2">
              <p className="text-sm font-medium">I need some clarification:</p>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                {metadata.clarifying_questions.map((question: string, index: number) => (
                  <li key={index}>{question}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Question Answer */}
          {metadata?.answer_text && metadata.recommended_action === "answer_question" && (
            <div className="mt-3 p-3 bg-lotus-green-light/20 rounded-lg border border-[hsl(var(--lotus-green-medium)/0.3)] transition-zen">
              <div className="flex items-start gap-2">
                <Info className="h-5 w-5 text-lotus-green flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-lotus-ink mb-1">
                    Answer:
                  </p>
                  <p className="text-sm text-foreground/90">
                    {metadata.answer_text}
                  </p>
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};

export default ChatMessageComponent;
