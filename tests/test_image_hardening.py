"""Untrusted-image hardening: download cap, decoder allow-list, pixel limit,
and the golden-file rule that a missing golden must fail."""

import io

import pytest

from kindle_mailroom.core import images
from kindle_mailroom.core.images import ImageTooLarge, fetch_image, read_capped

PUBLIC = [(2, 1, 6, "", ("93.184.216.34", 0))]


def _encode(fmt, width=400, height=300, mode="RGB"):
    from PIL import Image

    buf = io.BytesIO()
    Image.new(mode, (width, height), 100).save(buf, fmt)
    return buf.getvalue()


class _Resp:
    """Streaming-capable stand-in for requests.Response."""

    def __init__(self, body, headers=None, chunk=1024):
        self._body = body
        self._chunk = chunk
        self.headers = {"content-type": "image/jpeg", **(headers or {})}
        self.is_redirect = False
        self.is_permanent_redirect = False
        self.closed = False
        self.served_chunks = 0

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size=1):
        for i in range(0, len(self._body), self._chunk):
            self.served_chunks += 1
            yield self._body[i : i + self._chunk]

    def close(self):
        self.closed = True


@pytest.fixture
def serve(monkeypatch):
    """Make fetch_image's HTTP call return a given response from a 'public' host."""
    monkeypatch.setattr(images.socket, "getaddrinfo", lambda *a, **kw: PUBLIC)

    def _install(resp):
        monkeypatch.setattr(images.requests, "get", lambda *a, **kw: resp)
        return resp

    return _install


def test_ordinary_jpeg_still_works(serve):
    serve(_Resp(_encode("JPEG")))
    assert fetch_image("https://x/a.jpg", 0) is not None


@pytest.mark.parametrize("fmt", ["BMP", "TIFF", "PPM"])
def test_formats_outside_the_allow_list_are_rejected(serve, fmt):
    serve(_Resp(_encode(fmt)))
    assert fetch_image("https://x/a.img", 0) is None


@pytest.mark.parametrize("fmt", ["PNG", "GIF", "WEBP"])
def test_allowed_formats_decode(serve, fmt):
    serve(_Resp(_encode(fmt)))
    assert fetch_image("https://x/a.img", 0) is not None


@pytest.mark.filterwarnings("ignore::PIL.Image.DecompressionBombWarning")
def test_decompression_bomb_is_refused_before_pixels_decode(serve, monkeypatch):
    from PIL import Image

    # ~64M pixels of one value: compresses to tens of KB, would allocate ~64MB.
    bomb = _encode("PNG", 8000, 8000, mode="L")
    assert len(bomb) < images.MAX_IMAGE_BYTES
    decoded = []
    real_load = Image.Image.load
    monkeypatch.setattr(Image.Image, "load", lambda self, *a, **kw: decoded.append(1) or real_load(self, *a, **kw))
    serve(_Resp(bomb))
    assert fetch_image("https://x/bomb.png", 0) is None
    assert decoded == [], "pixels were decoded before the size check"


def test_declared_oversize_body_is_rejected_without_reading(serve):
    resp = serve(_Resp(_encode("JPEG"), headers={"content-length": str(images.MAX_IMAGE_BYTES + 1)}))
    assert fetch_image("https://x/a.jpg", 0) is None
    assert resp.served_chunks == 0


def test_undeclared_oversize_body_stops_streaming_at_the_cap(serve, monkeypatch):
    monkeypatch.setattr(images, "MAX_IMAGE_BYTES", 5_000)
    resp = serve(_Resp(b"\xff" * 1_000_000, chunk=1_000))  # no content-length header
    assert fetch_image("https://x/a.jpg", 0) is None
    assert resp.served_chunks <= 6, f"kept reading after the cap: {resp.served_chunks} chunks"
    assert resp.closed


def test_read_capped_returns_body_under_the_cap():
    assert read_capped(_Resp(b"a" * 3_000), limit=5_000) == b"a" * 3_000


def test_read_capped_raises_over_the_cap():
    with pytest.raises(ImageTooLarge):
        read_capped(_Resp(b"a" * 6_000), limit=5_000)


def test_missing_golden_file_fails_instead_of_being_written(tmp_path, monkeypatch):
    import golden

    monkeypatch.setattr(golden, "GOLDEN_DIR", tmp_path)
    monkeypatch.setattr(golden, "canonicalize", lambda p: "canonical text")
    with pytest.raises(AssertionError, match="Missing golden file"):
        golden.assert_golden(tmp_path / "x.epub", "no_such_case")
    assert not (tmp_path / "no_such_case.txt").exists()
    golden.assert_golden(tmp_path / "x.epub", "no_such_case", update=True)
    assert (tmp_path / "no_such_case.txt").read_text() == "canonical text"
