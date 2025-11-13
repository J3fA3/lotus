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
import { Badge } from "./ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Calendar, Paperclip, MessageSquare, Trash2, X } from "lucide-react";
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
    const updated = { ...editedTask, ...updates, updatedAt: new Date().toISOString() };
    setEditedTask(updated);
    onUpdate(updated);
  };

  const handleAddComment = () => {
    if (!newComment.trim()) return;

    const comment: Comment = {
      id: crypto.randomUUID(),
      text: newComment,
      author: editedTask.assignee,
      createdAt: new Date().toISOString(),
    };

    handleUpdate({ comments: [...editedTask.comments, comment] });
    setNewComment("");
  };

  const handleAddAttachment = () => {
    if (!newAttachment.trim()) return;
    handleUpdate({ attachments: [...editedTask.attachments, newAttachment] });
    setNewAttachment("");
  };

  const handleRemoveAttachment = (index: number) => {
    const updated = editedTask.attachments.filter((_, i) => i !== index);
    handleUpdate({ attachments: updated });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="sr-only">Task Details</DialogTitle>
          <div className="flex items-start justify-between gap-4">
            <Input
              value={editedTask.title}
              onChange={(e) => handleUpdate({ title: e.target.value })}
              className="text-2xl font-semibold border-0 px-0 focus-visible:ring-0"
            />
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onDelete(task.id)}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>

        <div className="space-y-6 mt-6">
          {/* Status and Value Stream */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Status</Label>
              <Select
                value={editedTask.status}
                onValueChange={(value: any) => handleUpdate({ status: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todo">To-Do</SelectItem>
                  <SelectItem value="doing">Doing</SelectItem>
                  <SelectItem value="done">Done</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Value Stream</Label>
              <Input
                value={editedTask.valueStream || ""}
                onChange={(e) => handleUpdate({ valueStream: e.target.value })}
                placeholder="e.g., Marketing, Development"
              />
            </div>
          </div>

          {/* Dates */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                Start Date
              </Label>
              <Input
                type="date"
                value={editedTask.startDate || ""}
                onChange={(e) => handleUpdate({ startDate: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                Due Date
              </Label>
              <Input
                type="date"
                value={editedTask.dueDate || ""}
                onChange={(e) => handleUpdate({ dueDate: e.target.value })}
              />
            </div>
          </div>

          {/* Assignee */}
          <div className="space-y-2">
            <Label>Assignee</Label>
            <Input
              value={editedTask.assignee}
              onChange={(e) => handleUpdate({ assignee: e.target.value })}
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label>Description</Label>
            <Textarea
              value={editedTask.description || ""}
              onChange={(e) => handleUpdate({ description: e.target.value })}
              placeholder="Add a description..."
              rows={4}
            />
          </div>

          {/* Attachments */}
          <div className="space-y-3">
            <Label className="flex items-center gap-2">
              <Paperclip className="h-4 w-4" />
              Attachments
            </Label>
            <div className="flex gap-2">
              <Input
                value={newAttachment}
                onChange={(e) => setNewAttachment(e.target.value)}
                placeholder="Add attachment URL..."
              />
              <Button onClick={handleAddAttachment} size="sm">
                Add
              </Button>
            </div>
            {editedTask.attachments.length > 0 && (
              <div className="space-y-2">
                {editedTask.attachments.map((attachment, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-2 bg-muted rounded-lg"
                  >
                    <span className="text-sm truncate">{attachment}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveAttachment(index)}
                      className="h-6 w-6"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Comments */}
          <div className="space-y-3">
            <Label className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              Comments
            </Label>
            <div className="space-y-3">
              {editedTask.comments.map((comment) => (
                <div key={comment.id} className="p-3 bg-muted rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">{comment.author}</span>
                    <span className="text-xs text-muted-foreground">
                      {format(new Date(comment.createdAt), "MMM d, h:mm a")}
                    </span>
                  </div>
                  <p className="text-sm">{comment.text}</p>
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <Textarea
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="Add a comment..."
                rows={2}
              />
              <Button onClick={handleAddComment} size="sm">
                Add
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
