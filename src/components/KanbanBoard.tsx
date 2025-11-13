import { useState, useEffect } from "react";
import { Task, TaskStatus } from "@/types/task";
import { TaskCard } from "./TaskCard";
import { TaskDetailDialog } from "./TaskDetailDialog";
import { QuickAddTask } from "./QuickAddTask";
import { AIInferenceDialog } from "./AIInferenceDialog";
import { Button } from "./ui/button";
import { Plus, Keyboard, Sparkles, Loader2 } from "lucide-react";
import { toast } from "sonner";
import * as tasksApi from "@/api/tasks";
import { InferenceResponse } from "@/api/tasks";

const COLUMNS: { id: TaskStatus; title: string }[] = [
  { id: "todo", title: "To-Do" },
  { id: "doing", title: "In Progress" },
  { id: "done", title: "Done" },
];

export const KanbanBoard = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [draggedTask, setDraggedTask] = useState<Task | null>(null);
  const [quickAddColumn, setQuickAddColumn] = useState<TaskStatus | null>(null);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [isAIDialogOpen, setIsAIDialogOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [backendConnected, setBackendConnected] = useState(false);

  // Load tasks from backend on mount
  useEffect(() => {
    loadTasks();
    checkBackendHealth();
  }, []);

  const checkBackendHealth = async () => {
    try {
      const health = await tasksApi.checkHealth();
      setBackendConnected(health.ollama_connected);

      if (!health.ollama_connected) {
        toast.warning("Ollama is not connected. AI features will not work.", {
          duration: 5000,
        });
      }
    } catch (err) {
      console.error("Backend health check failed:", err);
      toast.error("Backend not connected. Using demo mode.", {
        description: "Start the backend server to enable AI features.",
        duration: 5000,
      });
    }
  };

  const loadTasks = async () => {
    setIsLoading(true);
    try {
      const fetchedTasks = await tasksApi.fetchTasks();
      setTasks(fetchedTasks);
    } catch (err) {
      console.error("Failed to load tasks:", err);
      toast.error("Failed to load tasks from backend");
    } finally {
      setIsLoading(false);
    }
  };

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      // 1 = Add to To-Do, 2 = Add to In Progress, 3 = Add to Done
      if (e.key === "1") {
        e.preventDefault();
        setQuickAddColumn("todo");
        toast.success("Quick add: To-Do");
      } else if (e.key === "2") {
        e.preventDefault();
        setQuickAddColumn("doing");
        toast.success("Quick add: In Progress");
      } else if (e.key === "3") {
        e.preventDefault();
        setQuickAddColumn("done");
        toast.success("Quick add: Done");
      } else if (e.key === "?" && e.shiftKey) {
        e.preventDefault();
        setShowShortcuts(!showShortcuts);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [showShortcuts]);

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
    setIsDialogOpen(true);
  };

  const handleQuickAddTask = async (status: TaskStatus, title: string) => {
    try {
      const newTask = await tasksApi.createTask({
        title,
        status,
        assignee: "You",
      });
      setTasks([...tasks, newTask]);
      setQuickAddColumn(null);
      toast.success("Task added");
    } catch (err) {
      console.error("Failed to create task:", err);
      toast.error("Failed to create task");
    }
  };

  const handleAddTask = (status: TaskStatus) => {
    setQuickAddColumn(status);
  };

  const handleUpdateTask = async (updatedTask: Task) => {
    try {
      await tasksApi.updateTask(updatedTask.id, updatedTask);
      setTasks(tasks.map((t) => (t.id === updatedTask.id ? updatedTask : t)));
      setSelectedTask(updatedTask);
    } catch (err) {
      console.error("Failed to update task:", err);
      toast.error("Failed to update task");
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    try {
      await tasksApi.deleteTask(taskId);
      setTasks(tasks.filter((t) => t.id !== taskId));
      setIsDialogOpen(false);
      setSelectedTask(null);
      toast.success("Task deleted");
    } catch (err) {
      console.error("Failed to delete task:", err);
      toast.error("Failed to delete task");
    }
  };

  const handleDragStart = (task: Task) => {
    setDraggedTask(task);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = async (status: TaskStatus) => {
    if (draggedTask && draggedTask.status !== status) {
      const updatedTask = { ...draggedTask, status, updatedAt: new Date().toISOString() };
      try {
        await tasksApi.updateTask(draggedTask.id, { status });
        setTasks(tasks.map((t) => (t.id === draggedTask.id ? updatedTask : t)));
      } catch (err) {
        console.error("Failed to update task:", err);
        toast.error("Failed to move task");
      }
    }
    setDraggedTask(null);
  };

  const handleTasksInferred = (result: InferenceResponse) => {
    // Add inferred tasks to the board
    setTasks([...tasks, ...result.tasks]);
    toast.success(
      `Added ${result.tasks_inferred} task${result.tasks_inferred > 1 ? "s" : ""} to your board!`,
      {
        description: `Processed in ${(result.inference_time_ms / 1000).toFixed(1)}s using ${result.model_used}`,
      }
    );
  };

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
          </div>
        </div>

        {showShortcuts && (
          <div className="mb-6 p-4 bg-muted/30 border border-border/30 rounded-xl">
            <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">
              Keyboard Shortcuts
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              <div className="flex items-center gap-2">
                <kbd className="px-2 py-1 bg-background border border-border rounded text-[10px] font-mono">1</kbd>
                <span className="text-muted-foreground">Quick add to To-Do</span>
              </div>
              <div className="flex items-center gap-2">
                <kbd className="px-2 py-1 bg-background border border-border rounded text-[10px] font-mono">2</kbd>
                <span className="text-muted-foreground">Quick add to In Progress</span>
              </div>
              <div className="flex items-center gap-2">
                <kbd className="px-2 py-1 bg-background border border-border rounded text-[10px] font-mono">3</kbd>
                <span className="text-muted-foreground">Quick add to Done</span>
              </div>
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
                  .map((task) => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      onClick={() => handleTaskClick(task)}
                      onDragStart={() => handleDragStart(task)}
                    />
                  ))}
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
    </div>
  );
};
