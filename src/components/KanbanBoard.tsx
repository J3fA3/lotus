import { useState, useEffect, useCallback, useRef } from "react";
import { Task, TaskStatus } from "@/types/task";
import { TaskCard } from "./TaskCard";
import { TaskDetailDialog } from "./TaskDetailDialog";
import { QuickAddTask } from "./QuickAddTask";
import { AIInferenceDialog } from "./AIInferenceDialog";
import { ShortcutSettings } from "./ShortcutSettings";
import { Button } from "./ui/button";
import { Plus, Keyboard, Sparkles, Loader2, Settings2 } from "lucide-react";
import { toast } from "sonner";
import * as tasksApi from "@/api/tasks";
import { InferenceResponse } from "@/api/tasks";
import { useRegisterShortcut, useShortcuts } from "@/contexts/ShortcutContext";
import { getShortcutDisplay } from "@/hooks/useKeyboardHandler";

// Constants
const COLUMNS: { id: TaskStatus; title: string }[] = [
  { id: "todo", title: "To-Do" },
  { id: "doing", title: "In Progress" },
  { id: "done", title: "Done" },
];

const KEYBOARD_SHORTCUTS = {
  TODO: "1",
  DOING: "2",
  DONE: "3",
  HELP: "?",
} as const;

const TOAST_DURATION = {
  SHORT: 2000,
  MEDIUM: 3000,
  LONG: 5000,
} as const;

export const KanbanBoard = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [draggedTask, setDraggedTask] = useState<Task | null>(null);
  const [quickAddColumn, setQuickAddColumn] = useState<TaskStatus | null>(null);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [isAIDialogOpen, setIsAIDialogOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [backendConnected, setBackendConnected] = useState(false);

  // New state for keyboard navigation
  const [focusedColumn, setFocusedColumn] = useState<number>(0); // 0 = todo, 1 = doing, 2 = done
  const [focusedTaskIndex, setFocusedTaskIndex] = useState<number>(0);
  const [navigationMode, setNavigationMode] = useState(false); // Track if we're in keyboard navigation mode

  const { shortcuts, getShortcutByAction } = useShortcuts();

  // Load tasks from backend on mount
  useEffect(() => {
    loadTasks();
    checkBackendHealth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const checkBackendHealth = useCallback(async () => {
    try {
      const health = await tasksApi.checkHealth();
      setBackendConnected(health.ollama_connected);

      if (!health.ollama_connected) {
        toast.warning("Ollama is not connected. AI features will not work.", {
          duration: TOAST_DURATION.LONG,
        });
      }
    } catch (err) {
      console.error("Backend health check failed:", err);
      setBackendConnected(false);
      toast.error("Backend not connected. Using demo mode.", {
        description: "Start the backend server to enable AI features.",
        duration: TOAST_DURATION.LONG,
      });
    }
  }, []);

  const loadTasks = useCallback(async () => {
    setIsLoading(true);
    try {
      const fetchedTasks = await tasksApi.fetchTasks();
      setTasks(fetchedTasks);
    } catch (err) {
      console.error("Failed to load tasks:", err);
      toast.error("Failed to load tasks from backend", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Helper function to get tasks in current column
  const getColumnTasks = useCallback((columnIndex: number) => {
    const status = COLUMNS[columnIndex].id;
    return tasks.filter((t) => t.status === status);
  }, [tasks]);

  // Helper function to get focused task
  const getFocusedTask = useCallback(() => {
    const columnTasks = getColumnTasks(focusedColumn);
    return columnTasks[focusedTaskIndex] || null;
  }, [focusedColumn, focusedTaskIndex, getColumnTasks]);

  // Register keyboard shortcuts
  useRegisterShortcut('quick_add_todo', () => {
    setQuickAddColumn("todo");
    setFocusedColumn(0);
    setNavigationMode(true);
    toast.success("Quick add: To-Do", { duration: TOAST_DURATION.SHORT });
  });

  useRegisterShortcut('quick_add_doing', () => {
    setQuickAddColumn("doing");
    setFocusedColumn(1);
    setNavigationMode(true);
    toast.success("Quick add: In Progress", { duration: TOAST_DURATION.SHORT });
  });

  useRegisterShortcut('quick_add_done', () => {
    setQuickAddColumn("done");
    setFocusedColumn(2);
    setNavigationMode(true);
    toast.success("Quick add: Done", { duration: TOAST_DURATION.SHORT });
  });

  useRegisterShortcut('toggle_help', () => {
    setShowShortcuts(!showShortcuts);
  });

  useRegisterShortcut('open_settings', () => {
    setIsSettingsOpen(true);
  });

  // Column navigation
  useRegisterShortcut('next_column', () => {
    setFocusedColumn((prev) => Math.min(prev + 1, COLUMNS.length - 1));
    setFocusedTaskIndex(0);
    setNavigationMode(true);
  });

  useRegisterShortcut('prev_column', () => {
    setFocusedColumn((prev) => Math.max(prev - 1, 0));
    setFocusedTaskIndex(0);
    setNavigationMode(true);
  });

  // Task navigation
  useRegisterShortcut('next_task', () => {
    const columnTasks = getColumnTasks(focusedColumn);
    setFocusedTaskIndex((prev) => Math.min(prev + 1, columnTasks.length - 1));
    setNavigationMode(true);
  });

  useRegisterShortcut('prev_task', () => {
    setFocusedTaskIndex((prev) => Math.max(prev - 1, 0));
    setNavigationMode(true);
  });

  useRegisterShortcut('first_task', () => {
    setFocusedTaskIndex(0);
    setNavigationMode(true);
  });

  useRegisterShortcut('last_task', () => {
    const columnTasks = getColumnTasks(focusedColumn);
    setFocusedTaskIndex(Math.max(0, columnTasks.length - 1));
    setNavigationMode(true);
  });

  // Task actions
  useRegisterShortcut('open_task', () => {
    const task = getFocusedTask();
    if (task) {
      handleTaskClick(task);
    }
  });

  useRegisterShortcut('new_task', () => {
    const status = COLUMNS[focusedColumn].id;
    setQuickAddColumn(status);
    setNavigationMode(true);
  });

  useRegisterShortcut('edit_task', () => {
    const task = getFocusedTask();
    if (task) {
      handleTaskClick(task);
    }
  });

  useRegisterShortcut('delete_task', () => {
    const task = getFocusedTask();
    if (task) {
      if (confirm(`Delete task "${task.title}"?`)) {
        handleDeleteTask(task.id);
      }
    }
  });

  useRegisterShortcut('duplicate_task', () => {
    const task = getFocusedTask();
    if (task) {
      const duplicated = {
        ...task,
        id: undefined,
        title: `${task.title} (copy)`,
      };
      tasksApi.createTask(duplicated).then((newTask) => {
        setTasks((prev) => [...prev, newTask]);
        toast.success("Task duplicated", { duration: TOAST_DURATION.SHORT });
      });
    }
  });

  useRegisterShortcut('toggle_complete', () => {
    const task = getFocusedTask();
    if (task) {
      const newStatus: TaskStatus = task.status === "done" ? "todo" : "done";
      handleUpdateTask({ ...task, status: newStatus });
    }
  });

  useRegisterShortcut('move_task', () => {
    const task = getFocusedTask();
    if (task) {
      // Cycle through statuses
      const statusOrder: TaskStatus[] = ["todo", "doing", "done"];
      const currentIndex = statusOrder.indexOf(task.status);
      const nextStatus = statusOrder[(currentIndex + 1) % statusOrder.length];
      handleUpdateTask({ ...task, status: nextStatus });
      toast.success(`Moved to ${COLUMNS.find(c => c.id === nextStatus)?.title}`, { duration: TOAST_DURATION.SHORT });
    }
  });

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
    setIsDialogOpen(true);
  };

  const handleQuickAddTask = useCallback(async (status: TaskStatus, title: string) => {
    try {
      const newTask = await tasksApi.createTask({
        title,
        status,
        assignee: "You",
      });
      setTasks((prev) => [...prev, newTask]);
      setQuickAddColumn(null);
      toast.success("Task added", { duration: TOAST_DURATION.SHORT });
    } catch (err) {
      console.error("Failed to create task:", err);
      toast.error("Failed to create task", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    }
  }, []);

  const handleAddTask = useCallback((status: TaskStatus) => {
    setQuickAddColumn(status);
  }, []);

  const handleUpdateTask = useCallback(async (updatedTask: Task) => {
    try {
      await tasksApi.updateTask(updatedTask.id, updatedTask);
      setTasks((prev) => prev.map((t) => (t.id === updatedTask.id ? updatedTask : t)));
      setSelectedTask(updatedTask);
    } catch (err) {
      console.error("Failed to update task:", err);
      toast.error("Failed to update task", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    }
  }, []);

  const handleDeleteTask = useCallback(async (taskId: string) => {
    try {
      await tasksApi.deleteTask(taskId);
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
      setIsDialogOpen(false);
      setSelectedTask(null);
      toast.success("Task deleted", { duration: TOAST_DURATION.SHORT });
    } catch (err) {
      console.error("Failed to delete task:", err);
      toast.error("Failed to delete task", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    }
  }, []);

  const handleDragStart = useCallback((task: Task) => {
    setDraggedTask(task);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const handleDrop = useCallback(async (status: TaskStatus) => {
    if (!draggedTask || draggedTask.status === status) {
      setDraggedTask(null);
      return;
    }

    const updatedTask = { ...draggedTask, status, updatedAt: new Date().toISOString() };
    try {
      await tasksApi.updateTask(draggedTask.id, { status });
      setTasks((prev) => prev.map((t) => (t.id === draggedTask.id ? updatedTask : t)));
      toast.success("Task moved", { duration: TOAST_DURATION.SHORT });
    } catch (err) {
      console.error("Failed to update task:", err);
      toast.error("Failed to move task", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    }
    setDraggedTask(null);
  }, [draggedTask]);

  const handleTasksInferred = useCallback((result: InferenceResponse) => {
    // Add inferred tasks to the board
    setTasks((prev) => [...prev, ...result.tasks]);
    
    const taskCount = result.tasks_inferred;
    const taskWord = taskCount === 1 ? "task" : "tasks";
    const timeInSeconds = (result.inference_time_ms / 1000).toFixed(1);
    
    toast.success(
      `Added ${taskCount} ${taskWord} to your board!`,
      {
        description: `Processed in ${timeInSeconds}s using ${result.model_used}`,
        duration: TOAST_DURATION.MEDIUM,
      }
    );
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-[1600px] mx-auto px-6 lg:px-12 py-8 lg:py-12">
        <div className="mb-10 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-foreground mb-1.5 tracking-tight">
              Tasks Board
            </h1>
            <p className="text-sm text-muted-foreground font-light">
              Organize and track your work with clarity
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="default"
              size="sm"
              onClick={() => setIsAIDialogOpen(true)}
              className="gap-2"
              disabled={!backendConnected}
            >
              <Sparkles className="h-4 w-4" />
              <span className="text-xs">AI Infer Tasks</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowShortcuts(!showShortcuts)}
              className="text-muted-foreground hover:text-foreground gap-2"
            >
              <Keyboard className="h-4 w-4" />
              <span className="text-xs">Shortcuts</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsSettingsOpen(true)}
              className="text-muted-foreground hover:text-foreground gap-2"
            >
              <Settings2 className="h-4 w-4" />
              <span className="text-xs">Settings</span>
            </Button>
          </div>
        </div>

        {showShortcuts && (
          <div className="mb-6 p-6 bg-muted/30 border border-border/30 rounded-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-foreground uppercase tracking-wider">
                Keyboard Shortcuts
              </h3>
              <span className="text-xs text-muted-foreground">
                Press ? to toggle
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* Board Navigation */}
              <div>
                <h4 className="text-xs font-semibold text-foreground/80 mb-2">Board Navigation</h4>
                <div className="space-y-1.5">
                  {shortcuts.filter(s => s.category === 'board' && s.enabled).slice(0, 8).map(shortcut => (
                    <div key={shortcut.id} className="flex items-center gap-2">
                      <kbd className="px-2 py-1 bg-background border border-border rounded text-[10px] font-mono min-w-[3rem] text-center">
                        {getShortcutDisplay(shortcut)}
                      </kbd>
                      <span className="text-xs text-muted-foreground">{shortcut.description}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Task Navigation */}
              <div>
                <h4 className="text-xs font-semibold text-foreground/80 mb-2">Task Navigation</h4>
                <div className="space-y-1.5">
                  {shortcuts.filter(s => s.category === 'task' && s.enabled).slice(0, 8).map(shortcut => (
                    <div key={shortcut.id} className="flex items-center gap-2">
                      <kbd className="px-2 py-1 bg-background border border-border rounded text-[10px] font-mono min-w-[3rem] text-center">
                        {getShortcutDisplay(shortcut)}
                      </kbd>
                      <span className="text-xs text-muted-foreground">{shortcut.description}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Quick Actions */}
              <div>
                <h4 className="text-xs font-semibold text-foreground/80 mb-2">Quick Actions</h4>
                <div className="space-y-1.5">
                  {shortcuts.filter(s => s.category === 'task' && s.enabled).slice(8, 16).map(shortcut => (
                    <div key={shortcut.id} className="flex items-center gap-2">
                      <kbd className="px-2 py-1 bg-background border border-border rounded text-[10px] font-mono min-w-[3rem] text-center">
                        {getShortcutDisplay(shortcut)}
                      </kbd>
                      <span className="text-xs text-muted-foreground">{shortcut.description}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="mt-4 pt-4 border-t border-border/30 flex items-center justify-between">
              <p className="text-xs text-muted-foreground">
                💡 Tip: Use arrow keys (↑↓←→) or Vim keys (h/j/k/l) for navigation. Press Enter to open tasks.
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setShowShortcuts(false);
                  setIsSettingsOpen(true);
                }}
                className="gap-2"
              >
                <Settings2 className="h-3 w-3" />
                <span className="text-xs">Customize Shortcuts</span>
              </Button>
            </div>
          </div>
        )}

        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        )}

        {!isLoading && !backendConnected && (
          <div className="mb-6 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-xl">
            <p className="text-sm text-yellow-700 dark:text-yellow-400">
              ⚠️ Backend not connected. Start the backend server to enable task persistence and AI features.
            </p>
          </div>
        )}

        {!isLoading && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {COLUMNS.map((column) => (
            <div
              key={column.id}
              className="flex flex-col bg-column-bg rounded-2xl p-3 min-h-[70vh] transition-all duration-300"
              onDragOver={handleDragOver}
              onDrop={() => handleDrop(column.id)}
            >
              <div className="flex items-center justify-between px-2 py-3 mb-2">
                <div className="flex items-center gap-2.5">
                  <h2 className="text-xs font-semibold text-foreground/70 uppercase tracking-wider">
                    {column.title}
                  </h2>
                  <span className="text-xs text-muted-foreground font-medium bg-background/60 px-2 py-0.5 rounded-full">
                    {tasks.filter((t) => t.status === column.id).length}
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 hover:bg-background/60 rounded-lg transition-colors"
                  onClick={() => handleAddTask(column.id)}
                >
                  <Plus className="h-3.5 w-3.5" />
                </Button>
              </div>

              <div className="space-y-2.5 flex-1 px-1">
                {quickAddColumn === column.id && (
                  <QuickAddTask
                    onAdd={(title) => handleQuickAddTask(column.id, title)}
                    onCancel={() => setQuickAddColumn(null)}
                  />
                )}
                {tasks
                  .filter((task) => task.status === column.id)
                  .map((task, taskIndex) => {
                    const columnIndex = COLUMNS.findIndex(c => c.id === column.id);
                    const isFocused = navigationMode &&
                                     columnIndex === focusedColumn &&
                                     taskIndex === focusedTaskIndex;

                    return (
                      <div
                        key={task.id}
                        className={`${isFocused ? 'ring-2 ring-primary ring-offset-2 rounded-lg' : ''}`}
                      >
                        <TaskCard
                          task={task}
                          onClick={() => handleTaskClick(task)}
                          onDragStart={() => handleDragStart(task)}
                        />
                      </div>
                    );
                  })}
              </div>
            </div>
          ))}
        </div>
        )}
      </div>

      <AIInferenceDialog
        open={isAIDialogOpen}
        onOpenChange={setIsAIDialogOpen}
        onTasksInferred={handleTasksInferred}
      />

      {selectedTask && (
        <TaskDetailDialog
          task={selectedTask}
          open={isDialogOpen}
          onOpenChange={setIsDialogOpen}
          onUpdate={handleUpdateTask}
          onDelete={handleDeleteTask}
        />
      )}

      <ShortcutSettings
        open={isSettingsOpen}
        onOpenChange={setIsSettingsOpen}
      />
    </div>
  );
};
