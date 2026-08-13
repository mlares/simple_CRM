"""Request-time session invalidation for disabled identities."""

from __future__ import annotations

from collections.abc import Callable

from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse

from .policy import identity_is_enabled


class IdentitySessionMiddleware:
    """Flush an existing session as soon as offboarding is observed."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.user.is_authenticated and not identity_is_enabled(request.user):
            logout(request)
        return self.get_response(request)
