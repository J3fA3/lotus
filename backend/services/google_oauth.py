"""
Google OAuth Service - Phase 4

Handles OAuth 2.0 flow for Google Calendar API access.

Key Features:
1. Generate authorization URL for user to grant access
2. Exchange authorization code for tokens
3. Store and refresh tokens automatically
4. Provide valid credentials for API calls

Security:
- Tokens are stored in database
- Access tokens expire after 1 hour
- Refresh tokens used to get new access tokens
- TODO Production: Encrypt tokens at rest

Usage:
    oauth = GoogleOAuthService()

    # Step 1: Get authorization URL
    auth_url = oauth.get_authorization_url(user_id=1)
    # User visits URL and grants access

    # Step 2: Handle callback with auth code
    await oauth.handle_callback(code, user_id=1, db)

    # Step 3: Get valid credentials for API calls
    credentials = await oauth.get_valid_credentials(user_id=1, db)
    service = build('calendar', 'v3', credentials=credentials)
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.models import GoogleOAuthToken

logger = logging.getLogger(__name__)


class GoogleOAuthService:
    """Service for managing Google OAuth 2.0 authentication."""

    def __init__(self):
        """Initialize OAuth service with environment configuration."""
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

        scopes_str = os.getenv("GOOGLE_CALENDAR_SCOPES", "")
        self.scopes = [s.strip() for s in scopes_str.split(",") if s.strip()]

        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            logger.error("Missing required Google OAuth environment variables")
            raise ValueError("Google OAuth not configured. Check .env file.")

        logger.info(f"Google OAuth initialized with {len(self.scopes)} scopes")

    def get_authorization_url(self, user_id: int = 1, state: Optional[str] = None) -> str:
        """Generate OAuth authorization URL for user to grant access.

        Args:
            user_id: User ID to associate with this auth flow
            state: Optional state parameter (defaults to user_id)

        Returns:
            Authorization URL for user to visit

        Example:
            auth_url = oauth.get_authorization_url(user_id=1)
            # Redirect user to auth_url
            # They'll be redirected back to GOOGLE_REDIRECT_URI with code
        """
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }

        flow = Flow.from_client_config(
            client_config,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )

        # Use user_id as state to identify user on callback
        state_value = state or str(user_id)

        authorization_url, state_returned = flow.authorization_url(
            access_type='offline',  # Get refresh token
            include_granted_scopes='true',
            prompt='consent',  # Force consent screen to ensure refresh token
            state=state_value
        )

        logger.info(f"Generated OAuth URL for user {user_id}")
        return authorization_url

    async def handle_callback(
        self,
        code: str,
        user_id: int,
        db: AsyncSession
    ) -> Credentials:
        """Exchange authorization code for tokens and store in database.

        Args:
            code: Authorization code from OAuth callback
            user_id: User ID to associate tokens with
            db: Database session

        Returns:
            Google Credentials object

        Raises:
            ValueError: If code exchange fails
        """
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }

        flow = Flow.from_client_config(
            client_config,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )

        try:
            # Exchange code for tokens
            flow.fetch_token(code=code)
            credentials = flow.credentials

            # Store tokens in database
            await self._store_tokens(user_id, credentials, db)

            logger.info(f"OAuth tokens stored for user {user_id}")
            return credentials

        except Exception as e:
            logger.error(f"OAuth callback failed for user {user_id}: {e}")
            raise ValueError(f"Failed to exchange authorization code: {e}")

    async def get_valid_credentials(
        self,
        user_id: int,
        db: AsyncSession
    ) -> Credentials:
        """Get valid credentials for API calls, refreshing if expired.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Valid Google Credentials object

        Raises:
            ValueError: If no tokens found or refresh fails
        """
        # Load tokens from database
        query = select(GoogleOAuthToken).where(
            GoogleOAuthToken.user_id == user_id
        )
        result = await db.execute(query)
        token_record = result.scalar_one_or_none()

        if not token_record:
            raise ValueError(f"No OAuth tokens found for user {user_id}. User must authorize first.")

        # Create credentials object
        credentials = Credentials(
            token=token_record.access_token,
            refresh_token=token_record.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=token_record.scopes
        )

        # Set expiry
        credentials.expiry = token_record.token_expiry

        # Refresh if expired
        if credentials.expired and credentials.refresh_token:
            logger.info(f"Refreshing expired token for user {user_id}")
            try:
                credentials.refresh(Request())

                # Update database with new tokens
                await self._update_tokens(user_id, credentials, db)
                logger.info(f"Token refreshed successfully for user {user_id}")

            except Exception as e:
                logger.error(f"Token refresh failed for user {user_id}: {e}")
                raise ValueError(f"Failed to refresh token: {e}. User may need to re-authorize.")

        return credentials

    async def _store_tokens(
        self,
        user_id: int,
        credentials: Credentials,
        db: AsyncSession
    ):
        """Store OAuth tokens in database.

        Args:
            user_id: User ID
            credentials: Google Credentials object
            db: Database session
        """
        # Check if tokens already exist
        query = select(GoogleOAuthToken).where(
            GoogleOAuthToken.user_id == user_id
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing tokens
            existing.access_token = credentials.token
            existing.refresh_token = credentials.refresh_token or existing.refresh_token
            existing.token_expiry = credentials.expiry
            existing.scopes = credentials.scopes or existing.scopes
            existing.updated_at = datetime.utcnow()
        else:
            # Create new token record
            new_token = GoogleOAuthToken(
                user_id=user_id,
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_expiry=credentials.expiry,
                scopes=credentials.scopes or []
            )
            db.add(new_token)

        await db.commit()

    async def _update_tokens(
        self,
        user_id: int,
        credentials: Credentials,
        db: AsyncSession
    ):
        """Update tokens after refresh.

        Args:
            user_id: User ID
            credentials: Refreshed credentials
            db: Database session
        """
        query = select(GoogleOAuthToken).where(
            GoogleOAuthToken.user_id == user_id
        )
        result = await db.execute(query)
        token_record = result.scalar_one()

        token_record.access_token = credentials.token
        token_record.token_expiry = credentials.expiry
        token_record.updated_at = datetime.utcnow()

        await db.commit()

    async def is_authorized(self, user_id: int, db: AsyncSession) -> bool:
        """Check if user has valid OAuth tokens.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            True if user has tokens (may be expired but refreshable)
        """
        query = select(GoogleOAuthToken).where(
            GoogleOAuthToken.user_id == user_id
        )
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None

    async def revoke_authorization(self, user_id: int, db: AsyncSession):
        """Revoke OAuth authorization and delete tokens.

        Args:
            user_id: User ID
            db: Database session
        """
        query = select(GoogleOAuthToken).where(
            GoogleOAuthToken.user_id == user_id
        )
        result = await db.execute(query)
        token_record = result.scalar_one_or_none()

        if token_record:
            await db.delete(token_record)
            await db.commit()
            logger.info(f"Revoked OAuth tokens for user {user_id}")


# Singleton instance
_oauth_service = None


def get_oauth_service() -> GoogleOAuthService:
    """Get singleton OAuth service instance.

    Returns:
        GoogleOAuthService instance
    """
    global _oauth_service
    if _oauth_service is None:
        _oauth_service = GoogleOAuthService()
    return _oauth_service
