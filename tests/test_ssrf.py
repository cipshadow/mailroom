"""SSRF guard on outbound image fetches.

<img src> values come from newsletter HTML and fetched article pages, i.e.
from whoever wrote them. These tests pin the boundary that stops a crafted
image tag turning this process into a proxy for cloud metadata, loopback
services, and LAN admin pages.

Deliberately kept out of test_images.py, which autouses a fixture that
disables the guard so its decode/resize tests can use made-up hostnames.
"""

import io

from kindle_mailroom.core import images
from kindle_mailroom.core.images import fetch_image, get_if_public, is_public_url

PUBLIC = [(None, None, None, "", ("93.184.216.34", 0))]


def _jpeg_bytes(width, height):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (width, height), (100, 100, 100)).save(buf, "JPEG")
    return buf.getvalue()


class _FakeImageResponse:
    """A response good enough that fetch_image would happily embed it."""

    def __init__(self, content):
        self.content = content
        self.headers = {"content-type": "image/jpeg"}
        self.is_redirect = False
        self.is_permanent_redirect = False

    def raise_for_status(self):
        pass


def test_rejects_internal_targets():
    for url in (
        "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
        "http://127.0.0.1:9200/_cluster/health",
        "http://192.168.1.1/cgi-bin/admin",
        "http://10.0.0.5/internal",
        "http://172.16.0.1/x",
        "http://[::1]/x",
        "http://0.0.0.0/x",
    ):
        assert is_public_url(url) is False, url


def test_rejects_non_http_schemes():
    for url in (
        "file:///etc/passwd",
        "gopher://example.com/x",
        "ftp://example.com/f.png",
        "data:image/png;base64,AAAA",
    ):
        assert is_public_url(url) is False, url


def test_allows_ordinary_public_image(monkeypatch):
    monkeypatch.setattr(images.socket, "getaddrinfo", lambda *a, **kw: PUBLIC)
    assert is_public_url("https://cdn.example.com/chart.png") is True


def test_rejects_host_resolving_to_both_public_and_internal(monkeypatch):
    # A DNS answer mixing a public and an internal record must not pass on the
    # strength of the public one alone.
    monkeypatch.setattr(
        images.socket,
        "getaddrinfo",
        lambda *a, **kw: PUBLIC + [(None, None, None, "", ("127.0.0.1", 0))],
    )
    assert is_public_url("https://sneaky.example.com/x.png") is False


def test_unresolvable_host_is_rejected(monkeypatch):
    def _fail(*a, **kw):
        raise OSError("name or service not known")

    monkeypatch.setattr(images.socket, "getaddrinfo", _fail)
    assert is_public_url("https://nope.invalid/x.png") is False


def test_fetch_image_refuses_internal_url_even_when_it_would_succeed(monkeypatch):
    """The guard has to be wired into fetch_image, not merely available.

    The fake server here returns a perfectly good image, so if the guard is
    bypassed fetch_image returns a result and both assertions fail. Raising
    from the fake instead would prove nothing - fetch_image wraps the fetch
    in a bare `except Exception` and would swallow it into the same None.
    """
    served = []

    def _serve(url, *a, **kw):
        served.append(url)
        return _FakeImageResponse(_jpeg_bytes(800, 600))

    monkeypatch.setattr(images.requests, "get", _serve)
    assert fetch_image("http://169.254.169.254/latest/meta-data/", 0) is None
    assert served == [], f"guard bypassed, fetched: {served}"


def test_redirect_onto_internal_host_is_blocked(monkeypatch):
    """A public CDN that 302s to the metadata endpoint must not be followed."""

    class _Redirect:
        is_redirect = True
        is_permanent_redirect = False
        headers = {"location": "http://169.254.169.254/latest/meta-data/"}

        def raise_for_status(self):
            pass

    monkeypatch.setattr(images.requests, "get", lambda *a, **kw: _Redirect())
    monkeypatch.setattr(images.socket, "getaddrinfo", lambda *a, **kw: PUBLIC)
    assert get_if_public("https://cdn.example.com/img.png") is None


def test_redirect_chain_is_bounded(monkeypatch):
    """An endless public→public redirect loop gives up instead of hanging."""

    class _Redirect:
        is_redirect = True
        is_permanent_redirect = False
        headers = {"location": "https://cdn.example.com/next.png"}

        def raise_for_status(self):
            pass

    calls = []

    def _get(*a, **kw):
        calls.append(1)
        return _Redirect()

    monkeypatch.setattr(images.requests, "get", _get)
    monkeypatch.setattr(images.socket, "getaddrinfo", lambda *a, **kw: PUBLIC)
    assert get_if_public("https://cdn.example.com/img.png") is None
    assert len(calls) <= images.MAX_REDIRECTS + 1
