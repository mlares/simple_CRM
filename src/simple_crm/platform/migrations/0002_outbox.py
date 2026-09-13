"""Create the transactional outbox and notification preference tables."""

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("simple_crm_identity", "0002_seed_roles"),
        ("simple_crm_platform", "0001_enable_pg_trgm"),
    ]

    operations = [
        migrations.CreateModel(
            name="OutboxJob",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "job_type",
                    models.CharField(
                        choices=[("REMINDER", "Recordatorio"), ("DIGEST", "Resumen")],
                        max_length=16,
                    ),
                ),
                ("payload_reference", models.JSONField(default=dict)),
                ("idempotency_key", models.CharField(max_length=220, unique=True)),
                ("scheduled_at", models.DateTimeField()),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("max_attempts", models.PositiveSmallIntegerField(default=5)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pendiente"),
                            ("CLAIMED", "Tomado por un trabajador"),
                            ("SUCCEEDED", "Completado"),
                            ("FAILED", "Reintento programado"),
                            ("DEAD", "Revisión requerida"),
                            ("CANCELLED", "Cancelado"),
                        ],
                        default="PENDING",
                        max_length=16,
                    ),
                ),
                ("lease_until", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.CharField(blank=True, max_length=300)),
                (
                    "provider_idempotency_key",
                    models.CharField(
                        blank=True, max_length=220, null=True, unique=True
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "recipient",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="outbox_jobs",
                        to="simple_crm_identity.identityprofile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Trabajo de plataforma",
                "verbose_name_plural": "Trabajos de plataforma",
                "ordering": ("scheduled_at", "created_at", "pk"),
            },
        ),
        migrations.CreateModel(
            name="NotificationDelivery",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("channel", models.CharField(default="IN_APP", max_length=24)),
                (
                    "provider_idempotency_key",
                    models.CharField(max_length=220, unique=True),
                ),
                (
                    "delivered_at",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("metadata", models.JSONField(default=dict)),
                (
                    "identity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="notification_deliveries",
                        to="simple_crm_identity.identityprofile",
                    ),
                ),
                (
                    "job",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="delivery",
                        to="simple_crm_platform.outboxjob",
                    ),
                ),
            ],
            options={
                "verbose_name": "Entrega de notificación",
                "verbose_name_plural": "Entregas de notificaciones",
            },
        ),
        migrations.CreateModel(
            name="NotificationPreference",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("digest_enabled", models.BooleanField(default=True)),
                ("escalation_enabled", models.BooleanField(default=False)),
                ("daily_digest_hour", models.PositiveSmallIntegerField(default=8)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "identity",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="notification_preferences",
                        to="simple_crm_identity.identityprofile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Preferencia de notificación",
                "verbose_name_plural": "Preferencias de notificación",
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            ("daily_digest_hour__gte", 0),
                            ("daily_digest_hour__lte", 23),
                        ),
                        name="platform_digest_hour_valid",
                    )
                ],
            },
        ),
        migrations.AddIndex(
            model_name="outboxjob",
            index=models.Index(
                fields=["state", "scheduled_at"], name="platform_job_poll_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="outboxjob",
            index=models.Index(
                fields=["job_type", "state"], name="platform_job_review_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="outboxjob",
            constraint=models.CheckConstraint(
                condition=models.Q(("attempts__lte", models.F("max_attempts"))),
                name="platform_job_attempts_bounded",
            ),
        ),
        migrations.AddConstraint(
            model_name="outboxjob",
            constraint=models.CheckConstraint(
                condition=models.Q(("max_attempts__gte", 1)),
                name="platform_job_max_attempts_positive",
            ),
        ),
    ]
