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

    # Convert to response format
    return [_task_to_schema(task) for task in tasks]


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
    """Update a task"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update fields
    if task_data.title is not None:
        task.title = task_data.title
    if task_data.status is not None:
        task.status = task_data.status
    if task_data.assignee is not None:
        task.assignee = task_data.assignee
    if task_data.startDate is not None:
        task.start_date = task_data.startDate
    if task_data.dueDate is not None:
        task.due_date = task_data.dueDate
    if task_data.valueStream is not None:
        task.value_stream = task_data.valueStream
    if task_data.description is not None:
        task.description = task_data.description

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
            task = Task(
                id=task_data["id"],
                title=task_data["title"],
                status=task_data["status"],
                assignee=task_data["assignee"],
                start_date=task_data.get("startDate"),
                due_date=task_data.get("dueDate"),
                value_stream=task_data.get("valueStream"),
                description=task_data.get("description"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        # Read PDF file
        pdf_bytes = await file.read()

        # Validate PDF
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
            task = Task(
                id=task_data["id"],
                title=task_data["title"],
                status=task_data["status"],
                assignee=task_data["assignee"],
                start_date=task_data.get("startDate"),
                due_date=task_data.get("dueDate"),
                value_stream=task_data.get("valueStream"),
                description=task_data.get("description"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
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
        raise HTTPException(status_code=500, detail=str(e))


# ============= Helper Functions =============

def _task_to_schema(task: Task) -> TaskSchema:
    """Convert SQLAlchemy Task to Pydantic schema"""
    # Safely access relationships - they may not be loaded
    try:
        attachments = [att.url for att in task.attachments] if hasattr(task, 'attachments') and task.attachments else []
    except:
        attachments = []
    
    try:
        comments = [
            CommentSchema(
                id=comment.id,
                text=comment.text,
                author=comment.author,
                createdAt=comment.created_at.isoformat()
            )
            for comment in task.comments
        ] if hasattr(task, 'comments') and task.comments else []
    except:
        comments = []
    
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
        createdAt=task.created_at.isoformat(),
        updatedAt=task.updated_at.isoformat()
    )
