import json

import pytest

from kindle_mailroom import config as cfg
from kindle_mailroom.config import Config
from kindle_mailroom.core import auth


@pytest.fixture
def app():
    from kindle_mailroom.web import create_app

    app = create_app(start_background=False)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def complete_setup():
    """Simulate a finished setup: config filled, client secret + token on disk."""
    config = Config.load()
    config.gmail_address = "me@gmail.com"
    config.kindle_email = "me@kindle.com"
    config.save()
    from kindle_mailroom import config as cfg

    cfg.write_private(cfg.client_secret_path(), json.dumps(
        {"installed": {"client_id": "id", "client_secret": "secret",
                       "token_uri": "https://oauth2.googleapis.com/token"}}))
    cfg.write_private(cfg.token_path(), json.dumps(
        {"token": "x", "refresh_token": "r", "client_id": "id",
         "client_secret": "secret", "token_uri": "https://oauth2.googleapis.com/token",
         "scopes": auth.SCOPES,
         # Without an explicit future expiry, google-auth treats the token as
         # already expired and tries to refresh it over the network.
         "expiry": "2099-01-01T00:00:00Z"}))


def test_unconfigured_redirects_to_setup(client):
    resp = client.get("/", base_url="http://localhost:8377")
    assert resp.status_code == 302
    assert "/setup" in resp.headers["Location"]


def test_setup_page_renders(client):
    resp = client.get("/setup", base_url="http://localhost:8377")
    assert resp.status_code == 200
    assert b"OAuth client" in resp.data


def test_host_header_guard(client):
    resp = client.get("/setup", base_url="http://evil.example.com")
    assert resp.status_code == 403


def test_post_without_csrf_rejected(client):
    resp = client.post("/setup/credentials", data={"client_secret_json": "{}"},
                       base_url="http://localhost:8377")
    assert resp.status_code == 400


def test_csrf_token_flow_and_client_secret_validation(client):
    page = client.get("/setup", base_url="http://localhost:8377")
    with client.session_transaction() as session:
        token = session["csrf_token"]
    assert page.status_code == 200

    # web-app client rejected with a helpful message
    resp = client.post(
        "/setup/credentials",
        data={"client_secret_json": json.dumps({"web": {"client_id": "x", "client_secret": "y"}}),
              "csrf_token": token},
        base_url="http://localhost:8377",
        follow_redirects=True,
    )
    assert b"Desktop app" in resp.data
    assert not auth.has_client_secret()

    # desktop client accepted
    resp = client.post(
        "/setup/credentials",
        data={"client_secret_json": json.dumps({"installed": {"client_id": "x", "client_secret": "y"}}),
              "csrf_token": token},
        base_url="http://localhost:8377",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert auth.has_client_secret()


def test_dashboard_renders_when_configured(client):
    complete_setup()
    resp = client.get("/", base_url="http://localhost:8377")
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data
    assert b"me@kindle.com" in resp.data


def test_history_and_url_pages_render(client):
    complete_setup()
    for path in ("/history", "/url", "/settings"):
        resp = client.get(path, base_url="http://localhost:8377")
        assert resp.status_code == 200, path


def test_mark_batch_headers_uses_batch_start_not_first_seen_row():
    from kindle_mailroom.web.views.dashboard import _mark_batch_headers

    # list_deliveries orders newest-first, so within a batch the row seen
    # first is the *last* send, not the first - the header must still show
    # the batch's start time, not that row's own sent_at.
    deliveries = [
        {"sent_at": "2026-08-28T19:01:42+00:00", "batch_id": "b1"},
        {"sent_at": "2026-08-28T18:59:00+00:00", "batch_id": "b1"},
        {"sent_at": "2026-08-28T18:57:25+00:00", "batch_id": "b1"},
        {"sent_at": "2026-08-15T09:50:42+00:00", "batch_id": "b2"},
        {"sent_at": "2026-08-01T11:09:49+00:00", "batch_id": None},
        {"sent_at": "2026-08-01T11:09:55+00:00", "batch_id": None},
    ]
    result = _mark_batch_headers(deliveries)

    assert [d["show_sent_header"] for d in result] == [True, False, False, True, True, True]
    assert result[0]["batch_started_at"] == "2026-08-28T18:57:25+00:00"
    assert result[1]["batch_started_at"] == "2026-08-28T18:57:25+00:00"
    assert result[3]["batch_started_at"] == "2026-08-15T09:50:42+00:00"


def test_jobs_endpoint_idle(client):
    complete_setup()
    resp = client.get("/jobs/current", base_url="http://localhost:8377")
    assert resp.get_json()["state"] == "idle"


def test_settings_save(client):
    complete_setup()
    with client.session_transaction() as session:
        session["csrf_token"] = "tok"
    resp = client.post(
        "/settings",
        data={
            "csrf_token": "tok",
            "kindle_email": "new@kindle.com",
            "source_label": "ToKindle",
            "sent_label": "Kindle/Sent",
            "send_limit": "5",
            "schedule_enabled": "on",
            "schedule_frequency": "weekly",
            "schedule_time": "07:30",
            "schedule_weekday": "2",
        },
        base_url="http://localhost:8377",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    config = Config.load()
    assert config.kindle_email == "new@kindle.com"
    assert config.source_label == "ToKindle"
    assert config.schedule_enabled is True
    assert config.schedule_frequency == "weekly"
    assert config.schedule_time == "07:30"
    assert config.schedule_weekday == 2


# --- setup wizard: step 3 (delivery settings) ---------------------------------

def seed_credentials():
    """Client secret + token + a captured Gmail address, but no Kindle
    address yet -> step 3."""
    seed_token_only()
    config = Config.load()
    config.gmail_address = "me@gmail.com"
    config.save()


def seed_token_only():
    """Client secret + token on disk, but no Gmail address captured yet -
    e.g. sign-in succeeded but reading the profile email failed."""
    from kindle_mailroom import config as cfg

    cfg.write_private(cfg.client_secret_path(), json.dumps(
        {"installed": {"client_id": "id", "client_secret": "secret",
                       "token_uri": "https://oauth2.googleapis.com/token"}}))
    cfg.write_private(cfg.token_path(), json.dumps(
        {"token": "x", "refresh_token": "r", "client_id": "id",
         "client_secret": "secret", "token_uri": "https://oauth2.googleapis.com/token",
         "scopes": auth.SCOPES,
         # Without an explicit future expiry, google-auth treats the token as
         # already expired and tries to refresh it over the network.
         "expiry": "2099-01-01T00:00:00Z"}))


def no_network_labels(monkeypatch):
    """Stub the Gmail calls the wizard/settings make to pre-create labels."""
    created = []
    monkeypatch.setattr("kindle_mailroom.web.views.setup.build_service", lambda creds: object())
    monkeypatch.setattr("kindle_mailroom.web.views.setup.ensure_label",
                        lambda service, name: created.append(name))
    monkeypatch.setattr("kindle_mailroom.web.views.settings.build_service", lambda creds: object())
    monkeypatch.setattr("kindle_mailroom.web.views.settings.ensure_label",
                        lambda service, name: created.append(name))
    return created


def csrf(client):
    with client.session_transaction() as session:
        session["csrf_token"] = "tok"
    return "tok"


def test_wizard_returns_to_step2_when_gmail_address_missing(client):
    # Regression test: a token can exist while gmail_address is blank (the
    # post-OAuth profile read failed, e.g. Gmail API not yet enabled). The
    # wizard used to mark step 2 done anyway, stranding the user at step 3
    # forever - is_complete needs gmail_address, and nothing on step 3 can
    # set it. It must drop back to step 2 so they can reconnect.
    seed_token_only()
    resp = client.get("/setup", base_url="http://localhost:8377")
    body = resp.data.decode()
    assert "Step 2 of 3" in body
    assert "Connect Google account" in body  # the retry button is offered


def test_wizard_step3_shows_counter_and_label_howto(client):
    seed_credentials()
    resp = client.get("/setup", base_url="http://localhost:8377")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Step 3 of 3" in body
    assert "How do I label an email?" in body   # cheat-sheet present
    assert "Label as" in body                    # the actual Gmail gesture
    assert cfg.DEFAULT_SOURCE_LABEL in body      # prefilled default label


def test_wizard_complete_shows_done_state(client):
    complete_setup()
    resp = client.get("/setup", base_url="http://localhost:8377")
    body = resp.data.decode()
    assert "Setup complete" in body
    assert "Go to the dashboard" in body


def test_setup_accepts_free_kindle_address(client, monkeypatch):
    seed_credentials()
    created = no_network_labels(monkeypatch)
    token = csrf(client)
    resp = client.post("/setup/settings", data={
        "csrf_token": token,
        "kindle_email": "me_AB12CD@free.kindle.com",
        "source_label": "My Reading",
    }, base_url="http://localhost:8377")
    assert resp.status_code == 302  # straight to the dashboard
    config = Config.load()
    assert config.kindle_email == "me_AB12CD@free.kindle.com"
    assert config.source_label == "My Reading"
    assert "My Reading" in created  # label pre-created


def test_setup_rejects_non_kindle_address_and_keeps_typed_values(client):
    seed_credentials()
    token = csrf(client)
    resp = client.post("/setup/settings", data={
        "csrf_token": token,
        "kindle_email": "me@gmail.com",
        "source_label": "Typed Label",
        "digest": "on",
    }, base_url="http://localhost:8377")
    # Re-rendered (not redirected) so the user doesn't retype everything
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "me@gmail.com" in body
    assert "Typed Label" in body
    assert "@free.kindle.com" in body  # error message names both domains
    assert not Config.load().kindle_email  # nothing saved


def test_setup_empty_label_falls_back_to_default(client, monkeypatch):
    seed_credentials()
    no_network_labels(monkeypatch)
    token = csrf(client)
    client.post("/setup/settings", data={
        "csrf_token": token, "kindle_email": "me@kindle.com", "source_label": "  ",
    }, base_url="http://localhost:8377")
    # Guards against the view's fallback drifting from config.py's default
    assert Config.load().source_label == cfg.DEFAULT_SOURCE_LABEL


def test_setup_reset_clears_credentials(client):
    seed_credentials()
    assert auth.has_client_secret() and auth.has_token()
    token = csrf(client)
    resp = client.post("/setup/reset", data={"csrf_token": token},
                       base_url="http://localhost:8377")
    assert resp.status_code == 302
    assert not auth.has_client_secret()
    assert not auth.has_token()


def test_oauth_pkce_code_verifier_round_trips(client, monkeypatch):
    # Regression test: oauth_callback used to build a fresh Flow object with
    # no code_verifier, so Google's real token exchange failed with
    # "invalid_grant: Missing code verifier" even though everything else
    # about the flow was correct. The verifier must round-trip via the
    # session the same way `state` does.
    cfg.write_private(cfg.client_secret_path(), json.dumps(
        {"installed": {"client_id": "id", "client_secret": "secret",
                       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                       "token_uri": "https://oauth2.googleapis.com/token"}}))

    resp = client.get("/setup/oauth", base_url="http://localhost:8377")
    assert resp.status_code == 302
    with client.session_transaction() as session:
        state = session["oauth_state"]
        code_verifier = session["oauth_code_verifier"]
    assert code_verifier and len(code_verifier) >= 43  # RFC 7636 minimum

    import time

    from requests_oauthlib import OAuth2Session

    captured = {}

    def fake_fetch_token(self, token_url, **kwargs):
        captured["code_verifier"] = kwargs.get("code_verifier")
        self.token = {"access_token": "x", "refresh_token": "r", "expires_at": time.time() + 3600}
        self.scope = auth.SCOPES
        return self.token

    monkeypatch.setattr(OAuth2Session, "fetch_token", fake_fetch_token)
    monkeypatch.setattr("kindle_mailroom.web.views.setup.get_profile_email", lambda service: "me@gmail.com")
    monkeypatch.setattr("kindle_mailroom.web.views.setup.build_service", lambda creds: object())

    resp = client.get(
        f"/oauth2/callback?state={state}&code=fakecode",
        base_url="http://localhost:8377", follow_redirects=True,
    )
    assert resp.status_code == 200
    # The verifier used at token-exchange time must be the exact one
    # generated (and persisted) during the authorization step.
    assert captured["code_verifier"] == code_verifier
    assert auth.has_token()
    assert b"Connected as me@gmail.com" in resp.data


def test_oauth_callback_surfaces_gmail_api_disabled_with_direct_link(client, monkeypatch):
    # Regression: this used to dump the raw HttpError - a wall of nested
    # JSON - into the flash message. Forgetting to click "Enable" on the
    # Gmail API page is the single most common first-run mistake (found by
    # actually running the fresh-install flow), so this case gets a short,
    # actionable message with a direct link built from the project number
    # Google's own error names, instead of the generic fallback.
    import httplib2
    from googleapiclient.errors import HttpError

    cfg.write_private(cfg.client_secret_path(), json.dumps(
        {"installed": {"client_id": "id", "client_secret": "secret",
                       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                       "token_uri": "https://oauth2.googleapis.com/token"}}))

    resp = client.get("/setup/oauth", base_url="http://localhost:8377")
    with client.session_transaction() as session:
        state = session["oauth_state"]

    import time

    from requests_oauthlib import OAuth2Session

    def fake_fetch_token(self, token_url, **kwargs):
        self.token = {"access_token": "x", "refresh_token": "r", "expires_at": time.time() + 3600}
        self.scope = auth.SCOPES
        return self.token

    message = (
        "Gmail API has not been used in project 419490807757 before or it is "
        "disabled. Enable it by visiting https://console.developers.google.com/"
        "apis/api/gmail.googleapis.com/overview?project=419490807757 then retry."
    )
    content = json.dumps({"error": {
        "code": 403, "message": message,
        "errors": [{"message": message, "domain": "usageLimits", "reason": "accessNotConfigured"}],
    }}).encode()
    api_disabled = HttpError(
        httplib2.Response({"status": 403}), content,
        uri="https://gmail.googleapis.com/gmail/v1/users/me/profile",
    )

    def fake_profile(service):
        raise api_disabled

    monkeypatch.setattr(OAuth2Session, "fetch_token", fake_fetch_token)
    monkeypatch.setattr("kindle_mailroom.web.views.setup.get_profile_email", fake_profile)
    monkeypatch.setattr("kindle_mailroom.web.views.setup.build_service", lambda creds: object())

    resp = client.get(
        f"/oauth2/callback?state={state}&code=fakecode",
        base_url="http://localhost:8377", follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"click Enable" in resp.data
    assert b"project=419490807757" in resp.data
    assert b"usageLimits" not in resp.data  # not the raw error dump anymore


# --- dashboard: dry run -------------------------------------------------------

def test_send_work_passes_dry_run_through_to_pipeline(monkeypatch):
    # The dashboard's "Build without sending" checkbox is only useful if its
    # value actually reaches pipeline.send_labelled - this was previously
    # impossible from the web UI at all: the route read request.form["dry_run"]
    # but no template exposed a checkbox with that name.
    from kindle_mailroom.core.models import SendReport
    from kindle_mailroom.web.views import dashboard

    captured = {}

    def fake_send_labelled(service, store, config, *, digest, dry_run, progress):
        captured["dry_run"] = dry_run
        captured["digest"] = digest
        return SendReport(dry_run=dry_run)

    monkeypatch.setattr(dashboard.auth, "load_credentials", lambda: object())
    monkeypatch.setattr(dashboard, "build_service", lambda creds: object())
    monkeypatch.setattr(dashboard.pipeline, "send_labelled", fake_send_labelled)

    class FakeJob:
        def log_line(self, _msg):
            pass

    work = dashboard._send_work(digest_override=None, dry_run=True)
    work(FakeJob())
    assert captured == {"dry_run": True, "digest": None}

    work = dashboard._send_work(digest_override=True, dry_run=False)
    work(FakeJob())
    assert captured == {"dry_run": False, "digest": True}


# --- settings ----------------------------------------------------------------

def test_settings_label_change_creates_gmail_label(client, monkeypatch):
    complete_setup()
    created = no_network_labels(monkeypatch)
    token = csrf(client)
    client.post("/settings", data={
        "csrf_token": token, "source_label": "Renamed", "sent_label": "Renamed/Sent",
        "send_limit": "5", "schedule_time": "08:00",
    }, base_url="http://localhost:8377", follow_redirects=True)
    # Without this the very next send dies with LabelNotFoundError
    assert "Renamed" in created and "Renamed/Sent" in created


def test_settings_label_change_warns_when_gmail_unreachable(client, monkeypatch):
    complete_setup()

    def boom(*a, **kw):
        raise RuntimeError("network down")

    monkeypatch.setattr("kindle_mailroom.web.views.settings.build_service", boom)
    token = csrf(client)
    resp = client.post("/settings", data={
        "csrf_token": token, "source_label": "Renamed", "sent_label": "Renamed/Sent",
        "send_limit": "5", "schedule_time": "08:00",
    }, base_url="http://localhost:8377", follow_redirects=True)
    assert resp.status_code == 200
    assert b"created on the next send" in resp.data
    assert Config.load().source_label == "Renamed"  # still saved


def test_settings_accepts_free_kindle_address(client, monkeypatch):
    complete_setup()
    no_network_labels(monkeypatch)
    token = csrf(client)
    client.post("/settings", data={
        "csrf_token": token, "kindle_email": "me@free.kindle.com",
        "send_limit": "5", "schedule_time": "08:00",
    }, base_url="http://localhost:8377", follow_redirects=True)
    assert Config.load().kindle_email == "me@free.kindle.com"


def test_settings_send_limit_zero_and_unread_toggle(client, monkeypatch):
    complete_setup()
    no_network_labels(monkeypatch)
    token = csrf(client)
    # 0 must be stored as 0 (no limit), not fall back to the previous value
    client.post("/settings", data={
        "csrf_token": token, "send_limit": "0", "unread_only": "on",
        "schedule_time": "08:00",
    }, base_url="http://localhost:8377", follow_redirects=True)
    config = Config.load()
    assert config.send_limit == 0
    assert config.unread_only is True

    # absent checkbox turns the toggle back off; out-of-range limit is clamped
    client.post("/settings", data={
        "csrf_token": token, "send_limit": "9999", "schedule_time": "08:00",
    }, base_url="http://localhost:8377", follow_redirects=True)
    config = Config.load()
    assert config.send_limit == 500
    assert config.unread_only is False


# --- identity header + shutdown (desktop build needs both) -------------------

class _ImmediateTimer:
    """Stand-in for threading.Timer that fires synchronously, so tests can
    observe the effect without a real 0.5s background thread."""

    def __init__(self, interval, function, args=None, kwargs=None):
        self.function = function
        self.args = args or ()
        self.kwargs = kwargs or {}

    def start(self):
        self.function(*self.args, **self.kwargs)


def test_identity_header_present(client):
    from kindle_mailroom import __version__
    resp = client.get("/setup", base_url="http://localhost:8377")
    assert resp.headers.get("X-Kindle-Mailroom") == __version__


def test_identity_header_present_on_redirect(client):
    resp = client.get("/", base_url="http://localhost:8377")
    assert resp.status_code == 302  # unconfigured -> redirected to /setup
    assert "X-Kindle-Mailroom" in resp.headers


def test_shutdown_requires_csrf(client):
    resp = client.post("/shutdown", data={}, base_url="http://localhost:8377")
    assert resp.status_code == 400


def test_shutdown_reachable_before_setup(client, monkeypatch):
    # No config/credentials at all yet -> still reachable, like /setup itself.
    monkeypatch.setattr("os._exit", lambda code: None)
    monkeypatch.setattr("threading.Timer", _ImmediateTimer)
    token = csrf(client)
    resp = client.post("/shutdown", data={"csrf_token": token}, base_url="http://localhost:8377")
    assert resp.status_code == 200
    assert b"shutting down" in resp.data.lower()


def test_shutdown_exits_process(client, monkeypatch):
    complete_setup()
    exited = []
    monkeypatch.setattr("os._exit", lambda code: exited.append(code))
    monkeypatch.setattr("threading.Timer", _ImmediateTimer)
    token = csrf(client)
    resp = client.post("/shutdown", data={"csrf_token": token}, base_url="http://localhost:8377")
    assert resp.status_code == 200
    assert exited == [0]


def test_shutdown_confirms_first_when_job_running(client, app):
    complete_setup()
    from kindle_mailroom.web.jobs import Job

    app.extensions["job_runner"].current = Job(kind="send", state="running")
    token = csrf(client)
    resp = client.post("/shutdown", data={"csrf_token": token}, base_url="http://localhost:8377")
    assert resp.status_code == 409
    assert b"Quit anyway" in resp.data


def test_shutdown_force_quits_even_when_job_running(client, app, monkeypatch):
    complete_setup()
    from kindle_mailroom.web.jobs import Job

    app.extensions["job_runner"].current = Job(kind="send", state="running")
    exited = []
    monkeypatch.setattr("os._exit", lambda code: exited.append(code))
    monkeypatch.setattr("threading.Timer", _ImmediateTimer)
    token = csrf(client)
    resp = client.post("/shutdown", data={"csrf_token": token, "force": "1"},
                       base_url="http://localhost:8377")
    assert resp.status_code == 200
    assert exited == [0]
