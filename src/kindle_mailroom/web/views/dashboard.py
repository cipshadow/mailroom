"""Dashboard: status, send-now, job progress, delivery history."""

from __future__ import annotations

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for

from ...config import Config, db_path, epub_dir
from ...core import auth, pipeline
from ...core.epub_build import url_to_epub
from ...core.gmail_client import build_service, send_epub_to_kindle
from ...core.store import Store
from ..jobs import JobBusyError, JobRunner
from ..scheduler import is_due

bp = Blueprint("dashboard", __name__)


def _runner() -> JobRunner:
    return current_app.extensions["job_runner"]


def _auth_status() -> tuple[bool, str]:
    try:
        auth.load_credentials()
        return True, "Connected"
    except auth.NotAuthenticatedError as exc:
        return False, str(exc)


def _mark_batch_headers(deliveries: list[dict]) -> list[dict]:
    """Flag the first row of each consecutive run sharing a batch_id, so the
    template can show the send timestamp once per job run instead of once
    per row - rows from one "Send now" click are otherwise indistinguishable
    from unrelated sends at a glance. Rows without a batch_id (sent before
    this tracking existed) always get their own header.

    The list is newest-first, so the row where a batch is first encountered
    is its *last* send, not its first - batch_started_at looks up the
    earliest sent_at in the group instead, so the header reflects when the
    batch began."""
    batch_started_at: dict[str, str] = {}
    for d in deliveries:
        bid = d["batch_id"]
        sent = d["sent_at"] or ""
        if bid is not None and (bid not in batch_started_at or sent < batch_started_at[bid]):
            batch_started_at[bid] = sent

    prev_batch = object()
    for d in deliveries:
        current = d["batch_id"]
        d["show_sent_header"] = current is None or current != prev_batch
        d["batch_started_at"] = batch_started_at.get(current, d["sent_at"])
        prev_batch = current
    return deliveries


@bp.route("/")
def index():
    config = Config.load()
    store = Store(db_path())
    try:
        deliveries = _mark_batch_headers(store.list_deliveries(limit=15))
    finally:
        store.close()
    auth_ok, auth_message = _auth_status()
    runner = _runner()
    return render_template(
        "dashboard.html",
        config=config,
        deliveries=deliveries,
        auth_ok=auth_ok,
        auth_message=auth_message,
        job=runner.current.as_dict() if runner.current else None,
        job_busy=runner.busy,
        schedule_due=is_due(config),
    )


def _send_work(digest_override: bool | None, dry_run: bool):
    def work(job):
        config = Config.load()
        service = build_service(auth.load_credentials())
        store = Store(db_path())
        try:
            report = pipeline.send_labelled(
                service, store, config,
                digest=digest_override, dry_run=dry_run, progress=job.log_line,
            )
        finally:
            store.close()
        return report.summary()

    return work


@bp.route("/send", methods=["POST"])
def send_now():
    digest_override = None
    if request.form.get("mode") == "digest":
        digest_override = True
    elif request.form.get("mode") == "single":
        digest_override = False
    dry_run = bool(request.form.get("dry_run"))
    try:
        _runner().submit("send", _send_work(digest_override, dry_run))
    except JobBusyError:
        flash("A job is already running — wait for it to finish.", "error")
    return redirect(url_for("dashboard.index"))


@bp.route("/send-test", methods=["POST"])
def send_test():
    def work(job):
        config = Config.load()
        service = build_service(auth.load_credentials())
        job.log_line(f"Sending a test document to {config.kindle_email}...")
        epub_path = url_to_epub(
            "Kindle Mailroom test",
            "<p>If you can read this on your Kindle, everything is set up correctly. "
            "Newsletters you label in Gmail will arrive just like this.</p>",
            "https://github.com/",
            epub_dir(),
        )
        send_epub_to_kindle(service, epub_path, "Kindle Mailroom test",
                            config.gmail_address, config.kindle_email)
        job.log_line("Test sent. It can take a few minutes to appear on the Kindle.")
        job.log_line("If it never arrives, check Amazon's approved sender list (see docs).")
        return "test sent"

    try:
        _runner().submit("test", work)
    except JobBusyError:
        flash("A job is already running — wait for it to finish.", "error")
    return redirect(url_for("dashboard.index"))


@bp.route("/jobs/current")
def current_job():
    runner = _runner()
    if not runner.current:
        return jsonify({"state": "idle"})
    return jsonify(runner.current.as_dict())


@bp.route("/history")
def history():
    store = Store(db_path())
    try:
        deliveries = _mark_batch_headers(store.list_deliveries(limit=500))
    finally:
        store.close()
    return render_template("history.html", deliveries=deliveries, job_busy=_runner().busy,
                           config=Config.load())


@bp.route("/restore", methods=["POST"])
def restore():
    def work(job):
        config = Config.load()
        service = build_service(auth.load_credentials())
        store = Store(db_path())
        try:
            restored = pipeline.restore_sent(service, store, config, progress=job.log_line)
        finally:
            store.close()
        return f"{restored} restored"

    try:
        _runner().submit("restore", work)
        flash(f'Restoring sent messages back to your "{Config.load().source_label}" label…', "ok")
    except JobBusyError:
        flash("A job is already running — wait for it to finish.", "error")
    return redirect(url_for("dashboard.history"))
