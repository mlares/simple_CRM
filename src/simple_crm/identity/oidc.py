"""Small OIDC authorization-code client with PKCE and provider MFA boundary."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from .models import IdentityProfile


class OIDCUnavailable(Exception):
    """The configured provider cannot currently complete authentication."""


class OIDCProtocolError(Exception):
    """The provider returned an invalid or incomplete response."""


@dataclass(frozen=True)
class OIDCConfiguration:
    issuer_url: str
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: tuple[str, ...] = ("openid", "profile", "email")

    @classmethod
    def from_settings(cls) -> "OIDCConfiguration":
        values = (
            getattr(settings, "OIDC_ISSUER_URL", ""),
            getattr(settings, "OIDC_CLIENT_ID", ""),
            getattr(settings, "OIDC_CLIENT_SECRET", ""),
            getattr(settings, "OIDC_REDIRECT_URI", ""),
        )
        if not all(values):
            raise OIDCUnavailable("OIDC no está configurado.")
        return cls(*values)

    @property
    def discovery_url(self) -> str:
        return f"{self.issuer_url.rstrip('/')}/.well-known/openid-configuration"


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _json_request(
    url: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url, data=data, headers=headers or {}, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, TimeoutError, ValueError) as error:
        raise OIDCUnavailable from error
    if not isinstance(payload, dict):
        raise OIDCProtocolError("La respuesta OIDC no es un objeto JSON.")
    return payload


def authorization_url(
    configuration: OIDCConfiguration, *, state: str, nonce: str, challenge: str
) -> str:
    """Build an authorization-code request; MFA remains provider-enforced."""

    discovery = _json_request(configuration.discovery_url)
    endpoint = discovery.get("authorization_endpoint")
    if not isinstance(endpoint, str):
        raise OIDCProtocolError("Falta el endpoint de autorización OIDC.")
    query = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": configuration.client_id,
            "redirect_uri": configuration.redirect_uri,
            "scope": " ".join(configuration.scopes),
            "state": state,
            "nonce": nonce,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{endpoint}?{query}"


def exchange_code(
    configuration: OIDCConfiguration, *, code: str, verifier: str
) -> dict[str, Any]:
    discovery = _json_request(configuration.discovery_url)
    token_endpoint = discovery.get("token_endpoint")
    userinfo_endpoint = discovery.get("userinfo_endpoint")
    if not isinstance(token_endpoint, str) or not isinstance(userinfo_endpoint, str):
        raise OIDCProtocolError("Faltan endpoints OIDC requeridos.")
    form = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": configuration.redirect_uri,
            "client_id": configuration.client_id,
            "client_secret": configuration.client_secret,
            "code_verifier": verifier,
        }
    ).encode("ascii")
    token = _json_request(
        token_endpoint,
        method="POST",
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    access_token = token.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise OIDCProtocolError("El proveedor no entregó un token de acceso.")
    return _json_request(
        userinfo_endpoint,
        headers={"Authorization": f"Bearer {access_token}"},
    )


def user_for_claims(claims: dict[str, Any]) -> Any:
    """Link a provider subject to one local identity without trusting email alone."""

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise OIDCProtocolError("El proveedor no entregó un sujeto estable.")
    try:
        profile = IdentityProfile.objects.select_related("user").get(
            oidc_subject=subject
        )
    except IdentityProfile.DoesNotExist:
        user_model = get_user_model()
        username = "oidc_" + hashlib.sha256(subject.encode("utf-8")).hexdigest()[:40]
        user = user_model.objects.create_user(
            username=username,
            email=claims.get("email", "")
            if isinstance(claims.get("email"), str)
            else "",
            first_name=(
                claims.get("given_name", "")
                if isinstance(claims.get("given_name"), str)
                else ""
            ),
            last_name=(
                claims.get("family_name", "")
                if isinstance(claims.get("family_name"), str)
                else ""
            ),
        )
        user.set_unusable_password()
        user.save(update_fields=("password",))
        profile = IdentityProfile.objects.get(user=user)
        profile.oidc_subject = subject
    if not profile.is_enabled:
        raise PermissionDenied("La identidad está deshabilitada.")
    display_name = claims.get("name")
    if isinstance(display_name, str) and display_name.strip():
        profile.display_name = display_name.strip()
    profile.save(update_fields=("oidc_subject", "display_name", "updated_at"))
    return profile.user
