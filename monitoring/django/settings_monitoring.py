"""
LexBangla monitoring settings — import or include in your main settings.py:

    from .settings_monitoring import *   # or merge selectively

Requirements (add to requirements.txt):
    django-prometheus>=0.3.1
    sentry-sdk[django]>=2.0.0
"""

import os
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration
import logging

# ── Sentry ────────────────────────────────────────────────────────────────────

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
SENTRY_ENVIRONMENT = os.environ.get("SENTRY_ENVIRONMENT", "production")
SENTRY_RELEASE = os.environ.get("SENTRY_RELEASE", "")
SENTRY_TRACES_SAMPLE_RATE = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
SENTRY_PROFILES_SAMPLE_RATE = float(os.environ.get("SENTRY_PROFILES_SAMPLE_RATE", "0.05"))

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        release=SENTRY_RELEASE or None,
        integrations=[
            DjangoIntegration(
                transaction_style="url",
                middleware_spans=True,
                signals_spans=True,
                cache_spans=True,
            ),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
            RedisIntegration(),
        ],
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=SENTRY_PROFILES_SAMPLE_RATE,
        send_default_pii=False,
        attach_stacktrace=True,
        before_send=_sentry_before_send,
    )


def _sentry_before_send(event, hint):
    """Strip sensitive fields before shipping to Sentry."""
    request = event.get("request", {})
    headers = request.get("headers", {})
    for key in ("Authorization", "Cookie", "X-Api-Key"):
        if key in headers:
            headers[key] = "[Filtered]"
    return event


# ── django-prometheus ─────────────────────────────────────────────────────────
# Prepend PrometheusBeforeMiddleware and append PrometheusAfterMiddleware so
# the timing wraps all other middleware.

PROMETHEUS_MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
]

PROMETHEUS_MIDDLEWARE_AFTER = [
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

# Merge these into MIDDLEWARE in your main settings, e.g.:
#   MIDDLEWARE = PROMETHEUS_MIDDLEWARE + MIDDLEWARE + PROMETHEUS_MIDDLEWARE_AFTER

# ── Prometheus export latency buckets (seconds) ───────────────────────────────
# Matches SLO tiers: 50 ms, 100 ms, 250 ms, 500 ms, 1 s, 2 s, 5 s, 10 s
PROMETHEUS_LATENCY_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, float("inf"))

# django-prometheus respects this setting automatically when it is set:
DJANGO_METRICS_EXPORT_PORT = 9090   # unused; /metrics is served via urls.py

# ── URL configuration ─────────────────────────────────────────────────────────
# Add to your root urls.py:
#
#   from django.urls import path, include
#   urlpatterns += [
#       path("", include("django_prometheus.urls")),
#   ]
#
# This exposes GET /metrics — protect it at the network/nginx layer.
