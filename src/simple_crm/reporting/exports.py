"""Permissioned, bounded CSV/XLSX export requests and artifacts."""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook  # type: ignore[import-untyped]

from simple_crm.config.observability import record_event, record_metric
from simple_crm.identity.models import Action, IdentityProfile
from simple_crm.identity.policy import has_action_permission

from .models import ExportAuditEvent, ExportFormat, ExportRequest, ExportState
from .services import execute_definition, validate_definition

MAX_EXPORT_ROWS = 10_000
EXPIRY_HOURS = 24
FORMULA_PREFIXES = ("=", "+", "-", "@")


@dataclass(frozen=True)
class ExportField:
    label: str
    getter: Callable[[Any], object]


EXPORT_FIELDS: dict[str, ExportField] = {
    "lead_number": ExportField("Número de lead", lambda lead: lead.lead_number),
    "campaign_code": ExportField("Código de campaña", lambda lead: lead.campaign.code),
    "campaign_label": ExportField("Campaña", lambda lead: lead.campaign.label),
    "stage_code": ExportField("Código de etapa", lambda lead: lead.current_stage.code),
    "stage_label": ExportField("Etapa", lambda lead: lead.current_stage.label),
    "data_readiness": ExportField(
        "Preparación de datos", lambda lead: lead.get_data_readiness_display()
    ),
    "created_date": ExportField(
        "Fecha de creación", lambda lead: lead.created_at.date().isoformat()
    ),
    "source": ExportField(
        "Origen", lambda lead: str(lead.source_attribution.get("source", ""))
    ),
}


def _require_export_permission(actor: IdentityProfile) -> None:
    if not actor.is_enabled or not has_action_permission(actor, Action.BULK_EXPORT):
        raise PermissionDenied("No tiene autorización para exportar.")


def _safe_cell(value: object) -> object:
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value


def _audit(
    export_request: ExportRequest,
    actor: IdentityProfile,
    action: str,
    metadata: dict[str, object] | None = None,
) -> None:
    ExportAuditEvent.objects.create(
        export_request=export_request,
        actor=actor.user,
        action=action,
        metadata=metadata or {},
    )


def _denied_audit(
    actor: IdentityProfile, export_format: str, idempotency_key: str
) -> None:
    request = ExportRequest.objects.create(
        requested_by=actor,
        format=export_format
        if export_format in ExportFormat.values
        else ExportFormat.CSV,
        state=ExportState.FAILED,
        idempotency_key=f"denied:{idempotency_key}:{timezone.now().timestamp()}",
        reason="Solicitud denegada",
        last_error="PERMISSION_DENIED",
    )
    _audit(request, actor, "denied", {"reason": "missing_export_permission"})


def request_export(
    *,
    actor: IdentityProfile,
    definition: dict[str, Any],
    fields: list[str],
    export_format: str,
    idempotency_key: str,
    reason: str,
) -> ExportRequest:
    if not actor.is_enabled or not has_action_permission(actor, Action.BULK_EXPORT):
        _denied_audit(actor, export_format, idempotency_key)
        raise PermissionDenied("No tiene autorización para exportar.")
    if export_format not in ExportFormat.values:
        raise ValidationError("El formato de exportación no está permitido.")
    if not idempotency_key.strip() or len(idempotency_key) > 160:
        raise ValidationError("La clave de idempotencia no es válida.")
    if not reason.strip():
        raise ValidationError("La exportación requiere un motivo.")
    if (
        not fields
        or len(fields) > len(EXPORT_FIELDS)
        or any(field not in EXPORT_FIELDS for field in fields)
    ):
        raise ValidationError("Las columnas de exportación no están permitidas.")
    normalized = validate_definition(definition)
    existing = ExportRequest.objects.filter(idempotency_key=idempotency_key).first()
    if existing is not None:
        if (
            existing.requested_by_id != actor.pk
            or existing.definition_snapshot != normalized
            or existing.fields != fields
        ):
            raise ValidationError(
                "La clave de idempotencia ya pertenece a otra solicitud."
            )
        return existing
    request = ExportRequest.objects.create(
        requested_by=actor,
        format=export_format,
        idempotency_key=idempotency_key,
        definition_snapshot=normalized,
        fields=list(fields),
        scope_snapshot={"scope": "current_authorized_scope"},
        reason=reason.strip(),
    )
    _audit(
        request, actor, "requested", {"fields": list(fields), "format": export_format}
    )
    record_metric("exports.requested")
    record_event("exports.request", component="export", format=export_format)
    return request


def _rows(
    actor: IdentityProfile, request: ExportRequest
) -> tuple[list[str], list[list[object]]]:
    headers = [EXPORT_FIELDS[field].label for field in request.fields]
    values: list[list[object]] = []
    cursor = 0
    while len(values) < MAX_EXPORT_ROWS:
        page = execute_definition(
            actor=actor,
            definition=request.definition_snapshot,
            cursor=cursor,
            page_size=min(50, MAX_EXPORT_ROWS - len(values)),
        )
        for lead in page.results:
            values.append(
                [
                    _safe_cell(EXPORT_FIELDS[field].getter(lead))
                    for field in request.fields
                ]
            )
        if page.next_cursor is None:
            break
        cursor = page.next_cursor
    return headers, values


def _serialize(
    request: ExportRequest, headers: list[str], values: list[list[object]]
) -> bytes:
    if request.format == ExportFormat.CSV:
        stream = io.StringIO(newline="")
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(values)
        return stream.getvalue().encode("utf-8")
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Leads"
    sheet.append(headers)
    for row in values:
        sheet.append(row)
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


@transaction.atomic
def materialize_export(*, actor: IdentityProfile, export_id: int) -> ExportRequest:
    _require_export_permission(actor)
    request = ExportRequest.objects.select_for_update().get(pk=export_id)
    if request.requested_by_id != actor.pk and not has_action_permission(
        actor, Action.BULK_EXPORT
    ):
        raise PermissionDenied("No tiene autorización para procesar esta exportación.")
    if (
        request.state == ExportState.READY
        and request.expires_at
        and request.expires_at > timezone.now()
    ):
        return request
    request.state = ExportState.PROCESSING
    request.attempts += 1
    request.save(update_fields=("state", "attempts"))
    try:
        headers, values = _rows(actor, request)
        payload = _serialize(request, headers, values)
        request.file_payload = payload
        request.checksum = hashlib.sha256(payload).hexdigest()
        request.row_count = len(values)
        request.state = ExportState.READY
        request.completed_at = timezone.now()
        request.expires_at = timezone.now() + timedelta(hours=EXPIRY_HOURS)
        request.last_error = ""
        request.save(
            update_fields=(
                "file_payload",
                "checksum",
                "row_count",
                "state",
                "completed_at",
                "expires_at",
                "last_error",
            )
        )
        _audit(
            request,
            actor,
            "materialized",
            {"row_count": len(values), "checksum": request.checksum},
        )
        record_metric("exports.materialized")
        record_event(
            "exports.materialize",
            component="export",
            format=request.format,
            row_count=len(values),
        )
    except Exception:
        record_metric("exports.failed")
        record_event("exports.materialize", component="export", outcome="failed")
        request.state = ExportState.FAILED
        request.last_error = "No se pudo materializar la exportación."
        request.save(update_fields=("state", "last_error"))
        _audit(request, actor, "failed", {"reason": "materialization_error"})
        raise
    return request


def download_export(*, actor: IdentityProfile, export_id: int) -> HttpResponse:
    request = ExportRequest.objects.get(pk=export_id)
    if request.requested_by_id != actor.pk:
        _require_export_permission(actor)
    if (
        request.state != ExportState.READY
        or not request.expires_at
        or request.expires_at <= timezone.now()
    ):
        if request.state == ExportState.READY:
            request.state = ExportState.EXPIRED
            request.save(update_fields=("state",))
        raise PermissionDenied("La exportación no está disponible.")
    _audit(request, actor, "downloaded", {"row_count": request.row_count})
    content_type = (
        "text/csv; charset=utf-8"
        if request.format == ExportFormat.CSV
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    suffix = "csv" if request.format == ExportFormat.CSV else "xlsx"
    response = HttpResponse(request.file_payload, content_type=content_type)
    response["Content-Disposition"] = (
        f'attachment; filename="exportacion-{request.pk}.{suffix}"'
    )
    return response
