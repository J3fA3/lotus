/**
 * AI Assistant Chat Interface
 *
 * Main component for the Phase 2 AI Assistant chat interface.
 * Provides a conversational UI for creating and managing tasks.
 */

import React, { useState, useRef, useEffect } from "react";
import { Send, Loader2, Sparkles } from "lucide-react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { ScrollArea } from "./ui/scroll-area";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { useChat, useChatMessages, useIsProcessing, usePendingProposals } from "../hooks/useChat";
import ProposedTaskCard from "./ProposedTaskCard";
import ChatMessageComponent from "./ChatMessageComponent";

const AIAssistant: React.FC = () => {
  const [inputValue, setInputValue] = useState("");
  const [sourceType, setSourceType] = useState<string>("manual");
  const scrollRef = useRef<HTMLDivElement>(null);

  const { sendMessage, approveProposals, rejectProposals } = useChat();
  const messages = useChatMessages();
  const isProcessing = useIsProcessing();
  const pendingProposals = usePendingProposals();

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

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

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b p-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-purple-500" />
          <h1 className="text-2xl font-bold">AI Assistant</h1>
          <Badge variant="secondary" className="ml-auto">
            Phase 2
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          I'll help you create and manage tasks from your communications
        </p>
      </div>

      {/* Messages Area */}
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4 max-w-4xl mx-auto">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <Sparkles className="h-16 w-16 text-purple-300 mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2">Welcome to AI Assistant!</h2>
              <p className="text-muted-foreground max-w-md mx-auto">
                Paste Slack messages, meeting notes, or just tell me what needs to be done.
                I'll automatically create tasks with smart suggestions.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8 max-w-2xl mx-auto">
                <Card className="p-4">
                  <div className="text-sm font-medium mb-1">📝 Quick Task</div>
                  <div className="text-xs text-muted-foreground">
                    "Andy needs the CRESCO dashboard by Friday"
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-sm font-medium mb-1">💬 Slack Thread</div>
                  <div className="text-xs text-muted-foreground">
                    Paste entire Slack conversations
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-sm font-medium mb-1">❓ Questions</div>
                  <div className="text-xs text-muted-foreground">
                    "What's my top priority this week?"
                  </div>
                </Card>
              </div>
            </div>
          )}

          {messages.map((message) => (
            <ChatMessageComponent key={message.id} message={message} />
          ))}

          {/* Pending Proposals */}
          {pendingProposals && (
            <div className="space-y-4 p-4 bg-yellow-50 dark:bg-yellow-950 rounded-lg border-2 border-yellow-200 dark:border-yellow-800">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">
                  Review Proposed Tasks ({pendingProposals.tasks.length})
                </h3>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleReject}
                    disabled={isProcessing}
                  >
                    Reject All
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleApprove}
                    disabled={isProcessing}
                  >
                    {isProcessing ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        Approving...
                      </>
                    ) : (
                      "Approve All"
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
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>AI is thinking...</span>
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
              className="h-[80px] w-[80px]"
            >
              {isProcessing ? (
                <Loader2 className="h-6 w-6 animate-spin" />
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
    </div>
  );
};

export default AIAssistant;
