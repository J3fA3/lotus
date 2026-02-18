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
import { Calendar, Paperclip, MessageSquare, Trash2, User, ArrowLeft, Minimize2 } from "lucide-react";
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
  const assigneeRef = useRef<HTMLInputElement>(null);
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
      className={`fixed inset-0 z-50 bg-background overflow-y-auto will-change-[transform,opacity] ${
        isExiting 
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
            />
          </div>

          {/* Properties Grid */}
          <div className="grid grid-cols-3 gap-8">
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

            <div className="space-y-3">
              <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                <User className="h-3.5 w-3.5 opacity-60" />
                Assignee
              </Label>
              <Input
                ref={assigneeRef}
                value={editedTask.assignee}
                onChange={(e) => handleUpdate({ assignee: e.target.value })}
                className="h-11 border-border/50 focus:border-primary/50 transition-[border-color] duration-150"
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
            <Label className="text-sm font-semibold text-foreground">
              Description
            </Label>
            <div ref={descriptionRef}>
              <RichTextEditor
                content={editedTask.description || ""}
                onChange={(content) => handleUpdate({ description: content })}
                variant="full"
                placeholder="Add a detailed description..."
                resetKey={resetKey}
              />
            </div>
          </div>

          {/* Attachments Section - Full Width */}
          <div className="space-y-4">
            <Label className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Paperclip className="h-4 w-4 opacity-60" />
              Attachments
            </Label>
            <UnifiedAttachments
              attachments={editedTask.attachments}
              onAddAttachment={handleAddAttachment}
              onRemoveAttachment={handleRemoveAttachment}
              onEditAttachment={handleEditAttachment}
            />
          </div>

          {/* Comments Section - Full Width, Chat-style */}
          <div className="space-y-4">
            <Label className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <MessageSquare className="h-4 w-4 opacity-60" />
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
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center mt-1">
                <User className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="flex-1" ref={commentsRef}>
                <Textarea
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Add a comment..."
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

          {/* Notes Section - Full Width, No Header */}
          <div className="space-y-3 pb-24">
            <Label className="text-sm font-semibold text-foreground">
              Notes
            </Label>
            <div ref={notesRef}>
              <RichTextEditor
                content={editedTask.notes || ""}
                onChange={(content) => handleUpdate({ notes: content })}
                variant="full"
                placeholder="Write your notes, thoughts, or documentation here..."
                className="min-h-[500px]"
                resetKey={resetKey}
              />
            </div>
            <span className="text-xs text-muted-foreground">Ctrl+D to focus notes • Ctrl+Tab to cycle through sections</span>
          </div>
        <AskLotus taskId={task.id} />
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
