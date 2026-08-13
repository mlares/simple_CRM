from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from simple_crm.crm.lead_services import (
    create_lead,
    reassign_lead,
    transition_lead,
    visible_leads,
)
from simple_crm.crm.models import (
    AssignmentRole,
    Campaign,
    Lead,
    LeadAssignment,
    LeadConcurrencyError,
    LeadPartyRole,
    LeadStageHistory,
)
from simple_crm.crm.services import create_organization_party
from simple_crm.identity.models import (
    IdentityProfile,
    Role,
    RoleAssignment,
    ScopeGrant,
    ScopeType,
)


def _seller(username: str, role_code: str = "sales_representative") -> IdentityProfile:
    user = get_user_model().objects.create_user(username=username, password="safe-pass")
    profile = IdentityProfile.objects.get(user=user)
    RoleAssignment.objects.create(
        identity=profile, role=Role.objects.get(code=role_code)
    )
    return profile


def _campaign_scope(profile: IdentityProfile, campaign: Campaign) -> None:
    ScopeGrant.objects.create(
        identity=profile, scope_type=ScopeType.CAMPAIGN, campaign=campaign
    )


def _new_lead(
    actor: IdentityProfile,
    campaign: Campaign,
    party=None,
) -> Lead:
    if party is None:
        party, _ = create_organization_party(display_name="Hospital de prueba")
    lead, _ = create_lead(
        actor=actor,
        campaign=campaign,
        owner=actor,
        parties=((party, LeadPartyRole.ACCOUNT),),
    )
    return lead


@pytest.mark.django_db
def test_lead_creation_writes_current_stage_history_owner_and_links_atomically() -> (
    None
):
    actor = _seller("lead-creator")
    campaign = Campaign.objects.get(code="GENERAL")
    _campaign_scope(actor, campaign)
    party, _ = create_organization_party(display_name="Hospital Central")
    due_at = timezone.now() + timedelta(days=2)

    lead, warnings = create_lead(
        actor=actor,
        campaign=campaign,
        owner=actor,
        parties=((party, LeadPartyRole.ACCOUNT),),
        source_attribution={"source": "workbook", "row": 12},
        next_task_description="Confirmar contacto",
        next_task_due_at=due_at,
    )

    assert warnings == []
    assert lead.lead_number == f"LEAD-{lead.pk:06d}"
    assert lead.current_stage.code == "NUEVO"
    assert lead.stage_history.latest("occurred_at").to_stage == lead.current_stage
    assert (
        lead.assignments.get(
            assignment_role=AssignmentRole.PRIMARY, unassigned_at__isnull=True
        ).identity
        == actor
    )
    assert lead.party_links.get(party=party).party_role == LeadPartyRole.ACCOUNT
    assert lead.source_attribution["row"] == 12


@pytest.mark.django_db
def test_stage_transition_matrix_reasons_and_required_fields_are_atomic() -> None:
    actor = _seller("stage-owner")
    campaign = Campaign.objects.get(code="GENERAL")
    _campaign_scope(actor, campaign)
    lead = _new_lead(actor, campaign)

    with pytest.raises(ValidationError, match="próximo paso"):
        transition_lead(
            actor=actor,
            lead=lead,
            target_stage_code="EN_GESTION",
            reason="Comenzar seguimiento",
        )
    lead.refresh_from_db()
    assert lead.current_stage.code == "NUEVO"
    assert lead.stage_history.count() == 1

    transition_lead(
        actor=actor,
        lead=lead,
        target_stage_code="EN_GESTION",
        reason="Comenzar seguimiento",
        transition_fields={
            "next_task_description": "Llamar al contacto",
            "next_task_due_at": timezone.now() + timedelta(days=1),
        },
    )
    lead.refresh_from_db()
    assert lead.current_stage.code == "EN_GESTION"
    assert lead.stage_history.count() == 2

    with pytest.raises(ValidationError, match="cierre"):
        transition_lead(
            actor=actor,
            lead=lead,
            target_stage_code="CERRADO",
            reason="Finalizar",
        )
    lead.refresh_from_db()
    assert lead.current_stage.code == "EN_GESTION"
    assert lead.stage_history.count() == 2

    transition_lead(
        actor=actor,
        lead=lead,
        target_stage_code="CERRADO",
        reason="Finalizar",
        transition_fields={"closure_reason": "No requiere seguimiento"},
    )
    lead.refresh_from_db()
    assert lead.current_stage.code == "CERRADO"
    assert lead.stage_history.latest("occurred_at").to_stage == lead.current_stage

    with pytest.raises(ValidationError, match="transición"):
        transition_lead(
            actor=actor,
            lead=lead,
            target_stage_code="NUEVO",
            reason="Reabrir",
        )


@pytest.mark.django_db
def test_primary_assignment_is_unique_and_reassignment_preserves_history() -> None:
    manager = _seller("assignment-manager", "sales_manager")
    replacement = _seller("replacement")
    campaign = Campaign.objects.get(code="GENERAL")
    _campaign_scope(manager, campaign)
    _campaign_scope(replacement, campaign)
    lead = _new_lead(manager, campaign)

    with transaction.atomic(), pytest.raises(IntegrityError):
        LeadAssignment.objects.create(
            lead=lead,
            identity=replacement,
            assignment_role=AssignmentRole.PRIMARY,
        )

    reassigned = reassign_lead(
        actor=manager,
        lead=lead,
        new_owner=replacement,
        expected_version=lead.version,
    )
    assert (
        reassigned.assignments.filter(
            assignment_role=AssignmentRole.PRIMARY, unassigned_at__isnull=True
        ).count()
        == 1
    )
    assert reassigned.assignments.filter(unassigned_at__isnull=False).count() == 1


@pytest.mark.django_db
def test_out_of_scope_identity_cannot_transition_reassign_or_list_by_id() -> None:
    actor = _seller("scoped-owner")
    outsider = _seller("scoped-outsider", "sales_manager")
    campaign = Campaign.objects.get(code="GENERAL")
    _campaign_scope(actor, campaign)
    lead = _new_lead(actor, campaign)

    with pytest.raises(PermissionDenied):
        transition_lead(
            actor=outsider,
            lead=lead,
            target_stage_code="EN_GESTION",
            reason="Intento fuera de alcance",
            transition_fields={
                "next_task_reason": "Debe ser rechazado",
            },
        )
    with pytest.raises(PermissionDenied):
        reassign_lead(actor=outsider, lead=lead, new_owner=outsider)
    assert not visible_leads(outsider).filter(pk=lead.pk).exists()


@pytest.mark.django_db
def test_stale_transition_is_rejected_without_partial_history_write() -> None:
    actor = _seller("concurrent-owner")
    campaign = Campaign.objects.get(code="GENERAL")
    _campaign_scope(actor, campaign)
    lead = _new_lead(actor, campaign)
    stale_version = lead.version
    transition_lead(
        actor=actor,
        lead=lead,
        target_stage_code="EN_GESTION",
        reason="Avance válido",
        transition_fields={"next_task_reason": "Esperando confirmación"},
    )

    with pytest.raises(LeadConcurrencyError, match="cambió"):
        transition_lead(
            actor=actor,
            lead=lead,
            target_stage_code="CERRADO",
            reason="Edición obsoleta",
            transition_fields={"closure_reason": "No corresponde"},
            expected_version=stale_version,
        )
    assert LeadStageHistory.objects.filter(lead=lead).count() == 2


@pytest.mark.django_db
def test_lead_creation_warns_existing_candidate_but_creates_new_atomic_lead() -> None:
    actor = _seller("candidate-owner")
    campaign = Campaign.objects.get(code="GENERAL")
    _campaign_scope(actor, campaign)
    party, _ = create_organization_party(display_name="Candidato repetido")
    first = _new_lead(actor, campaign, party)
    second, warnings = create_lead(
        actor=actor,
        campaign=campaign,
        owner=actor,
        parties=((party, LeadPartyRole.ACCOUNT),),
        next_task_reason="Revisar duplicado antes de contactar",
    )

    assert second.pk != first.pk
    assert any(w.warning_type == "EXISTING_LEAD_CANDIDATE" for w in warnings)
    assert second.stage_history.count() == 1
    assert second.assignments.filter(unassigned_at__isnull=True).count() == 1
