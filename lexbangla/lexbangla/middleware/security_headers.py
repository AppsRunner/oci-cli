"""
Security-headers middleware — addresses OWASP ZAP baseline findings:
  - ZAP-001: Missing Anti-clickjacking Header        → X-Frame-Options
  - ZAP-002: X-Content-Type-Options Header Missing   → X-Content-Type-Options
  - ZAP-003: Server leaks version via Server header  → Server header stripped
  - ZAP-004: Missing Permissions-Policy              → Permissions-Policy
  - ZAP-005: Cross-Domain Misconfiguration           → Access-Control-Allow-Origin
"""


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["X-Frame-Options"] = "DENY"
        response["X-Content-Type-Options"] = "nosniff"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), "
            "gyroscope=(), magnetometer=(), microphone=(), "
            "payment=(), usb=()"
        )
        # Strip server-version leakage (ZAP-003)
        response["Server"] = "LexBangla"
        # Block cross-domain reads (ZAP-005); CORS is opt-in per view if needed
        response.pop("Access-Control-Allow-Origin", None)
        return response
