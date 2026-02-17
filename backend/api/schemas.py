"""
Pydantic schemas for API request/response validation
"""
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
    notes: Optional[str] = None
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
    notes: Optional[str] = None


class TaskUpdateRequest(BaseModel):
    """Request for updating a task"""
    title: Optional[str] = None
    status: Optional[Literal["todo", "doing", "done"]] = None
    assignee: Optional[str] = None
    startDate: Optional[str] = None
    dueDate: Optional[str] = None
    valueStream: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    comments: Optional[List[dict]] = None
    attachments: Optional[List[str]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    database_connected: bool


class ShortcutConfigSchema(BaseModel):
    """Keyboard shortcut configuration schema"""
    id: str
    category: Literal["global", "board", "task", "dialog", "message", "bulk"]
    action: str
    key: str
    modifiers: List[str] = Field(default_factory=list)
    enabled: bool = True
    description: str
    user_id: Optional[int] = None
    is_default: bool = True
    createdAt: str
    updatedAt: str

    class Config:
        from_attributes = True


class ShortcutCreateRequest(BaseModel):
    """Request for creating or updating a shortcut"""
    id: str
    category: Literal["global", "board", "task", "dialog", "message", "bulk"]
    action: str
    key: str
    modifiers: List[str] = Field(default_factory=list)
    enabled: bool = True
    description: str
    user_id: Optional[int] = None


class ShortcutUpdateRequest(BaseModel):
    """Request for updating a shortcut"""
    key: Optional[str] = None
    modifiers: Optional[List[str]] = None
    enabled: Optional[bool] = None


class ShortcutBulkUpdateRequest(BaseModel):
    """Request for bulk updating shortcuts"""
    shortcuts: List[ShortcutCreateRequest]


class ShortcutResetRequest(BaseModel):
    """Request for resetting shortcuts"""
    user_id: Optional[int] = None


class ValueStreamSchema(BaseModel):
    """Value stream schema for task organization"""
    id: str
    name: str
    color: Optional[str] = None
    createdAt: str
    updatedAt: str

    class Config:
        from_attributes = True


class ValueStreamCreateRequest(BaseModel):
    """Request for creating a new value stream"""
    name: str
    color: Optional[str] = None


class AIAssistRequest(BaseModel):
    """Request for AI task assistance"""
    task_id: str
    prompt: Optional[str] = None


class AIAssistResponse(BaseModel):
    """Response from AI assistance"""
    response: str
    similar_cases: int
    model: str
