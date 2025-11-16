import { useState, useRef, useEffect } from "react";
import { Input } from "./ui/input";
import { X } from "lucide-react";

interface QuickAddTaskProps {
  onAdd: (title: string) => void;
  onCancel: () => void;
  autoFocus?: boolean;
}

export const QuickAddTask = ({ onAdd, onCancel, autoFocus = true }: QuickAddTaskProps) => {
  const [title, setTitle] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedTitle = title.trim();
    
    if (trimmedTitle) {
      onAdd(trimmedTitle);
      setTitle("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault();
      onCancel();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="group">
      <div className="relative bg-card border border-primary/30 rounded-xl p-3 shadow-zen-sm hover:shadow-zen-md transition-all duration-300">
        <Input
          ref={inputRef}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Task title, then press Enter..."
          className="border-0 px-0 h-auto text-[15px] focus-visible:ring-0 placeholder:text-muted-foreground/50"
        />
        <button
          type="button"
          onClick={onCancel}
          className="absolute top-3 right-3 text-muted-foreground hover:text-foreground transition-colors opacity-0 group-hover:opacity-100"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <p className="text-[10px] text-muted-foreground mt-1.5 ml-1 font-light">
        Press Enter to add • Esc to cancel
      </p>
    </form>
  );
};
