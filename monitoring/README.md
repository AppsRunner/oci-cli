# LexBangla — Monitoring & Observability (Chapter 11)

## Stack

| Component | Image | Port | Purpose |
|-----------|-------|------|---------|
| Prometheus | `prom/prometheus:v2.52.0` | 9090 | Metrics collection & alerting |
| Grafana | `grafana/grafana:10.4.2` | 3000 | Dashboards |
| Alertmanager | `prom/alertmanager:v0.27.0` | 9093 | Alert routing (email + Slack) |
| nginx-exporter | `nginx/nginx-prometheus-exporter:1.1.0` | 9113 | Nginx metrics |
| cAdvisor | `gcr.io/cadvisor/cadvisor:v0.49.1` | 8080 | Container metrics |
| node-exporter | `prom/node-exporter:v1.8.0` | 9100 | Host metrics |

## Quick start

```bash
cd monitoring
cp .env.example .env
# Edit .env with real credentials
docker compose up -d
```

## Django integration

1. Add to `requirements.txt`:
   ```
   django-prometheus==0.3.1
   sentry-sdk[django,redis]==2.4.0
   ```

2. Modify `settings.py`:
   ```python
   from .settings_monitoring import *

   INSTALLED_APPS += ["django_prometheus"]

   MIDDLEWARE = (
       PROMETHEUS_MIDDLEWARE
       + MIDDLEWARE
       + PROMETHEUS_MIDDLEWARE_AFTER
   )
   ```

3. Add to `urls.py`:
   ```python
   urlpatterns += [path("", include("django_prometheus.urls"))]
   ```
   This exposes `GET /metrics` — restrict it at the Nginx layer.

4. Set environment variable:
   ```bash
   SENTRY_DSN=https://<key>@o0.ingest.sentry.io/<project>
   ```

## Nginx integration

Include `nginx/nginx_stub_status.conf` in your Nginx config. It opens port 8080
for the exporter's scrape on `/nginx_status` and denies public access.

## Alert rules

| Alert | Threshold | Channel |
|-------|-----------|---------|
| `HighP95RequestLatency` | p95 > 2 s for 5 min | `#lexbangla-backend-alerts` |
| `CriticalP95RequestLatency` | p95 > 5 s for 2 min | `#lexbangla-alerts-critical` + email |
| `ContainerRestarting` | >2 restarts / 15 min | `#lexbangla-ops-alerts` |
| `ContainerCrashLooping` | >5 restarts / 1 h | `#lexbangla-alerts-critical` + email |
| `HighErrorRate` | 5xx > 5% for 3 min | `#lexbangla-backend-alerts` |
| `CriticalErrorRate` | 5xx > 20% for 1 min | `#lexbangla-alerts-critical` + email |
| `PostgresConnectionsNearLimit` | >85% max_connections | `#lexbangla-backend-alerts` |

## Grafana dashboards

- **Request Latency** (`uid: lexbangla-latency`) — p50/p95/p99 by view, slowest-view table
- **Error Rates** (`uid: lexbangla-errors`) — 5xx/4xx rates, Nginx RPS + connections
- **DB Connections** (`uid: lexbangla-db`) — Django query volume/latency, PG pool usage

All dashboards auto-provision from `grafana/dashboards/` on container start.
