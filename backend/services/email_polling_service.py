"""
Email Polling Background Service - Phase 5

Polls Gmail for new emails at configured intervals.

Runs as asyncio background task with graceful shutdown.
Processes emails in batches with error handling and retries.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from services.gmail_service import get_gmail_service
from services.email_parser import get_email_parser
from agents.email_classification import classify_email_content
from db.database import get_async_session
from db.models import EmailAccount, EmailMessage

logger = logging.getLogger(__name__)


class EmailPollingService:
    """Background service for polling Gmail and processing emails."""

    def __init__(self):
        """Initialize email polling service."""
        self.poll_interval_minutes = int(os.getenv("GMAIL_POLL_INTERVAL_MINUTES", "20"))
        self.max_results = int(os.getenv("GMAIL_MAX_RESULTS", "50"))

        self.gmail_service = None
        self.email_parser = None

        self._running = False
        self._task = None

        # Status tracking
        self.last_sync_at = None
        self.emails_processed = 0
        self.errors_count = 0

        logger.info(f"Email polling service initialized (interval={self.poll_interval_minutes}min)")

    async def start(self):
        """Start polling loop in background."""
        if self._running:
            logger.warning("Email polling already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._polling_loop())

        logger.info(f"Email polling started (every {self.poll_interval_minutes} minutes)")

    async def stop(self):
        """Stop polling loop gracefully."""
        if not self._running:
            return

        logger.info("Stopping email polling service...")
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Email polling stopped")

    async def sync_now(self) -> Dict[str, Any]:
        """Force immediate sync (bypassing scheduled polling).

        Returns:
            Dict with sync results
        """
        logger.info("Manual sync triggered")

        try:
            result = await self._sync_emails()
            return {
                "success": True,
                "emails_processed": result["emails_processed"],
                "errors": result["errors"],
                "duration_ms": result["duration_ms"]
            }
        except Exception as e:
            logger.error(f"Manual sync failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_status(self) -> Dict[str, Any]:
        """Get polling service status.

        Returns:
            Dict with status info
        """
        return {
            "running": self._running,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "emails_processed_total": self.emails_processed,
            "errors_count": self.errors_count,
            "poll_interval_minutes": self.poll_interval_minutes,
            "next_sync_in_minutes": self._get_next_sync_in_minutes()
        }

    async def _polling_loop(self):
        """Main polling loop."""
        while self._running:
            try:
                # Perform sync
                await self._sync_emails()

                # Wait for next interval
                await asyncio.sleep(self.poll_interval_minutes * 60)

            except asyncio.CancelledError:
                # Graceful shutdown
                break

            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                self.errors_count += 1

                # Wait before retry (shorter interval on error)
                await asyncio.sleep(60)  # 1 minute retry interval

    async def _sync_emails(self) -> Dict[str, Any]:
        """Sync emails from Gmail.

        Returns:
            Dict with sync results
        """
        start_time = datetime.utcnow()

        logger.info("Starting email sync...")

        try:
            # Initialize services if needed
            if not self.gmail_service:
                self.gmail_service = get_gmail_service()

            if not self.email_parser:
                self.email_parser = get_email_parser()

            # Get database session
            async with get_async_session() as db:
                # Authenticate Gmail
                await self.gmail_service.authenticate(user_id=1, db=db)

                # Fetch unread/unprocessed emails
                query = "is:unread -label:processed"
                gmail_messages = await self.gmail_service.get_recent_emails(
                    max_results=self.max_results,
                    query=query
                )

                logger.info(f"Found {len(gmail_messages)} emails to process")

                # Process emails in batches
                emails_processed = 0
                errors = []

                for gmail_msg in gmail_messages:
                    try:
                        # Parse email
                        email_data = self.email_parser.parse_email(gmail_msg)

                        # Classify email
                        classification_result = await classify_email_content(
                            email_id=email_data.id,
                            email_subject=email_data.subject,
                            email_sender=email_data.sender,
                            email_sender_name=email_data.sender_name,
                            email_sender_email=email_data.sender_email,
                            email_body=email_data.body_text,
                            email_snippet=email_data.snippet,
                            action_phrases=email_data.action_phrases,
                            is_meeting_invite=email_data.is_meeting_invite
                        )

                        # Store in database
                        await self._store_email(db, email_data, classification_result)

                        # Mark as processed in Gmail
                        await self.gmail_service.mark_as_processed(email_data.id)

                        emails_processed += 1

                    except Exception as e:
                        logger.error(f"Failed to process email {gmail_msg.get('id', 'unknown')}: {e}")
                        errors.append(str(e))

                # Update tracking
                self.last_sync_at = datetime.utcnow()
                self.emails_processed += emails_processed

                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                logger.info(
                    f"Email sync complete: {emails_processed} processed, "
                    f"{len(errors)} errors, {duration_ms}ms"
                )

                return {
                    "emails_processed": emails_processed,
                    "errors": errors,
                    "duration_ms": duration_ms
                }

        except Exception as e:
            logger.error(f"Email sync failed: {e}")
            self.errors_count += 1
            raise

    async def _store_email(
        self,
        db: AsyncSession,
        email_data,
        classification_result: Dict[str, Any]
    ):
        """Store email in database.

        Args:
            db: Database session
            email_data: Parsed email data
            classification_result: Classification result from agent
        """
        # Get or create email account
        from sqlalchemy import select

        account_query = select(EmailAccount).where(
            EmailAccount.email_address == email_data.to or email_data.recipient_to
        )
        result = await db.execute(account_query)
        account = result.scalar_one_or_none()

        if not account:
            # Create default account (this would normally be done during OAuth setup)
            account = EmailAccount(
                user_id=1,
                email_address=email_data.to or "default@example.com",
                provider="gmail",
                sync_enabled=True
            )
            db.add(account)
            await db.flush()

        # Create email message record
        classification = classification_result.get("classification")

        email_message = EmailMessage(
            gmail_message_id=email_data.id,
            thread_id=email_data.thread_id,
            account_id=account.id,
            subject=email_data.subject,
            sender=email_data.sender,
            sender_name=email_data.sender_name,
            sender_email=email_data.sender_email,
            recipient_to=email_data.to,
            recipient_cc=email_data.cc,
            recipient_bcc=email_data.bcc,
            body_text=email_data.body_text,
            body_html=email_data.body_html,
            snippet=email_data.snippet,
            labels=email_data.labels,
            has_attachments=email_data.has_attachments,
            links=email_data.links,
            action_phrases=email_data.action_phrases,
            is_meeting_invite=email_data.is_meeting_invite,
            received_at=email_data.received_at,
            processed_at=datetime.utcnow(),
            classification=classification.action_type if classification else "unprocessed",
            classification_confidence=classification.confidence if classification else 0.0
        )

        db.add(email_message)
        await db.commit()

        logger.debug(f"Email {email_data.id} stored in database")

    def _get_next_sync_in_minutes(self) -> Optional[int]:
        """Calculate minutes until next sync.

        Returns:
            Minutes until next sync or None if not running
        """
        if not self._running or not self.last_sync_at:
            return None

        next_sync = self.last_sync_at + timedelta(minutes=self.poll_interval_minutes)
        delta = next_sync - datetime.utcnow()

        minutes = int(delta.total_seconds() / 60)
        return max(0, minutes)


# Singleton instance
_polling_service = None


def get_email_polling_service() -> EmailPollingService:
    """Get singleton EmailPollingService instance.

    Returns:
        EmailPollingService instance
    """
    global _polling_service
    if _polling_service is None:
        _polling_service = EmailPollingService()
    return _polling_service
