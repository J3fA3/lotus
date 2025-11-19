"""
Email Parser Service - Phase 5

Parses and cleans email content for processing.

Key Features:
1. Parse raw Gmail messages into structured EmailData
2. Clean HTML to plain text (strip signatures, footers)
3. Extract action-indicating phrases
4. Detect meeting invitations
5. Extract links and attachments

Usage:
    parser = EmailParser()

    # Parse email
    email_data = parser.parse_email(gmail_message)

    # Clean HTML
    text = parser.html_to_text(html_content)

    # Extract action phrases
    phrases = parser.extract_action_phrases(text)

    # Detect meeting invitation
    is_invite = parser.detect_meeting_invitation(email_data)
"""

import re
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime

import html2text
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class EmailData:
    """Structured email data after parsing."""
    id: str
    thread_id: str
    subject: str
    sender: str
    sender_name: str
    sender_email: str
    to: str
    cc: str
    bcc: str
    date: str
    received_at: datetime
    body_text: str
    body_html: str
    snippet: str
    labels: List[str]
    has_attachments: bool
    links: List[str]
    action_phrases: List[str]
    is_meeting_invite: bool


class EmailParser:
    """Service for parsing and cleaning email content."""

    def __init__(self):
        """Initialize email parser."""
        # Action-indicating keywords
        self.action_keywords = [
            # Direct requests
            "can you", "could you", "would you", "please", "need you to",
            "need to", "have to", "must", "should", "required",
            # Task verbs
            "review", "check", "approve", "send", "share", "update",
            "complete", "finish", "prepare", "create", "build", "fix",
            "investigate", "look into", "follow up", "get back",
            # Deadlines
            "by", "before", "deadline", "due", "asap", "urgent",
            "today", "tomorrow", "this week", "next week", "friday"
        ]

        # Meeting invitation patterns
        self.meeting_patterns = [
            r"has invited you",
            r"meeting invitation",
            r"calendar invite",
            r"scheduled.*meeting",
            r"join.*call",
            r"zoom meeting",
            r"teams meeting",
            r"google meet",
            r"when:.*where:",
            r"invited to attend"
        ]

        # Email signature patterns (for removal)
        self.signature_patterns = [
            r"--\s*\n",  # Standard signature delimiter
            r"^Sent from",
            r"^Get Outlook for",
            r"^Confidentiality Notice",
            r"^This email",
            r"^DISCLAIMER",
            r"^The information contained",
            r"^\s*Best regards,",
            r"^\s*Regards,",
            r"^\s*Thanks,",
            r"^\s*Cheers,"
        ]

        # HTML to text converter
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
        self.html_converter.ignore_emphasis = False
        self.html_converter.body_width = 0  # No wrapping

        logger.info("Email parser initialized")

    def parse_email(self, gmail_message: Dict[str, Any]) -> EmailData:
        """Parse Gmail message into structured EmailData.

        Args:
            gmail_message: Raw Gmail API message dict

        Returns:
            Structured EmailData object

        Raises:
            ValueError: If required fields missing
        """
        try:
            # Extract headers
            headers = self._extract_headers(gmail_message.get('payload', {}))

            # Extract body
            body_text, body_html = self._extract_body(gmail_message.get('payload', {}))

            # Clean text body
            body_text = self._clean_text(body_text)

            # Parse sender
            sender = headers.get('from', '')
            sender_name, sender_email = self._parse_email_address(sender)

            # Parse date
            date_str = headers.get('date', '')
            received_at = self._parse_date(date_str)

            # Extract links
            links = self._extract_links(body_html or body_text)

            # Extract action phrases
            action_phrases = self.extract_action_phrases(body_text)

            # Build EmailData
            email_data = EmailData(
                id=gmail_message.get('id', ''),
                thread_id=gmail_message.get('threadId', ''),
                subject=headers.get('subject', '(No Subject)'),
                sender=sender,
                sender_name=sender_name,
                sender_email=sender_email,
                to=headers.get('to', ''),
                cc=headers.get('cc', ''),
                bcc=headers.get('bcc', ''),
                date=date_str,
                received_at=received_at,
                body_text=body_text,
                body_html=body_html,
                snippet=gmail_message.get('snippet', ''),
                labels=gmail_message.get('labelIds', []),
                has_attachments=self._has_attachments(gmail_message.get('payload', {})),
                links=links,
                action_phrases=action_phrases,
                is_meeting_invite=False  # Set after detection
            )

            # Detect meeting invitation
            email_data.is_meeting_invite = self.detect_meeting_invitation(email_data)

            logger.debug(f"Parsed email {email_data.id}: {email_data.subject}")
            return email_data

        except Exception as e:
            logger.error(f"Failed to parse email: {e}")
            raise ValueError(f"Email parsing failed: {e}")

    def html_to_text(self, html: str) -> str:
        """Convert HTML email to clean plain text.

        Args:
            html: HTML content

        Returns:
            Plain text (signatures and footers removed)
        """
        if not html:
            return ""

        try:
            # Use html2text for markdown-style conversion
            text = self.html_converter.handle(html)

            # Additional BeautifulSoup cleaning
            soup = BeautifulSoup(html, 'html.parser')

            # Remove script and style elements
            for element in soup(['script', 'style', 'meta', 'link']):
                element.decompose()

            # Get text
            text = soup.get_text(separator='\n', strip=True)

            # Clean up
            text = self._clean_text(text)

            return text

        except Exception as e:
            logger.warning(f"HTML to text conversion failed: {e}")
            return html  # Return original if conversion fails

    def extract_action_phrases(self, text: str) -> List[str]:
        """Extract action-indicating phrases from text.

        Args:
            text: Email text content

        Returns:
            List of sentences/phrases that indicate actions
        """
        if not text:
            return []

        action_phrases = []

        # Split into sentences
        sentences = re.split(r'[.!?]\s+', text)

        # Check each sentence for action keywords
        for sentence in sentences:
            sentence_lower = sentence.lower()

            # Check if sentence contains action keywords
            for keyword in self.action_keywords:
                if keyword in sentence_lower:
                    # Clean and add
                    phrase = sentence.strip()
                    if phrase and len(phrase) > 10:  # Minimum length
                        action_phrases.append(phrase)
                    break

        # Remove duplicates while preserving order
        seen = set()
        unique_phrases = []
        for phrase in action_phrases:
            if phrase not in seen:
                seen.add(phrase)
                unique_phrases.append(phrase)

        return unique_phrases[:10]  # Limit to 10 most relevant

    def detect_meeting_invitation(self, email: EmailData) -> bool:
        """Detect if email is a meeting invitation.

        Args:
            email: Parsed EmailData

        Returns:
            True if email is a meeting invitation
        """
        # Combine text to search
        search_text = f"{email.subject} {email.body_text} {email.snippet}".lower()

        # Check for meeting patterns
        for pattern in self.meeting_patterns:
            if re.search(pattern, search_text, re.IGNORECASE):
                logger.debug(f"Detected meeting invite: {email.subject}")
                return True

        # Check for .ics attachment (calendar file)
        if email.has_attachments:
            # This would need to check attachment names from payload
            # For now, we check body text for calendar references
            if 'calendar' in search_text or '.ics' in search_text:
                return True

        return False

    def _extract_headers(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Extract headers from Gmail payload.

        Args:
            payload: Gmail message payload

        Returns:
            Dict of header name -> value (lowercase names)
        """
        headers = {}
        for header in payload.get('headers', []):
            name = header.get('name', '').lower()
            value = header.get('value', '')
            headers[name] = value
        return headers

    def _extract_body(self, payload: Dict[str, Any]) -> tuple[str, str]:
        """Extract text and HTML body from payload.

        Args:
            payload: Gmail message payload

        Returns:
            Tuple of (text_body, html_body)
        """
        text_body = ""
        html_body = ""

        # Check if multipart
        if 'parts' in payload:
            text_body, html_body = self._extract_multipart_body(payload['parts'])
        elif 'body' in payload and 'data' in payload['body']:
            # Simple message
            mime_type = payload.get('mimeType', '')
            data = payload['body']['data']
            decoded = self._decode_base64(data)

            if 'text/html' in mime_type:
                html_body = decoded
                text_body = self.html_to_text(decoded)
            else:
                text_body = decoded

        return text_body, html_body

    def _extract_multipart_body(self, parts: List[Dict[str, Any]]) -> tuple[str, str]:
        """Extract body from multipart message.

        Args:
            parts: List of message parts

        Returns:
            Tuple of (text_body, html_body)
        """
        text_body = ""
        html_body = ""

        for part in parts:
            mime_type = part.get('mimeType', '')

            # Recursive for nested parts
            if 'parts' in part:
                nested_text, nested_html = self._extract_multipart_body(part['parts'])
                text_body += nested_text
                html_body += nested_html
                continue

            # Extract body data
            if 'body' not in part or 'data' not in part['body']:
                continue

            data = part['body']['data']
            decoded = self._decode_base64(data)

            if 'text/plain' in mime_type:
                text_body += decoded + "\n"
            elif 'text/html' in mime_type:
                html_body += decoded + "\n"

        return text_body.strip(), html_body.strip()

    def _decode_base64(self, data: str) -> str:
        """Decode base64url encoded string.

        Args:
            data: Base64url encoded string

        Returns:
            Decoded string
        """
        try:
            import base64
            decoded_bytes = base64.urlsafe_b64decode(data.encode('ASCII'))
            return decoded_bytes.decode('utf-8', errors='replace')
        except Exception as e:
            logger.warning(f"Failed to decode base64: {e}")
            return ""

    def _clean_text(self, text: str) -> str:
        """Clean text by removing signatures, extra whitespace, etc.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove email signatures
        for pattern in self.signature_patterns:
            # Split on signature and take first part
            parts = re.split(pattern, text, flags=re.MULTILINE | re.IGNORECASE)
            if len(parts) > 1:
                text = parts[0]
                break

        # Remove multiple blank lines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        # Remove leading/trailing whitespace
        text = text.strip()

        # Remove common email headers/footers
        text = re.sub(r'^On.*wrote:$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^>+.*$', '', text, flags=re.MULTILINE)  # Quoted text

        return text

    def _parse_email_address(self, address: str) -> tuple[str, str]:
        """Parse email address into name and email.

        Args:
            address: Email address like "John Doe <john@example.com>"

        Returns:
            Tuple of (name, email)
        """
        if not address:
            return "", ""

        # Pattern: "Name <email>" or just "email"
        match = re.match(r'^"?([^"<]+)"?\s*<(.+)>$', address.strip())
        if match:
            name = match.group(1).strip()
            email = match.group(2).strip()
            return name, email

        # Just email address
        if '@' in address:
            return "", address.strip()

        return address.strip(), ""

    def _parse_date(self, date_str: str) -> datetime:
        """Parse email date string to datetime.

        Args:
            date_str: Email date string

        Returns:
            Parsed datetime (or current time if parse fails)
        """
        if not date_str:
            return datetime.utcnow()

        try:
            return parsedate_to_datetime(date_str)
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return datetime.utcnow()

    def _extract_links(self, text: str) -> List[str]:
        """Extract URLs from text.

        Args:
            text: Text or HTML content

        Returns:
            List of URLs
        """
        if not text:
            return []

        # URL pattern
        url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'

        urls = re.findall(url_pattern, text)

        # Clean and deduplicate
        clean_urls = []
        seen = set()

        for url in urls:
            # Remove trailing punctuation
            url = re.sub(r'[.,;:!?]+$', '', url)

            if url not in seen and len(url) > 10:
                seen.add(url)
                clean_urls.append(url)

        return clean_urls[:20]  # Limit to 20 URLs

    def _has_attachments(self, payload: Dict[str, Any]) -> bool:
        """Check if message has attachments.

        Args:
            payload: Message payload

        Returns:
            True if has attachments
        """
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('filename'):
                    return True
                if 'parts' in part:
                    if self._has_attachments(part):
                        return True
        return False


# Singleton instance
_email_parser = None


def get_email_parser() -> EmailParser:
    """Get singleton EmailParser instance.

    Returns:
        EmailParser instance
    """
    global _email_parser
    if _email_parser is None:
        _email_parser = EmailParser()
    return _email_parser
