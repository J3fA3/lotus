# Phase 5: Gmail API Setup Guide

## Step 1: Enable Gmail API in Google Cloud Console

**Important:** You'll use the same Google Cloud Project from Phase 4 (Calendar API).

### Enable Gmail API

1. Go to **[Google Cloud Console - Gmail API](https://console.cloud.google.com/apis/library/gmail.googleapis.com)**
2. Make sure you're in the correct project (same one used for Calendar API)
3. Click **"Enable"** button
4. Wait for the API to be enabled (takes ~30 seconds)

### Update OAuth Consent Screen

1. Go to **[OAuth Consent Screen](https://console.cloud.google.com/apis/credentials/consent)**
2. Click **"Edit App"**
3. Scroll down to **"Scopes"** section
4. Click **"Add or Remove Scopes"**
5. In the filter box, search for: `gmail.readonly`
6. Check the box next to: **`https://www.googleapis.com/auth/gmail.readonly`**
   - Description: "Read all resources and their metadata—no write operations"
7. Click **"Update"** at the bottom
8. Click **"Save and Continue"**

### Verify Scopes

Your OAuth app should now have these scopes:
- ✅ `https://www.googleapis.com/auth/calendar.readonly`
- ✅ `https://www.googleapis.com/auth/calendar.events`
- ✅ `https://www.googleapis.com/auth/gmail.readonly` (new)

## Step 2: No Credential Changes Required

Good news! You'll reuse the same OAuth credentials from Phase 4:
- **Client ID:** Already in `.env` as `GOOGLE_CLIENT_ID`
- **Client Secret:** Already in `.env` as `GOOGLE_CLIENT_SECRET`
- **Redirect URI:** `http://localhost:8000/api/auth/google/callback`

The Gmail service will use the same OAuth flow, but with the updated scopes.

## Step 3: Re-authenticate (Required)

Since we added a new scope, you'll need to re-authenticate:

1. Delete the existing token (if any):
   ```bash
   cd backend
   rm -f gmail_token.json calendar_token.json
   ```

2. Run the OAuth flow again (will be done in Step 5)

## Step 4: Verify Configuration

Check that your `backend/.env` file has these Phase 5 variables:

```bash
# Phase 5: Gmail Integration
GMAIL_CREDENTIALS_PATH=gmail_credentials.json
GMAIL_TOKEN_PATH=gmail_token.json
GMAIL_POLL_INTERVAL_MINUTES=20
GMAIL_MAX_RESULTS=50
EMAIL_CLASSIFICATION_THRESHOLD=0.7
EMAIL_AUTO_CREATE_THRESHOLD=0.8
ENABLE_AGENT_PARALLELIZATION=true
MAX_PARALLEL_AGENTS=4
KG_CACHE_TTL_SECONDS=60
```

## Troubleshooting

### Error: "Access Not Configured. Gmail API has not been used..."
- **Solution:** Make sure you enabled the Gmail API (Step 1)
- Wait 30-60 seconds after enabling

### Error: "Insufficient Permission: Request had insufficient authentication scopes"
- **Solution:** Make sure `GOOGLE_CALENDAR_SCOPES` includes `gmail.readonly`
- Delete token file and re-authenticate

### Error: "Invalid grant: Token has been expired or revoked"
- **Solution:** Delete `gmail_token.json` and re-authenticate

## Next Steps

Continue with **Step 2: Create Gmail Service Wrapper** in the implementation plan.

## Cost & Quotas

**Gmail API Quotas (Free Tier):**
- **Quota:** 1 billion requests/day (more than enough)
- **Rate Limit:** 250 requests/second/user
- **Cost:** **FREE** (no charges)

**Our Usage (polling every 20 minutes):**
- ~72 requests/day (well within free quota)
- Cost: **$0.00/month**

Total Phase 5 cost: **$0.00/month** (Gmail is free!)
