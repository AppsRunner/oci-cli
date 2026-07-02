"""
Monitoring additions — merge these into your Django settings.py / base.py.

  1. Copy the INSTALLED_APPS additions below into your INSTALLED_APPS list.
  2. Copy the MIDDLEWARE additions (order matters — see comments).
  3. Add the urls.py snippet to your root URLconf.
  4. Call sentry.early_init() at the very top of your settings file.

This file is NOT imported directly by Django; it documents the integration
surface so each piece can be added to the existing settings files.
"""

# ── Step 1: Add to INSTALLED_APPS ─────────────────────────────────────────────
INSTALLED_APPS_TO_ADD = [
    "django_prometheus",  # must be first in the list for accurate middleware timing
]

# ── Step 2: Wrap MIDDLEWARE with django-prometheus ─────────────────────────────
# django-prometheus requires its middleware to be the FIRST and LAST items so it
# can measure end-to-end latency across all other middleware.
#
# MIDDLEWARE = [
#     "django_prometheus.middleware.PrometheusBeforeMiddleware",  # <-- FIRST
#     ...your existing middleware...
#     "django_prometheus.middleware.PrometheusAfterMiddleware",   # <-- LAST
# ]

MIDDLEWARE_FIRST = "django_prometheus.middleware.PrometheusBeforeMiddleware"
MIDDLEWARE_LAST = "django_prometheus.middleware.PrometheusAfterMiddleware"

# ── Step 3: Database instrumentation ──────────────────────────────────────────
# Replace the default ENGINE with the django-prometheus wrapper:
#
# DATABASES = {
#     "default": {
#         "ENGINE": "django_prometheus.db.backends.postgresql",  # was: django.db.backends.postgresql
#         "NAME": ...,
#     }
# }
#
# Cache instrumentation (optional):
# CACHES = {
#     "default": {
#         "BACKEND": "django_prometheus.cache.backends.redis.RedisCache",
#         ...
#     }
# }

# ── Step 4: Add to root urls.py ───────────────────────────────────────────────
# from django.urls import path, include
#
# urlpatterns = [
#     path("", include("django_prometheus.urls")),  # exposes /metrics
#     ...
# ]

# ── Step 5: Call Sentry init at top of settings.py ────────────────────────────
# from config import sentry
# sentry.early_init()

# ── Full example of what settings.py / base.py should look like ───────────────
EXAMPLE_SETTINGS_SNIPPET = """
# --- top of settings.py ---
from config import sentry
sentry.early_init()

INSTALLED_APPS = [
    "django_prometheus",       # <-- first
    "django.contrib.admin",
    "django.contrib.auth",
    # ... rest of your apps
    "rest_framework",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",  # <-- first
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageContextProcessor",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",   # <-- last
]

DATABASES = {
    "default": {
        "ENGINE": "django_prometheus.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="lexbangla"),
        "USER": env("POSTGRES_USER", default="lexbangla"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("DB_HOST", default="postgres"),
        "PORT": env("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
    }
}
"""
