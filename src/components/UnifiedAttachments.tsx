/**
 * @fileoverview Unified Attachments Component
 *
 * A cohesive, best-in-class interface for managing both URL links and file
 * attachments in a single unified experience. This replaces the previous
 * tabbed approach that separated "Upload Files" and "Add Links" into
 * different views.
 *
 * ## Design Philosophy
 *
 * The component follows a "progressive disclosure" pattern:
 * 1. Compact input row at top for quick URL pasting or file selection
 * 2. Unified list showing all attachments (links + files) with consistent styling
 * 3. Subtle drop zone at bottom for drag-and-drop convenience
 *
 * ## Key Features
 *
 * - **Enter-to-submit**: Press Enter to add URLs without clicking buttons
 * - **Clickable URLs**: Links open in new tabs with visual feedback
 * - **Inline editing**: Edit URLs without modals or page navigation
 * - **Smart URL display**: Shows domain prominently, truncates paths gracefully
 * - **Type-aware icons**: Different icons for PDF, Excel, Word, etc.
 * - **Auto-normalization**: Adds https:// to URLs if missing
 * - **Drag-and-drop**: Subtle 48px drop zone expands on drag hover
 *
 * ## Usage
 *
 * ```tsx
 * <UnifiedAttachments
 *   attachments={task.attachments}
 *   onAddAttachment={(url) => handleAdd(url)}
 *   onRemoveAttachment={(index) => handleRemove(index)}
 *   onEditAttachment={(index, newUrl) => handleEdit(index, newUrl)}
 *   documents={uploadedDocuments}
 *   onFileSelect={(file) => handleUpload(file)}
 *   onDocumentDeleted={(docId) => handleDocDeleted(docId)}
 *   isUploading={isUploading}
 * />
 * ```
 *
 * @module components/UnifiedAttachments
 */

import { useState, useRef, useCallback } from "react";
import {
  Link2,
  FileText,
  Download,
  Trash2,
  Pencil,
  Check,
  X,
  Plus,
  ExternalLink,
  File,
  FileSpreadsheet,
  FileType,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  downloadDocument,
  deleteDocument as apiDeleteDocument,
  formatFileSize,
  SUPPORTED_DOCUMENT_TYPES,
  isSupportedDocumentType,
} from "@/api/tasks";
import { Document } from "@/types/task";
import { toast } from "sonner";

// ============================================================================
// Types
// ============================================================================

/**
 * Props for the UnifiedAttachments component.
 */
interface UnifiedAttachmentsProps {
  /** Array of URL strings attached to the task */
  attachments: string[];
  /** Callback when a new URL is added */
  onAddAttachment: (url: string) => void;
  /** Callback when a URL is removed by index */
  onRemoveAttachment: (index: number) => void;
  /** Callback when a URL is edited (index + new value) */
  onEditAttachment: (index: number, newUrl: string) => void;
  /** Array of uploaded Document objects from the API */
  documents: Document[];
  /** Callback when a file is selected for upload */
  onFileSelect: (file: File) => void;
  /** Callback when a document is deleted */
  onDocumentDeleted: (documentId: string) => void;
  /** Whether a file upload is currently in progress */
  isUploading?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// ============================================================================
// Constants
// ============================================================================

/** Maximum file size in bytes (50MB) */
const MAX_FILE_SIZE = 50 * 1024 * 1024;

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Returns an appropriate icon component based on file extension.
 *
 * @param filename - The filename to get an icon for
 * @returns A Lucide icon component
 */
function getFileIcon(filename: string): JSX.Element {
  const ext = filename.split(".").pop()?.toLowerCase();
  switch (ext) {
    case "pdf":
      return <FileText className="w-4 h-4" />;
    case "xlsx":
    case "xls":
    case "csv":
      return <FileSpreadsheet className="w-4 h-4" />;
    case "doc":
    case "docx":
      return <FileType className="w-4 h-4" />;
    default:
      return <File className="w-4 h-4" />;
  }
}

/**
 * Formats a URL for display by extracting the domain and truncating the path.
 *
 * @param url - The URL string to format
 * @returns Object with `domain` and `path` strings
 *
 * @example
 * formatUrlForDisplay("https://docs.google.com/document/d/abc123/edit")
 * // => { domain: "docs.google.com", path: "/document/d/abc..." }
 */
function formatUrlForDisplay(url: string): { domain: string; path: string } {
  try {
    const parsed = new URL(url);
    const domain = parsed.hostname.replace("www.", "");
    const path = parsed.pathname + parsed.search;
    return {
      domain,
      path: path.length > 30 ? path.slice(0, 27) + "..." : path,
    };
  } catch {
    // Not a valid URL, just truncate the whole thing
    return {
      domain: url.length > 40 ? url.slice(0, 37) + "..." : url,
      path: "",
    };
  }
}

/**
 * Validates whether a string is a valid URL (or can become one with https://).
 *
 * @param string - The string to validate
 * @returns True if the string is a valid URL
 */
function isValidUrl(string: string): boolean {
  try {
    new URL(string);
    return true;
  } catch {
    // Try adding https:// prefix for convenience
    try {
      new URL("https://" + string);
      return string.includes(".");
    } catch {
      return false;
    }
  }
}

/**
 * Normalizes a URL by adding https:// if no protocol is present.
 *
 * @param url - The URL to normalize
 * @returns The normalized URL with https:// prefix
 */
function normalizeUrl(url: string): string {
  const trimmed = url.trim();
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed;
  }
  return "https://" + trimmed;
}

// ============================================================================
// Component
// ============================================================================

/**
 * UnifiedAttachments - A cohesive interface for managing links and files.
 *
 * Renders a compact input row for adding URLs, a unified list of all
 * attachments (both URL links and uploaded documents), and a subtle
 * drag-and-drop zone for file uploads.
 */
export function UnifiedAttachments({
  attachments,
  onAddAttachment,
  onRemoveAttachment,
  onEditAttachment,
  documents,
  onFileSelect,
  onDocumentDeleted,
  isUploading = false,
  className,
}: UnifiedAttachmentsProps) {
  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  const [newUrl, setNewUrl] = useState("");
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editingValue, setEditingValue] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // Refs
  // ---------------------------------------------------------------------------

  const fileInputRef = useRef<HTMLInputElement>(null);
  const editInputRef = useRef<HTMLInputElement>(null);

  // ---------------------------------------------------------------------------
  // URL Handlers
  // ---------------------------------------------------------------------------

  /** Validates and adds the URL from the input field */
  const handleAddUrl = useCallback(() => {
    const trimmed = newUrl.trim();
    if (!trimmed) return;

    if (!isValidUrl(trimmed)) {
      setError("Please enter a valid URL");
      return;
    }

    setError(null);
    onAddAttachment(normalizeUrl(trimmed));
    setNewUrl("");
  }, [newUrl, onAddAttachment]);

  /** Handles Enter key to submit URL */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleAddUrl();
      }
    },
    [handleAddUrl]
  );

  /** Enters edit mode for a URL at the given index */
  const startEditing = useCallback((index: number, currentUrl: string) => {
    setEditingIndex(index);
    setEditingValue(currentUrl);
    setTimeout(() => editInputRef.current?.focus(), 0);
  }, []);

  /** Saves the edited URL and exits edit mode */
  const saveEdit = useCallback(() => {
    if (editingIndex === null) return;

    const trimmed = editingValue.trim();
    if (!trimmed) {
      setEditingIndex(null);
      return;
    }

    if (!isValidUrl(trimmed)) {
      toast.error("Please enter a valid URL");
      return;
    }

    onEditAttachment(editingIndex, normalizeUrl(trimmed));
    setEditingIndex(null);
    setEditingValue("");
  }, [editingIndex, editingValue, onEditAttachment]);

  /** Cancels edit mode without saving */
  const cancelEdit = useCallback(() => {
    setEditingIndex(null);
    setEditingValue("");
  }, []);

  /** Handles keyboard shortcuts in edit mode (Enter to save, Escape to cancel) */
  const handleEditKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        saveEdit();
      } else if (e.key === "Escape") {
        cancelEdit();
      }
    },
    [saveEdit, cancelEdit]
  );

  // ---------------------------------------------------------------------------
  // File Handlers
  // ---------------------------------------------------------------------------

  /** Validates a file against size and type constraints */
  const validateFile = useCallback((file: File): string | null => {
    if (file.size > MAX_FILE_SIZE) {
      return `File too large. Maximum size is 50MB`;
    }
    if (!isSupportedDocumentType(file.name)) {
      return `Unsupported file type. Supported: PDF, Word, Excel, Markdown, Text`;
    }
    return null;
  }, []);

  /** Validates and passes the file to the parent for upload */
  const handleFileSelection = useCallback(
    (file: File) => {
      setError(null);
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }
      onFileSelect(file);
    },
    [validateFile, onFileSelect]
  );

  // ---------------------------------------------------------------------------
  // Drag & Drop Handlers
  // ---------------------------------------------------------------------------

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        handleFileSelection(files[0]);
      }
    },
    [handleFileSelection]
  );

  /** Handles file selection from the hidden input element */
  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        handleFileSelection(files[0]);
      }
      // Reset input so the same file can be selected again
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    [handleFileSelection]
  );

  // ---------------------------------------------------------------------------
  // Document Handlers
  // ---------------------------------------------------------------------------

  /** Downloads a document via the API */
  const handleDownload = useCallback(async (doc: Document) => {
    try {
      await downloadDocument(doc.id, doc.original_filename);
      toast.success(`Downloaded ${doc.original_filename}`);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to download document"
      );
    }
  }, []);

  /** Deletes a document after confirmation */
  const handleDeleteDocument = useCallback(
    async (doc: Document) => {
      if (!confirm(`Delete "${doc.original_filename}"?`)) {
        return;
      }
      try {
        await apiDeleteDocument(doc.id);
        toast.success("Document deleted");
        onDocumentDeleted(doc.id);
      } catch (error) {
        toast.error(
          error instanceof Error ? error.message : "Failed to delete document"
        );
      }
    },
    [onDocumentDeleted]
  );

  // ---------------------------------------------------------------------------
  // Derived State
  // ---------------------------------------------------------------------------

  const hasItems = attachments.length > 0 || documents.length > 0;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className={cn("space-y-3", className)}>
      {/* ===== Input Row: URL input + Add button + Upload button ===== */}
      <div className="flex gap-2 items-center">
        <div className="relative flex-1">
          <Input
            value={newUrl}
            onChange={(e) => {
              setNewUrl(e.target.value);
              setError(null);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Paste a link..."
            className={cn(
              "h-9 pl-9 pr-3 text-sm border-border/50 focus:border-primary/50 transition-all",
              "placeholder:text-muted-foreground/60"
            )}
          />
          <Link2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/50" />
        </div>
        <Button
          onClick={handleAddUrl}
          size="sm"
          variant="ghost"
          className="h-9 px-3 hover:bg-primary/10 hover:text-primary"
          disabled={!newUrl.trim()}
        >
          <Plus className="w-4 h-4" />
        </Button>
        <div className="w-px h-5 bg-border/50" />
        <Button
          onClick={() => fileInputRef.current?.click()}
          size="sm"
          variant="ghost"
          className="h-9 px-3 hover:bg-primary/10 hover:text-primary"
          disabled={isUploading}
          title="Upload file"
        >
          <Upload className="w-4 h-4" />
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept={SUPPORTED_DOCUMENT_TYPES.join(",")}
          onChange={handleFileInput}
          className="hidden"
        />
      </div>

      {/* ===== Validation Error ===== */}
      {error && (
        <p className="text-xs text-destructive px-1">{error}</p>
      )}

      {/* ===== Unified Attachments List ===== */}
      {hasItems && (
        <div className="space-y-1.5">
          {/* ----- URL Links ----- */}
          {attachments.map((url, index) => {
            const { domain, path } = formatUrlForDisplay(url);
            const isEditing = editingIndex === index;

            return (
              <div
                key={`link-${index}`}
                className={cn(
                  "group flex items-center gap-2 px-3 py-2 rounded-lg",
                  "bg-muted/30 border border-transparent",
                  "hover:border-border/40 hover:bg-muted/50 transition-all duration-150"
                )}
              >
                <Link2 className="w-4 h-4 text-primary/70 flex-shrink-0" />

                {isEditing ? (
                  // Edit mode
                  <div className="flex-1 flex items-center gap-2">
                    <Input
                      ref={editInputRef}
                      value={editingValue}
                      onChange={(e) => setEditingValue(e.target.value)}
                      onKeyDown={handleEditKeyDown}
                      className="h-7 text-sm flex-1"
                      autoFocus
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={saveEdit}
                      className="h-7 w-7 p-0 hover:bg-primary/10 hover:text-primary"
                    >
                      <Check className="w-3.5 h-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={cancelEdit}
                      className="h-7 w-7 p-0 hover:bg-muted"
                    >
                      <X className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                ) : (
                  // Display mode
                  <>
                    <a
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 flex items-center gap-1.5 min-w-0 group/link"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <span className="text-sm font-medium text-foreground/90 truncate hover:text-primary transition-colors">
                        {domain}
                      </span>
                      {path && path !== "/" && (
                        <span className="text-xs text-muted-foreground truncate hidden sm:inline">
                          {path}
                        </span>
                      )}
                      <ExternalLink className="w-3 h-3 text-muted-foreground/50 opacity-0 group-hover/link:opacity-100 transition-opacity flex-shrink-0" />
                    </a>

                    {/* Actions */}
                    <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => startEditing(index, url)}
                        className="h-7 w-7 p-0 hover:bg-primary/10 hover:text-primary"
                        title="Edit link"
                      >
                        <Pencil className="w-3 h-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onRemoveAttachment(index)}
                        className="h-7 w-7 p-0 hover:bg-destructive/10 hover:text-destructive"
                        title="Remove link"
                      >
                        <X className="w-3 h-3" />
                      </Button>
                    </div>
                  </>
                )}
              </div>
            );
          })}

          {/* ----- Uploaded Documents ----- */}
          {documents.map((doc) => (
            <div
              key={`doc-${doc.id}`}
              className={cn(
                "group flex items-center gap-2 px-3 py-2 rounded-lg",
                "bg-muted/30 border border-transparent",
                "hover:border-border/40 hover:bg-muted/50 transition-all duration-150"
              )}
            >
              <span className="text-primary/70 flex-shrink-0">
                {getFileIcon(doc.original_filename)}
              </span>

              <div className="flex-1 min-w-0 flex items-center gap-2">
                <span className="text-sm font-medium text-foreground/90 truncate">
                  {doc.original_filename}
                </span>
                <span className="text-xs text-muted-foreground flex-shrink-0 hidden sm:inline">
                  {formatFileSize(doc.size_bytes)}
                </span>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDownload(doc)}
                  className="h-7 w-7 p-0 hover:bg-primary/10 hover:text-primary"
                  title="Download"
                >
                  <Download className="w-3 h-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDeleteDocument(doc)}
                  className="h-7 w-7 p-0 hover:bg-destructive/10 hover:text-destructive"
                  title="Delete"
                >
                  <Trash2 className="w-3 h-3" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ===== Compact Drop Zone ===== */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          "flex items-center justify-center gap-2 h-12 rounded-lg cursor-pointer",
          "border border-dashed transition-all duration-200",
          isDragging
            ? "border-primary bg-primary/5 scale-[1.01]"
            : "border-border/40 hover:border-primary/40 hover:bg-muted/30",
          isUploading && "opacity-50 cursor-not-allowed"
        )}
      >
        <Upload
          className={cn(
            "w-4 h-4 transition-colors",
            isDragging ? "text-primary" : "text-muted-foreground/50"
          )}
        />
        <span
          className={cn(
            "text-xs transition-colors",
            isDragging ? "text-primary" : "text-muted-foreground/60"
          )}
        >
          {isUploading
            ? "Uploading..."
            : isDragging
            ? "Drop to upload"
            : "Drop files here or click to upload"}
        </span>
      </div>
    </div>
  );
}

