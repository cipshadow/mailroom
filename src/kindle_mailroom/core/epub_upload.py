"""Validation and staging for EPUB files the user uploads from their device.

Uploaded files are sent to the Kindle exactly as received; nothing here
rewrites them. We only confirm each one really is an EPUB (a ZIP with an
OCF container), enforce a size cap, read the title for the Kindle subject
line, and hash the bytes so a re-upload can be flagged as a duplicate.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

from lxml import etree

from ..config import data_dir

# Gmail's attachment ceiling is 25 MB. [VERIFY: current Gmail API send limit]
MAX_EPUB_BYTES = 25 * 1024 * 1024
MAX_FILES_PER_UPLOAD = 20
STAGE_TTL_SECONDS = 24 * 60 * 60
_MAX_XML_BYTES = 2 * 1024 * 1024
_STAGE_ID = re.compile(r"^[0-9a-f]{32}$")
_CONTAINER = "META-INF/container.xml"


class EpubUploadError(ValueError):
    """The upload was rejected; the message is safe to show the user."""


@dataclass
class StagedFile:
    name: str       # original filename, for display
    title: str      # from EPUB metadata, falling back to the filename
    sha256: str
    size: int
    stored: str     # filename inside the stage directory

    @property
    def message_id(self) -> str:
        """Key used in the deliveries table."""
        return f"file:{self.sha256}"


def uploads_root() -> Path:
    path = data_dir() / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def new_stage_dir() -> tuple[str, Path]:
    import secrets

    purge_stale_stages()
    stage_id = secrets.token_hex(16)
    path = uploads_root() / stage_id
    path.mkdir()
    return stage_id, path


def stage_path(stage_id: str) -> Path | None:
    """The stage directory, or None for anything that isn't a stage we made."""
    if not _STAGE_ID.match(stage_id or ""):
        return None
    path = uploads_root() / stage_id
    return path if path.is_dir() else None


def purge_stale_stages() -> None:
    cutoff = time.time() - STAGE_TTL_SECONDS
    for child in uploads_root().iterdir():
        try:
            if child.is_dir() and child.stat().st_mtime < cutoff:
                shutil.rmtree(child, ignore_errors=True)
        except OSError:
            continue


def discard_stage(stage_id: str) -> None:
    path = stage_path(stage_id)
    if path:
        shutil.rmtree(path, ignore_errors=True)


def _read_member(zf: zipfile.ZipFile, name: str) -> bytes:
    with zf.open(name) as member:
        data = member.read(_MAX_XML_BYTES + 1)
    if len(data) > _MAX_XML_BYTES:
        raise EpubUploadError("its metadata is unreasonably large")
    return data


def _parse(data: bytes):
    parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)
    return etree.fromstring(data, parser)


def read_title(path: Path) -> str | None:
    """dc:title from the EPUB's package document, or None if unreadable."""
    try:
        with zipfile.ZipFile(path) as zf:
            container = _parse(_read_member(zf, _CONTAINER))
            rootfile = container.xpath("//*[local-name()='rootfile']/@full-path")
            if not rootfile:
                return None
            opf = _parse(_read_member(zf, rootfile[0]))
            titles = opf.xpath("//*[local-name()='title' and namespace-uri()='http://purl.org/dc/elements/1.1/']")
            text = " ".join((titles[0].text or "").split()) if titles else ""
            return text or None
    except (KeyError, zipfile.BadZipFile, etree.XMLSyntaxError, EpubUploadError, OSError):
        return None


def validate_epub(path: Path) -> None:
    """Raise EpubUploadError unless the file on disk is a plausible EPUB."""
    size = path.stat().st_size
    if size == 0:
        raise EpubUploadError("the file is empty")
    if size > MAX_EPUB_BYTES:
        raise EpubUploadError(
            f"it is {size / 1024 / 1024:.1f} MB; the limit is {MAX_EPUB_BYTES // 1024 // 1024} MB"
        )
    if not zipfile.is_zipfile(path):
        raise EpubUploadError("it is not a valid EPUB (not a ZIP archive)")
    with zipfile.ZipFile(path) as zf:
        if _CONTAINER not in zf.namelist():
            raise EpubUploadError("it is not a valid EPUB (no META-INF/container.xml)")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_name(filename: str) -> str:
    """Last path component only, control characters stripped."""
    name = re.split(r"[\\/]", filename or "")[-1]
    return re.sub(r"[\x00-\x1f\x7f]", "", name).strip() or "upload.epub"


def write_manifest(stage: Path, files: list[StagedFile]) -> None:
    (stage / "manifest.json").write_text(json.dumps([asdict(f) for f in files]), encoding="utf-8")


def read_manifest(stage: Path) -> list[StagedFile]:
    try:
        raw = json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
        return [StagedFile(**item) for item in raw]
    except (OSError, ValueError, TypeError):
        return []
