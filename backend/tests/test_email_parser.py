"""
Unit tests for Email Parser Service - Phase 5

Tests email parsing, cleaning, and content extraction.
"""

import pytest
from datetime import datetime

from services.email_parser import EmailParser, EmailData, get_email_parser


@pytest.fixture
def parser():
    """Create EmailParser instance."""
    return EmailParser()


@pytest.fixture
def simple_gmail_message():
    """Simple plain text email."""
    return {
        'id': 'msg_simple',
        'threadId': 'thread_001',
        'labelIds': ['UNREAD', 'INBOX'],
        'snippet': 'Can you review the CRESCO document...',
        'payload': {
            'mimeType': 'text/plain',
            'headers': [
                {'name': 'From', 'value': 'Jef Adriaenssens <jef@example.com>'},
                {'name': 'To', 'value': 'recipient@example.com'},
                {'name': 'Subject', 'value': 'CRESCO Document Review'},
                {'name': 'Date', 'value': 'Mon, 18 Nov 2024 10:00:00 +0000'}
            ],
            'body': {
                'data': 'Q2FuIHlvdSByZXZpZXcgdGhlIENSRVNDTyBkb2N1bWVudCBieSBGcmlkYXk/'
                # "Can you review the CRESCO document by Friday?"
            }
        }
    }


@pytest.fixture
def multipart_gmail_message():
    """Multipart email with HTML and text."""
    return {
        'id': 'msg_multi',
        'threadId': 'thread_002',
        'labelIds': ['INBOX'],
        'snippet': 'Meeting invitation...',
        'payload': {
            'mimeType': 'multipart/alternative',
            'headers': [
                {'name': 'From', 'value': 'Alberto <alberto@spain.com>'},
                {'name': 'Subject', 'value': 'Meeting: Spain Pharmacy Pinning'},
                {'name': 'Date', 'value': 'Tue, 19 Nov 2024 14:00:00 +0000'}
            ],
            'parts': [
                {
                    'mimeType': 'text/plain',
                    'body': {
                        'data': 'UGxlYXNlIGpvaW4gdGhlIG1lZXRpbmcgdG9kYXkgYXQgMnBtLg=='
                        # "Please join the meeting today at 2pm."
                    }
                },
                {
                    'mimeType': 'text/html',
                    'body': {
                        'data': 'PGh0bWw+PGJvZHk+PHA+UGxlYXNlIDxiPmpvaW48L2I+IHRoZSBtZWV0aW5nIHRvZGF5IGF0IDJwbS48L3A+PC9ib2R5PjwvaHRtbD4='
                        # "<html><body><p>Please <b>join</b> the meeting today at 2pm.</p></body></html>"
                    }
                }
            ]
        }
    }


@pytest.fixture
def meeting_invite_message():
    """Email with meeting invitation."""
    return {
        'id': 'msg_invite',
        'threadId': 'thread_003',
        'labelIds': ['INBOX'],
        'snippet': 'You have been invited...',
        'payload': {
            'mimeType': 'text/plain',
            'headers': [
                {'name': 'From', 'value': 'calendar@google.com'},
                {'name': 'Subject', 'value': 'Invitation: Weekly Standup @ Mon Nov 20'},
                {'name': 'Date', 'value': 'Mon, 18 Nov 2024 09:00:00 +0000'}
            ],
            'body': {
                'data': 'WW91IGhhdmUgYmVlbiBpbnZpdGVkIHRvIGEgR29vZ2xlIE1lZXQgdmlkZW8gY2FsbC4='
                # "You have been invited to a Google Meet video call."
            }
        }
    }


class TestEmailParserParsing:
    """Test email parsing functionality."""

    def test_parse_simple_email(self, parser, simple_gmail_message):
        """Test parsing simple plain text email."""
        email_data = parser.parse_email(simple_gmail_message)

        assert email_data.id == 'msg_simple'
        assert email_data.thread_id == 'thread_001'
        assert email_data.subject == 'CRESCO Document Review'
        assert email_data.sender_name == 'Jef Adriaenssens'
        assert email_data.sender_email == 'jef@example.com'
        assert 'Can you review' in email_data.body_text
        assert 'Friday' in email_data.body_text
        assert email_data.has_attachments is False
        assert len(email_data.action_phrases) > 0

    def test_parse_multipart_email(self, parser, multipart_gmail_message):
        """Test parsing multipart email with HTML."""
        email_data = parser.parse_email(multipart_gmail_message)

        assert email_data.id == 'msg_multi'
        assert 'Please join the meeting' in email_data.body_text
        assert email_data.body_html != ""
        assert email_data.sender_name == 'Alberto'
        assert email_data.sender_email == 'alberto@spain.com'

    def test_parse_no_subject(self, parser):
        """Test parsing email without subject."""
        message = {
            'id': 'msg_no_subj',
            'threadId': 'thread_004',
            'payload': {
                'headers': [],
                'body': {'data': 'VGVzdA=='}  # "Test"
            }
        }

        email_data = parser.parse_email(message)
        assert email_data.subject == '(No Subject)'

    def test_parse_missing_fields(self, parser):
        """Test parsing email with missing optional fields."""
        message = {
            'id': 'msg_minimal',
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Test'}
                ],
                'body': {'data': 'VGVzdA=='}
            }
        }

        email_data = parser.parse_email(message)
        assert email_data.id == 'msg_minimal'
        assert email_data.thread_id == ''
        assert email_data.sender == ''
        assert email_data.to == ''


class TestEmailParserHTMLCleaning:
    """Test HTML to text conversion."""

    def test_html_to_text_basic(self, parser):
        """Test basic HTML to text conversion."""
        html = '<html><body><p>Hello <b>world</b>!</p></body></html>'
        text = parser.html_to_text(html)

        assert 'Hello' in text
        assert 'world' in text
        assert '<' not in text  # No HTML tags

    def test_html_to_text_with_links(self, parser):
        """Test HTML with links."""
        html = '<html><body><p>Check out <a href="https://example.com">this link</a>!</p></body></html>'
        text = parser.html_to_text(html)

        assert 'Check out' in text
        assert 'https://example.com' in text or 'this link' in text

    def test_html_to_text_removes_scripts(self, parser):
        """Test that scripts/styles are removed."""
        html = '''
        <html>
        <head><script>alert('test');</script></head>
        <body>
        <style>body { color: red; }</style>
        <p>Content</p>
        </body>
        </html>
        '''
        text = parser.html_to_text(html)

        assert 'Content' in text
        assert 'alert' not in text
        assert 'color:' not in text

    def test_html_to_text_empty(self, parser):
        """Test empty HTML."""
        assert parser.html_to_text('') == ''
        assert parser.html_to_text(None) == ''


class TestEmailParserActionPhrases:
    """Test action phrase extraction."""

    def test_extract_action_phrases_direct_request(self, parser):
        """Test extracting direct request phrases."""
        text = "Can you please review the document by Friday? It's urgent."
        phrases = parser.extract_action_phrases(text)

        assert len(phrases) > 0
        assert any('review' in p.lower() for p in phrases)

    def test_extract_action_phrases_deadlines(self, parser):
        """Test extracting phrases with deadlines."""
        text = "Need to complete the report by tomorrow. Please send it ASAP."
        phrases = parser.extract_action_phrases(text)

        assert len(phrases) >= 1
        assert any('tomorrow' in p.lower() or 'asap' in p.lower() for p in phrases)

    def test_extract_action_phrases_task_verbs(self, parser):
        """Test extracting task verb phrases."""
        text = "Please update the spreadsheet. Review the changes and approve when ready."
        phrases = parser.extract_action_phrases(text)

        assert len(phrases) >= 2
        assert any('update' in p.lower() for p in phrases)
        assert any('review' in p.lower() or 'approve' in p.lower() for p in phrases)

    def test_extract_action_phrases_empty(self, parser):
        """Test with non-action text."""
        text = "Just letting you know that the meeting went well."
        phrases = parser.extract_action_phrases(text)

        # May or may not extract depending on keyword presence
        # Just verify it doesn't crash
        assert isinstance(phrases, list)

    def test_extract_action_phrases_limit(self, parser):
        """Test that action phrases are limited."""
        # Create text with many action phrases
        text = " ".join([f"Can you check item {i}?" for i in range(20)])
        phrases = parser.extract_action_phrases(text)

        assert len(phrases) <= 10  # Should be limited to 10


class TestEmailParserMeetingDetection:
    """Test meeting invitation detection."""

    def test_detect_meeting_invite_in_subject(self, parser):
        """Test detection from subject line."""
        email = EmailData(
            id='test', thread_id='t1', subject='Meeting Invitation: Project Review',
            sender='', sender_name='', sender_email='', to='', cc='', bcc='',
            date='', received_at=datetime.utcnow(), body_text='', body_html='',
            snippet='', labels=[], has_attachments=False, links=[],
            action_phrases=[], is_meeting_invite=False
        )

        assert parser.detect_meeting_invitation(email) is True

    def test_detect_meeting_invite_in_body(self, parser):
        """Test detection from email body."""
        email = EmailData(
            id='test', thread_id='t1', subject='Quick question',
            sender='', sender_name='', sender_email='', to='', cc='', bcc='',
            date='', received_at=datetime.utcnow(),
            body_text='You have been invited to join a Zoom meeting tomorrow at 2pm.',
            body_html='', snippet='', labels=[], has_attachments=False, links=[],
            action_phrases=[], is_meeting_invite=False
        )

        assert parser.detect_meeting_invitation(email) is True

    def test_detect_meeting_invite_google_meet(self, parser):
        """Test detection of Google Meet invites."""
        email = EmailData(
            id='test', thread_id='t1', subject='Team Sync',
            sender='', sender_name='', sender_email='', to='', cc='', bcc='',
            date='', received_at=datetime.utcnow(),
            body_text='Join us on Google Meet for the weekly standup.',
            body_html='', snippet='', labels=[], has_attachments=False, links=[],
            action_phrases=[], is_meeting_invite=False
        )

        assert parser.detect_meeting_invitation(email) is True

    def test_detect_meeting_invite_negative(self, parser):
        """Test non-meeting email."""
        email = EmailData(
            id='test', thread_id='t1', subject='Document Review',
            sender='', sender_name='', sender_email='', to='', cc='', bcc='',
            date='', received_at=datetime.utcnow(),
            body_text='Can you review this document when you have time?',
            body_html='', snippet='', labels=[], has_attachments=False, links=[],
            action_phrases=[], is_meeting_invite=False
        )

        assert parser.detect_meeting_invitation(email) is False


class TestEmailParserAddressParsing:
    """Test email address parsing."""

    def test_parse_email_address_with_name(self, parser):
        """Test parsing 'Name <email>' format."""
        name, email = parser._parse_email_address('John Doe <john@example.com>')

        assert name == 'John Doe'
        assert email == 'john@example.com'

    def test_parse_email_address_quoted_name(self, parser):
        """Test parsing quoted name."""
        name, email = parser._parse_email_address('"Jane Smith" <jane@example.com>')

        assert name == 'Jane Smith'
        assert email == 'jane@example.com'

    def test_parse_email_address_only(self, parser):
        """Test parsing just email address."""
        name, email = parser._parse_email_address('simple@example.com')

        assert name == ''
        assert email == 'simple@example.com'

    def test_parse_email_address_empty(self, parser):
        """Test parsing empty address."""
        name, email = parser._parse_email_address('')

        assert name == ''
        assert email == ''


class TestEmailParserLinkExtraction:
    """Test URL extraction."""

    def test_extract_links_http(self, parser):
        """Test extracting HTTP links."""
        text = 'Check out https://example.com and http://test.org for more info.'
        links = parser._extract_links(text)

        assert len(links) == 2
        assert 'https://example.com' in links
        assert 'http://test.org' in links

    def test_extract_links_www(self, parser):
        """Test extracting www links."""
        text = 'Visit www.example.com for details.'
        links = parser._extract_links(text)

        assert len(links) == 1
        assert 'www.example.com' in links

    def test_extract_links_removes_punctuation(self, parser):
        """Test that trailing punctuation is removed."""
        text = 'See https://example.com. Another at https://test.org!'
        links = parser._extract_links(text)

        assert len(links) == 2
        assert all(not link.endswith('.') and not link.endswith('!') for link in links)

    def test_extract_links_deduplication(self, parser):
        """Test link deduplication."""
        text = 'Link: https://example.com and again: https://example.com'
        links = parser._extract_links(text)

        assert len(links) == 1

    def test_extract_links_limit(self, parser):
        """Test link limit."""
        # Create text with many links
        text = ' '.join([f'https://example{i}.com' for i in range(30)])
        links = parser._extract_links(text)

        assert len(links) <= 20  # Should be limited to 20


class TestEmailParserSignatureRemoval:
    """Test signature and footer removal."""

    def test_clean_text_removes_signature_delimiter(self, parser):
        """Test removing standard signature delimiter."""
        text = '''Email body content here.

--
Best regards,
John Doe
Company Name'''

        cleaned = parser._clean_text(text)

        assert 'Email body content' in cleaned
        assert 'Best regards' not in cleaned
        assert 'Company Name' not in cleaned

    def test_clean_text_removes_sent_from(self, parser):
        """Test removing 'Sent from' signatures."""
        text = '''Email message.

Sent from my iPhone'''

        cleaned = parser._clean_text(text)

        assert 'Email message' in cleaned
        assert 'Sent from my iPhone' not in cleaned

    def test_clean_text_removes_blank_lines(self, parser):
        """Test removing excess blank lines."""
        text = '''Paragraph 1.


Paragraph 2.'''

        cleaned = parser._clean_text(text)

        # Should have at most double newlines
        assert '\n\n\n' not in cleaned


class TestEmailParserSingleton:
    """Test singleton pattern."""

    def test_get_email_parser_singleton(self):
        """Test that get_email_parser returns same instance."""
        parser1 = get_email_parser()
        parser2 = get_email_parser()

        assert parser1 is parser2


class TestEmailParserIntegration:
    """Integration tests with full parsing flow."""

    def test_full_parse_action_email(self, parser, simple_gmail_message):
        """Test full parsing of action-oriented email."""
        email_data = parser.parse_email(simple_gmail_message)

        # Verify parsing
        assert email_data.id == 'msg_simple'
        assert email_data.subject == 'CRESCO Document Review'

        # Verify action phrase extraction
        assert len(email_data.action_phrases) > 0
        assert any('review' in p.lower() for p in email_data.action_phrases)

        # Verify not a meeting
        assert email_data.is_meeting_invite is False

    def test_full_parse_meeting_email(self, parser, meeting_invite_message):
        """Test full parsing of meeting invitation."""
        email_data = parser.parse_email(meeting_invite_message)

        # Verify parsing
        assert email_data.id == 'msg_invite'

        # Verify meeting detection
        assert email_data.is_meeting_invite is True

    def test_performance_parse_100ms(self, parser, simple_gmail_message):
        """Test that parsing completes within performance target."""
        import time

        start = time.time()
        parser.parse_email(simple_gmail_message)
        elapsed = time.time() - start

        assert elapsed < 0.1  # Should be under 100ms
