"""Response headers that complement Django's deployment security checks."""

from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse


class SecurityHeadersMiddleware:
    """Add safe defaults without overwriting an explicitly set response header."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        headers: dict[str, str] = {
            "Content-Security-Policy": settings.CONTENT_SECURITY_POLICY,
            "Permissions-Policy": settings.PERMISSIONS_POLICY,
        }
        for name, value in headers.items():
            if name not in response:
                response[name] = value
        return response


class RequestRateLimitMiddleware:
    """Apply small cache-backed limits to authentication and expensive reads."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        rule = next(
            (
                value
                for path, value in settings.RATE_LIMIT_RULES.items()
                if request.path.startswith(path)
            ),
            None,
        )
        if rule is not None:
            maximum, window_seconds = rule
            address = request.META.get("REMOTE_ADDR", "unknown")
            key = f"simple-crm:rate:{request.path}:{address}"
            if not cache.add(key, 1, timeout=window_seconds):
                try:
                    count = cache.incr(key)
                except ValueError:
                    cache.set(key, 1, timeout=window_seconds)
                    count = 1
                if count > maximum:
                    response = HttpResponse(
                        "Demasiadas solicitudes. Espere un momento y vuelva a intentar.",
                        status=429,
                        content_type="text/plain; charset=utf-8",
                    )
                    response["Retry-After"] = str(window_seconds)
                    return response
        return self.get_response(request)
