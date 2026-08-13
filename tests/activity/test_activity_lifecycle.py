from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from simple_crm.activity.models import (
    ActivityAuditEvent,
    Interaction,
    InteractionDirection,
    InteractionParticipant,
    InteractionResult,
    Task,
    TaskStatus,
)
from simple_crm.activity.services import (
    NextTaskSpec,
    complete_task,
    lead_timeline,
    quick_contact,
    reschedule_task,
)
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


def _lead(actor: IdentityProfile):
    campaign = Campaign.objects.get(code="GENERAL")
    _campaign_scope(actor, campaign)
    party, _ = create_organization_party(display_name="Hospital de actividad")
    lead, _ = create_lead(
        actor=actor,
        campaign=campaign,
        owner=actor,
        parties=((party, LeadPartyRole.ACCOUNT),),
    )
    return lead, party


@pytest.mark.django_db
def test_quick_contact_atomically_writes_interaction_task_stage_and_audit() -> None:
    actor = _seller("activity-creator")
    lead, party = _lead(actor)

    result = quick_contact(
        actor=actor,
        lead=lead,
        occurrence_date=date(2026, 8, 10),
        direction=InteractionDirection.OUTBOUND,
        channel_code="TELEFONO",
        outcome_code="SIN_RESPUESTA",
        result=InteractionResult.ATTEMPTED,
        note="Se intentó llamar al contacto.",
        participants=(party,),
        next_task=NextTaskSpec(
            description="Volver a llamar",
            due_date=date(2026, 8, 12),
        ),
        target_stage_code="EN_GESTION",
        stage_change_reason="Inicio del seguimiento",
        expected_version=lead.version,
    )

    assert result.interaction.lead_id == lead.pk
    assert result.interaction.occurrence_time is None
    assert InteractionParticipant.objects.filter(
        interaction=result.interaction, party=party
    ).exists()
    assert result.task is not None
    assert result.task.originating_interaction_id == result.interaction.pk
    assert result.task.status == TaskStatus.OPEN
    assert ActivityAuditEvent.objects.filter(
        interaction=result.interaction, task=result.task, action="quick_contact"
    ).exists()
    result.lead.refresh_from_db()
    assert result.lead.current_stage.code == "EN_GESTION"
    assert result.lead.next_task_description == "Volver a llamar"


@pytest.mark.django_db
def test_invalid_quick_contact_does_not_create_partial_activity() -> None:
    actor = _seller("activity-invalid")
    lead, _ = _lead(actor)

    with pytest.raises(ValidationError, match="evento real"):
        quick_contact(
            actor=actor,
            lead=lead,
            occurrence_date=date(2026, 8, 10),
            direction=InteractionDirection.OUTBOUND,
            channel_code="TELEFONO",
            outcome_code="CONTACTADO",
            result=InteractionResult.COMPLETED,
            note="Sin accion",
            next_task=NextTaskSpec(
                description="No debe persistir", due_date=date.today()
            ),
        )

    assert Interaction.objects.count() == 0
    assert Task.objects.count() == 0
    assert ActivityAuditEvent.objects.count() == 0


@pytest.mark.django_db
def test_task_state_dates_and_timezone_aware_overdue_behavior() -> None:
    actor = _seller("task-owner")
    lead, _ = _lead(actor)
    result = quick_contact(
        actor=actor,
        lead=lead,
        occurrence_date=date.today(),
        direction=InteractionDirection.OUTBOUND,
        channel_code="EMAIL",
        outcome_code="CONTACTADO",
        result=InteractionResult.COMPLETED,
        note="Respondió por correo.",
        next_task=NextTaskSpec(description="Enviar propuesta", due_date=date.today()),
    )
    assert result.task is not None
    assert not result.task.is_overdue(today=date.today())
    completed = complete_task(actor=actor, task=result.task, completion_note="Enviada")
    assert completed.status == TaskStatus.COMPLETED
    assert completed.completed_at is not None
    assert timezone.is_aware(completed.completed_at)

    second = quick_contact(
        actor=actor,
        lead=lead,
        occurrence_date=date.today(),
        direction=InteractionDirection.OUTBOUND,
        channel_code="EMAIL",
        outcome_code="SEGUIMIENTO",
        result=InteractionResult.COMPLETED,
        note="Se acordó revisar el presupuesto.",
        next_task=NextTaskSpec(
            description="Revisar presupuesto", due_date=date.today() - timedelta(days=1)
        ),
    ).task
    assert second is not None and second.is_overdue(today=date.today())
    rescheduled = reschedule_task(
        actor=actor,
        task=second,
        due_date=date.today() + timedelta(days=2),
        reason="El cliente pidió más tiempo",
    )
    assert rescheduled.status == TaskStatus.RESCHEDULED
    assert rescheduled.completed_at is None
    assert rescheduled.rescheduled_at is not None


@pytest.mark.django_db
def test_timeline_is_stable_date_aware_and_permission_scoped() -> None:
    actor = _seller("timeline-owner")
    outsider = _seller("timeline-outsider", "sales_manager")
    lead, _ = _lead(actor)
    quick_contact(
        actor=actor,
        lead=lead,
        occurrence_date=date(2026, 8, 9),
        direction=InteractionDirection.OUTBOUND,
        channel_code="WHATSAPP",
        outcome_code="CONTACTADO",
        result=InteractionResult.COMPLETED,
        note="Confirmó recepción.",
    )

    timeline = lead_timeline(actor=actor, lead=lead)
    assert timeline[0].event_type == "interaction"
    assert {event.event_type for event in timeline[1:]} >= {"assignment", "stage"}
    assert timeline[0].occurrence_time is None
    assert timeline[0].source == "user"
    assert timeline[-1].event_type in {"assignment", "stage"}

    with pytest.raises(PermissionDenied):
        lead_timeline(actor=outsider, lead=lead)


@pytest.mark.django_db
def test_governed_semantics_reject_non_inbound_response_and_inactive_channel() -> None:
    actor = _seller("activity-semantics")
    lead, _ = _lead(actor)

    with pytest.raises(ValidationError, match="entrante"):
        quick_contact(
            actor=actor,
            lead=lead,
            occurrence_date=date.today(),
            direction=InteractionDirection.OUTBOUND,
            channel_code="EMAIL",
            outcome_code="CONTACTADO",
            result=InteractionResult.RESPONSE,
            note="Respuesta mal clasificada.",
        )

    with pytest.raises(ValidationError, match="canal"):
        quick_contact(
            actor=actor,
            lead=lead,
            occurrence_date=date.today(),
            direction=InteractionDirection.INBOUND,
            channel_code="WEB",
            outcome_code="CONTACTADO",
            result=InteractionResult.RESPONSE,
            note="Formulario recibido.",
        )
