"""Deterministic, lossless normalization for party contact values."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

import phonenumbers
from django.core.exceptions import ValidationError

EMAIL = "EMAIL"
PHONE_KINDS = {"PHONE", "WHATSAPP"}


def comparison_key(value: str) -> str:
    """Normalize comparison text without replacing the source evidence."""

    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return " ".join(without_marks.casefold().split())


def _email(raw_value: str) -> tuple[str | None, str]:
    normalized = raw_value.strip().casefold()
    if not normalized or any(separator in normalized for separator in (",", ";", "\n")):
        return None, "AMBIGUOUS"
    try:
        from django.core.validators import validate_email

        validate_email(normalized)
    except ValidationError:
        return None, "INVALID"
    return normalized, "VALID"


def _phone(raw_value: str, *, region: str = "AR") -> tuple[str | None, str]:
    candidate = raw_value.strip()
    if not candidate:
        return None, "INVALID"
    if re.search(r"(?:/|;|\bor\b|\bo\b)", candidate, flags=re.IGNORECASE):
        return None, "AMBIGUOUS"
    try:
        parsed = phonenumbers.parse(candidate, region)
    except phonenumbers.NumberParseException:
        return None, "INVALID"
    if phonenumbers.is_valid_number(parsed):
        return phonenumbers.format_number(
            parsed, phonenumbers.PhoneNumberFormat.E164
        ), "VALID"
    if phonenumbers.is_possible_number(parsed):
        return None, "AMBIGUOUS"
    return None, "INVALID"


def _website(raw_value: str) -> tuple[str | None, str]:
    candidate = raw_value.strip()
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return candidate, "VALID"
    return None, "INVALID"


def normalize_contact_value(
    kind: str, raw_value: str, *, phone_region: str = "AR"
) -> tuple[str | None, str]:
    """Return normalized value and explicit quality state."""

    if kind == EMAIL:
        return _email(raw_value)
    if kind in PHONE_KINDS:
        return _phone(raw_value, region=phone_region)
    if kind == "WEBSITE":
        return _website(raw_value)
    normalized = raw_value.strip()
    return (normalized or None, "VALID" if normalized else "INVALID")
