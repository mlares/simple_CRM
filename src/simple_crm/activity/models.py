"""Interactions, tasks, and the activity timeline domain."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class InteractionDirection(models.TextChoices):
    OUTBOUND = "OUTBOUND", "Saliente"
    INBOUND = "INBOUND", "Entrante"


class InteractionResult(models.TextChoices):
    ATTEMPTED = "ATTEMPTED", "Intento de contacto"
    COMPLETED = "COMPLETED", "Contacto completado"
    RESPONSE = "RESPONSE", "Respuesta"


class TaskStatus(models.TextChoices):
    OPEN = "OPEN", "Abierta"
    COMPLETED = "COMPLETED", "Completada"
    RESCHEDULED = "RESCHEDULED", "Reprogramada"
    CANCELLED = "CANCELLED", "Cancelada"


class TaskPriority(models.TextChoices):
    LOW = "LOW", "Baja"
    NORMAL = "NORMAL", "Normal"
    HIGH = "HIGH", "Alta"


NON_EVENT_TEXT = frozenset(
    {
        "sin accion",
        "sin acción",
        "sin accion.",
        "sin acción.",
        "sin contacto",
        "sin contacto.",
    }
)


class Interaction(models.Model):
    lead = models.ForeignKey(
        "simple_crm_crm.Lead",
        on_delete=models.PROTECT,
        related_name="interactions",
    )
    occurrence_date = models.DateField()
    occurrence_time = models.TimeField(null=True, blank=True)
    direction = models.CharField(max_length=12, choices=InteractionDirection.choices)
    channel = models.ForeignKey(
        "simple_crm_crm.InteractionChannel",
        on_delete=models.PROTECT,
        related_name="interactions",
    )
    outcome = models.ForeignKey(
        "simple_crm_crm.InteractionOutcome",
        on_delete=models.PROTECT,
        related_name="interactions",
    )
    result = models.CharField(max_length=12, choices=InteractionResult.choices)
    note = models.TextField(blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="interactions_entered",
    )
    source = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-occurrence_date", "-occurrence_time", "-created_at", "-pk")
        verbose_name = "Interacción"
        verbose_name_plural = "Interacciones"
        constraints = [
            models.CheckConstraint(
                condition=Q(occurrence_date__isnull=False),
                name="activity_interaction_date_required",
            )
        ]

    def clean(self) -> None:
        if self.note.strip().casefold() in NON_EVENT_TEXT:
            raise ValidationError("La interacción debe describir un evento real.")

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)


class InteractionParticipant(models.Model):
    interaction = models.ForeignKey(
        Interaction, on_delete=models.PROTECT, related_name="participants"
    )
    party = models.ForeignKey(
        "simple_crm_crm.Party",
        on_delete=models.PROTECT,
        related_name="interaction_participations",
    )
    participant_role = models.CharField(max_length=32, default="CONTACT")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("interaction", "party", "participant_role"),
                name="activity_interaction_participant_unique",
            )
        ]
        verbose_name = "Participante de interacción"
        verbose_name_plural = "Participantes de interacción"


class Task(models.Model):
    lead = models.ForeignKey(
        "simple_crm_crm.Lead", on_delete=models.PROTECT, related_name="tasks"
    )
    owner = models.ForeignKey(
        "simple_crm_identity.IdentityProfile",
        on_delete=models.PROTECT,
        related_name="tasks",
    )
    description = models.CharField(max_length=300)
    due_date = models.DateField()
    status = models.CharField(
        max_length=16, choices=TaskStatus.choices, default=TaskStatus.OPEN
    )
    priority = models.CharField(
        max_length=12, choices=TaskPriority.choices, default=TaskPriority.NORMAL
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    completion_note = models.CharField(max_length=500, blank=True)
    rescheduled_at = models.DateTimeField(null=True, blank=True)
    reschedule_reason = models.CharField(max_length=500, blank=True)
    originating_interaction = models.ForeignKey(
        Interaction,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="follow_up_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("due_date", "-created_at", "-pk")
        verbose_name = "Tarea"
        verbose_name_plural = "Tareas"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(status=TaskStatus.COMPLETED, completed_at__isnull=False)
                    | Q(
                        status__in=(
                            TaskStatus.OPEN,
                            TaskStatus.RESCHEDULED,
                            TaskStatus.CANCELLED,
                        ),
                        completed_at__isnull=True,
                    )
                ),
                name="activity_task_completion_shape_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status=TaskStatus.RESCHEDULED, rescheduled_at__isnull=False)
                    | ~Q(status=TaskStatus.RESCHEDULED)
                ),
                name="activity_task_reschedule_date_valid",
            ),
        ]

    def clean(self) -> None:
        if self.status == TaskStatus.COMPLETED and self.completed_at is None:
            raise ValidationError(
                "Una tarea completada requiere fecha de finalización."
            )
        if self.status != TaskStatus.COMPLETED and self.completed_at is not None:
            raise ValidationError(
                "Una tarea abierta no puede tener fecha de finalización."
            )
        if self.status == TaskStatus.RESCHEDULED:
            if self.rescheduled_at is None or not self.reschedule_reason.strip():
                raise ValidationError(
                    "Una tarea reprogramada requiere fecha y motivo de reprogramación."
                )

    @property
    def is_open(self) -> bool:
        return self.status in {TaskStatus.OPEN, TaskStatus.RESCHEDULED}

    def is_overdue(self, *, today: date | None = None) -> bool:
        return self.is_open and self.due_date < (today or timezone.localdate())

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)


class ActivityAuditEvent(models.Model):
    lead = models.ForeignKey(
        "simple_crm_crm.Lead", on_delete=models.PROTECT, related_name="activity_audits"
    )
    interaction = models.ForeignKey(
        Interaction,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="audit_events",
    )
    task = models.ForeignKey(
        Task,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="audit_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="activity_audit_events",
    )
    action = models.CharField(max_length=64)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "pk")
        verbose_name = "Auditoría de actividad"
        verbose_name_plural = "Auditorías de actividad"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk:
            raise ValidationError("La auditoría de actividad es inmutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("La auditoría de actividad es inmutable.")
