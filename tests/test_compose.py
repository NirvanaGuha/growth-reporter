"""Unit tests for report composition — synthetic data, no network."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from reporter.compose import (compose_markdown, compose_summary, fmt_delta,
                              last_complete_week, pct_change, rule_based_tldr,
                              windows)
from growthkit.google.gsc import movers

CFG = {"property_id": "123", "site_name": "Example.com", "events": ["sign_up"],
       "top_n": 5, "min_mover_clicks": 3}

GA = {
    "windows": {"this": ("2026-08-03", "2026-08-09"), "prev": ("2026-07-27", "2026-08-02"),
                "four_weeks": ("2026-07-06", "2026-08-02"), "label": "Aug 3 – Aug 9, 2026"},
    "metrics": {"sessions": {"this": 5200, "prev": 4800, "four_avg": 4900.0},
                "totalUsers": {"this": 4100, "prev": 4200, "four_avg": 4000.0}},
    "events": {"sign_up": {"this": 120, "prev": 90, "four_avg": 100.0}},
    "channels": {"this": {"Organic Search": 3000, "Direct": 1500},
                 "prev": {"Organic Search": 2800, "Direct": 1600}},
}

SC = {
    "totals_this": {"clicks": 900, "impressions": 40000, "ctr": 0.0225, "position": 12.4},
    "totals_prev": {"clicks": 800, "impressions": 41000, "ctr": 0.0195, "position": 13.1},
    "gainers": [("push notifications", 50, 30, 20)],
    "losers": [("web push cost", 10, 25, -15)],
    "top_pages": {"https://example.com/": {"clicks": 300, "impressions": 9000,
                                           "ctr": 0.033, "position": 4.2}},
}


def test_last_complete_week_is_mon_sun():
    mon, sun = last_complete_week(date(2026, 8, 15))  # a Saturday
    assert mon == date(2026, 8, 3) and sun == date(2026, 8, 9)
    assert mon.weekday() == 0 and sun.weekday() == 6


def test_windows_are_contiguous():
    w = windows(date(2026, 8, 15))
    assert w["this"] == ("2026-08-03", "2026-08-09")
    assert w["prev"] == ("2026-07-27", "2026-08-02")
    assert w["four_weeks"] == ("2026-07-06", "2026-08-02")


def test_pct_change():
    assert pct_change(110, 100) == 10
    assert pct_change(90, 100) == -10
    assert pct_change(5, 0) is None


def test_fmt_delta():
    assert fmt_delta(110, 100).startswith("▲")
    assert fmt_delta(90, 100).startswith("▼")
    assert fmt_delta(5, 0) == "new"
    assert fmt_delta(0, 0) == "—"


def test_movers_join_and_noise_floor():
    this_w = {"a": {"clicks": 50}, "b": {"clicks": 1}, "new q": {"clicks": 10}}
    last_w = {"a": {"clicks": 30}, "b": {"clicks": 2}, "gone q": {"clicks": 20}}
    gainers, losers = movers(this_w, last_w, top_n=5, min_clicks=3)
    g_keys = [g[0] for g in gainers]
    l_keys = [l[0] for l in losers]
    assert "a" in g_keys and "new q" in g_keys
    assert "gone q" in l_keys
    assert "b" not in g_keys + l_keys  # below noise floor


def test_markdown_has_all_sections():
    md = compose_markdown(CFG, GA, SC, "TLDR SENTENCE")
    for expected in ("# Weekly Growth Report — Example.com", "TLDR SENTENCE",
                     "## Traffic (GA4)", "### By channel", "## Key events",
                     "## Organic search", "Winning queries", "Losing queries",
                     "Top pages", "sign_up", "5,200", "▲ 8.3%"):
        assert expected in md, f"missing: {expected}"


def test_markdown_without_gsc():
    md = compose_markdown(CFG, GA, None, "T")
    assert "Organic search" not in md and "## Traffic (GA4)" in md


def test_summary_is_short_and_complete():
    s = compose_summary(CFG, GA, SC, "T")
    assert "Example.com" in s and "sign_up" in s and "Search clicks" in s
    assert len(s.splitlines()) < 12


def test_rule_based_tldr():
    t = rule_based_tldr(GA, SC)
    assert "Sessions" in t and "sign_up" in t and "Search clicks" in t


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ✓ {name}")
            except AssertionError as e:
                print(f"  ✗ {name}: {e}")
                failed += 1
    sys.exit(1 if failed else 0)
