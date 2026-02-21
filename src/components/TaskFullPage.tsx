import { useState, useEffect, useRef, useCallback } from "react";
import { Task, Comment } from "@/types/task";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { Button } from "./ui/button";
import { Label } from "./ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Calendar, Paperclip, MessageSquare, Trash2, User, ArrowLeft, Minimize2, ScrollText, Send } from "lucide-react";
import { ValueStreamCombobox } from "./ValueStreamCombobox";
import { useRegisterShortcut } from "@/contexts/ShortcutContext";
import { DeleteTaskDialog } from "./DeleteTaskDialog";
import { CommentItem } from "./CommentItem";
import { AskLotus } from "./AskLotus";
import { RichTextEditor } from "./RichTextEditor";
import { UnifiedAttachments } from "./UnifiedAttachments";

interface TaskFullPageProps {
  task: Task;
  onUpdate: (task: Task) => void;
  onDelete: (taskId: string) => void;
  onClose: () => void;
  onFullyClose?: () => void;
}

export const TaskFullPage = ({
  task,
  onUpdate,
  onDelete,
  onClose,
  onFullyClose,
}: TaskFullPageProps) => {
  const [editedTask, setEditedTask] = useState<Task>({
    ...task,
    comments: task.comments || [],
    attachments: task.attachments || [],
  });
  const [newComment, setNewComment] = useState("");
  const [isExiting, setIsExiting] = useState(false);
  const [resetKey, setResetKey] = useState(0);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const notesRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLDivElement>(null);
  const descriptionRef = useRef<HTMLDivElement>(null);
  const statusRef = useRef<HTMLButtonElement>(null);
  const commentsRef = useRef<HTMLDivElement>(null);
  const startDateRef = useRef<HTMLInputElement>(null);
  const dueDateRef = useRef<HTMLInputElement>(null);
  const valueStreamRef = useRef<HTMLDivElement>(null);
  const [currentSectionIndex, setCurrentSectionIndex] = useState(0);

  // Track last update timestamp to prevent feedback loops
  const lastExternalUpdateRef = useRef<string>("");

  // Handle exit animation before closing
  const handleClose = useCallback(() => {
    setIsExiting(true);
    setTimeout(() => {
      if (onFullyClose) {
        // Fully close with smooth animation
        onFullyClose();
      } else {
        onClose();
      }
    }, 300); // Match exit animation duration
  }, [onClose, onFullyClose]);

  // Update editedTask when the task prop changes
  useEffect(() => {
    // Only update if the timestamp actually changed (prevents feedback loop)
    if (task.updatedAt && task.updatedAt !== lastExternalUpdateRef.current) {
      lastExternalUpdateRef.current = task.updatedAt;
      setEditedTask({
        ...task,
        comments: task.comments || [],
        attachments: task.attachments || [],
      });
      setResetKey(prev => prev + 1);
    }
  }, [task.updatedAt]);

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

      // For contenteditable elements (RichTextEditor)
      const contentEditable = element.querySelector('[contenteditable="true"]') as HTMLElement;
      if (contentEditable) {
        contentEditable.focus();
        return;
      }

      // For Textarea elements
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
    handleClose();
  });

  useRegisterShortcut('focus_notes', () => {
    notesRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => {
      const contentEditable = notesRef.current?.querySelector('[contenteditable="true"]') as HTMLElement;
      if (contentEditable) {
        contentEditable.focus();
        return;
      }
      const textarea = notesRef.current?.querySelector('textarea') as HTMLTextAreaElement;
      if (textarea) {
        textarea.focus();
      }
    }, 300);
  });

  useRegisterShortcut('tab_section', () => {
    const nextIndex = (currentSectionIndex + 1) % sections.length;
    setCurrentSectionIndex(nextIndex);
    focusSection(nextIndex);
  });

  const handleUpdate = useCallback((updates: Partial<Task>) => {
    const updated = {
      ...editedTask,
      ...updates,
      updatedAt: new Date().toISOString()
    };
    setEditedTask(updated);
    onUpdate(updated);
  }, [editedTask, onUpdate]);

  const handleAddComment = () => {
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
  };

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
    <div
      className={`fixed inset-0 z-50 bg-background overflow-y-auto will-change-[transform,opacity] ${isExiting
        ? "animate-view-morph-out"
        : "animate-view-morph-in"
        }`}
      style={{
        transform: isExiting ? "scale(0.98) translateZ(0)" : "scale(1) translateZ(0)",
        opacity: isExiting ? 0 : 1,
        transition: isExiting
          ? "opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)"
          : "opacity 0.4s cubic-bezier(0.16, 1, 0.3, 1), transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)",
        backfaceVisibility: "hidden",
        WebkitBackfaceVisibility: "hidden",
      }}
    >
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background/95 backdrop-blur-sm border-b border-border/30 transition-all duration-300">
        <div className="max-w-5xl mx-auto px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={handleClose}
              className="h-9 w-9 text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-lg transition-all"
              title="Back to board (Esc)"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div className="flex items-center gap-2">
              <Minimize2 className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium text-muted-foreground">Full Page</span>
            </div>
          </div>

          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsDeleteDialogOpen(true)}
            className="h-9 w-9 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-all"
            title="Delete task"
          >
            <Trash2 className="h-5 w-5" />
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-5xl mx-auto px-8 py-12">
        <div className="space-y-12">
          {/* Title */}
          <div ref={titleRef}>
            <RichTextEditor
              content={editedTask.title}
              onChange={(content) => handleUpdate({ title: content })}
              variant="title"
              placeholder="Task title"
              resetKey={resetKey}
              className="text-4xl font-semibold tracking-tight"
            />
          </div>

          {/* Properties Grid */}
          <div className="grid grid-cols-2 gap-8">
            <div className="space-y-3">
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Status
              </Label>
              <Select
                value={editedTask.status}
                onValueChange={(value) => handleUpdate({ status: value as Task["status"] })}
              >
                <SelectTrigger ref={statusRef} className="h-11 border-border/50 focus:border-primary/50 transition-[border-color] duration-150">
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
          <div className="grid grid-cols-2 gap-8">
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
                className="h-11 border-border/50 focus:border-primary/50 transition-[border-color] duration-150"
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
                className="h-11 border-border/50 focus:border-primary/50 transition-[border-color] duration-150"
              />
            </div>
          </div>

          {/* Description */}
          <div className="space-y-4">
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Description
            </Label>
            <div ref={descriptionRef}>
              <RichTextEditor
                content={editedTask.description || ""}
                onChange={(content) => handleUpdate({ description: content })}
                variant="full"
                placeholder="Add a detailed description..."
                resetKey={resetKey}
                className="min-h-[60px]"
              />
            </div>
          </div>

          {/* Comments Section - Full Width, Chat-style */}
          <div className="space-y-3">
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
            <div className="flex gap-3 items-center">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                <User className="h-4 w-4 text-muted-foreground" />
              </div>
              <div
                ref={commentsRef}
                className="flex-1 group relative flex items-center gap-2 pl-4 pr-2 py-2.5 rounded-2xl border border-border/40 bg-muted/20 hover:border-border/70 focus-within:border-primary/40 focus-within:bg-background transition-all duration-300"
                onKeyDown={(e) => {
                  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                    e.preventDefault();
                    handleAddComment();
                  }
                }}
              >
                <Textarea
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Add a comment… ⌘↵ to post"
                  className="flex-1 border-0 bg-transparent focus-visible:ring-0 shadow-none resize-none min-h-[22px] max-h-[120px] p-0 m-0 text-sm leading-relaxed"
                  rows={1}
                />
                <button
                  onClick={handleAddComment}
                  disabled={!newComment.trim()}
                  className={`flex-shrink-0 h-9 w-9 rounded-full flex items-center justify-center transition-all duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)] ${newComment.trim()
                      ? 'opacity-100 scale-100 bg-primary text-primary-foreground shadow-md hover:scale-110 active:scale-95 cursor-pointer pointer-events-auto'
                      : 'opacity-0 scale-75 bg-transparent text-transparent pointer-events-none'
                    }`}
                  aria-label="Post comment"
                >
                  <Send className="h-4 w-4 transform translate-x-[1px]" />
                </button>
              </div>
            </div>
          </div>

          {/* Attachments Section - Full Width */}
          <div className="space-y-4">
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
          <div className="mt-16 group pb-24">
            <div className="flex items-center gap-3 mb-6 opacity-80 transition-opacity duration-300 group-hover:opacity-100">
              <div className="h-[1px] flex-1 bg-gradient-to-r from-transparent via-border/40 to-border/40" />
              <div className="flex items-center gap-2 px-5 py-2 rounded-full border border-[#E5E0D8] dark:border-[#2C2A25] bg-[#F9F8F6] dark:bg-[#1A1918] shadow-sm">
                <ScrollText className="h-4 w-4 text-amber-700/80 dark:text-amber-400/80" />
                <Label className="text-[12px] font-semibold text-amber-900/80 dark:text-amber-200/80 uppercase tracking-widest cursor-default">
                  Workspace Canvas
                </Label>
              </div>
              <div className="h-[1px] flex-1 bg-gradient-to-l from-transparent via-border/40 to-border/40" />
            </div>

            {/* Seamless AskLotus Integration */}
            <div className="mb-8">
              <AskLotus taskId={task.id} />
            </div>

            <div className="relative rounded-3xl border border-[#E5E0D8] dark:border-[#2C2A25] bg-[#FCFBF8] dark:bg-[#161615] shadow-[0_8px_30px_rgb(0,0,0,0.03)] dark:shadow-[0_8px_30px_rgb(0,0,0,0.2)] transition-all duration-500 hover:shadow-[0_8px_30px_rgb(0,0,0,0.06)] overflow-hidden">
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
                style={{ backgroundImage: 'radial-gradient(circle at 1px 1px, currentColor 1px, transparent 0)', backgroundSize: '32px 32px' }} />

              <div ref={notesRef} className="relative z-10 p-10 min-h-[600px]">
                <RichTextEditor
                  content={editedTask.notes || ""}
                  onChange={(content) => handleUpdate({ notes: content })}
                  variant="full"
                  placeholder="Start capturing thoughts, research, or documentation... (Ctrl+D to focus)"
                  className="border-none shadow-none focus-within:ring-0 px-0 [&_.ProseMirror]:px-0 [&_.ProseMirror]:min-h-[600px] bg-transparent"
                  resetKey={resetKey}
                />
              </div>
            </div>
          </div>

        </div>

      </div>

      <DeleteTaskDialog
        open={isDeleteDialogOpen}
        onOpenChange={setIsDeleteDialogOpen}
        taskTitle={editedTask.title}
        onConfirm={async () => {
          try {
            await onDelete(task.id);
            handleClose();
          } catch (error) {
            // Re-throw so DeleteTaskDialog can handle it (keep dialog open on error)
            throw error;
          }
        }}
      />
    </div>
  );
};
