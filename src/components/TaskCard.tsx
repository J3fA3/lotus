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
      className="p-4 cursor-pointer bg-card border border-border/50 hover:border-primary/20 hover:shadow-zen-md transition-all duration-300 group"
      draggable
      onDragStart={onDragStart}
      onClick={onClick}
    >
      <h3 className="font-medium text-[15px] text-card-foreground mb-3 leading-snug tracking-tight group-hover:text-primary transition-colors duration-300">
        {task.title}
      </h3>

      <div className="space-y-2.5">
        {task.valueStream && (
          <Badge 
            variant="secondary" 
            className="text-[11px] px-2.5 py-0.5 font-medium bg-accent text-accent-foreground border-0"
          >
            {task.valueStream}
          </Badge>
        )}

        {task.dueDate && (
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <Calendar className="h-3 w-3 opacity-60" />
            <span className="font-normal">
              {format(new Date(task.dueDate), "MMM d")}
            </span>
          </div>
        )}

        {(task.comments.length > 0 || task.attachments.length > 0) && (
          <div className="flex items-center gap-3 text-[11px] text-muted-foreground pt-1 border-t border-border/30">
            {task.comments.length > 0 && (
              <div className="flex items-center gap-1">
                <MessageSquare className="h-3 w-3 opacity-60" />
                <span className="font-normal">{task.comments.length}</span>
              </div>
            )}
            {task.attachments.length > 0 && (
              <div className="flex items-center gap-1">
                <Paperclip className="h-3 w-3 opacity-60" />
                <span className="font-normal">{task.attachments.length}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
};
