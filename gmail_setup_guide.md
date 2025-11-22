# How to Get `credentials.json` for Gmail API

The `GMAIL_CREDENTIALS_FILE` refers to the **OAuth 2.0 Client ID** JSON file that allows this application to access your Gmail account securely.

## Step-by-Step Guide

### 1. Create a Project in Google Cloud Console
1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Click the project dropdown (top left) and select **New Project**.
3.  Name it (e.g., "RAG Support Bot") and click **Create**.

### 2. Enable the Gmail API
1.  In the sidebar, go to **APIs & Services** > **Library**.
2.  Search for **"Gmail API"**.
3.  Click on it and click **Enable**.

### 3. Configure OAuth Consent Screen
1.  Go to **APIs & Services** > **OAuth consent screen**.
2.  Select **External** (unless you have a Google Workspace organization, then Internal is fine). Click **Create**.
3.  **App Information**: Fill in App Name (e.g., "Support Bot") and User Support Email.
4.  **Developer Contact**: Add your email.
5.  Click **Save and Continue**.
6.  **Scopes**: Click **Add or Remove Scopes**. Search for `gmail.modify` and select it. Click **Update**, then **Save and Continue**.
7.  **Test Users**: Click **Add Users** and add the Gmail address you want to use for sending emails. **This is crucial.**
8.  Click **Save and Continue**.

### 4. Create Credentials
1.  Go to **APIs & Services** > **Credentials**.
2.  Click **+ CREATE CREDENTIALS** > **OAuth client ID**.
3.  **Application type**: Select **Desktop app**.
4.  Name it (e.g., "Python Client").
5.  Click **Create**.

### 5. Download the JSON File
1.  You will see a pop-up "OAuth client created".
2.  Click the **Download JSON** button (icon with a down arrow).
3.  Save this file to your project folder: `/Users/nayaneshgupte/AI Projects/RAG Demo/`.
4.  **Rename** the file to `credentials.json`.

## Final Check
Your project folder should now contain:
-   `main.py`
-   `.env`
-   `credentials.json` <--- The file you just downloaded.
