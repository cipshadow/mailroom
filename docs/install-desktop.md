# Installing the desktop app

This covers the macOS and Windows downloads from the
[GitHub Releases page](https://github.com/cipshadow/mailroom/releases). If you'd
rather run it from a terminal (or you're on Linux), see [Installing](../README.md#installing)
in the README instead — both paths run the exact same app. The short version
for a first launch is also there; this page is the detail behind it.

## First launch

The app isn't signed with a paid developer certificate, so your OS shows an
"unknown publisher" warning the first time you open it. This is expected —
skip to [Why unsigned?](#why-unsigned) if you want the reasoning.

Move **Kindle Mailroom** into your **Applications** folder before the first
launch on a Mac. The steps below assume that's where it lives.

- **macOS:** opening it says macOS can't verify the developer.
  - **macOS 15 Sequoia and later:** go to **System Settings**, then
    **Privacy & Security**, scroll down, and click **Open Anyway**, then
    confirm.
  - **Older macOS:** right-click the app and choose **Open**.
  - **Terminal, once:** `xattr -dr com.apple.quarantine "/Applications/Kindle Mailroom.app"`,
    then open it normally.
- **Windows:** SmartScreen shows "Windows protected your PC." Click **More
  info**, then **Run anyway**.

Either way, this is a one-time step per download — later launches open
normally. The app then opens the setup wizard. The command-line version
opens that same wizard in your browser.

## Where things live

There's no installer. On a Mac, keep **Kindle Mailroom** in Applications.
On Windows it's a single `.exe` you can run from Downloads or put wherever
you keep programs.

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

It's a free open-source app built by an indie developer, without a paid
signing certificate, and the source is right here. Code-signing certificates
cost money every year — an Apple Developer account (what notarization
requires) and a separate certificate for Windows — and there's no revenue
behind the project. Rather than pass that cost on or skip a desktop build
entirely, the apps ship unsigned: the OS warnings above are the tradeoff.

## Verify your download

Each release includes `SHA256SUMS.txt`. Because the apps are unsigned, this is
how you confirm the file you downloaded is the one that was published:

```bash
# macOS
shasum -a 256 KindleMailroom-*.zip
# Windows (PowerShell)
Get-FileHash KindleMailroom-*.exe -Algorithm SHA256
```

Compare the result with the matching line in `SHA256SUMS.txt` from the same
release page. If they differ, do not run the file.
