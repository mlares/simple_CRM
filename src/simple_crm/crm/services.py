"""Party creation previews and lifecycle services."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable, cast

from django.db import transaction

from .models import (
    ContactPoint,
    Organization,
    Party,
    PartyContactPoint,
    PartyLifecycle,
    PartyType,
    Person,
)
from .normalization import comparison_key, normalize_contact_value


@dataclass(frozen=True)
class ContactInput:
    kind: str
    raw_value: str
    platform: str = ""
    purpose: str = ""
    provenance: dict[str, object] | None = None


@dataclass(frozen=True)
class PartyMatchWarning:
    warning_type: str
    message: str
    party_id: int
    matched_value: str


def preview_party_creation(
    display_name: str, contact_inputs: Iterable[ContactInput] = ()
) -> list[PartyMatchWarning]:
    """Return duplicate candidates without merging or blocking creation."""

    warnings: list[PartyMatchWarning] = []
    seen: set[tuple[str, int]] = set()
    for contact in contact_inputs:
        normalized, quality_state = normalize_contact_value(
            contact.kind, contact.raw_value
        )
        if not normalized or quality_state != "VALID":
            continue
        matches = ContactPoint.objects.filter(
            kind=contact.kind,
            normalized_value=normalized,
            party_links__party__lifecycle=PartyLifecycle.ACTIVE,
        ).distinct()
        for point in matches:
            for party_id in point.party_links.values_list("party_id", flat=True):
                key = ("EXACT_CONTACT", party_id)
                if key not in seen:
                    warnings.append(
                        PartyMatchWarning(
                            warning_type=key[0],
                            message="El valor de contacto ya está asociado a otra parte.",
                            party_id=party_id,
                            matched_value=normalized,
                        )
                    )
                    seen.add(key)

    candidate_key = comparison_key(display_name)
    if candidate_key:
        for party in Party.objects.active().only(
            "pk", "display_name", "canonical_name"
        ):
            ratio = SequenceMatcher(None, candidate_key, party.canonical_name).ratio()
            if ratio >= 0.84:
                key = ("POSSIBLE_NAME_MATCH", party.pk)
                if key not in seen:
                    warnings.append(
                        PartyMatchWarning(
                            warning_type=key[0],
                            message="El nombre se parece a una parte existente; revise antes de crear.",
                            party_id=party.pk,
                            matched_value=party.display_name,
                        )
                    )
                    seen.add(key)
    return warnings


def _party(
    *,
    party_type: str,
    display_name: str,
    subtype: Person | Organization,
    contact_inputs: Iterable[ContactInput],
) -> tuple[Party, list[PartyMatchWarning]]:
    warnings = preview_party_creation(display_name, contact_inputs)
    party = Party.objects.create(
        party_type=party_type,
        display_name=display_name.strip(),
        canonical_name=comparison_key(display_name),
        person=cast(Person, subtype) if party_type == PartyType.PERSON else None,
        organization=(
            cast(Organization, subtype)
            if party_type == PartyType.ORGANIZATION
            else None
        ),
    )
    for contact in contact_inputs:
        point = ContactPoint.objects.create(
            kind=contact.kind,
            platform=contact.platform,
            raw_value=contact.raw_value,
            provenance=contact.provenance or {},
        )
        PartyContactPoint.objects.create(
            party=party, contact_point=point, purpose=contact.purpose
        )
    return party, warnings


@transaction.atomic
def create_person_party(
    *,
    display_name: str,
    given_names: str = "",
    family_names: str = "",
    honorific: str = "",
    contact_inputs: Iterable[ContactInput] = (),
) -> tuple[Party, list[PartyMatchWarning]]:
    contacts = tuple(contact_inputs)
    person = Person.objects.create(
        given_names=given_names,
        family_names=family_names,
        honorific=honorific,
    )
    return _party(
        party_type=PartyType.PERSON,
        display_name=display_name,
        subtype=person,
        contact_inputs=contacts,
    )


@transaction.atomic
def create_organization_party(
    *,
    display_name: str,
    legal_name: str = "",
    organization_type: str = "",
    contact_inputs: Iterable[ContactInput] = (),
) -> tuple[Party, list[PartyMatchWarning]]:
    contacts = tuple(contact_inputs)
    organization = Organization.objects.create(
        legal_name=legal_name,
        organization_type=organization_type,
    )
    return _party(
        party_type=PartyType.ORGANIZATION,
        display_name=display_name,
        subtype=organization,
        contact_inputs=contacts,
    )
