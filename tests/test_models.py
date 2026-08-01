"""Sender display names and digest grouping.

extract_sender_domain feeds the digest grouping key, the sender_domain DB
column, and the EPUB title, so getting it wrong is visible in three places
at once.
"""

import pytest

from kindle_mailroom.core.models import extract_sender_domain


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
