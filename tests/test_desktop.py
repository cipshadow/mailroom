"""desktop.py isn't used by the pip/pipx CLI at all - it's the entry point
for the PyInstaller-built double-click apps in packaging/. The one thing
worth unit-testing here (the rest needs a real frozen binary, see
packaging/README or the release workflow) is --selftest, since it's plain
Python and runs the same regardless of whether it's frozen."""

from kindle_mailroom import desktop


def test_selftest_passes(capsys):
    assert desktop.main(["--selftest"]) == 0


def test_port_is_free_detects_busy_port():
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    try:
        assert desktop._port_is_free(port) is False
    finally:
        sock.close()
    assert desktop._port_is_free(port) is True


def test_probe_running_instance_true_for_real_app():
    from kindle_mailroom.web import create_app

    app = create_app(start_background=False)
    client = app.test_client()

    # _probe_running_instance uses a real socket, which a Flask test client
    # doesn't provide - so exercise the header logic the same way the probe
    # reads it, against the actual app, rather than spinning up a live
    # server just for this test.
    resp = client.get("/", base_url="http://127.0.0.1:8377")
    assert resp.headers.get("X-Kindle-Mailroom") is not None


def test_probe_running_instance_false_when_nothing_listening():
    # Nothing bound on this port - should fail fast (OSError -> False), not hang.
    assert desktop._probe_running_instance(8399) is False
