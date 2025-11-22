"""
Email API Routes - Phase 5

REST API endpoints for email management and syncing.
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from db.database import get_async_session
from db.models import EmailMessage, EmailThread, EmailAccount, EmailTaskLink
from services.email_polling_service import get_email_polling_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/email", tags=["email"])


# ==============================================================================
# Request/Response Models
# ==============================================================================


class EmailSyncResponse(BaseModel):
    """Response for sync operations."""
    success: bool
    emails_processed: Optional[int] = None
    errors: Optional[List[str]] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None


class EmailStatusResponse(BaseModel):
    """Email polling service status."""
    running: bool
    last_sync_at: Optional[str]
    emails_processed_total: int
    errors_count: int
    poll_interval_minutes: int
    next_sync_in_minutes: Optional[int]


class EmailMessageResponse(BaseModel):
    """Email message details."""
    id: int
    gmail_message_id: str
    thread_id: str
    subject: Optional[str]
    sender: Optional[str]
    sender_name: Optional[str]
    sender_email: Optional[str]
    body_text: Optional[str]
    snippet: Optional[str]
    received_at: Optional[datetime]
    processed_at: Optional[datetime]
    classification: Optional[str]
    classification_confidence: Optional[float]
    task_id: Optional[str]
    is_meeting_invite: bool
    has_attachments: bool
    links: Optional[List[str]]
    action_phrases: Optional[List[str]]


class EmailThreadResponse(BaseModel):
    """Email thread details."""
    id: int
    gmail_thread_id: str
    subject: Optional[str]
    message_count: int
    first_message_at: Optional[datetime]
    last_message_at: Optional[datetime]
    is_consolidated: bool
    consolidated_task_id: Optional[str]
    participant_emails: Optional[List[str]]


# ==============================================================================
# Endpoints
# ==============================================================================


@router.get("/status", response_model=EmailStatusResponse)
async def get_email_status():
    """Get email polling service status.

    Returns current sync status, last sync time, and statistics.
    """
    try:
        polling_service = get_email_polling_service()
        status = await polling_service.get_status()

        return EmailStatusResponse(**status)

    except Exception as e:
        logger.error(f"Failed to get email status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync", response_model=EmailSyncResponse)
async def force_email_sync():
    """Force immediate email sync (bypasses scheduled polling).

    Fetches and processes emails from Gmail immediately.
    """
    try:
        polling_service = get_email_polling_service()
        result = await polling_service.sync_now()

        return EmailSyncResponse(**result)

    except Exception as e:
        logger.error(f"Manual sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent", response_model=List[EmailMessageResponse])
async def get_recent_emails(
    limit: int = Query(50, ge=1, le=200),
    classification: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_session)
):
    """Get recent processed emails.

    Args:
        limit: Maximum number of emails to return (1-200)
        classification: Filter by classification type (optional)
        db: Database session

    Returns:
        List of recent emails
    """
    try:
        # Build query
        query = select(EmailMessage).order_by(desc(EmailMessage.received_at)).limit(limit)

        # Apply classification filter
        if classification:
            query = query.where(EmailMessage.classification == classification)

        # Execute query
        result = await db.execute(query)
        emails = result.scalars().all()

        # Convert to response models
        return [
            EmailMessageResponse(
                id=email.id,
                gmail_message_id=email.gmail_message_id,
                thread_id=email.thread_id,
                subject=email.subject,
                sender=email.sender,
                sender_name=email.sender_name,
                sender_email=email.sender_email,
                body_text=email.body_text,
                snippet=email.snippet,
                received_at=email.received_at,
                processed_at=email.processed_at,
                classification=email.classification,
                classification_confidence=email.classification_confidence,
                task_id=email.task_id,
                is_meeting_invite=email.is_meeting_invite,
                has_attachments=email.has_attachments,
                links=email.links or [],
                action_phrases=email.action_phrases or []
            )
            for email in emails
        ]

    except Exception as e:
        logger.error(f"Failed to get recent emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{email_id}", response_model=EmailMessageResponse)
async def get_email_by_id(
    email_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """Get single email by ID.

    Args:
        email_id: Email ID
        db: Database session

    Returns:
        Email details
    """
    try:
        query = select(EmailMessage).where(EmailMessage.id == email_id)
        result = await db.execute(query)
        email = result.scalar_one_or_none()

        if not email:
            raise HTTPException(status_code=404, detail=f"Email {email_id} not found")

        return EmailMessageResponse(
            id=email.id,
            gmail_message_id=email.gmail_message_id,
            thread_id=email.thread_id,
            subject=email.subject,
            sender=email.sender,
            sender_name=email.sender_name,
            sender_email=email.sender_email,
            body_text=email.body_text,
            snippet=email.snippet,
            received_at=email.received_at,
            processed_at=email.processed_at,
            classification=email.classification,
            classification_confidence=email.classification_confidence,
            task_id=email.task_id,
            is_meeting_invite=email.is_meeting_invite,
            has_attachments=email.has_attachments,
            links=email.links or [],
            action_phrases=email.action_phrases or []
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get email {email_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thread/{thread_id}", response_model=EmailThreadResponse)
async def get_email_thread(
    thread_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """Get email thread by Gmail thread ID.

    Args:
        thread_id: Gmail thread ID
        db: Database session

    Returns:
        Thread details
    """
    try:
        query = select(EmailThread).where(EmailThread.gmail_thread_id == thread_id)
        result = await db.execute(query)
        thread = result.scalar_one_or_none()

        if not thread:
            raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")

        return EmailThreadResponse(
            id=thread.id,
            gmail_thread_id=thread.gmail_thread_id,
            subject=thread.subject,
            message_count=thread.message_count,
            first_message_at=thread.first_message_at,
            last_message_at=thread.last_message_at,
            is_consolidated=thread.is_consolidated,
            consolidated_task_id=thread.consolidated_task_id,
            participant_emails=thread.participant_emails or []
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{email_id}/reprocess")
async def reprocess_email(
    email_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """Reprocess email if classification was wrong.

    Reclassifies the email and updates database.

    Args:
        email_id: Email ID
        db: Database session

    Returns:
        Updated classification
    """
    try:
        # Get email
        query = select(EmailMessage).where(EmailMessage.id == email_id)
        result = await db.execute(query)
        email = result.scalar_one_or_none()

        if not email:
            raise HTTPException(status_code=404, detail=f"Email {email_id} not found")

        # Reclassify
        from agents.email_classification import classify_email_content

        classification_result = await classify_email_content(
            email_id=email.gmail_message_id,
            email_subject=email.subject or "",
            email_sender=email.sender or "",
            email_sender_name=email.sender_name or "",
            email_sender_email=email.sender_email or "",
            email_body=email.body_text or "",
            email_snippet=email.snippet or "",
            action_phrases=email.action_phrases or [],
            is_meeting_invite=email.is_meeting_invite
        )

        # Update classification
        classification = classification_result.get("classification")
        if classification:
            email.classification = classification.action_type
            email.classification_confidence = classification.confidence
            email.processed_at = datetime.utcnow()

            await db.commit()

        return {
            "success": True,
            "email_id": email_id,
            "classification": email.classification,
            "confidence": email.classification_confidence
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reprocess email {email_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
