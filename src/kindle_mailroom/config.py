"""Per-user configuration and data paths.

All state (config, OAuth secrets, delivery DB, generated EPUBs) lives in the
OS user data directory, never in the repository. Secret-bearing files are
written with 0600 permissions.
"""

from __future__ import annotations

import json
import os
import secrets
import stat
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "kindle-mailroom"
DEFAULT_PORT = 8377


def data_dir() -> Path:
    """The per-user data directory. Overridable via KINDLE_MAILROOM_DATA_DIR
    (used by tests and by anyone who wants their state elsewhere)."""
    override = os.environ.get("KINDLE_MAILROOM_DATA_DIR")
    base = Path(override) if override else Path(user_data_dir(APP_NAME))
    base.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(base, 0o700)
    except OSError:
        pass
    return base


def config_path() -> Path:
    return data_dir() / "config.json"


def client_secret_path() -> Path:
    return data_dir() / "client_secret.json"


def token_path() -> Path:
    return data_dir() / "token.json"


def db_path() -> Path:
    return data_dir() / "mailroom.sqlite3"


def epub_dir() -> Path:
    path = data_dir() / "epubs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_path() -> Path:
    return data_dir() / "mailroom.log"


def write_private(path: Path, text: str) -> None:
    """Write a secret-bearing file readable only by the current user."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(path, flags, 0o600)
    try:
        os.write(fd, text.encode("utf-8"))
    finally:
        os.close(fd)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


# Defaults for fresh installs; a saved config.json always wins in Config.load,
# so renaming these never touches existing users. The sent label nests under
# the source label in Gmail's sidebar via the "/" separator.
# Both nest under a shared "Mailroom" parent in Gmail's sidebar. Labels are
# matched by exact name via the Gmail API (never search queries), so the
# emoji are safe.
DEFAULT_SOURCE_LABEL = "Mailroom/Send next 📤"
DEFAULT_SENT_LABEL = "Mailroom/Sent ✅"

# Amazon issues both plain and Wi-Fi-only delivery addresses.
KINDLE_ADDRESS_DOMAINS = ("@kindle.com", "@free.kindle.com")


def is_kindle_address(address: str) -> bool:
    return address.lower().endswith(KINDLE_ADDRESS_DOMAINS)


@dataclass
class Config:
    gmail_address: str = ""
    kindle_email: str = ""
    source_label: str = DEFAULT_SOURCE_LABEL
    sent_label: str = DEFAULT_SENT_LABEL
    digest: bool = False
    send_limit: int = 0  # 0 = no limit: send everything labelled
    unread_only: bool = False  # opt-in: skip labelled emails already read
    send_delay: float = 2.0
    mark_read: bool = False
    schedule_enabled: bool = False
    schedule_frequency: str = "daily"  # "daily" | "weekly"
    schedule_time: str = "08:00"
    schedule_weekday: int = 0  # 0 = Monday, used when weekly
    last_scheduled_run: str = ""  # ISO date of the last schedule-driven send
    secret_key: str = ""
    port: int = DEFAULT_PORT

    @classmethod
    def load(cls) -> "Config":
        path = config_path()
        data: dict = {}
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = {}
        known = {f.name for f in fields(cls)}
        config = cls(**{k: v for k, v in data.items() if k in known})
        if not config.secret_key:
            config.secret_key = secrets.token_hex(32)
            config.save()
        return config

    def save(self) -> None:
        write_private(config_path(), json.dumps(asdict(self), indent=2))

    @property
    def is_complete(self) -> bool:
        """Setup finished: both addresses known (auth state checked separately)."""
        return bool(self.gmail_address and self.kindle_email)
