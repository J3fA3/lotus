"""
API routes for task management and AI inference
"""
import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime

from api.schemas import (
    TaskSchema,
    TaskCreateRequest,
    TaskUpdateRequest,
    InferenceRequest,
    InferenceResponse,
    HealthResponse,
    CommentSchema
)
from db.database import get_db
from db.models import Task, Comment, Attachment, InferenceHistory
from agents.task_extractor import TaskExtractor
from agents.pdf_processor import PDFProcessor

router = APIRouter()

# Initialize AI components
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")

task_extractor = TaskExtractor(OLLAMA_BASE_URL, OLLAMA_MODEL)
pdf_processor = PDFProcessor()


# ============= Health Check =============

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API, Ollama, and database health"""
    ollama_connected = await task_extractor.check_connection()

    return HealthResponse(
        status="healthy",
        ollama_connected=ollama_connected,
        database_connected=True,
        model=OLLAMA_MODEL
    )


# ============= Task CRUD =============

@router.get("/tasks", response_model=List[TaskSchema])
async def get_tasks(db: AsyncSession = Depends(get_db)):
    """Get all tasks"""
    result = await db.execute(select(Task))
    tasks = result.scalars().all()

    # Convert to response format - relationships not loaded, will return empty arrays
    return [_task_to_schema(task, load_relationships=False) for task in tasks]


@router.post("/tasks", response_model=TaskSchema)
async def create_task(
    task_data: TaskCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new task"""
    task_id = str(uuid.uuid4())
    now = datetime.utcnow()

    task = Task(
        id=task_id,
        title=task_data.title,
        status=task_data.status,
        assignee=task_data.assignee,
        start_date=task_data.startDate,
        due_date=task_data.dueDate,
        value_stream=task_data.valueStream,
        description=task_data.description,
        created_at=now,
        updated_at=now
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    return _task_to_schema(task)


@router.get("/tasks/{task_id}", response_model=TaskSchema)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific task"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return _task_to_schema(task)


@router.put("/tasks/{task_id}", response_model=TaskSchema)
async def update_task(
    task_id: str,
    task_data: TaskUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update a task with provided fields"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update only provided fields
    update_data = task_data.model_dump(exclude_unset=True)
    field_mapping = {
        "title": "title",
        "status": "status",
        "assignee": "assignee",
        "startDate": "start_date",
        "dueDate": "due_date",
        "valueStream": "value_stream",
        "description": "description"
    }
    
    for api_field, db_field in field_mapping.items():
        if api_field in update_data:
            setattr(task, db_field, update_data[api_field])

    task.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(task)

    return _task_to_schema(task)


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a task"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.commit()

    return {"message": "Task deleted successfully"}


# ============= AI Task Inference =============

@router.post("/infer-tasks", response_model=InferenceResponse)
async def infer_tasks_from_text(
    request: InferenceRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Infer tasks from text using AI
    """
    try:
        # Extract tasks using AI
        result = await task_extractor.extract_tasks(
            request.text,
            request.assignee
        )

        # Save tasks to database
        saved_tasks = []
        for task_data in result["tasks"]:
            task = _create_task_from_data(task_data)
            db.add(task)
            saved_tasks.append(task)

        # Save inference history
        history = InferenceHistory(
            input_text=request.text[:1000],  # Limit stored text
            input_type="text",
            tasks_inferred=len(saved_tasks),
            model_used=result["model_used"],
            inference_time=result["inference_time_ms"]
        )
        db.add(history)

        await db.commit()

        # Refresh all tasks
        for task in saved_tasks:
            await db.refresh(task)

        return InferenceResponse(
            tasks=[_task_to_schema(task) for task in saved_tasks],
            inference_time_ms=result["inference_time_ms"],
            model_used=result["model_used"],
            tasks_inferred=len(saved_tasks)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task inference failed: {str(e)}")


@router.post("/infer-tasks-pdf", response_model=InferenceResponse)
async def infer_tasks_from_pdf(
    file: UploadFile = File(...),
    assignee: str = Form("You"),
    db: AsyncSession = Depends(get_db)
):
    """
    Infer tasks from PDF file
    """
    try:
        # Read and validate PDF file
        pdf_bytes = await file.read()

        if not pdf_processor.validate_pdf(pdf_bytes):
            raise HTTPException(status_code=400, detail="Invalid PDF file")

        # Extract text from PDF
        extracted_text = await pdf_processor.extract_text_from_pdf(pdf_bytes)

        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="No text found in PDF")

        # Extract tasks using AI
        result = await task_extractor.extract_tasks(extracted_text, assignee)

        # Save tasks to database
        saved_tasks = []
        for task_data in result["tasks"]:
            task = _create_task_from_data(task_data)
            db.add(task)
            saved_tasks.append(task)

        # Save inference history
        history = InferenceHistory(
            input_text=extracted_text[:1000],
            input_type="pdf",
            tasks_inferred=len(saved_tasks),
            model_used=result["model_used"],
            inference_time=result["inference_time_ms"]
        )
        db.add(history)

        await db.commit()

        # Refresh all tasks
        for task in saved_tasks:
            await db.refresh(task)

        return InferenceResponse(
            tasks=[_task_to_schema(task) for task in saved_tasks],
            inference_time_ms=result["inference_time_ms"],
            model_used=result["model_used"],
            tasks_inferred=len(saved_tasks)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")


# ============= Helper Functions =============

def _task_to_schema(task: Task, load_relationships: bool = False) -> TaskSchema:
    """Convert SQLAlchemy Task to Pydantic schema with safe relationship access
    
    Args:
        task: Task model instance
        load_relationships: Whether to attempt loading relationships (requires proper async context)
    """
    # Don't try to access relationships in async context - they cause greenlet errors
    # Relationships would need to be eager-loaded in the query
    attachments = []
    comments = []
    
    # Handle potential None values for timestamps
    created_at = task.created_at if task.created_at else datetime.utcnow()
    updated_at = task.updated_at if task.updated_at else datetime.utcnow()
    
    return TaskSchema(
        id=task.id,
        title=task.title,
        status=task.status,
        assignee=task.assignee,
        startDate=task.start_date,
        dueDate=task.due_date,
        valueStream=task.value_stream,
        description=task.description,
        attachments=attachments,
        comments=comments,
        createdAt=created_at.isoformat(),
        updatedAt=updated_at.isoformat()
    )


def _create_task_from_data(task_data: dict) -> Task:
    """Create a Task model instance from dictionary data"""
    now = datetime.utcnow()
    return Task(
        id=task_data["id"],
        title=task_data["title"],
        status=task_data["status"],
        assignee=task_data["assignee"],
        start_date=task_data.get("startDate"),
        due_date=task_data.get("dueDate"),
        value_stream=task_data.get("valueStream"),
        description=task_data.get("description"),
        created_at=now,
        updated_at=now
    )
