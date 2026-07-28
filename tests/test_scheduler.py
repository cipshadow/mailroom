from datetime import datetime

from kindle_mailroom.config import Config
from kindle_mailroom.web.scheduler import is_due


def make_config(**overrides) -> Config:
    config = Config(secret_key="x")
    config.schedule_enabled = True
    config.schedule_frequency = "daily"
    config.schedule_time = "08:00"
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


def test_disabled_never_due():
    config = make_config(schedule_enabled=False)
    assert not is_due(config, datetime(2026, 7, 10, 9, 0))


def test_daily_due_after_slot():
    config = make_config()
    assert not is_due(config, datetime(2026, 7, 10, 7, 59))
    assert is_due(config, datetime(2026, 7, 10, 8, 0))
    assert is_due(config, datetime(2026, 7, 10, 23, 0))  # catch-up later in the day


def test_daily_not_due_twice_same_day():
    config = make_config(last_scheduled_run="2026-07-10")
    assert not is_due(config, datetime(2026, 7, 10, 9, 0))
    assert is_due(config, datetime(2026, 7, 11, 9, 0))


def test_weekly_only_on_configured_day():
    config = make_config(schedule_frequency="weekly", schedule_weekday=0)  # Monday
    assert is_due(config, datetime(2026, 7, 6, 8, 30))  # a Monday
    assert not is_due(config, datetime(2026, 7, 7, 8, 30))  # Tuesday


def test_bad_time_string_is_never_due():
    config = make_config(schedule_time="not-a-time")
    assert not is_due(config, datetime(2026, 7, 10, 9, 0))
