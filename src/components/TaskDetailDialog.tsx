import { useState } from "react";
import { Task, Comment } from "@/types/task";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";
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
import { Calendar, Paperclip, MessageSquare, Trash2, X, User } from "lucide-react";
import { format } from "date-fns";

interface TaskDetailDialogProps {
  task: Task;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUpdate: (task: Task) => void;
  onDelete: (taskId: string) => void;
}

export const TaskDetailDialog = ({
  task,
  open,
  onOpenChange,
  onUpdate,
  onDelete,
}: TaskDetailDialogProps) => {
  const [editedTask, setEditedTask] = useState<Task>(task);
  const [newComment, setNewComment] = useState("");
  const [newAttachment, setNewAttachment] = useState("");

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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto p-0 gap-0 border-border/50">
        <DialogHeader className="px-8 pt-8 pb-6 border-b border-border/30">
          <DialogTitle className="sr-only">Task Details</DialogTitle>
          <div className="flex items-start justify-between gap-4">
            <Input
              value={editedTask.title}
              onChange={(e) => handleUpdate({ title: e.target.value })}
              className="text-2xl font-semibold border-0 px-0 focus-visible:ring-0 tracking-tight"
              placeholder="Task title"
            />
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onDelete(task.id)}
              className="text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-colors"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>

        <div className="px-8 py-6 space-y-8">
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
                <SelectTrigger className="h-10 border-border/50 focus:border-primary/50 transition-colors">
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
                className="h-10 border-border/50 focus:border-primary/50 transition-colors"
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
                className="h-10 border-border/50 focus:border-primary/50 transition-colors"
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
                className="h-10 border-border/50 focus:border-primary/50 transition-colors"
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
              className="h-10 border-border/50 focus:border-primary/50 transition-colors"
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
              rows={5}
              className="resize-none border-border/50 focus:border-primary/50 transition-colors leading-relaxed"
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
                className="h-10 border-border/50 focus:border-primary/50 transition-colors"
              />
              <Button 
                onClick={handleAddAttachment} 
                size="sm"
                className="h-10 px-5 bg-primary hover:bg-primary/90 transition-colors"
              >
                Add
              </Button>
            </div>
            {editedTask.attachments.length > 0 && (
              <div className="space-y-2">
                {editedTask.attachments.map((attachment, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-muted/50 rounded-lg border border-border/30 group hover:border-border/50 transition-colors"
                  >
                    <span className="text-sm truncate text-muted-foreground">{attachment}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveAttachment(index)}
                      className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
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
                <div key={comment.id} className="p-4 bg-muted/30 rounded-lg border border-border/20">
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
                className="resize-none border-border/50 focus:border-primary/50 transition-colors leading-relaxed"
              />
              <Button 
                onClick={handleAddComment} 
                size="sm"
                className="h-auto px-5 bg-primary hover:bg-primary/90 transition-colors"
              >
                Add
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
