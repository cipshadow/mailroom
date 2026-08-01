"""Pipeline behaviour that touches the user's mailbox.

_skip_thin relabels messages in Gmail, which is a mutation - so it has to
respect dry_run. It previously did not, meaning `send --dry-run` stripped
the source label and marked thin messages read.
"""

from kindle_mailroom.config import Config
from kindle_mailroom.core import pipeline
from kindle_mailroom.core.models import GmailMessage

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
