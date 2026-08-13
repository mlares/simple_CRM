"""Atomic lead lifecycle, ownership, and scope-aware services."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from simple_crm.config.observability import record_event, record_metric
from simple_crm.identity.models import Action, IdentityProfile
from simple_crm.identity.policy import ScopeSpec, can_access, scoped_queryset

from .models import (
    AssignmentRole,
    Campaign,
    Lead,
    LeadAssignment,
    LeadConcurrencyError,
    LeadParty,
    LeadStageHistory,
    LeadStatus,
    Party,
)

ALLOWED_STAGE_TRANSITIONS: dict[str, frozenset[str]] = {
    "NUEVO": frozenset({"EN_GESTION", "CERRADO"}),
    "EN_GESTION": frozenset({"CERRADO"}),
    "CERRADO": frozenset(),
}


@dataclass(frozen=True)
class LeadMatchWarning:
    warning_type: str
    message: str
    party_id: int
    lead_id: int


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


def preview_lead_creation(
    *, campaign: Campaign, parties: Iterable[Party]
) -> list[LeadMatchWarning]:
    party_ids = {party.pk for party in parties if party.pk is not None}
    if not party_ids:
        return []
    warnings: list[LeadMatchWarning] = []
    leads = (
        Lead.objects.active()
        .filter(campaign=campaign, party_links__party_id__in=party_ids)
        .distinct()
    )
    for lead in leads:
        for party_id in lead.party_links.filter(party_id__in=party_ids).values_list(
            "party_id", flat=True
        ):
            warnings.append(
                LeadMatchWarning(
                    warning_type="EXISTING_LEAD_CANDIDATE",
                    message="La parte ya participa en un lead de esta campaña.",
                    party_id=party_id,
                    lead_id=lead.pk,
                )
            )
    return warnings


def _next_action_values(
    next_task_description: str = "",
    next_task_due_at: datetime | None = None,
    next_task_reason: str = "",
) -> dict[str, Any]:
    description = next_task_description.strip()
    reason = next_task_reason.strip()
    if (description and next_task_due_at) or reason:
        return {
            "next_task_description": description,
            "next_task_due_at": next_task_due_at,
            "next_task_reason": reason,
        }
    if description or next_task_due_at:
        raise ValidationError(
            "El próximo paso requiere descripción y fecha, o un motivo explícito."
        )
    return {
        "next_task_description": "",
        "next_task_due_at": None,
        "next_task_reason": "",
    }


def _json_safe_fields(fields: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(json.dumps(fields, cls=DjangoJSONEncoder))
    except (TypeError, ValueError) as exc:
        raise ValidationError("Los campos del cambio no son serializables.") from exc


@transaction.atomic
def create_lead(
    *,
    actor: IdentityProfile,
    campaign: Campaign,
    owner: IdentityProfile,
    parties: Iterable[tuple[Party, str]],
    team_id: int | None = None,
    source_attribution: dict[str, Any] | None = None,
    next_task_description: str = "",
    next_task_due_at: datetime | None = None,
    next_task_reason: str = "",
) -> tuple[Lead, list[LeadMatchWarning]]:
    if not _scope_allowed(
        actor, Action.CREATE, campaign_id=campaign.pk, team_id=team_id
    ):
        raise PermissionDenied("No tiene autorización para crear este lead.")
    if not owner.is_enabled or not _scope_allowed(
        owner, Action.VIEW, campaign_id=campaign.pk, team_id=team_id
    ):
        raise ValidationError("El propietario no tiene el alcance del lead.")
    party_links = tuple(parties)
    warnings = preview_lead_creation(
        campaign=campaign, parties=(p for p, _ in party_links)
    )
    initial_stage = LeadStatus.objects.get(code="NUEVO")
    lead = Lead(
        campaign=campaign,
        team_id=team_id,
        current_stage=initial_stage,
        source_attribution=source_attribution or {},
        **_next_action_values(
            next_task_description, next_task_due_at, next_task_reason
        ),
    )
    lead.save()
    for party, role in party_links:
        LeadParty.objects.create(lead=lead, party=party, party_role=role)
    LeadAssignment.objects.create(
        lead=lead,
        identity=owner,
        assignment_role=AssignmentRole.PRIMARY,
        assigned_by=actor.user,
    )
    LeadStageHistory.objects.create(
        lead=lead,
        from_stage=None,
        to_stage=initial_stage,
        actor=actor.user,
        reason="Creación del lead",
    )
    record_metric("domain.leads.created")
    record_event("domain.lead.create", component="domain", outcome="created")
    return lead, warnings


@transaction.atomic
def transition_lead(
    *,
    actor: IdentityProfile,
    lead: Lead,
    target_stage_code: str,
    reason: str,
    transition_fields: dict[str, Any] | None = None,
    expected_version: int | None = None,
) -> Lead:
    locked = Lead.objects.select_for_update().get(pk=lead.pk)
    if expected_version is not None and locked.version != expected_version:
        raise LeadConcurrencyError(
            "El lead cambió; recárguelo antes de cambiar la etapa."
        )
    _require_lead_access(actor, Action.CHANGE, locked)
    target = LeadStatus.objects.get(code=target_stage_code)
    current_code = locked.current_stage.code
    if target.code not in ALLOWED_STAGE_TRANSITIONS.get(current_code, frozenset()):
        raise ValidationError("La transición de etapa no está permitida.")
    if not reason.strip():
        raise ValidationError("El cambio de etapa requiere un motivo.")
    fields = dict(transition_fields or {})
    history_fields = _json_safe_fields(fields)
    next_values = _next_action_values(
        fields.get("next_task_description", locked.next_task_description),
        fields.get("next_task_due_at", locked.next_task_due_at),
        fields.get("next_task_reason", locked.next_task_reason),
    )
    if target.is_closed and not str(fields.get("closure_reason", "")).strip():
        raise ValidationError("El cierre requiere un motivo de cierre.")
    if target.code == "EN_GESTION" and not any(next_values.values()):
        raise ValidationError("Un lead en gestión requiere próximo paso o motivo.")
    previous = locked.current_stage
    locked.current_stage = target
    locked.next_task_description = next_values["next_task_description"]
    locked.next_task_due_at = next_values["next_task_due_at"]
    locked.next_task_reason = next_values["next_task_reason"]
    locked.save()
    LeadStageHistory.objects.create(
        lead=locked,
        from_stage=previous,
        to_stage=target,
        actor=actor.user,
        reason=reason.strip(),
        transition_fields=history_fields,
    )
    record_metric("domain.leads.transitioned")
    record_event("domain.lead.transition", component="domain", outcome="changed")
    return locked


@transaction.atomic
def reassign_lead(
    *,
    actor: IdentityProfile,
    lead: Lead,
    new_owner: IdentityProfile,
    expected_version: int | None = None,
) -> Lead:
    locked = Lead.objects.select_for_update().get(pk=lead.pk)
    if expected_version is not None and locked.version != expected_version:
        raise LeadConcurrencyError("El lead cambió; recárguelo antes de reasignarlo.")
    _require_lead_access(actor, Action.REASSIGN, locked)
    if not new_owner.is_enabled or not _scope_allowed(
        new_owner,
        Action.VIEW,
        campaign_id=locked.campaign_id,
        team_id=locked.team_id,
    ):
        raise ValidationError("El nuevo propietario no tiene el alcance del lead.")
    now = timezone.now()
    LeadAssignment.objects.filter(
        lead=locked,
        assignment_role=AssignmentRole.PRIMARY,
        unassigned_at__isnull=True,
    ).update(unassigned_at=now)
    LeadAssignment.objects.create(
        lead=locked,
        identity=new_owner,
        assignment_role=AssignmentRole.PRIMARY,
        assigned_at=now,
        assigned_by=actor.user,
    )
    locked.save()
    record_metric("domain.leads.reassigned")
    record_event("domain.lead.reassign", component="domain", outcome="changed")
    return locked


def visible_leads(actor: IdentityProfile) -> QuerySet[Lead]:
    return scoped_queryset(
        Lead.objects.active(),
        actor,
        Action.VIEW,
        team_field="team_id",
        campaign_field="campaign_id",
    )
