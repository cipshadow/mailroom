"""First-run setup wizard: OAuth client → Google sign-in → delivery settings."""

from __future__ import annotations

import os
import re

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from googleapiclient.errors import HttpError

from ...config import DEFAULT_SOURCE_LABEL, Config, is_kindle_address
from ...core import auth
from ...core.gmail_client import build_service, ensure_label, get_profile_email

bp = Blueprint("setup", __name__)


def _step(config: Config) -> int:
    """1-3 = current wizard step; 4 = setup finished (all steps done).

    Step 2 needs both a token *and* a captured gmail_address — a token
    alone isn't "connected". If reading the profile email failed (e.g. the
    Gmail API wasn't enabled yet), the token is still saved but the address
    stays blank, and config.is_complete can then never become true. Without
    this check the wizard would show step 2 as done and strand the user at
    step 3 with no way back to retry the connection.
    """
    if not auth.has_client_secret():
        return 1
    if not auth.has_token() or not config.gmail_address:
        return 2
    if not config.is_complete:
        return 3
    return 4


@bp.route("/setup")
def start():
    config = Config.load()
    return render_template("setup.html", step=_step(config), config=config, form=None)


@bp.route("/setup/reset", methods=["POST"])
def reset():
    """Escape hatch: a structurally-valid but wrong OAuth client would
    otherwise dead-end the wizard, since /settings (and its Forget
    credentials button) sits behind the setup gate. Keeps config.json so a
    re-run remembers the Kindle address."""
    auth.forget_credentials()
    flash("Setup reset — start again from step 1.", "ok")
    return redirect(url_for("setup.start"))


@bp.route("/setup/credentials", methods=["POST"])
def save_credentials():
    text = (request.form.get("client_secret_json") or "").strip()
    upload = request.files.get("client_secret_file")
    if upload and upload.filename:
        text = upload.read().decode("utf-8", errors="replace")
    if not text:
        flash("Paste the JSON or choose the downloaded file.", "error")
        return redirect(url_for("setup.start"))
    try:
        auth.save_client_secret(text)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("setup.start"))
    flash("OAuth client saved. Now connect your Google account.", "ok")
    return redirect(url_for("setup.start"))


@bp.route("/setup/oauth")
def oauth_start():
    try:
        flow = auth.build_web_flow(url_for("setup.oauth_callback", _external=True))
    except auth.NotAuthenticatedError as exc:
        flash(str(exc), "error")
        return redirect(url_for("setup.start"))
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="false",
        prompt="consent",  # always get a refresh token, even on re-connect
    )
    session["oauth_state"] = state
    # authorization_url() is what generates the PKCE code_verifier (lazily,
    # on the Flow instance) — must round-trip it to the callback the same
    # way as state, or Google's token exchange fails with invalid_grant.
    session["oauth_code_verifier"] = flow.code_verifier
    return redirect(authorization_url)


@bp.route("/oauth2/callback")
def oauth_callback():
    if request.args.get("error"):
        flash(f"Google sign-in was cancelled or failed: {request.args['error']}", "error")
        return redirect(url_for("setup.start"))
    state = session.pop("oauth_state", None)
    if not state or request.args.get("state") != state:
        flash("OAuth state mismatch — please try connecting again.", "error")
        return redirect(url_for("setup.start"))
    code_verifier = session.pop("oauth_code_verifier", None)

    # The redirect lands on http://127.0.0.1, which oauthlib treats as
    # insecure transport even though it never leaves this machine. Loopback
    # redirects are explicitly sanctioned by RFC 8252 (the token exchange
    # itself still goes to Google over HTTPS). Google may also normalise the
    # granted scope list, which oauthlib would otherwise reject.
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

    try:
        flow = auth.build_web_flow(url_for("setup.oauth_callback", _external=True), code_verifier=code_verifier)
        flow.fetch_token(authorization_response=request.url)
    except Exception as exc:
        flash(f"Could not complete Google sign-in: {exc}", "error")
        return redirect(url_for("setup.start"))

    creds = flow.credentials
    auth.save_token(creds)

    # Record the authenticated address - it becomes the From address, and
    # Config.is_complete gates the whole app on it. Nothing else writes it,
    # so silently leaving it blank strands the user on /setup with a success
    # message and no way out but reconnecting.
    try:
        gmail_address = get_profile_email(build_service(creds))
    except HttpError as exc:
        current_app.logger.warning("Could not read Gmail address after sign-in", exc_info=True)
        # The single most common first-run mistake: the OAuth client works
        # fine, but the Gmail API was never actually enabled (or was
        # enabled in a different project) for the Google Cloud project
        # behind it. Google's own error names the project number, so surface
        # a direct, actionable link instead of the raw error dump - the
        # generic message below still fires for anything else.
        if getattr(exc, "status_code", None) == 403 and "accessNotConfigured" in str(exc):
            project = re.search(r"project[=/](\d+)", str(exc))
            enable_url = (
                f"https://console.cloud.google.com/apis/api/gmail.googleapis.com/overview?project={project.group(1)}"
                if project
                else "https://console.cloud.google.com/apis/library/gmail.googleapis.com"
            )
            flash(
                "Signed in, but the Gmail API isn't turned on yet for your Google "
                f"Cloud project. Go to {enable_url}, click Enable, wait until the "
                "button changes to \"Manage\" (that's your confirmation it's really "
                "on), then press Connect Google again.",
                "error",
            )
        else:
            flash(
                "Signed in, but we couldn't read your Gmail address "
                f"({exc}). Press Connect Google again to finish.",
                "error",
            )
        return redirect(url_for("setup.start"))
    except Exception as exc:
        current_app.logger.warning("Could not read Gmail address after sign-in", exc_info=True)
        flash(
            "Signed in, but we couldn't read your Gmail address "
            f"({exc}). Press Connect Google again to finish.",
            "error",
        )
        return redirect(url_for("setup.start"))

    config = Config.load()
    config.gmail_address = gmail_address
    config.save()

    flash(f"Connected as {gmail_address}.", "ok")
    # oauth_start opens in the system browser on purpose (see setup.html) -
    # in the desktop app this success page lands in a new Chrome/Safari tab,
    # separate from the app's own window, which reads as a dead end unless
    # we say so explicitly. oauth_done tells the template to show that.
    return redirect(url_for("setup.start", oauth_done=1))


@bp.route("/setup/settings", methods=["POST"])
def save_settings():
    config = Config.load()
    kindle_email = (request.form.get("kindle_email") or "").strip()
    source_label = (request.form.get("source_label") or "").strip() or DEFAULT_SOURCE_LABEL
    if not is_kindle_address(kindle_email):
        flash(
            "That doesn't look like a Kindle address — it should end in "
            "@kindle.com or @free.kindle.com.",
            "error",
        )
        # Re-render (no redirect) so the values the user just typed survive.
        return render_template(
            "setup.html",
            step=3,
            config=config,
            form={
                "kindle_email": kindle_email,
                "source_label": request.form.get("source_label", ""),
                "digest": bool(request.form.get("digest")),
            },
        )

    config.kindle_email = kindle_email
    config.source_label = source_label
    config.digest = bool(request.form.get("digest"))
    config.save()

    # Create the label up front so "label an email" works immediately.
    try:
        service = build_service(auth.load_credentials())
        ensure_label(service, config.source_label)
        ensure_label(service, config.sent_label)
    except Exception:
        current_app.logger.warning("Could not pre-create Gmail labels", exc_info=True)
        flash(
            "Setup is complete, but the Gmail labels couldn't be created yet — "
            "they'll be created automatically on your first send.",
            "error",
        )

    flash("Setup complete! Label an email and press Send to Kindle.", "ok")
    return redirect(url_for("dashboard.index"))
