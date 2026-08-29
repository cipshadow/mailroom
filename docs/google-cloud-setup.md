# Setting up your Google key

Kindle Mailroom reads and sends mail as you, using a key that only you hold.
There's no shared server behind the app, so it can't ship with a built-in
key — each person creates their own, free, in about five minutes.

Every step below links straight to the right page. Do them in order, and make
sure your new project stays selected as you go.

1. **[Create a project](https://console.cloud.google.com/projectcreate)** —
   name it **Kindle Mailroom**. Leave **Organization** set to "No
   organization" (it only shows up if your Google account belongs to a
   Google Workspace org; for a personal Gmail account it's the only option
   anyway, and it has no effect on how the app works).
2. **[Enable the Gmail API](https://console.cloud.google.com/flows/enableapi?apiid=gmail.googleapis.com)**
   for the project you just created.

   > ⚠️ **This is the step people miss.** The page loads with an **Enable**
   > button front and center — you have to actually click it, not just land
   > on the page. Nothing on the page auto-enables the API for you.
   >
   > **You're not done until the button itself changes.** After clicking
   > Enable, wait for the page to reload — it now shows a **Manage** button
   > and a usage graph instead of Enable. That's your confirmation. If you
   > still see an **Enable** button anywhere on the page, it isn't on yet -
   > click it again.
   >
   > If you skip this and try to connect Kindle Mailroom anyway, you'll get
   > an error naming your project number, e.g. *"Gmail API has not been
   > used in project 123456789...".* Fix: go back to this same page (using
   > the project number from that error if you're not sure you're on the
   > right project), click **Enable**, confirm it now says **Manage**, wait
   > 2-3 minutes, then retry in Kindle Mailroom.
3. **[Set up the consent screen](https://console.cloud.google.com/auth/overview)**
   → **Get started**. On the first page (**App Information**), name it
   **Kindle Mailroom** and use your own email as the contact. Continue
   through the wizard's own steps until you reach **Audience** — choose
   **External** there.
4. **Add yourself as a test user.** Still on the **Audience** page (or via
   **[this direct link](https://console.cloud.google.com/auth/audience)**
   if you've already moved past it): under **Test users**, click **Add
   users** and enter your own Gmail address. Finish the rest of the wizard.
   You do not need to submit the app for verification — leaving it in
   "Testing" is fine for personal use.
5. **[Create the client](https://console.cloud.google.com/auth/clients/create)**
   → application type **Desktop app** → name it **Kindle Mailroom** (this
   name only shows up in your own Cloud console, never to you-as-end-user,
   but it keeps things unambiguous if you ever have more than one OAuth
   client) → **Create** → **Download JSON**.

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
