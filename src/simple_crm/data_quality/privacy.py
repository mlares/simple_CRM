"""Permissioned privacy bundles, suppression, retention, and safe audit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from simple_crm.activity.models import Interaction, Task
from simple_crm.crm.models import (
    ContactPoint,
    Lead,
    Party,
    PartyContactPoint,
)
from simple_crm.identity.models import Action, IdentityProfile
from simple_crm.identity.policy import ScopeSpec, can_access
from simple_crm.reporting.models import ExportRequest

from .models import (
    GovernanceAuditEvent,
    LegalHold,
    PrivacyCase,
    PrivacyCaseState,
    PrivacyCaseType,
    RetentionCategory,
    RetentionDecision,
    RetentionDecisionState,
    SourceCanonicalLink,
)

CLINICAL_DATA_GUIDANCE = (
    "Este CRM es comercial: no registre pacientes, historias clínicas, diagnósticos "
    "ni otros datos clínicos. Reporte contenido sensible al responsable de privacidad."
)


@dataclass(frozen=True)
class PrivacyBundle:
    party: Party
    contact_points: tuple[dict[str, Any], ...]
    leads: tuple[dict[str, Any], ...]
    interactions: tuple[dict[str, Any], ...]
    tasks: tuple[dict[str, Any], ...]
    source_links: tuple[dict[str, Any], ...]
    exports: tuple[dict[str, Any], ...]
    suppression: tuple[dict[str, Any], ...]


def _require_audit_access(actor: IdentityProfile) -> None:
    if not actor.is_enabled or not can_access(
        actor, Action.AUDIT_VIEW, ScopeSpec.global_scope()
    ):
        raise PermissionDenied("No tiene autorización para revisar privacidad.")


def _require_change_access(actor: IdentityProfile) -> None:
    if not actor.is_enabled or not can_access(
        actor, Action.CHANGE, ScopeSpec.global_scope()
    ):
        raise PermissionDenied("No tiene autorización para ejecutar esta corrección.")


def _safe_audit(
    *,
    actor: IdentityProfile | None,
    action: str,
    target_type: str,
    target_id: object,
    reason: str = "",
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    correlation: str = "",
    metadata: dict[str, Any] | None = None,
) -> GovernanceAuditEvent:
    return GovernanceAuditEvent.objects.create(
        actor=actor.user if actor else None,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        request_correlation=correlation,
        reason=reason.strip(),
        before_state=before or {},
        after_state=after or {},
        metadata=metadata or {},
    )


def privacy_bundle(*, actor: IdentityProfile, party_id: int) -> PrivacyBundle:
    """Return related personal-data locations without exposing arbitrary payloads."""

    _require_audit_access(actor)
    party = Party.objects.get(pk=party_id)
    contact_points = tuple(
        {
            "id": link.contact_point_id,
            "kind": link.contact_point.kind,
            "raw_value": link.contact_point.raw_value,
            "is_suppressed": link.contact_point.is_suppressed,
            "suppression_reason": link.contact_point.suppression_reason,
        }
        for link in PartyContactPoint.objects.filter(party=party).select_related(
            "contact_point"
        )
    )
    leads = tuple(
        {
            "id": lead.pk,
            "lead_number": lead.lead_number,
            "campaign": lead.campaign.code,
            "stage": lead.current_stage.code,
            "lifecycle": lead.lifecycle,
        }
        for lead in Lead.objects.filter(party_links__party=party)
        .select_related("campaign", "current_stage")
        .distinct()
    )
    lead_ids = [row["id"] for row in leads if row["id"] is not None]
    interactions = tuple(
        {
            "id": interaction.pk,
            "lead_id": interaction.lead_id,
            "occurrence_date": interaction.occurrence_date.isoformat(),
            "result": interaction.result,
            "has_note": bool(interaction.note.strip()),
        }
        for interaction in Interaction.objects.filter(lead_id__in=lead_ids)
    )
    tasks = tuple(
        {
            "id": task.pk,
            "lead_id": task.lead_id,
            "due_date": task.due_date.isoformat(),
            "status": task.status,
        }
        for task in Task.objects.filter(lead_id__in=lead_ids)
    )
    source_links = tuple(
        {
            "source_record_id": link.source_record_id,
            "relation": link.relation,
            "target_type": link.target_type,
        }
        for link in SourceCanonicalLink.objects.filter(
            target_type="Party", target_id=str(party.pk)
        )
    )
    exports = tuple(
        {
            "id": export.pk,
            "state": export.state,
            "row_count": export.row_count,
            "checksum": export.checksum,
        }
        for export in ExportRequest.objects.filter(
            definition_snapshot__icontains=str(party.pk)
        )[:100]
    )
    return PrivacyBundle(
        party=party,
        contact_points=contact_points,
        leads=leads,
        interactions=interactions,
        tasks=tasks,
        source_links=source_links,
        exports=exports,
        suppression=tuple(
            {"contact_point_id": item["id"], "suppressed": item["is_suppressed"]}
            for item in contact_points
        ),
    )


@transaction.atomic
def open_privacy_case(
    *,
    actor: IdentityProfile,
    subject: Party,
    case_type: str,
    reason: str,
    correlation: str = "",
) -> PrivacyCase:
    _require_audit_access(actor)
    if case_type not in PrivacyCaseType.values or not reason.strip():
        raise ValidationError("La solicitud de privacidad no es válida.")
    case = PrivacyCase.objects.create(
        subject=subject,
        requested_by=actor,
        case_type=case_type,
        reason=reason.strip(),
        request_correlation=correlation,
    )
    _safe_audit(
        actor=actor,
        action="privacy_case_opened",
        target_type="PrivacyCase",
        target_id=case.pk,
        reason=reason,
        correlation=correlation,
        after={"state": case.state, "case_type": case.case_type},
    )
    return case


@transaction.atomic
def complete_privacy_case(
    *, actor: IdentityProfile, case_id: int, decision_reason: str
) -> PrivacyCase:
    _require_change_access(actor)
    if not decision_reason.strip():
        raise ValidationError("La decisión de privacidad requiere un motivo.")
    case = PrivacyCase.objects.select_for_update().get(pk=case_id)
    if case.state not in {PrivacyCaseState.OPEN, PrivacyCaseState.APPROVED}:
        raise ValidationError("La solicitud no puede completarse en su estado actual.")
    before = {"state": case.state}
    case.state = PrivacyCaseState.COMPLETED
    case.decision_reason = decision_reason.strip()
    case.completed_at = timezone.now()
    case.save(update_fields=("state", "decision_reason", "completed_at", "updated_at"))
    _safe_audit(
        actor=actor,
        action="privacy_case_completed",
        target_type="PrivacyCase",
        target_id=case.pk,
        reason=decision_reason,
        before=before,
        after={"state": case.state},
    )
    return case


@transaction.atomic
def suppress_contact_point(
    *,
    actor: IdentityProfile,
    contact_point: ContactPoint,
    reason: str,
    case_id: int | None = None,
) -> ContactPoint:
    _require_change_access(actor)
    if not reason.strip():
        raise ValidationError("La supresión requiere un motivo.")
    before = {"is_suppressed": contact_point.is_suppressed}
    contact_point.suppress(reason)
    _safe_audit(
        actor=actor,
        action="contact_suppressed",
        target_type="ContactPoint",
        target_id=contact_point.pk,
        reason=reason,
        before=before,
        after={"is_suppressed": True},
        metadata={"case_id": case_id} if case_id else {},
    )
    return contact_point


def _has_hold(target_type: str, target_id: str) -> bool:
    return LegalHold.objects.filter(
        target_type=target_type, target_id=target_id, active=True
    ).exists()


@transaction.atomic
def preview_retention(
    *,
    actor: IdentityProfile,
    target_type: str,
    target_id: str,
    category: RetentionCategory,
    reason: str,
) -> RetentionDecision:
    _require_audit_access(actor)
    if not reason.strip() or not category.is_active:
        raise ValidationError("La previsualización de retención no es válida.")
    held = _has_hold(target_type, target_id)
    decision = RetentionDecision.objects.create(
        target_type=target_type,
        target_id=str(target_id),
        category=category,
        preview={
            "target_type": target_type,
            "target_id": str(target_id),
            "retention_days": category.retention_days,
            "eligible": not held,
        },
        legal_hold_excluded=held,
        reason=reason.strip(),
    )
    _safe_audit(
        actor=actor,
        action="retention_previewed",
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        after={"eligible": not held},
        metadata={"decision_id": decision.pk},
    )
    return decision


@transaction.atomic
def approve_retention(
    *, actor: IdentityProfile, decision_id: int, reason: str
) -> RetentionDecision:
    _require_change_access(actor)
    if not reason.strip():
        raise ValidationError("La aprobación de retención requiere un motivo.")
    decision = RetentionDecision.objects.select_for_update().get(pk=decision_id)
    if decision.state != RetentionDecisionState.PREVIEWED:
        raise ValidationError("La decisión ya fue procesada.")
    decision.state = RetentionDecisionState.APPROVED
    decision.approved_by = actor.user
    decision.approved_at = timezone.now()
    decision.reason = reason.strip()
    decision.save(update_fields=("state", "approved_by", "approved_at", "reason"))
    _safe_audit(
        actor=actor,
        action="retention_approved",
        target_type=decision.target_type,
        target_id=decision.target_id,
        reason=reason,
        after={"state": decision.state},
        metadata={"decision_id": decision.pk},
    )
    return decision


@transaction.atomic
def execute_retention(
    *, actor: IdentityProfile, decision_id: int, reason: str
) -> RetentionDecision:
    _require_change_access(actor)
    decision = RetentionDecision.objects.select_for_update().get(pk=decision_id)
    if decision.state != RetentionDecisionState.APPROVED:
        raise ValidationError("La retención requiere aprobación previa.")
    held = _has_hold(decision.target_type, decision.target_id)
    decision.legal_hold_excluded = held
    decision.state = RetentionDecisionState.EXECUTED
    decision.executed_at = timezone.now()
    decision.save(update_fields=("legal_hold_excluded", "state", "executed_at"))
    _safe_audit(
        actor=actor,
        action="retention_executed",
        target_type=decision.target_type,
        target_id=decision.target_id,
        reason=reason,
        after={"state": decision.state, "excluded_by_legal_hold": held},
        metadata={"destructive_delete": False, "retention_only": True},
    )
    return decision
