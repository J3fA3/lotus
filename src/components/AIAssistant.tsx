/**
 * Lotus Chat Interface
 *
 * Main component for the Lotus task management chat interface.
 * Provides a conversational UI for creating and managing tasks with Zen aesthetic.
 */

import React, { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { ScrollArea } from "./ui/scroll-area";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { useChat, useChatMessages, useIsProcessing, usePendingProposals } from "../hooks/useChat";
import ProposedTaskCard from "./ProposedTaskCard";
import ChatMessageComponent from "./ChatMessageComponent";
import { TaskDetailSheet } from "./TaskDetailSheet";
import { LotusIcon } from "./LotusIcon";
import { LotusLoading } from "./LotusLoading";
import type { Task } from "../types/task";
import { updateTask, deleteTask } from "../api/tasks";
import { toast } from "sonner";

const AIAssistant: React.FC = () => {
  const [inputValue, setInputValue] = useState("");
  const [sourceType, setSourceType] = useState<string>("manual");
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isTaskDetailOpen, setIsTaskDetailOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const previousMessageCountRef = useRef(0);

  const { sendMessage, approveProposals, rejectProposals, approveTask, rejectTask } = useChat();
  const messages = useChatMessages();
  const isProcessing = useIsProcessing();
  const pendingProposals = usePendingProposals();

  // Auto-scroll to bottom on new messages - optimized to not interfere with typing
  useEffect(() => {
    // Only scroll when messages actually increase (new message added)
    if (messages.length > previousMessageCountRef.current && scrollRef.current) {
      // Use requestAnimationFrame to avoid layout thrashing during typing
      requestAnimationFrame(() => {
        if (scrollRef.current) {
          // Use instant scroll instead of smooth to avoid animation conflicts
          scrollRef.current.scrollIntoView({ behavior: "instant" });
        }
      });
    }
    previousMessageCountRef.current = messages.length;
  }, [messages.length]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isProcessing) return;

    const content = inputValue.trim();
    setInputValue("");

    await sendMessage(content, sourceType);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleApprove = async () => {
    await approveProposals();
  };

  const handleReject = async () => {
    await rejectProposals("User rejected proposals");
  };

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
    setIsTaskDetailOpen(true);
  };

  const handleUpdateTask = async (updatedTask: Task) => {
    try {
      await updateTask(updatedTask.id, updatedTask);
      setSelectedTask(updatedTask);
      toast.success("Task updated");
    } catch (error) {
      console.error("Failed to update task:", error);
      toast.error("Failed to update task");
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    try {
      await deleteTask(taskId);
      setIsTaskDetailOpen(false);
      setSelectedTask(null);
      toast.success("Task deleted");
    } catch (error) {
      console.error("Failed to delete task:", error);
      toast.error("Failed to delete task");
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-[hsl(var(--border)/0.5)] p-4 bg-gradient-to-b from-[hsl(var(--lotus-paper))] to-background">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gradient-to-br from-[hsl(var(--lotus-green-light))] to-[hsl(var(--lotus-green-medium))]">
            <LotusIcon className="h-6 w-6 text-[hsl(var(--lotus-paper))]" size={24} />
          </div>
          <h1 className="text-2xl font-semibold text-lotus-ink tracking-tight">Lotus</h1>
          <Badge variant="secondary" className="ml-auto text-xs">
            Task Management
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground mt-2 ml-[52px]">
          Transform your communications into organized tasks
        </p>
      </div>

      {/* Messages Area */}
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4 max-w-4xl mx-auto">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-[hsl(var(--lotus-green-light))] to-[hsl(var(--lotus-green-medium))] flex items-center justify-center">
                <LotusIcon className="h-10 w-10 text-[hsl(var(--lotus-paper))]" size={40} />
              </div>
              <h2 className="text-xl font-semibold mb-2 text-lotus-ink">Welcome to Lotus</h2>
              <p className="text-muted-foreground max-w-md mx-auto">
                Share your conversations, notes, or ideas. Lotus will thoughtfully organize them into clear, actionable tasks.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8 max-w-2xl mx-auto">
                <Card className="p-4 paper-subtle transition-zen hover:shadow-zen-md">
                  <div className="text-sm font-medium mb-1 text-lotus-ink">Quick Task</div>
                  <div className="text-xs text-muted-foreground">
                    "Andy needs the CRESCO dashboard by Friday"
                  </div>
                </Card>
                <Card className="p-4 paper-subtle transition-zen hover:shadow-zen-md">
                  <div className="text-sm font-medium mb-1 text-lotus-ink">Slack Thread</div>
                  <div className="text-xs text-muted-foreground">
                    Paste entire conversations
                  </div>
                </Card>
                <Card className="p-4 paper-subtle transition-zen hover:shadow-zen-md">
                  <div className="text-sm font-medium mb-1 text-lotus-ink">Questions</div>
                  <div className="text-xs text-muted-foreground">
                    "What's my top priority?"
                  </div>
                </Card>
              </div>
            </div>
          )}

          {messages.map((message) => (
            <ChatMessageComponent
              key={message.id}
              message={message}
              onTaskClick={handleTaskClick}
            />
          ))}

          {/* Pending Proposals */}
          {pendingProposals && pendingProposals.tasks.length > 0 && (
            <div className="space-y-4 p-4 bg-lotus-green-light/10 rounded-lg border border-[hsl(var(--lotus-green-medium)/0.3)] shadow-zen-sm transition-zen">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-lotus-ink">
                  {pendingProposals.tasks.length} Proposed Task{pendingProposals.tasks.length !== 1 ? 's' : ''}
                </h3>
                <p className="text-sm text-muted-foreground">Review and create</p>
              </div>
              <div className="space-y-3">
                {pendingProposals.tasks.map((task) => (
                  <ProposedTaskCard
                    key={task.id}
                    task={task}
                    onApprove={approveTask}
                    onReject={rejectTask}
                    isProcessing={isProcessing}
                  />
                ))}
              </div>
            </div>
          )}

          {isProcessing && (
            <div className="flex items-center gap-3 text-muted-foreground">
              <LotusLoading variant="small" />
              <span className="text-sm">Lotus is processing...</span>
            </div>
          )}

          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="border-t p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-2 mb-2">
            <select
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value)}
              className="px-3 py-1 text-sm border rounded-md bg-background"
            >
              <option value="manual">Manual Input</option>
              <option value="slack">Slack Message</option>
              <option value="transcript">Meeting Transcript</option>
              <option value="question">Question</option>
            </select>
          </div>
          <div className="flex gap-2">
            <Textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Paste Slack messages, meeting notes, or tell me what needs to be done..."
              className="min-h-[80px] resize-none"
              disabled={isProcessing}
            />
            <Button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isProcessing}
              size="icon"
              className="h-[80px] w-[80px] bg-lotus-green-medium hover:bg-[hsl(var(--lotus-green-dark))] transition-zen"
            >
              {isProcessing ? (
                <LotusLoading variant="small" />
              ) : (
                <Send className="h-6 w-6" />
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Press <kbd className="px-1 py-0.5 bg-muted rounded text-xs">Enter</kbd> to send, <kbd className="px-1 py-0.5 bg-muted rounded text-xs">Shift+Enter</kbd> for new line
          </p>
        </div>
      </div>

      {/* Task Detail Sheet */}
      {selectedTask && (
        <TaskDetailSheet
          task={selectedTask}
          open={isTaskDetailOpen}
          onOpenChange={setIsTaskDetailOpen}
          onUpdate={handleUpdateTask}
          onDelete={handleDeleteTask}
        />
      )}
    </div>
  );
};

export default AIAssistant;
