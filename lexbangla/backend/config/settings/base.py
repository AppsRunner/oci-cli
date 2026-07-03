"""
LexBangla Django base settings — shared across all environments.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = False

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "lexbangla.com").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    "django_redis",
    # LexBangla apps
    "apps.legal_docs",
    "apps.users",
    "apps.search",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.cache.UpdateCacheMiddleware",      # must come BEFORE common
    "django.middleware.common.CommonMiddleware",
    "django.middleware.cache.FetchFromCacheMiddleware",   # must come AFTER common
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

# ============================================================
# Database — OCI PostgreSQL managed service
# ============================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.environ["DB_HOST"],
        "PORT": os.environ.get("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,   # Keep DB connections open for 60 s (reduces overhead)
        "OPTIONS": {
            "connect_timeout": 10,
            "options": "-c statement_timeout=30000",  # 30 s max per query
        },
    }
}

# ============================================================
# Cache — OCI Cache (Redis-compatible) / self-hosted Redis
# ============================================================
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/1")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "TIMEOUT": 300,  # 5-minute default TTL
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "RETRY_ON_TIMEOUT": True,
            "MAX_CONNECTIONS": 20,
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "IGNORE_EXCEPTIONS": True,  # Degrade gracefully if Redis is down
        },
        "KEY_PREFIX": "lexbangla",
        "VERSION": 1,
    }
}

# Session backed by Redis (shares the cache instance)
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 86400 * 7  # 7 days

# Site-wide cache TTL used by FetchFromCacheMiddleware for anonymous views
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = "lexbangla_mw"
CACHE_MIDDLEWARE_ALIAS = "default"

# ============================================================
# Static / media files
# ============================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ============================================================
# Internationalisation — Bangla primary
# ============================================================
LANGUAGE_CODE = "bn"
LANGUAGES = [
    ("bn", "বাংলা"),
    ("en", "English"),
]
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_L10N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
