"""Single-worker background job runner for send operations.

Sends take seconds to minutes (image downloads, Gmail API calls), so they run
on a worker thread while the dashboard polls /jobs/current for progress. Only
one job runs at a time — manual and scheduled sends can't overlap.
"""

from __future__ import annotations

import threading
import traceback
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable


@dataclass
class Job:
    kind: str  # "send" | "send-url" | "restore" | "test"
    state: str = "queued"  # queued | running | done | error
    started_at: str = ""
    finished_at: str = ""
    result: str = ""
    log: deque = field(default_factory=lambda: deque(maxlen=500))

    def log_line(self, message: str) -> None:
        self.log.append(message)

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "state": self.state,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "result": self.result,
            "log": list(self.log),
        }


class JobBusyError(Exception):
    pass


class JobRunner:
    def __init__(self):
        self._lock = threading.Lock()
        self.current: Job | None = None

    @property
    def busy(self) -> bool:
        return bool(self.current and self.current.state in ("queued", "running"))

    def submit(self, kind: str, work: Callable[[Job], str]) -> Job:
        """Run work(job) on the worker thread; its return value becomes the
        job result. Raises JobBusyError if a job is already in flight."""
        with self._lock:
            if self.busy:
                raise JobBusyError("A job is already running.")
            job = Job(kind=kind)
            self.current = job

        def run():
            job.state = "running"
            job.started_at = datetime.now(timezone.utc).isoformat()
            try:
                job.result = work(job) or "done"
                job.state = "done"
            except Exception as exc:
                job.state = "error"
                job.result = str(exc)
                job.log_line(f"ERROR: {exc}")
                job.log_line(traceback.format_exc(limit=3))
            finally:
                job.finished_at = datetime.now(timezone.utc).isoformat()

        threading.Thread(target=run, daemon=True).start()
        return job
