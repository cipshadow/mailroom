# Security

## Threat model

Kindle Mailroom is a **local, single-user tool**. It runs a web server bound to
`127.0.0.1` only — it is never reachable from other machines. There is no
hosted service, no account system, and no telemetry. Nothing leaves your
machine except:

- the Gmail API calls you initiate;
- fetches of any article URL you paste into **Send a URL**;
- the image downloads needed to build each EPUB.

## What is stored, and where

Everything lives in your OS user data directory (shown on the Settings page):

| File | Contents | Permissions |
|---|---|---|
| `client_secret.json` | Your own Google OAuth client (you create it) | `0600` |
| `token.json` | OAuth token granting Gmail read/modify/send | `0600` |
| `config.json` | Gmail and Kindle addresses, label names, delivery options, schedule, port, app secret key | `0600` |
| `mailroom.sqlite3` | Delivery history (subjects, message IDs) | user-only dir |
| `epubs/` | Generated EPUB files | user-only dir |
| `mailroom.log` | Run log, including email subjects (desktop builds send all output here) | user-only dir |

Setting `KINDLE_MAILROOM_DATA_DIR` relocates all of the above.

Nothing secret is ever written into the repository directory, and the app
never logs token or client-secret contents.

## Web-server hardening

- Binds `127.0.0.1` only; there is deliberately no flag to change this.
- Every POST requires a session CSRF token (a malicious website you visit
  could otherwise POST to `http://127.0.0.1:8377`).
- Requests with an unexpected `Host` header are rejected (DNS-rebinding guard).

## Revoking access

To cut the app off from your Gmail at any time:

1. Visit <https://myaccount.google.com/permissions> and remove the app.
2. Optionally delete the OAuth client in Google Cloud Console
   (APIs & Services → Credentials) — this also invalidates the refresh token.
3. Use **Settings → Forget credentials** in the app to delete the local
   `token.json` and `client_secret.json`.

## Reporting a vulnerability

Open an issue at https://github.com/cipshadow/mailroom/issues. For anything sensitive, please use GitHub's
private vulnerability reporting on that repository rather than a public
issue. Reproduction steps are always appreciated.
