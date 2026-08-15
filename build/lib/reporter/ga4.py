"""Thin GA4 Data API wrapper with config-driven dimension filters."""
from functools import lru_cache

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Filter, FilterExpression, FilterExpressionList,
    Metric, RunReportRequest,
)

from .auth import get_credentials

_MATCH_TYPES = {
    "exact": Filter.StringFilter.MatchType.EXACT,
    "contains": Filter.StringFilter.MatchType.CONTAINS,
    "begins_with": Filter.StringFilter.MatchType.BEGINS_WITH,
    "ends_with": Filter.StringFilter.MatchType.ENDS_WITH,
    "regexp": Filter.StringFilter.MatchType.FULL_REGEXP,
}


@lru_cache(maxsize=1)
def client() -> BetaAnalyticsDataClient:
    return BetaAnalyticsDataClient(credentials=get_credentials())


def _single_filter(spec: dict) -> FilterExpression:
    """One config filter → FilterExpression. Multiple values become an in-list."""
    dim = spec["dimension"]
    values = spec.get("values") or ([spec["value"]] if spec.get("value") else [])
    if len(values) > 1:
        expr = FilterExpression(filter=Filter(
            field_name=dim,
            in_list_filter=Filter.InListFilter(values=[str(v) for v in values]),
        ))
    else:
        mt = _MATCH_TYPES[spec.get("match_type", "exact")]
        expr = FilterExpression(filter=Filter(
            field_name=dim,
            string_filter=Filter.StringFilter(value=str(values[0]), match_type=mt),
        ))
    if spec.get("negate"):
        expr = FilterExpression(not_expression=expr)
    return expr


def build_filter(cfg: dict, extra: FilterExpression | None = None) -> FilterExpression | None:
    """AND together all configured dimension_filters (plus an optional extra)."""
    exprs = [_single_filter(s) for s in cfg.get("dimension_filters", [])]
    if extra is not None:
        exprs.append(extra)
    if not exprs:
        return None
    if len(exprs) == 1:
        return exprs[0]
    return FilterExpression(and_group=FilterExpressionList(expressions=exprs))


def event_filter(event_name: str) -> FilterExpression:
    return FilterExpression(filter=Filter(
        field_name="eventName",
        string_filter=Filter.StringFilter(
            value=event_name, match_type=Filter.StringFilter.MatchType.EXACT),
    ))


def daily_series(cfg: dict, start: str, end: str, metrics: list[str],
                 extra_filter: FilterExpression | None = None) -> dict[str, dict[str, int]]:
    """Return {YYYYMMDD: {metric: value}} for the window, filters applied."""
    req = RunReportRequest(
        property=f"properties/{cfg['property_id']}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="date")],
        metrics=[Metric(name=m) for m in metrics],
        dimension_filter=build_filter(cfg, extra_filter),
        limit=100000,
    )
    resp = client().run_report(req)
    out: dict[str, dict[str, int]] = {}
    for row in resp.rows:
        date = row.dimension_values[0].value
        out[date] = {m: int(float(row.metric_values[i].value)) for i, m in enumerate(metrics)}
    return out
