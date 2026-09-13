"""Create interactions, tasks, activity audit events, and participants."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("simple_crm_crm", "0005_lead_domain"),
        ("simple_crm_identity", "0002_seed_roles"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Interaction",
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
                ("occurrence_date", models.DateField()),
                ("occurrence_time", models.TimeField(blank=True, null=True)),
                (
                    "direction",
                    models.CharField(
                        choices=[("OUTBOUND", "Saliente"), ("INBOUND", "Entrante")],
                        max_length=12,
                    ),
                ),
                (
                    "result",
                    models.CharField(
                        choices=[
                            ("ATTEMPTED", "Intento de contacto"),
                            ("COMPLETED", "Contacto completado"),
                            ("RESPONSE", "Respuesta"),
                        ],
                        max_length=12,
                    ),
                ),
                ("note", models.TextField(blank=True)),
                ("source", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="interactions_entered",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "channel",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="interactions",
                        to="simple_crm_crm.interactionchannel",
                    ),
                ),
                (
                    "lead",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="interactions",
                        to="simple_crm_crm.lead",
                    ),
                ),
                (
                    "outcome",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="interactions",
                        to="simple_crm_crm.interactionoutcome",
                    ),
                ),
            ],
            options={
                "verbose_name": "Interacción",
                "verbose_name_plural": "Interacciones",
                "ordering": ("-occurrence_date", "-occurrence_time", "-created_at", "-pk"),
            },
        ),
        migrations.CreateModel(
            name="InteractionParticipant",
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
                ("participant_role", models.CharField(default="CONTACT", max_length=32)),
                (
                    "interaction",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="participants",
                        to="simple_crm_activity.interaction",
                    ),
                ),
                (
                    "party",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="interaction_participations",
                        to="simple_crm_crm.party",
                    ),
                ),
            ],
            options={
                "verbose_name": "Participante de interacción",
                "verbose_name_plural": "Participantes de interacción",
            },
        ),
        migrations.CreateModel(
            name="Task",
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
                ("description", models.CharField(max_length=300)),
                ("due_date", models.DateField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("OPEN", "Abierta"),
                            ("COMPLETED", "Completada"),
                            ("RESCHEDULED", "Reprogramada"),
                            ("CANCELLED", "Cancelada"),
                        ],
                        default="OPEN",
                        max_length=16,
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[("LOW", "Baja"), ("NORMAL", "Normal"), ("HIGH", "Alta")],
                        default="NORMAL",
                        max_length=12,
                    ),
                ),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("completion_note", models.CharField(blank=True, max_length=500)),
                ("rescheduled_at", models.DateTimeField(blank=True, null=True)),
                ("reschedule_reason", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "lead",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tasks",
                        to="simple_crm_crm.lead",
                    ),
                ),
                (
                    "originating_interaction",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="follow_up_tasks",
                        to="simple_crm_activity.interaction",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tasks",
                        to="simple_crm_identity.identityprofile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Tarea",
                "verbose_name_plural": "Tareas",
                "ordering": ("due_date", "-created_at", "-pk"),
            },
        ),
        migrations.CreateModel(
            name="ActivityAuditEvent",
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
                ("action", models.CharField(max_length=64)),
                ("details", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="activity_audit_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "lead",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="activity_audits",
                        to="simple_crm_crm.lead",
                    ),
                ),
                (
                    "interaction",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="audit_events",
                        to="simple_crm_activity.interaction",
                    ),
                ),
                (
                    "task",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="audit_events",
                        to="simple_crm_activity.task",
                    ),
                ),
            ],
            options={
                "verbose_name": "Auditoría de actividad",
                "verbose_name_plural": "Auditorías de actividad",
                "ordering": ("created_at", "pk"),
            },
        ),
        migrations.AddConstraint(
            model_name="interaction",
            constraint=models.CheckConstraint(
                condition=models.Q(("occurrence_date__isnull", False)),
                name="activity_interaction_date_required",
            ),
        ),
        migrations.AddConstraint(
            model_name="interactionparticipant",
            constraint=models.UniqueConstraint(
                fields=("interaction", "party", "participant_role"),
                name="activity_interaction_participant_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("completed_at__isnull", False), ("status", "COMPLETED")),
                    models.Q(
                        ("completed_at__isnull", True),
                        ("status__in", ("OPEN", "RESCHEDULED", "CANCELLED")),
                    ),
                    _connector="OR",
                ),
                name="activity_task_completion_shape_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("rescheduled_at__isnull", False), ("status", "RESCHEDULED")),
                    models.Q(("status", "RESCHEDULED"), _negated=True),
                    _connector="OR",
                ),
                name="activity_task_reschedule_date_valid",
            ),
        ),
    ]
