"""Send article URLs to Kindle."""

from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from ...config import Config, db_path
from ...core import auth, pipeline
from ...core.gmail_client import build_service
from ...core.store import Store
from ..jobs import JobBusyError

bp = Blueprint("urlsend", __name__)


@bp.route("/url")
def form():
    runner = current_app.extensions["job_runner"]
    return render_template("url.html", job_busy=runner.busy)


@bp.route("/url", methods=["POST"])
def send():
    raw = request.form.get("urls") or ""
    urls = [line.strip() for line in raw.splitlines() if line.strip()]
    urls = [u for u in urls if u.startswith("http://") or u.startswith("https://")]
    if not urls:
        flash("Enter at least one http(s) URL, one per line.", "error")
        return redirect(url_for("urlsend.form"))

    number = bool(request.form.get("number"))
    chronological = bool(request.form.get("chronological"))

    def work(job):
        config = Config.load()
        service = build_service(auth.load_credentials())
        store = Store(db_path())
        try:
            report = pipeline.send_urls(
                service, store, config, urls,
                number=number, chronological=chronological, progress=job.log_line,
            )
        finally:
            store.close()
        return report.summary()

    runner = current_app.extensions["job_runner"]
    try:
        runner.submit("send-url", work)
    except JobBusyError:
        flash("A job is already running — wait for it to finish.", "error")
        return redirect(url_for("urlsend.form"))
    return redirect(url_for("dashboard.index"))
