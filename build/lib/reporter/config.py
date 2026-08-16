"""Reporter config: growthkit loader + this app's defaults."""
from pathlib import Path

from growthkit import config as kit_config

APP = "growth-reporter"

DEFAULTS = {
    "property_id": None,            # required — GA4 property
    "gsc_site": "",                 # e.g. "sc-domain:example.com" or "https://www.example.com/"; blank = skip GSC section
    "gsc_url_contains": "",         # only count search data for pages containing this (filters spam subdomains)
    "site_name": "",                # display name for the report header
    "events": [],                   # key GA4 events to include
    "dimension_filters": [],        # same shape as ga4-watchdog (hostname filters etc.)
    "top_n": 5,                     # movers/pages shown per list
    "min_mover_clicks": 3,          # ignore movers below this many weekly clicks
    "report_dir": "reports",        # weekly .md files land here
    "channels": {
        "stdout": True,
        "slack_webhook_env": "REPORTER_SLACK_WEBHOOK",
        "telegram_bot_token_env": "REPORTER_TELEGRAM_TOKEN",
        "telegram_chat_id_env": "REPORTER_TELEGRAM_CHAT_ID",
        "generic_webhook_env": "REPORTER_WEBHOOK_URL",
    },
    "narration": {
        "enabled": True,            # LLM-written TL;DR; falls back to rule-based
        "base_url": "",             # any OpenAI-compatible endpoint (see README)
        "model": "",
        "api_key_env": "LLM_API_KEY",
        "extra_context": "",
    },
}


# Back-compat: this app searched reporter.yaml before growthkit existed.
_LEGACY = Path("reporter.yaml")


def load_config(explicit: str | None = None) -> dict:
    if explicit is None and _LEGACY.exists():
        explicit = str(_LEGACY)
    return kit_config.load(APP, DEFAULTS, required=("property_id",), explicit=explicit)
