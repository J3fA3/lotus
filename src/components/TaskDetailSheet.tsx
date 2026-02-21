import { useState, useEffect, useRef, useCallback } from "react";
import { Task, Comment } from "@/types/task";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "./ui/sheet";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { Button } from "./ui/button";
import { RichTextEditor } from "./RichTextEditor";
import { UnifiedAttachments } from "./UnifiedAttachments";
import { Label } from "./ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Skeleton } from "./ui/skeleton";
import { Calendar, Paperclip, MessageSquare, Trash2, User, Maximize2, Minimize2, Expand, ScrollText } from "lucide-react";
import { toast } from "sonner";
import { ValueStreamCombobox } from "./ValueStreamCombobox";
import { useRegisterShortcut } from "@/contexts/ShortcutContext";
import { DeleteTaskDialog } from "./DeleteTaskDialog";
import { CommentItem } from "./CommentItem";
import { AskLotus } from "./AskLotus";

// Helper function to get today's date in YYYY-MM-DD format
const getTodayDateString = (): string => {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

// Helper function to auto-set start date when moving from todo to doing
const shouldAutoSetStartDate = (oldStatus: Task["status"], newStatus: Task["status"], currentStartDate?: string): boolean => {
  return oldStatus === "todo" && newStatus === "doing" && !currentStartDate;
};

interface TaskDetailSheetProps {
  task: Task;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUpdate: (task: Task) => void;
  onDelete: (taskId: string) => void;
  isExpanded?: boolean;
  onToggleExpanded?: () => void;
  onFullPage?: () => void;
  onFullyClose?: () => void;
}

export const TaskDetailSheet = ({
  task,
  open,
  onOpenChange,
  onUpdate,
  onDelete,
  isExpanded: isExpandedProp = false,
  onToggleExpanded,
  onFullPage,
  onFullyClose,
}: TaskDetailSheetProps) => {
  const [editedTask, setEditedTask] = useState<Task>({
    ...task,
    comments: task.comments || [],
    attachments: task.attachments || [],
  });
  const [newComment, setNewComment] = useState("");
  const [isExpanded, setIsExpanded] = useState(isExpandedProp);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isExiting, setIsExiting] = useState(false);
  const notesRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLDivElement>(null);
  const descriptionRef = useRef<HTMLDivElement>(null);
  const statusRef = useRef<HTMLButtonElement>(null);
  const commentsRef = useRef<HTMLDivElement>(null);
  const startDateRef = useRef<HTMLInputElement>(null);
  const dueDateRef = useRef<HTMLInputElement>(null);
  const valueStreamRef = useRef<HTMLDivElement>(null);
  const previousTaskIdRef = useRef<string>(task.id);
  const [currentSectionIndex, setCurrentSectionIndex] = useState(0);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [resetKey, setResetKey] = useState(0);

  // Track last update timestamp to prevent feedback loops
  const lastExternalUpdateRef = useRef<string>("");

  // Track in-flight local updates to prevent race conditions
  const localUpdateInProgressRef = useRef(false);
  const localUpdateTimestampRef = useRef<string>("");
  const localUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Update editedTask when the task prop changes with skeleton transition
  useEffect(() => {
    // Check if task actually changed (different ID)
    if (task.id !== previousTaskIdRef.current) {
      // Show skeleton briefly for smooth transition
      setIsTransitioning(true);

      // Quick skeleton flash (150ms) then update content
      const timer = setTimeout(() => {
        setEditedTask({
          ...task,
          comments: task.comments || [],
          attachments: task.attachments || [],
        });
        previousTaskIdRef.current = task.id;
        lastExternalUpdateRef.current = task.updatedAt || "";
        localUpdateInProgressRef.current = false;
        localUpdateTimestampRef.current = "";
        setResetKey(prev => prev + 1);
        setIsTransitioning(false);
      }, 150);

      return () => clearTimeout(timer);
    } else if (task.updatedAt && task.updatedAt !== lastExternalUpdateRef.current) {
      // Same task, but externally updated (e.g., from another component)
      // CRITICAL: Don't overwrite if we have a local update in progress
      // This prevents race conditions where the API call hasn't completed yet
      if (localUpdateInProgressRef.current && localUpdateTimestampRef.current) {
        // Check if this update is the response to our local update
        // If the task.updatedAt is newer than our local timestamp, it's likely the API response
        const taskTime = new Date(task.updatedAt).getTime();
        const localTime = new Date(localUpdateTimestampRef.current).getTime();

        if (taskTime >= localTime) {
          // This is the API response to our update - accept it and clear the flag
          localUpdateInProgressRef.current = false;
          localUpdateTimestampRef.current = "";
          // Clear the timeout since the update completed successfully
          if (localUpdateTimeoutRef.current) {
            clearTimeout(localUpdateTimeoutRef.current);
            localUpdateTimeoutRef.current = null;
          }
          lastExternalUpdateRef.current = task.updatedAt;
          setEditedTask({
            ...task,
            comments: task.comments || [],
            attachments: task.attachments || [],
          });
        }
        // Otherwise, ignore this update as we're still waiting for our update to complete
      } else {
        // No local update in progress, safe to update from external source
        lastExternalUpdateRef.current = task.updatedAt;
        setEditedTask({
          ...task,
          comments: task.comments || [],
          attachments: task.attachments || [],
        });
      }
    }
    // If same task with same timestamp, don't update (prevents feedback loop)
  }, [task.id, task.updatedAt]);

  // Sync local isExpanded with parent prop
  useEffect(() => {
    setIsExpanded(isExpandedProp);
  }, [isExpandedProp]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (localUpdateTimeoutRef.current) {
        clearTimeout(localUpdateTimeoutRef.current);
      }
    };
  }, []);

  // Section tabbing - list of focusable sections in order
  const sections = [
    titleRef,        // Input
    statusRef,       // SelectTrigger
    valueStreamRef,  // ValueStreamCombobox button
    startDateRef,    // Input date
    dueDateRef,      // Input date
    descriptionRef,  // Textarea
    notesRef,       // Textarea
  ];

  const focusSection = useCallback((index: number) => {
    const sectionRef = sections[index];
    if (!sectionRef || !sectionRef.current) return;

    // Scroll into view
    sectionRef.current.scrollIntoView({ behavior: "smooth", block: "center" });

    // Focus based on element type
    setTimeout(() => {
      const element = sectionRef.current;
      if (!element) return;

      // For RichTextEditor (contenteditable) or Textarea elements
      const contentEditable = element.querySelector('[contenteditable="true"]') as HTMLElement;
      if (contentEditable) {
        contentEditable.focus();
        return;
      }
      const textarea = element.querySelector('textarea') as HTMLTextAreaElement;
      if (textarea) {
        textarea.focus();
        return;
      }

      // For Input elements (date inputs)
      if (element instanceof HTMLInputElement) {
        element.focus();
        return;
      }

      // For Button elements (SelectTrigger)
      if (element instanceof HTMLButtonElement) {
        element.focus();
        return;
      }

      // For ValueStreamCombobox: find the button trigger
      if (index === 2) { // valueStreamRef is at index 2
        const button = element.querySelector('button[role="combobox"]') as HTMLButtonElement;
        if (button) {
          button.focus();
          return;
        }
      }

      // Try to focus the element itself
      if (element.tabIndex >= 0) {
        element.focus();
      }
    }, 300); // Wait for scroll animation
  }, [sections]);

  // Configurable keyboard shortcuts
  useRegisterShortcut('close_dialog', () => {
    if (open) {
      if (onFullyClose) {
        // Fully close with smooth animation
        setIsExiting(true);
        setTimeout(() => {
          onFullyClose();
        }, 300);
      } else {
        onOpenChange(false);
      }
    }
  });

  useRegisterShortcut('focus_notes', () => {
    if (open) {
      notesRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      setTimeout(() => {
        const editable = notesRef.current?.querySelector('[contenteditable="true"]') as HTMLElement;
        if (editable) {
          editable.focus();
          return;
        }
        const textarea = notesRef.current?.querySelector('textarea') as HTMLTextAreaElement;
        if (textarea) {
          textarea.focus();
        }
      }, 300);
    }
  });

  useRegisterShortcut('tab_section', () => {
    if (open) {
      const nextIndex = (currentSectionIndex + 1) % sections.length;
      setCurrentSectionIndex(nextIndex);
      focusSection(nextIndex);
    }
  });

  const handleUpdate = useCallback((updates: Partial<Task>) => {
    // Auto-set start date when moving from todo to doing
    const finalUpdates = { ...updates };
    if (updates.status && shouldAutoSetStartDate(editedTask.status, updates.status, editedTask.startDate)) {
      finalUpdates.startDate = getTodayDateString();
    }

    const timestamp = new Date().toISOString();
    const updated = {
      ...editedTask,
      ...finalUpdates,
      updatedAt: timestamp
    };

    // Mark that we have a local update in progress to prevent race conditions
    localUpdateInProgressRef.current = true;
    localUpdateTimestampRef.current = timestamp;

    // Clear any existing timeout
    if (localUpdateTimeoutRef.current) {
      clearTimeout(localUpdateTimeoutRef.current);
    }

    // Set a timeout to automatically clear the in-flight flag after 10 seconds
    // This ensures we don't get stuck if the API call fails or takes too long
    localUpdateTimeoutRef.current = setTimeout(() => {
      localUpdateInProgressRef.current = false;
      localUpdateTimestampRef.current = "";
      localUpdateTimeoutRef.current = null;
    }, 10000);

    setEditedTask(updated);
    onUpdate(updated);
  }, [editedTask, onUpdate]);

  const handleAddComment = useCallback(() => {
    const trimmedComment = newComment.trim();
    if (!trimmedComment) {
      return;
    }

    const comment: Comment = {
      id: crypto.randomUUID(),
      text: trimmedComment,
      author: editedTask.assignee,
      createdAt: new Date().toISOString(),
    };

    handleUpdate({ comments: [...(editedTask.comments || []), comment] });
    setNewComment("");
  }, [newComment, editedTask.assignee, editedTask.comments, handleUpdate]);

  const handleEditComment = useCallback((commentId: string, newText: string) => {
    const updatedComments = editedTask.comments.map(c =>
      c.id === commentId ? { ...c, text: newText } : c
    );
    handleUpdate({ comments: updatedComments });
  }, [editedTask.comments, handleUpdate]);

  const handleDeleteComment = useCallback((commentId: string) => {
    const updatedComments = editedTask.comments.filter(c => c.id !== commentId);
    handleUpdate({ comments: updatedComments });
  }, [editedTask.comments, handleUpdate]);

  const handleAddAttachment = useCallback((url: string) => {
    handleUpdate({ attachments: [...(editedTask.attachments || []), url] });
  }, [editedTask.attachments, handleUpdate]);

  const handleRemoveAttachment = useCallback((index: number) => {
    const updatedAttachments = (editedTask.attachments || []).filter((_, i) => i !== index);
    handleUpdate({ attachments: updatedAttachments });
  }, [editedTask.attachments, handleUpdate]);

  const handleEditAttachment = useCallback((index: number, newUrl: string) => {
    const updatedAttachments = [...(editedTask.attachments || [])];
    updatedAttachments[index] = newUrl;
    handleUpdate({ attachments: updatedAttachments });
  }, [editedTask.attachments, handleUpdate]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange} modal={false}>
      <SheetContent
        side="right"
        className={`p-0 border-l border-border/30 transition-[width,max-width,opacity,transform] duration-[400ms] ease-butter task-sheet-scroll overflow-y-auto shadow-2xl will-change-[width,max-width,opacity,transform] ${isExpanded ? "w-full sm:max-w-[900px]" : "w-full sm:max-w-[600px]"
          } ${isExiting ? "opacity-0 scale-[0.98]" : "opacity-100 scale-100"}`}
        onOpenAutoFocus={(e) => e.preventDefault()}
        style={{
          transform: isExiting ? "scale(0.98) translateZ(0)" : "scale(1) translateZ(0)",
          backfaceVisibility: "hidden",
          WebkitBackfaceVisibility: "hidden",
        }}
      >
        {/* Sticky Header */}
        <SheetHeader className="sticky top-0 z-10 bg-background/95 backdrop-blur-sm px-8 py-6 border-b border-border/30">
          <SheetTitle className="sr-only">Task Details</SheetTitle>
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => {
                  if (onToggleExpanded) {
                    onToggleExpanded();
                  } else {
                    setIsExpanded(!isExpanded);
                  }
                  toast.success(isExpanded ? "Peek mode" : "Expanded view");
                }}
                className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-lg transition-all duration-200 hover:scale-105 active:scale-95"
                title={isExpanded ? "Minimize (Cmd/Ctrl+E)" : "Expand (Cmd/Ctrl+E)"}
              >
                <div className={`transition-all duration-300 ${isExpanded ? 'rotate-0' : 'rotate-0'}`}>
                  {isExpanded ? (
                    <Minimize2 className="h-4 w-4 transition-transform duration-300" />
                  ) : (
                    <Maximize2 className="h-4 w-4 transition-transform duration-300" />
                  )}
                </div>
              </Button>
              {onFullPage && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    setIsExiting(true);
                    setTimeout(() => {
                      onFullPage();
                    }, 200); // Smooth exit before full page opens
                    toast.success("Full page view");
                  }}
                  className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-lg transition-all duration-200 hover:scale-105 active:scale-95"
                  title="Full page (Cmd/Ctrl+Shift+E)"
                >
                  <Expand className="h-4 w-4 transition-transform duration-300 hover:rotate-45" />
                </Button>
              )}
              <span className="text-xs text-muted-foreground transition-all duration-300">
                {isExpanded ? "Expanded" : "Peek"}
              </span>
            </div>

            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsDeleteDialogOpen(true)}
              className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-all duration-200 hover:scale-105 active:scale-95"
              title="Delete task"
            >
              <Trash2 className="h-4 w-4 transition-transform duration-200 hover:rotate-12" />
            </Button>
          </div>
        </SheetHeader>

        {/* Content */}
        <div className="px-8 py-6 space-y-6">
          {isTransitioning ? (
            /* Skeleton Loading State */
            <div className="space-y-8 animate-in fade-in duration-150">
              {/* Title Skeleton */}
              <div className="space-y-3">
                <Skeleton className={`${isExpanded ? "h-12" : "h-10"} w-3/4 transition-all duration-300`} />
              </div>

              {/* Properties Grid Skeleton */}
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-3">
                  <Skeleton className="h-3 w-16" />
                  <Skeleton className="h-10 w-full" />
                </div>
                <div className="space-y-3">
                  <Skeleton className="h-3 w-24" />
                  <Skeleton className="h-10 w-full" />
                </div>
              </div>

              {/* Dates Skeleton */}
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-3">
                  <Skeleton className="h-3 w-20" />
                  <Skeleton className="h-10 w-full" />
                </div>
                <div className="space-y-3">
                  <Skeleton className="h-3 w-20" />
                  <Skeleton className="h-10 w-full" />
                </div>
              </div>

              {/* Description Skeleton */}
              <div className="space-y-3">
                <Skeleton className="h-3 w-24" />
                <Skeleton className={`w-full ${isExpanded ? "h-32" : "h-24"}`} />
              </div>

              {/* Attachments Skeleton */}
              <div className="space-y-3">
                <Skeleton className="h-3 w-28" />
                <Skeleton className="h-10 w-full" />
              </div>

              {/* Notes Skeleton */}
              <div className="space-y-3">
                <Skeleton className="h-3 w-16" />
                <Skeleton className={`w-full ${isExpanded ? "h-[500px]" : "h-[400px]"}`} />
              </div>
            </div>
          ) : (
            /* Actual Content */
            <div className="space-y-8 animate-in fade-in duration-200">
              {/* Title */}
              <div ref={titleRef}>
                <RichTextEditor
                  content={editedTask.title}
                  onChange={(content) => handleUpdate({ title: content })}
                  placeholder="Task title"
                  variant="title"
                  resetKey={resetKey}
                  className="text-3xl font-semibold"
                />
              </div>

              {/* Properties Grid */}
              <div className="grid grid-cols-2 gap-6 transition-[grid-template-columns] duration-[400ms] ease-butter will-change-[grid-template-columns]">
                <div className="space-y-3">
                  <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Status
                  </Label>
                  <Select
                    value={editedTask.status}
                    onValueChange={(value) => handleUpdate({ status: value as Task["status"] })}
                  >
                    <SelectTrigger ref={statusRef} className="h-10 border-border/50 focus:border-primary/50 transition-[border-color] duration-150 hover:border-primary/30">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="todo">To-Do</SelectItem>
                      <SelectItem value="doing">In Progress</SelectItem>
                      <SelectItem value="done">Done</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-3" ref={valueStreamRef}>
                  <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Value Stream
                  </Label>
                  <ValueStreamCombobox
                    value={editedTask.valueStream || ""}
                    onChange={(value) => handleUpdate({ valueStream: value })}
                    placeholder="Select or create value stream..."
                    className="w-full"
                  />
                </div>
              </div>

              {/* Dates */}
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-3">
                  <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    <Calendar className="h-3.5 w-3.5 opacity-60" />
                    Start Date
                  </Label>
                  <Input
                    ref={startDateRef}
                    type="date"
                    value={editedTask.startDate || ""}
                    onChange={(e) => handleUpdate({ startDate: e.target.value })}
                    className="h-10 border-border/50 focus:border-primary/50 transition-[border-color] duration-150 hover:border-primary/30"
                  />
                </div>

                <div className="space-y-3">
                  <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    <Calendar className="h-3.5 w-3.5 opacity-60" />
                    Due Date
                  </Label>
                  <Input
                    ref={dueDateRef}
                    type="date"
                    value={editedTask.dueDate || ""}
                    onChange={(e) => handleUpdate({ dueDate: e.target.value })}
                    className="h-10 border-border/50 focus:border-primary/50 transition-[border-color] duration-150 hover:border-primary/30"
                  />
                </div>
              </div>



              {/* Description */}
              <div className="space-y-3">
                <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Description
                </Label>
                <div ref={descriptionRef}>
                  <RichTextEditor
                    content={editedTask.description || ""}
                    onChange={(content) => handleUpdate({ description: content })}
                    placeholder="Add a detailed description..."
                    variant="full"
                    resetKey={resetKey}
                    className="min-h-[60px]"
                  />
                </div>
              </div>

              {/* Comments - Chat-style */}
              <div className="space-y-4">
                <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  <MessageSquare className="h-3.5 w-3.5 opacity-60" />
                  Comments
                </Label>
                {editedTask.comments.length > 0 && (
                  <div className="space-y-3">
                    {editedTask.comments.map((comment) => (
                      <CommentItem
                        key={comment.id}
                        comment={comment}
                        onEdit={handleEditComment}
                        onDelete={handleDeleteComment}
                        currentUser={editedTask.assignee}
                      />
                    ))}
                  </div>
                )}
                <div className="flex gap-3 items-start">
                  <div className="flex-shrink-0 w-7 h-7 rounded-full bg-muted flex items-center justify-center mt-1">
                    <User className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                  <div
                    className="flex-1"
                    ref={commentsRef}
                    onKeyDown={(e) => {
                      // Handle Command+Enter or Ctrl+Enter to post comment
                      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                        e.preventDefault();
                        handleAddComment();
                      }
                    }}
                  >
                    <Textarea
                      value={newComment}
                      onChange={(e) => setNewComment(e.target.value)}
                      placeholder="Add a comment... Press Cmd/Ctrl+Enter to post"
                      className="border-0 border-b rounded-none min-h-[60px]"
                    />
                    <Button
                      onClick={handleAddComment}
                      size="sm"
                      className="mt-2 h-8"
                      disabled={!newComment.trim()}
                    >
                      Comment
                    </Button>
                  </div>
                </div>
              </div>

              {/* Attachments */}
              <div className="space-y-3">
                <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  <Paperclip className="h-3.5 w-3.5 opacity-60" />
                  Attachments
                </Label>
                <UnifiedAttachments
                  attachments={editedTask.attachments}
                  onAddAttachment={handleAddAttachment}
                  onRemoveAttachment={handleRemoveAttachment}
                  onEditAttachment={handleEditAttachment}
                />
              </div>

              {/* Notes / Canvas Section - Zen & Papyrus Theme */}
              <div className="mt-12 group">
                <div className="flex items-center gap-3 mb-5 opacity-80 transition-opacity duration-300 group-hover:opacity-100">
                  <div className="h-[1px] flex-1 bg-gradient-to-r from-transparent via-border/40 to-border/40" />
                  <div className="flex items-center gap-2 px-4 py-1.5 rounded-full border border-[#E5E0D8] dark:border-[#2C2A25] bg-[#F9F8F6] dark:bg-[#1A1918] shadow-sm">
                    <ScrollText className="h-4 w-4 text-amber-700/80 dark:text-amber-400/80" />
                    <Label className="text-[11px] font-semibold text-amber-900/80 dark:text-amber-200/80 uppercase tracking-widest cursor-default">
                      Workspace Canvas
                    </Label>
                  </div>
                  <div className="h-[1px] flex-1 bg-gradient-to-l from-transparent via-border/40 to-border/40" />
                </div>

                {/* Seamless AskLotus Integration */}
                {!isTransitioning && (
                  <div className="mb-6">
                    <AskLotus taskId={task.id} />
                  </div>
                )}

                <div className="relative rounded-2xl border border-[#E5E0D8] dark:border-[#2C2A25] bg-[#FCFBF8] dark:bg-[#161615] shadow-[0_8px_30px_rgb(0,0,0,0.03)] dark:shadow-[0_8px_30px_rgb(0,0,0,0.2)] transition-all duration-500 hover:shadow-[0_8px_30px_rgb(0,0,0,0.06)] overflow-hidden">
                  {/* Subtle papyrus/canvas texture overlay */}
                  <div
                    className="absolute inset-0 z-0 opacity-[0.35] mix-blend-multiply dark:mix-blend-screen pointer-events-none"
                    style={{
                      backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noiseFilter%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.8%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noiseFilter)%22/%3E%3C/svg%3E")',
                      backgroundSize: '150px 150px'
                    }}
                  />

                  {/* Subtle grid pattern background */}
                  <div className="absolute inset-0 z-0 opacity-[0.02] dark:opacity-[0.03] pointer-events-none"
                    style={{ backgroundImage: 'radial-gradient(circle at 1px 1px, currentColor 1px, transparent 0)', backgroundSize: '24px 24px' }} />

                  <div ref={notesRef} className="relative z-10 p-6 sm:p-8 min-h-[400px]">
                    <RichTextEditor
                      content={editedTask.notes || ""}
                      onChange={(content) => handleUpdate({ notes: content })}
                      placeholder="Start capturing thoughts, research, or documentation... (Ctrl+D to focus)"
                      variant="full"
                      resetKey={resetKey}
                      className="min-h-[400px] border-none shadow-none focus-within:ring-0 px-0 [&_.ProseMirror]:px-0 [&_.ProseMirror]:min-h-[400px] bg-transparent"
                    />
                  </div>
                </div>
              </div>


            </div>
          )}

        </div>
      </SheetContent>

      <DeleteTaskDialog
        open={isDeleteDialogOpen}
        onOpenChange={setIsDeleteDialogOpen}
        taskTitle={editedTask.title}
        onConfirm={async () => {
          try {
            await onDelete(task.id);
          } catch (error) {
            // Re-throw so DeleteTaskDialog can handle it (keep dialog open on error)
            throw error;
          }
        }}
      />
    </Sheet>
  );
};

