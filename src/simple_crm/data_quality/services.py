"""Bounded, lossless workbook staging and audited import-state services."""

from __future__ import annotations

import hashlib
import io
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from difflib import SequenceMatcher
from pathlib import PurePosixPath
from typing import Any, Iterable

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from openpyxl import load_workbook  # type: ignore[import-untyped]

from simple_crm.activity.models import Interaction, InteractionParticipant, Task
from simple_crm.config.observability import record_event, record_metric
from simple_crm.crm.models import (
    ContactPoint,
    LeadParty,
    Party,
    PartyAlias,
    PartyContactPoint,
    PartyLifecycle,
    PartyType,
)
from simple_crm.crm.normalization import comparison_key
from simple_crm.identity.models import Action, IdentityProfile
from simple_crm.identity.policy import ScopeSpec, can_access

from .models import (
    CandidateMatch,
    ImportAuditEvent,
    ImportBatch,
    ImportStatus,
    MatchState,
    MatchType,
    QualityAuditEvent,
    QualityIssue,
    QualityIssueState,
    QualitySeverity,
    SourceCanonicalLink,
    SourceDocument,
    SourceRecord,
    SourceRecordClassification,
)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
DEFAULT_PARSER_VERSION = "openpyxl-xlsx-v1"
DEFAULT_APPLICATION_VERSION = "crm-010-v1"

KNOWN_HEADER_KEYS = frozenset(
    {
        "area",
        "asignado",
        "campaign_id",
        "celular_whatsapp",
        "contacto",
        "correo",
        "current_status_code",
        "data_readiness",
        "email",
        "estatus",
        "fecha_contacto",
        "fuente",
        "lead_id",
        "mail",
        "medio",
        "nombre",
        "notas_observaciones",
        "organizacion",
        "organization",
        "party_id",
        "phone",
        "provincia",
        "respuesta",
        "role",
        "source_record_id",
        "siguientes_pasos",
        "status",
        "telefono",
        "telefono_digits",
        "telefono_normalizado",
        "telefono_whatsapp",
        "whatsapp",
    }
)

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def safe_upload_filename(filename: str) -> str:
    """Keep an upload label safe for logs, audit, and future filesystem use."""

    basename = PurePosixPath(filename.replace("\\", "/")).name
    normalized = unicodedata.normalize("NFKD", basename)
    ascii_name = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    safe_name = _UNSAFE_FILENAME_CHARS.sub("_", ascii_name).strip("._")
    if not safe_name or not safe_name.lower().endswith(".xlsx"):
        raise ValidationError("El nombre del archivo Excel no es válido.")
    return f"{safe_name[:-5][:115]}.xlsx"


@dataclass(frozen=True)
class ImportPreview:
    batch: ImportBatch
    reused: bool
    row_count: int
    error_count: int
    warning_count: int
    duplicate_count: int
    unmatched_count: int
    canonical_diff_count: int


def _normalized_header(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return "_".join(
        part
        for part in "".join(
            char.lower() if char.isalnum() else " " for char in ascii_text
        ).split()
    )


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _checksum(value: Any) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_steward(actor: IdentityProfile, action: str) -> None:
    is_steward = (
        actor.role_assignments.filter(
            role__code__in=("data_steward", "system_administrator"),
            role__is_active=True,
            starts_at__lte=timezone.now(),
        )
        .filter(models_q_ends_at())
        .exists()
    )
    if (
        not actor.is_enabled
        or not is_steward
        or not can_access(actor, action, ScopeSpec.global_scope())
    ):
        raise PermissionDenied("Sólo un responsable de datos puede operar este lote.")


def models_q_ends_at() -> Any:
    """Keep the active-role predicate local without importing model internals."""

    from django.db.models import Q

    return Q(ends_at__isnull=True) | Q(ends_at__gt=timezone.now())


def _workbook_rows(content: bytes) -> list[dict[str, Any]]:
    try:
        workbook = load_workbook(
            filename=io.BytesIO(content), read_only=True, data_only=False
        )
    except Exception as exc:  # openpyxl exposes several parser-specific exceptions
        raise ValidationError(
            "No se pudo leer el archivo Excel proporcionado."
        ) from exc

    rows: list[dict[str, Any]] = []
    recognized_sheets = 0
    try:
        for worksheet in workbook.worksheets:
            header_cells = next(worksheet.iter_rows(min_row=1, max_row=1), ())
            headers = [_normalized_header(cell.value) for cell in header_cells]
            if not any(header in KNOWN_HEADER_KEYS for header in headers):
                continue
            recognized_sheets += 1
            for row_number, cells in enumerate(worksheet.iter_rows(min_row=2), start=2):
                if not any(cell.value is not None for cell in cells):
                    continue
                payload: dict[str, Any] = {}
                errors: list[str] = []
                for index, cell in enumerate(cells):
                    header = headers[index] if index < len(headers) else ""
                    key = header or f"column_{index + 1}"
                    payload[key] = _json_value(cell.value)
                    if cell.data_type == "e" or (
                        isinstance(cell.value, str) and cell.value.startswith("#")
                    ):
                        errors.append(f"{key}: error de fórmula o valor Excel inválido")
                rows.append(
                    {
                        "sheet_name": worksheet.title,
                        "row_number": row_number,
                        "source_coordinate": f"{worksheet.title}!{row_number}",
                        "payload": payload,
                        "errors": errors,
                    }
                )
    finally:
        workbook.close()
    if recognized_sheets == 0:
        raise ValidationError(
            "El archivo no contiene encabezados de ventas reconocidos."
        )
    return rows


def _preview_counts(records: Iterable[SourceRecord]) -> dict[str, int]:
    values = list(records)
    return {
        "row_count": len(values),
        "error_count": sum(
            record.classification == SourceRecordClassification.ERROR
            for record in values
        ),
        "warning_count": sum(
            record.classification == SourceRecordClassification.WARNING
            for record in values
        ),
        "duplicate_count": sum(
            record.classification == SourceRecordClassification.DUPLICATE
            for record in values
        ),
        "unmatched_count": sum(
            record.classification == SourceRecordClassification.UNMATCHED
            for record in values
        ),
        "canonical_diff_count": sum(bool(record.canonical_links) for record in values),
    }


def _as_preview(batch: ImportBatch, *, reused: bool) -> ImportPreview:
    counts = batch.preview_counts
    return ImportPreview(
        batch=batch,
        reused=reused,
        row_count=counts.get("row_count", 0),
        error_count=counts.get("error_count", 0),
        warning_count=counts.get("warning_count", 0),
        duplicate_count=counts.get("duplicate_count", 0),
        unmatched_count=counts.get("unmatched_count", 0),
        canonical_diff_count=counts.get("canonical_diff_count", 0),
    )


@transaction.atomic
def preview_workbook(
    *,
    actor: IdentityProfile,
    filename: str,
    content: bytes,
    parser_version: str = DEFAULT_PARSER_VERSION,
    application_version: str = DEFAULT_APPLICATION_VERSION,
) -> ImportPreview:
    _require_steward(actor, Action.IMPORT)
    safe_filename = safe_upload_filename(filename)
    if not content:
        raise ValidationError("El archivo está vacío.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValidationError("El archivo supera el tamaño máximo permitido de 10 MB.")
    digest = _checksum(content)
    existing = ImportBatch.objects.filter(
        checksum=digest,
        parser_version=parser_version,
        application_version=application_version,
    ).first()
    if existing is not None:
        record_metric("imports.preview.reused")
        record_event("imports.preview", component="import", outcome="reused")
        return _as_preview(existing, reused=True)

    staged_rows = _workbook_rows(content)
    document, _ = SourceDocument.objects.get_or_create(
        checksum=digest,
        defaults={
            "filename": safe_filename,
            "size_bytes": len(content),
            "content": content,
            "uploaded_by": actor.user,
        },
    )
    batch = ImportBatch.objects.create(
        source_document=document,
        checksum=digest,
        parser_version=parser_version,
        application_version=application_version,
        status=ImportStatus.STAGED,
        import_actor=actor.user,
    )
    seen_row_checksums: set[str] = set()
    for row in staged_rows:
        row_checksum = _checksum(
            json.dumps(row["payload"], sort_keys=True, ensure_ascii=False).encode()
        )
        errors = row["errors"]
        if errors:
            classification = SourceRecordClassification.ERROR
        elif row_checksum in seen_row_checksums:
            classification = SourceRecordClassification.DUPLICATE
        else:
            classification = SourceRecordClassification.NEW
        seen_row_checksums.add(row_checksum)
        SourceRecord.objects.create(
            batch=batch,
            sheet_name=row["sheet_name"],
            row_number=row["row_number"],
            source_coordinate=row["source_coordinate"],
            raw_payload=row["payload"],
            raw_checksum=row_checksum,
            classification=classification,
            errors=errors,
            warnings=[],
            rejection_reason="; ".join(errors),
        )
    records = list(batch.source_records.all())
    batch.preview_counts = _preview_counts(records)
    batch.save(update_fields=("preview_counts", "updated_at"))
    ImportAuditEvent.objects.create(
        batch=batch,
        actor=actor.user,
        action="uploaded",
        details={
            "filename": safe_filename,
            "checksum": digest,
            **batch.preview_counts,
        },
    )
    record_metric("imports.preview.completed")
    record_event(
        "imports.preview",
        component="import",
        outcome="staged",
        row_count=batch.preview_counts.get("row_count", 0),
    )
    return _as_preview(batch, reused=False)


@transaction.atomic
def approve_import(
    *, actor: IdentityProfile, batch: ImportBatch, reason: str
) -> ImportBatch:
    _require_steward(actor, Action.IMPORT)
    if not reason.strip():
        raise ValidationError("La aprobación requiere un motivo.")
    locked = ImportBatch.objects.select_for_update().get(pk=batch.pk)
    if locked.status not in {
        ImportStatus.STAGED,
        ImportStatus.VALIDATED,
        ImportStatus.CANDIDATE_MATCHED,
    }:
        raise ValidationError("El lote no está disponible para aprobación.")
    locked.status = ImportStatus.APPROVED
    locked.approved_by = actor.user
    locked.approved_at = timezone.now()
    locked.save(update_fields=("status", "approved_by", "approved_at", "updated_at"))
    ImportAuditEvent.objects.create(
        batch=locked,
        actor=actor.user,
        action="approved",
        reason=reason.strip(),
        details={"status": locked.status},
    )
    record_metric("imports.apply.completed")
    record_event("imports.apply", component="import", outcome="applied")
    return locked


@transaction.atomic
def apply_import(
    *, actor: IdentityProfile, batch: ImportBatch, reason: str
) -> ImportBatch:
    _require_steward(actor, Action.IMPORT)
    if not reason.strip():
        raise ValidationError("La aplicación requiere un motivo.")
    locked = ImportBatch.objects.select_for_update().get(pk=batch.pk)
    if locked.status != ImportStatus.APPROVED:
        raise ValidationError("El lote debe aprobarse antes de aplicarse.")
    locked.status = ImportStatus.APPLYING
    locked.save(update_fields=("status", "updated_at"))
    # Canonical creation/correction is deliberately deferred to the governed
    # CRM-011/CRM-021 workflows. Applying here commits the approved staged
    # state and lineage atomically without guessing ambiguous business values.
    locked.source_records.update(classification=SourceRecordClassification.APPLIED)
    locked.status = ImportStatus.APPLIED
    locked.applied_at = timezone.now()
    locked.save(update_fields=("status", "applied_at", "updated_at"))
    ImportAuditEvent.objects.create(
        batch=locked,
        actor=actor.user,
        action="applied",
        reason=reason.strip(),
        details={"status": locked.status, "canonical_writes": 0},
    )
    return locked


@dataclass(frozen=True)
class MergePreview:
    survivor: Party
    candidate: Party
    lead_links: tuple[LeadParty, ...]
    interactions: tuple[Interaction, ...]
    tasks: tuple[Task, ...]
    contact_links: tuple[PartyContactPoint, ...]
    aliases: tuple[PartyAlias, ...]
    source_links: tuple[SourceCanonicalLink, ...]


def _require_quality_access(actor: IdentityProfile) -> None:
    steward = (
        actor.role_assignments.filter(
            role__code__in=("data_steward", "system_administrator"),
            role__is_active=True,
            starts_at__lte=timezone.now(),
        )
        .filter(models_q_ends_at())
        .exists()
    )
    if (
        not actor.is_enabled
        or not steward
        or not can_access(actor, Action.RESOLVE_QUALITY, ScopeSpec.global_scope())
    ):
        raise PermissionDenied("Sólo un responsable de datos puede operar calidad.")


def quality_issue_queue(actor: IdentityProfile) -> QuerySet[QualityIssue]:
    _require_quality_access(actor)
    from django.db.models import Case, IntegerField, Value, When

    return QualityIssue.objects.order_by(
        Case(
            When(severity=QualitySeverity.ERROR, then=Value(0)),
            When(severity=QualitySeverity.WARNING, then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        ),
        "created_at",
        "pk",
    )


@transaction.atomic
def create_quality_issue(
    *,
    actor: IdentityProfile,
    rule_code: str,
    severity: str,
    source_record: SourceRecord | None = None,
    target_type: str = "",
    target_id: str = "",
    owner: IdentityProfile | None = None,
) -> QualityIssue:
    _require_quality_access(actor)
    if severity not in QualitySeverity.values:
        raise ValidationError("La severidad de calidad no es válida.")
    issue = QualityIssue.objects.create(
        rule_code=rule_code,
        severity=severity,
        source_record=source_record,
        target_type=target_type,
        target_id=target_id,
        owner=owner,
    )
    QualityAuditEvent.objects.create(
        action="issue_created",
        actor=actor.user,
        target_type="QualityIssue",
        target_id=str(issue.pk),
        reason="Creación de incidencia",
        before_state={},
        after_state={"state": issue.state, "severity": issue.severity},
        source_evidence={
            "source_record_id": source_record.pk if source_record else None
        },
    )
    return issue


@transaction.atomic
def change_issue_state(
    *,
    actor: IdentityProfile,
    issue: QualityIssue,
    state: str,
    reason: str,
    decision: str = "",
) -> QualityIssue:
    _require_quality_access(actor)
    if state not in QualityIssueState.values:
        raise ValidationError("El estado de calidad no es válido.")
    if not reason.strip():
        raise ValidationError("El cambio de calidad requiere un motivo.")
    locked = QualityIssue.objects.select_for_update().get(pk=issue.pk)
    allowed: dict[str, set[str]] = {
        QualityIssueState.OPEN: {
            QualityIssueState.RESOLVED,
            QualityIssueState.ACCEPTED,
        },
        QualityIssueState.REOPENED: {
            QualityIssueState.RESOLVED,
            QualityIssueState.ACCEPTED,
        },
        QualityIssueState.RESOLVED: {QualityIssueState.REOPENED},
        QualityIssueState.ACCEPTED: {QualityIssueState.REOPENED},
    }
    if state not in allowed.get(locked.state, set()):
        raise ValidationError("La transición de la incidencia no es válida.")
    before = {"state": locked.state, "decision": locked.decision}
    locked.state = state
    locked.decision = decision.strip()
    locked.acceptance_reason = (
        reason.strip() if state == QualityIssueState.ACCEPTED else ""
    )
    locked.resolved_at = (
        timezone.now()
        if state in {QualityIssueState.RESOLVED, QualityIssueState.ACCEPTED}
        else None
    )
    locked.save()
    QualityAuditEvent.objects.create(
        action="issue_state_changed",
        actor=actor.user,
        target_type="QualityIssue",
        target_id=str(locked.pk),
        reason=reason.strip(),
        before_state=before,
        after_state={"state": locked.state, "decision": locked.decision},
        source_evidence={
            "source_record_id": locked.source_record_id,
            "target_type": locked.target_type,
            "target_id": locked.target_id,
        },
    )
    return locked


def _ordered_parties(first: Party, second: Party) -> tuple[Party, Party]:
    if first.pk is None or second.pk is None or first.pk == second.pk:
        raise ValidationError("Se requieren dos partes distintas.")
    return (first, second) if first.pk < second.pk else (second, first)


@transaction.atomic
def find_exact_candidates(
    *, actor: IdentityProfile, kind: str, normalized_value: str
) -> list[CandidateMatch]:
    _require_quality_access(actor)
    points = ContactPoint.objects.filter(
        kind=kind,
        normalized_value=normalized_value,
        is_active=True,
    ).prefetch_related("party_links__party")
    parties: list[Party] = []
    for point in points:
        parties.extend(
            link.party
            for link in point.party_links.all()
            if link.party.lifecycle == PartyLifecycle.ACTIVE
        )
    matches: list[CandidateMatch] = []
    match_type = {
        "EMAIL": MatchType.EXACT_EMAIL,
        "PHONE": MatchType.EXACT_PHONE,
        "WHATSAPP": MatchType.EXACT_PHONE,
    }.get(kind, MatchType.EXACT_SOURCE)
    for index, first in enumerate(parties):
        for second in parties[index + 1 :]:
            survivor, candidate = _ordered_parties(first, second)
            match, _ = CandidateMatch.objects.get_or_create(
                survivor=survivor,
                candidate=candidate,
                match_type=match_type,
                defaults={
                    "confidence": Decimal("1.0000"),
                    "evidence": {"kind": kind, "normalized_value": normalized_value},
                },
            )
            matches.append(match)
    return matches


@transaction.atomic
def find_fuzzy_candidate(
    *, actor: IdentityProfile, first: Party, second: Party, threshold: float = 0.84
) -> CandidateMatch:
    _require_quality_access(actor)
    if (
        first.lifecycle != PartyLifecycle.ACTIVE
        or second.lifecycle != PartyLifecycle.ACTIVE
    ):
        raise ValidationError("Sólo se comparan partes activas.")
    first_key = comparison_key(first.display_name)
    second_key = comparison_key(second.display_name)
    confidence = SequenceMatcher(None, first_key, second_key).ratio()
    if confidence < threshold:
        raise ValidationError("La similitud no alcanza el umbral de revisión.")
    survivor, candidate = _ordered_parties(first, second)
    match, _ = CandidateMatch.objects.get_or_create(
        survivor=survivor,
        candidate=candidate,
        match_type=(
            MatchType.FUZZY_ORGANIZATION
            if first.party_type == PartyType.ORGANIZATION
            and second.party_type == PartyType.ORGANIZATION
            else MatchType.FUZZY_NAME
        ),
        defaults={
            "confidence": round(confidence, 4),
            "evidence": {
                "first_name": first.display_name,
                "second_name": second.display_name,
                "algorithm": "SequenceMatcher",
                "threshold": threshold,
            },
        },
    )
    return match


@transaction.atomic
def review_candidate(
    *, actor: IdentityProfile, candidate: CandidateMatch, state: str, reason: str
) -> CandidateMatch:
    _require_quality_access(actor)
    if state not in {MatchState.APPROVED, MatchState.REJECTED}:
        raise ValidationError("La decisión de coincidencia no es válida.")
    if not reason.strip():
        raise ValidationError("La decisión requiere un motivo.")
    locked = CandidateMatch.objects.select_for_update().get(pk=candidate.pk)
    if locked.state != MatchState.REVIEW:
        raise ValidationError("El candidato ya fue decidido.")
    before = {"state": locked.state}
    locked.state = state
    locked.reviewed_by = actor.user
    locked.reviewed_at = timezone.now()
    locked.review_reason = reason.strip()
    locked.save(update_fields=("state", "reviewed_by", "reviewed_at", "review_reason"))
    QualityAuditEvent.objects.create(
        action="candidate_reviewed",
        actor=actor.user,
        target_type="CandidateMatch",
        target_id=str(locked.pk),
        reason=reason.strip(),
        before_state=before,
        after_state={"state": locked.state},
        source_evidence=locked.evidence,
    )
    return locked


def preview_merge(*, actor: IdentityProfile, candidate: CandidateMatch) -> MergePreview:
    _require_quality_access(actor)
    locked = CandidateMatch.objects.select_related("survivor", "candidate").get(
        pk=candidate.pk
    )
    lead_links = tuple(
        LeadParty.objects.filter(party=locked.candidate).select_related("lead", "party")
    )
    interaction_links = tuple(
        InteractionParticipant.objects.filter(party=locked.candidate).select_related(
            "interaction"
        )
    )
    interactions = tuple(link.interaction for link in interaction_links)
    tasks = tuple(
        Task.objects.filter(lead_id__in=[link.lead_id for link in lead_links])
    )
    return MergePreview(
        survivor=locked.survivor,
        candidate=locked.candidate,
        lead_links=lead_links,
        interactions=interactions,
        tasks=tasks,
        contact_links=tuple(
            PartyContactPoint.objects.filter(party=locked.candidate).select_related(
                "contact_point"
            )
        ),
        aliases=tuple(PartyAlias.objects.filter(party=locked.candidate)),
        source_links=tuple(
            SourceCanonicalLink.objects.filter(
                target_type__iexact="Party", target_id=str(locked.candidate.pk)
            )
        ),
    )


@transaction.atomic
def merge_approved_candidate(
    *, actor: IdentityProfile, candidate: CandidateMatch, reason: str
) -> Party:
    _require_quality_access(actor)
    if not reason.strip():
        raise ValidationError("La fusión requiere un motivo.")
    locked_match = (
        CandidateMatch.objects.select_for_update()
        .select_related("survivor", "candidate")
        .get(pk=candidate.pk)
    )
    if locked_match.state != MatchState.APPROVED:
        raise ValidationError("La coincidencia debe aprobarse antes de fusionar.")
    survivor = Party.objects.select_for_update().get(pk=locked_match.survivor_id)
    duplicate = Party.objects.select_for_update().get(pk=locked_match.candidate_id)
    if duplicate.lifecycle != PartyLifecycle.ACTIVE:
        raise ValidationError("La parte candidata ya está archivada.")
    lead_links = list(LeadParty.objects.filter(party=duplicate))
    for link in lead_links:
        if LeadParty.objects.filter(
            lead_id=link.lead_id, party=survivor, party_role=link.party_role
        ).exists():
            raise ValidationError("La fusión tiene un vínculo de lead en conflicto.")
    participant_links = list(InteractionParticipant.objects.filter(party=duplicate))
    for participant_link in participant_links:
        if InteractionParticipant.objects.filter(
            interaction_id=participant_link.interaction_id,
            party=survivor,
            participant_role=participant_link.participant_role,
        ).exists():
            raise ValidationError("La fusión tiene un participante en conflicto.")
    before = {
        "survivor_id": survivor.pk,
        "candidate_id": duplicate.pk,
        "lead_count": len(lead_links),
        "interaction_count": len(participant_links),
        "contact_count": PartyContactPoint.objects.filter(party=duplicate).count(),
        "alias_count": PartyAlias.objects.filter(party=duplicate).count(),
    }
    for contact_link in PartyContactPoint.objects.filter(party=duplicate):
        PartyContactPoint.objects.get_or_create(
            party=survivor,
            contact_point=contact_link.contact_point,
            defaults={
                "purpose": contact_link.purpose,
                "is_primary": contact_link.is_primary,
                "is_verified": contact_link.is_verified,
                "verification_note": contact_link.verification_note,
            },
        )
    PartyContactPoint.objects.filter(party=duplicate).delete()
    for lead_link in lead_links:
        lead_link.party = survivor
        lead_link.save(update_fields=("party",))
    for participant_link in participant_links:
        participant_link.party = survivor
        participant_link.save(update_fields=("party",))
    PartyAlias.objects.get_or_create(
        party=survivor,
        alias_normalized=comparison_key(duplicate.display_name),
        alias_type="MERGED_FROM",
        defaults={
            "alias_value": duplicate.display_name,
            "provenance": {"merged_party_id": duplicate.pk},
        },
    )
    for source_link in SourceCanonicalLink.objects.filter(
        target_type__iexact="Party", target_id=str(duplicate.pk)
    ):
        SourceCanonicalLink.objects.get_or_create(
            source_record=source_link.source_record,
            target_type=source_link.target_type,
            target_id=str(survivor.pk),
            relation=source_link.relation,
            defaults={
                "evidence": {
                    **source_link.evidence,
                    "merged_from_party_id": duplicate.pk,
                }
            },
        )
    duplicate.archive(expected_version=duplicate.version)
    locked_match.state = MatchState.APPLIED
    locked_match.save(update_fields=("state",))
    after = {
        "survivor_id": survivor.pk,
        "candidate_id": duplicate.pk,
        "candidate_lifecycle": duplicate.lifecycle,
        "lead_count": len(lead_links),
        "interaction_count": len(participant_links),
    }
    QualityAuditEvent.objects.create(
        action="party_merged",
        actor=actor.user,
        target_type="PartyMerge",
        target_id=str(duplicate.pk),
        reason=reason.strip(),
        before_state=before,
        after_state=after,
        source_evidence=locked_match.evidence,
    )
    return survivor
