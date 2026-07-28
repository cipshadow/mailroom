# Scheduling

Kindle Mailroom has two ways to run automatically. Use one or both.

## Built-in scheduler (runs while the app is open)

Turn it on in **Settings → Schedule**: pick daily or weekly, and a time.
Every minute, while the app is running, it checks whether that time has
passed today (or this week) without a send yet, and if so sends
automatically. If the app was closed when the scheduled time arrived, it
catches up the next time you open it.

This is the simplest option, but it only works while Kindle Mailroom is
running — it is **not** a background service.

## OS-level scheduling (fully unattended)

For delivery even when the app isn't open, use your operating system's
scheduler to run the headless CLI:

```
kindle-mailroom send            # one-per-email mode, uses your saved settings
kindle-mailroom send --digest   # force weekly digest mode for this run
```

This uses the same credentials and settings you configured in the web UI —
no browser required for scheduled runs (only the one-time setup needs a
browser).

### macOS / Linux — cron

```
crontab -e
```

Add a line to run daily at 7am. `cron` runs with a minimal `PATH`, so the
command is given by absolute path — run `which kindle-mailroom` and paste the
result if `$(which ...)` doesn't resolve inside your crontab:

```
# macOS
0 7 * * * "$(which kindle-mailroom)" send >> "$HOME/Library/Logs/kindle-mailroom-cron.log" 2>&1
# Linux
0 7 * * * "$(which kindle-mailroom)" send >> "$HOME/kindle-mailroom-cron.log" 2>&1
```

### macOS — launchd (an alternative to cron)

Save as `~/Library/LaunchAgents/com.kindlemailroom.send.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.kindlemailroom.send</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/kindle-mailroom</string>  <!-- use the output of: which kindle-mailroom -->
    <string>send</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>7</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key><string>/tmp/kindle-mailroom.log</string>
  <key>StandardErrorPath</key><string>/tmp/kindle-mailroom.err</string>
</dict>
</plist>
```

Load it with:

```
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kindlemailroom.send.plist
```

### Windows — Task Scheduler

1. Open **Task Scheduler → Create Basic Task**.
2. Name it "Kindle Mailroom", trigger **Daily** at your preferred time.
3. Action: **Start a program**. Program/script: the full path to
   `kindle-mailroom.exe` (find it with `where kindle-mailroom` in a
   Command Prompt after installing). Arguments: `send`.
4. Finish. Test it once with **Run** in Task Scheduler to confirm it works.
