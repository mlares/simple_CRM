"""Durable platform jobs and notification preferences."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class JobType(models.TextChoices):
    REMINDER = "REMINDER", "Recordatorio"
    DIGEST = "DIGEST", "Resumen"


class JobState(models.TextChoices):
    PENDING = "PENDING", "Pendiente"
    CLAIMED = "CLAIMED", "Tomado por un trabajador"
    SUCCEEDED = "SUCCEEDED", "Completado"
    FAILED = "FAILED", "Reintento programado"
    DEAD = "DEAD", "Revisión requerida"
    CANCELLED = "CANCELLED", "Cancelado"


class OutboxJob(models.Model):
    """A safe, idempotent unit of work committed with its business change."""

    job_type = models.CharField(max_length=16, choices=JobType.choices)
    recipient = models.ForeignKey(
        "simple_crm_identity.IdentityProfile",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="outbox_jobs",
    )
    payload_reference = models.JSONField(default=dict)
    idempotency_key = models.CharField(max_length=220, unique=True)
    scheduled_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    state = models.CharField(
        max_length=16, choices=JobState.choices, default=JobState.PENDING
    )
    lease_until = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=300, blank=True)
    provider_idempotency_key = models.CharField(
        max_length=220, unique=True, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("scheduled_at", "created_at", "pk")
        indexes = [
            models.Index(
                fields=("state", "scheduled_at"),
                name="platform_job_poll_idx",
            ),
            models.Index(
                fields=("job_type", "state"),
                name="platform_job_review_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(attempts__lte=models.F("max_attempts")),
                name="platform_job_attempts_bounded",
            ),
            models.CheckConstraint(
                condition=Q(max_attempts__gte=1),
                name="platform_job_max_attempts_positive",
            ),
        ]
        verbose_name = "Trabajo de plataforma"
        verbose_name_plural = "Trabajos de plataforma"

    def clean(self) -> None:
        if not isinstance(self.payload_reference, dict):
            raise ValidationError("La referencia del trabajo debe ser un objeto.")
        if self.idempotency_key != self.idempotency_key.strip():
            raise ValidationError("La clave de idempotencia no puede tener espacios.")
        if self.provider_idempotency_key and self.state not in {
            JobState.PENDING,
            JobState.CLAIMED,
            JobState.SUCCEEDED,
            JobState.FAILED,
            JobState.DEAD,
            JobState.CANCELLED,
        }:
            raise ValidationError("La clave del proveedor no es válida en este estado.")

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)


class NotificationPreference(models.Model):
    """Per-identity defaults; escalation remains an explicitly restricted flag."""

    identity = models.OneToOneField(
        "simple_crm_identity.IdentityProfile",
        on_delete=models.PROTECT,
        related_name="notification_preferences",
    )
    digest_enabled = models.BooleanField(default=True)
    escalation_enabled = models.BooleanField(default=False)
    daily_digest_hour = models.PositiveSmallIntegerField(default=8)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Preferencia de notificación"
        verbose_name_plural = "Preferencias de notificación"
        constraints = [
            models.CheckConstraint(
                condition=Q(daily_digest_hour__gte=0) & Q(daily_digest_hour__lte=23),
                name="platform_digest_hour_valid",
            )
        ]

    def clean(self) -> None:
        if not 0 <= self.daily_digest_hour <= 23:
            raise ValidationError("La hora del resumen debe estar entre 0 y 23.")

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)


class NotificationDelivery(models.Model):
    """Internal provider-idempotency receipt; it contains no message body."""

    job = models.OneToOneField(
        OutboxJob,
        on_delete=models.PROTECT,
        related_name="delivery",
    )
    identity = models.ForeignKey(
        "simple_crm_identity.IdentityProfile",
        on_delete=models.PROTECT,
        related_name="notification_deliveries",
    )
    channel = models.CharField(max_length=24, default="IN_APP")
    provider_idempotency_key = models.CharField(max_length=220, unique=True)
    delivered_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Entrega de notificación"
        verbose_name_plural = "Entregas de notificaciones"

    def clean(self) -> None:
        if not isinstance(self.metadata, dict):
            raise ValidationError("Los metadatos de entrega deben ser un objeto.")

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)
