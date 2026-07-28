# Contributing

Thanks for taking a look. Bug reports and pull requests are welcome.

## Development setup

```bash
git clone https://github.com/cipshadow/mailroom
cd mailroom
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"      # quotes matter in zsh
```

## Before you open a PR

```bash
ruff check src tests
pytest
```

Both should be clean. If you're changing how EPUBs are built or how email HTML
is sanitized, please add a test with the real-world markup that motivated it —
most of the tests in `tests/test_sanitize.py` and `tests/test_epub_build.py`
exist because a specific newsletter rendered badly on an actual Kindle, and
they're the reason those bugs stay fixed.

## Testing against your own mail without touching your real setup

Point the app at a scratch directory:

```bash
KINDLE_MAILROOM_DATA_DIR=/tmp/mailroom-test kindle-mailroom
```

Everything (config, credentials, database, generated EPUBs) is read from and
written to that directory, so your normal install is untouched.

## House style

- Templates are plain Jinja with a little vanilla JS — please don't add a
  frontend framework or a build step.
- The web app is local-only by design: it binds `127.0.0.1`, requires a CSRF
  token on every POST, and checks the `Host` header. Please don't loosen those.
- Keep secrets out of logs.
