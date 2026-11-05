"""Send EPUB files from the user's device to the Kindle."""

from __future__ import annotations

import shutil

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from ...config import Config, db_path
from ...core import auth, pipeline
from ...core.epub_upload import (
    MAX_EPUB_BYTES,
    MAX_FILES_PER_UPLOAD,
    EpubUploadError,
    StagedFile,
    discard_stage,
    display_name,
    new_stage_dir,
    read_manifest,
    read_title,
    sha256_of,
    stage_path,
    validate_epub,
    write_manifest,
)
from ...core.gmail_client import build_service
from ...core.store import Store, now_iso
from ..jobs import JobBusyError

bp = Blueprint("filesend", __name__)


@bp.route("/files")
def form():
    runner = current_app.extensions["job_runner"]
    return render_template(
        "files.html",
        config=Config.load(),
        job_busy=runner.busy,
        max_mb=MAX_EPUB_BYTES // 1024 // 1024,
        max_files=MAX_FILES_PER_UPLOAD,
    )


def _stage_uploads(uploads) -> tuple[str, list[StagedFile]]:
    """Validate and store each upload under a fresh stage directory. Rejected
    files are reported with flash() and left out; a stage with no accepted
    files is deleted."""
    stage_id, stage = new_stage_dir()
    staged: list[StagedFile] = []
    for upload in uploads[:MAX_FILES_PER_UPLOAD]:
        name = display_name(upload.filename or "")
        if not name.lower().endswith(".epub"):
            flash(f"{name}: only .epub files are supported.", "error")
            continue
        stored = f"{len(staged)}.epub"
        target = stage / stored
        upload.save(target)
        try:
            validate_epub(target)
        except EpubUploadError as exc:
            target.unlink(missing_ok=True)
            flash(f"{name}: {exc}.", "error")
            continue
        title = read_title(target) or name.rsplit(".", 1)[0]
        staged.append(StagedFile(name=name, title=title, sha256=sha256_of(target),
                                 size=target.stat().st_size, stored=stored))
    if len(uploads) > MAX_FILES_PER_UPLOAD:
        flash(f"Only the first {MAX_FILES_PER_UPLOAD} files were used.", "error")
    if staged:
        write_manifest(stage, staged)
    else:
        shutil.rmtree(stage, ignore_errors=True)
    return stage_id, staged


def _submit(stage_id: str, files: list[StagedFile], *, include_gmail: bool,
            resend_duplicates: bool):
    stage = stage_path(stage_id)
    assert stage is not None

    def work(job):
        config = Config.load()
        service = build_service(auth.load_credentials())
        store = Store(db_path())
        batch_id = now_iso()
        try:
            report = pipeline.send_files(
                service, store, config, stage, files,
                batch_id=batch_id, resend_duplicates=resend_duplicates,
                progress=job.log_line,
            )
            if include_gmail:
                gmail_report = pipeline.send_labelled(
                    service, store, config, batch_id=batch_id, progress=job.log_line)
                report.sent += gmail_report.sent
                report.skipped += gmail_report.skipped
                report.errors += gmail_report.errors
        finally:
            store.close()
            discard_stage(stage_id)
        return report.summary()

    runner = current_app.extensions["job_runner"]
    try:
        runner.submit("send-files", work)
    except JobBusyError:
        discard_stage(stage_id)
        flash("A job is already running, wait for it to finish.", "error")
        return redirect(url_for("filesend.form"))
    return redirect(url_for("dashboard.index"))


@bp.route("/files/upload", methods=["POST"])
def upload():
    uploads = [f for f in request.files.getlist("files") if f and f.filename]
    if not uploads:
        flash("Choose at least one .epub file.", "error")
        return redirect(url_for("filesend.form"))

    stage_id, staged = _stage_uploads(uploads)
    if not staged:
        return redirect(url_for("filesend.form"))

    include_gmail = bool(request.form.get("include_gmail"))
    if request.form.get("mode") == "immediate":
        return _submit(stage_id, staged, include_gmail=include_gmail, resend_duplicates=False)

    store = Store(db_path())
    try:
        duplicates = {f.sha256 for f in staged if store.already_sent(f.message_id)}
    finally:
        store.close()
    runner = current_app.extensions["job_runner"]
    return render_template(
        "files_review.html",
        stage_id=stage_id,
        files=staged,
        duplicates=duplicates,
        include_gmail=include_gmail,
        config=Config.load(),
        job_busy=runner.busy,
    )


@bp.route("/files/send", methods=["POST"])
def send():
    stage_id = request.form.get("stage_id", "")
    stage = stage_path(stage_id)
    if stage is None:
        flash("That upload expired. Choose the files again.", "error")
        return redirect(url_for("filesend.form"))

    selected = set(request.form.getlist("stored"))
    files = [f for f in read_manifest(stage) if f.stored in selected]
    if not files:
        discard_stage(stage_id)
        flash("Nothing selected, nothing was sent.", "error")
        return redirect(url_for("filesend.form"))

    # Ticking a file the review flagged as already sent is an explicit resend.
    return _submit(stage_id, files, include_gmail=bool(request.form.get("include_gmail")),
                   resend_duplicates=True)
