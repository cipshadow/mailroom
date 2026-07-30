"""Frozen (PyInstaller) desktop entry point.

Not used by the pip/pipx CLI at all — `cli.py` is untouched and remains the
supported way to run Kindle Mailroom from a terminal. This module is only
for the double-click .app/.exe builds in packaging/, which differ from the
CLI in three ways: there is no console to print startup info to or Ctrl+C
out of, a double-click can happen while an instance is already running (so
it needs to find and reuse it instead of erroring out on the busy port),
and a `--selftest` mode CI uses right after building, to prove the bundled
data files and native dependencies actually made it into the binary before
it ever reaches a release asset.
"""

from __future__ import annotations

import http.client
import io
import logging
import os
import socket
import sys
import threading
import webbrowser

from . import __version__
from .config import Config, data_dir, log_path

# config.port is tried first; these are the fallback if it's taken by
# something that *isn't* another Kindle Mailroom (see _probe_running_instance).
_PORT_SCAN_RANGE = range(8377, 8398)


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _probe_running_instance(port: int) -> bool:
    """True if a Kindle Mailroom instance is already answering on this port.

    Uses http.client rather than urllib: urllib raises on non-2xx responses
    and follows redirects, and "/" is a 302 before setup completes - we just
    need the header, whatever the status code.
    """
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=0.5)
        conn.request("GET", "/")
        resp = conn.getresponse()
        found = resp.getheader("X-Kindle-Mailroom") is not None
        conn.close()
        return found
    except OSError:
        return False


def _setup_logging() -> None:
    """Windowed builds have no console: stdout/stderr/logging all go to
    config.log_path() instead (the path already existed, unused, before this
    module). One-generation rotation keeps it from growing forever. This
    must run before importing anything that touches sys.stderr at import
    time - werkzeug's logger captures it when the handler is created."""
    path = log_path()
    try:
        if path.exists() and path.stat().st_size > 1_000_000:
            path.replace(path.with_name(path.name + ".1"))
    except OSError:
        pass  # best-effort; a full disk shouldn't block startup

    log_file = open(path, "a", buffering=1, encoding="utf-8")
    sys.stdout = log_file
    sys.stderr = log_file
    try:
        os.dup2(log_file.fileno(), 1)
        os.dup2(log_file.fileno(), 2)
    except (OSError, AttributeError, io.UnsupportedOperation):
        pass  # native writers (lxml) go unlogged on platforms without dup2

    logging.basicConfig(
        stream=log_file, level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    sys.excepthook = lambda *exc_info: logging.getLogger(__name__).error(
        "Unhandled error", exc_info=exc_info)


def _selftest() -> int:
    """CI smoke gate for a freshly built binary. Exit code is the only
    signal a windowed build can give - stdout may not exist."""
    import tempfile

    try:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["KINDLE_MAILROOM_DATA_DIR"] = tmp

            from .web import create_app
            client = create_app(start_background=False).test_client()

            resp = client.get("/", base_url="http://127.0.0.1:8377")
            assert resp.status_code == 302, "GET / should redirect to /setup pre-setup"
            resp = client.get("/setup", base_url="http://127.0.0.1:8377")
            assert resp.status_code == 200, "GET /setup failed - templates not bundled?"
            assert resp.headers.get("X-Kindle-Mailroom"), "identity header missing"
            resp = client.get("/static/style.css", base_url="http://127.0.0.1:8377")
            assert resp.status_code == 200, "static/style.css not bundled"

            # bs4 + lxml + ebooklib, exercised the same way core/epub_build.py
            # is used for real (see web/views/dashboard.py:send_test).
            from .core.epub_build import url_to_epub
            out = url_to_epub("Selftest", "<p>hello</p>", "https://example.com",
                              data_dir() / "selftest-epubs")
            assert out.exists(), "EPUB build failed"

            from PIL import Image
            buf = io.BytesIO()
            Image.new("RGB", (2, 2)).save(buf, format="PNG")
            Image.open(io.BytesIO(buf.getvalue())).load()

            import ssl

            import certifi
            ssl.create_default_context(cafile=certifi.where())

            # Proves googleapiclient's bundled gmail.v1.json discovery doc
            # made it into the build - build() reads it locally, no network.
            import httplib2
            from googleapiclient.discovery import build
            build("gmail", "v1", http=httplib2.Http(), static_discovery=True)

        print("SELFTEST OK", file=sys.__stderr__)
        return 0
    except Exception:
        import traceback
        traceback.print_exc(file=sys.__stderr__)
        return 1


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--selftest" in argv:
        return _selftest()

    _setup_logging()
    log = logging.getLogger(__name__)
    log.info("Kindle Mailroom %s starting", __version__)

    from .web import create_app

    config = Config.load()
    candidate_ports = [config.port] + [p for p in _PORT_SCAN_RANGE if p != config.port]

    for port in candidate_ports:
        url = f"http://127.0.0.1:{port}/"
        if _probe_running_instance(port):
            log.info("Already running at %s - opening it instead of starting a second copy", url)
            webbrowser.open(url)
            return 0
        if _port_is_free(port):
            app = create_app()
            threading.Timer(1.0, lambda u=url: webbrowser.open(u)).start()
            log.info("Serving at %s", url)
            # Localhost only, on purpose. See SECURITY.md.
            app.run(host="127.0.0.1", port=port, debug=False)
            return 0
        # Occupied by something that didn't answer as us in time - try the next port.

    log.error("Could not find a free port in %s-%s", _PORT_SCAN_RANGE.start, _PORT_SCAN_RANGE.stop - 1)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
