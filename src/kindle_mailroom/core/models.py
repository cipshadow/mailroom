"""Shared data structures."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.header import decode_header


@dataclass
class GmailMessage:
    message_id: str
    thread_id: str
    subject: str
    sender: str
    date: str
    html_body: str


@dataclass
class SendReport:
    sent: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    dry_run: bool = False

    def summary(self) -> str:
        parts = [f"{self.sent} sent", f"{self.skipped} skipped"]
        if self.errors:
            parts.append(f"{len(self.errors)} errors")
        if self.dry_run:
            parts.append("(dry run)")
        return ", ".join(parts)


def get_week_start(date_str: str) -> str:
    """Return ISO format date of Monday (start of week) for the given date."""
    if not date_str or len(date_str) < 10:
        return "0000-00-00"
    try:
        dt = datetime.fromisoformat(date_str[:19])
        monday = dt - timedelta(days=dt.weekday())
        return monday.date().isoformat()
    except (ValueError, AttributeError):
        return "0000-00-00"


# Multi-label public suffixes we see on newsletter senders. Anything ending in
# one of these needs the label *before* it, not the last label.
_MULTI_LABEL_SUFFIXES = (".co.uk", ".com.au", ".co.nz", ".co.jp", ".org.uk", ".ac.uk")


def extract_sender_domain(sender: str) -> str:
    """Display name for a sender, from 'Name <email@domain>' format.

    Returns the registrable label - "stratechery" from stratechery.com,
    "ghost" from ghost.io - title-cased. Naively taking the last label
    yielded the TLD for anything that wasn't .com or .co.uk ("Io", "Org",
    "To"), which in digest mode collapsed every .org sender in a week into a
    single digest titled "Org".
    """
    match = re.search(r"<([^@]+@[^>]+)>", sender)
    if not match:
        return "Unknown"

    domain = match.group(1).split("@")[-1].strip().lower().rstrip(".")
    for suffix in _MULTI_LABEL_SUFFIXES:
        if domain.endswith(suffix):
            domain = domain[: -len(suffix)]
            break
    else:
        domain = domain.rpartition(".")[0] or domain

    # Whatever's left, the registrable label is its last part.
    label = domain.rpartition(".")[2]
    return label.title() if label else "Unknown"


def extract_sender_name(sender: str) -> str:
    """Display name for a sender, from 'Name <email@domain>' format.

    Grouping digests by domain put every newsletter on a shared sending
    platform - every Substack author sends from a *.substack.com-family
    address - into one combined digest per week, regardless of who actually
    wrote it. The display name is what actually distinguishes them.
    """
    header_part = sender.split("<", 1)[0].strip() if "<" in sender else ""
    if header_part:
        # Gmail can hand back MIME-encoded headers for non-ASCII names
        # (e.g. "=?UTF-8?B?...?=") rather than decoded text.
        try:
            decoded = "".join(
                part.decode(enc or "utf-8", errors="replace") if isinstance(part, bytes) else part
                for part, enc in decode_header(header_part)
            )
        except (UnicodeDecodeError, LookupError):
            decoded = header_part
        name = decoded.strip().strip('"').strip()
        if name:
            return name
    # No display name (bare email address) - fall back to a domain label
    # so these still degrade gracefully instead of colliding as "Unknown".
    return extract_sender_domain(sender)


def digest_title(sender_name: str, week_start: str) -> str:
    """The one title used for both the EPUB's own metadata and the email
    subject, so they can't drift apart into e.g. "Substack 2026-07-30" as
    a subject next to a "2026-07-30 - Substack 2026-07-30.epub" filename."""
    try:
        d = datetime.fromisoformat(week_start).date()
        date_label = f"{d.day:02d}/{d.month}"
    except ValueError:
        date_label = week_start
    return f"{sender_name} - {date_label} digest"


def group_messages_by_sender_week(messages: list[GmailMessage]) -> dict[tuple[str, str], list[GmailMessage]]:
    """Group messages by (sender_name, week_start_date)."""
    groups: dict[tuple[str, str], list[GmailMessage]] = {}
    for msg in messages:
        name = extract_sender_name(msg.sender)
        week = get_week_start(msg.date)
        groups.setdefault((name, week), []).append(msg)
    # Sort each group by date (oldest first)
    for key in groups:
        groups[key].sort(key=lambda m: m.date or "")
    return groups
