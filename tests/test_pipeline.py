"""Pipeline behaviour that touches the user's mailbox.

_skip_thin relabels messages in Gmail, which is a mutation - so it has to
respect dry_run. It previously did not, meaning `send --dry-run` stripped
the source label and marked thin messages read.
"""

from kindle_mailroom.config import Config, db_path
from kindle_mailroom.core import pipeline
from kindle_mailroom.core.models import GmailMessage
from kindle_mailroom.core.store import Store

THIN_BODY = "<p>Only a few words here.</p>"
FAT_BODY = "<p>" + " ".join(["word"] * (pipeline.MIN_WORDS + 50)) + "</p>"


def _message(body):
    return GmailMessage(
        message_id="m1",
        thread_id="t1",
        subject="A thin one",
        sender="Someone <news@example.com>",
        date="2026-07-30T10:00:00",
        html_body=body,
    )


def _track_relabels(monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline.gc, "move_to_sent_label", lambda *a, **kw: calls.append(a))
    return calls


def test_dry_run_does_not_relabel_thin_messages(monkeypatch):
    calls = _track_relabels(monkeypatch)
    skipped = pipeline._skip_thin(
        None, Config(), _message(THIN_BODY), lambda _: None, dry_run=True
    )
    assert skipped is True, "a thin message should still be reported as skipped"
    assert calls == [], "dry run must not mutate the mailbox"


def test_real_run_does_relabel_thin_messages(monkeypatch):
    calls = _track_relabels(monkeypatch)
    skipped = pipeline._skip_thin(
        None, Config(), _message(THIN_BODY), lambda _: None, dry_run=False
    )
    assert skipped is True
    assert len(calls) == 1, "outside dry run the message should be moved on"


def test_substantial_messages_are_not_skipped(monkeypatch):
    calls = _track_relabels(monkeypatch)
    skipped = pipeline._skip_thin(
        None, Config(), _message(FAT_BODY), lambda _: None, dry_run=False
    )
    assert skipped is False
    assert calls == [], "a message over the word floor is left alone here"


def test_send_labelled_follows_config_for_limit_and_unread(monkeypatch):
    # limit=None / unread_only=None must fall back to the config values -
    # the web UI and scheduler call send_labelled without either argument.
    seen = {}

    def fake_fetch(service, label, limit, unread_only):
        seen["limit"], seen["unread_only"] = limit, unread_only
        return []

    monkeypatch.setattr(pipeline.gc, "fetch_labelled_messages", fake_fetch)
    config = Config()
    config.send_limit = 0
    config.unread_only = True
    pipeline.send_labelled(None, None, config, progress=lambda _: None)
    assert seen == {"limit": 0, "unread_only": True}

    # explicit arguments still win over config
    pipeline.send_labelled(None, None, config, limit=3, unread_only=False,
                           progress=lambda _: None)
    assert seen == {"limit": 3, "unread_only": False}


def test_message_ids_restricts_send_to_the_selected_subset(monkeypatch):
    # The dashboard's review screen lets the user uncheck emails before
    # sending - message_ids is how that selection reaches the pipeline.
    # Everything fetch_labelled_messages finds should still be fetched
    # (limit/unread_only are unaffected), but only the selected subset
    # should actually get sent.
    messages = [
        _digest_message("Sender A <a@example.com>", "Post A", "m1"),
        _digest_message("Sender B <b@example.com>", "Post B", "m2"),
        _digest_message("Sender C <c@example.com>", "Post C", "m3"),
    ]
    monkeypatch.setattr(pipeline.gc, "fetch_labelled_messages", lambda *a, **kw: messages)
    monkeypatch.setattr(pipeline.gc, "move_to_sent_label", lambda *a, **kw: None)

    sent_ids = []
    monkeypatch.setattr(
        pipeline.gc, "send_epub_to_kindle",
        lambda service, epub_path, title, from_address, kindle_email: sent_ids.append(title),
    )

    config = Config()
    config.digest = False
    store = Store(db_path())
    try:
        report = pipeline.send_labelled(
            None, store, config, message_ids={"m1", "m3"}, progress=lambda _: None,
        )
    finally:
        store.close()

    assert report.sent == 2
    assert sent_ids == ["Post A", "Post C"], "m2 was left unchecked, so it must not be sent"


def _digest_message(sender, subject, msg_id):
    return GmailMessage(
        message_id=msg_id, thread_id=msg_id, subject=subject, sender=sender,
        date="2026-07-06T10:00:00", html_body=FAT_BODY,
    )


def test_digest_mode_groups_by_sender_not_domain(monkeypatch, tmp_path):
    # The reported bug, exercised through the real pipeline entry point:
    # two different Substack authors must produce two separate digests,
    # each titled "[name] - dd/m digest", not one combined "Substack" digest.
    messages = [
        _digest_message("Lenny's Newsletter <lenny@substack.com>", "Post A", "m1"),
        _digest_message("Platformer <casey@substack.com>", "Post B", "m2"),
    ]
    monkeypatch.setattr(pipeline.gc, "move_to_sent_label", lambda *a, **kw: None)

    sent_titles = []

    def fake_send(service, epub_path, title, from_address, kindle_email):
        sent_titles.append(title)
        return "gmail-id"

    monkeypatch.setattr(pipeline.gc, "send_epub_to_kindle", fake_send)

    config = Config()
    config.digest = True
    store = Store(db_path())
    try:
        report = pipeline._send_digest_mode(
            None, store, config, messages, "test-batch", dry_run=False, resend=False,
            progress=lambda _: None,
        )
    finally:
        store.close()

    assert report.sent == 2, "one digest per author, not one combined digest"
    assert sorted(sent_titles) == [
        "Lenny's Newsletter - 06 Jul digest",
        "Platformer - 06 Jul digest",
    ]
