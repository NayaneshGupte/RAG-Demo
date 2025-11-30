# Dashboard-Initiated Gmail OAuth Setup Guide

## Prerequisites
- Google Cloud Console account
- Flask app running on `http://localhost:5000`

## Step 1: Configure OAuth Redirect URI in Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create one if needed)
3. Navigate to **APIs & Services** → **Credentials**
4. Click on your OAuth 2.0 Client ID (or create one if you haven't)
5. Under **Authorized redirect URIs**, add:
   ```
   http://localhost:5000/auth/gmail/callback
   ```
6. Click **Save**

## Step 2: Environment Variables

Add these to your `.env` file:

```env
# OAuth Configuration
OAUTH_REDIRECT_URI=http://localhost:5000/auth/gmail/callback
SECRET_KEY=your-secret-key-here-minimum-32-chars

# Agent Settings (optional)
AGENT_POLL_INTERVAL=60  # seconds between email checks
```

**Generate a secure SECRET_KEY**:
```python
import secrets
print(secrets.token_hex(32))
```

## Step 3: Start the Application

1. **Start Flask Dashboard**:
   ```bash
   python wsgi.py
   ```

2. **Open Browser**:
   Navigate to `http://localhost:5000`

3.  **Authenticate**:
   - Dashboard will show "Gmail Authentication Required"
   - Click "Connect Gmail" button
   - Authorize the app in Google OAuth consent screen
   - You'll be redirected back to dashboard
   - Agent will auto-start

## What Happens During Auth Flow

1. User clicks "Connect Gmail" button
2. Redirected to Google OAuth consent screen
3. User authorizes the app
4. Google redirects to `/auth/gmail/callback` with code
5. App exchanges code for credentials
6. Credentials saved to `token.json`
7. Session created with user email
8. Agent automatically starts in background
9. Dashboard displays with agent status

## Auto-Resume on Flask Restart

If you restart Flask and `token.json` still valid:
- Agent automatically resumes on startup
- No need to re-authenticate
- Dashboard shows authenticated state

## Agent Status Display

Dashboard shows:
- ✅ **Running** (green pulsing dot) - Agent is active
- ⭕ **Stopped** (gray dot) - Agent is not running
- **Uptime** - How long agent has been running
- **Last Poll** - When agent last checked for emails
- **Processed** - Number of emails processed

## Troubleshooting

### "Invalid redirect URI" error
- Make sure you added `http://localhost:5000/auth/gmail/callback` to Google Cloud Console
- Check for typos in OAUTH_REDIRECT_URI in .env

### Agent doesn't auto-start
- Check Flask logs for errors
- Verify token.json exists and is valid
- Restart Flask app

### Session expires / Auth required again
- Sessions last 30 days by default
- Can be changed in `app/__init__.py` → `PERMANENT_SESSION_LIFETIME`

## Production Deployment

For production (e.g., Heroku, AWS):

1. Update OAUTH_REDIRECT_URI:
   ```env
   OAUTH_REDIRECT_URI=https://yourdomain.com/auth/gmail/callback
   ```

2. Add production URL to Google Cloud Console authorized redirect URIs

3. Use strong SECRET_KEY (never commit to git)

4. Consider using Redis for session storage instead of filesystem
