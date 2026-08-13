"""Create lead lifecycle, party links, assignments, and immutable stage history."""

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("simple_crm_crm", "0004_party_domain"),
        ("simple_crm_identity", "0002_seed_roles"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Lead",
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
                    "lead_number",
                    models.CharField(
                        blank=True, max_length=24, null=True, unique=True
                    ),
                ),
                (
                    "data_readiness",
                    models.CharField(
                        choices=[
                            ("UNREVIEWED", "Sin revisar"),
                            ("NEEDS_RESEARCH", "Requiere investigación"),
                            ("CONTACTABLE", "Contactable"),
                            ("VERIFIED", "Verificado"),
                        ],
                        default="UNREVIEWED",
                        max_length=20,
                    ),
                ),
                (
                    "lifecycle",
                    models.CharField(
                        choices=[("ACTIVE", "Activo"), ("ARCHIVED", "Archivado")],
                        default="ACTIVE",
                        max_length=16,
                    ),
                ),
                ("source_attribution", models.JSONField(default=dict)),
                ("next_task_description", models.CharField(blank=True, max_length=300)),
                ("next_task_due_at", models.DateTimeField(blank=True, null=True)),
                ("next_task_reason", models.CharField(blank=True, max_length=500)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="leads",
                        to="simple_crm_crm.campaign",
                    ),
                ),
                (
                    "current_stage",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="current_leads",
                        to="simple_crm_crm.leadstatus",
                    ),
                ),
                (
                    "team",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="leads",
                        to="simple_crm_identity.team",
                    ),
                ),
            ],
            options={
                "verbose_name": "Lead",
                "verbose_name_plural": "Leads",
                "ordering": ("-created_at", "-pk"),
            },
        ),
        migrations.CreateModel(
            name="LeadAssignment",
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
                    "assignment_role",
                    models.CharField(
                        choices=[("PRIMARY", "Principal"), ("SECONDARY", "Secundario")],
                        max_length=12,
                    ),
                ),
                ("assigned_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("unassigned_at", models.DateTimeField(blank=True, null=True)),
                (
                    "assigned_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lead_assignments_made",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "identity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lead_assignments",
                        to="simple_crm_identity.identityprofile",
                    ),
                ),
                (
                    "lead",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assignments",
                        to="simple_crm_crm.lead",
                    ),
                ),
            ],
            options={
                "verbose_name": "Asignación de lead",
                "verbose_name_plural": "Asignaciones de leads",
            },
        ),
        migrations.CreateModel(
            name="LeadParty",
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
                    "party_role",
                    models.CharField(
                        choices=[
                            ("ACCOUNT", "Cuenta"),
                            ("PRIMARY_CONTACT", "Contacto principal"),
                            ("SECONDARY_CONTACT", "Contacto secundario"),
                            ("SECRETARY", "Secretaría"),
                            ("OTHER", "Otro"),
                        ],
                        max_length=24,
                    ),
                ),
                (
                    "lead",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="party_links",
                        to="simple_crm_crm.lead",
                    ),
                ),
                (
                    "party",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lead_links",
                        to="simple_crm_crm.party",
                    ),
                ),
            ],
            options={
                "verbose_name": "Parte del lead",
                "verbose_name_plural": "Partes de los leads",
            },
        ),
        migrations.CreateModel(
            name="LeadStageHistory",
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
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("reason", models.CharField(blank=True, max_length=500)),
                ("transition_fields", models.JSONField(default=dict)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lead_stage_changes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "from_stage",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stage_history_from",
                        to="simple_crm_crm.leadstatus",
                    ),
                ),
                (
                    "lead",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stage_history",
                        to="simple_crm_crm.lead",
                    ),
                ),
                (
                    "to_stage",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stage_history_to",
                        to="simple_crm_crm.leadstatus",
                    ),
                ),
            ],
            options={
                "verbose_name": "Historial de etapa",
                "verbose_name_plural": "Historial de etapas",
                "ordering": ("occurred_at", "pk"),
            },
        ),
        migrations.AddConstraint(
            model_name="lead",
            constraint=models.CheckConstraint(
                condition=models.Q(("lead_number__gt", "")),
                name="crm_lead_number_not_empty",
            ),
        ),
        migrations.AddConstraint(
            model_name="lead",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("next_task_description__gt", ""),
                        ("next_task_due_at__isnull", False),
                    ),
                    ("next_task_reason__gt", ""),
                    models.Q(
                        ("next_task_description", ""),
                        ("next_task_due_at__isnull", True),
                        ("next_task_reason", ""),
                    ),
                    _connector="OR",
                ),
                name="crm_lead_next_action_shape_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="leadassignment",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("unassigned_at__isnull", True),
                    ("unassigned_at__gte", models.F("assigned_at")),
                    _connector="OR",
                ),
                name="crm_lead_assignment_dates_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="leadassignment",
            constraint=models.UniqueConstraint(
                condition=models.Q(("unassigned_at__isnull", True)),
                fields=("lead", "assignment_role"),
                name="crm_active_lead_assignment_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="leadparty",
            constraint=models.UniqueConstraint(
                fields=("lead", "party", "party_role"),
                name="crm_lead_party_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="leadparty",
            constraint=models.UniqueConstraint(
                condition=models.Q(("party_role", "ACCOUNT")),
                fields=("lead",),
                name="crm_one_account_per_lead",
            ),
        ),
        migrations.AddConstraint(
            model_name="leadparty",
            constraint=models.UniqueConstraint(
                condition=models.Q(("party_role", "PRIMARY_CONTACT")),
                fields=("lead",),
                name="crm_one_primary_contact_per_lead",
            ),
        ),
    ]
