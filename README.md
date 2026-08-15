# growth-reporter

**Your weekly growth report, written and delivered while you sleep.**

Every Tuesday it pulls the last complete week from Google Analytics 4 and Search Console, compares it to the week before (and a 4-week average), and delivers a report: traffic by channel, your key events, search winners and losers — with a TL;DR written by an AI model of your choice, or a solid rule-based summary with no AI at all.

```
# Weekly Growth Report — PushEngage
**Week of Aug 3 – Aug 9, 2026**

## TL;DR
Sessions ▲ 7.2% week-over-week (4,043 vs 3,772). Biggest event move:
signup_success ▲ 75.0%. Search clicks ▼ 0.2%.

| Metric   | This week | Last week | Δ      | 4-wk avg |
|----------|-----------|-----------|--------|----------|
| Sessions | 4,043     | 3,772     | ▲ 7.2% | 3,872    |
...
### Winning queries          ### Losing queries
| push engage  10 → 16 |     | pushengage  61 → 49 |
```

The full markdown report is saved to a `reports/` folder (or committed straight into your repo on GitHub Actions); a short summary goes to Slack or Telegram.

**Setup is designed for non-developers:** sign in with Google in your browser, then pick your property, Search Console site, and events from menus. No API consoles, no numeric IDs.

---

## Option A — run it on your own computer

**Step 1.** Open Terminal (Mac: press `Cmd+Space`, type "Terminal", press Enter).

**Step 2.** Copy-paste and press Enter:

```bash
git clone https://github.com/NirvanaGuha/growth-reporter && cd growth-reporter
./install.sh
```

**Step 3.** The wizard opens your browser → **sign in with the Google account you use for Analytics/Search Console** (read-only access), then shows menus to pick:
1. your GA4 property,
2. your Search Console site (or skip it),
3. the hostnames that are really yours (filters out spam),
4. the events that matter (signups, purchases).

**Step 4.** The installer prints a cron line. Run `crontab -e`, paste it, save — reports now arrive every Tuesday.

```bash
./.venv/bin/growth-reporter run --dry    # print this week's report right now
./.venv/bin/growth-reporter doctor       # check config / auth / APIs
./.venv/bin/growth-reporter test-alert   # verify Slack/Telegram delivery
```

<details>
<summary><b>If the browser sign-in says "no OAuth client available"</b></summary>

The sign-in flow needs a (free) Google "OAuth client". Create your own once — 5 minutes:

1. Go to [console.cloud.google.com](https://console.cloud.google.com) → project dropdown → **New project** → name it anything → Create.
2. Search and **Enable** three APIs: "Google Analytics Data API", "Google Analytics Admin API", "Google Search Console API".
3. **APIs & Services → OAuth consent screen** → External → fill the required fields → Save. Add your own email under Test users.
4. **Credentials → Create credentials → OAuth client ID** → Application type: **Desktop app** → Create → **Download JSON**.
5. Point the tool at it and rerun:
   ```bash
   export GA4_OAUTH_CLIENT_JSON="$HOME/Downloads/client_secret_XXXX.json"
   ./.venv/bin/growth-reporter init
   ```
</details>

---

## Option B — GitHub Actions (no computer needs to stay on)

Runs weekly on GitHub's servers for free, and commits each report into your repo so you build a browsable archive. Requires a **service account** (a robot Google identity that works unattended).

<details>
<summary><b>Step-by-step (≈10 minutes, no prior knowledge assumed)</b></summary>

**1. Fork this repository** (Fork button, top right).

**2. Create the service account.**
1. [console.cloud.google.com](https://console.cloud.google.com) → New project → name it "reporter".
2. Search "Google Analytics Data API" → **Enable**. Repeat for "Google Search Console API".
3. Search "Service accounts" → **Create service account** → name it → Create → Done.
4. Open it → **Keys → Add key → Create new key → JSON** → a file downloads.
5. Copy the service account's **email** (ends in `.iam.gserviceaccount.com`).

**3. Grant it read access.**
- GA4: [analytics.google.com](https://analytics.google.com) → Admin → **Property access management** → + → paste the email → role **Viewer**.
- Search Console: [search.google.com/search-console](https://search.google.com/search-console) → your property → Settings → **Users and permissions** → Add user → paste the email → **Restricted**.

**4. Add secrets to your fork.** Settings → Secrets and variables → Actions → New repository secret:
- `GA4_SA_JSON` — the whole JSON key file content (required)
- `REPORTER_SLACK_WEBHOOK` and/or `REPORTER_TELEGRAM_TOKEN` + `REPORTER_TELEGRAM_CHAT_ID` (optional — see guides below)
- `LLM_API_KEY` (optional, for the AI TL;DR)

**5. Configure.** Edit `config.example.yaml` in your fork (property ID is under GA4 Admin → Property settings), rename it to `reporter.yaml`, commit.

**6. Enable.** Actions tab → enable workflows → "Weekly Growth Report" → **Run workflow** to test. Reports arrive Tuesdays 07:00 UTC and are committed to `reports/` in your repo.

</details>

---

## Delivery channels

<details>
<summary><b>Slack — get a webhook URL (≈3 minutes)</b></summary>

1. [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → From scratch → pick your workspace.
2. **Incoming Webhooks** → toggle On → **Add New Webhook to Workspace** → pick a channel → Allow.
3. Copy the URL. Set it as `REPORTER_SLACK_WEBHOOK` (env var locally / Actions secret).
4. Verify: `growth-reporter test-alert`.
</details>

<details>
<summary><b>Telegram — reports on your phone (≈3 minutes)</b></summary>

1. Message **@BotFather** → `/newbot` → follow prompts → copy the **token**.
2. Message your new bot anything once.
3. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser → find `"chat":{"id":…}` → that's your **chat ID**.
4. Set `REPORTER_TELEGRAM_TOKEN` and `REPORTER_TELEGRAM_CHAT_ID`.
5. Verify: `growth-reporter test-alert`.
</details>

Anything else: set `REPORTER_WEBHOOK_URL` to any HTTPS endpoint (Zapier/Make/n8n hooks work) — it receives `{"text": "..."}` as JSON.

---

## The AI TL;DR (optional, any LLM)

Works with **any OpenAI-compatible API** — pick whichever you already use, including free local models. Without it, you get a rule-based TL;DR instead; the report never depends on the AI being up.

| Provider | `base_url` | example `model` | API key |
|---|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| Anthropic | `https://api.anthropic.com/v1` | `claude-opus-5` | [console.anthropic.com](https://console.anthropic.com/settings/keys) |
| OpenRouter | `https://openrouter.ai/api/v1` | `anthropic/claude-sonnet-5` | [openrouter.ai/keys](https://openrouter.ai/keys) |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` | [console.groq.com/keys](https://console.groq.com/keys) |
| Ollama (local, free) | `http://localhost:11434/v1` | `llama3.1` | none |
| LM Studio (local, free) | `http://localhost:1234/v1` | your loaded model | none |

Set `narration.base_url` + `narration.model` in `reporter.yaml`; the key goes in the `LLM_API_KEY` env var. Only aggregate weekly numbers are sent — never URLs with parameters, never user-level data.

---

## Notes on data quirks

- **Why Tuesday?** Search Console finalizes data ~2 days late; by Tuesday the week ending Sunday is complete.
- **`sc-domain` properties count every subdomain** — including spammy ones you don't control. Set `gsc_url_contains: "www.yoursite.com"` to keep the search section honest.
- **GA4 hostname filters** (`dimension_filters`) keep referral spam and staging traffic out of your traffic numbers.
- Query movers have a noise floor (`min_mover_clicks`, default 3) so one-click queries don't dominate the winners/losers lists.

## Tests

```bash
python tests/test_compose.py    # no network, no credentials needed
```

## License

MIT
