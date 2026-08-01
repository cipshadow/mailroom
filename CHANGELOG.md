# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-07-30

Free, unsigned desktop apps for macOS and Windows — no Python, no terminal.

### Added
- **Desktop apps** for macOS (Apple Silicon and Intel) and Windows, downloadable
  from [Releases](https://github.com/cipshadow/mailroom/releases/latest).
  Double-click to launch; the browser opens straight to the setup wizard, same
  as the command-line version. See
  [docs/install-desktop.md](docs/install-desktop.md) for first-launch steps
  (they're unsigned, so the OS warns you once) and where data/logs live.
- **A Quit control** in the footer of every page — the desktop apps have no
  terminal to `Ctrl+C`, so this is now the one way to stop the server on any
  platform. Confirms first if a send is in progress.
- Opening the app while it's already running now finds the running instance
  and opens it, instead of failing to bind the port or starting a second copy.

### Changed
- **New default labels for fresh installs**: `Mailroom/Send next 📤` (watched)
  and `Mailroom/Sent ✅` (delivered), both nested under one `Mailroom` heading
  in Gmail's sidebar. Existing installs keep whatever labels they configured.
- **Every labelled email is now sent, read or unread.** Previously only unread
  mail was picked up, which silently skipped anything you'd already opened.
  The old behavior is available as an "Only send unread emails" toggle in
  Settings. `send --include-read` still forces read mail for one run.
- **No send limit by default.** "Max emails per run" now defaults to 0
  (no limit — pages through everything labelled); set a number in Settings to
  cap it. Existing installs keep their saved limit.
- No behavior change for existing pipx/pip installs from the desktop-app work
  itself — the desktop app is an additional way to run the same code, not a
  replacement.

### Fixed
- **Digest mode grouped every newsletter on a shared sending platform into
  one combined weekly digest**, regardless of who wrote it — every Substack
  author sends from a `*.substack.com`-family address, so they all collapsed
  into one "Substack" document. Digests are now grouped by the sender's
  display name instead of their email domain.
- Digest titles were `[sender] [ISO date]`, paired with a filename that
  repeated the date again (`2026-07-30 - Substack 2026-07-30.epub`) — visibly
  duplicated. Digest titles (and the email subject) are now
  `[blog name] - dd/m digest`, e.g. `Lenny's Newsletter - 30/7 digest`.
- Google sign-in could fail with `invalid_grant: Missing code verifier` on
  every connection attempt. The OAuth callback rebuilt the PKCE flow from
  scratch instead of reusing the code verifier generated at the start of
  sign-in; it's now carried through the session like the OAuth state already
  was.
- If sign-in succeeded but reading your Gmail address failed (e.g. the Gmail
  API wasn't enabled yet), the wizard marked "Connect account" as done and
  stranded you on step 3 with no way to retry the connection. It now returns
  to step 2 so you can reconnect.

## [0.2.0] — 2026-07-28

Onboarding overhaul plus a batch of device-verified rendering fixes.

### Added
- **Guided Google Cloud setup.** Each step in the wizard now deep-links straight
  to the right console page (create project → enable Gmail API → consent screen
  → create client) instead of describing a path to navigate by hand, with a
  fallback note for when Google rearranges the console.
- **Progress indicator** in the setup wizard ("Step 2 of 3"), so it's clear how
  much is left. Step 3 can now show a completed state and a link onward.
- **"How do I label an email?" explainer** in the wizard and in Settings —
  covering Gmail on the web, Gmail on a phone, and creating a filter to label a
  newsletter automatically. It also spells out that only *unread* labelled
  emails are picked up.
- **"Start over" button** in the wizard. Previously, an OAuth client that was
  well-formed but wrong left you stuck: Settings (with its *Forget credentials*
  button) sits behind the setup gate, so the only way out was deleting files by
  hand.
- Screenshots in the README, a favicon, and this changelog.

### Changed
- **Default labels are now `Send to Kindle` and `Send to Kindle/Sent`** (was
  `Reading` / `Kindle/Sent`). The `/` makes the sent label nest under the
  watched label in Gmail's sidebar, so you can browse everything already
  delivered. **Existing installs keep their saved labels** — a saved config
  always wins over these defaults, so this only affects fresh setups.
- `@free.kindle.com` addresses are accepted everywhere. They were documented as
  supported but rejected by the address check, which hard-blocked anyone
  following the docs.
- Renaming a label in Settings now creates it in Gmail. Previously the rename
  saved fine and then every send failed with `LabelNotFoundError`.
- Failing to pre-create labels during setup now shows a warning instead of only
  writing to the log — setup still completes.
- A rejected Kindle address no longer discards the label and digest choices you
  just typed.
- Running the app on a port that's already in use prints what to do next
  instead of a traceback.
- The history page and its confirmation dialog use your configured label name
  rather than a hardcoded "reading label".

### Fixed
- Newsletters whose templates wrap the body in `<center>` are no longer
  centre-aligned on the device. The `<center>` element survived sanitization
  because, unlike `align=`/`style=`, it has no attribute to strip.
- Inline icons no longer render enormous. Senders often declare image size only
  in CSS (`style="width: 14px"`); that was invisible to the size logic, which
  fell back to the source file's dimensions — so a 14px icon shipped at its full
  512px size. Pixel sizes are now lifted out of `style=` before it is stripped,
  which also means such icons are correctly filtered out as decorative chrome.

## [0.1.0]

Initial release: Gmail label → EPUB → Kindle, weekly digests, URL-to-Kindle,
delivery history, in-app scheduling, and a local setup wizard.
