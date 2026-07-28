"""In-process scheduler.

Runs only while the app is open — that is the honest story for a local tool.
Every minute it checks whether a configured daily/weekly slot has been passed
without a run today, and if so enqueues a send through the shared JobRunner
(so scheduled and manual sends never overlap). If the app was closed at the
scheduled time, the send catches up at next launch.

For fully unattended delivery, docs/scheduling.md covers cron/launchd/Task
Scheduler invoking `kindle-mailroom send`.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

from ..config import Config, db_path
from ..core import auth
from ..core.gmail_client import build_service
from ..core.store import Store
from .jobs import JobBusyError, JobRunner

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60


def _slot_passed_today(config: Config, now: datetime) -> bool:
    """True if today has a scheduled slot and we're past its time."""
    try:
        hour, minute = (int(part) for part in config.schedule_time.split(":"))
    except ValueError:
        return False
    if config.schedule_frequency == "weekly" and now.weekday() != config.schedule_weekday:
        return False
    return (now.hour, now.minute) >= (hour, minute)


def is_due(config: Config, now: datetime | None = None) -> bool:
    if not config.schedule_enabled:
        return False
    now = now or datetime.now()
    today = now.date().isoformat()
    if config.last_scheduled_run == today:
        return False
    return _slot_passed_today(config, now)


def run_scheduled_send(job) -> str:
    from ..core import pipeline

    config = Config.load()
    creds = auth.load_credentials()
    service = build_service(creds)
    store = Store(db_path())
    try:
        report = pipeline.send_labelled(service, store, config, progress=job.log_line)
    finally:
        store.close()
    config = Config.load()
    config.last_scheduled_run = datetime.now().date().isoformat()
    config.save()
    return report.summary()


def start_scheduler(runner: JobRunner) -> threading.Thread:
    def loop():
        while True:
            time.sleep(CHECK_INTERVAL_SECONDS)
            try:
                config = Config.load()
                if not is_due(config):
                    continue
                if not (config.is_complete and auth.has_token()):
                    continue
                logger.info("Scheduled send is due; enqueueing")
                runner.submit("send", run_scheduled_send)
            except JobBusyError:
                pass  # try again next minute
            except Exception:
                logger.exception("Scheduler check failed")

    thread = threading.Thread(target=loop, daemon=True, name="mailroom-scheduler")
    thread.start()
    return thread
