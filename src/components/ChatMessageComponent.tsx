/**
 * Chat Message Component
 *
 * Renders a single chat message (user or assistant) with markdown support
 * and embedded task cards when applicable.
 */

import React from "react";
import ReactMarkdown from "react-markdown";
import { User, Bot, CheckCircle, AlertTriangle, Info } from "lucide-react";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import type { ChatMessage } from "../hooks/useChat";
import ProposedTaskCard from "./ProposedTaskCard";

interface ChatMessageComponentProps {
  message: ChatMessage;
}

const ChatMessageComponent: React.FC<ChatMessageComponentProps> = ({ message }) => {
  const isUser = message.role === "user";
  const metadata = message.metadata;

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
          isUser ? "bg-blue-500" : "bg-purple-500"
        }`}
      >
        {isUser ? (
          <User className="h-5 w-5 text-white" />
        ) : (
          <Bot className="h-5 w-5 text-white" />
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 max-w-[80%] ${isUser ? "items-end" : "items-start"}`}>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium">
            {isUser ? "You" : "AI Assistant"}
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
              ? "bg-blue-100 dark:bg-blue-950 border-blue-200 dark:border-blue-800"
              : "bg-muted"
          } p-3`}
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
            <div className="mt-3 space-y-2">
              <p className="text-sm font-medium text-green-700 dark:text-green-400">
                ✓ Created {metadata.created_tasks.length} task(s)
              </p>
              {metadata.created_tasks.map((task: any) => (
                <div
                  key={task.id}
                  className="text-sm p-2 bg-green-50 dark:bg-green-950 rounded border border-green-200 dark:border-green-800"
                >
                  <div className="font-medium">{task.title}</div>
                  {task.assignee && (
                    <div className="text-muted-foreground text-xs">
                      Assigned to: {task.assignee}
                    </div>
                  )}
                </div>
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
            <div className="mt-3 p-3 bg-emerald-50 dark:bg-emerald-950/50 rounded-lg border border-emerald-200 dark:border-emerald-800">
              <div className="flex items-start gap-2">
                <Info className="h-5 w-5 text-emerald-600 dark:text-emerald-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-emerald-900 dark:text-emerald-100 mb-1">
                    Answer:
                  </p>
                  <p className="text-sm text-emerald-800 dark:text-emerald-200">
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
