# Paste this into your Django settings.py (or settings/production.py).
# Writes structured logs that Promtail's multiline + regex pipeline can parse.

import os
from pathlib import Path

DJANGO_LOG_DIR = Path(os.getenv("DJANGO_LOG_DIR", "/var/log/django"))
DJANGO_LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)-8s %(name)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
    },
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
        "require_debug_true": {"()": "django.utils.log.RequireDebugTrue"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "filters": ["require_debug_true"],
        },
        "app_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": DJANGO_LOG_DIR / "app.log",
            "when": "midnight",
            "backupCount": 14,
            "formatter": "standard",
            "encoding": "utf-8",
        },
        "error_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": DJANGO_LOG_DIR / "error.log",
            "when": "midnight",
            "backupCount": 30,
            "level": "ERROR",
            "formatter": "standard",
            "encoding": "utf-8",
        },
        "request_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": DJANGO_LOG_DIR / "requests.log",
            "when": "midnight",
            "backupCount": 7,
            "formatter": "standard",
            "encoding": "utf-8",
        },
        "security_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": DJANGO_LOG_DIR / "security.log",
            "when": "midnight",
            "backupCount": 90,
            "formatter": "standard",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "app_file", "error_file"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "django.request": {
            "handlers": ["request_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["security_file", "error_file"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": os.getenv("DB_LOG_LEVEL", "WARNING"),
            "propagate": False,
        },
        "lexbangla": {
            "handlers": ["console", "app_file", "error_file"],
            "level": os.getenv("APP_LOG_LEVEL", "DEBUG"),
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "app_file"],
        "level": "WARNING",
    },
}
