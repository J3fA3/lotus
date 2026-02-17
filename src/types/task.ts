export type TaskStatus = "todo" | "doing" | "done";

export interface Task {
  id: string;
  title: string;
  status: TaskStatus;
  assignee: string;
  startDate?: string;
  dueDate?: string;
  valueStream?: string;
  description?: string;
  attachments: string[];
  comments: Comment[];
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Comment {
  id: string;
  text: string;
  author: string;
  createdAt: string;
}

export interface ValueStream {
  id: string;
  name: string;
  color?: string;
  createdAt: string;
  updatedAt: string;
}
