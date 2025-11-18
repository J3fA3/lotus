/**
 * Chat State Management Hook
 *
 * This hook manages the AI Assistant chat state using Zustand.
 * It handles:
 * - Chat messages (user + assistant)
 * - Pending task proposals
 * - Chat sessions
 * - Loading states
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  processMessage,
  processMessageWithFile,
  processPdfFast,
  approveTasks,
  rejectTasks,
  getChatHistory,
  ProcessMessageResponse,
  TaskProposal,
  EnrichmentOperation,
  ChatMessage as APIChatMessage,
} from "../api/assistant";

// ============================================================================
// TYPES
// ============================================================================

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  metadata?: {
    answer_text?: string | null;  // For question responses
    proposed_tasks?: TaskProposal[];
    enrichment_operations?: EnrichmentOperation[];
    created_tasks?: any[];
    clarifying_questions?: string[];
    confidence?: number;
    recommended_action?: string;
    context_item_id?: number | null;
  };
}

interface ChatState {
  // State
  sessionId: string | null;
  messages: ChatMessage[];
  isProcessing: boolean;
  pendingProposals: {
    tasks: TaskProposal[];
    enrichments: EnrichmentOperation[];
    contextItemId: number | null;
  } | null;

  // Actions
  sendMessage: (content: string, sourceType?: string, file?: File) => Promise<void>;
  uploadPdfFast: (file: File) => Promise<void>;
  approveProposals: () => Promise<void>;
  rejectProposals: (reason?: string) => Promise<void>;
  loadHistory: (sessionId: string) => Promise<void>;
  clearChat: () => void;
  setSessionId: (sessionId: string) => void;
}

// ============================================================================
// STORE
// ============================================================================

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      // Initial state
      sessionId: null,
      messages: [],
      isProcessing: false,
      pendingProposals: null,

      // Send a message to the AI Assistant
      sendMessage: async (content: string, sourceType: string = "manual", file?: File) => {
        const currentSessionId = get().sessionId || generateSessionId();

        // Add user message immediately
        const userMessage: ChatMessage = {
          id: `user-${Date.now()}`,
          role: "user",
          content: file ? `[Uploaded: ${file.name}]\n${content}` : content,
          timestamp: new Date(),
        };

        set({
          messages: [...get().messages, userMessage],
          isProcessing: true,
          sessionId: currentSessionId,
        });

        try {
          // Process message through orchestrator
          let response: ProcessMessageResponse;

          if (file) {
            // Use file upload endpoint
            response = await processMessageWithFile({
              content,
              source_type: sourceType,
              session_id: currentSessionId,
              file,
            });
          } else {
            // Use regular endpoint
            response = await processMessage({
              content,
              source_type: sourceType,
              session_id: currentSessionId,
            });
          }

          // Update session ID
          set({ sessionId: response.session_id });

          // Create assistant message
          const assistantMessage: ChatMessage = {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: response.message,
            timestamp: new Date(),
            metadata: {
              answer_text: response.answer_text,
              proposed_tasks: response.proposed_tasks,
              enrichment_operations: response.enrichment_operations,
              created_tasks: response.created_tasks,
              clarifying_questions: response.clarifying_questions,
              confidence: response.overall_confidence,
              recommended_action: response.recommended_action,
              context_item_id: response.context_item_id,
            },
          };

          // Update state
          set({
            messages: [...get().messages, assistantMessage],
            isProcessing: false,
            pendingProposals:
              response.needs_approval &&
              (response.proposed_tasks.length > 0 ||
                response.enrichment_operations.length > 0)
                ? {
                    tasks: response.proposed_tasks,
                    enrichments: response.enrichment_operations,
                    contextItemId: response.context_item_id,
                  }
                : null,
          });
        } catch (error) {
          console.error("Error sending message:", error);

          // Add error message
          const errorMessage: ChatMessage = {
            id: `error-${Date.now()}`,
            role: "assistant",
            content:
              "Sorry, I encountered an error processing your message. Please try again.",
            timestamp: new Date(),
          };

          set({
            messages: [...get().messages, errorMessage],
            isProcessing: false,
          });
        }
      },

      // Fast PDF upload (bypasses orchestrator for speed)
      uploadPdfFast: async (file: File) => {
        const currentSessionId = get().sessionId || generateSessionId();

        // Add user message immediately
        const userMessage: ChatMessage = {
          id: `user-${Date.now()}`,
          role: "user",
          content: `[Uploaded: ${file.name}]`,
          timestamp: new Date(),
        };

        set({
          messages: [...get().messages, userMessage],
          isProcessing: true,
          sessionId: currentSessionId,
        });

        try {
          // Use fast PDF processing endpoint
          const response = await processPdfFast(file, currentSessionId);

          // Update session ID
          set({ sessionId: response.session_id });

          // Create assistant message
          const assistantMessage: ChatMessage = {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: response.message,
            timestamp: new Date(),
            metadata: {
              created_tasks: response.created_tasks,
              recommended_action: "auto",
              context_item_id: response.context_item_id,
            },
          };

          // Update state
          set({
            messages: [...get().messages, assistantMessage],
            isProcessing: false,
          });
        } catch (error) {
          console.error("Error uploading PDF:", error);

          // Add error message
          const errorMessage: ChatMessage = {
            id: `error-${Date.now()}`,
            role: "assistant",
            content:
              "Sorry, I encountered an error processing your PDF. Please try again.",
            timestamp: new Date(),
          };

          set({
            messages: [...get().messages, errorMessage],
            isProcessing: false,
          });
        }
      },

      // Approve pending task proposals
      approveProposals: async () => {
        const { pendingProposals, sessionId } = get();

        if (!pendingProposals || !sessionId) {
          return;
        }

        set({ isProcessing: true });

        try {
          const result = await approveTasks({
            session_id: sessionId,
            task_proposals: pendingProposals.tasks,
            enrichment_operations: pendingProposals.enrichments,
            context_item_id: pendingProposals.contextItemId,
          });

          // Add confirmation message
          const confirmationMessage: ChatMessage = {
            id: `confirmation-${Date.now()}`,
            role: "assistant",
            content: result.message,
            timestamp: new Date(),
            metadata: {
              created_tasks: result.created_tasks,
            },
          };

          set({
            messages: [...get().messages, confirmationMessage],
            isProcessing: false,
            pendingProposals: null,
          });
        } catch (error) {
          console.error("Error approving proposals:", error);
          set({ isProcessing: false });
        }
      },

      // Reject pending task proposals
      rejectProposals: async (reason?: string) => {
        const { pendingProposals, sessionId } = get();

        if (!pendingProposals || !sessionId) {
          return;
        }

        set({ isProcessing: true });

        try {
          const taskIds = pendingProposals.tasks.map((t) => t.id);

          await rejectTasks(
            sessionId,
            taskIds,
            reason,
            pendingProposals.contextItemId
          );

          // Add confirmation message
          const confirmationMessage: ChatMessage = {
            id: `rejection-${Date.now()}`,
            role: "assistant",
            content: `Understood. I won't create those ${taskIds.length} task(s).`,
            timestamp: new Date(),
          };

          set({
            messages: [...get().messages, confirmationMessage],
            isProcessing: false,
            pendingProposals: null,
          });
        } catch (error) {
          console.error("Error rejecting proposals:", error);
          set({ isProcessing: false });
        }
      },

      // Load chat history from server
      loadHistory: async (sessionId: string) => {
        try {
          const history = await getChatHistory(sessionId);

          // Convert API messages to ChatMessage format
          const messages: ChatMessage[] = history.map((msg: APIChatMessage) => ({
            id: `${msg.role}-${msg.id}`,
            role: msg.role,
            content: msg.content,
            timestamp: new Date(msg.created_at),
            metadata: msg.metadata || undefined,
          }));

          set({
            sessionId,
            messages,
          });
        } catch (error) {
          console.error("Error loading chat history:", error);
        }
      },

      // Clear chat and start new session
      clearChat: () => {
        set({
          sessionId: null,
          messages: [],
          pendingProposals: null,
        });
      },

      // Set session ID (for resuming sessions)
      setSessionId: (sessionId: string) => {
        set({ sessionId });
      },
    }),
    {
      name: "chat-storage",
      partialize: (state) => ({
        sessionId: state.sessionId,
        // Don't persist messages (load from server on demand)
      }),
    }
  )
);

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function generateSessionId(): string {
  return `session-${Date.now()}-${Math.random().toString(36).substring(7)}`;
}

// Convenience hooks
export function useChat() {
  return useChatStore();
}

export function useChatMessages() {
  return useChatStore((state) => state.messages);
}

export function useIsProcessing() {
  return useChatStore((state) => state.isProcessing);
}

export function usePendingProposals() {
  return useChatStore((state) => state.pendingProposals);
}
