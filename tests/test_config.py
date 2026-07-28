import json
import os
import stat
import sys

import pytest

from kindle_mailroom import config as cfg
from kindle_mailroom.config import Config


def test_defaults_and_roundtrip():
    config = Config.load()
    assert config.source_label == cfg.DEFAULT_SOURCE_LABEL
    assert config.sent_label == cfg.DEFAULT_SENT_LABEL
    assert not config.is_complete
    config.gmail_address = "me@gmail.com"
    config.kindle_email = "me@kindle.com"
    config.digest = True
    config.save()

    reloaded = Config.load()
    assert reloaded.gmail_address == "me@gmail.com"
    assert reloaded.digest is True
    assert reloaded.is_complete


def test_secret_key_generated_once():
    first = Config.load().secret_key
    assert len(first) == 64
    assert Config.load().secret_key == first


def test_unknown_keys_ignored():
    config = Config.load()
    config.save()
    data = json.loads(cfg.config_path().read_text())
    data["obsolete_field"] = "junk"
    cfg.config_path().write_text(json.dumps(data))
    assert Config.load().source_label == cfg.DEFAULT_SOURCE_LABEL  # doesn't blow up


def test_saved_labels_survive_default_change():
    # Renaming the shipped defaults must never touch an existing install:
    # whatever is in config.json wins over the dataclass defaults.
    config = Config.load()
    config.source_label = "Reading"
    config.save()
    assert Config.load().source_label == "Reading"


def test_is_kindle_address():
    assert cfg.is_kindle_address("name@kindle.com")
    assert cfg.is_kindle_address("name@free.kindle.com")
    assert cfg.is_kindle_address("Name_AB12CD@Kindle.COM")  # case-insensitive
    assert not cfg.is_kindle_address("name@gmail.com")
    assert not cfg.is_kindle_address("")


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions only")
def test_secret_files_are_0600():
    Config.load().save()
    mode = stat.S_IMODE(os.stat(cfg.config_path()).st_mode)
    assert mode == 0o600

    cfg.write_private(cfg.token_path(), "{}")
    mode = stat.S_IMODE(os.stat(cfg.token_path()).st_mode)
    assert mode == 0o600
