# Django Metrics Integration (django-prometheus)

Add the following to the **backend** application to expose Prometheus metrics at `/metrics/`.

## 1. Install package

```
pip install django-prometheus sentry-sdk
```

Add to `requirements.txt`:
```
django-prometheus==2.3.1
sentry-sdk[django]==2.x
```

## 2. settings/production.py

```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

INSTALLED_APPS = [
    "django_prometheus",   # must be FIRST
    # ... existing apps ...
    "django_prometheus",   # must also be LAST (wraps database)
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",  # first
    # ... existing middleware ...
    "django_prometheus.middleware.PrometheusAfterMiddleware",   # last
]

DATABASES = {
    "default": {
        "ENGINE": "django_prometheus.db.backends.postgresql",  # replaces django.db.backends.postgresql
        # ... rest of DB config ...
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_prometheus.cache.backends.redis.RedisCache",
        # ... rest of cache config ...
    }
}

# Sentry
sentry_sdk.init(
    dsn=env("SENTRY_DSN", default=""),
    integrations=[DjangoIntegration(), CeleryIntegration(), RedisIntegration()],
    traces_sample_rate=0.1,       # 10% of transactions
    profiles_sample_rate=0.05,    # 5% profiling
    send_default_pii=False,
    environment="production",
)
```

## 3. urls.py (root)

```python
from django.urls import path, include

urlpatterns = [
    # ... existing urls ...
    path("", include("django_prometheus.urls")),   # exposes /metrics/
]
```

## 4. Verify

After deploying, from inside the Docker network:
```bash
curl http://backend:8000/metrics/ | grep django_http_requests
```

The nginx config already restricts `/metrics/` to the Docker bridge CIDR.
