"""Sender display names and digest grouping.

extract_sender_domain feeds the sender_domain DB column and the fallback
grouping label for senders with no display name. Digest grouping itself uses
extract_sender_name: grouping by domain put every Substack author - they all
send from a *.substack.com-family address - into one combined weekly digest
regardless of who wrote it, which is the bug this module now guards against.
"""

import pytest

from kindle_mailroom.core.models import (
    GmailMessage,
    digest_title,
    extract_sender_domain,
    extract_sender_name,
    group_messages_by_sender_week,
)


@pytest.mark.parametrize(
    "sender,expected",
    [
        # The common case: a plain .com newsletter.
        ("Stratechery <news@stratechery.com>", "Stratechery"),
        ("Lenny's Newsletter <lenny@substack.com>", "Substack"),
        # Non-.com TLDs used to return the TLD itself - "Io", "Org", "Net",
        # "To" - which collapsed unrelated senders into one digest.
        ("Ghost <hello@ghost.io>", "Ghost"),
        ("Every <editor@every.to>", "Every"),
        ("Some Org <news@foo.org>", "Foo"),
        ("Netty <y@z.net>", "Z"),
        # Multi-label public suffixes keep the label before the suffix.
        ("Beeb <news@bbc.co.uk>", "Bbc"),
        ("Uni <x@dept.ac.uk>", "Dept"),
        # Subdomains resolve to the registrable label, not the subdomain.
        ("Mailer <n@mail.example.com>", "Example"),
        # Degenerate but shouldn't crash.
        ("Odd <a@b>", "B"),
        ("no angle brackets here", "Unknown"),
        ("", "Unknown"),
    ],
)
def test_extract_sender_domain(sender, expected):
    assert extract_sender_domain(sender) == expected


def test_distinct_senders_do_not_collapse():
    """The digest-grouping regression: two unrelated .org/.io senders must
    not share a grouping key just because they share a TLD."""
    a = extract_sender_domain("Alpha <news@alpha.org>")
    b = extract_sender_domain("Beta <news@beta.org>")
    c = extract_sender_domain("Gamma <news@gamma.io>")
    assert len({a, b, c}) == 3, (a, b, c)


@pytest.mark.parametrize(
    "sender,expected",
    [
        ("Stratechery <news@stratechery.com>", "Stratechery"),
        # The actual bug report: two different Substack authors must not
        # both resolve to "Substack".
        ("Lenny's Newsletter <lenny@substack.com>", "Lenny's Newsletter"),
        ("Platformer <casey@substack.com>", "Platformer"),
        # Quoted display names (RFC 5322 allows a quoted-string local part).
        ('"Stratechery, LLC" <news@stratechery.com>', "Stratechery, LLC"),
        # MIME-encoded (RFC 2047) header, as Gmail can hand back for
        # non-ASCII names.
        ("=?UTF-8?B?TMOpbm55?= <lenny@substack.com>", "Lénny"),
        # No display name at all - falls back to the domain label rather
        # than crashing or returning an empty group key.
        ("<news@example.com>", "Example"),
        ("", "Unknown"),
    ],
)
def test_extract_sender_name(sender, expected):
    assert extract_sender_name(sender) == expected


def test_distinct_substack_authors_do_not_collapse():
    """The actual reported bug: grouping by domain merged every Substack
    newsletter into one weekly digest. Grouping by name must not."""
    a = extract_sender_name("Lenny's Newsletter <lenny@substack.com>")
    b = extract_sender_name("Platformer <casey@substack.com>")
    c = extract_sender_name("Stratechery <news@stratechery.com>")
    assert len({a, b, c}) == 3, (a, b, c)


@pytest.mark.parametrize(
    "week_start,expected",
    [
        ("2026-07-06", "Lenny's Newsletter - 06/7 digest"),
        ("2026-01-01", "Lenny's Newsletter - 01/1 digest"),
        ("2026-12-25", "Lenny's Newsletter - 25/12 digest"),
    ],
)
def test_digest_title_format(week_start, expected):
    assert digest_title("Lenny's Newsletter", week_start) == expected


def _msg(sender, date="2026-07-06T10:00:00"):
    return GmailMessage(message_id=sender, thread_id=sender, subject="s",
                        sender=sender, date=date, html_body="<p>hi</p>")


def test_group_messages_by_sender_week_keeps_substack_authors_separate():
    messages = [
        _msg("Lenny's Newsletter <lenny@substack.com>"),
        _msg("Platformer <casey@substack.com>"),
        _msg("Lenny's Newsletter <lenny@substack.com>"),
    ]
    groups = group_messages_by_sender_week(messages)
    keys = {name for name, _week in groups}
    assert keys == {"Lenny's Newsletter", "Platformer"}
    assert len(groups[("Lenny's Newsletter", "2026-07-06")]) == 2
    assert len(groups[("Platformer", "2026-07-06")]) == 1
