"""
Production settings for LexBangla.
Imported by DJANGO_SETTINGS_MODULE=lexbangla.settings.production.
Secrets are pulled from OCI Vault at startup via scripts/vault_secrets.py.
"""
from .base import *  # noqa: F401,F403

# ---------------------------------------------------------------------------
# HTTPS / HSTS — fix ZAP "Strict-Transport-Security" finding
# ---------------------------------------------------------------------------

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31_536_000          # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ---------------------------------------------------------------------------
# OCI Vault — secret names resolved in vault_secrets.py at container startup
# ---------------------------------------------------------------------------

OCI_VAULT_COMPARTMENT_ID = config("OCI_VAULT_COMPARTMENT_ID")   # noqa: F405
OCI_VAULT_VAULT_ID = config("OCI_VAULT_VAULT_ID")               # noqa: F405
OCI_VAULT_SECRET_NAMES = {
    "DJANGO_SECRET_KEY": config("VAULT_SECRET_DJANGO_SECRET_KEY", default="lexbangla-django-secret-key"),  # noqa: F405
    "DB_PASSWORD": config("VAULT_SECRET_DB_PASSWORD", default="lexbangla-db-password"),                   # noqa: F405
}

# ---------------------------------------------------------------------------
# Email (production)
# ---------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.example.com")    # noqa: F405
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)          # noqa: F405
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")          # noqa: F405
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")  # noqa: F405

DEFAULT_FROM_EMAIL = "noreply@lexbangla.com"
SERVER_EMAIL = "errors@lexbangla.com"
