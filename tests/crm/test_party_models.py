from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from simple_crm.crm.models import (
    Address,
    ContactKind,
    ContactPoint,
    ContactQuality,
    Country,
    Organization,
    OrganizationPerson,
    Party,
    PartyConcurrencyError,
    PartyContactPoint,
    PartyDeletionNotAllowed,
    PartyType,
    Person,
    Province,
)
from simple_crm.crm.services import (
    ContactInput,
    create_organization_party,
    create_person_party,
    preview_party_creation,
)


@pytest.mark.django_db
def test_party_constraint_requires_exactly_one_subtype() -> None:
    person = Person.objects.create(given_names="Ana", family_names="Pérez")
    organization = Organization.objects.create(legal_name="DigPatho")

    Party.objects.create(
        party_type=PartyType.PERSON,
        display_name="Ana Pérez",
        canonical_name="ana perez",
        person=person,
    )
    with transaction.atomic(), pytest.raises(IntegrityError):
        Party.objects.create(
            party_type=PartyType.PERSON,
            display_name="Sin subtipo",
            canonical_name="sin subtipo",
        )
    with transaction.atomic(), pytest.raises(IntegrityError):
        Party.objects.create(
            party_type=PartyType.PERSON,
            display_name="Dos subtipos",
            canonical_name="dos subtipos",
            person=Person.objects.create(given_names="Otra"),
            organization=organization,
        )


@pytest.mark.django_db
def test_relationships_validate_party_types_and_effective_dates() -> None:
    person, _ = create_person_party(
        display_name="Ana Pérez", given_names="Ana", family_names="Pérez"
    )
    organization, _ = create_organization_party(
        display_name="DigPatho", legal_name="DigPatho SA"
    )
    relationship = OrganizationPerson(
        organization=organization,
        person=person,
        relationship_type="RESPONSIBLE",
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 12, 31),
    )
    relationship.full_clean()
    relationship.save()

    with pytest.raises(ValidationError, match="organización"):
        OrganizationPerson(
            organization=person,
            person=person,
            relationship_type="INVALID",
        ).full_clean()


@pytest.mark.django_db
def test_contact_normalization_preserves_raw_value_and_quality_state() -> None:
    email = ContactPoint.objects.create(
        kind=ContactKind.EMAIL,
        raw_value="  VENTAS@EXAMPLE.COM ",
        provenance={"sheet": "Bases de datos", "row": 12},
    )
    phone = ContactPoint.objects.create(
        kind=ContactKind.PHONE,
        raw_value="+54 9 351 555 1234",
    )
    invalid = ContactPoint.objects.create(kind=ContactKind.PHONE, raw_value="123")

    assert email.raw_value == "  VENTAS@EXAMPLE.COM "
    assert email.normalized_value == "ventas@example.com"
    assert email.quality_state == ContactQuality.VALID
    assert phone.normalized_value == "+5493515551234"
    assert phone.quality_state == ContactQuality.VALID
    assert invalid.raw_value == "123"
    assert invalid.normalized_value is None
    assert invalid.quality_state == ContactQuality.INVALID


@pytest.mark.django_db
def test_suppression_survives_edits_and_removes_outreach_selection() -> None:
    point = ContactPoint.objects.create(
        kind=ContactKind.EMAIL, raw_value="contacto@example.com"
    )
    point.suppress("No contactar por solicitud explícita")
    point.raw_value = "nuevo@example.com"
    point.save()
    point.refresh_from_db()

    assert point.is_suppressed is True
    assert point.normalized_value == "nuevo@example.com"
    assert not ContactPoint.selectable_for_outreach().filter(pk=point.pk).exists()
    point.is_suppressed = False
    with pytest.raises(ValidationError, match="suprimido"):
        point.save()


@pytest.mark.django_db
def test_archiving_preserves_relationships_and_stale_edits_are_rejected() -> None:
    party, _ = create_organization_party(
        display_name="Organización histórica", legal_name="Histórica SA"
    )
    point = ContactPoint.objects.create(
        kind=ContactKind.EMAIL, raw_value="historia@example.com"
    )
    PartyContactPoint.objects.create(party=party, contact_point=point)
    stale = Party.objects.get(pk=party.pk)
    party.display_name = "Nombre actualizado"
    party.save()

    stale.display_name = "Sobrescritura incorrecta"
    with pytest.raises(PartyConcurrencyError, match="cambió"):
        stale.save()

    party.archive(expected_version=party.version)
    assert not Party.objects.active().filter(pk=party.pk).exists()
    assert PartyContactPoint.objects.filter(party=party).exists()
    with pytest.raises(PartyDeletionNotAllowed):
        party.delete()


@pytest.mark.django_db
def test_creation_preview_warns_on_exact_contact_and_plausible_name_without_merging() -> (
    None
):
    existing, _ = create_organization_party(
        display_name="Hospital Córdoba",
        legal_name="Hospital Córdoba",
        contact_inputs=[
            ContactInput(kind=ContactKind.EMAIL, raw_value="info@hospital.test")
        ],
    )
    warnings = preview_party_creation(
        "Hospital Cordoba",
        [ContactInput(kind=ContactKind.EMAIL, raw_value="INFO@HOSPITAL.TEST")],
    )
    warning_types = {warning.warning_type for warning in warnings}

    assert "EXACT_CONTACT" in warning_types
    assert "POSSIBLE_NAME_MATCH" in warning_types
    created, creation_warnings = create_organization_party(
        display_name="Hospital Cordoba",
        legal_name="Hospital Cordoba",
        contact_inputs=[
            ContactInput(kind=ContactKind.EMAIL, raw_value="INFO@HOSPITAL.TEST")
        ],
    )
    assert created.pk != existing.pk
    assert creation_warnings
    assert Party.objects.count() == 2


@pytest.mark.django_db
def test_shared_organizational_contact_point_is_not_a_person_identifier() -> None:
    organization, _ = create_organization_party(display_name="Clínica Norte")
    person, _ = create_person_party(display_name="Secretaría", given_names="Secretaría")
    point = ContactPoint.objects.create(
        kind=ContactKind.PHONE, raw_value="+54 9 351 555 1234"
    )
    PartyContactPoint.objects.create(
        party=organization, contact_point=point, purpose="Central institucional"
    )
    PartyContactPoint.objects.create(
        party=person, contact_point=point, purpose="Secretaría compartida"
    )

    assert point.party_links.count() == 2


@pytest.mark.django_db
def test_address_rejects_mismatched_geography_parent() -> None:
    party, _ = create_organization_party(display_name="Geografía SA")
    country = Country.objects.get(code="AR")
    province = Province.objects.first()
    assert province is not None
    other_country = Country.objects.create(code="UY", label="Uruguay")
    address = Address(
        party=party, country=other_country, province=province, address_line="Centro"
    )
    with pytest.raises(ValidationError, match="país"):
        address.full_clean()
    assert country.pk != other_country.pk
