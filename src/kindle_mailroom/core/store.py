"""SQLite delivery tracking.

Schema is identical to the original personal tool, so an existing database can
be dropped into the data directory and history carries over.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import GmailMessage, extract_sender_domain


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Store:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.execute(
            """
            create table if not exists deliveries (
              gmail_message_id text primary key,
              thread_id text not null,
              subject text not null,
              sender text not null,
              gmail_date text,
              status text not null,
              epub_path text,
              sent_at text,
              read_at text,
              kindle_email text,
              digest_id text,
              sender_domain text,
              batch_id text
            )
            """
        )
        # migrate a pre-digest database if needed
        try:
            self.conn.execute("select digest_id from deliveries limit 1")
        except sqlite3.OperationalError:
            self.conn.execute("alter table deliveries add column digest_id text")
            self.conn.execute("alter table deliveries add column sender_domain text")
        # migrate a pre-batch database if needed
        try:
            self.conn.execute("select batch_id from deliveries limit 1")
        except sqlite3.OperationalError:
            self.conn.execute("alter table deliveries add column batch_id text")

    def close(self) -> None:
        self.conn.close()

    def already_sent(self, message_id: str) -> bool:
        row = self.conn.execute(
            "select status from deliveries where gmail_message_id = ?",
            (message_id,),
        ).fetchone()
        return bool(row and row[0] in {"sent", "read"})

    def digest_already_sent(self, message_ids: list[str]) -> bool:
        return any(
            self.conn.execute(
                "select status from deliveries where gmail_message_id = ? and status in ('sent', 'read')",
                (message_id,),
            ).fetchone()
            for message_id in message_ids
        )

    def record_sent(
        self,
        message: GmailMessage,
        epub_path: Path,
        kindle_email: str,
        digest_id: str | None = None,
        sender_domain: str | None = None,
        batch_id: str | None = None,
    ) -> None:
        self.conn.execute(
            """
            insert into deliveries (
              gmail_message_id, thread_id, subject, sender, gmail_date, status,
              epub_path, sent_at, kindle_email, digest_id, sender_domain, batch_id
            )
            values (?, ?, ?, ?, ?, 'sent', ?, ?, ?, ?, ?, ?)
            on conflict(gmail_message_id) do update set
              status = 'sent',
              epub_path = excluded.epub_path,
              sent_at = excluded.sent_at,
              kindle_email = excluded.kindle_email,
              digest_id = excluded.digest_id,
              sender_domain = excluded.sender_domain,
              batch_id = excluded.batch_id
            """,
            (
                message.message_id,
                message.thread_id,
                message.subject,
                message.sender,
                message.date,
                str(epub_path),
                now_iso(),
                kindle_email,
                digest_id,
                sender_domain or extract_sender_domain(message.sender),
                batch_id,
            ),
        )
        self.conn.commit()

    def record_url_sent(self, url: str, title: str, epub_path: Path,
                        kindle_email: str, gmail_id: str, batch_id: str | None = None) -> None:
        self.conn.execute(
            """
            insert or replace into deliveries
              (gmail_message_id, thread_id, subject, sender, gmail_date,
               status, epub_path, sent_at, kindle_email, sender_domain, batch_id)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"url:{url}",
                gmail_id,
                title,
                url,
                None,
                "sent",
                str(epub_path),
                now_iso(),
                kindle_email,
                url.split("/")[2] if "/" in url else url,
                batch_id,
            ),
        )
        self.conn.commit()

    def list_deliveries(self, limit: int = 200) -> list[dict]:
        rows = self.conn.execute(
            """
            select gmail_message_id, subject, sender, status, sent_at, read_at, digest_id, gmail_date, batch_id
            from deliveries
            order by coalesce(read_at, sent_at) desc
            limit ?
            """,
            (limit,),
        ).fetchall()
        keys = ["message_id", "subject", "sender", "status", "sent_at", "read_at", "digest_id", "gmail_date", "batch_id"]
        return [dict(zip(keys, row)) for row in rows]

    def sent_message_ids(self) -> list[tuple[str, str]]:
        """(message_id, subject) for everything with status 'sent' — restore candidates."""
        return self.conn.execute(
            "select gmail_message_id, subject from deliveries where status = 'sent'"
        ).fetchall()

    def mark_pending(self, message_id: str) -> None:
        self.conn.execute(
            "update deliveries set status = 'pending' where gmail_message_id = ?",
            (message_id,),
        )
        self.conn.commit()

    def mark_read(self, message_id: str) -> bool:
        cur = self.conn.execute(
            """
            update deliveries
            set status = 'read', read_at = coalesce(read_at, ?)
            where gmail_message_id = ?
            """,
            (now_iso(), message_id),
        )
        self.conn.commit()
        return cur.rowcount > 0
