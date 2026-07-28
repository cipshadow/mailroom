import io

from kindle_mailroom.core import images
from kindle_mailroom.core.images import fetch_image, parse_declared_length, url_width_hint


def _jpeg_bytes(width, height):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (width, height), (100, 100, 100)).save(buf, "JPEG")
    return buf.getvalue()


class _FakeResponse:
    def __init__(self, content, content_type="image/jpeg"):
        self.content = content
        self.headers = {"content-type": content_type}

    def raise_for_status(self):
        pass


def test_parse_declared_length():
    assert parse_declared_length("146") == 146
    assert parse_declared_length("146px") == 146
    assert parse_declared_length("100%") is None
    assert parse_declared_length("auto") is None
    assert parse_declared_length(None) is None


def test_url_width_hint():
    assert url_width_hint("https://cdn.example.com/chart,w_1100,c_limit/chart.png") == 1100
    assert url_width_hint("https://cdn.example.com/plain.png") is None


def test_declared_display_size_wins_over_decoded_pixels(monkeypatch):
    # Substack serves a headshot at full resolution (1200x1200) but the email
    # displays it at 146x146 via width/height attributes. The embedded image
    # must be stamped with the DISPLAY size, not the file's decoded size -
    # otherwise Kindle blows a small headshot up to full column width.
    monkeypatch.setattr(images.requests, "get", lambda *a, **kw: _FakeResponse(_jpeg_bytes(1200, 1200)))
    result = fetch_image("https://x/headshot.jpg", 0, declared_width=146, declared_height=146)
    assert result is not None
    _, _, _, width, height = result
    assert (width, height) == (146, 146)


def test_missing_declared_dimension_filled_from_aspect_ratio(monkeypatch):
    monkeypatch.setattr(images.requests, "get", lambda *a, **kw: _FakeResponse(_jpeg_bytes(800, 400)))
    result = fetch_image("https://x/wide.jpg", 0, declared_width=200, declared_height=None)
    assert result is not None
    _, _, _, width, height = result
    assert width == 200
    assert height == 100  # 400/800 * 200


def test_no_declared_size_falls_back_to_decoded_pixels(monkeypatch):
    monkeypatch.setattr(images.requests, "get", lambda *a, **kw: _FakeResponse(_jpeg_bytes(1100, 700)))
    result = fetch_image("https://x/chart.jpg", 0)
    assert result is not None
    _, _, _, width, height = result
    assert (width, height) == (1100, 700)


def test_icon_dropped_when_only_one_dimension_declared_small(monkeypatch):
    # A HiDPI byline avatar: declared 40px wide (decorative chrome) even
    # though the file itself decodes to 144x144. Only one dimension being
    # declared shouldn't bypass the icon filter.
    monkeypatch.setattr(images.requests, "get", lambda *a, **kw: _FakeResponse(_jpeg_bytes(144, 144)))
    assert fetch_image("https://x/avatar.jpg", 0, declared_width=40, declared_height=None) is None


def test_real_content_image_not_dropped_as_icon(monkeypatch):
    monkeypatch.setattr(images.requests, "get", lambda *a, **kw: _FakeResponse(_jpeg_bytes(1100, 700)))
    assert fetch_image("https://x/chart.jpg", 0, declared_width=1100, declared_height=700) is not None
