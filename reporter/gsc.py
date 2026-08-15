"""Google Search Console (Search Analytics) wrapper."""
from functools import lru_cache


@lru_cache(maxsize=1)
def client():
    from googleapiclient.discovery import build
    from .auth import get_credentials
    return build("searchconsole", "v1", credentials=get_credentials(),
                 cache_discovery=False)


def list_sites() -> list[str]:
    resp = client().sites().list().execute()
    return sorted(e["siteUrl"] for e in resp.get("siteEntry", [])
                  if e.get("permissionLevel") != "siteUnverifiedUser")


def _page_filter(url_contains: str | None) -> dict:
    """dimensionFilterGroups restricting to pages containing a substring.
    Useful when an sc-domain property counts spammy subdomains you don't own."""
    if not url_contains:
        return {}
    return {"dimensionFilterGroups": [{"filters": [{
        "dimension": "page", "operator": "contains", "expression": url_contains}]}]}


def totals(site: str, start: str, end: str, url_contains: str | None = None) -> dict:
    """Aggregate clicks/impressions/ctr/position for a date window."""
    resp = client().searchanalytics().query(
        siteUrl=site, body={"startDate": start, "endDate": end,
                            **_page_filter(url_contains)}).execute()
    rows = resp.get("rows", [])
    if not rows:
        return {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0}
    r = rows[0]
    return {"clicks": int(r["clicks"]), "impressions": int(r["impressions"]),
            "ctr": r["ctr"], "position": r["position"]}


def by_dimension(site: str, start: str, end: str, dimension: str,
                 limit: int = 250, url_contains: str | None = None) -> dict[str, dict]:
    """{dimension_value: {clicks, impressions, ctr, position}}"""
    resp = client().searchanalytics().query(siteUrl=site, body={
        "startDate": start, "endDate": end,
        "dimensions": [dimension], "rowLimit": limit,
        **_page_filter(url_contains),
    }).execute()
    return {r["keys"][0]: {
        "clicks": int(r["clicks"]), "impressions": int(r["impressions"]),
        "ctr": r["ctr"], "position": r["position"],
    } for r in resp.get("rows", [])}


def movers(this_week: dict[str, dict], last_week: dict[str, dict],
           top_n: int = 5, min_clicks: int = 3) -> tuple[list, list]:
    """Join two weekly by-dimension dicts on key; return (gainers, losers) by click delta.

    min_clicks keeps one-click noise out: a mover must have at least that many
    clicks in one of the two weeks.
    """
    deltas = []
    for key in set(this_week) | set(last_week):
        now = this_week.get(key, {}).get("clicks", 0)
        before = last_week.get(key, {}).get("clicks", 0)
        if max(now, before) < min_clicks:
            continue
        deltas.append((key, now, before, now - before))
    gainers = sorted([d for d in deltas if d[3] > 0], key=lambda d: -d[3])[:top_n]
    losers = sorted([d for d in deltas if d[3] < 0], key=lambda d: d[3])[:top_n]
    return gainers, losers
