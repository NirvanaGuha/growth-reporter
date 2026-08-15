"""Delivery: markdown file always; stdout/Slack/Telegram/webhook for the summary."""
import json
import os
from pathlib import Path

import requests


def write_report(md: str, cfg: dict, week_start: str) -> Path:
    d = Path(cfg["report_dir"]).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"growth-report-{week_start}.md"
    path.write_text(md)
    return path


def _env(channels: dict, key: str) -> str | None:
    name = channels.get(key)
    return os.environ.get(name) if name else None


def send_summary(text: str, cfg: dict, report_path: Path | None = None) -> list[str]:
    channels = cfg["channels"]
    sent = []
    footer = f"\n\nFull report: {report_path}" if report_path else ""

    if channels.get("stdout", True):
        print(text + footer)
        sent.append("stdout")

    slack_url = _env(channels, "slack_webhook_env")
    if slack_url:
        r = requests.post(slack_url, json={"text": text + footer}, timeout=15)
        if r.ok:
            sent.append("slack")

    tg_token = _env(channels, "telegram_bot_token_env")
    tg_chat = _env(channels, "telegram_chat_id_env")
    if tg_token and tg_chat:
        r = requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage",
                          json={"chat_id": tg_chat, "text": text}, timeout=15)
        if r.ok:
            sent.append("telegram")

    hook = _env(channels, "generic_webhook_env")
    if hook:
        r = requests.post(hook, data=json.dumps({"text": text}),
                          headers={"Content-Type": "application/json"}, timeout=15)
        if r.ok:
            sent.append("webhook")

    return sent
