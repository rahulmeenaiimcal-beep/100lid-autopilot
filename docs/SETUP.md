# One-time setup (about 30–45 minutes)

You only do this once. Go slowly. Each step says exactly where to click.
Where a step asks you to copy a key, **you** paste it into GitHub. Keys are like passwords: never share them in chat or email.

---

## Step 1 — The free AI writer (Gemini) · 5 minutes

1. Open **https://aistudio.google.com/apikey** and sign in with any Google account.
2. Click **Create API key**, then copy the long key it shows.
3. Open your repo on GitHub: **rahulmeenaiimcal-beep/100lid-autopilot**.
4. Click **Settings** (top bar) → in the left menu **Secrets and variables** → **Actions**.
5. Click the green **New repository secret** button.
6. Name: `GEMINI_API_KEY` · Secret: paste the key → **Add secret**.

**Optional backup writer (recommended):** at **https://console.groq.com/keys** create a key, and add it the same way with the name `GROQ_API_KEY`. If Gemini is ever busy, the robot uses Groq. Groq is also used as the second, independent fact-checker.

---

## Step 2 — Connect YouTube · 20–30 minutes

> ⚠️ Use the **Google account that owns the 100LID - EDUCATION channel**.
> The robot double-checks the channel ID before every upload, so it can never post to another channel by mistake.

### 2a. Create a Google Cloud project
1. Open **https://console.cloud.google.com/** (signed in with the 100LID Google account).
2. Top bar → project picker → **New project** → name it `100LID Autopilot` → **Create**, then select it.
3. Left menu → **APIs & Services** → **Library**. Search for and **Enable** both of these:
   - **YouTube Data API v3**
   - **YouTube Analytics API**

### 2b. The consent screen (who is allowed to log in)
1. **APIs & Services** → **OAuth consent screen** (or "Google Auth Platform" → **Branding**).
2. App name: `100LID Autopilot`. Support email: your email. **Audience/User type: External**. Save.
3. Go to **Audience** and click **Publish app** → confirm. The status must say **In production**.
   *(If you skip this, YouTube logs the robot out every 7 days.)*
   Google may say the app is "unverified". That is fine, because only you use it.

### 2c. Create the login keys
1. **APIs & Services** → **Credentials** → **Create credentials** → **OAuth client ID**.
2. Application type: **Web application**. Name: `robot`.
3. Under **Authorized redirect URIs** click **Add URI** and paste exactly:
   `https://developers.google.com/oauthplayground`
4. **Create**. Copy the **Client ID** and the **Client secret**.
5. In GitHub (as in Step 1) add two secrets:
   - `YT_CLIENT_ID` = the Client ID
   - `YT_CLIENT_SECRET` = the Client secret

### 2d. Get the "refresh token" (lets the robot stay logged in)
1. Open **https://developers.google.com/oauthplayground**.
2. Click the ⚙️ gear (top right) → tick **Use your own OAuth credentials** → paste your Client ID and Client secret → close.
3. On the left, in the box **"Input your own scopes"**, paste these three lines together, separated by spaces:
   ```
   https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.force-ssl https://www.googleapis.com/auth/yt-analytics.readonly
   ```
4. Click **Authorize APIs** → sign in with the 100LID Google account → **choose the 100LID - EDUCATION channel** if asked.
   If you see "Google hasn't verified this app": click **Advanced** → **Go to 100LID Autopilot (unsafe)** → **Continue**/**Allow**. It's your own app.
5. Back in the Playground, click **Exchange authorization code for tokens**.
6. Copy the **Refresh token** and add it to GitHub as the secret `YT_REFRESH_TOKEN`.

---

## Step 3 — Test everything · 3 minutes
1. In GitHub, click **Actions** → **Autopilot** (left) → **Run workflow** → job: **check** → green **Run workflow**.
2. After about 1–2 minutes, open the run. The summary shows a table: every row should have ✅.
   The YouTube row must say **100LID - EDUCATION**.

## Step 4 — Make sure you get the review emails
1. GitHub → your picture (top right) → **Settings** → **Notifications** → make sure **Email** is ticked for "Participating" and "Watching".
2. On the repo page, the **Watch** button should say "Watching" or "All activity".

## Step 5 — Custom thumbnails
YouTube only allows custom thumbnails on verified channels. In **YouTube Studio → Settings → Channel → Feature eligibility**, make sure **Intermediate features** are on (phone verification).

---

## When it's all set
The robot starts on its own. The first video arrives about 2 days before Tuesday 6 pm.

**To pause the robot:** Actions → Autopilot → "…" (top right) → **Disable workflow**.
**To make a video right now:** Actions → Autopilot → Run workflow → job **long** (tick Upload) or **short**.
**To test without posting:** job **long** with Upload unticked → open the run → download the video under **Artifacts**.
