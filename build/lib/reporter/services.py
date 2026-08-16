"""App-scoped growthkit service singletons."""
from growthkit.google.auth import (GoogleAuth, READONLY_ANALYTICS,
                                   READONLY_WEBMASTERS)
from growthkit.google.ga4 import GA4
from growthkit.google.gsc import GSC

AUTH = GoogleAuth("growth-reporter", [READONLY_ANALYTICS, READONLY_WEBMASTERS])
GA = GA4(AUTH)
SC = GSC(AUTH)
