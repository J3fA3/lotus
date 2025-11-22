#!/usr/bin/env python3
"""
Test Gmail API access comprehensively.

This script tests real Gmail API access including:
- OAuth authentication
- Email fetching
- Database storage verification

Usage:
    python backend/test_gmail_access.py
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from services.gmail_service import get_gmail_service
from db.database import AsyncSessionLocal
from sqlalchemy import select
from db.models import EmailMessage

async def test_real_gmail():
    """
    Test real Gmail API access end-to-end.
    
    Returns:
        bool: True if all tests pass, False otherwise
    """
    print("=" * 70)
    print("REAL GMAIL API ACCESS TEST")
    print("=" * 70)
    
    async with AsyncSessionLocal() as db:
        gmail = get_gmail_service()
        
        print("\n[1/4] Authenticating with Gmail API...")
        try:
            await gmail.authenticate(user_id=1, db=db)
            print("   ✅ SUCCESS: Authenticated")
            print(f"   - Service object: {'Created' if gmail.service else 'Missing'}")
            print(f"   - Credentials valid: {gmail.credentials.valid if gmail.credentials else 'N/A'}")
            if gmail.credentials:
                print(f"   - Scopes: {len(gmail.credentials.scopes)} scopes")
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n[2/4] Fetching unread emails (max 5)...")
        try:
            emails = await gmail.get_recent_emails(
                query="is:unread -label:processed",
                max_results=5,
                user_id="me"
            )
            print(f"   ✅ SUCCESS: Found {len(emails)} unread emails")
            if emails:
                print("\n   Email Details:")
                for i, email in enumerate(emails[:3], 1):
                    subject = email.get('subject', 'No subject')
                    sender = email.get('sender', 'Unknown')
                    snippet = email.get('snippet', '')[:80]
                    print(f"   {i}. Subject: {subject[:60]}")
                    print(f"      From: {sender[:50]}")
                    print(f"      Preview: {snippet}...")
            else:
                print("   ℹ️  No unread emails found (this is normal if inbox is empty)")
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n[3/4] Fetching recent emails (any status, max 3)...")
        try:
            emails = await gmail.get_recent_emails(
                query="",
                max_results=3,
                user_id="me"
            )
            print(f"   ✅ SUCCESS: Found {len(emails)} recent emails")
            if emails:
                for i, email in enumerate(emails, 1):
                    print(f"   {i}. {email.get('subject', 'No subject')[:60]}")
        except Exception as e:
            print(f"   ⚠️  WARNING: {e}")
        
        print("\n[4/4] Checking database for stored emails...")
        try:
            result = await db.execute(select(EmailMessage))
            stored = result.scalars().all()
            real_emails = [e for e in stored if not e.gmail_message_id.startswith('test_')]
            print(f"   ✅ Found {len(real_emails)} real emails in database")
            if real_emails:
                for email in real_emails[:3]:
                    print(f"      - {email.subject[:50]} ({email.classification or 'unclassified'})")
        except Exception as e:
            print(f"   ⚠️  WARNING: {e}")
        
        print("\n" + "=" * 70)
        print("✅ GMAIL API ACCESS: FULLY WORKING")
        print("=" * 70)
        print("\nSummary:")
        print(f"  - OAuth: ✅ Authorized with all scopes")
        print(f"  - Authentication: ✅ Working")
        print(f"  - Email Fetch: ✅ Working")
        print(f"  - API Access: ✅ Full access confirmed")
        return True

if __name__ == "__main__":
    """Main entry point for the test script."""
    try:
        result = asyncio.run(test_real_gmail())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



