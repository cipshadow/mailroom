"""Orchestration: the send flows shared by the CLI, web UI, and scheduler.

All progress goes through a callback so the CLI can print and the web job
runner can stream to the browser. Nothing here reads stdin.
"""

from __future__ import annotations

import time
from typing import Callable

from ..config import Config, epub_dir
from . import gmail_client as gc
from .epub_build import message_to_epub, messages_to_digest_epub, url_to_epub
from .models import GmailMessage, SendReport, group_messages_by_sender_week
from .sanitize import count_words
from .store import Store
from .urlfetch import download_images, fetch_article, get_article_date

ProgressFn = Callable[[str], None]

MIN_WORDS = 200  # emails thinner than this aren't worth a Kindle document


def send_labelled(
    service,
    store: Store,
    config: Config,
    *,
    digest: bool | None = None,
    dry_run: bool = False,
    resend: bool = False,
    limit: int | None = None,
    unread_only: bool = True,
    progress: ProgressFn = print,
) -> SendReport:
    """Send emails carrying the source label to the Kindle address."""
    use_digest = config.digest if digest is None else digest
    messages = gc.fetch_labelled_messages(
        service, config.source_label, limit or config.send_limit, unread_only
    )
    progress(f"Found {len(messages)} message(s) in \"{config.source_label}\"")
    if use_digest:
        return _send_digest_mode(service, store, config, messages,
                                 dry_run=dry_run, resend=resend, progress=progress)
    return _send_one_by_one(service, store, config, messages,
                            dry_run=dry_run, resend=resend, progress=progress)


def _skip_thin(service, config: Config, message: GmailMessage,
               progress: ProgressFn, *, dry_run: bool) -> bool:
    word_count = count_words(message.html_body)
    if word_count >= MIN_WORDS:
        return False
    progress(f"skip (thin, {word_count} words): {message.subject}")
    # Relabelling is a mutation of the user's mailbox, so it has to respect
    # dry_run - otherwise `send --dry-run` silently strips the source label
    # and marks thin messages read, which is the opposite of a no-op.
    if not dry_run:
        gc.move_to_sent_label(service, message.message_id, config.source_label,
                              config.sent_label, config.mark_read)
    return True


def _send_one_by_one(service, store: Store, config: Config, messages: list[GmailMessage],
                     *, dry_run: bool, resend: bool, progress: ProgressFn) -> SendReport:
    """Send one EPUB per email (original mode)."""
    report = SendReport(dry_run=dry_run)
    for message in messages:
        if store.already_sent(message.message_id) and not resend:
            report.skipped += 1
            continue

        if _skip_thin(service, config, message, progress, dry_run=dry_run):
            report.skipped += 1
            continue

        epub_path = message_to_epub(message, epub_dir(), resend=resend, progress=progress)
        if dry_run:
            progress(f"[dry-run] {message.subject} -> {epub_path.name}")
            continue

        send_title = f"[resend] {message.subject}" if resend else message.subject
        gc.send_epub_to_kindle(service, epub_path, send_title,
                               config.gmail_address, config.kindle_email)
        store.record_sent(message, epub_path, config.kindle_email)
        gc.move_to_sent_label(service, message.message_id, config.source_label,
                              config.sent_label, config.mark_read)
        report.sent += 1
        progress(f"sent: {message.subject}")
        time.sleep(config.send_delay)

    progress(f"done: {report.summary()}")
    return report


def _send_digest_mode(service, store: Store, config: Config, messages: list[GmailMessage],
                      *, dry_run: bool, resend: bool, progress: ProgressFn) -> SendReport:
    """Send weekly digests grouped by sender."""
    report = SendReport(dry_run=dry_run)

    filtered = []
    for message in messages:
        if _skip_thin(service, config, message, progress, dry_run=dry_run):
            report.skipped += 1
            continue
        filtered.append(message)

    groups = group_messages_by_sender_week(filtered)

    for (sender_domain, week_start), group_messages in sorted(groups.items()):
        digest_id = f"{sender_domain}-{week_start}"

        already = store.digest_already_sent([m.message_id for m in group_messages])
        if already and not resend:
            progress(f"skip (digest already sent) {sender_domain} {week_start}")
            report.skipped += len(group_messages)
            continue

        epub_path = messages_to_digest_epub(group_messages, sender_domain, week_start,
                                            epub_dir(), progress=progress)
        if dry_run:
            progress(f"[dry-run] {sender_domain} {week_start} -> {epub_path.name}")
            continue

        gc.send_epub_to_kindle(service, epub_path, f"{sender_domain} {week_start}",
                               config.gmail_address, config.kindle_email)
        for msg in group_messages:
            store.record_sent(msg, epub_path, config.kindle_email,
                              digest_id=digest_id, sender_domain=sender_domain)
            gc.move_to_sent_label(service, msg.message_id, config.source_label,
                                  config.sent_label, config.mark_read)

        report.sent += 1
        progress(f"sent digest {sender_domain} {week_start} ({len(group_messages)} articles)")
        time.sleep(config.send_delay)

    progress(f"done: {report.summary()} (digests)")
    return report


def send_urls(
    service,
    store: Store,
    config: Config,
    urls: list[str],
    *,
    number: bool = False,
    chronological: bool = False,
    progress: ProgressFn = print,
) -> SendReport:
    """Fetch each URL, build an EPUB, and send it to the Kindle address."""
    report = SendReport()

    if chronological or (number and len(urls) > 1):
        progress(f"Sorting {len(urls)} article(s) chronologically...")
        dated = [(get_article_date(u), u) for u in urls]
        dated.sort(key=lambda x: x[0])
        urls = [u for _, u in dated]

    numbering = number and len(urls) > 1
    for i, url in enumerate(urls, 1):
        prefix = f"{i} " if numbering else ""
        try:
            progress(f"Fetching: {url}")
            title, html_body = fetch_article(url)
            display_title = f"{prefix}{title}"
            html_body, images = download_images(html_body, url)
            progress(f"  {display_title} — embedded {len(images)} image(s)")

            epub_path = url_to_epub(display_title, html_body, url, epub_dir(), image_items=images)
            progress(f"  EPUB: {epub_path.name} ({epub_path.stat().st_size // 1024}KB)")

            gmail_id = gc.send_epub_to_kindle(service, epub_path, display_title,
                                              config.gmail_address, config.kindle_email)
            store.record_url_sent(url, display_title, epub_path, config.kindle_email, gmail_id)
            report.sent += 1
            progress(f"  sent ({gmail_id})")
        except Exception as exc:
            report.errors.append(f"{url}: {exc}")
            progress(f"  ERROR: {exc}")

    progress(f"done: {report.summary()}")
    return report


def restore_sent(service, store: Store, config: Config, progress: ProgressFn = print) -> int:
    """Move sent messages back to the source label so they can be resent."""
    source_label_id = gc.ensure_label(service, config.source_label)
    sent_label_id = gc.get_label_id(service, config.sent_label)

    rows = store.sent_message_ids()
    restored = 0
    for message_id, subject in rows:
        if message_id.startswith("url:"):
            continue
        try:
            gc.restore_message(service, message_id, source_label_id, sent_label_id)
            store.mark_pending(message_id)
            progress(f"restored: {subject}")
            restored += 1
        except Exception as exc:
            progress(f"skipped {subject}: {exc}")
    progress(f"done: {restored} restored to \"{config.source_label}\"")
    return restored
