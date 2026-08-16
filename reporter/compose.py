"""Gather one week of GA4 + GSC data and compose the report.

Window = the last complete Monday–Sunday week. Comparison = the week before it,
plus a trailing 4-week average for context.
"""
from datetime import date, timedelta


# ── date windows ─────────────────────────────────────────────────────────

def last_complete_week(today: date | None = None) -> tuple[date, date]:
    """Most recent full Mon–Sun week."""
    today = today or date.today()
    last_sunday = today - timedelta(days=today.weekday() + 1)
    return last_sunday - timedelta(days=6), last_sunday


def windows(today: date | None = None) -> dict:
    mon, sun = last_complete_week(today)
    prev_mon, prev_sun = mon - timedelta(days=7), sun - timedelta(days=7)
    four_start = mon - timedelta(days=28)
    return {
        "this": (mon.isoformat(), sun.isoformat()),
        "prev": (prev_mon.isoformat(), prev_sun.isoformat()),
        "four_weeks": (four_start.isoformat(), (mon - timedelta(days=1)).isoformat()),
        "label": f"{mon.strftime('%b %-d')} – {sun.strftime('%b %-d, %Y')}",
    }


# ── math / formatting helpers (pure, unit-tested) ────────────────────────

def pct_change(now: float, before: float) -> float | None:
    if before == 0:
        return None
    return (now - before) / before * 100


def fmt_delta(now: float, before: float) -> str:
    d = pct_change(now, before)
    if d is None:
        return "new" if now else "—"
    arrow = "▲" if d > 0 else ("▼" if d < 0 else "＝")
    return f"{arrow} {abs(d):.1f}%"


def fmt_int(n) -> str:
    return f"{int(round(n)):,}"


# ── GA4 gathering ────────────────────────────────────────────────────────

def _sum_series(series: dict[str, dict[str, int]], metric: str) -> int:
    return sum(v.get(metric, 0) for v in series.values())


def gather_ga4(cfg: dict) -> dict:
    from .services import get_ga
    GA = get_ga(cfg)
    w = windows()
    out = {"windows": w, "metrics": {}, "events": {}, "channels": {}}

    # One 5-week pull covers this week, prev week, and the 4-week average.
    full_start = w["four_weeks"][0]
    series = GA.daily_series(cfg["property_id"], full_start, w["this"][1],
                             ["sessions", "totalUsers"],
                             filters=cfg["dimension_filters"])

    def window_sum(series_, metric, win):
        lo, hi = win[0].replace("-", ""), win[1].replace("-", "")
        return sum(v.get(metric, 0) for d, v in series_.items() if lo <= d <= hi)

    for metric in ("sessions", "totalUsers"):
        out["metrics"][metric] = {
            "this": window_sum(series, metric, w["this"]),
            "prev": window_sum(series, metric, w["prev"]),
            "four_avg": window_sum(series, metric, w["four_weeks"]) / 4,
        }

    for event in cfg.get("events", []):
        ev = GA.daily_series(cfg["property_id"], full_start, w["this"][1],
                             ["eventCount"], filters=cfg["dimension_filters"],
                             event_name=event)
        out["events"][event] = {
            "this": window_sum(ev, "eventCount", w["this"]),
            "prev": window_sum(ev, "eventCount", w["prev"]),
            "four_avg": window_sum(ev, "eventCount", w["four_weeks"]) / 4,
        }

    out["channels"] = {
        "this": _channels(cfg, *w["this"]),
        "prev": _channels(cfg, *w["prev"]),
    }
    return out


def _channels(cfg: dict, start: str, end: str) -> dict[str, int]:
    from .services import get_ga
    return get_ga(cfg).dim_totals(cfg["property_id"], start, end,
                         "sessionDefaultChannelGroup", "sessions",
                         filters=cfg["dimension_filters"], limit=15)


# ── GSC gathering ────────────────────────────────────────────────────────

def gather_gsc(cfg: dict) -> dict | None:
    site = cfg.get("gsc_site")
    if not site:
        return None
    from .services import get_sc
    SC = get_sc(cfg)
    from growthkit.google.gsc import movers
    w = windows()
    uc = cfg.get("gsc_url_contains") or None
    this_q = SC.by_dimension(site, *w["this"], "query", url_contains=uc)
    prev_q = SC.by_dimension(site, *w["prev"], "query", url_contains=uc)
    gainers, losers = movers(this_q, prev_q, cfg["top_n"],
                             cfg["min_mover_clicks"])
    return {
        "totals_this": SC.totals(site, *w["this"], url_contains=uc),
        "totals_prev": SC.totals(site, *w["prev"], url_contains=uc),
        "gainers": gainers,
        "losers": losers,
        "top_pages": dict(list(SC.by_dimension(
            site, *w["this"], "page", cfg["top_n"],
            url_contains=uc).items())[:cfg["top_n"]]),
    }


# ── composition (pure, unit-tested) ──────────────────────────────────────

def rule_based_tldr(ga: dict, sc: dict | None) -> str:
    """Fallback TL;DR when no LLM is configured — biggest movers, one paragraph."""
    parts = []
    m = ga["metrics"]["sessions"]
    parts.append(f"Sessions {fmt_delta(m['this'], m['prev'])} week-over-week "
                 f"({fmt_int(m['this'])} vs {fmt_int(m['prev'])}).")
    if ga["events"]:
        biggest = max(ga["events"].items(),
                      key=lambda kv: abs(pct_change(kv[1]["this"], kv[1]["prev"]) or 0))
        name, v = biggest
        parts.append(f"Biggest event move: {name} {fmt_delta(v['this'], v['prev'])}.")
    if sc:
        parts.append(f"Search clicks {fmt_delta(sc['totals_this']['clicks'], sc['totals_prev']['clicks'])}.")
    return " ".join(parts)


def _table(rows: list[tuple], header: tuple) -> str:
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def compose_markdown(cfg: dict, ga: dict, sc: dict | None, tldr: str) -> str:
    w = ga["windows"]
    name = cfg.get("site_name") or f"property {cfg['property_id']}"
    md = [f"# Weekly Growth Report — {name}",
          f"**Week of {w['label']}** (vs the week before; 4-week average for context)",
          "", "## TL;DR", tldr, "", "## Traffic (GA4)"]

    rows = []
    labels = {"sessions": "Sessions", "totalUsers": "Users"}
    for key, label in labels.items():
        m = ga["metrics"][key]
        rows.append((label, fmt_int(m["this"]), fmt_int(m["prev"]),
                     fmt_delta(m["this"], m["prev"]), fmt_int(m["four_avg"])))
    md.append(_table(rows, ("Metric", "This week", "Last week", "Δ", "4-wk avg")))

    ch_this, ch_prev = ga["channels"]["this"], ga["channels"]["prev"]
    if ch_this:
        md += ["", "### By channel"]
        rows = [(ch, fmt_int(n), fmt_delta(n, ch_prev.get(ch, 0)))
                for ch, n in list(ch_this.items())[:8]]
        md.append(_table(rows, ("Channel", "Sessions", "Δ vs last week")))

    if ga["events"]:
        md += ["", "## Key events"]
        rows = [(e, fmt_int(v["this"]), fmt_int(v["prev"]),
                 fmt_delta(v["this"], v["prev"]), fmt_int(v["four_avg"]))
                for e, v in ga["events"].items()]
        md.append(_table(rows, ("Event", "This week", "Last week", "Δ", "4-wk avg")))

    if sc:
        t, p = sc["totals_this"], sc["totals_prev"]
        md += ["", "## Organic search (Search Console)"]
        rows = [("Clicks", fmt_int(t["clicks"]), fmt_int(p["clicks"]),
                 fmt_delta(t["clicks"], p["clicks"])),
                ("Impressions", fmt_int(t["impressions"]), fmt_int(p["impressions"]),
                 fmt_delta(t["impressions"], p["impressions"])),
                ("CTR", f"{t['ctr']*100:.2f}%", f"{p['ctr']*100:.2f}%",
                 fmt_delta(t["ctr"], p["ctr"])),
                ("Avg position", f"{t['position']:.1f}", f"{p['position']:.1f}",
                 fmt_delta(p["position"], t["position"]))]  # lower position = better
        md.append(_table(rows, ("Metric", "This week", "Last week", "Δ")))

        if sc["gainers"]:
            md += ["", "### Winning queries"]
            md.append(_table([(q, b, n, f"+{d}") for q, n, b, d in sc["gainers"]],
                             ("Query", "Last wk clicks", "This wk", "Δ")))
        if sc["losers"]:
            md += ["", "### Losing queries"]
            md.append(_table([(q, b, n, str(d)) for q, n, b, d in sc["losers"]],
                             ("Query", "Last wk clicks", "This wk", "Δ")))
        if sc["top_pages"]:
            md += ["", "### Top pages by clicks"]
            md.append(_table([(u, fmt_int(v["clicks"]), f"{v['position']:.1f}")
                              for u, v in sc["top_pages"].items()],
                             ("Page", "Clicks", "Avg pos")))

    md += ["", "---", "_Generated by growth-reporter_"]
    return "\n".join(md)


def compose_summary(cfg: dict, ga: dict, sc: dict | None, tldr: str) -> str:
    """Short plain-text version for chat channels."""
    w = ga["windows"]
    name = cfg.get("site_name") or f"property {cfg['property_id']}"
    m = ga["metrics"]
    lines = [f"📈 Weekly Growth Report — {name} — {w['label']}", "", tldr, ""]
    lines.append(f"Sessions {fmt_int(m['sessions']['this'])} "
                 f"({fmt_delta(m['sessions']['this'], m['sessions']['prev'])}) · "
                 f"Users {fmt_int(m['totalUsers']['this'])} "
                 f"({fmt_delta(m['totalUsers']['this'], m['totalUsers']['prev'])})")
    for e, v in ga["events"].items():
        lines.append(f"{e}: {fmt_int(v['this'])} ({fmt_delta(v['this'], v['prev'])})")
    if sc:
        t, p = sc["totals_this"], sc["totals_prev"]
        lines.append(f"Search clicks {fmt_int(t['clicks'])} "
                     f"({fmt_delta(t['clicks'], p['clicks'])})")
    return "\n".join(lines)
