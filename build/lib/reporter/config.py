"""Config loading and defaults. Config lives in YAML; secrets live in env vars."""
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATHS = [
    Path("reporter.yaml"),
    Path("config.yaml"),
    Path.home() / ".growth-reporter" / "config.yaml",
]

DEFAULTS = {
    "property_id": None,            # required — GA4 property
    "gsc_site": "",                 # e.g. "sc-domain:example.com" or "https://www.example.com/"; blank = skip GSC section
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


def _merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def find_config_path(explicit: str | None = None) -> Path | None:
    if explicit:
        p = Path(explicit).expanduser()
        return p if p.exists() else None
    for p in DEFAULT_CONFIG_PATHS:
        if p.expanduser().exists():
            return p.expanduser()
    return None


def load_config(explicit: str | None = None) -> dict:
    path = find_config_path(explicit)
    if path is None:
        raise FileNotFoundError(
            "No config found. Run `growth-reporter init` to create one "
            f"(searched: {', '.join(str(p) for p in DEFAULT_CONFIG_PATHS)})."
        )
    with open(path) as f:
        cfg = _merge(DEFAULTS, yaml.safe_load(f) or {})
    if not cfg.get("property_id"):
        raise ValueError(f"`property_id` missing in {path}.")
    cfg["_config_path"] = str(path)
    return cfg
