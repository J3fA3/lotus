import { useState, useEffect, useRef } from "react";
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
import { Label } from "./ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Calendar, Paperclip, MessageSquare, Trash2, X, User, Maximize2, Minimize2, FileText } from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";

interface TaskDetailSheetProps {
  task: Task;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUpdate: (task: Task) => void;
  onDelete: (taskId: string) => void;
}

export const TaskDetailSheet = ({
  task,
  open,
  onOpenChange,
  onUpdate,
  onDelete,
}: TaskDetailSheetProps) => {
  const [editedTask, setEditedTask] = useState<Task>(task);
  const [newComment, setNewComment] = useState("");
  const [newAttachment, setNewAttachment] = useState("");
  const [isExpanded, setIsExpanded] = useState(false);
  const notesRef = useRef<HTMLTextAreaElement>(null);

  // Update editedTask when the task prop changes
  useEffect(() => {
    setEditedTask(task);
  }, [task]);

  // Keyboard shortcuts
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Escape to close
      if (e.key === "Escape") {
        onOpenChange(false);
        return;
      }

      // Cmd/Ctrl + E to toggle expand
      if ((e.metaKey || e.ctrlKey) && e.key === "e") {
        e.preventDefault();
        setIsExpanded(!isExpanded);
        toast.success(isExpanded ? "Peek mode" : "Expanded view");
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
  }, [open, isExpanded, onOpenChange]);

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
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent 
        side="right"
        className={`p-0 border-l border-border/30 transition-all duration-300 ease-out task-sheet-scroll overflow-y-auto ${
          isExpanded ? "w-full sm:max-w-[900px]" : "w-full sm:max-w-[600px]"
        }`}
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        {/* Sticky Header */}
        <SheetHeader className="sticky top-0 z-10 bg-background/95 backdrop-blur-sm px-8 py-6 border-b border-border/30">
          <SheetTitle className="sr-only">Task Details</SheetTitle>
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => {
                  setIsExpanded(!isExpanded);
                  toast.success(isExpanded ? "Peek mode" : "Expanded view");
                }}
                className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-lg transition-all"
                title={isExpanded ? "Minimize (Cmd/Ctrl+E)" : "Expand (Cmd/Ctrl+E)"}
              >
                {isExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
              </Button>
              <span className="text-xs text-muted-foreground">
                {isExpanded ? "Expanded" : "Peek"}
              </span>
            </div>

            <Button
              variant="ghost"
              size="icon"
              onClick={() => onDelete(task.id)}
              className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-all"
              title="Delete task"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </SheetHeader>

        {/* Content */}
        <div className="px-8 py-6 space-y-8">
          {/* Title */}
          <div>
            <Input
              value={editedTask.title}
              onChange={(e) => handleUpdate({ title: e.target.value })}
              className="text-3xl font-semibold border-0 px-0 focus-visible:ring-0 tracking-tight bg-transparent"
              placeholder="Task title"
              autoFocus={false}
            />
          </div>

          {/* Properties Grid */}
          <div className="grid grid-cols-2 gap-6">
            <div className="space-y-3">
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Status
              </Label>
              <Select
                value={editedTask.status}
                onValueChange={(value) => handleUpdate({ status: value as Task["status"] })}
              >
                <SelectTrigger className="h-10 border-border/50 focus:border-primary/50 transition-all">
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
                className="h-10 border-border/50 focus:border-primary/50 transition-all"
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
                type="date"
                value={editedTask.startDate || ""}
                onChange={(e) => handleUpdate({ startDate: e.target.value })}
                className="h-10 border-border/50 focus:border-primary/50 transition-all"
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
                className="h-10 border-border/50 focus:border-primary/50 transition-all"
              />
            </div>
          </div>

          {/* Assignee */}
          <div className="space-y-3">
            <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              <User className="h-3.5 w-3.5 opacity-60" />
              Assignee
            </Label>
            <Input
              value={editedTask.assignee}
              onChange={(e) => handleUpdate({ assignee: e.target.value })}
              className="h-10 border-border/50 focus:border-primary/50 transition-all"
            />
          </div>

          {/* Description */}
          <div className="space-y-3">
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Description
            </Label>
            <Textarea
              value={editedTask.description || ""}
              onChange={(e) => handleUpdate({ description: e.target.value })}
              placeholder="Add a detailed description..."
              rows={4}
              className="resize-none border-border/50 focus:border-primary/50 transition-all leading-relaxed"
            />
          </div>

          {/* Attachments */}
          <div className="space-y-4">
            <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              <Paperclip className="h-3.5 w-3.5 opacity-60" />
              Attachments
            </Label>
            <div className="flex gap-2">
              <Input
                value={newAttachment}
                onChange={(e) => setNewAttachment(e.target.value)}
                placeholder="Paste attachment URL..."
                className="h-10 border-border/50 focus:border-primary/50 transition-all"
              />
              <Button 
                onClick={handleAddAttachment} 
                size="sm"
                className="h-10 px-5 bg-primary hover:bg-primary/90 transition-all"
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
                      className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-all"
                    >
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Comments */}
          <div className="space-y-4">
            <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              <MessageSquare className="h-3.5 w-3.5 opacity-60" />
              Comments
            </Label>
            <div className="space-y-3">
              {editedTask.comments.map((comment) => (
                <div key={comment.id} className="p-4 bg-muted/20 rounded-lg border border-border/10">
                  <div className="flex items-center justify-between mb-2.5">
                    <span className="text-sm font-medium text-foreground">{comment.author}</span>
                    <span className="text-xs text-muted-foreground font-light">
                      {format(new Date(comment.createdAt), "MMM d, h:mm a")}
                    </span>
                  </div>
                  <p className="text-sm text-foreground/90 leading-relaxed">{comment.text}</p>
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <Textarea
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="Add a comment..."
                rows={3}
                className="resize-none border-border/50 focus:border-primary/50 transition-all leading-relaxed"
              />
              <Button 
                onClick={handleAddComment} 
                size="sm"
                className="h-auto px-5 bg-primary hover:bg-primary/90 transition-all"
              >
                Add
              </Button>
            </div>
          </div>

          {/* Divider */}
          <div className="relative py-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border/20"></div>
            </div>
            <div className="relative flex justify-center">
              <span className="bg-background px-4 text-xs text-muted-foreground uppercase tracking-wider">
                Document
              </span>
            </div>
          </div>

          {/* Notes / Document Editor */}
          <div className="space-y-4 pb-12">
            <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              <FileText className="h-3.5 w-3.5 opacity-60" />
              Notes
              <span className="text-[10px] normal-case opacity-60 ml-auto">(Cmd/Ctrl+D to focus)</span>
            </Label>
            <Textarea
              ref={notesRef}
              value={editedTask.notes || ""}
              onChange={handleNotesChange}
              placeholder="Write your notes, thoughts, or documentation here...

This is your freeform space to:
• Document decisions and context
• Brainstorm ideas
• Track progress
• Add meeting notes
• Whatever helps you work better"
              className="min-h-[400px] resize-none border-border/30 focus:border-primary/50 transition-all leading-relaxed text-base p-6 rounded-xl"
              style={{ 
                overflow: "hidden",
                fontFamily: "'Inter', sans-serif"
              }}
            />
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
};
