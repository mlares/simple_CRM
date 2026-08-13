"""Authentication endpoints with generic failures and Spanish-facing copy."""

from __future__ import annotations

import secrets

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from simple_crm.config.observability import record_event, record_metric

from .oidc import (
    OIDCConfiguration,
    OIDCProtocolError,
    OIDCUnavailable,
    authorization_url,
    exchange_code,
    pkce_pair,
    user_for_claims,
)
from .policy import identity_is_enabled


def _safe_next(request: HttpRequest) -> str:
    candidate = request.POST.get("next") or request.GET.get("next") or "/"
    return (
        candidate
        if url_has_allowed_host_and_scheme(
            candidate,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )
        else "/"
    )


def local_login(request: HttpRequest) -> HttpResponse:
    if not getattr(settings, "LOCAL_AUTH_FALLBACK_ENABLED", False):
        return JsonResponse(
            {"detail": "El acceso local sólo está disponible cuando OIDC no responde."},
            status=404,
        )
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )
        if user is not None and identity_is_enabled(user):
            login(request, user)
            record_metric("auth.login.success")
            record_event("auth.login", component="auth", outcome="success")
            return redirect(_safe_next(request))
        form.add_error(None, "No fue posible iniciar la sesión.")
    return render(
        request,
        "identity/local_login.html",
        {"form": form, "next": _safe_next(request)},
    )


def oidc_start(request: HttpRequest) -> HttpResponse:
    try:
        configuration = OIDCConfiguration.from_settings()
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier, challenge = pkce_pair()
        request.session["oidc_state"] = state
        request.session["oidc_nonce"] = nonce
        request.session["oidc_verifier"] = verifier
        request.session["oidc_next"] = _safe_next(request)
        return redirect(
            authorization_url(
                configuration, state=state, nonce=nonce, challenge=challenge
            )
        )
    except (OIDCUnavailable, OSError):
        return JsonResponse(
            {"detail": "El inicio de sesión no está disponible."}, status=503
        )


def oidc_callback(request: HttpRequest) -> HttpResponse:
    supplied_state = request.GET.get("state", "")
    expected_state = request.session.pop("oidc_state", "")
    verifier = request.session.pop("oidc_verifier", "")
    request.session.pop("oidc_nonce", None)
    next_url = request.session.pop("oidc_next", "/")
    if (
        not supplied_state
        or not expected_state
        or not secrets.compare_digest(supplied_state, expected_state)
    ):
        return JsonResponse(
            {"detail": "La respuesta de autenticación no es válida."}, status=400
        )
    code = request.GET.get("code", "")
    if not code or not verifier:
        return JsonResponse(
            {"detail": "La respuesta de autenticación no es válida."}, status=400
        )
    try:
        claims = exchange_code(
            OIDCConfiguration.from_settings(), code=code, verifier=verifier
        )
        user = user_for_claims(claims)
    except (OIDCProtocolError, OIDCUnavailable, PermissionDenied):
        return JsonResponse(
            {"detail": "No fue posible completar el inicio de sesión."}, status=503
        )
    login(request, user)
    return redirect(
        next_url
        if url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )
        else reverse("platform:home")
    )


def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("platform:home")


@login_required
def me(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"username": request.user.get_username()})
