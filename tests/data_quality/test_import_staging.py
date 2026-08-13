from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from openpyxl import Workbook

from simple_crm.crm.models import Lead, Party
from simple_crm.data_quality.models import (
    ImportAuditEvent,
    ImportStatus,
    SourceDocument,
    SourceRecord,
    SourceRecordClassification,
)
from simple_crm.data_quality.services import (
    MAX_UPLOAD_BYTES,
    apply_import,
    approve_import,
    preview_workbook,
)
from simple_crm.identity.models import (
    IdentityProfile,
    Role,
    RoleAssignment,
    ScopeGrant,
    ScopeType,
)


def _actor(username: str, role_code: str) -> IdentityProfile:
    user = get_user_model().objects.create_user(username=username, password="safe-pass")
    profile = IdentityProfile.objects.get(user=user)
    RoleAssignment.objects.create(
        identity=profile, role=Role.objects.get(code=role_code)
    )
    ScopeGrant.objects.create(identity=profile, scope_type=ScopeType.GLOBAL)
    return profile


def _xlsx(headers: list[str], rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Leads"
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


@pytest.mark.django_db
def test_preview_stages_rows_without_touching_canonical_business_data() -> None:
    steward = _actor("steward-preview", "data_steward")
    content = _xlsx(
        ["Organization", "Email", "Fecha contacto"],
        [
            ["Hospital Central", "ventas@hospital.test", "2026-08-11"],
            ["Clínica Sur", None, None],
        ],
    )

    preview = preview_workbook(
        actor=steward,
        filename="prospects.xlsx",
        content=content,
    )

    assert preview.reused is False
    assert preview.batch.status == ImportStatus.STAGED
    assert preview.row_count == 2
    assert preview.batch.source_document.size_bytes == len(content)
    record = SourceRecord.objects.get(batch=preview.batch, row_number=2)
    assert record.sheet_name == "Leads"
    assert record.source_coordinate == "Leads!2"
    assert record.raw_payload["organization"] == "Hospital Central"
    assert Party.objects.count() == 0
    assert Lead.objects.count() == 0
    assert ImportAuditEvent.objects.filter(
        batch=preview.batch, action="uploaded"
    ).exists()


@pytest.mark.django_db
def test_same_checksum_parser_and_application_version_is_idempotent() -> None:
    steward = _actor("steward-idempotent", "data_steward")
    content = _xlsx(["organization", "email"], [["Hospital Norte", "norte@test"]])

    first = preview_workbook(actor=steward, filename="same.xlsx", content=content)
    second = preview_workbook(actor=steward, filename="same-copy.xlsx", content=content)

    assert second.reused is True
    assert second.batch.pk == first.batch.pk
    assert ImportBatchCount(first.batch.pk) == 1
    assert SourceDocument.objects.count() == 1
    assert (
        ImportAuditEvent.objects.filter(batch=first.batch, action="uploaded").count()
        == 1
    )


def ImportBatchCount(batch_id: int) -> int:
    return SourceRecord.objects.filter(batch_id=batch_id).count()


@pytest.mark.django_db
def test_formula_errors_and_malformed_uploads_are_retained_or_rejected_safely() -> None:
    steward = _actor("steward-errors", "data_steward")
    formula_error = _xlsx(["organization", "email"], [["Hospital Error", "#REF!"]])
    preview = preview_workbook(
        actor=steward, filename="formula.xlsx", content=formula_error
    )
    record = SourceRecord.objects.get(batch=preview.batch)
    assert record.classification == SourceRecordClassification.ERROR
    assert record.errors
    assert record.raw_payload["email"] == "#REF!"

    with pytest.raises(ValidationError, match="encabezados"):
        preview_workbook(
            actor=steward,
            filename="unexpected.xlsx",
            content=_xlsx(["unknown column"], [["value"]]),
        )
    with pytest.raises(ValidationError, match="leer"):
        preview_workbook(actor=steward, filename="broken.xlsx", content=b"not an xlsx")
    with pytest.raises(ValidationError, match="10 MB"):
        preview_workbook(
            actor=steward,
            filename="large.xlsx",
            content=b"x" * (MAX_UPLOAD_BYTES + 1),
        )
    assert SourceDocument.objects.count() == 1


@pytest.mark.django_db
def test_only_data_steward_can_approve_and_apply_with_separate_audits() -> None:
    steward = _actor("steward-approve", "data_steward")
    manager = _actor("manager-approve", "sales_manager")
    content = _xlsx(["organization"], [["Hospital Aprobado"]])
    preview = preview_workbook(actor=steward, filename="approval.xlsx", content=content)

    with pytest.raises(PermissionDenied):
        approve_import(actor=manager, batch=preview.batch, reason="No corresponde")
    with pytest.raises(ValidationError, match="motivo"):
        approve_import(actor=steward, batch=preview.batch, reason=" ")

    approved = approve_import(
        actor=steward, batch=preview.batch, reason="Revisión del responsable de datos"
    )
    assert approved.status == ImportStatus.APPROVED
    with pytest.raises(PermissionDenied):
        apply_import(actor=manager, batch=approved, reason="No corresponde")

    applied = apply_import(actor=steward, batch=approved, reason="Aplicación aprobada")
    assert applied.status == ImportStatus.APPLIED
    assert (
        SourceRecord.objects.get(batch=applied).classification
        == SourceRecordClassification.APPLIED
    )
    assert list(
        ImportAuditEvent.objects.filter(batch=applied).values_list("action", flat=True)
    ) == ["uploaded", "approved", "applied"]


@pytest.mark.django_db
def test_import_audit_is_append_only_and_apply_requires_approval() -> None:
    steward = _actor("steward-audit", "data_steward")
    preview = preview_workbook(
        actor=steward,
        filename="audit.xlsx",
        content=_xlsx(["organization"], [["Hospital Audit"]]),
    )
    with pytest.raises(ValidationError, match="aprobarse"):
        apply_import(actor=steward, batch=preview.batch, reason="Intento")
    audit = ImportAuditEvent.objects.get(batch=preview.batch)
    with pytest.raises(ValidationError, match="inmutable"):
        audit.save()
