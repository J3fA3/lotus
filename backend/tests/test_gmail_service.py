"""
Unit tests for Gmail Service - Phase 5

Tests Gmail API operations with mocked API calls.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from googleapiclient.errors import HttpError

from services.gmail_service import GmailService, get_gmail_service


@pytest.fixture
def mock_credentials():
    """Mock Google credentials."""
    creds = Mock()
    creds.token = "mock_access_token"
    creds.refresh_token = "mock_refresh_token"
    creds.expiry = datetime.utcnow() + timedelta(hours=1)
    creds.expired = False
    return creds


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def gmail_service():
    """Create GmailService instance."""
    return GmailService()


@pytest.fixture
def sample_gmail_message():
    """Sample Gmail API message response."""
    return {
        'id': 'msg_123',
        'threadId': 'thread_456',
        'labelIds': ['UNREAD', 'INBOX'],
        'snippet': 'This is a test email...',
        'payload': {
            'headers': [
                {'name': 'From', 'value': 'sender@example.com'},
                {'name': 'To', 'value': 'recipient@example.com'},
                {'name': 'Subject', 'value': 'Test Email Subject'},
                {'name': 'Date', 'value': 'Mon, 18 Nov 2024 10:00:00 +0000'}
            ],
            'body': {
                'data': 'VGhpcyBpcyBhIHRlc3QgZW1haWwgYm9keQ=='  # "This is a test email body" in base64
            }
        }
    }


@pytest.fixture
def sample_multipart_message():
    """Sample multipart Gmail message with HTML."""
    return {
        'id': 'msg_789',
        'threadId': 'thread_012',
        'labelIds': ['UNREAD'],
        'snippet': 'Multipart email...',
        'payload': {
            'headers': [
                {'name': 'From', 'value': 'sender@example.com'},
                {'name': 'Subject', 'value': 'Multipart Test'},
                {'name': 'Date', 'value': 'Mon, 18 Nov 2024 11:00:00 +0000'}
            ],
            'parts': [
                {
                    'mimeType': 'text/plain',
                    'body': {'data': 'UGxhaW4gdGV4dCBib2R5'}  # "Plain text body"
                },
                {
                    'mimeType': 'text/html',
                    'body': {'data': 'PGh0bWw+PGJvZHk+SFRNTCBib2R5PC9ib2R5PjwvaHRtbD4='}  # "<html><body>HTML body</body></html>"
                }
            ]
        }
    }


class TestGmailServiceAuthentication:
    """Test Gmail authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_success(self, gmail_service, mock_db_session, mock_credentials):
        """Test successful authentication."""
        with patch('services.gmail_service.get_oauth_service') as mock_oauth:
            mock_oauth_instance = Mock()
            mock_oauth_instance.get_valid_credentials = AsyncMock(return_value=mock_credentials)
            mock_oauth.return_value = mock_oauth_instance

            with patch('services.gmail_service.build') as mock_build:
                mock_build.return_value = Mock()

                credentials = await gmail_service.authenticate(user_id=1, db=mock_db_session)

                assert credentials == mock_credentials
                assert gmail_service.credentials == mock_credentials
                assert gmail_service.service is not None
                mock_oauth_instance.get_valid_credentials.assert_called_once_with(1, mock_db_session)

    @pytest.mark.asyncio
    async def test_authenticate_without_db(self, gmail_service):
        """Test authentication fails without database session."""
        with pytest.raises(ValueError, match="Database session required"):
            await gmail_service.authenticate(user_id=1, db=None)

    @pytest.mark.asyncio
    async def test_authenticate_oauth_failure(self, gmail_service, mock_db_session):
        """Test authentication handles OAuth failures."""
        with patch('services.gmail_service.get_oauth_service') as mock_oauth:
            mock_oauth_instance = Mock()
            mock_oauth_instance.get_valid_credentials = AsyncMock(
                side_effect=ValueError("No OAuth tokens found")
            )
            mock_oauth.return_value = mock_oauth_instance

            with pytest.raises(ValueError, match="Gmail authentication failed"):
                await gmail_service.authenticate(user_id=1, db=mock_db_session)


class TestGmailServiceEmailFetching:
    """Test email fetching operations."""

    @pytest.mark.asyncio
    async def test_get_recent_emails_success(self, gmail_service, sample_gmail_message):
        """Test fetching recent emails."""
        gmail_service.service = Mock()

        # Mock the list response
        mock_list_response = {
            'messages': [
                {'id': 'msg_123'},
                {'id': 'msg_124'}
            ]
        }

        # Mock the get responses
        mock_get_response = sample_gmail_message

        # Setup mocks
        mock_list_request = Mock()
        mock_list_request.execute = Mock(return_value=mock_list_response)

        mock_get_request = Mock()
        mock_get_request.execute = Mock(return_value=mock_get_response)

        gmail_service.service.users().messages().list.return_value = mock_list_request
        gmail_service.service.users().messages().get.return_value = mock_get_request

        emails = await gmail_service.get_recent_emails(max_results=50)

        assert len(emails) == 2
        assert emails[0]['id'] == 'msg_123'
        assert emails[0]['subject'] == 'Test Email Subject'
        assert emails[0]['sender'] == 'sender@example.com'

    @pytest.mark.asyncio
    async def test_get_recent_emails_empty(self, gmail_service):
        """Test fetching emails when none found."""
        gmail_service.service = Mock()

        mock_list_response = {'messages': []}
        mock_list_request = Mock()
        mock_list_request.execute = Mock(return_value=mock_list_response)

        gmail_service.service.users().messages().list.return_value = mock_list_request

        emails = await gmail_service.get_recent_emails()

        assert emails == []

    @pytest.mark.asyncio
    async def test_get_recent_emails_not_authenticated(self, gmail_service):
        """Test fetching emails without authentication."""
        with pytest.raises(ValueError, match="Not authenticated"):
            await gmail_service.get_recent_emails()

    @pytest.mark.asyncio
    async def test_get_email_by_id_success(self, gmail_service, sample_gmail_message):
        """Test fetching single email by ID."""
        gmail_service.service = Mock()

        mock_get_request = Mock()
        mock_get_request.execute = Mock(return_value=sample_gmail_message)

        gmail_service.service.users().messages().get.return_value = mock_get_request

        email = await gmail_service.get_email_by_id('msg_123')

        assert email['id'] == 'msg_123'
        assert email['subject'] == 'Test Email Subject'
        assert email['thread_id'] == 'thread_456'
        assert 'This is a test email body' in email['body_text']

    @pytest.mark.asyncio
    async def test_get_email_by_id_not_found(self, gmail_service):
        """Test fetching non-existent email."""
        gmail_service.service = Mock()

        mock_error = Mock()
        mock_error.resp.status = 404

        mock_get_request = Mock()
        mock_get_request.execute = Mock(side_effect=HttpError(mock_error, b'Not found'))

        gmail_service.service.users().messages().get.return_value = mock_get_request

        with pytest.raises(ValueError, match="not found"):
            await gmail_service.get_email_by_id('nonexistent')


class TestGmailServiceMessageParsing:
    """Test message parsing logic."""

    def test_parse_simple_message(self, gmail_service, sample_gmail_message):
        """Test parsing simple text message."""
        parsed = gmail_service._parse_message(sample_gmail_message)

        assert parsed['id'] == 'msg_123'
        assert parsed['thread_id'] == 'thread_456'
        assert parsed['subject'] == 'Test Email Subject'
        assert parsed['sender'] == 'sender@example.com'
        assert parsed['to'] == 'recipient@example.com'
        assert 'This is a test email body' in parsed['body_text']
        assert parsed['body_html'] == ''
        assert parsed['has_attachments'] is False

    def test_parse_multipart_message(self, gmail_service, sample_multipart_message):
        """Test parsing multipart message with HTML."""
        parsed = gmail_service._parse_message(sample_multipart_message)

        assert parsed['id'] == 'msg_789'
        assert 'Plain text body' in parsed['body_text']
        assert 'HTML body' in parsed['body_html']

    def test_parse_message_no_subject(self, gmail_service):
        """Test parsing message without subject."""
        message = {
            'id': 'msg_no_subject',
            'threadId': 'thread_001',
            'payload': {
                'headers': [],
                'body': {'data': 'Tm8gc3ViamVjdA=='}  # "No subject"
            }
        }

        parsed = gmail_service._parse_message(message)
        assert parsed['subject'] == '(No Subject)'

    def test_has_attachments_true(self, gmail_service):
        """Test detecting attachments."""
        payload = {
            'parts': [
                {'filename': 'document.pdf', 'mimeType': 'application/pdf'}
            ]
        }

        assert gmail_service._has_attachments(payload) is True

    def test_has_attachments_false(self, gmail_service):
        """Test no attachments."""
        payload = {
            'parts': [
                {'mimeType': 'text/plain', 'body': {'data': 'test'}}
            ]
        }

        assert gmail_service._has_attachments(payload) is False


class TestGmailServiceMarkAsProcessed:
    """Test marking emails as processed."""

    @pytest.mark.asyncio
    async def test_mark_as_processed_existing_label(self, gmail_service):
        """Test marking email as processed with existing label."""
        gmail_service.service = Mock()

        # Mock label list response
        mock_label_response = {
            'labels': [
                {'id': 'Label_1', 'name': 'processed'}
            ]
        }

        mock_label_request = Mock()
        mock_label_request.execute = Mock(return_value=mock_label_response)

        # Mock modify request
        mock_modify_request = Mock()
        mock_modify_request.execute = Mock(return_value={})

        gmail_service.service.users().labels().list.return_value = mock_label_request
        gmail_service.service.users().messages().modify.return_value = mock_modify_request

        result = await gmail_service.mark_as_processed('msg_123')

        assert result is True
        mock_modify_request.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_as_processed_create_label(self, gmail_service):
        """Test marking email as processed - creates label if not exists."""
        gmail_service.service = Mock()

        # Mock label list response (no processed label)
        mock_label_list = {'labels': [{'id': 'Label_1', 'name': 'other'}]}
        mock_label_list_request = Mock()
        mock_label_list_request.execute = Mock(return_value=mock_label_list)

        # Mock label create response
        mock_label_create = {'id': 'Label_2', 'name': 'processed'}
        mock_label_create_request = Mock()
        mock_label_create_request.execute = Mock(return_value=mock_label_create)

        # Mock modify request
        mock_modify_request = Mock()
        mock_modify_request.execute = Mock(return_value={})

        gmail_service.service.users().labels().list.return_value = mock_label_list_request
        gmail_service.service.users().labels().create.return_value = mock_label_create_request
        gmail_service.service.users().messages().modify.return_value = mock_modify_request

        result = await gmail_service.mark_as_processed('msg_123')

        assert result is True
        mock_label_create_request.execute.assert_called_once()
        mock_modify_request.execute.assert_called_once()


class TestGmailServiceErrorHandling:
    """Test error handling and retry logic."""

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self, gmail_service):
        """Test retry on 429 rate limit error."""
        gmail_service.service = Mock()

        mock_error = Mock()
        mock_error.resp.status = 429

        mock_request = Mock()
        # First call fails with 429, second succeeds
        mock_request.execute = Mock(side_effect=[
            HttpError(mock_error, b'Rate limit'),
            {'messages': []}
        ])

        gmail_service.service.users().messages().list.return_value = mock_request

        emails = await gmail_service.get_recent_emails()

        assert emails == []
        assert mock_request.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_server_error(self, gmail_service):
        """Test retry on 500 server error."""
        gmail_service.service = Mock()

        mock_error = Mock()
        mock_error.resp.status = 500

        mock_request = Mock()
        mock_request.execute = Mock(side_effect=[
            HttpError(mock_error, b'Server error'),
            {'messages': []}
        ])

        gmail_service.service.users().messages().list.return_value = mock_request

        emails = await gmail_service.get_recent_emails()

        assert emails == []
        assert mock_request.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_bad_request(self, gmail_service):
        """Test no retry on 400 bad request."""
        gmail_service.service = Mock()

        mock_error = Mock()
        mock_error.resp.status = 400

        mock_request = Mock()
        mock_request.execute = Mock(side_effect=HttpError(mock_error, b'Bad request'))

        gmail_service.service.users().messages().list.return_value = mock_request

        with pytest.raises(HttpError):
            await gmail_service.get_recent_emails()

        assert mock_request.execute.call_count == 1


class TestGmailServiceSingleton:
    """Test singleton pattern."""

    def test_get_gmail_service_singleton(self):
        """Test that get_gmail_service returns same instance."""
        service1 = get_gmail_service()
        service2 = get_gmail_service()

        assert service1 is service2


class TestGmailServiceBase64Decoding:
    """Test base64 decoding utility."""

    def test_decode_base64_success(self, gmail_service):
        """Test successful base64 decoding."""
        encoded = 'VGhpcyBpcyBhIHRlc3Q='  # "This is a test"
        decoded = gmail_service._decode_base64(encoded)
        assert decoded == 'This is a test'

    def test_decode_base64_invalid(self, gmail_service):
        """Test handling of invalid base64."""
        decoded = gmail_service._decode_base64('invalid!!!!')
        assert decoded == ''  # Should return empty string on error
