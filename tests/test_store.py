import sqlite3
from pathlib import Path

from kindle_mailroom.core.models import GmailMessage
from kindle_mailroom.core.store import Store


def make_message(msg_id="m1"):
    return GmailMessage(
        message_id=msg_id,
        thread_id="t1",
        subject="Test Subject",
        sender="Writer <writer@newsletter.com>",
        date="2026-07-10T08:00:00+00:00",
        html_body="<p>hello</p>",
    )


def test_record_and_dedup(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    msg = make_message()
    assert not store.already_sent(msg.message_id)
    store.record_sent(msg, Path("/tmp/x.epub"), "you@kindle.com")
    assert store.already_sent(msg.message_id)
    # upsert keeps a single row
    store.record_sent(msg, Path("/tmp/y.epub"), "you@kindle.com")
    assert len(store.list_deliveries()) == 1
    store.close()


def test_digest_dedup(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    a, b = make_message("a"), make_message("b")
    store.record_sent(a, Path("/tmp/d.epub"), "you@kindle.com", digest_id="Newsletter-2026-07-06")
    assert store.digest_already_sent(["a", "zzz"])
    assert not store.digest_already_sent(["b", "zzz"])
    store.record_sent(b, Path("/tmp/d.epub"), "you@kindle.com")  # sent, but not as digest
    assert not store.digest_already_sent(["b"])
    store.close()


def test_mark_read_and_restore_flow(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    msg = make_message()
    store.record_sent(msg, Path("/tmp/x.epub"), "you@kindle.com")
    assert store.mark_read(msg.message_id)
    assert not store.mark_read("nonexistent")
    # read messages still count as delivered
    assert store.already_sent(msg.message_id)
    store.mark_pending(msg.message_id)
    assert not store.already_sent(msg.message_id)
    store.close()


def test_url_records(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    store.record_url_sent("https://ex.com/post", "Post", Path("/tmp/p.epub"),
                          "you@kindle.com", "gm123")
    rows = store.list_deliveries()
    assert rows[0]["message_id"] == "url:https://ex.com/post"
    assert rows[0]["status"] == "sent"
    store.close()


def test_migration_of_pre_digest_schema(tmp_path):
    db = tmp_path / "old.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute(
        """
        create table deliveries (
          gmail_message_id text primary key,
          thread_id text not null,
          subject text not null,
          sender text not null,
          gmail_date text,
          status text not null,
          epub_path text,
          sent_at text,
          read_at text,
          kindle_email text
        )
        """
    )
    conn.execute(
        "insert into deliveries values "
        "('old1', 't', 's', 'x@y.com', null, 'sent', null, '2026-01-01', null, 'k@kindle.com')"
    )
    conn.commit()
    conn.close()

    store = Store(db)  # triggers ALTER TABLE migration
    assert store.already_sent("old1")
    assert not store.digest_already_sent(["old1"])
    store.close()
