"""Atomic interaction, task, and timeline services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any, Iterable

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from simple_crm.crm.lead_services import transition_lead
from simple_crm.crm.models import (
    InteractionChannel,
    InteractionOutcome,
    Lead,
    LeadAssignment,
    LeadConcurrencyError,
    LeadParty,
    LeadStageHistory,
    Party,
    PartyLifecycle,
)
from simple_crm.identity.models import Action, IdentityProfile
from simple_crm.identity.policy import ScopeSpec, can_access

from .models import (
    ActivityAuditEvent,
    Interaction,
    InteractionDirection,
    InteractionParticipant,
    InteractionResult,
    Task,
    TaskPriority,
    TaskStatus,
)


@dataclass(frozen=True)
class NextTaskSpec:
    description: str
    due_date: date
    owner: IdentityProfile | None = None
    priority: str = TaskPriority.NORMAL


@dataclass(frozen=True)
class QuickContactResult:
    lead: Lead
    interaction: Interaction
    task: Task | None
    audit_event: ActivityAuditEvent


@dataclass(frozen=True)
class TimelineEvent:
    event_type: str
    occurrence_date: date
    occurrence_time: time | None
    entered_at: datetime
    source: str
    record: Any


def _scope_allowed(
    identity: IdentityProfile, action: str, *, campaign_id: int, team_id: int | None
) -> bool:
    if can_access(identity, action, ScopeSpec.campaign_scope(campaign_id)):
        return True
    return bool(team_id and can_access(identity, action, ScopeSpec.team_scope(team_id)))


def _require_lead_access(identity: IdentityProfile, action: str, lead: Lead) -> None:
    if not identity.is_enabled or not _scope_allowed(
        identity,
        action,
        campaign_id=lead.campaign_id,
        team_id=lead.team_id,
    ):
        raise PermissionDenied("No tiene autorización para este lead.")


def _catalog(code: str, model: type[Any], label: str) -> Any:
    try:
        catalog = model.objects.get(code=code)
    except model.DoesNotExist as exc:
        raise ValidationError(f"{label} desconocido.") from exc
    if not catalog.is_active:
        raise ValidationError(f"El {label.lower()} está inactivo.")
    return catalog


def _validate_interaction_semantics(
    *,
    direction: str,
    result: str,
    channel: InteractionChannel,
    outcome: InteractionOutcome,
    note: str,
) -> None:
    if direction not in InteractionDirection.values:
        raise ValidationError("La dirección de interacción no es válida.")
    if result not in InteractionResult.values:
        raise ValidationError("El resultado de contacto no es válido.")
    if direction == InteractionDirection.INBOUND and not channel.allows_inbound:
        raise ValidationError("El canal no admite interacciones entrantes.")
    if (
        result == InteractionResult.RESPONSE
        and direction != InteractionDirection.INBOUND
    ):
        raise ValidationError("Una respuesta debe ser una interacción entrante.")
    if result == InteractionResult.ATTEMPTED and outcome.code == "CONTACTADO":
        raise ValidationError("Un contacto completado no puede ser sólo un intento.")
    if result == InteractionResult.COMPLETED and outcome.code == "SIN_RESPUESTA":
        raise ValidationError("Sin respuesta no representa un contacto completado.")
    if note.strip().casefold() in {
        "sin accion",
        "sin acción",
        "sin accion.",
        "sin acción.",
        "sin contacto",
        "sin contacto.",
    }:
        raise ValidationError("La interacción debe describir un evento real.")


def _validate_next_task(actor: IdentityProfile, lead: Lead, spec: NextTaskSpec) -> None:
    if not spec.description.strip():
        raise ValidationError("La tarea requiere una descripción.")
    if spec.due_date is None:
        raise ValidationError("La tarea requiere fecha de vencimiento.")
    if spec.priority not in TaskPriority.values:
        raise ValidationError("La prioridad de la tarea no es válida.")
    owner = spec.owner or actor
    if not owner.is_enabled or not _scope_allowed(
        owner,
        Action.VIEW,
        campaign_id=lead.campaign_id,
        team_id=lead.team_id,
    ):
        raise ValidationError("El responsable no tiene el alcance del lead.")


@transaction.atomic
def quick_contact(
    *,
    actor: IdentityProfile,
    lead: Lead,
    occurrence_date: date,
    direction: str,
    channel_code: str,
    outcome_code: str,
    result: str,
    note: str = "",
    occurrence_time: time | None = None,
    participants: Iterable[Party] = (),
    source: dict[str, Any] | None = None,
    next_task: NextTaskSpec | None = None,
    target_stage_code: str | None = None,
    stage_change_reason: str = "",
    expected_version: int | None = None,
) -> QuickContactResult:
    """Create a contact, optional next task/stage update, and audit event atomically."""

    locked = Lead.objects.select_for_update().get(pk=lead.pk)
    if expected_version is not None and locked.version != expected_version:
        raise LeadConcurrencyError(
            "El lead cambió; recárguelo antes de registrar el contacto."
        )
    _require_lead_access(actor, Action.CREATE, locked)
    if not occurrence_date:
        raise ValidationError("La interacción requiere fecha de ocurrencia.")
    channel = _catalog(channel_code, InteractionChannel, "canal")
    outcome = _catalog(outcome_code, InteractionOutcome, "resultado")
    _validate_interaction_semantics(
        direction=direction,
        result=result,
        channel=channel,
        outcome=outcome,
        note=note,
    )
    task_owner = (next_task.owner if next_task else None) or actor
    if next_task is not None:
        _validate_next_task(actor, locked, next_task)
        task_owner = next_task.owner or actor

    interaction = Interaction.objects.create(
        lead=locked,
        occurrence_date=occurrence_date,
        occurrence_time=occurrence_time,
        direction=direction,
        channel=channel,
        outcome=outcome,
        result=result,
        note=note.strip(),
        actor=actor.user,
        source=source or {"source_type": "user"},
    )
    for party in participants:
        if party.lifecycle != PartyLifecycle.ACTIVE:
            raise ValidationError("No se puede registrar un participante archivado.")
        if not LeadParty.objects.filter(lead=locked, party=party).exists():
            raise ValidationError("El participante no está vinculado al lead.")
        InteractionParticipant.objects.create(interaction=interaction, party=party)

    task = None
    if next_task is not None:
        task = Task.objects.create(
            lead=locked,
            owner=task_owner,
            description=next_task.description.strip(),
            due_date=next_task.due_date,
            priority=next_task.priority,
            originating_interaction=interaction,
        )
        from simple_crm.platform.jobs import schedule_task_reminder

        schedule_task_reminder(task)

    if target_stage_code:
        transition_fields: dict[str, Any] = {}
        if next_task is not None:
            transition_fields = {
                "next_task_description": next_task.description,
                "next_task_due_at": timezone.make_aware(
                    datetime.combine(next_task.due_date, time.min)
                ),
            }
        locked = transition_lead(
            actor=actor,
            lead=locked,
            target_stage_code=target_stage_code,
            reason=stage_change_reason,
            transition_fields=transition_fields,
            expected_version=locked.version,
        )
    elif next_task is not None:
        locked.next_task_description = next_task.description.strip()
        locked.next_task_due_at = timezone.make_aware(
            datetime.combine(next_task.due_date, time.min)
        )
        locked.next_task_reason = ""
        locked.save(
            update_fields=(
                "next_task_description",
                "next_task_due_at",
                "next_task_reason",
            )
        )

    audit_event = ActivityAuditEvent.objects.create(
        lead=locked,
        interaction=interaction,
        task=task,
        actor=actor.user,
        action="quick_contact",
        details={
            "direction": direction,
            "channel": channel.code,
            "outcome": outcome.code,
            "result": result,
            "target_stage": target_stage_code,
        },
    )
    return QuickContactResult(
        lead=locked, interaction=interaction, task=task, audit_event=audit_event
    )


@transaction.atomic
def complete_task(
    *, actor: IdentityProfile, task: Task, completion_note: str = ""
) -> Task:
    locked = Task.objects.select_for_update().select_related("lead").get(pk=task.pk)
    _require_lead_access(actor, Action.CHANGE, locked.lead)
    if not locked.is_open:
        raise ValidationError("La tarea ya no está abierta.")
    locked.status = TaskStatus.COMPLETED
    locked.completed_at = timezone.now()
    locked.completion_note = completion_note.strip()
    locked.save()
    from simple_crm.platform.jobs import cancel_task_reminders

    cancel_task_reminders(locked.pk)
    ActivityAuditEvent.objects.create(
        lead=locked.lead,
        task=locked,
        actor=actor.user,
        action="task_completed",
        details={"task_id": locked.pk},
    )
    return locked


@transaction.atomic
def reschedule_task(
    *, actor: IdentityProfile, task: Task, due_date: date, reason: str
) -> Task:
    locked = Task.objects.select_for_update().select_related("lead").get(pk=task.pk)
    _require_lead_access(actor, Action.CHANGE, locked.lead)
    if not locked.is_open:
        raise ValidationError("Sólo se puede reprogramar una tarea abierta.")
    if not reason.strip():
        raise ValidationError("La reprogramación requiere un motivo.")
    locked.status = TaskStatus.RESCHEDULED
    locked.due_date = due_date
    locked.rescheduled_at = timezone.now()
    locked.reschedule_reason = reason.strip()
    locked.save()
    from simple_crm.platform.jobs import schedule_task_reminder

    schedule_task_reminder(locked)
    ActivityAuditEvent.objects.create(
        lead=locked.lead,
        task=locked,
        actor=actor.user,
        action="task_rescheduled",
        details={"task_id": locked.pk, "due_date": due_date.isoformat()},
    )
    return locked


@transaction.atomic
def cancel_task(*, actor: IdentityProfile, task: Task, reason: str) -> Task:
    """Cancel an open task and its obsolete reminders atomically."""

    locked = Task.objects.select_for_update().select_related("lead").get(pk=task.pk)
    _require_lead_access(actor, Action.CHANGE, locked.lead)
    if not locked.is_open:
        raise ValidationError("La tarea ya no está abierta.")
    if not reason.strip():
        raise ValidationError("La cancelación requiere un motivo.")
    locked.status = TaskStatus.CANCELLED
    locked.save()
    from simple_crm.platform.jobs import cancel_task_reminders

    cancel_task_reminders(locked.pk)
    ActivityAuditEvent.objects.create(
        lead=locked.lead,
        task=locked,
        actor=actor.user,
        action="task_cancelled",
        details={"task_id": locked.pk},
    )
    return locked


def lead_timeline(*, actor: IdentityProfile, lead: Lead) -> list[TimelineEvent]:
    lead = Lead.objects.get(pk=lead.pk)
    _require_lead_access(actor, Action.VIEW, lead)
    events: list[TimelineEvent] = []
    for interaction in Interaction.objects.filter(lead=lead):
        events.append(
            TimelineEvent(
                event_type="interaction",
                occurrence_date=interaction.occurrence_date,
                occurrence_time=interaction.occurrence_time,
                entered_at=interaction.created_at,
                source=(interaction.source or {}).get("source_type", "user"),
                record=interaction,
            )
        )
    for history in LeadStageHistory.objects.filter(lead=lead):
        events.append(
            TimelineEvent(
                event_type="stage",
                occurrence_date=timezone.localtime(history.occurred_at).date(),
                occurrence_time=timezone.localtime(history.occurred_at).time(),
                entered_at=history.occurred_at,
                source="stage_history",
                record=history,
            )
        )
    for assignment in LeadAssignment.objects.filter(lead=lead):
        assigned_at = timezone.localtime(assignment.assigned_at)
        events.append(
            TimelineEvent(
                event_type="assignment",
                occurrence_date=assigned_at.date(),
                occurrence_time=assigned_at.time(),
                entered_at=assignment.assigned_at,
                source="assignment_history",
                record=assignment,
            )
        )
    return sorted(
        events,
        key=lambda event: (
            event.occurrence_date,
            event.occurrence_time or time.min,
            event.entered_at,
            event.event_type,
            event.record.pk,
        ),
    )
