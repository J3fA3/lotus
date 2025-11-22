import { useState, useEffect, useRef, useCallback } from "react";
import { Task, Comment, Document as DocumentType } from "@/types/task";
import { LotusIcon } from "./LotusIcon";
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
import { Skeleton } from "./ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Calendar, Paperclip, MessageSquare, Trash2, X, User, Maximize2, Minimize2, FileText, Expand, Upload, Link } from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";
import { DocumentUpload } from "./DocumentUpload";
import { DocumentList } from "./DocumentList";
import { uploadDocument, listDocuments } from "@/api/tasks";
import { ValueStreamCombobox } from "./ValueStreamCombobox";
import { RichTextEditor } from "./RichTextEditor";
import { TaskScheduler } from "./TaskScheduler";

interface TaskDetailSheetProps {
  task: Task;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUpdate: (task: Task) => void;
  onDelete: (taskId: string) => void;
  isExpanded?: boolean;
  onToggleExpanded?: () => void;
  onFullPage?: () => void;
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
}: TaskDetailSheetProps) => {
  const [editedTask, setEditedTask] = useState<Task>({
    ...task,
    comments: task.comments || [],
    attachments: task.attachments || [],
  });
  const [newComment, setNewComment] = useState("");
  const [newAttachment, setNewAttachment] = useState("");
  const [isExpanded, setIsExpanded] = useState(isExpandedProp);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [uploadedDocuments, setUploadedDocuments] = useState<DocumentType[]>([]);
  const [isUploadingDocument, setIsUploadingDocument] = useState(false);
  const [selectedDocumentFile, setSelectedDocumentFile] = useState<File | null>(null);
  const notesRef = useRef<HTMLTextAreaElement>(null);
  const previousTaskIdRef = useRef<string>(task.id);

  // Track last update timestamp to prevent feedback loops
  const lastExternalUpdateRef = useRef<string>("");

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
        setIsTransitioning(false);
      }, 150);

      return () => clearTimeout(timer);
    } else if (task.updatedAt && task.updatedAt !== lastExternalUpdateRef.current) {
      // Same task, but externally updated (e.g., from another component)
      // Only update if the timestamp actually changed
      lastExternalUpdateRef.current = task.updatedAt;
      setEditedTask({
        ...task,
        comments: task.comments || [],
        attachments: task.attachments || [],
      });
    }
    // If same task with same timestamp, don't update (prevents feedback loop)
  }, [task.id, task.updatedAt]);

  // Sync local isExpanded with parent prop
  useEffect(() => {
    setIsExpanded(isExpandedProp);
  }, [isExpandedProp]);

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
        if (onToggleExpanded) {
          onToggleExpanded();
        } else {
          setIsExpanded(!isExpanded);
        }
        toast.success(isExpanded ? "Peek mode" : "Expanded view");
        return;
      }

      // Cmd/Ctrl + Shift + F for full page
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "F") {
        e.preventDefault();
        if (onFullPage) {
          onFullPage();
          toast.success("Full page view");
        }
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
  }, [open, isExpanded, onOpenChange, onToggleExpanded, onFullPage]);

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

  // Document handlers
  const loadTaskDocuments = async () => {
    try {
      const response = await listDocuments("tasks", task.id);
      setUploadedDocuments(response.documents);
    } catch (error) {
      console.error("Failed to load documents:", error);
    }
  };

  const handleDocumentUpload = async () => {
    if (!selectedDocumentFile) return;

    setIsUploadingDocument(true);
    try {
      await uploadDocument(selectedDocumentFile, "tasks", task.id);
      toast.success(`Uploaded ${selectedDocumentFile.name}`);
      setSelectedDocumentFile(null);
      await loadTaskDocuments();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to upload document");
    } finally {
      setIsUploadingDocument(false);
    }
  };

  const handleDocumentDeleted = async (documentId: string) => {
    await loadTaskDocuments();
  };

  // Load documents when task changes
  useEffect(() => {
    if (open && task.id) {
      loadTaskDocuments();
    }
  }, [open, task.id]);


  return (
    <Sheet open={open} onOpenChange={onOpenChange} modal={false}>
      <SheetContent
        side="right"
        className={`p-0 border-l border-border/30 transition-[width,max-width] duration-300 ease-out task-sheet-scroll overflow-y-auto shadow-2xl ${
          isExpanded ? "w-full sm:max-w-[900px]" : "w-full sm:max-w-[600px]"
        }`}
        onOpenAutoFocus={(e) => e.preventDefault()}
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
                    onFullPage();
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
              onClick={() => onDelete(task.id)}
              className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-all duration-200 hover:scale-105 active:scale-95"
              title="Delete task"
            >
              <Trash2 className="h-4 w-4 transition-transform duration-200 hover:rotate-12" />
            </Button>
          </div>
        </SheetHeader>

        {/* Content */}
        <div className="px-8 py-6 space-y-8">
          {isTransitioning ? (
            /* Skeleton Loading State */
            <div className="space-y-8 animate-in fade-in duration-150">
              {/* Title Skeleton */}
              <div className="space-y-3">
                <Skeleton className={`${isExpanded ? "h-12" : "h-10"} w-3/4 transition-all duration-300`} />
              </div>

              {/* Properties Grid Skeleton */}
              <div className={`grid gap-6 ${isExpanded ? "grid-cols-3" : "grid-cols-2"}`}>
                <div className="space-y-3">
                  <Skeleton className="h-3 w-16" />
                  <Skeleton className="h-10 w-full" />
                </div>
                <div className="space-y-3">
                  <Skeleton className="h-3 w-24" />
                  <Skeleton className="h-10 w-full" />
                </div>
                {isExpanded && (
                  <div className="space-y-3">
                    <Skeleton className="h-3 w-20" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                )}
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
              <div>
                <RichTextEditor
                  content={editedTask.title}
                  onChange={(html) => handleUpdate({ title: html })}
                  placeholder="Task title - Type / for Word Art styles!"
                  variant="title"
                  className={`transition-[font-size] duration-200 ease-out ${
                    isExpanded ? "text-4xl" : "text-3xl"
                  }`}
                  autoFocus={false}
                />
              </div>

          {/* Properties Grid */}
          <div className={`grid gap-6 transition-[grid-template-columns] duration-200 ease-out ${
            isExpanded ? "grid-cols-3" : "grid-cols-2"
          }`}>
            <div className="space-y-3">
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Status
              </Label>
              <Select
                value={editedTask.status}
                onValueChange={(value) => handleUpdate({ status: value as Task["status"] })}
              >
                <SelectTrigger className="h-10 border-border/50 focus:border-primary/50 transition-[border-color] duration-150 hover:border-primary/30">
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
              <ValueStreamCombobox
                value={editedTask.valueStream || ""}
                onChange={(value) => handleUpdate({ valueStream: value })}
                placeholder="Select or create value stream..."
                className="w-full"
              />
            </div>

            {isExpanded && (
              <div className="space-y-3 animate-in fade-in slide-in-from-right-3 duration-200">
                <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  <User className="h-3.5 w-3.5 opacity-60" />
                  Assignee
                </Label>
                <Input
                  value={editedTask.assignee}
                  onChange={(e) => handleUpdate({ assignee: e.target.value })}
                  className="h-10 border-border/50 focus:border-primary/50 transition-[border-color] duration-150 hover:border-primary/30"
                />
              </div>
            )}
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
                className="h-10 border-border/50 focus:border-primary/50 transition-[border-color] duration-150 hover:border-primary/30"
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
                className="h-10 border-border/50 focus:border-primary/50 transition-[border-color] duration-150 hover:border-primary/30"
              />
            </div>
          </div>

          {/* Schedule */}
          <TaskScheduler
            taskId={editedTask.id}
            taskTitle={editedTask.title}
            comments={editedTask.comments}
            onScheduled={(action) => {
              // Only show toast for approvals, not cancellations (cancellation already shows its own toast)
              if (action === 'approved') {
                toast.success("Time block added to calendar");
              }
              // Refresh task to get updated comments
              // The parent component should handle this via onUpdate
            }}
          />

          {/* Assignee - only show in peek mode since it's in the grid for expanded */}
          {!isExpanded && (
            <div className="space-y-3">
              <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                <User className="h-3.5 w-3.5 opacity-60" />
                Assignee
              </Label>
              <Input
                value={editedTask.assignee}
                onChange={(e) => handleUpdate({ assignee: e.target.value })}
                className="h-10 border-border/50 focus:border-primary/50 transition-[border-color] duration-150 hover:border-primary/30"
              />
            </div>
          )}

          {/* Description */}
          <div className="space-y-3">
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Description
            </Label>
            <RichTextEditor
              content={editedTask.description || ""}
              onChange={(html) => handleUpdate({ description: html })}
              placeholder="Add a detailed description... Type / for commands, * for bullets"
              variant="minimal"
            />
          </div>

          {/* Attachments & Documents */}
          <div className="space-y-4">
            <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              <Paperclip className="h-3.5 w-3.5 opacity-60" />
              Attachments & Documents
            </Label>

            <Tabs defaultValue="documents" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="documents" className="text-xs gap-1.5">
                  <Upload className="h-3 w-3" />
                  Upload Files
                </TabsTrigger>
                <TabsTrigger value="links" className="text-xs gap-1.5">
                  <Link className="h-3 w-3" />
                  Add Links
                </TabsTrigger>
              </TabsList>

              {/* Document Upload Tab */}
              <TabsContent value="documents" className="space-y-3 mt-3">
                <DocumentUpload
                  onFileSelect={setSelectedDocumentFile}
                  onFileRemove={() => setSelectedDocumentFile(null)}
                  selectedFile={selectedDocumentFile}
                  disabled={isUploadingDocument}
                  showFileInfo={true}
                />

                {selectedDocumentFile && (
                  <Button
                    onClick={handleDocumentUpload}
                    disabled={isUploadingDocument}
                    className="w-full"
                    size="sm"
                  >
                    {isUploadingDocument ? "Uploading..." : "Upload Document"}
                  </Button>
                )}

                {uploadedDocuments.length > 0 && (
                  <div className="pt-2">
                    <p className="text-xs text-muted-foreground mb-2">Attached Documents</p>
                    <DocumentList
                      documents={uploadedDocuments}
                      onDocumentDeleted={handleDocumentDeleted}
                      showDelete={true}
                      compact={true}
                    />
                  </div>
                )}
              </TabsContent>

              {/* URL Links Tab */}
              <TabsContent value="links" className="space-y-3 mt-3">
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
              </TabsContent>
            </Tabs>
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
                  <div key={comment.id} className="flex gap-3">
                    <div
                      className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${
                        comment.author === "Lotus"
                          ? "bg-gradient-to-br from-[hsl(var(--lotus-green-light))] to-[hsl(var(--lotus-green-medium))]"
                          : "bg-primary/10"
                      }`}
                    >
                      {comment.author === "Lotus" ? (
                        <LotusIcon className="text-[hsl(var(--lotus-paper))]" size={14} />
                      ) : (
                        <User className="h-3.5 w-3.5 text-primary" />
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
              <div className="flex-shrink-0 w-7 h-7 rounded-full bg-muted flex items-center justify-center mt-1">
                <User className="h-3.5 w-3.5 text-muted-foreground" />
              </div>
              <div className="flex-1">
                <RichTextEditor
                  content={newComment}
                  onChange={(html) => setNewComment(html)}
                  placeholder="Add a comment... Type / for commands, * for bullets"
                  variant="minimal"
                  className="border-0 border-b rounded-none"
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

          {/* Notes - No Header Divider */}
          <div className="space-y-3 pb-12">
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Notes
            </Label>
            <RichTextEditor
              content={editedTask.notes || ""}
              onChange={(html) => handleUpdate({ notes: html })}
              placeholder="Write your notes, thoughts, or documentation here... Type / for commands, * for bullets, create tables and more!"
              variant="full"
            />
            <span className="text-xs text-muted-foreground">Cmd/Ctrl+D to focus notes • Full formatting available: headings, tables, code blocks, and Word Art!</span>
          </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
};
