"""Gmail API operations: fetch labeled messages, send EPUBs, manage labels."""

from __future__ import annotations

import base64
import email.utils
import html
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import google_auth_httplib2
import httplib2
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .models import GmailMessage
from .sanitize import sanitize_html


class LabelNotFoundError(Exception):
    def __init__(self, label_name: str):
        super().__init__(f'Gmail label "{label_name}" was not found.')
        self.label_name = label_name


def build_service(creds: Credentials):
    http = google_auth_httplib2.AuthorizedHttp(creds, http=httplib2.Http(timeout=120))
    return build("gmail", "v1", http=http)


def get_profile_email(service) -> str:
    """The authenticated Gmail address (shown after OAuth, used as From)."""
    return service.users().getProfile(userId="me").execute().get("emailAddress", "")


def b64url_decode(data: str) -> bytes:
    data += "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data.encode("ascii"))


def get_header(headers: list[dict[str, str]], name: str) -> str:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def walk_parts(payload: dict[str, Any]):
    yield payload
    for part in payload.get("parts", []) or []:
        yield from walk_parts(part)


def extract_body(payload: dict[str, Any]) -> str:
    html_part = None
    text_part = None

    for part in walk_parts(payload):
        mime_type = part.get("mimeType")
        body_data = part.get("body", {}).get("data")
        if not body_data:
            continue
        if mime_type == "text/html" and html_part is None:
            html_part = b64url_decode(body_data).decode("utf-8", errors="replace")
        elif mime_type == "text/plain" and text_part is None:
            text_part = b64url_decode(body_data).decode("utf-8", errors="replace")

    if html_part:
        return sanitize_html(html_part)
    if text_part:
        return "<pre>" + html.escape(text_part) + "</pre>"
    return "<p>No readable message body found.</p>"


def ensure_label(service, label_name: str) -> str:
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"] == label_name:
            return label["id"]

    created = (
        service.users()
        .labels()
        .create(
            userId="me",
            body={
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        )
        .execute()
    )
    return created["id"]


def get_label_id(service, label_name: str) -> str:
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"] == label_name:
            return label["id"]
    raise LabelNotFoundError(label_name)


def fetch_labelled_messages(
    service,
    source_label: str,
    limit: int,
    unread_only: bool,
) -> list[GmailMessage]:
    """limit 0 (or negative) means no limit: page through every labelled message."""
    label_id = get_label_id(service, source_label)
    label_ids = [label_id]
    if unread_only:
        label_ids.append("UNREAD")
    refs: list[dict] = []
    page_token = None
    while True:
        page_size = min(500, limit - len(refs)) if limit > 0 else 500
        results = (
            service.users()
            .messages()
            .list(userId="me", labelIds=label_ids, maxResults=page_size,
                  pageToken=page_token)
            .execute()
        )
        refs.extend(results.get("messages", []))
        page_token = results.get("nextPageToken")
        if not page_token or (limit > 0 and len(refs) >= limit):
            break
    if limit > 0:
        refs = refs[:limit]
    messages = []

    for ref in refs:
        raw = (
            service.users()
            .messages()
            .get(userId="me", id=ref["id"], format="full")
            .execute()
        )
        payload = raw["payload"]
        headers = payload.get("headers", [])
        subject = get_header(headers, "Subject") or "Gmail Message"
        sender = get_header(headers, "From")
        date = get_header(headers, "Date")
        parsed_date = email.utils.parsedate_to_datetime(date) if date else None
        messages.append(
            GmailMessage(
                message_id=raw["id"],
                thread_id=raw["threadId"],
                subject=subject,
                sender=sender,
                date=parsed_date.isoformat() if parsed_date else date,
                html_body=extract_body(payload),
            )
        )

    return messages


def send_epub_to_kindle(service, epub_path: Path, subject: str,
                        from_address: str, kindle_email: str,
                        attachment_filename: str | None = None) -> str:
    """Email an EPUB attachment to the Kindle address. Returns the sent
    message's Gmail ID."""
    msg = MIMEMultipart()
    msg["From"] = from_address
    msg["To"] = kindle_email
    msg["Subject"] = subject[:120] or "Kindle Mailroom"
    msg.attach(MIMEText("Attached for Kindle.", "plain"))

    with epub_path.open("rb") as file:
        attachment = MIMEApplication(file.read(), _subtype="epub")
    attachment.add_header("Content-Disposition", "attachment",
                          filename=attachment_filename or epub_path.name)
    msg.attach(attachment)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return result.get("id", "")


def move_to_sent_label(
    service,
    message_id: str,
    source_label: str,
    sent_label: str,
    mark_read: bool,
) -> None:
    source_label_id = get_label_id(service, source_label)
    sent_label_id = ensure_label(service, sent_label)
    remove_label_ids = [source_label_id, "INBOX"]
    if mark_read:
        remove_label_ids.append("UNREAD")
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": [sent_label_id], "removeLabelIds": remove_label_ids},
    ).execute()


def restore_message(service, message_id: str, source_label_id: str, sent_label_id: str) -> None:
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": [source_label_id], "removeLabelIds": [sent_label_id]},
    ).execute()
