import { useState, useRef, useEffect } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "./ui/alert-dialog";
import { Button } from "./ui/button";
import { Trash2 } from "lucide-react";

interface DeleteTaskDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  taskTitle: string;
  onConfirm: () => void | Promise<void>;
  isLoading?: boolean;
}

export function DeleteTaskDialog({
  open,
  onOpenChange,
  taskTitle,
  onConfirm,
  isLoading = false,
}: DeleteTaskDialogProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const deleteButtonRef = useRef<HTMLButtonElement>(null);

  const handleConfirm = async () => {
    setIsDeleting(true);
    
    // Safety timeout: if the operation takes more than 30 seconds, reset loading state
    const timeoutId = setTimeout(() => {
      console.warn("Delete operation timed out, resetting loading state");
      setIsDeleting(false);
    }, 30000);
    
    try {
      await onConfirm();
      // Only close dialog on success - parent component handles state updates
      onOpenChange(false);
    } catch (error) {
      // Error handling is done by the parent component
      // Don't close dialog on error so user can see the error and potentially retry
      console.error("Error deleting task:", error);
      // Don't re-throw - parent's error handler will have already executed
      // The error was thrown from within onConfirm, so parent's try-catch will handle it
    } finally {
      clearTimeout(timeoutId);
      setIsDeleting(false);
    }
  };

  // Extract plain text from HTML if taskTitle contains HTML
  const getPlainText = (html: string): string => {
    const div = document.createElement("div");
    div.innerHTML = html;
    return div.textContent || div.innerText || html;
  };

  const plainTitle = getPlainText(taskTitle);

  // Auto-focus the delete button when dialog opens and ensure focus is trapped
  useEffect(() => {
    if (open) {
      // Focus the delete button immediately when dialog opens
      const timer = setTimeout(() => {
        deleteButtonRef.current?.focus();
      }, 50);

      // Prevent ALL keyboard events from reaching the board when dialog is open
      // This is a safety net - the keyboard handler should also check for dialogs
      const handleKeyDown = (e: KeyboardEvent) => {
        // Only allow Escape to pass through (Radix UI handles closing)
        if (e.key === 'Escape') {
          return;
        }

        // Check if event target is within the dialog
        const dialogContent = document.querySelector('[role="alertdialog"]');
        const isFromDialog = dialogContent?.contains(e.target as Node);

        // If event is not from within the dialog, block it completely
        if (!isFromDialog) {
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
          return false;
        }

        // Even if from dialog, prevent Enter from bubbling if it's not on a button
        if (e.key === 'Enter') {
          const target = e.target as HTMLElement;
          const isButton = target.tagName === 'BUTTON' || 
                          target.closest('button') !== null ||
                          target.getAttribute('role') === 'button';
          
          if (!isButton) {
            e.preventDefault();
            e.stopPropagation();
          }
        }
      };

      // Add event listener in capture phase (before all other handlers)
      document.addEventListener('keydown', handleKeyDown, true);

      return () => {
        clearTimeout(timer);
        document.removeEventListener('keydown', handleKeyDown, true);
      };
    }
  }, [open]);

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent
        onOpenAutoFocus={(e) => {
          // Prevent default auto-focus behavior and focus delete button instead
          e.preventDefault();
          setTimeout(() => {
            deleteButtonRef.current?.focus();
          }, 0);
        }}
        onEscapeKeyDown={(e) => {
          // Allow Escape to close the dialog
          // This is the default behavior, but we're being explicit
        }}
      >
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <Trash2 className="h-5 w-5 text-destructive" />
            Delete Task
          </AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to delete <strong>"{plainTitle}"</strong>? This action cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isDeleting || isLoading}>
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            ref={deleteButtonRef}
            onClick={handleConfirm}
            onKeyDown={(e) => {
              // Ensure Enter key triggers delete when button is focused
              if (e.key === 'Enter' && !isDeleting && !isLoading) {
                e.preventDefault();
                e.stopPropagation();
                handleConfirm();
              }
            }}
            disabled={isDeleting || isLoading}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            autoFocus
          >
            {isDeleting || isLoading ? "Deleting..." : "Delete"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

