import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError

from simple_crm.crm.lead_services import create_lead
from simple_crm.crm.models import Campaign, LeadPartyRole
from simple_crm.crm.services import create_organization_party
from simple_crm.identity.models import (
    IdentityProfile,
    Role,
    RoleAssignment,
    ScopeGrant,
    ScopeType,
)
from simple_crm.reporting.models import SavedViewVisibility
from simple_crm.reporting.services import (
    archive_saved_view,
    copy_saved_view,
    create_saved_view,
    execute_definition,
    execute_saved_view,
    rename_saved_view,
)


def _actor(username: str, role_code: str = "sales_representative") -> IdentityProfile:
    user = get_user_model().objects.create_user(username=username, password="safe-pass")
    profile = IdentityProfile.objects.get(user=user)
    RoleAssignment.objects.create(
        identity=profile, role=Role.objects.get(code=role_code)
    )
    return profile


def _lead(actor: IdentityProfile, name: str):
    campaign = Campaign.objects.get(code="GENERAL")
    ScopeGrant.objects.get_or_create(
        identity=actor, scope_type=ScopeType.CAMPAIGN, campaign=campaign
    )
    party, _ = create_organization_party(display_name=name)
    return create_lead(
        actor=actor,
        campaign=campaign,
        owner=actor,
        parties=((party, LeadPartyRole.ACCOUNT),),
    )[0]


@pytest.mark.django_db
def test_typed_filters_are_allow_listed_and_scope_is_applied_before_count() -> None:
    actor = _actor("segment-owner")
    visible = _lead(actor, "Cuenta visible")
    outsider = _actor("segment-outsider")
    hidden_campaign = Campaign.objects.create(code="SEG-HIDDEN", label="Oculta")
    ScopeGrant.objects.create(
        identity=outsider, scope_type=ScopeType.CAMPAIGN, campaign=hidden_campaign
    )
    hidden_party, _ = create_organization_party(display_name="Cuenta fuera de alcance")
    create_lead(
        actor=outsider,
        campaign=hidden_campaign,
        owner=outsider,
        parties=((hidden_party, LeadPartyRole.ACCOUNT),),
    )

    page = execute_definition(
        actor=actor,
        definition={
            "and": [{"field": "stage", "operator": "eq", "value": "NUEVO"}],
            "or": [],
            "sort": "lead_number",
        },
    )
    assert page.total == 1
    assert page.results[0].pk == visible.pk
    assert page.summary == "etapa: NUEVO"

    with pytest.raises(ValidationError):
        execute_definition(
            actor=actor,
            definition={
                "and": [
                    {"field": "current_stage__code", "operator": "eq", "value": "NUEVO"}
                ]
            },
        )
    with pytest.raises(ValidationError):
        execute_definition(
            actor=actor,
            definition={
                "and": [{"field": "source", "operator": "raw_sql", "value": "1=1"}]
            },
        )


@pytest.mark.django_db
def test_saved_view_lifecycle_and_private_shared_boundaries() -> None:
    owner = _actor("segment-private")
    _lead(owner, "Vista privada")
    other = _actor("segment-other")
    manager = _actor("segment-manager", "sales_manager")
    campaign = Campaign.objects.get(code="GENERAL")
    for actor in (other, manager):
        ScopeGrant.objects.get_or_create(
            identity=actor, scope_type=ScopeType.CAMPAIGN, campaign=campaign
        )
    definition = {
        "and": [{"field": "stage", "operator": "eq", "value": "NUEVO"}],
        "sort": "created_desc",
    }

    private = create_saved_view(actor=owner, name="Mis nuevos", definition=definition)
    assert execute_saved_view(actor=owner, view_id=private.pk).total == 1
    with pytest.raises(PermissionDenied):
        execute_saved_view(actor=other, view_id=private.pk)
    shared = create_saved_view(
        actor=manager, name="Nuevos del equipo", definition=definition, shared=True
    )
    assert shared.visibility == SavedViewVisibility.SHARED
    assert execute_saved_view(actor=other, view_id=shared.pk).total == 1
    renamed = rename_saved_view(
        actor=owner,
        view_id=private.pk,
        name="Mis nuevos 2",
        expected_version=private.version,
    )
    copied = copy_saved_view(actor=owner, view_id=renamed.pk, name="Copia privada")
    assert copied.owner_id == owner.pk
    archive_saved_view(actor=owner, view_id=renamed.pk)
    with pytest.raises(PermissionDenied):
        execute_saved_view(actor=owner, view_id=renamed.pk)

    with pytest.raises(PermissionDenied):
        create_saved_view(
            actor=owner,
            name="Compartida no aprobada",
            definition=definition,
            shared=True,
        )


@pytest.mark.django_db
def test_stable_cursor_does_not_duplicate_equal_sort_values() -> None:
    actor = _actor("segment-pagination")
    _lead(actor, "Primera")
    _lead(actor, "Segunda")
    definition = {"and": [], "or": [], "sort": "created_desc"}
    first = execute_definition(actor=actor, definition=definition, page_size=1)
    second = execute_definition(
        actor=actor, definition=definition, cursor=first.next_cursor or 0, page_size=1
    )
    assert first.next_cursor == 1
    assert second.results and second.results[0].pk != first.results[0].pk
