import socket

import pytest

from kindle_mailroom import cli


def test_version_flag(capsys):
    # argparse exits 0 after printing the version
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert "kindle-mailroom" in capsys.readouterr().out


def test_web_port_in_use_is_friendly(capsys):
    # Bind a real port rather than stubbing app.run: werkzeug handles the bind
    # failure itself and exits, so an `except OSError` around app.run never
    # fires. Only a real occupied port proves the check actually works.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    try:
        rc = cli.main(["web", "--no-browser", "--port", str(port)])
    finally:
        sock.close()

    assert rc == 1
    err = capsys.readouterr().err
    assert str(port) in err
    assert f"--port {port + 1}" in err  # concrete next command, not just advice
