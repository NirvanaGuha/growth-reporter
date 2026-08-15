"""Optional LLM TL;DR via any OpenAI-compatible endpoint. Falls back to the
rule-based TL;DR in compose.py — the report never ships without a summary."""
import json
import os

import requests


def is_configured(cfg: dict) -> tuple[bool, str]:
    n = cfg["narration"]
    if not n.get("enabled"):
        return False, "disabled in config"
    if not n.get("base_url") or not n.get("model"):
        return False, "narration.base_url / narration.model not set"
    return True, f"{n['model']} @ {n['base_url']}"


def llm_tldr(cfg: dict, ga: dict, sc: dict | None) -> str | None:
    ok, _ = is_configured(cfg)
    if not ok:
        return None
    n = cfg["narration"]

    digest = {
        "week": ga["windows"]["label"],
        "metrics": ga["metrics"],
        "events": ga["events"],
        "channels_this_week": ga["channels"]["this"],
        "channels_last_week": ga["channels"]["prev"],
    }
    if sc:
        digest["search"] = {
            "totals_this_week": sc["totals_this"],
            "totals_last_week": sc["totals_prev"],
            "winning_queries": [{"query": q, "this": nw, "last": b, "delta": d}
                                for q, nw, b, d in sc["gainers"]],
            "losing_queries": [{"query": q, "this": nw, "last": b, "delta": d}
                               for q, nw, b, d in sc["losers"]],
        }
    extra = n.get("extra_context") or ""

    prompt = (
        "You are a growth analyst writing the executive summary of a weekly "
        "website report. Here is this week's data as JSON (this week vs last "
        "week; four_avg = trailing 4-week weekly average):\n\n"
        + json.dumps(digest, indent=1)
        + (f"\n\nSite context: {extra}" if extra else "")
        + "\n\nWrite a TL;DR of 3-5 sentences, plain prose, no headers or bullet "
        "points. Lead with the most decision-relevant change, note what moved "
        "together (or didn't), call out one thing worth investigating or one win "
        "worth doubling down on. Use concrete numbers sparingly. Do not invent "
        "data you weren't given."
    )

    headers = {"Content-Type": "application/json"}
    key = os.environ.get(n.get("api_key_env") or "LLM_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"

    try:
        r = requests.post(
            n["base_url"].rstrip("/") + "/chat/completions",
            headers=headers,
            json={"model": n["model"],
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 600},
            timeout=120,
        )
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
        return text.strip() or None
    except Exception:
        return None
