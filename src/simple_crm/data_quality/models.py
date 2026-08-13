"""Lossless source-document, import-batch, and lineage persistence."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ImportStatus(models.TextChoices):
    UPLOADED = "UPLOADED", "Subido"
    STAGED = "STAGED", "En staging"
    VALIDATED = "VALIDATED", "Validado"
    CANDIDATE_MATCHED = "CANDIDATE_MATCHED", "Candidatos identificados"
    APPROVED = "APPROVED", "Aprobado"
    APPLYING = "APPLYING", "Aplicando"
    APPLIED = "APPLIED", "Aplicado"
    RECONCILED = "RECONCILED", "Reconciliado"
    FAILED = "FAILED", "Fallido"


class SourceRecordClassification(models.TextChoices):
    NEW = "NEW", "Nuevo"
    UPDATE = "UPDATE", "Actualización"
    DUPLICATE = "DUPLICATE", "Duplicado"
    WARNING = "WARNING", "Advertencia"
    ERROR = "ERROR", "Error"
    UNMATCHED = "UNMATCHED", "Sin coincidencia"
    APPLIED = "APPLIED", "Aplicado"


class SourceDocument(models.Model):
    filename = models.CharField(max_length=255)
    content_type = models.CharField(
        max_length=120,
        default="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    size_bytes = models.PositiveIntegerField()
    checksum = models.CharField(max_length=64, unique=True)
    content = models.BinaryField()
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="source_documents_uploaded",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-uploaded_at", "-pk")
        verbose_name = "Documento fuente"
        verbose_name_plural = "Documentos fuente"


class ImportBatch(models.Model):
    source_document = models.ForeignKey(
        SourceDocument, on_delete=models.PROTECT, related_name="batches"
    )
    checksum = models.CharField(max_length=64)
    parser_version = models.CharField(max_length=80)
    application_version = models.CharField(max_length=80)
    status = models.CharField(
        max_length=24, choices=ImportStatus.choices, default=ImportStatus.UPLOADED
    )
    import_actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="import_batches_created",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="import_batches_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    error_summary = models.JSONField(default=dict)
    preview_counts = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("checksum", "parser_version", "application_version"),
                name="dq_import_batch_version_unique",
            )
        ]
        ordering = ("-created_at", "-pk")
        verbose_name = "Lote de importación"
        verbose_name_plural = "Lotes de importación"


class SourceRecord(models.Model):
    batch = models.ForeignKey(
        ImportBatch, on_delete=models.PROTECT, related_name="source_records"
    )
    sheet_name = models.CharField(max_length=120)
    row_number = models.PositiveIntegerField()
    source_coordinate = models.CharField(max_length=32)
    raw_payload = models.JSONField(default=dict)
    raw_checksum = models.CharField(max_length=64)
    classification = models.CharField(
        max_length=16,
        choices=SourceRecordClassification.choices,
        default=SourceRecordClassification.NEW,
    )
    errors = models.JSONField(default=list)
    warnings = models.JSONField(default=list)
    canonical_links = models.JSONField(default=list)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("batch", "sheet_name", "row_number"),
                name="dq_source_record_coordinate_unique",
            )
        ]
        ordering = ("sheet_name", "row_number", "pk")
        verbose_name = "Registro fuente"
        verbose_name_plural = "Registros fuente"


class SourceCanonicalLink(models.Model):
    source_record = models.ForeignKey(
        SourceRecord, on_delete=models.PROTECT, related_name="canonical_links_rows"
    )
    target_type = models.CharField(max_length=120)
    target_id = models.CharField(max_length=128)
    relation = models.CharField(max_length=40)
    evidence = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("source_record", "target_type", "target_id", "relation"),
                name="dq_source_canonical_link_unique",
            )
        ]
        verbose_name = "Vínculo fuente-canónico"
        verbose_name_plural = "Vínculos fuente-canónico"


class ImportAuditEvent(models.Model):
    batch = models.ForeignKey(
        ImportBatch, on_delete=models.PROTECT, related_name="audit_events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="import_audit_events",
    )
    action = models.CharField(max_length=32)
    reason = models.CharField(max_length=500, blank=True)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "pk")
        verbose_name = "Auditoría de importación"
        verbose_name_plural = "Auditorías de importación"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk:
            raise ValidationError("La auditoría de importación es inmutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("La auditoría de importación es inmutable.")


class QualitySeverity(models.TextChoices):
    ERROR = "ERROR", "Error"
    WARNING = "WARNING", "Advertencia"
    INFO = "INFO", "Información"


class QualityIssueState(models.TextChoices):
    OPEN = "OPEN", "Abierta"
    RESOLVED = "RESOLVED", "Resuelta"
    ACCEPTED = "ACCEPTED", "Aceptada"
    REOPENED = "REOPENED", "Reabierta"


class MatchType(models.TextChoices):
    EXACT_EMAIL = "EXACT_EMAIL", "Email exacto"
    EXACT_PHONE = "EXACT_PHONE", "Teléfono exacto"
    EXACT_SOURCE = "EXACT_SOURCE", "Identificador fuente exacto"
    FUZZY_NAME = "FUZZY_NAME", "Nombre similar"
    FUZZY_ORGANIZATION = "FUZZY_ORGANIZATION", "Organización similar"


class MatchState(models.TextChoices):
    REVIEW = "REVIEW", "En revisión"
    APPROVED = "APPROVED", "Aprobada"
    REJECTED = "REJECTED", "Rechazada"
    APPLIED = "APPLIED", "Aplicada"


class QualityIssue(models.Model):
    rule_code = models.CharField(max_length=80)
    severity = models.CharField(max_length=12, choices=QualitySeverity.choices)
    state = models.CharField(
        max_length=12, choices=QualityIssueState.choices, default=QualityIssueState.OPEN
    )
    source_record = models.ForeignKey(
        "SourceRecord",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="quality_issues",
    )
    target_type = models.CharField(max_length=120, blank=True)
    target_id = models.CharField(max_length=128, blank=True)
    owner = models.ForeignKey(
        "simple_crm_identity.IdentityProfile",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="quality_issues_owned",
    )
    decision = models.CharField(max_length=40, blank=True)
    acceptance_reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("severity", "created_at", "pk")
        indexes = [
            models.Index(fields=("state", "severity", "created_at")),
            models.Index(fields=("target_type", "target_id")),
        ]
        verbose_name = "Incidencia de calidad"
        verbose_name_plural = "Incidencias de calidad"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(state=QualityIssueState.ACCEPTED, acceptance_reason__gt="")
                    | ~models.Q(state=QualityIssueState.ACCEPTED)
                ),
                name="dq_accepted_issue_reason_required",
            )
        ]


class CandidateMatch(models.Model):
    survivor = models.ForeignKey(
        "simple_crm_crm.Party",
        on_delete=models.PROTECT,
        related_name="quality_survivor_candidates",
    )
    candidate = models.ForeignKey(
        "simple_crm_crm.Party",
        on_delete=models.PROTECT,
        related_name="quality_duplicate_candidates",
    )
    match_type = models.CharField(max_length=32, choices=MatchType.choices)
    confidence = models.DecimalField(max_digits=5, decimal_places=4)
    evidence = models.JSONField(default=dict)
    state = models.CharField(
        max_length=12, choices=MatchState.choices, default=MatchState.REVIEW
    )
    source_record = models.ForeignKey(
        "SourceRecord",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="candidate_matches",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="quality_matches_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("survivor", "candidate", "match_type"),
                name="dq_candidate_match_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(confidence__gte=0, confidence__lte=1),
                name="dq_candidate_confidence_range",
            ),
        ]
        ordering = ("-confidence", "created_at", "pk")
        verbose_name = "Candidato de coincidencia"
        verbose_name_plural = "Candidatos de coincidencia"


class QualityAuditEvent(models.Model):
    action = models.CharField(max_length=40)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="quality_audit_events",
    )
    target_type = models.CharField(max_length=120)
    target_id = models.CharField(max_length=128)
    reason = models.CharField(max_length=500)
    before_state = models.JSONField(default=dict)
    after_state = models.JSONField(default=dict)
    source_evidence = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "pk")
        verbose_name = "Auditoría de calidad"
        verbose_name_plural = "Auditorías de calidad"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk:
            raise ValidationError("La auditoría de calidad es inmutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("La auditoría de calidad es inmutable.")


class GovernanceAuditEvent(models.Model):
    """Safe append-only cross-feature governance evidence."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="governance_audit_events",
    )
    action = models.CharField(max_length=48)
    target_type = models.CharField(max_length=120)
    target_id = models.CharField(max_length=128)
    request_correlation = models.CharField(max_length=120, blank=True)
    reason = models.CharField(max_length=500, blank=True)
    before_state = models.JSONField(default=dict)
    after_state = models.JSONField(default=dict)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "pk")
        indexes = [models.Index(fields=("target_type", "target_id", "created_at"))]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk:
            raise ValidationError("La auditoría de gobernanza es inmutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("La auditoría de gobernanza es inmutable.")


class PrivacyCaseType(models.TextChoices):
    ACCESS = "ACCESS", "Acceso"
    CORRECTION = "CORRECTION", "Corrección"
    SUPPRESSION = "SUPPRESSION", "Supresión"
    RETENTION = "RETENTION", "Retención"


class PrivacyCaseState(models.TextChoices):
    OPEN = "OPEN", "Abierto"
    APPROVED = "APPROVED", "Aprobado"
    COMPLETED = "COMPLETED", "Completado"
    REJECTED = "REJECTED", "Rechazado"


class PrivacyCase(models.Model):
    subject = models.ForeignKey(
        "simple_crm_crm.Party", on_delete=models.PROTECT, related_name="privacy_cases"
    )
    requested_by = models.ForeignKey(
        "simple_crm_identity.IdentityProfile",
        on_delete=models.PROTECT,
        related_name="privacy_cases_requested",
    )
    case_type = models.CharField(max_length=16, choices=PrivacyCaseType.choices)
    state = models.CharField(
        max_length=12, choices=PrivacyCaseState.choices, default=PrivacyCaseState.OPEN
    )
    reason = models.CharField(max_length=500)
    decision_reason = models.CharField(max_length=500, blank=True)
    request_correlation = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")


class RetentionCategory(models.Model):
    code = models.CharField(max_length=60, unique=True)
    label = models.CharField(max_length=160)
    retention_days = models.PositiveIntegerField()
    purpose = models.CharField(max_length=300)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("code",)


class LegalHold(models.Model):
    target_type = models.CharField(max_length=120)
    target_id = models.CharField(max_length=128)
    reason = models.CharField(max_length=500)
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="legal_holds_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)


class RetentionDecisionState(models.TextChoices):
    PREVIEWED = "PREVIEWED", "Previsualizada"
    APPROVED = "APPROVED", "Aprobada"
    EXECUTED = "EXECUTED", "Ejecutada"


class RetentionDecision(models.Model):
    target_type = models.CharField(max_length=120)
    target_id = models.CharField(max_length=128)
    category = models.ForeignKey(
        RetentionCategory, on_delete=models.PROTECT, related_name="decisions"
    )
    state = models.CharField(
        max_length=12,
        choices=RetentionDecisionState.choices,
        default=RetentionDecisionState.PREVIEWED,
    )
    preview = models.JSONField(default=dict)
    legal_hold_excluded = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="retention_decisions_approved",
    )
    reason = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
