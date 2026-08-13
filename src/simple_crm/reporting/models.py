"""Persisted, structured reporting views."""

from __future__ import annotations

from datetime import date
from typing import Any, cast

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class SavedViewVisibility(models.TextChoices):
    PRIVATE = "PRIVATE", "Privada"
    SHARED = "SHARED", "Compartida"


class SavedView(models.Model):
    """A versioned filter definition; never store executable SQL here."""

    owner = models.ForeignKey(
        "simple_crm_identity.IdentityProfile",
        on_delete=models.PROTECT,
        related_name="saved_views",
    )
    name = models.CharField(max_length=120)
    definition = models.JSONField(default=dict)
    visibility = models.CharField(
        max_length=12,
        choices=SavedViewVisibility.choices,
        default=SavedViewVisibility.PRIVATE,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="saved_views_approved",
    )
    version = models.PositiveIntegerField(default=1)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "pk")
        verbose_name = "Vista guardada"
        verbose_name_plural = "Vistas guardadas"
        constraints = [
            models.CheckConstraint(
                condition=Q(name__gt=""), name="reporting_saved_view_name_not_empty"
            ),
            models.CheckConstraint(
                condition=Q(visibility="PRIVATE") | Q(approved_by__isnull=False),
                name="reporting_shared_view_approved",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk:
            current = type(self).objects.get(pk=self.pk)
            if self.version != current.version:
                raise ValidationError("La vista cambió; recárguela antes de guardarla.")
            self.version += 1
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                fields = set(cast(Any, update_fields))
                fields.update(("version", "updated_at"))
                kwargs["update_fields"] = fields
        if not self.name.strip():
            raise ValidationError("La vista requiere un nombre.")
        if (
            self.visibility == SavedViewVisibility.SHARED
            and self.approved_by_id is None
        ):
            raise ValidationError("Una vista compartida requiere aprobación.")
        super().save(*args, **kwargs)


class MetricDefinition(models.Model):
    """Governed, versioned semantics displayed alongside every KPI."""

    code = models.CharField(max_length=60, unique=True)
    label = models.CharField(max_length=160)
    owner = models.CharField(max_length=160)
    description = models.TextField()
    numerator = models.CharField(max_length=300)
    denominator = models.CharField(max_length=300)
    inclusion_rules = models.JSONField(default=dict)
    timeframe_semantics = models.CharField(max_length=300)
    version = models.PositiveIntegerField(default=1)
    effective_from = models.DateField(default=date.today)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("code",)
        verbose_name = "Definición de métrica"
        verbose_name_plural = "Definiciones de métricas"
        constraints = [
            models.CheckConstraint(
                condition=Q(code__gt=""), name="reporting_metric_code_not_empty"
            ),
            models.CheckConstraint(
                condition=Q(label__gt=""), name="reporting_metric_label_not_empty"
            ),
        ]


class ExportFormat(models.TextChoices):
    CSV = "CSV", "CSV"
    XLSX = "XLSX", "XLSX"


class ExportState(models.TextChoices):
    PENDING = "PENDING", "Pendiente"
    PROCESSING = "PROCESSING", "Procesando"
    READY = "READY", "Lista"
    FAILED = "FAILED", "Fallida"
    EXPIRED = "EXPIRED", "Vencida"


class ExportRequest(models.Model):
    """Immutable request snapshot plus bounded materialized artifact state."""

    requested_by = models.ForeignKey(
        "simple_crm_identity.IdentityProfile",
        on_delete=models.PROTECT,
        related_name="export_requests",
    )
    format = models.CharField(max_length=8, choices=ExportFormat.choices)
    state = models.CharField(
        max_length=16, choices=ExportState.choices, default=ExportState.PENDING
    )
    idempotency_key = models.CharField(max_length=160, unique=True)
    definition_snapshot = models.JSONField(default=dict)
    fields = models.JSONField(default=list)
    scope_snapshot = models.JSONField(default=dict)
    reason = models.CharField(max_length=500, blank=True)
    file_payload = models.BinaryField(null=True, blank=True)
    checksum = models.CharField(max_length=64, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=500, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-requested_at", "-pk")
        verbose_name = "Solicitud de exportación"
        verbose_name_plural = "Solicitudes de exportación"


class ExportAuditEvent(models.Model):
    """Append-only export request, denial, materialization, and download log."""

    export_request = models.ForeignKey(
        ExportRequest, on_delete=models.PROTECT, related_name="audit_events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT
    )
    action = models.CharField(max_length=32)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "pk")

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk:
            raise ValidationError("La auditoría de exportaciones es inmutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("La auditoría de exportaciones es inmutable.")
