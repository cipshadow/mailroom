"""Flask app factory with localhost-only security hardening."""

from __future__ import annotations

import secrets

from flask import Flask, redirect, request, session, url_for

from ..config import Config
from ..core import auth
from .jobs import JobRunner
from .scheduler import start_scheduler

# Wizard + static + OAuth callback must stay reachable before setup completes.
_SETUP_EXEMPT_PREFIXES = ("/setup", "/oauth2", "/static")


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

    from .views.dashboard import bp as dashboard_bp
    from .views.settings import bp as settings_bp
    from .views.setup import bp as setup_bp
    from .views.urlsend import bp as urlsend_bp

    app.register_blueprint(setup_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(urlsend_bp)
    app.register_blueprint(settings_bp)

    return app
