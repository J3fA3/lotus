"""
Gmail Service - Phase 5

Handles Gmail API operations for email ingestion and processing.

Key Features:
1. OAuth authentication using shared GoogleOAuthService
2. Fetch recent unread emails with pagination
3. Fetch individual emails with full content
4. Mark emails as processed using labels
5. Robust error handling (401, 429, 500+)

Usage:
    gmail = GmailService()

    # Authenticate (uses existing OAuth tokens)
    credentials = await gmail.authenticate(user_id=1, db)

    # Fetch recent emails
    emails = await gmail.get_recent_emails(max_results=50)

    # Get single email
    email = await gmail.get_email_by_id('msg_123')

    # Mark as processed
    await gmail.mark_as_processed('msg_123')
"""

import os
import logging
import asyncio
import base64
from typing import List, Dict, Optional, Any
from datetime import datetime
from email.utils import parsedate_to_datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.ext.asyncio import AsyncSession

from services.google_oauth import get_oauth_service

logger = logging.getLogger(__name__)


class GmailService:
    """Service for Gmail API operations."""

    def __init__(self):
        """Initialize Gmail service with environment configuration."""
        self.credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH", "gmail_credentials.json")
        self.token_path = os.getenv("GMAIL_TOKEN_PATH", "gmail_token.json")
        self.max_results = int(os.getenv("GMAIL_MAX_RESULTS", "50"))
        # SSL/Network optimization settings
        self.batch_size = int(os.getenv("GMAIL_BATCH_SIZE", "3"))
        self.batch_delay = float(os.getenv("GMAIL_BATCH_DELAY_SECONDS", "0.5"))
        self.fetch_delay = float(os.getenv("GMAIL_FETCH_DELAY_SECONDS", "0.2"))
        self.sequential_processing = os.getenv("GMAIL_SEQUENTIAL_PROCESSING", "false").lower() == "true"

        self.oauth_service = get_oauth_service()
        self.service = None
        self.credentials = None

        logger.info(f"Gmail service initialized (batch_size={self.batch_size}, sequential={self.sequential_processing})")

    async def authenticate(self, user_id: int = 1, db: Optional[AsyncSession] = None) -> Credentials:
        """Authenticate with Gmail API using OAuth tokens.

        Args:
            user_id: User ID to get credentials for
            db: Database session (required for token refresh)

        Returns:
            Google Credentials object

        Raises:
            ValueError: If no credentials available or authentication fails
        """
        if not db:
            raise ValueError("Database session required for Gmail authentication")

        try:
            # Get valid credentials (will refresh if expired)
            self.credentials = await self.oauth_service.get_valid_credentials(user_id, db)

            # Build Gmail service
            self.service = build('gmail', 'v1', credentials=self.credentials)

            logger.info(f"Gmail authenticated successfully for user {user_id}")
            return self.credentials

        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            raise ValueError(f"Gmail authentication failed: {e}")

    async def get_recent_emails(
        self,
        max_results: Optional[int] = None,
        query: str = "in:inbox",  # Changed from "is:unread" to get ALL inbox emails
        user_id: str = "me"
    ) -> List[Dict[str, Any]]:
        """Fetch recent emails matching query.

        Args:
            max_results: Maximum number of emails to fetch (default from env)
            query: Gmail search query (default: "in:inbox" - all inbox emails)
            user_id: Gmail user ID (default: "me")

        Returns:
            List of email dictionaries with message details

        Raises:
            ValueError: If not authenticated
            HttpError: For Gmail API errors (handled with retries)
        """
        if not self.service:
            raise ValueError("Not authenticated. Call authenticate() first.")

        max_results = max_results or self.max_results

        try:
            # List messages matching query
            logger.info(f"Fetching emails with query: '{query}', max_results: {max_results}")

            response = await self._execute_with_retry(
                self.service.users().messages().list(
                    userId=user_id,
                    q=query,
                    maxResults=max_results
                )
            )

            messages = response.get('messages', [])

            if not messages:
                logger.info("No emails found matching query")
                return []

            logger.info(f"Found {len(messages)} emails, fetching full details...")

            # Fetch full details for each message (in parallel batches)
            emails = await self._fetch_messages_batch(messages, user_id)

            logger.info(f"Successfully fetched {len(emails)} emails")
            return emails

        except HttpError as e:
            logger.error(f"Gmail API error in get_recent_emails: {e}")
            raise

    async def get_email_by_id(self, email_id: str, user_id: str = "me") -> Dict[str, Any]:
        """Fetch single email by ID with full content.

        Args:
            email_id: Gmail message ID
            user_id: Gmail user ID (default: "me")

        Returns:
            Email dictionary with full details

        Raises:
            ValueError: If not authenticated or email not found
            HttpError: For Gmail API errors
        """
        if not self.service:
            raise ValueError("Not authenticated. Call authenticate() first.")

        try:
            logger.info(f"Fetching email {email_id}")

            message = await self._execute_with_retry(
                self.service.users().messages().get(
                    userId=user_id,
                    id=email_id,
                    format='full'
                )
            )

            email_data = self._parse_message(message)
            logger.info(f"Successfully fetched email {email_id}")
            return email_data

        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"Email {email_id} not found")
            logger.error(f"Gmail API error in get_email_by_id: {e}")
            raise

    async def mark_as_processed(self, email_id: str, user_id: str = "me") -> bool:
        """Mark email as processed by adding 'processed' label.

        Creates the label if it doesn't exist.

        Args:
            email_id: Gmail message ID
            user_id: Gmail user ID (default: "me")

        Returns:
            True if successful

        Raises:
            ValueError: If not authenticated
            HttpError: For Gmail API errors
        """
        if not self.service:
            raise ValueError("Not authenticated. Call authenticate() first.")

        try:
            # Get or create 'processed' label
            label_id = await self._get_or_create_label("processed", user_id)

            # Add label to message
            logger.info(f"Marking email {email_id} as processed")

            await self._execute_with_retry(
                self.service.users().messages().modify(
                    userId=user_id,
                    id=email_id,
                    body={'addLabelIds': [label_id]}
                )
            )

            logger.info(f"Email {email_id} marked as processed")
            return True

        except HttpError as e:
            logger.error(f"Failed to mark email {email_id} as processed: {e}")
            raise

    async def _fetch_messages_batch(
        self,
        message_refs: List[Dict[str, str]],
        user_id: str,
        batch_size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch full message details in parallel batches or sequentially.

        Args:
            message_refs: List of message references with 'id'
            user_id: Gmail user ID
            batch_size: Number of messages to fetch in parallel (uses instance default if None)

        Returns:
            List of parsed email dictionaries
        """
        emails = []
        batch_size = batch_size or self.batch_size

        # Sequential processing (most reliable, slower)
        if self.sequential_processing:
            logger.info(f"Processing {len(message_refs)} messages sequentially")
            for msg in message_refs:
                if self.fetch_delay > 0:
                    await asyncio.sleep(self.fetch_delay)
                result = await self._fetch_single_message(msg['id'], user_id)
                if result:
                    emails.append(result)
            return emails

        # Parallel batch processing (faster, more SSL connections)
        logger.info(f"Processing {len(message_refs)} messages in batches of {batch_size}")
        for i in range(0, len(message_refs), batch_size):
            batch = message_refs[i:i + batch_size]

            # Fetch batch in parallel
            tasks = [
                self._fetch_single_message(msg['id'], user_id)
                for msg in batch
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.warning(f"Failed to fetch message in batch: {result}")
                elif result:
                    emails.append(result)

            # Delay between batches to allow SSL connections to stabilize
            if i + batch_size < len(message_refs) and self.batch_delay > 0:
                await asyncio.sleep(self.batch_delay)

        return emails

    async def _fetch_single_message(self, message_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch single message with error handling.

        Args:
            message_id: Gmail message ID
            user_id: Gmail user ID

        Returns:
            Parsed email dictionary or None if error
        """
        try:
            message = await self._execute_with_retry(
                self.service.users().messages().get(
                    userId=user_id,
                    id=message_id,
                    format='full'
                )
            )
            return self._parse_message(message)
        except Exception as e:
            logger.error(f"Failed to fetch message {message_id}: {e}")
            return None

    def _parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gmail message into structured format.

        Args:
            message: Raw Gmail message object

        Returns:
            Structured email dictionary
        """
        headers = {h['name'].lower(): h['value'] for h in message['payload'].get('headers', [])}

        # Extract body
        body_text = ""
        body_html = ""

        if 'parts' in message['payload']:
            # Multipart message
            for part in message['payload']['parts']:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain' and 'data' in part.get('body', {}):
                    body_text = self._decode_base64(part['body']['data'])
                elif mime_type == 'text/html' and 'data' in part.get('body', {}):
                    body_html = self._decode_base64(part['body']['data'])
        elif 'body' in message['payload'] and 'data' in message['payload']['body']:
            # Simple message
            body_text = self._decode_base64(message['payload']['body']['data'])

        # Parse date
        date_str = headers.get('date', '')
        try:
            received_at = parsedate_to_datetime(date_str) if date_str else datetime.utcnow()
        except Exception:
            received_at = datetime.utcnow()

        return {
            'id': message['id'],
            'thread_id': message.get('threadId'),
            'subject': headers.get('subject', '(No Subject)'),
            'sender': headers.get('from', ''),
            'to': headers.get('to', ''),
            'cc': headers.get('cc', ''),
            'bcc': headers.get('bcc', ''),
            'date': date_str,
            'received_at': received_at,
            'body_text': body_text,
            'body_html': body_html,
            'snippet': message.get('snippet', ''),
            'labels': message.get('labelIds', []),
            'has_attachments': self._has_attachments(message['payload'])
        }

    def _decode_base64(self, data: str) -> str:
        """Decode base64url encoded string.

        Args:
            data: Base64url encoded string

        Returns:
            Decoded string
        """
        try:
            # Gmail uses base64url encoding
            decoded_bytes = base64.urlsafe_b64decode(data.encode('ASCII'))
            return decoded_bytes.decode('utf-8', errors='replace')
        except Exception as e:
            logger.warning(f"Failed to decode base64 data: {e}")
            return ""

    def _has_attachments(self, payload: Dict[str, Any]) -> bool:
        """Check if message has attachments.

        Args:
            payload: Message payload

        Returns:
            True if message has attachments
        """
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('filename'):
                    return True
                if 'parts' in part:
                    if self._has_attachments(part):
                        return True
        return False

    async def _get_or_create_label(self, label_name: str, user_id: str) -> str:
        """Get or create Gmail label.

        Args:
            label_name: Label name to get or create
            user_id: Gmail user ID

        Returns:
            Label ID
        """
        try:
            # List all labels
            response = await self._execute_with_retry(
                self.service.users().labels().list(userId=user_id)
            )

            labels = response.get('labels', [])

            # Check if label exists
            for label in labels:
                if label['name'].lower() == label_name.lower():
                    return label['id']

            # Create label if not found
            logger.info(f"Creating label '{label_name}'")
            label_object = {
                'name': label_name,
                'messageListVisibility': 'show',
                'labelListVisibility': 'labelShow'
            }

            created_label = await self._execute_with_retry(
                self.service.users().labels().create(
                    userId=user_id,
                    body=label_object
                )
            )

            return created_label['id']

        except Exception as e:
            logger.error(f"Failed to get or create label '{label_name}': {e}")
            raise

    async def _execute_with_retry(
        self,
        request,
        max_retries: int = 5,  # Increased from 3
        base_delay: float = 2.0,  # Increased from 1.0
        timeout: float = 60.0  # Add explicit timeout
    ) -> Any:
        """Execute Gmail API request with exponential backoff retry.

        Handles:
        - 401 (token refresh handled by OAuth service)
        - 429 (rate limit - retry with backoff)
        - 500+ (server errors - retry with backoff)
        - SSL errors (retry with backoff)
        - Timeout errors (retry with backoff)

        Args:
            request: Gmail API request object
            max_retries: Maximum number of retries
            base_delay: Base delay in seconds for exponential backoff
            timeout: Timeout in seconds for each request

        Returns:
            API response

        Raises:
            HttpError: If all retries fail
        """
        import socket
        import ssl
        
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                # Execute request in thread pool (API calls are blocking)
                loop = asyncio.get_event_loop()
                
                # Set socket timeout
                socket.setdefaulttimeout(timeout)
                
                response = await loop.run_in_executor(None, request.execute)
                return response

            except (ssl.SSLError, socket.timeout, ConnectionError, OSError) as e:
                # Network/SSL errors - always retry
                last_error = e
                error_type = type(e).__name__
                
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Network error ({error_type}), retrying in {delay}s "
                        f"(attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"Network error ({error_type}) after {max_retries} retries: {e}")
                    raise ValueError(f"Gmail API network error after {max_retries} retries: {e}")

            except HttpError as e:
                last_error = e
                status = e.resp.status

                # Don't retry these errors
                if status in [400, 403, 404]:
                    logger.error(f"Non-retryable Gmail API error {status}: {e}")
                    raise

                # Retry these errors with backoff
                if status in [401, 429, 500, 502, 503, 504]:
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"Gmail API error {status}, retrying in {delay}s "
                            f"(attempt {attempt + 1}/{max_retries}): {e}"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(f"Gmail API error {status} after {max_retries} retries: {e}")
                        raise

                # Unknown error
                logger.error(f"Unexpected Gmail API error {status}: {e}")
                raise

            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error in Gmail API request: {e}")
                
                # Retry on unexpected errors
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Retrying after unexpected error in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise

        # All retries exhausted
        if last_error:
            raise last_error
        raise RuntimeError("Gmail API request failed after all retries")


# Singleton instance
_gmail_service = None


def get_gmail_service() -> GmailService:
    """Get singleton Gmail service instance.

    Returns:
        GmailService instance
    """
    global _gmail_service
    if _gmail_service is None:
        _gmail_service = GmailService()
    return _gmail_service
