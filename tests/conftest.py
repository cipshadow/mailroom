import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--golden-update",
        action="store_true",
        default=False,
        help="Regenerate tests/golden/*.txt instead of asserting against them.",
    )


@pytest.fixture
def golden_update(request):
    return request.config.getoption("--golden-update")


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Every test gets its own data directory; nothing touches the real one."""
    monkeypatch.setenv("KINDLE_MAILROOM_DATA_DIR", str(tmp_path / "data"))
    yield tmp_path / "data"


@pytest.fixture
def fake_image(monkeypatch):
    """Replace network image fetching with a small in-memory JPEG."""
    import io

    from PIL import Image

    def make(width=200, height=100):
        buf = io.BytesIO()
        Image.new("RGB", (width, height), (120, 40, 200)).save(buf, "JPEG")
        return buf.getvalue()

    data = make()

    def fake_fetch(url, idx, declared_width=None, declared_height=None):
        return f"images/img{idx:03d}.jpg", "image/jpeg", data, 200, 100

    monkeypatch.setattr("kindle_mailroom.core.epub_build.fetch_image", fake_fetch)
    monkeypatch.setattr("kindle_mailroom.core.urlfetch.fetch_image", fake_fetch)
    return data
