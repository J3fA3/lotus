import { useState, useEffect, useRef } from "react";
import { Comment } from "@/types/task";
import { LotusIcon } from "./LotusIcon";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { User, Pencil, Trash2, Check, X } from "lucide-react";
import { format } from "date-fns";

interface CommentItemProps {
  comment: Comment;
  onEdit: (commentId: string, newText: string) => void;
  onDelete: (commentId: string) => void;
  currentUser?: string;
}

export const CommentItem = ({
  comment,
  onEdit,
  onDelete,
  currentUser,
}: CommentItemProps) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(comment.text);
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const confirmRef = useRef<HTMLDivElement>(null);

  // Lotus comments are system-generated and read-only
  const isLotusComment = comment.author === "Lotus";
  const canModify = !isLotusComment;

  // Handle escape key to cancel delete confirmation
  useEffect(() => {
    if (!isConfirmingDelete) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsConfirmingDelete(false);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isConfirmingDelete]);

  // Handle click outside to cancel delete confirmation
  useEffect(() => {
    if (!isConfirmingDelete) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (confirmRef.current && !confirmRef.current.contains(e.target as Node)) {
        setIsConfirmingDelete(false);
      }
    };

    // Delay adding listener to prevent immediate trigger
    const timer = setTimeout(() => {
      document.addEventListener("mousedown", handleClickOutside);
    }, 0);

    return () => {
      clearTimeout(timer);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isConfirmingDelete]);

  const handleSaveEdit = () => {
    const trimmedText = editText.trim();
    if (trimmedText && trimmedText !== comment.text) {
      onEdit(comment.id, trimmedText);
    }
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditText(comment.text);
    setIsEditing(false);
  };

  const handleStartEdit = () => {
    setEditText(comment.text);
    setIsEditing(true);
    setIsConfirmingDelete(false);
  };

  const handleConfirmDelete = () => {
    onDelete(comment.id);
    setIsConfirmingDelete(false);
  };

  const formattedDate = (() => {
    try {
      const date = new Date(comment.createdAt);
      return isNaN(date.getTime()) ? comment.createdAt : format(date, "MMM d");
    } catch {
      return comment.createdAt;
    }
  })();

  return (
    <div
      ref={confirmRef}
      className={`flex gap-3 group rounded-lg transition-all duration-300 ease-out ${
        isConfirmingDelete
          ? "bg-destructive/5 -mx-3 px-3 py-2 ring-1 ring-destructive/20"
          : ""
      }`}
    >
      <div
        className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center transition-all duration-300 ${
          isLotusComment
            ? "bg-gradient-to-br from-[hsl(var(--lotus-green-light))] to-[hsl(var(--lotus-green-medium))]"
            : isConfirmingDelete
            ? "bg-destructive/20"
            : "bg-primary/10"
        }`}
      >
        {isLotusComment ? (
          <LotusIcon className="text-[hsl(var(--lotus-paper))]" size={14} />
        ) : (
          <User
            className={`h-3.5 w-3.5 transition-colors duration-300 ${
              isConfirmingDelete ? "text-destructive" : "text-primary"
            }`}
          />
        )}
      </div>
      <div className="flex-1 space-y-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground">{comment.author}</span>
          <span className="text-xs text-muted-foreground">{formattedDate}</span>
          {canModify && !isEditing && !isConfirmingDelete && (
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150 ml-auto">
              <Button
                variant="ghost"
                size="icon"
                onClick={handleStartEdit}
                className="h-6 w-6 text-muted-foreground hover:text-foreground"
                title="Edit comment"
              >
                <Pencil className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsConfirmingDelete(true)}
                className="h-6 w-6 text-muted-foreground hover:text-destructive"
                title="Delete comment"
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          )}
        </div>

        {/* Delete confirmation state */}
        {isConfirmingDelete && (
          <div className="animate-in fade-in slide-in-from-top-1 duration-200">
            <div className="flex items-center gap-3 py-1">
              <span className="text-sm text-muted-foreground">
                Delete this comment?
              </span>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={handleConfirmDelete}
                  className="h-7 px-3 text-xs"
                >
                  Delete
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsConfirmingDelete(false)}
                  className="h-7 px-3 text-xs text-muted-foreground hover:text-foreground"
                >
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Edit state */}
        {isEditing && (
          <div className="space-y-2">
            <div
              onKeyDown={(e) => {
                if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                  e.preventDefault();
                  handleSaveEdit();
                }
              }}
            >
              <Textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                placeholder="Edit your comment... Press Cmd/Ctrl+Enter to save"
                className="border rounded-md min-h-[80px]"
                autoFocus={true}
              />
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                onClick={handleSaveEdit}
                disabled={!editText.trim()}
                className="h-7 px-3 text-xs"
              >
                <Check className="h-3 w-3 mr-1" />
                Save
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCancelEdit}
                className="h-7 px-3 text-xs"
              >
                <X className="h-3 w-3 mr-1" />
                Cancel
              </Button>
            </div>
          </div>
        )}

        {/* Normal display state */}
        {!isEditing && !isConfirmingDelete && (
          <div
            className="text-sm text-foreground/90 leading-relaxed prose prose-sm max-w-none"
            dangerouslySetInnerHTML={{ __html: comment.text }}
          />
        )}
      </div>
    </div>
  );
};
