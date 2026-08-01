# Installing the desktop app

This covers the macOS and Windows downloads from
[Releases](https://github.com/cipshadow/mailroom/releases/latest). If you'd
rather run it from a terminal (or you're on Linux), see the Quickstart in the
[README](../README.md) instead — both paths run the exact same app.

## First launch

The app isn't signed with a paid developer certificate, so your OS shows an
"unknown publisher" warning the first time you open it. This is expected —
skip to [Why unsigned?](#why-unsigned) if you want the reasoning.

- **macOS:** double-clicking will refuse to open it outright ("Apple could
  not verify..."). Go to **System Settings → Privacy & Security**, scroll to
  the message about the app being blocked, and click **Open Anyway**. Then
  open it once more and confirm. (Power-user alternative: `xattr -d
  com.apple.quarantine "Kindle Mailroom.app"` in Terminal, once, then open it
  normally.)
- **Windows:** SmartScreen shows "Windows protected your PC." Click **More
  info**, then **Run anyway**.

Either way, this is a one-time step per download — later launches open
normally. Your browser then opens straight to the setup wizard, same as the
command-line version.

## Where things live

There's no installer, so there's nothing to place — the app is a single
file (Windows) or a single `.app` bundle (macOS) you can put wherever you'd
put any app, or leave in Downloads.

- **Your data** (config, Google sign-in, delivery history, generated EPUBs)
  lives in the OS-standard per-user data directory, same as the command-line
  version — shown on the Settings page.
- **Logs** live alongside your data, as `mailroom.log`. Once it passes about
  1 MB it's rolled over to `mailroom.log.1`, so at most two files ever exist.
  Since a windowed app has no terminal, this is where to look if something
  goes wrong — everything that would print to a terminal goes here instead,
  including the subjects of the emails being sent.

## Quitting

There's no terminal to `Ctrl+C`, so every page has a **Quit** link in the
footer. If a send is in progress it'll ask you to confirm first, since
quitting mid-send leaves it incomplete.

Opening the app again while it's already running doesn't start a second
copy — it just brings you back to the running one.

## No auto-update

The app never phones home to check for a new version, on purpose — that's
the same "nothing leaves your machine except the fetches you ask for"
promise the command-line version makes (see [SECURITY.md](../SECURITY.md)
for the exact list). Check
[Releases](https://github.com/cipshadow/mailroom/releases) yourself
occasionally; a new download replaces the old one directly (your data isn't
touched).

## Why unsigned?

Code-signing certificates cost money every year — an Apple Developer account
plus notarization, a separate certificate for Windows — and this is a free,
open-source project with no revenue behind it. Rather than pass that cost on
or skip a desktop build entirely, it ships unsigned: the OS warnings above
are the tradeoff. The source is public; you can read exactly what you're
running before you click through them.
