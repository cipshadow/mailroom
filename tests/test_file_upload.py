"""EPUB uploads from the user's device: validation, send pipeline, web flow."""

import io
import zipfile

import pytest
from test_web import complete_setup

from kindle_mailroom.config import Config, db_path
from kindle_mailroom.core import epub_upload, pipeline
from kindle_mailroom.core.store import Store

CONTAINER = (
    '<?xml version="1.0"?><container version="1.0" '
    'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
    '<rootfiles><rootfile full-path="content.opf" '
    'media-type="application/oebps-package+xml"/></rootfiles></container>'
)
OPF = (
    '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="2.0">'
    '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>{title}</dc:title>'
    "</metadata></package>"
)


def make_epub(title="My Book", container=True):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        if container:
            zf.writestr("META-INF/container.xml", CONTAINER)
            zf.writestr("content.opf", OPF.format(title=title))
    return buf.getvalue()


def write(tmp_path, data, name="book.epub"):
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_validate_accepts_epub_and_reads_title(tmp_path):
    path = write(tmp_path, make_epub("Dune"))
    epub_upload.validate_epub(path)
    assert epub_upload.read_title(path) == "Dune"


@pytest.mark.parametrize("data,fragment", [
    (b"", "empty"),
    (b"not a zip at all", "ZIP"),
    (make_epub(container=False), "container.xml"),
])
def test_validate_rejects_bad_files(tmp_path, data, fragment):
    with pytest.raises(epub_upload.EpubUploadError, match=fragment):
        epub_upload.validate_epub(write(tmp_path, data))


def test_validate_rejects_oversize(tmp_path, monkeypatch):
    monkeypatch.setattr(epub_upload, "MAX_EPUB_BYTES", 100)
    with pytest.raises(epub_upload.EpubUploadError, match="limit"):
        epub_upload.validate_epub(write(tmp_path, make_epub()))


def test_stage_path_rejects_traversal():
    assert epub_upload.stage_path("../../etc") is None
    assert epub_upload.stage_path("") is None


def _staged(tmp_path, title="My Book"):
    path = write(tmp_path, make_epub(title), "0.epub")
    return epub_upload.StagedFile(name="book.epub", title=title,
                                  sha256=epub_upload.sha256_of(path),
                                  size=path.stat().st_size, stored="0.epub")


def test_send_files_sends_records_and_skips_duplicates(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(pipeline.gc, "send_epub_to_kindle",
                        lambda *a, **kw: sent.append((a, kw)) or "gid")
    monkeypatch.setattr(pipeline.time, "sleep", lambda _: None)
    config = Config(gmail_address="me@gmail.com", kindle_email="me@kindle.com")
    store = Store(db_path())
    staged = _staged(tmp_path)

    report = pipeline.send_files(None, store, config, tmp_path, [staged], progress=lambda _: None)
    assert (report.sent, report.skipped) == (1, 0)
    assert sent[0][0][2] == "My Book"
    assert store.already_sent(staged.message_id)

    again = pipeline.send_files(None, store, config, tmp_path, [staged], progress=lambda _: None)
    assert (again.sent, again.skipped) == (0, 1)
    forced = pipeline.send_files(None, store, config, tmp_path, [staged],
                                 resend_duplicates=True, progress=lambda _: None)
    assert forced.sent == 1
    store.close()


def test_send_files_collects_errors(tmp_path, monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("smtp down")
    monkeypatch.setattr(pipeline.gc, "send_epub_to_kindle", boom)
    store = Store(db_path())
    report = pipeline.send_files(None, store, Config(), tmp_path, [_staged(tmp_path)],
                                 progress=lambda _: None)
    assert report.sent == 0 and "smtp down" in report.errors[0]
    store.close()


@pytest.fixture
def web():
    from kindle_mailroom.web import create_app

    app = create_app(start_background=False)
    app.config["TESTING"] = True
    client = app.test_client()
    complete_setup()
    return app, client


def _csrf(client):
    client.get("/files", base_url="http://localhost:8377")
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def test_upload_review_page_lists_files(web):
    _, client = web
    token = _csrf(client)
    resp = client.post("/files/upload", base_url="http://localhost:8377", data={
        "csrf_token": token, "mode": "review",
        "files": [(io.BytesIO(make_epub("Dune")), "dune.epub"),
                  (io.BytesIO(b"junk"), "bad.epub"),
                  (io.BytesIO(b"x"), "notes.txt")],
    }, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert b"Dune" in resp.data and b"Send selected" in resp.data
    assert b"bad.epub" not in resp.data.split(b"<table>")[1]


def test_upload_requires_csrf(web):
    _, client = web
    resp = client.post("/files/upload", base_url="http://localhost:8377",
                       data={"files": (io.BytesIO(make_epub()), "a.epub")},
                       content_type="multipart/form-data")
    assert resp.status_code == 400


def test_send_with_expired_stage_redirects(web):
    _, client = web
    token = _csrf(client)
    resp = client.post("/files/send", base_url="http://localhost:8377",
                       data={"csrf_token": token, "stage_id": "../../x", "stored": "0.epub"})
    assert resp.status_code == 302 and "/files" in resp.headers["Location"]
