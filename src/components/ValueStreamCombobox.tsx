/**
 * ValueStreamCombobox Component
 *
 * A combobox that allows users to:
 * - Select from existing value streams
 * - Create new value streams on-the-fly
 */
import * as React from "react";
import { Check, ChevronsUpDown, Plus, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ValueStream } from "@/types/task";
import { fetchValueStreams, createValueStream, deleteValueStream } from "@/api/valueStreams";
import { toast } from "sonner";

interface ValueStreamComboboxProps {
  value?: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export function ValueStreamCombobox({
  value,
  onChange,
  placeholder = "Select value stream...",
  className,
}: ValueStreamComboboxProps) {
  const [open, setOpen] = React.useState(false);
  const [valueStreams, setValueStreams] = React.useState<ValueStream[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [searchValue, setSearchValue] = React.useState("");

  // Load value streams on mount
  React.useEffect(() => {
    loadValueStreams();
  }, []);

  const loadValueStreams = async () => {
    setIsLoading(true);
    try {
      const streams = await fetchValueStreams();
      setValueStreams(streams);
    } catch (error) {
      console.error("Failed to load value streams:", error);
      toast.error("Failed to load value streams");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateNew = async () => {
    if (!searchValue.trim()) {
      return;
    }

    // Check if it already exists
    const exists = valueStreams.some(
      (vs) => vs.name.toLowerCase() === searchValue.toLowerCase()
    );

    if (exists) {
      toast.error("A value stream with this name already exists");
      return;
    }

    try {
      const newValueStream = await createValueStream({ name: searchValue });
      setValueStreams((prev) => [...prev, newValueStream]);
      onChange(newValueStream.name);
      setOpen(false);
      setSearchValue("");
      toast.success(`Created value stream "${newValueStream.name}"`);
    } catch (error) {
      console.error("Failed to create value stream:", error);
      if (error instanceof Error) {
        toast.error(error.message);
      } else {
        toast.error("Failed to create value stream");
      }
    }
  };

  const handleSelect = (currentValue: string) => {
    onChange(currentValue === value ? "" : currentValue);
    setOpen(false);
    setSearchValue("");
  };

  const handleDelete = async (e: React.MouseEvent, stream: ValueStream) => {
    e.stopPropagation();
    
    try {
      await deleteValueStream(stream.id);
      setValueStreams((prev) => prev.filter((vs) => vs.id !== stream.id));
      
      // Clear selection if the deleted stream was selected
      if (value === stream.name) {
        onChange("");
      }
      
      toast.success(`Deleted value stream "${stream.name}"`);
    } catch (error) {
      console.error("Failed to delete value stream:", error);
      if (error instanceof Error) {
        toast.error(error.message);
      } else {
        toast.error("Failed to delete value stream");
      }
    }
  };

  const showCreateOption =
    searchValue.trim() !== "" &&
    !valueStreams.some(
      (vs) => vs.name.toLowerCase() === searchValue.toLowerCase()
    );

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn(
            "justify-between font-normal h-10 border-border/50 focus:border-primary/50",
            className
          )}
        >
          <span className={cn(!value && "text-muted-foreground")}>
            {value || placeholder}
          </span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[300px] p-0" align="start">
        <Command>
          <CommandInput
            placeholder="Search or create..."
            value={searchValue}
            onValueChange={setSearchValue}
          />
          <CommandList>
            <CommandEmpty>
              {isLoading ? "Loading..." : "No value streams found."}
            </CommandEmpty>
            {valueStreams.length > 0 && (
              <CommandGroup>
                {valueStreams.map((stream) => (
                  <CommandItem
                    key={stream.id}
                    value={stream.name}
                    onSelect={handleSelect}
                    className="group"
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        value === stream.name ? "opacity-100" : "opacity-0"
                      )}
                    />
                    <span className="flex-1">{stream.name}</span>
                    <button
                      onClick={(e) => handleDelete(e, stream)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity ml-2 p-1 hover:bg-destructive/10 rounded"
                      title="Delete value stream"
                    >
                      <X className="h-3 w-3 text-muted-foreground hover:text-destructive" />
                    </button>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
            {showCreateOption && (
              <CommandGroup>
                <CommandItem onSelect={handleCreateNew}>
                  <Plus className="mr-2 h-4 w-4" />
                  Create &quot;{searchValue}&quot;
                </CommandItem>
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
