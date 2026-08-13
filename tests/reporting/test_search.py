from datetime import date

import pytest
from django.contrib.auth import get_user_model

from simple_crm.activity.models import InteractionDirection, InteractionResult
from simple_crm.activity.services import quick_contact
from simple_crm.crm.lead_services import create_lead
from simple_crm.crm.models import (
    Campaign,
    ContactKind,
    LeadPartyRole,
    PartyAlias,
)
from simple_crm.crm.services import (
    ContactInput,
    create_organization_party,
    create_person_party,
)
from simple_crm.identity.models import (
    IdentityProfile,
    Role,
    RoleAssignment,
    ScopeGrant,
    ScopeType,
)
from simple_crm.reporting.search import SearchInputError, search


def _actor(username: str, role_code: str = "sales_representative") -> IdentityProfile:
    user = get_user_model().objects.create_user(username=username, password="safe-pass")
    profile = IdentityProfile.objects.get(user=user)
    RoleAssignment.objects.create(
        identity=profile, role=Role.objects.get(code=role_code)
    )
    return profile


def _lead(actor: IdentityProfile, name: str, *, email: str = ""):
    campaign = Campaign.objects.get(code="GENERAL")
    ScopeGrant.objects.get_or_create(
        identity=actor, scope_type=ScopeType.CAMPAIGN, campaign=campaign
    )
    inputs = (ContactInput(kind=ContactKind.EMAIL, raw_value=email),) if email else ()
    party, _ = create_person_party(
        display_name=name,
        given_names=name.split()[0],
        family_names=" ".join(name.split()[1:]),
        contact_inputs=inputs,
    )
    lead, _ = create_lead(
        actor=actor,
        campaign=campaign,
        owner=actor,
        parties=((party, LeadPartyRole.PRIMARY_CONTACT),),
    )
    return party, lead


@pytest.mark.django_db
def test_search_finds_exact_normalized_fuzzy_alias_and_authorized_note() -> None:
    actor = _actor("search-owner")
    party, lead = _lead(actor, "Ana Pérez", email="ventas@example.com")
    phone_party, phone_lead = _lead(
        actor, "Hospital Madre", email="hospital@example.com"
    )
    phone = ContactInput(kind=ContactKind.PHONE, raw_value="+54 9 351 555 1234")
    phone_party, _ = create_person_party(
        display_name="Teléfono Hospital",
        given_names="Teléfono",
        family_names="Hospital",
        contact_inputs=(phone,),
    )
    create_lead(
        actor=actor,
        campaign=Campaign.objects.get(code="GENERAL"),
        owner=actor,
        parties=((phone_party, LeadPartyRole.PRIMARY_CONTACT),),
    )
    PartyAlias.objects.create(
        party=phone_party,
        alias_value="Hospital Madre (fuente)",
        alias_type="SOURCE_NAME",
    )
    quick_contact(
        actor=actor,
        lead=lead,
        occurrence_date=date.today(),
        direction=InteractionDirection.OUTBOUND,
        channel_code="EMAIL",
        outcome_code="SEGUIMIENTO",
        result=InteractionResult.COMPLETED,
        note="Presupuesto urgente para la próxima reunión.",
    )

    email_page = search(actor=actor, query="VENTAS@EXAMPLE.COM")
    assert any(
        result.object_id == party.pk
        and result.match_reason == "Correo o teléfono exacto"
        for result in email_page.results
    )

    accent_page = search(actor=actor, query="Ana Perez")
    assert any(result.object_id == party.pk for result in accent_page.results)

    phone_page = search(actor=actor, query="+54 9 351 555 1234")
    assert any(result.object_id == phone_party.pk for result in phone_page.results)

    alias_page = search(actor=actor, query="Hospital Madra")
    assert any(
        result.object_id == phone_party.pk and "similar" in result.match_reason
        for result in alias_page.results
    )

    note_page = search(actor=actor, query="presupuesto")
    assert any(
        result.result_type == "activity" and result.object_id
        for result in note_page.results
    )
    assert all(result.url.startswith("/leads/") for result in note_page.results)
    assert phone_lead.pk != lead.pk


@pytest.mark.django_db
def test_search_applies_scope_before_counts_and_snippets() -> None:
    actor = _actor("search-scoped")
    visible_party, _ = _lead(actor, "Cuenta visible")
    outsider = _actor("search-outsider")
    hidden_campaign = Campaign.objects.create(code="HIDDEN", label="Campaña oculta")
    ScopeGrant.objects.create(
        identity=outsider, scope_type=ScopeType.CAMPAIGN, campaign=hidden_campaign
    )
    hidden_party, _ = create_organization_party(display_name="Cuenta secreta")
    hidden_lead, _ = create_lead(
        actor=outsider,
        campaign=hidden_campaign,
        owner=outsider,
        parties=((hidden_party, LeadPartyRole.ACCOUNT),),
    )
    quick_contact(
        actor=outsider,
        lead=hidden_lead,
        occurrence_date=date.today(),
        direction=InteractionDirection.OUTBOUND,
        channel_code="EMAIL",
        outcome_code="SEGUIMIENTO",
        result=InteractionResult.COMPLETED,
        note="Secreto no visible para el otro equipo.",
    )

    page = search(actor=actor, query="secreta")
    assert page.total == 0
    assert page.results == ()
    visible = search(actor=actor, query="visible")
    assert any(result.object_id == visible_party.pk for result in visible.results)


@pytest.mark.django_db
def test_search_rejects_unbounded_input_and_paginates_deterministically() -> None:
    actor = _actor("search-bounds")
    _lead(actor, "Primera cuenta")
    _lead(actor, "Segunda cuenta")

    with pytest.raises(SearchInputError):
        search(actor=actor, query="x" * 121)
    with pytest.raises(SearchInputError):
        search(actor=actor, query="***")
    with pytest.raises(SearchInputError):
        search(actor=actor, query="cuenta", cursor="not-a-cursor")

    first = search(actor=actor, query="cuenta", page_size=1)
    assert first.total >= 2
    assert first.next_cursor == 1
    second = search(actor=actor, query="cuenta", cursor=first.next_cursor, page_size=1)
    assert second.results
    assert second.results[0].object_id != first.results[0].object_id
