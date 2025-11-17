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
    user_id: Optional[int] = None  # If provided, reset user overrides; if None, reset all


class DocumentSchema(BaseModel):
    """Document metadata schema"""
    id: str
    file_id: str
    original_filename: str
    file_extension: str
    mime_type: Optional[str] = None
    file_hash: str
    size_bytes: int
    storage_path: str
    category: str
    text_preview: Optional[str] = None
    page_count: Optional[int] = None
    task_id: Optional[str] = None
    inference_history_id: Optional[int] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    """Response for document upload"""
    document: DocumentSchema
    message: str


class DocumentListResponse(BaseModel):
    """Response for listing documents"""
    documents: List[DocumentSchema]
    total: int
    category: Optional[str] = None


class KnowledgeBaseSummaryResponse(BaseModel):
    """Knowledge base statistics"""
    total_documents: int
    total_size_bytes: int
    total_size_mb: float
    by_category: dict
    by_extension: dict
    last_updated: str
