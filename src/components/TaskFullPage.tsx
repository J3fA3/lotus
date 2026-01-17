import { useState, useEffect, useRef, useCallback } from "react";
import { Task, Comment } from "@/types/task";
import { LotusIcon } from "./LotusIcon";
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
import { Calendar, Paperclip, MessageSquare, Trash2, X, User, FileText, ArrowLeft, Minimize2 } from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";
import { ValueStreamCombobox } from "./ValueStreamCombobox";
import { RichTextEditor } from "./RichTextEditor";
import { TaskScheduler } from "./TaskScheduler";
import { useRegisterShortcut } from "@/contexts/ShortcutContext";
import { DeleteTaskDialog } from "./DeleteTaskDialog";

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
  const [newAttachment, setNewAttachment] = useState("");
  const [commentResetKey, setCommentResetKey] = useState(0);
  const [isExiting, setIsExiting] = useState(false);
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
  const scheduleRef = useRef<HTMLDivElement>(null);
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
    }
  }, [task.updatedAt]);

  // Section tabbing - list of focusable sections in order
  const sections = [
    titleRef,        // RichTextEditor
    statusRef,       // SelectTrigger
    valueStreamRef,  // ValueStreamCombobox button
    startDateRef,    // Input date
    dueDateRef,      // Input date
    scheduleRef,     // TaskScheduler button
    descriptionRef,  // RichTextEditor
    notesRef,       // RichTextEditor
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

      // For RichTextEditor divs, find the contenteditable element
      const editable = element.querySelector('[contenteditable="true"]') as HTMLElement;
      if (editable) {
        editable.focus();
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

      // For TaskScheduler: find the focusable button
      if (index === 5) { // scheduleRef is at index 5
        // Try to find button with text containing "Find" or "best time" (collapsed state)
        const buttons = element.querySelectorAll('button');
        for (const btn of buttons) {
          const text = btn.textContent || '';
          if (text.includes('Find') || text.includes('best time') || text.includes('Find the best')) {
            btn.focus();
            return;
          }
        }
        // If scheduled, try to find the cancel button or any interactive button
        for (const btn of buttons) {
          if (btn.textContent?.includes('Cancel') || btn.textContent?.includes('Scheduled')) {
            btn.focus();
            return;
          }
        }
        // Fallback: focus first focusable button if found
        if (buttons.length > 0) {
          buttons[0].focus();
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
      const editable = notesRef.current?.querySelector('[contenteditable="true"]') as HTMLElement;
      if (editable) {
        editable.focus();
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
    // Increment reset key to force the RichTextEditor to sync with the empty content
    setCommentResetKey(prev => prev + 1);
  };

  const handleAddAttachment = () => {
    const trimmedUrl = newAttachment.trim();
    if (!trimmedUrl) {
      return;
    }
    
    handleUpdate({ attachments: [...(editedTask.attachments || []), trimmedUrl] });
    setNewAttachment("");
  };

  const handleRemoveAttachment = (index: number) => {
    const updatedAttachments = (editedTask.attachments || []).filter((_, i) => i !== index);
    handleUpdate({ attachments: updatedAttachments });
  };

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
              onChange={(html) => handleUpdate({ title: html })}
              placeholder="Task title - Type / for Word Art styles!"
              variant="title"
              className="text-5xl"
              autoFocus={false}
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

          {/* Schedule */}
          <div ref={scheduleRef}>
            <TaskScheduler
              taskId={editedTask.id}
              taskTitle={editedTask.title}
              comments={editedTask.comments}
              onScheduled={(action) => {
                if (action === 'approved') {
                  toast.success("Time block added to calendar");
                }
              }}
            />
          </div>

          {/* Description */}
          <div className="space-y-4">
            <Label className="text-sm font-semibold text-foreground">
              Description
            </Label>
            <div ref={descriptionRef}>
              <RichTextEditor
                content={editedTask.description || ""}
                onChange={(html) => handleUpdate({ description: html })}
                placeholder="Add a detailed description... Type / for commands, * for bullets"
                variant="minimal"
              />
            </div>
          </div>

          {/* Attachments Section - Full Width */}
          <div className="space-y-4">
            <Label className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Paperclip className="h-4 w-4 opacity-60" />
              Attachments
            </Label>
            <div className="flex gap-2">
              <Input
                value={newAttachment}
                onChange={(e) => setNewAttachment(e.target.value)}
                placeholder="Paste attachment URL..."
                className="h-11 border-border/50 focus:border-primary/50 transition-[border-color] duration-150"
              />
              <Button
                onClick={handleAddAttachment}
                size="sm"
                className="h-11 px-6 bg-primary hover:bg-primary/90 transition-colors duration-150"
              >
                Add
              </Button>
            </div>
            {editedTask.attachments.length > 0 && (
              <div className="space-y-2">
                {editedTask.attachments.map((attachment, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border border-border/20 group hover:border-border/40 transition-[border-color] duration-150"
                  >
                    <span className="text-sm truncate text-muted-foreground">{attachment}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveAttachment(index)}
                      className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity duration-150"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
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
                  <div key={comment.id} className="flex gap-3">
                    <div
                      className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                        comment.author === "Lotus"
                          ? "bg-gradient-to-br from-[hsl(var(--lotus-green-light))] to-[hsl(var(--lotus-green-medium))]"
                          : "bg-primary/10"
                      }`}
                    >
                      {comment.author === "Lotus" ? (
                        <LotusIcon className="text-[hsl(var(--lotus-paper))]" size={16} />
                      ) : (
                        <User className="h-4 w-4 text-primary" />
                      )}
                    </div>
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-foreground">{comment.author}</span>
                        <span className="text-xs text-muted-foreground">
                          {(() => {
                            try {
                              const date = new Date(comment.createdAt);
                              return isNaN(date.getTime()) ? comment.createdAt : format(date, "MMM d");
                            } catch {
                              return comment.createdAt;
                            }
                          })()}
                        </span>
                      </div>
                      <div
                        className="text-sm text-foreground/90 leading-relaxed prose prose-sm max-w-none"
                        dangerouslySetInnerHTML={{ __html: comment.text }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
            <div className="flex gap-3 items-start">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center mt-1">
                <User className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="flex-1" ref={commentsRef}>
                <RichTextEditor
                  content={newComment}
                  onChange={setNewComment}
                  placeholder="Add a comment... Type / for commands, * for bullets"
                  variant="minimal"
                  className="border-0 border-b rounded-none"
                  resetKey={commentResetKey}
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
                onChange={(html) => handleUpdate({ notes: html })}
                placeholder="Write your notes, thoughts, or documentation here... Type / for commands, * for bullets, create tables and more!"
                variant="full"
              />
            </div>
            <span className="text-xs text-muted-foreground">Ctrl+D to focus notes • Ctrl+Tab to cycle through sections • Full formatting available: headings, tables, code blocks, and Word Art!</span>
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
