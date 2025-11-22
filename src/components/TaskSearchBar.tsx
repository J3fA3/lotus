import { useState, useRef, useEffect, useImperativeHandle, forwardRef } from "react";
import { Search, X, Loader2 } from "lucide-react";
import { Input } from "./ui/input";
import { cn } from "@/lib/utils";

interface TaskSearchBarProps {
  onSearch: (query: string) => void;
  isSearching?: boolean;
  className?: string;
}

export interface TaskSearchBarRef {
  focus: () => void;
}

export const TaskSearchBar = forwardRef<TaskSearchBarRef, TaskSearchBarProps>(
  ({ onSearch, isSearching = false, className }, ref) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout>();

  // Handle search with debouncing (reduced to 150ms for faster feel)
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      console.log('[TaskSearchBar] Triggering search with query:', searchQuery);
      onSearch(searchQuery);
    }, 150);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [searchQuery, onSearch]);

  // Auto-focus when expanded
  useEffect(() => {
    if (isExpanded && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isExpanded]);

  // Handle clicks outside to collapse
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node) &&
        !searchQuery.trim()
      ) {
        setIsExpanded(false);
      }
    };

    if (isExpanded) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isExpanded, searchQuery]);

  const handleExpand = () => {
    setIsExpanded(true);
  };

  const handleClear = () => {
    setSearchQuery("");
    setIsExpanded(false);
    onSearch("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      handleClear();
    }
  };

  // Expose focus method to parent components
  useImperativeHandle(ref, () => ({
    focus: () => {
      if (!isExpanded) {
        setIsExpanded(true);
      }
      // Focus will happen automatically via the useEffect that watches isExpanded
      // But we'll also ensure it focuses after a brief delay to handle the DOM update
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
        }
      }, 0);
    },
  }));

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      {!isExpanded ? (
        // Collapsed: Show search icon button
        <button
          onClick={handleExpand}
          className="flex items-center justify-center h-9 w-9 rounded-lg bg-card border border-border hover:border-primary/50 hover:bg-accent/50 transition-all duration-200 shadow-sm hover:shadow-md"
          aria-label="Search tasks"
        >
          <Search className="h-4 w-4 text-muted-foreground" />
        </button>
      ) : (
        // Expanded: Show search input
        <div className="flex items-center gap-2 bg-card border border-primary/30 rounded-lg px-3 py-1.5 shadow-zen-sm hover:shadow-zen-md transition-all duration-300 min-w-[280px]">
          {isSearching ? (
            <Loader2 className="h-4 w-4 text-primary flex-shrink-0 animate-spin" />
          ) : (
            <Search className="h-4 w-4 text-muted-foreground flex-shrink-0" />
          )}
          <Input
            ref={inputRef}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search tasks..."
            className="border-0 px-0 h-auto text-sm focus-visible:ring-0 placeholder:text-muted-foreground/50 bg-transparent"
          />
          {searchQuery && (
            <button
              onClick={handleClear}
              className="flex-shrink-0 text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Clear search"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      )}
    </div>
  );
});

TaskSearchBar.displayName = "TaskSearchBar";
