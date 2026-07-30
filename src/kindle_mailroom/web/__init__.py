"""Flask app factory with localhost-only security hardening."""

from __future__ import annotations

import os
import secrets
import threading

from flask import Flask, redirect, render_template, request, session, url_for

from .. import __version__
from ..config import Config
from ..core import auth
from .jobs import JobRunner
from .scheduler import start_scheduler

# Wizard + static + OAuth callback must stay reachable before setup completes.
# /shutdown too: a windowed desktop build has no Ctrl+C, so quitting has to
# work even mid-wizard.
_SETUP_EXEMPT_PREFIXES = ("/setup", "/oauth2", "/static", "/shutdown")


def create_app(start_background: bool = True) -> Flask:
    app = Flask(__name__)
    config = Config.load()
    app.secret_key = config.secret_key
    app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # setup uploads are tiny

    runner = JobRunner()
    app.extensions["job_runner"] = runner
    if start_background:
        start_scheduler(runner)

    @app.before_request
    def security_and_setup_gate():
        # DNS-rebinding guard: only accept requests addressed to localhost.
        host = (request.host or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            return "Forbidden", 403

        # CSRF: every POST must carry the session token. A malicious website
        # you visit could otherwise fire POSTs at 127.0.0.1 and send email
        # from your Gmail.
        if request.method == "POST":
            token = session.get("csrf_token")
            sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
            if not token or sent != token:
                return "CSRF token missing or invalid", 400

        # Setup gate: until config + auth exist, everything routes to the wizard.
        if request.path.startswith(_SETUP_EXEMPT_PREFIXES):
            return None
        current = Config.load()
        if not (current.is_complete and auth.has_token()):
            return redirect(url_for("setup.start"))
        return None

    @app.context_processor
    def inject_csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(16)
        return {"csrf_token": session["csrf_token"]}

    @app.after_request
    def identify(response):
        # Lets the desktop launcher tell "a Kindle Mailroom I already
        # started" apart from "some other thing answering on this port"
        # when it probes for an already-running instance.
        response.headers["X-Kindle-Mailroom"] = __version__
        return response

    @app.route("/shutdown", methods=["POST"])
    def shutdown():
        # Ctrl+C equivalent for the windowed desktop build, which has no
        # console to interrupt. Exposed to everyone (pipx users too) so
        # there's one obvious way to stop the server from the browser.
        if runner.busy and not request.form.get("force"):
            return render_template("shutdown_confirm.html"), 409
        response = render_template("shutdown.html")
        threading.Timer(0.5, os._exit, args=(0,)).start()
        return response

    from .views.dashboard import bp as dashboard_bp
    from .views.settings import bp as settings_bp
    from .views.setup import bp as setup_bp
    from .views.urlsend import bp as urlsend_bp

    app.register_blueprint(setup_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(urlsend_bp)
    app.register_blueprint(settings_bp)

    return app
