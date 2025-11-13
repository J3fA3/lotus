import { useState } from "react";
import { Task, TaskStatus } from "@/types/task";
import { TaskCard } from "./TaskCard";
import { TaskDetailDialog } from "./TaskDetailDialog";
import { Button } from "./ui/button";
import { Plus } from "lucide-react";

const COLUMNS: { id: TaskStatus; title: string }[] = [
  { id: "todo", title: "To-Do" },
  { id: "doing", title: "In Progress" },
  { id: "done", title: "Done" },
];

export const KanbanBoard = () => {
  const [tasks, setTasks] = useState<Task[]>([
    {
      id: "1",
      title: "Design new landing page",
      status: "todo",
      assignee: "You",
      startDate: "2025-11-13",
      dueDate: "2025-11-20",
      valueStream: "Marketing",
      description: "Create a modern, responsive landing page design",
      attachments: [],
      comments: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    },
    {
      id: "2",
      title: "Implement authentication",
      status: "doing",
      assignee: "You",
      startDate: "2025-11-10",
      dueDate: "2025-11-15",
      valueStream: "Development",
      description: "Add user login and signup functionality",
      attachments: [],
      comments: [
        {
          id: "c1",
          text: "Started working on the OAuth integration",
          author: "You",
          createdAt: new Date().toISOString(),
        },
      ],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    },
  ]);

  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [draggedTask, setDraggedTask] = useState<Task | null>(null);

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
    setIsDialogOpen(true);
  };

  const handleAddTask = (status: TaskStatus) => {
    const newTask: Task = {
      id: crypto.randomUUID(),
      title: "New Task",
      status,
      assignee: "You",
      attachments: [],
      comments: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setTasks([...tasks, newTask]);
    setSelectedTask(newTask);
    setIsDialogOpen(true);
  };

  const handleUpdateTask = (updatedTask: Task) => {
    setTasks(tasks.map((t) => (t.id === updatedTask.id ? updatedTask : t)));
    setSelectedTask(updatedTask);
  };

  const handleDeleteTask = (taskId: string) => {
    setTasks(tasks.filter((t) => t.id !== taskId));
    setIsDialogOpen(false);
    setSelectedTask(null);
  };

  const handleDragStart = (task: Task) => {
    setDraggedTask(task);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (status: TaskStatus) => {
    if (draggedTask && draggedTask.status !== status) {
      const updatedTask = { ...draggedTask, status, updatedAt: new Date().toISOString() };
      setTasks(tasks.map((t) => (t.id === draggedTask.id ? updatedTask : t)));
    }
    setDraggedTask(null);
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-[1600px] mx-auto px-6 lg:px-12 py-8 lg:py-12">
        <div className="mb-10">
          <h1 className="text-2xl font-semibold text-foreground mb-1.5 tracking-tight">
            Tasks Board
          </h1>
          <p className="text-sm text-muted-foreground font-light">
            Organize and track your work with clarity
          </p>
        </div>

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
      </div>

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
