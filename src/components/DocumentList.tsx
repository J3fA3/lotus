/**
 * @fileoverview Document List Component
 *
 * Displays a list or grid of attached documents with download and delete actions.
 * Used for displaying uploaded documents in various contexts. For task
 * attachments that combine links and files, see UnifiedAttachments.
 *
 * ## Components
 *
 * - `DocumentList` - Vertical list layout with file details
 * - `DocumentGrid` - 2-column grid layout for compact display
 *
 * ## Features
 *
 * - File type icons and metadata display
 * - Download functionality via API
 * - Delete with confirmation dialog
 * - Compact mode for space-constrained layouts
 * - Empty state handling
 *
 * @module components/DocumentList
 */
import { FileText, Download, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  downloadDocument,
  deleteDocument as apiDeleteDocument,
  getFileTypeName,
  formatFileSize,
} from "@/api/tasks";
import { Document } from "@/types/task";
import { toast } from "sonner";

interface DocumentListProps {
  documents: Document[];
  onDocumentDeleted?: (documentId: string) => void;
  showDelete?: boolean;
  className?: string;
  compact?: boolean;
}

export function DocumentList({
  documents,
  onDocumentDeleted,
  showDelete = true,
  className,
  compact = false,
}: DocumentListProps) {
  const handleDownload = async (doc: Document) => {
    try {
      await downloadDocument(doc.id, doc.original_filename);
      toast.success(`Downloaded ${doc.original_filename}`);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to download document"
      );
    }
  };

  const handleDelete = async (doc: Document) => {
    if (!confirm(`Delete "${doc.original_filename}"?`)) {
      return;
    }

    try {
      await apiDeleteDocument(doc.id);
      toast.success("Document deleted");
      if (onDocumentDeleted) {
        onDocumentDeleted(doc.id);
      }
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to delete document"
      );
    }
  };

  if (documents.length === 0) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center p-8 rounded-lg border border-dashed border-muted-foreground/25",
          className
        )}
      >
        <FileText className="w-12 h-12 text-muted-foreground/50 mb-2" />
        <p className="text-sm text-muted-foreground">No documents attached</p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-2", className)}>
      {documents.map((doc) => (
        <div
          key={doc.id}
          className={cn(
            "group flex items-center gap-3 p-3 rounded-lg border border-border bg-card",
            "transition-all duration-200 hover:shadow-md hover:border-primary/30",
            compact && "p-2"
          )}
        >
          {/* Icon */}
          <div className="flex-shrink-0">
            <FileText
              className={cn(
                "text-primary",
                compact ? "w-6 h-6" : "w-8 h-8"
              )}
            />
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <p
              className={cn(
                "font-medium text-foreground truncate",
                compact ? "text-xs" : "text-sm"
              )}
            >
              {doc.original_filename}
            </p>
            <div
              className={cn(
                "flex items-center gap-2 mt-0.5 text-muted-foreground",
                compact ? "text-[10px]" : "text-xs"
              )}
            >
              <span>{getFileTypeName(doc.original_filename)}</span>
              <span>•</span>
              <span>{formatFileSize(doc.size_bytes)}</span>
              {doc.page_count && (
                <>
                  <span>•</span>
                  <span>{doc.page_count} pages</span>
                </>
              )}
            </div>
            {doc.text_preview && !compact && (
              <p className="text-xs text-muted-foreground mt-1 line-clamp-1 italic">
                "{doc.text_preview.substring(0, 100)}..."
              </p>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1 flex-shrink-0">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleDownload(doc)}
              className={cn(
                "hover:bg-primary/10 hover:text-primary",
                compact ? "h-7 w-7 p-0" : "h-8 w-8 p-0"
              )}
              title="Download"
            >
              <Download className={compact ? "w-3.5 h-3.5" : "w-4 h-4"} />
            </Button>

            {showDelete && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleDelete(doc)}
                className={cn(
                  "hover:bg-destructive/10 hover:text-destructive",
                  compact ? "h-7 w-7 p-0" : "h-8 w-8 p-0"
                )}
                title="Delete"
              >
                <Trash2 className={compact ? "w-3.5 h-3.5" : "w-4 h-4"} />
              </Button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

interface DocumentGridProps {
  documents: Document[];
  onDocumentDeleted?: (documentId: string) => void;
  showDelete?: boolean;
  className?: string;
}

export function DocumentGrid({
  documents,
  onDocumentDeleted,
  showDelete = true,
  className,
}: DocumentGridProps) {
  const handleDownload = async (doc: Document) => {
    try {
      await downloadDocument(doc.id, doc.original_filename);
      toast.success(`Downloaded ${doc.original_filename}`);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to download document"
      );
    }
  };

  const handleDelete = async (doc: Document) => {
    if (!confirm(`Delete "${doc.original_filename}"?`)) {
      return;
    }

    try {
      await apiDeleteDocument(doc.id);
      toast.success("Document deleted");
      if (onDocumentDeleted) {
        onDocumentDeleted(doc.id);
      }
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to delete document"
      );
    }
  };

  if (documents.length === 0) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center p-8 rounded-lg border border-dashed border-muted-foreground/25",
          className
        )}
      >
        <FileText className="w-12 h-12 text-muted-foreground/50 mb-2" />
        <p className="text-sm text-muted-foreground">No documents attached</p>
      </div>
    );
  }

  return (
    <div className={cn("grid grid-cols-2 gap-3", className)}>
      {documents.map((doc) => (
        <div
          key={doc.id}
          className="group relative flex flex-col items-center p-4 rounded-lg border border-border bg-card transition-all duration-200 hover:shadow-md hover:border-primary/30 cursor-pointer"
          onClick={() => handleDownload(doc)}
        >
          {/* Icon */}
          <FileText className="w-12 h-12 text-primary mb-2" />

          {/* Filename */}
          <p className="text-xs font-medium text-foreground text-center truncate w-full px-2">
            {doc.original_filename}
          </p>

          {/* Type */}
          <p className="text-[10px] text-muted-foreground mt-1">
            {getFileTypeName(doc.original_filename)}
          </p>

          {/* Size */}
          <p className="text-[10px] text-muted-foreground">
            {formatFileSize(doc.size_bytes)}
          </p>

          {/* Delete Button */}
          {showDelete && (
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                handleDelete(doc);
              }}
              className="absolute top-2 right-2 h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-destructive/10 hover:text-destructive"
              title="Delete"
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          )}
        </div>
      ))}
    </div>
  );
}
