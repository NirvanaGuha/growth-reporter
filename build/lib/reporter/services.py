"""App-scoped growthkit services. Google backend (native vs Composio) is
chosen by the config's `google_backend` key via the growthkit factory."""
from growthkit.google.auth import (GoogleAuth, READONLY_ANALYTICS,
                                   READONLY_WEBMASTERS)
from growthkit.google import factory

AUTH = GoogleAuth("growth-reporter", [READONLY_ANALYTICS, READONLY_WEBMASTERS])


def get_ga(cfg: dict):
    return factory.make_ga4(cfg, AUTH)


def get_sc(cfg: dict):
    return factory.make_gsc(cfg, AUTH)


def backend_doctor_line(cfg: dict) -> str:
    return factory.doctor_line(cfg, AUTH)
