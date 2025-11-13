"""
Pydantic schemas for API request/response validation
"""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class CommentSchema(BaseModel):
    """Comment schema matching frontend"""
    id: str
    text: str
    author: str
    createdAt: str

    class Config:
        from_attributes = True


class TaskSchema(BaseModel):
    """Task schema matching frontend Task interface"""
    id: str
    title: str
    status: Literal["todo", "doing", "done"]
    assignee: str
    startDate: Optional[str] = None
    dueDate: Optional[str] = None
    valueStream: Optional[str] = None
    description: Optional[str] = None
    attachments: List[str] = Field(default_factory=list)
    comments: List[CommentSchema] = Field(default_factory=list)
    createdAt: str
    updatedAt: str

    class Config:
        from_attributes = True


class TaskCreateRequest(BaseModel):
    """Request for creating a new task"""
    title: str
    status: Literal["todo", "doing", "done"] = "todo"
    assignee: str = "You"
    startDate: Optional[str] = None
    dueDate: Optional[str] = None
    valueStream: Optional[str] = None
    description: Optional[str] = None


class TaskUpdateRequest(BaseModel):
    """Request for updating a task"""
    title: Optional[str] = None
    status: Optional[Literal["todo", "doing", "done"]] = None
    assignee: Optional[str] = None
    startDate: Optional[str] = None
    dueDate: Optional[str] = None
    valueStream: Optional[str] = None
    description: Optional[str] = None


class InferenceRequest(BaseModel):
    """Request for AI task inference"""
    text: str = Field(..., description="Text content to analyze for tasks")
    assignee: str = Field(default="You", description="Default assignee for inferred tasks")


class InferenceResponse(BaseModel):
    """Response from AI inference"""
    tasks: List[TaskSchema]
    inference_time_ms: int
    model_used: str
    tasks_inferred: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    ollama_connected: bool
    database_connected: bool
    model: str
