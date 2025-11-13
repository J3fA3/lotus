import { Task } from "@/types/task";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { Calendar, MessageSquare, Paperclip } from "lucide-react";
import { format } from "date-fns";

interface TaskCardProps {
  task: Task;
  onClick: () => void;
  onDragStart: () => void;
}

export const TaskCard = ({ task, onClick, onDragStart }: TaskCardProps) => {
  return (
    <Card
      className="p-4 cursor-pointer hover:shadow-lg transition-all duration-200 bg-card border-border group"
      draggable
      onDragStart={onDragStart}
      onClick={onClick}
    >
      <h3 className="font-medium text-card-foreground mb-3 group-hover:text-primary transition-colors">
        {task.title}
      </h3>

      {task.valueStream && (
        <Badge variant="secondary" className="mb-3 text-xs">
          {task.valueStream}
        </Badge>
      )}

      {task.dueDate && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3">
          <Calendar className="h-3 w-3" />
          <span>Due {format(new Date(task.dueDate), "MMM d")}</span>
        </div>
      )}

      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        {task.comments.length > 0 && (
          <div className="flex items-center gap-1">
            <MessageSquare className="h-3 w-3" />
            <span>{task.comments.length}</span>
          </div>
        )}
        {task.attachments.length > 0 && (
          <div className="flex items-center gap-1">
            <Paperclip className="h-3 w-3" />
            <span>{task.attachments.length}</span>
          </div>
        )}
      </div>
    </Card>
  );
};
