# Setting up your Google key

Kindle Mailroom reads and sends mail as you, using a key that only you hold.
There's no shared server behind the app, so it can't ship with a built-in
key — each person creates their own, free, in about five minutes.

Every step below links straight to the right page. Do them in order, and make
sure your new project stays selected as you go.

1. **[Create a project](https://console.cloud.google.com/projectcreate)** —
   any name works, e.g. `kindle-mailroom`.
2. **[Enable the Gmail API](https://console.cloud.google.com/flows/enableapi?apiid=gmail.googleapis.com)**
   → click **Enable**.
3. **[Set up the consent screen](https://console.cloud.google.com/auth/overview)**
   → **Get started**. Give the app a name (e.g. "Kindle Mailroom"), use your own
   email as the contact, and choose audience **External**. Finish the short
   wizard.
4. **[Add yourself as a test user](https://console.cloud.google.com/auth/audience)**
   → under **Test users**, click **Add users** and enter your own Gmail address.
   You do not need to submit the app for verification — leaving it in "Testing"
   is fine for personal use.
5. **[Create the client](https://console.cloud.google.com/auth/clients/create)**
   → application type **Desktop app** → **Create** → **Download JSON**.

   Choose *Desktop app*, not *Web application*: desktop clients accept Kindle
   Mailroom's local redirect without you having to register a redirect URI,
   which removes the single most error-prone step of this whole process.
6. In the Kindle Mailroom setup wizard, upload or paste that JSON file.

> **If a link 404s:** Google rearranges this console regularly. Open
> [console.cloud.google.com](https://console.cloud.google.com/), check your
> project is selected in the top bar, and search for "Gmail API", "Google Auth
> Platform", or "Credentials". (Consent-screen settings used to live under
> *APIs & Services → OAuth consent screen* and now sit under *Google Auth
> Platform*, so older write-ups you find elsewhere may not match what you see.)

## What Kindle Mailroom can access

It requests exactly two Gmail scopes, and nothing else:

| Scope | Why |
|---|---|
| `gmail.modify` | Read your mail and change labels — to find labelled emails and file them once sent. It does **not** allow deleting messages. |
| `gmail.send` | Email the generated EPUB to your Kindle address. |

Everything runs on your machine; nothing is sent anywhere except those Gmail
API calls, any article URL you paste into **Send a URL**, and the image
downloads needed to build each EPUB.

## Why "Testing" mode shows a warning

Google shows an "unverified app" screen before the consent prompt because the
app hasn't gone through Google's public-app review — expected, since it's
**your own** app that only you use. Click **Continue**.

## Tokens expire after 7 days in Testing mode

Google limits refresh tokens for apps in Testing mode to 7 days of inactivity.
Kindle Mailroom tells you when this happens (an `invalid_grant` error). Fix it
from **Settings → Reconnect Google account** — it takes a few seconds.

If that becomes annoying, you can switch your app from "Testing" to "In
production" in the Google Auth Platform console without submitting for
verification; for a single-user, non-public app this is normally fine, but
consult Google's current policy if in doubt.
