import { useState, useEffect, useRef } from "react";
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
import { Calendar, Paperclip, MessageSquare, Trash2, X, User, FileText, ArrowLeft, Minimize2 } from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";

interface TaskFullPageProps {
  task: Task;
  onUpdate: (task: Task) => void;
  onDelete: (taskId: string) => void;
  onClose: () => void;
}

export const TaskFullPage = ({
  task,
  onUpdate,
  onDelete,
  onClose,
}: TaskFullPageProps) => {
  const [editedTask, setEditedTask] = useState<Task>(task);
  const [newComment, setNewComment] = useState("");
  const [newAttachment, setNewAttachment] = useState("");
  const notesRef = useRef<HTMLTextAreaElement>(null);

  // Update editedTask when the task prop changes
  useEffect(() => {
    setEditedTask(task);
  }, [task]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Escape to close
      if (e.key === "Escape") {
        onClose();
        return;
      }

      // Cmd/Ctrl + D to focus document editor
      if ((e.metaKey || e.ctrlKey) && e.key === "d") {
        e.preventDefault();
        notesRef.current?.focus();
        notesRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const handleUpdate = (updates: Partial<Task>) => {
    const updated = { 
      ...editedTask, 
      ...updates, 
      updatedAt: new Date().toISOString() 
    };
    setEditedTask(updated);
    onUpdate(updated);
  };

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

    handleUpdate({ comments: [...editedTask.comments, comment] });
    setNewComment("");
  };

  const handleAddAttachment = () => {
    const trimmedUrl = newAttachment.trim();
    if (!trimmedUrl) {
      return;
    }
    
    handleUpdate({ attachments: [...editedTask.attachments, trimmedUrl] });
    setNewAttachment("");
  };

  const handleRemoveAttachment = (index: number) => {
    const updatedAttachments = editedTask.attachments.filter((_, i) => i !== index);
    handleUpdate({ attachments: updatedAttachments });
  };

  // Auto-resize textarea for notes
  const handleNotesChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    handleUpdate({ notes: e.target.value });
    
    // Auto-resize
    const textarea = e.target;
    textarea.style.height = "auto";
    textarea.style.height = textarea.scrollHeight + "px";
  };

  return (
    <div className="fixed inset-0 z-50 bg-background overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background/95 backdrop-blur-sm border-b border-border/30">
        <div className="max-w-5xl mx-auto px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
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
            onClick={() => {
              if (confirm(`Delete task "${editedTask.title}"?`)) {
                onDelete(task.id);
                onClose();
              }
            }}
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
          <div>
            <Input
              value={editedTask.title}
              onChange={(e) => handleUpdate({ title: e.target.value })}
              className="text-5xl font-bold border-0 px-0 focus-visible:ring-0 tracking-tight bg-transparent h-auto py-2"
              placeholder="Task title"
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
                <SelectTrigger className="h-11 border-border/50 focus:border-primary/50 transition-all">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todo">To-Do</SelectItem>
                  <SelectItem value="doing">In Progress</SelectItem>
                  <SelectItem value="done">Done</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-3">
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Value Stream
              </Label>
              <Input
                value={editedTask.valueStream || ""}
                onChange={(e) => handleUpdate({ valueStream: e.target.value })}
                placeholder="e.g., Marketing, Development"
                className="h-11 border-border/50 focus:border-primary/50 transition-all"
              />
            </div>

            <div className="space-y-3">
              <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                <User className="h-3.5 w-3.5 opacity-60" />
                Assignee
              </Label>
              <Input
                value={editedTask.assignee}
                onChange={(e) => handleUpdate({ assignee: e.target.value })}
                className="h-11 border-border/50 focus:border-primary/50 transition-all"
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
                type="date"
                value={editedTask.startDate || ""}
                onChange={(e) => handleUpdate({ startDate: e.target.value })}
                className="h-11 border-border/50 focus:border-primary/50 transition-all"
              />
            </div>

            <div className="space-y-3">
              <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                <Calendar className="h-3.5 w-3.5 opacity-60" />
                Due Date
              </Label>
              <Input
                type="date"
                value={editedTask.dueDate || ""}
                onChange={(e) => handleUpdate({ dueDate: e.target.value })}
                className="h-11 border-border/50 focus:border-primary/50 transition-all"
              />
            </div>
          </div>

          {/* Description */}
          <div className="space-y-4">
            <Label className="text-sm font-semibold text-foreground">
              Description
            </Label>
            <Textarea
              value={editedTask.description || ""}
              onChange={(e) => handleUpdate({ description: e.target.value })}
              placeholder="Add a detailed description..."
              rows={5}
              className="resize-none border-border/50 focus:border-primary/50 transition-all leading-relaxed text-base"
            />
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
                className="h-11 border-border/50 focus:border-primary/50 transition-all"
              />
              <Button 
                onClick={handleAddAttachment} 
                size="sm"
                className="h-11 px-6 bg-primary hover:bg-primary/90 transition-all"
              >
                Add
              </Button>
            </div>
            {editedTask.attachments.length > 0 && (
              <div className="space-y-2">
                {editedTask.attachments.map((attachment, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border border-border/20 group hover:border-border/40 transition-all"
                  >
                    <span className="text-sm truncate text-muted-foreground">{attachment}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveAttachment(index)}
                      className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-all"
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
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                      <User className="h-4 w-4 text-primary" />
                    </div>
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-foreground">{comment.author}</span>
                        <span className="text-xs text-muted-foreground">
                          {format(new Date(comment.createdAt), "MMM d")}
                        </span>
                      </div>
                      <p className="text-sm text-foreground/90 leading-relaxed">{comment.text}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <div className="flex gap-3 items-start">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center mt-1">
                <User className="h-4 w-4 text-muted-foreground" />
              </div>
              <Textarea
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleAddComment();
                  }
                }}
                placeholder="Add a comment..."
                rows={1}
                className="flex-1 resize-none border-0 border-b border-border/30 focus:border-primary/50 transition-all leading-relaxed rounded-none px-0 focus-visible:ring-0 focus-visible:ring-offset-0"
                style={{ minHeight: '32px' }}
              />
            </div>
          </div>

          {/* Notes Section - Full Width, No Header */}
          <div className="space-y-3 pb-24">
            <Textarea
              ref={notesRef}
              value={editedTask.notes || ""}
              onChange={handleNotesChange}
              placeholder="Write your notes, thoughts, or documentation here..."
              className="min-h-[400px] resize-none border-border/30 focus:border-primary/50 transition-all leading-relaxed text-base p-6 rounded-lg"
              style={{ 
                overflow: "hidden",
                fontFamily: "'Inter', sans-serif"
              }}
            />
            <span className="text-xs text-muted-foreground">Cmd/Ctrl+D to focus notes</span>
          </div>
        </div>
      </div>
    </div>
  );
};
