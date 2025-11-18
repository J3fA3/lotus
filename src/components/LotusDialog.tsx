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
import { Send, Loader2, Upload, X, Paperclip, Sparkles } from "lucide-react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { ScrollArea } from "./ui/scroll-area";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "./ui/dialog";
import { Badge } from "./ui/badge";
import { useChat, useChatMessages, useIsProcessing, usePendingProposals } from "../hooks/useChat";
import ProposedTaskCard from "./ProposedTaskCard";
import ChatMessageComponent from "./ChatMessageComponent";
import { toast } from "sonner";

interface LotusDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTasksCreated?: () => void;
}

const LotusDialog: React.FC<LotusDialogProps> = ({ open, onOpenChange, onTasksCreated }) => {
  const [inputValue, setInputValue] = useState("");
  const [sourceType, setSourceType] = useState<string>("manual");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { sendMessage, approveProposals, rejectProposals, clearChat } = useChat();
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

    // Handle file upload
    if (uploadedFile) {
      // TODO: Upload file and get content
      toast.info(`Processing ${uploadedFile.name}...`);
      setUploadedFile(null);
      // For now, just send filename in message
      await sendMessage(`[Uploaded: ${uploadedFile.name}]\n${content}`, "pdf");
    } else {
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
      setSourceType("pdf");
    }
  };

  const handleClose = () => {
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl h-[85vh] flex flex-col p-0">
        {/* Header */}
        <DialogHeader className="px-6 py-4 border-b bg-gradient-to-r from-emerald-50 to-green-50 dark:from-emerald-950 dark:to-green-950">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500 to-green-600 flex items-center justify-center">
                <Sparkles className="h-5 w-5 text-white" />
              </div>
              <div>
                <DialogTitle className="text-xl font-semibold">Lotus</DialogTitle>
                <p className="text-sm text-muted-foreground">Unified task management</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearChat}
              className="text-muted-foreground"
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
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-emerald-100 to-green-100 dark:from-emerald-900 dark:to-green-900 mx-auto mb-4 flex items-center justify-center">
                  <Sparkles className="h-8 w-8 text-emerald-600 dark:text-emerald-400" />
                </div>
                <h3 className="text-lg font-medium mb-2">What would you like to work on?</h3>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  Paste messages, upload documents, or just tell me what needs to be done.
                </p>
              </div>
            )}

            {messages.map((message) => (
              <ChatMessageComponent key={message.id} message={message} />
            ))}

            {/* Pending Proposals */}
            {pendingProposals && (
              <div className="space-y-3 p-4 bg-emerald-50 dark:bg-emerald-950/50 rounded-lg border border-emerald-200 dark:border-emerald-800">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium">
                    Review {pendingProposals.tasks.length} task{pendingProposals.tasks.length !== 1 ? 's' : ''}
                  </h4>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={handleReject}
                      disabled={isProcessing}
                    >
                      Reject
                    </Button>
                    <Button
                      size="sm"
                      onClick={handleApprove}
                      disabled={isProcessing}
                      className="bg-emerald-600 hover:bg-emerald-700"
                    >
                      {isProcessing ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                          Approving...
                        </>
                      ) : (
                        "Approve"
                      )}
                    </Button>
                  </div>
                </div>
                <div className="space-y-2">
                  {pendingProposals.tasks.map((task) => (
                    <ProposedTaskCard key={task.id} task={task} />
                  ))}
                </div>
              </div>
            )}

            {isProcessing && (
              <div className="flex items-center gap-2 text-muted-foreground text-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Processing...</span>
              </div>
            )}

            <div ref={scrollRef} />
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="border-t px-6 py-4 bg-muted/30">
          {/* File Upload Preview */}
          {uploadedFile && (
            <div className="flex items-center gap-2 mb-3 p-2 bg-emerald-50 dark:bg-emerald-950/50 rounded-md">
              <Paperclip className="h-4 w-4 text-emerald-600" />
              <span className="text-sm flex-1 truncate">{uploadedFile.name}</span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setUploadedFile(null)}
                className="h-6 w-6 p-0"
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
              placeholder="Describe what needs to be done, paste messages, or upload documents..."
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
                className="h-[60px] w-[60px]"
              >
                <Upload className="h-5 w-5" />
              </Button>
              <Button
                onClick={handleSendMessage}
                disabled={(!inputValue.trim() && !uploadedFile) || isProcessing}
                size="icon"
                className="h-[60px] w-[60px] bg-emerald-600 hover:bg-emerald-700"
              >
                {isProcessing ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
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
