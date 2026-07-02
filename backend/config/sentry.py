"""
Sentry SDK initialisation — call early_init() at the top of settings.py
before any other import that could raise an exception.

Required env var:  SENTRY_DSN
Optional env vars: DJANGO_ENV  (default: production)
                   APP_VERSION (default: unset)
                   SENTRY_TRACES_SAMPLE_RATE (default: 0.05)
                   SENTRY_PROFILES_SAMPLE_RATE (default: 0.05)
"""
import os

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging


def early_init() -> None:
    dsn = os.environ.get("SENTRY_DSN", "")
    if not dsn:
        return  # skip silently in local/test environments

    sentry_sdk.init(
        dsn=dsn,
        environment=os.environ.get("DJANGO_ENV", "production"),
        release=os.environ.get("APP_VERSION"),
        integrations=[
            DjangoIntegration(
                transaction_style="url",
                middleware_spans=True,
                signals_spans=False,
                cache_spans=True,
            ),
            LoggingIntegration(
                level=logging.WARNING,       # capture WARNING+ as breadcrumbs
                event_level=logging.ERROR,   # send ERROR+ as Sentry events
            ),
        ],
        # Sample 5% of transactions for performance monitoring
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.05")),
        # Profile the same fraction of sampled transactions
        profiles_sample_rate=float(os.environ.get("SENTRY_PROFILES_SAMPLE_RATE", "0.05")),
        # Do not attach PII (IP addresses, user emails) by default
        send_default_pii=False,
        # Avoid sending session data to reduce event volume
        auto_session_tracking=False,
        # Suppress noisy 4xx exceptions from reaching Sentry
        ignore_errors=[
            "django.http.response.Http404",
            "django.core.exceptions.PermissionDenied",
        ],
    )
