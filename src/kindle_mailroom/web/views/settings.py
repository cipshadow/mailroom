"""Settings: delivery options, schedule, and credential management."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ...config import DEFAULT_SENT_LABEL, DEFAULT_SOURCE_LABEL, Config, data_dir, is_kindle_address
from ...core import auth
from ...core.gmail_client import build_service, ensure_label

bp = Blueprint("settings", __name__)

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@bp.route("/settings")
def show():
    config = Config.load()
    return render_template(
        "settings.html",
        config=config,
        weekdays=WEEKDAYS,
        data_dir=str(data_dir()),
        has_token=auth.has_token(),
        has_client_secret=auth.has_client_secret(),
    )


@bp.route("/settings", methods=["POST"])
def save():
    config = Config.load()

    kindle_email = (request.form.get("kindle_email") or "").strip()
    if kindle_email and not is_kindle_address(kindle_email):
        flash("The Kindle address should end in @kindle.com or @free.kindle.com.", "error")
        return redirect(url_for("settings.show"))
    if kindle_email:
        config.kindle_email = kindle_email

    old_labels = (config.source_label, config.sent_label)
    config.source_label = (request.form.get("source_label") or config.source_label).strip() or DEFAULT_SOURCE_LABEL
    config.sent_label = (request.form.get("sent_label") or config.sent_label).strip() or DEFAULT_SENT_LABEL
    config.digest = bool(request.form.get("digest"))
    config.mark_read = bool(request.form.get("mark_read"))
    try:
        config.send_limit = max(1, min(50, int(request.form.get("send_limit") or config.send_limit)))
    except ValueError:
        pass

    config.schedule_enabled = bool(request.form.get("schedule_enabled"))
    frequency = request.form.get("schedule_frequency") or "daily"
    config.schedule_frequency = frequency if frequency in ("daily", "weekly") else "daily"
    schedule_time = (request.form.get("schedule_time") or "08:00").strip()
    try:
        hour, minute = (int(part) for part in schedule_time.split(":"))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            config.schedule_time = f"{hour:02d}:{minute:02d}"
    except ValueError:
        pass
    try:
        weekday = int(request.form.get("schedule_weekday") or 0)
        if 0 <= weekday <= 6:
            config.schedule_weekday = weekday
    except ValueError:
        pass

    config.save()

    # A renamed label doesn't exist in Gmail yet; without this the next send
    # dies with LabelNotFoundError. Best-effort - the pipeline's ensure_label
    # on the sent label plus get_label_id's clear error remain the backstop.
    if (config.source_label, config.sent_label) != old_labels:
        try:
            service = build_service(auth.load_credentials())
            ensure_label(service, config.source_label)
            ensure_label(service, config.sent_label)
        except Exception:
            flash(
                "Settings saved, but the Gmail label couldn't be created right "
                "now — it will be created on the next send.",
                "error",
            )
            return redirect(url_for("settings.show"))

    flash("Settings saved.", "ok")
    return redirect(url_for("settings.show"))


@bp.route("/settings/forget", methods=["POST"])
def forget():
    auth.forget_credentials()
    flash("Google credentials deleted from this machine. Run setup again to reconnect.", "ok")
    return redirect(url_for("setup.start"))
