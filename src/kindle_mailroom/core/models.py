"""Shared data structures."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta


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


def group_messages_by_sender_week(messages: list[GmailMessage]) -> dict[tuple[str, str], list[GmailMessage]]:
    """Group messages by (sender_domain, week_start_date)."""
    groups: dict[tuple[str, str], list[GmailMessage]] = {}
    for msg in messages:
        domain = extract_sender_domain(msg.sender)
        week = get_week_start(msg.date)
        groups.setdefault((domain, week), []).append(msg)
    # Sort each group by date (oldest first)
    for key in groups:
        groups[key].sort(key=lambda m: m.date or "")
    return groups
