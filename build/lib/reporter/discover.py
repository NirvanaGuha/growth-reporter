"""Post-auth discovery for init menus: GA4 properties, GSC sites, hostnames, events."""
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Metric, OrderBy, RunReportRequest,
)

from . import ga4


def list_properties() -> list[dict]:
    from google.analytics.admin_v1beta import AnalyticsAdminServiceClient
    from .auth import get_credentials

    admin = AnalyticsAdminServiceClient(credentials=get_credentials())
    out = []
    for acct in admin.list_account_summaries():
        for prop in acct.property_summaries:
            out.append({"id": prop.property.split("/")[-1],
                        "name": prop.display_name,
                        "account": acct.display_name})
    return out


def list_gsc_sites() -> list[str]:
    from . import gsc
    return gsc.list_sites()


def _top(property_id: str, dimension: str, metric: str, days: int = 28,
         limit: int = 15) -> list[tuple[str, int]]:
    req = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="yesterday")],
        dimensions=[Dimension(name=dimension)],
        metrics=[Metric(name=metric)],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name=metric), desc=True)],
        limit=limit,
    )
    resp = ga4.client().run_report(req)
    return [(r.dimension_values[0].value, int(float(r.metric_values[0].value)))
            for r in resp.rows]


def top_hostnames(property_id: str, limit: int = 10) -> list[tuple[str, int]]:
    return _top(property_id, "hostName", "sessions", limit=limit)


def top_events(property_id: str, limit: int = 20) -> list[tuple[str, int]]:
    return _top(property_id, "eventName", "eventCount", limit=limit)
