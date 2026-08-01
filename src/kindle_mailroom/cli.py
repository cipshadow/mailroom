"""Command line interface.

`kindle-mailroom` with no arguments launches the local web app (the friendly
path). Subcommands exist for power users and OS schedulers (cron/launchd/Task
Scheduler), which run headlessly using the credentials set up via the web UI.
"""

from __future__ import annotations

import argparse
import socket
import sys
import threading
import webbrowser

from . import __version__
from .config import Config, data_dir, db_path
from .core import auth, pipeline
from .core.gmail_client import LabelNotFoundError, build_service
from .core.store import Store


def _service_or_exit():
    try:
        creds = auth.load_credentials()
    except auth.NotAuthenticatedError as exc:
        raise SystemExit(f"{exc}\nRun `kindle-mailroom` (no arguments) to set up in the browser.")
    return build_service(creds)


def _config_or_exit() -> Config:
    config = Config.load()
    if not config.is_complete:
        raise SystemExit(
            "Setup incomplete (Gmail/Kindle addresses missing). "
            "Run `kindle-mailroom` (no arguments) to finish setup in the browser."
        )
    return config


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        # SO_REUSEADDR so a socket lingering in TIME_WAIT doesn't read as busy.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def command_web(args) -> int:
    from .web import create_app

    config = Config.load()
    port = args.port or config.port
    url = f"http://127.0.0.1:{port}/"

    # Check before starting: werkzeug handles the bind failure itself and exits,
    # so we'd never see the OSError - and launching twice is an easy mistake to
    # make, which deserves better than "Address already in use".
    if not _port_is_free(port):
        print(
            f"Port {port} is already in use.\n"
            f"If Kindle Mailroom is already running, open {url}\n"
            f"Otherwise start it on another port:\n"
            f"    kindle-mailroom web --port {port + 1}",
            file=sys.stderr,
        )
        return 1

    app = create_app()
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"Kindle Mailroom running at {url}  (Ctrl+C to stop)")
    print(f"Your data lives in: {data_dir()}")
    # Localhost only, on purpose. See SECURITY.md.
    app.run(host="127.0.0.1", port=port, debug=False)
    return 0


def command_send(args) -> int:
    config = _config_or_exit()
    service = _service_or_exit()
    store = Store(db_path())
    digest_override = True if args.digest else False if args.no_digest else None
    try:
        report = pipeline.send_labelled(
            service,
            store,
            config,
            digest=digest_override,
            dry_run=args.dry_run,
            resend=args.resend,
            limit=args.limit,
            # None = follow the config setting; the flag force-includes read mail
            unread_only=False if args.include_read else None,
        )
    except LabelNotFoundError as exc:
        raise SystemExit(str(exc))
    finally:
        store.close()
    return 0 if not report.errors else 1


def command_send_url(args) -> int:
    config = _config_or_exit()
    service = _service_or_exit()
    store = Store(db_path())
    try:
        report = pipeline.send_urls(
            service, store, config, args.urls,
            number=args.number, chronological=args.chronological,
        )
    finally:
        store.close()
    return 0 if not report.errors else 1


def command_list(_args) -> int:
    store = Store(db_path())
    try:
        for row in store.list_deliveries():
            print(
                f"{row['status']:4} sent={row['sent_at'] or '-'} "
                f"read={row['read_at'] or '-'} {row['message_id']} {row['subject']}"
            )
    finally:
        store.close()
    return 0


def command_restore(_args) -> int:
    config = _config_or_exit()
    service = _service_or_exit()
    store = Store(db_path())
    try:
        pipeline.restore_sent(service, store, config)
    except LabelNotFoundError as exc:
        raise SystemExit(str(exc))
    finally:
        store.close()
    return 0


def command_mark_read(args) -> int:
    store = Store(db_path())
    try:
        if not store.mark_read(args.message_id):
            print(f"no delivery found for {args.message_id}", file=sys.stderr)
            return 1
    finally:
        store.close()
    print(f"marked read: {args.message_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    # The default labels contain emoji; a Windows console redirected to a
    # cp1252 pipe would otherwise crash on the first progress line naming them.
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except (OSError, ValueError):
                pass
    parser = argparse.ArgumentParser(
        prog="kindle-mailroom",
        description="Send labeled Gmail newsletters and web articles to your Kindle.",
    )
    parser.add_argument("--version", action="version", version=f"kindle-mailroom {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    web_parser = subparsers.add_parser("web", help="Launch the local web app (default)")
    web_parser.add_argument("--port", type=int, default=None)
    web_parser.add_argument("--no-browser", action="store_true", help="Don't open the browser automatically")
    web_parser.set_defaults(func=command_web)

    send_parser = subparsers.add_parser("send", help="Send labeled Gmail messages to Kindle (headless)")
    send_parser.add_argument("--digest", action="store_true", help="Force digest mode for this run")
    send_parser.add_argument("--no-digest", action="store_true", help="Force one-per-email mode for this run")
    send_parser.add_argument("--limit", type=int, default=None,
                             help="Max emails this run (0 = no limit; default: config setting)")
    send_parser.add_argument("--resend", action="store_true", help="Resend even if already delivered")
    send_parser.add_argument("--dry-run", action="store_true")
    send_parser.add_argument("--include-read", action="store_true",
                             help="Also process read messages with the source label")
    send_parser.set_defaults(func=command_send)

    url_parser = subparsers.add_parser("send-url", help="Send article URLs to Kindle")
    url_parser.add_argument("urls", nargs="+", help="One or more article URLs")
    url_parser.add_argument("--number", "-n", action="store_true",
                            help="Prefix titles with chronological number (for batch sends)")
    url_parser.add_argument("--chronological", "-c", action="store_true",
                            help="Sort URLs by publish date before sending")
    url_parser.set_defaults(func=command_send_url)

    list_parser = subparsers.add_parser("list", help="List delivery history")
    list_parser.set_defaults(func=command_list)

    restore_parser = subparsers.add_parser("restore", help="Move sent messages back to the source label")
    restore_parser.set_defaults(func=command_restore)

    read_parser = subparsers.add_parser("mark-read", help="Mark a sent message as read")
    read_parser.add_argument("message_id")
    read_parser.set_defaults(func=command_mark_read)

    args = parser.parse_args(argv)
    if args.command is None:
        # Default: launch the web app.
        args = web_parser.parse_args([])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
