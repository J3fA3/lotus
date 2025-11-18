/**
 * Reusable Document Upload Component
 *
 * Supports drag-and-drop and click-to-upload for multiple document types
 * (PDF, Word, Markdown, Text, Excel)
 */
import { useState, useRef, useCallback } from "react";
import { FileText, Upload, X, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  SUPPORTED_DOCUMENT_TYPES,
  isSupportedDocumentType,
  getFileTypeName,
  formatFileSize,
} from "@/api/tasks";

interface DocumentUploadProps {
  onFileSelect: (file: File) => void;
  onFileRemove?: () => void;
  maxSizeBytes?: number;
  acceptedTypes?: string[];
  className?: string;
  selectedFile?: File | null;
  disabled?: boolean;
  showFileInfo?: boolean;
}

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

export function DocumentUpload({
  onFileSelect,
  onFileRemove,
  maxSizeBytes = MAX_FILE_SIZE,
  acceptedTypes,
  className,
  selectedFile,
  disabled = false,
  showFileInfo = true,
}: DocumentUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const allowedTypes = acceptedTypes || SUPPORTED_DOCUMENT_TYPES.map((t) => t);

  const validateFile = useCallback(
    (file: File): string | null => {
      // Check file size
      if (file.size > maxSizeBytes) {
        const maxMB = (maxSizeBytes / (1024 * 1024)).toFixed(1);
        return `File too large. Maximum size is ${maxMB}MB`;
      }

      // Check file type
      if (!isSupportedDocumentType(file.name)) {
        return `Unsupported file type. Supported: ${allowedTypes.join(", ")}`;
      }

      return null;
    },
    [maxSizeBytes, allowedTypes]
  );

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

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) {
        setIsDragging(true);
      }
    },
    [disabled]
  );

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

      if (disabled) return;

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        handleFileSelection(files[0]);
      }
    },
    [disabled, handleFileSelection]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        handleFileSelection(files[0]);
      }
    },
    [handleFileSelection]
  );

  const handleClick = useCallback(() => {
    if (!disabled) {
      fileInputRef.current?.click();
    }
  }, [disabled]);

  const handleRemove = useCallback(() => {
    setError(null);
    if (onFileRemove) {
      onFileRemove();
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, [onFileRemove]);

  // Build accept attribute for input
  const acceptAttribute = allowedTypes.join(",");

  return (
    <div className={cn("space-y-2", className)}>
      {/* Drop Zone */}
      {!selectedFile && (
        <div
          onClick={handleClick}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={cn(
            "relative flex flex-col items-center justify-center",
            "min-h-[160px] px-6 py-8 rounded-lg",
            "border-2 border-dashed transition-all duration-200",
            "cursor-pointer group",
            isDragging
              ? "border-primary bg-primary/5 scale-[1.02]"
              : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/30",
            disabled && "opacity-50 cursor-not-allowed"
          )}
        >
          <Upload
            className={cn(
              "w-12 h-12 mb-3 transition-all duration-200",
              isDragging
                ? "text-primary scale-110"
                : "text-muted-foreground group-hover:text-primary group-hover:scale-105"
            )}
          />
          <p className="text-sm font-medium text-foreground mb-1">
            {isDragging ? "Drop your document here" : "Click to upload or drag and drop"}
          </p>
          <p className="text-xs text-muted-foreground text-center">
            Supports: PDF, Word, Excel, Markdown, Text
            <br />
            Max size: {(maxSizeBytes / (1024 * 1024)).toFixed(0)}MB
          </p>

          <input
            ref={fileInputRef}
            type="file"
            accept={acceptAttribute}
            onChange={handleFileInput}
            className="hidden"
            disabled={disabled}
          />
        </div>
      )}

      {/* Selected File Display */}
      {selectedFile && showFileInfo && (
        <div
          className={cn(
            "flex items-center gap-3 p-4 rounded-lg",
            "border border-border bg-card shadow-sm",
            "transition-all duration-200 hover:shadow-md"
          )}
        >
          <div className="flex-shrink-0">
            <FileText className="w-10 h-10 text-primary" />
          </div>
          <div className="flex-1 min-w-0 overflow-hidden">
            <p className="text-sm font-medium text-foreground truncate" title={selectedFile.name}>
              {selectedFile.name}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5 truncate">
              {getFileTypeName(selectedFile.name)} • {formatFileSize(selectedFile.size)}
            </p>
          </div>
          {!disabled && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRemove}
              className="flex-shrink-0 h-8 w-8 p-0 hover:bg-destructive/10 hover:text-destructive"
            >
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/20">
          <AlertCircle className="w-4 h-4 text-destructive flex-shrink-0 mt-0.5" />
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}
    </div>
  );
}
