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


class InferenceRequest(BaseModel):
    """Request for AI task inference"""
    text: str = Field(..., description="Text content to analyze for tasks")
    assignee: str = Field(default="You", description="Default assignee for inferred tasks")


class InferenceResponse(BaseModel):
    """Response from AI inference"""
    model_config = {"protected_namespaces": ()}
    
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


# ============================================================================
# TASK VERSION CONTROL SCHEMAS (Phase 6 Stage 3)
# ============================================================================

class TaskVersionSchema(BaseModel):
    """Schema for task version history entry"""
    id: int
    task_id: str
    version_number: int
    created_at: str

    # Versioning type
    is_snapshot: bool
    is_milestone: bool

    # Provenance
    changed_by: Optional[str]
    change_source: str
    ai_model: Optional[str]

    # Change detection
    change_type: str
    changed_fields: List[str]

    # Data (one of these will be populated)
    snapshot_data: Optional[dict]
    delta_data: Optional[dict]

    # PR-style comment
    pr_comment: Optional[str]
    pr_comment_generated_at: Optional[str]

    # Learning signals
    ai_suggestion_overridden: bool
    overridden_fields: List[str]
    override_reason: Optional[str]

    # Quality
    change_confidence: Optional[float]
    user_approved: Optional[bool]

    class Config:
        from_attributes = True


class TaskVersionHistoryResponse(BaseModel):
    """Response containing version history for a task"""
    task_id: str
    total_versions: int
    versions: List[TaskVersionSchema]
    has_more: bool


class VersionComparisonResponse(BaseModel):
    """Response for comparing two versions"""
    task_id: str
    version_a: int
    version_b: int
    created_at_a: str
    created_at_b: str
    changed_fields: List[str]
    diff: dict  # {field: {old: value, new: value}}


# ============================================================================
# QUESTION QUEUE SCHEMAS (Phase 6 Stage 4)
# ============================================================================

class QuestionSchema(BaseModel):
    """Schema for contextual question"""
    id: int
    task_id: str
    field_name: str
    question: str
    suggested_answer: Optional[str]
    importance: str  # "HIGH", "MEDIUM", "LOW"
    confidence: float
    priority_score: float
    status: str  # "queued", "ready", "shown", "answered", "dismissed", "snoozed"
    created_at: str
    ready_at: Optional[str]
    shown_at: Optional[str]
    answered_at: Optional[str]
    answer: Optional[str]
    answer_source: Optional[str]
    answer_applied: bool
    user_feedback: Optional[str]
    semantic_cluster: Optional[str]

    class Config:
        from_attributes = True


class QuestionListResponse(BaseModel):
    """Response containing list of questions"""
    total: int
    questions: List[QuestionSchema]


class QuestionAnswerRequest(BaseModel):
    """Request to answer a question"""
    answer: str
    answer_source: str = "user_input"  # "user_input", "selected_suggestion"
    feedback: Optional[str] = None  # "helpful", "not_helpful"
    feedback_comment: Optional[str] = None
    apply_to_task: bool = True  # Should answer be applied to task immediately?


class QuestionSnoozeRequest(BaseModel):
    """Request to snooze a question"""
    snooze_hours: int = 24


class QuestionBatchSchema(BaseModel):
    """Schema for question batch"""
    id: str
    batch_type: str
    semantic_cluster: Optional[str]
    question_count: int
    question_ids: List[int]
    task_ids: List[str]
    shown_to_user: bool
    shown_at: Optional[str]
    completed: bool
    completed_at: Optional[str]
    answered_count: int
    dismissed_count: int
    snoozed_count: int
    created_at: str

    class Config:
        from_attributes = True


class QuestionBatchWithQuestions(BaseModel):
    """Batch with full question objects"""
    batch: QuestionBatchSchema
    questions: List[QuestionSchema]


class BatchProcessResponse(BaseModel):
    """Response from batch processing"""
    batches_created: int
    questions_woken: int
    processed_at: str
    error: Optional[str] = None
