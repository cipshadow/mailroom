"""OAuth credential lifecycle.

Uses a Google *Desktop app* OAuth client: desktop clients accept any
`http://127.0.0.1:<port>` loopback redirect without pre-registering the URI,
so users never have to configure redirect URIs in Google Cloud. The Flask
server (or, for the CLI, a throwaway local server) receives the callback.
"""

from __future__ import annotations

import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow

from .. import config as cfg

# gmail.modify covers reading and label changes; gmail.send covers delivery.
# (gmail.readonly would be redundant with modify — fewer consent checkboxes.)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


class NotAuthenticatedError(Exception):
    """No usable OAuth token; the user must (re)connect their Google account."""


def has_client_secret() -> bool:
    return cfg.client_secret_path().exists()


def has_token() -> bool:
    return cfg.token_path().exists()


def validate_client_secret(text: str) -> dict:
    """Parse pasted/uploaded OAuth client JSON; must be a Desktop-app client."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("That isn't valid JSON. Paste the full contents of the downloaded file.") from exc
    if "installed" not in data:
        if "web" in data:
            raise ValueError(
                'This is a "Web application" OAuth client. Create one with '
                'application type "Desktop app" instead — it needs no redirect URI setup.'
            )
        raise ValueError("This doesn't look like a Google OAuth client JSON (missing 'installed' key).")
    client = data["installed"]
    if not client.get("client_id") or not client.get("client_secret"):
        raise ValueError("The OAuth client JSON is missing client_id or client_secret.")
    return data


def save_client_secret(text: str) -> None:
    validate_client_secret(text)
    cfg.write_private(cfg.client_secret_path(), text)


def save_token(creds: Credentials) -> None:
    cfg.write_private(cfg.token_path(), creds.to_json())


def forget_credentials() -> None:
    for path in (cfg.token_path(), cfg.client_secret_path()):
        if path.exists():
            path.unlink()


def load_credentials() -> Credentials:
    """Load the stored token, refreshing it if expired. Raises
    NotAuthenticatedError when the user needs to go through OAuth (again)."""
    if not has_token():
        raise NotAuthenticatedError("Not connected to Google yet.")
    try:
        creds = Credentials.from_authorized_user_file(str(cfg.token_path()), SCOPES)
    except (ValueError, json.JSONDecodeError) as exc:
        raise NotAuthenticatedError(f"Stored token is unreadable: {exc}") from exc

    if creds.valid:
        return creds
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as exc:
            raise NotAuthenticatedError(
                "Google token could not be refreshed (it may have been revoked "
                "or expired — testing-mode tokens expire after 7 days). "
                "Reconnect your Google account from Settings."
            ) from exc
        save_token(creds)
        return creds
    raise NotAuthenticatedError("Stored Google token is invalid. Reconnect your Google account.")


def build_web_flow(redirect_uri: str) -> Flow:
    """Flow for the web UI: our Flask server receives the loopback redirect."""
    if not has_client_secret():
        raise NotAuthenticatedError("No OAuth client configured yet.")
    return Flow.from_client_secrets_file(
        str(cfg.client_secret_path()),
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )


def run_console_flow() -> Credentials:
    """Interactive flow for CLI-only use: spins up a one-shot local server."""
    if not has_client_secret():
        raise NotAuthenticatedError(
            f"No OAuth client at {cfg.client_secret_path()}. "
            "Run `kindle-mailroom` (no arguments) to complete setup in the browser."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(cfg.client_secret_path()), SCOPES)
    creds = flow.run_local_server(port=0)
    save_token(creds)
    return creds
