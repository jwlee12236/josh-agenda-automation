"""
Google OAuth helpers.

Local dev: runs the browser flow and writes token.json.
GitHub Actions: reads token.json from the TOKEN_JSON secret (base64-encoded).
"""

import base64
import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import CREDENTIALS_PATH, GOOGLE_SCOPES, TOKEN_PATH


def get_credentials() -> Credentials:
    """Return valid Google credentials, refreshing or re-authorising as needed."""
    creds = None

    # GitHub Actions: token JSON injected as base64 env var
    token_b64 = os.environ.get("TOKEN_JSON_B64")
    if token_b64:
        token_data = json.loads(base64.b64decode(token_b64).decode())
        creds = Credentials.from_authorized_user_info(token_data, GOOGLE_SCOPES)

    # Local dev: read from file
    elif os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, GOOGLE_SCOPES)

    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_token(creds)
        return creds

    # First-time local authorisation
    if not creds or not creds.valid:
        if not os.path.exists(CREDENTIALS_PATH):
            raise FileNotFoundError(
                f"credentials.json not found at {CREDENTIALS_PATH}. "
                "Download it from Google Cloud Console."
            )
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, GOOGLE_SCOPES)
        creds = flow.run_local_server(port=0)
        _save_token(creds)

    return creds


def _save_token(creds: Credentials) -> None:
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())


def get_calendar_service():
    return build("calendar", "v3", credentials=get_credentials())


def get_gmail_service():
    return build("gmail", "v1", credentials=get_credentials())
