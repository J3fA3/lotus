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
import { useRegisterShortcut } from "@/contexts/ShortcutContext";
import { DeleteTaskDialog } from "./DeleteTaskDialog";

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
  const [newAttachment, setNewAttachment] = useState("");
  const [isExpanded, setIsExpanded] = useState(isExpandedProp);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isExiting, setIsExiting] = useState(false);
  const [uploadedDocuments, setUploadedDocuments] = useState<DocumentType[]>([]);
  const [isUploadingDocument, setIsUploadingDocument] = useState(false);
  const [selectedDocumentFile, setSelectedDocumentFile] = useState<File | null>(null);
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
  const previousTaskIdRef = useRef<string>(task.id);
  const [currentSectionIndex, setCurrentSectionIndex] = useState(0);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  // Track last update timestamp to prevent feedback loops
  const lastExternalUpdateRef = useRef<string>("");

  // Track in-flight local updates to prevent race conditions
  const localUpdateInProgressRef = useRef(false);
  const localUpdateTimestampRef = useRef<string>("");
  const localUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Track the latest comment text to avoid stale state issues
  const latestCommentTextRef = useRef<string>("");

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

      // For TaskScheduler: find the "Find the best time" button
      if (index === 5) { // scheduleRef is at index 5
        // Try to find button with text containing "Find" or "best time"
        const buttons = element.querySelectorAll('button');
        for (const btn of buttons) {
          if (btn.textContent?.includes('Find') || btn.textContent?.includes('best time')) {
            btn.focus();
            return;
          }
        }
        // Fallback: focus first button if found
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

  useRegisterShortcut('delete_task', () => {
    if (open) {
      setIsDeleteDialogOpen(true);
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
    // Use the latest comment text from ref to avoid stale state issues
    const commentText = latestCommentTextRef.current || newComment;
    const trimmedComment = commentText.trim();
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
    latestCommentTextRef.current = "";
  }, [newComment, editedTask.assignee, editedTask.comments, handleUpdate]);

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
        className={`p-0 border-l border-border/30 transition-[width,max-width,opacity,transform] duration-[400ms] ease-butter task-sheet-scroll overflow-y-auto shadow-2xl will-change-[width,max-width,opacity,transform] ${
          isExpanded ? "w-full sm:max-w-[900px]" : "w-full sm:max-w-[600px]"
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
              <div ref={titleRef}>
                <RichTextEditor
                  content={editedTask.title}
                  onChange={(html) => handleUpdate({ title: html })}
                  placeholder="Task title - Type / for Word Art styles!"
                  variant="title"
                  className="text-3xl transition-all duration-[400ms] ease-butter"
                  autoFocus={false}
                />
              </div>

          {/* Properties Grid */}
          <div className={`grid gap-6 transition-[grid-template-columns] duration-[400ms] ease-butter will-change-[grid-template-columns] ${
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

            {isExpanded && (
              <div className="space-y-3 animate-in fade-in slide-in-from-right-3 duration-[400ms] ease-butter">
                <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  <User className="h-3.5 w-3.5 opacity-60" />
                  Assignee
                </Label>
                <Input
                  ref={assigneeRef}
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

          {/* Schedule */}
          <div ref={scheduleRef}>
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
          </div>

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
            <div ref={descriptionRef}>
              <RichTextEditor
                content={editedTask.description || ""}
                onChange={(html) => handleUpdate({ description: html })}
                placeholder="Add a detailed description... Type / for commands, * for bullets"
                variant="minimal"
              />
            </div>
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
                <RichTextEditor
                  content={newComment}
                  onChange={(html) => {
                    setNewComment(html);
                    // Also update ref to ensure we always have the latest value
                    latestCommentTextRef.current = html;
                  }}
                  placeholder="Add a comment... Type / for commands, * for bullets. Press Cmd/Ctrl+Enter to post"
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
