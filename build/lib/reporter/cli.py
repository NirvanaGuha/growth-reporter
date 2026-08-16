"""growth-reporter CLI: init | doctor | run | test-alert"""
import argparse
import os
import sys
from pathlib import Path

import yaml

from growthkit import channels as kit_channels
from growthkit import llm as kit_llm
from growthkit.menus import pick_many as _pick_many


def cmd_init(args):
    """Sign in with Google, pick property + GSC site + events from menus."""
    from .services import AUTH, get_ga, get_sc

    print("growth-reporter init — sign in, pick your property, done.\n")

    print("How do you want to connect to Google?")
    print("  1. Sign in with Google           (tokens stay on this machine)")
    print("  2. Connect via Composio          (no Google Cloud setup at all —")
    print("     free composio.dev account; tokens held by Composio)")
    choice = input("Choice [1]: ").strip() or "1"
    backend = "composio" if choice == "2" else "native"

    if backend == "composio":
        import os
        from growthkit.google.composio_backend import (GA_TOOLKIT, GSC_TOOLKIT,
                                                       ComposioClient)
        if not os.environ.get("COMPOSIO_API_KEY"):
            print("\n1. Create a free account at https://app.composio.dev")
            print("2. Settings → API keys → create one")
            key = input("Paste your Composio API key: ").strip()
            if not key:
                print("✗ No key — aborting.")
                return 1
            os.environ["COMPOSIO_API_KEY"] = key
            print("   (add `export COMPOSIO_API_KEY=...` to your ~/.zshrc to persist it)")
        client = ComposioClient()
        ok, why = client.available()
        if not ok:
            print(f"✗ {why}")
            return 1
        for toolkit, label in ((GA_TOOLKIT, "Google Analytics"),
                               (GSC_TOOLKIT, "Search Console")):
            if client.has_connection(toolkit):
                print(f"✓ {label} already connected via Composio.")
                continue
            print(f"\nConnecting {label} through Composio...")
            try:
                client.connect(toolkit)
                print(f"✓ {label} connected.")
            except Exception as e:
                print(f"✗ {label} connection failed: {e}")
                if toolkit == GA_TOOLKIT:
                    return 1
                print("  (continuing without Search Console — GSC section will be skipped)")
    else:
        src = AUTH.credential_source()
        if src != "none":
            print(f"✓ Already authenticated via {src}.")
            if input("  Sign in with a different Google account? [y/N] ").strip().lower() == "y":
                AUTH.oauth_login()
        else:
            print("A browser window will open — sign in with the Google account that")
            print("has access to your Analytics property and Search Console.")
            input("Press Enter to continue... ")
            try:
                AUTH.oauth_login()
                print(f"✓ Signed in. Token saved to {AUTH.token_path}")
            except RuntimeError as e:
                print(f"\n✗ {e}")
                print("\nNo OAuth client available? Rerun init and pick option 2 (Composio).")
                return 1

    _bcfg = {"google_backend": backend,
             "composio": {"user_id": "default", "api_key_env": "COMPOSIO_API_KEY"}}
    GA, SC = get_ga(_bcfg), get_sc(_bcfg)

    print("\nFetching your GA4 properties...")
    props = GA.list_properties()
    if not props:
        print("✗ This Google account has no GA4 properties.")
        return 1
    if len(props) == 1:
        prop = props[0]
        print(f"✓ Using your only property: {prop['name']} ({prop['id']})")
    else:
        for i, p in enumerate(props, 1):
            print(f"  {i:>2}. {p['name']:<40} (property {p['id']}, account: {p['account']})")
        n = input(f"Which property? [1-{len(props)}] ").strip()
        prop = props[int(n) - 1 if n.isdigit() and 1 <= int(n) <= len(props) else 0]

    print("\nFetching your Search Console sites...")
    gsc_site = ""
    try:
        sites = SC.list_sites()
        if sites:
            for i, s in enumerate(sites, 1):
                print(f"  {i:>2}. {s}")
            n = input(f"Which site for the search section? [1-{len(sites)}, blank = skip GSC] ").strip()
            if n.isdigit() and 1 <= int(n) <= len(sites):
                gsc_site = sites[int(n) - 1]
        else:
            print("  (no Search Console sites on this account — skipping the search section)")
    except Exception as e:
        print(f"  (couldn't list Search Console sites: {e} — skipping)")

    print(f"\nTraffic on {prop['name']} in the last 28 days came from these hostnames:")
    hosts = GA.top(prop["id"], "hostName", "sessions", limit=10)
    picked_hosts = _pick_many(hosts, "sessions",
                              "Count only these hostnames (e.g. 1,2 · 'all' · blank = no filter): ")

    print("\nMost frequent events in the last 28 days:")
    events = GA.top(prop["id"], "eventName", "eventCount", limit=20)
    picked_events = _pick_many(events, "times",
                               "Include which events in the report? (e.g. 3,5 · blank = none): ")

    cfg = {
        "property_id": prop["id"],
        "google_backend": backend,
        "site_name": prop["name"],
        "gsc_site": gsc_site,
        "events": picked_events,
    }
    if picked_hosts:
        cfg["dimension_filters"] = [{"dimension": "hostName", "values": picked_hosts}]

    out = Path("reporter.yaml")
    out.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    print(f"\n✓ Wrote {out.resolve()}")

    print("\nDelivery (all optional, via env vars):")
    print("  REPORTER_SLACK_WEBHOOK    — Slack incoming-webhook URL")
    print("  REPORTER_TELEGRAM_TOKEN + REPORTER_TELEGRAM_CHAT_ID")
    print("  REPORTER_WEBHOOK_URL      — any endpoint, receives JSON")
    print("  LLM_API_KEY + narration.base_url/model in reporter.yaml — AI-written TL;DR")
    print("\nNext: `growth-reporter run` — put it on a weekly cron (Tuesdays are good;")
    print("Search Console data needs ~2 days to finalize).")


def cmd_doctor(args):
    from .services import backend_doctor_line, get_ga, get_sc
    ok = True
    try:
        from .config import load_config
        cfg = load_config(args.config)
        print(f"✓ config: {cfg['_config_path']} (property {cfg['property_id']}, "
              f"gsc: {cfg['gsc_site'] or 'off'}, {len(cfg['events'])} events)")
    except Exception as e:
        print(f"✗ config: {e}")
        return 1

    line = backend_doctor_line(cfg)
    print(line)
    if line.startswith("✗"):
        return 1

    try:
        series = get_ga(cfg).daily_series(cfg["property_id"], "3daysAgo", "yesterday",
                                          ["sessions"], filters=cfg["dimension_filters"])
        print(f"✓ GA4 API: live query returned {len(series)} days")
    except Exception as e:
        print(f"✗ GA4 API: {e}")
        ok = False

    if cfg["gsc_site"]:
        try:
            get_sc(cfg).totals(cfg["gsc_site"], "2026-01-01", "2026-01-07")
            print(f"✓ GSC API: reachable for {cfg['gsc_site']}")
        except Exception as e:
            print(f"✗ GSC API: {e}")
            ok = False

    for line in kit_channels.doctor_lines(cfg["channels"]):
        print(line)
    from .narrate import is_configured
    n_ok, n_why = is_configured(cfg)
    print(f"{'✓' if n_ok else '·'} AI TL;DR: {n_why if n_ok else 'off — ' + n_why + ' (rule-based fallback)'}")
    return 0 if ok else 1


def cmd_run(args):
    from .config import load_config
    from .compose import (compose_markdown, compose_summary, gather_ga4,
                          gather_gsc, rule_based_tldr)
    from .deliver import send_summary, write_report
    from .narrate import llm_tldr

    cfg = load_config(args.config)
    print("Gathering GA4 data...", file=sys.stderr)
    ga = gather_ga4(cfg)
    print("Gathering Search Console data...", file=sys.stderr)
    sc = gather_gsc(cfg)

    tldr = llm_tldr(cfg, ga, sc) or rule_based_tldr(ga, sc)
    md = compose_markdown(cfg, ga, sc, tldr)
    summary = compose_summary(cfg, ga, sc, tldr)

    if args.dry:
        print(md)
        return 0

    path = write_report(md, cfg, ga["windows"]["this"][0])
    sent = send_summary(summary, cfg, path)
    print(f"\n[reporter] report written to {path}; summary sent to: {', '.join(sent)}",
          file=sys.stderr)
    return 0


def cmd_test_alert(args):
    from .config import load_config
    from .deliver import send_summary
    cfg = load_config(args.config)
    sent = send_summary("growth-reporter test message — delivery works.", cfg)
    print(f"Sent test message to: {', '.join(sent) or 'nowhere (no channels configured)'}")
    return 0


def main():
    p = argparse.ArgumentParser(
        prog="growth-reporter",
        description="Weekly GA4 + Search Console growth report with an AI-written TL;DR.")
    p.add_argument("--config", "-c", help="path to config YAML", default=None)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="interactive setup wizard (browser sign-in)")
    sub.add_parser("doctor", help="diagnose config, auth, APIs, channels")
    runp = sub.add_parser("run", help="build and deliver this week's report")
    runp.add_argument("--dry", action="store_true",
                      help="print the markdown report, deliver nothing")
    sub.add_parser("test-alert", help="send a test message to configured channels")

    args = p.parse_args()
    cmd = {"init": cmd_init, "doctor": cmd_doctor,
           "run": cmd_run, "test-alert": cmd_test_alert}[args.command]
    sys.exit(cmd(args) or 0)


if __name__ == "__main__":
    main()
