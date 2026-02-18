/**
 * @fileoverview Unified Attachments Component (URL-only)
 *
 * A cohesive interface for managing URL link attachments with smart display,
 * inline editing, and clickable links that open in new tabs.
 *
 * ## Key Features
 *
 * - **Enter-to-submit**: Press Enter to add URLs without clicking buttons
 * - **Clickable URLs**: Links open in new tabs with visual feedback
 * - **Inline editing**: Edit URLs without modals or page navigation
 * - **Smart URL display**: Shows domain prominently, truncates paths gracefully
 * - **Auto-normalization**: Adds https:// to URLs if missing
 */

import { useState, useRef, useCallback } from "react";
import {
  Link2,
  Pencil,
  Check,
  X,
  Plus,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

// ============================================================================
// Types
// ============================================================================

interface UnifiedAttachmentsProps {
  attachments: string[];
  onAddAttachment: (url: string) => void;
  onRemoveAttachment: (index: number) => void;
  onEditAttachment: (index: number, newUrl: string) => void;
  className?: string;
}

// ============================================================================
// Utility Functions
// ============================================================================

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
    return {
      domain: url.length > 40 ? url.slice(0, 37) + "..." : url,
      path: "",
    };
  }
}

function isValidUrl(string: string): boolean {
  try {
    new URL(string);
    return true;
  } catch {
    try {
      new URL("https://" + string);
      return string.includes(".");
    } catch {
      return false;
    }
  }
}

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

export function UnifiedAttachments({
  attachments,
  onAddAttachment,
  onRemoveAttachment,
  onEditAttachment,
  className,
}: UnifiedAttachmentsProps) {
  const [newUrl, setNewUrl] = useState("");
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editingValue, setEditingValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const editInputRef = useRef<HTMLInputElement>(null);

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

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleAddUrl();
      }
    },
    [handleAddUrl]
  );

  const startEditing = useCallback((index: number, currentUrl: string) => {
    setEditingIndex(index);
    setEditingValue(currentUrl);
    setTimeout(() => editInputRef.current?.focus(), 0);
  }, []);

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

  const cancelEdit = useCallback(() => {
    setEditingIndex(null);
    setEditingValue("");
  }, []);

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

  return (
    <div className={cn("space-y-3", className)}>
      {/* Input Row */}
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
      </div>

      {/* Validation Error */}
      {error && (
        <p className="text-xs text-destructive px-1">{error}</p>
      )}

      {/* Attachments List */}
      {attachments.length > 0 && (
        <div className="space-y-1.5">
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
        </div>
      )}
    </div>
  );
}
