/**
 * Lotus - Unified Task Management Dialog
 *
 * One-stop-shop for all task and work management:
 * - Natural language task creation
 * - Document parsing and analysis
 * - Context enrichment
 * - Smart task inference
 */

import React, { useState, useRef, useEffect } from "react";
import { Send, Upload, X, Paperclip, MessageSquare, FileText, Mic } from "lucide-react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { ScrollArea } from "./ui/scroll-area";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "./ui/dialog";
import { Badge } from "./ui/badge";
import { useChat, useChatMessages, useIsProcessing, usePendingProposals } from "../hooks/useChat";
import ProposedTaskCard from "./ProposedTaskCard";
import ChatMessageComponent from "./ChatMessageComponent";
import { toast } from "sonner";
import { LotusIcon } from "./LotusIcon";
import { LotusLoading } from "./LotusLoading";
import type { Task } from "../types/task";

interface LotusDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTasksCreated?: () => void;
  onTaskClick?: (task: Task) => void;
}

const LotusDialog: React.FC<LotusDialogProps> = ({ open, onOpenChange, onTasksCreated, onTaskClick }) => {
  const [inputValue, setInputValue] = useState("");
  const [sourceType, setSourceType] = useState<string>("manual");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { sendMessage, uploadPdfFast, approveProposals, rejectProposals, clearChat, approveTask, rejectTask } = useChat();
  const messages = useChatMessages();
  const isProcessing = useIsProcessing();
  const pendingProposals = usePendingProposals();

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Notify parent when tasks are created
  useEffect(() => {
    const lastMessage = messages[messages.length - 1];
    if (lastMessage?.metadata?.created_tasks?.length > 0 && onTasksCreated) {
      onTasksCreated();
    }
  }, [messages, onTasksCreated]);

  const handleSendMessage = async () => {
    if ((!inputValue.trim() && !uploadedFile) || isProcessing) return;

    const content = inputValue.trim();
    setInputValue("");

    // Handle file upload - use fast endpoint for PDFs
    if (uploadedFile) {
      toast.info(`Processing ${uploadedFile.name}...`);
      const file = uploadedFile;
      setUploadedFile(null);
      // Use fast PDF processing (bypasses orchestrator for speed)
      await uploadPdfFast(file);
    } else {
      // Use the selected source type (manual/slack/transcript)
      await sendMessage(content, sourceType);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleApprove = async () => {
    await approveProposals();
    if (onTasksCreated) {
      onTasksCreated();
    }
  };

  const handleReject = async () => {
    await rejectProposals("User rejected proposals");
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadedFile(file);
      // Note: sourceType will be "pdf" when sending, but we don't override the UI state
    }
  };

  const handleClose = () => {
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl h-[85vh] flex flex-col p-0">
        {/* Header */}
        <DialogHeader className="px-6 py-4 border-b border-[hsl(var(--border)/0.5)] bg-gradient-to-b from-[hsl(var(--lotus-paper))] to-background">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[hsl(var(--lotus-green-light))] to-[hsl(var(--lotus-green-medium))] flex items-center justify-center shadow-zen-sm">
                <LotusIcon className="h-5 w-5 text-[hsl(var(--lotus-paper))]" size={20} />
              </div>
              <div>
                <DialogTitle className="text-xl font-semibold text-lotus-ink">Lotus</DialogTitle>
                <p className="text-sm text-muted-foreground">Transform ideas into action</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearChat}
              className="text-muted-foreground hover:text-lotus-ink transition-zen"
            >
              Clear
            </Button>
          </div>
        </DialogHeader>

        {/* Messages Area */}
        <ScrollArea className="flex-1 px-6 py-4">
          <div className="space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-8">
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[hsl(var(--lotus-green-light))] to-[hsl(var(--lotus-green-medium))] mx-auto mb-4 flex items-center justify-center shadow-zen-md">
                  <LotusIcon className="h-8 w-8 text-[hsl(var(--lotus-paper))]" size={32} />
                </div>
                <h3 className="text-lg font-medium mb-2 text-lotus-ink">What would you like to work on?</h3>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  Share messages, upload documents, or describe what needs to be done.
                </p>
              </div>
            )}

            {messages.map((message) => (
              <ChatMessageComponent
                key={message.id}
                message={message}
                onTaskClick={onTaskClick}
              />
            ))}

            {/* Pending Proposals */}
            {pendingProposals && pendingProposals.tasks.length > 0 && (
              <div className="space-y-3 p-4 bg-lotus-green-light/10 rounded-lg border border-[hsl(var(--lotus-green-medium)/0.3)] shadow-zen-sm transition-zen">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-lotus-ink">
                    {pendingProposals.tasks.length} Proposed Task{pendingProposals.tasks.length !== 1 ? 's' : ''}
                  </h4>
                  <p className="text-xs text-muted-foreground">Review and create</p>
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
              <div className="flex items-center gap-3 text-muted-foreground text-sm">
                <LotusLoading size={24} />
                <span>Lotus is processing...</span>
              </div>
            )}

            <div ref={scrollRef} />
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="border-t border-[hsl(var(--border)/0.5)] px-6 py-4 bg-[hsl(var(--lotus-paper))]">
          {/* Source Type Selector */}
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs text-muted-foreground">Input type:</span>
            <div className="flex gap-1">
              <Button
                size="sm"
                variant={sourceType === "manual" ? "default" : "outline"}
                onClick={() => setSourceType("manual")}
                className={`h-7 text-xs transition-zen ${sourceType === "manual" ? "bg-lotus-green-medium hover:bg-[hsl(var(--lotus-green-dark))]" : ""}`}
              >
                <MessageSquare className="h-3 w-3 mr-1" />
                Manual
              </Button>
              <Button
                size="sm"
                variant={sourceType === "slack" ? "default" : "outline"}
                onClick={() => setSourceType("slack")}
                className={`h-7 text-xs transition-zen ${sourceType === "slack" ? "bg-lotus-green-medium hover:bg-[hsl(var(--lotus-green-dark))]" : ""}`}
              >
                <MessageSquare className="h-3 w-3 mr-1" />
                Slack
              </Button>
              <Button
                size="sm"
                variant={sourceType === "transcript" ? "default" : "outline"}
                onClick={() => setSourceType("transcript")}
                className={`h-7 text-xs transition-zen ${sourceType === "transcript" ? "bg-lotus-green-medium hover:bg-[hsl(var(--lotus-green-dark))]" : ""}`}
              >
                <Mic className="h-3 w-3 mr-1" />
                Transcript
              </Button>
            </div>
          </div>

          {/* File Upload Preview */}
          {uploadedFile && (
            <div className="flex items-center gap-2 mb-3 p-2 bg-lotus-green-light/20 rounded-md border border-[hsl(var(--lotus-green-medium)/0.3)]">
              <Paperclip className="h-4 w-4 text-lotus-green" />
              <span className="text-sm flex-1 truncate text-lotus-ink">{uploadedFile.name}</span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setUploadedFile(null)}
                className="h-6 w-6 p-0 transition-zen"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          )}

          <div className="flex gap-2">
            <Textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                sourceType === "slack"
                  ? "Paste Slack message here..."
                  : sourceType === "transcript"
                  ? "Paste transcript or meeting notes here..."
                  : "Ask a question or describe what needs to be done..."
              }
              className="min-h-[60px] resize-none"
              disabled={isProcessing}
            />
            <div className="flex flex-col gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.doc,.docx,.txt"
                className="hidden"
                onChange={handleFileSelect}
              />
              <Button
                size="icon"
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
                disabled={isProcessing}
                className="h-[60px] w-[60px] transition-zen hover:border-lotus-green-medium"
              >
                <Upload className="h-5 w-5" />
              </Button>
              <Button
                onClick={handleSendMessage}
                disabled={(!inputValue.trim() && !uploadedFile) || isProcessing}
                size="icon"
                className="h-[60px] w-[60px] bg-lotus-green-medium hover:bg-[hsl(var(--lotus-green-dark))] transition-zen shadow-zen-sm hover:shadow-zen-md"
              >
                {isProcessing ? (
                  <LotusLoading size={24} />
                ) : (
                  <Send className="h-5 w-5" />
                )}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default LotusDialog;
