from django.conf import settings


def test_identity_uses_argon2_first_and_explicit_oidc_fallback_flag() -> None:
    from simple_crm.config.settings import base

    assert base.PASSWORD_HASHERS[0].endswith("Argon2PasswordHasher")
    assert settings.LOCAL_AUTH_FALLBACK_ENABLED is False
    assert base.OIDC_ISSUER_URL == ""
    assert base.OIDC_CLIENT_SECRET == ""
