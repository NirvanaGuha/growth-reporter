"""OAuth client used by `growth-reporter init` for the browser sign-in flow.

For an installed (desktop) app, the client secret is not confidential — Google's
own docs say so, and tools like rclone and gcloud ship theirs embedded. Embedding
one here means end users get a pure "sign in with Google" experience with zero
cloud-console work.

To embed yours: Google Cloud console → create a project → enable the
"Google Analytics Data API" and "Google Analytics Admin API" → OAuth consent
screen (External, add the analytics.readonly scope) → Credentials →
Create OAuth client ID → Desktop app → paste the two values below.

Until then, `init` falls back to asking for a client_secrets.json path
(or the GA4_OAUTH_CLIENT_JSON env var).
"""

EMBEDDED_CLIENT_ID: str | None = None
EMBEDDED_CLIENT_SECRET: str | None = None
