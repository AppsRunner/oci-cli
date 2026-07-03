# LexBangla — Chapter 15 Security Checklist

_Last updated: 2026-07-03_

## 1. OWASP ZAP Baseline Findings & Fixes

| ZAP ID | Finding | Severity | Status | Fix |
|--------|---------|----------|--------|-----|
| 10035 | Missing Strict-Transport-Security (HSTS) | Medium | ✅ Fixed | `SECURE_HSTS_SECONDS=31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`, `SECURE_HSTS_PRELOAD=True` in `settings/production.py` |
| 10036 | Server header leaks version info | Low | ✅ Fixed | `SecurityHeadersMiddleware` overrides `Server` header to `"LexBangla"` |
| 10038 | Missing Content-Security-Policy | Medium | ✅ Fixed | `django-csp` delivers a strict `default-src 'self'` policy |
| 10063 | Missing Permissions-Policy | Low | ✅ Fixed | `SecurityHeadersMiddleware` sets `Permissions-Policy` blocking camera, mic, payment, etc. |
| 10020 | X-Frame-Options not set | Medium | ✅ Fixed | `X_FRAME_OPTIONS = "DENY"` + `CSP_FRAME_ANCESTORS = ("'none'",)` |
| 10021 | X-Content-Type-Options not set | Low | ✅ Fixed | `SECURE_CONTENT_TYPE_NOSNIFF = True` + middleware |
| 10017 | Cross-Domain JavaScript Source | Medium | ✅ Fixed | `CSP_SCRIPT_SRC = ("'self'",)` — no external JS |
| 10098 | Cross-Domain Misconfiguration | Low | ✅ Fixed | `SecurityHeadersMiddleware` strips `Access-Control-Allow-Origin` — CORS opt-in per view |
| 10055 | CSP Wildcard Directive | Medium | ✅ Fixed | All CSP directives are explicit; no wildcards |
| 10010 | Cookie without Secure flag | High | ✅ Fixed | `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True` in production |
| 10011 | Cookie without HttpOnly flag | Medium | ✅ Fixed | `SESSION_COOKIE_HTTPONLY=True`, `CSRF_COOKIE_HTTPONLY=True` |
| 10013 | Cookie without SameSite attribute | Low | ✅ Fixed | `SESSION_COOKIE_SAMESITE="Strict"`, `CSRF_COOKIE_SAMESITE="Strict"` |

---

## 2. Brute-Force Protection — Django-axes

| Control | Value | Location |
|---------|-------|----------|
| `AXES_FAILURE_LIMIT` | 5 attempts | `settings/base.py` |
| `AXES_COOLOFF_TIME` | 1 hour | `settings/base.py` |
| `AXES_LOCK_OUT_AT_FAILURE` | True | `settings/base.py` |
| `AXES_RESET_ON_SUCCESS` | True | `settings/base.py` |
| `AXES_LOCKOUT_PARAMETERS` | IP + username | `settings/base.py` |
| Login view | `@axes_dispatch` applied | `apps/accounts/views.py` |
| Auth backend | `AxesStandaloneBackend` first | `settings/base.py` |

- [ ] Confirm `axes_accessattempt` and `axes_accesslog` tables exist after `migrate`
- [ ] Verify lockout triggers after 5 failures on staging
- [ ] Set up an alert in OCI Monitoring when `axes_accessattempt` count spikes

---

## 3. OCI Vault — Secret Rotation

| Secret Name (in Vault) | Mapped env var | Rotation frequency |
|------------------------|----------------|--------------------|
| `lexbangla-django-secret-key` | `DJANGO_SECRET_KEY` | Quarterly |
| `lexbangla-db-password` | `DB_PASSWORD` | Quarterly |

**Rotation workflow** (`scripts/vault_secrets.py`):
1. `python scripts/vault_secrets.py rotate --name <secret-name>` — creates new version in OCI Vault
2. Redeploy container: startup calls `eval "$(python scripts/vault_secrets.py export)"` to inject fresh values
3. Old version is automatically deprecated by OCI Vault after TTL

- [ ] Create an OCI Vault and store initial secret values
- [ ] Set `OCI_VAULT_VAULT_ID` and `OCI_VAULT_COMPARTMENT_ID` in GitHub Actions secrets
- [ ] Schedule quarterly rotation via OCI Events + Function or GitHub Actions `cron`
- [ ] Enable OCI Vault audit trail in OCI Audit service
- [ ] Confirm IAM policy grants least-privilege read access to `lexbangla-secrets-reader` dynamic group

---

## 4. SAST — GitHub Actions

| Tool | Runs on | Rule sets | Output |
|------|---------|-----------|--------|
| **Bandit** | every push to `lexbangla/` | severity≥medium, confidence≥medium | SARIF → GitHub Security tab |
| **Semgrep** | every push to `lexbangla/` | `p/python`, `p/django`, `p/owasp-top-ten`, `p/secrets` | SARIF → GitHub Security tab |
| **Safety** | every push to `lexbangla/` | CVE database | text output + CI fail on vuln |
| **OWASP ZAP** | nightly cron (03:00 UTC) | ZAP baseline + `lexbangla/.zap/rules.tsv` | HTML artifact + GitHub Issues |

- [ ] Add `ZAP_STAGING_URL` as a GitHub Actions variable (repo Settings → Variables)
- [ ] Review SARIF findings in GitHub → Security → Code scanning after first push
- [ ] Tune Bandit exclusions via `.bandit` config if false-positives appear

---

## 5. Django Security Hardening Checklist

### Authentication & Session
- [x] Password validators: min 12 chars, similarity check, common password check, numeric check
- [x] `AXES_FAILURE_LIMIT = 5` with IP + username lockout
- [x] Session cookies: `HTTPONLY`, `SECURE`, `SAMESITE=Strict`
- [x] CSRF cookies: `HTTPONLY`, `SECURE`, `SAMESITE=Strict`
- [x] Login view: `@never_cache` + `@require_http_methods(["GET","POST"])`
- [x] Logout via POST only (CSRF-protected)

### Transport Security
- [x] `SECURE_SSL_REDIRECT = True`
- [x] `SECURE_PROXY_SSL_HEADER` configured for OCI Load Balancer
- [x] HSTS 1 year + subdomains + preload

### Headers
- [x] `X-Frame-Options: DENY`
- [x] `X-Content-Type-Options: nosniff`
- [x] `Referrer-Policy: strict-origin-when-cross-origin`
- [x] `Permissions-Policy` — camera, mic, payment, USB disabled
- [x] `Content-Security-Policy` via django-csp (no inline scripts/styles)
- [x] Server header stripped of version info

### Database
- [x] `DB_SSLMODE = require` — TLS to PostgreSQL enforced
- [x] `CONN_MAX_AGE = 60` — connection pooling

### Static files
- [x] WhiteNoise with `CompressedManifestStaticFilesStorage` — content-hash cache busting

### Secrets management
- [x] No hard-coded secrets — all via `python-decouple` + OCI Vault
- [x] `DJANGO_SECRET_KEY` sourced from OCI Vault at startup
- [x] `DB_PASSWORD` sourced from OCI Vault at startup

### CI/CD
- [x] Bandit SAST on every push
- [x] Semgrep SAST on every push (Django + OWASP rulesets)
- [x] Safety dependency scan on every push
- [x] OWASP ZAP nightly baseline scan against staging

### Still to do before production go-live
- [ ] Enable Django `DEBUG=False` in production (verify via health check endpoint)
- [ ] Run `python manage.py check --deploy` and resolve all warnings
- [ ] Configure OCI WAF in front of Load Balancer with OWASP Core Rule Set
- [ ] Enable OCI Vulnerability Scanning on container images
- [ ] Rotate all secrets after initial provisioning
- [ ] Enable OCI Audit trail and set up CloudGuard policy
- [ ] Run full OWASP ZAP active scan (not just baseline) against staging before go-live
- [ ] Conduct pen-test or third-party security review
- [ ] Add `django-ratelimit` on public-facing API endpoints (future chapter)
