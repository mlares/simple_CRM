import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("simple_crm_crm", "0005_lead_domain"),
        ("simple_crm_data_quality", "0002_quality_merge"),
        ("simple_crm_identity", "0002_seed_roles"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GovernanceAuditEvent",
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
                ("action", models.CharField(max_length=48)),
                ("target_type", models.CharField(max_length=120)),
                ("target_id", models.CharField(max_length=128)),
                ("request_correlation", models.CharField(blank=True, max_length=120)),
                ("reason", models.CharField(blank=True, max_length=500)),
                ("before_state", models.JSONField(default=dict)),
                ("after_state", models.JSONField(default=dict)),
                ("metadata", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="governance_audit_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ("created_at", "pk")},
        ),
        migrations.CreateModel(
            name="RetentionCategory",
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
                ("code", models.CharField(max_length=60, unique=True)),
                ("label", models.CharField(max_length=160)),
                ("retention_days", models.PositiveIntegerField()),
                ("purpose", models.CharField(max_length=300)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ("code",)},
        ),
        migrations.CreateModel(
            name="PrivacyCase",
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
                    "case_type",
                    models.CharField(
                        choices=[
                            ("ACCESS", "Acceso"),
                            ("CORRECTION", "Corrección"),
                            ("SUPPRESSION", "Supresión"),
                            ("RETENTION", "Retención"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("OPEN", "Abierto"),
                            ("APPROVED", "Aprobado"),
                            ("COMPLETED", "Completado"),
                            ("REJECTED", "Rechazado"),
                        ],
                        default="OPEN",
                        max_length=12,
                    ),
                ),
                ("reason", models.CharField(max_length=500)),
                ("decision_reason", models.CharField(blank=True, max_length=500)),
                ("request_correlation", models.CharField(blank=True, max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="privacy_cases_requested",
                        to="simple_crm_identity.identityprofile",
                    ),
                ),
                (
                    "subject",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="privacy_cases",
                        to="simple_crm_crm.party",
                    ),
                ),
            ],
            options={"ordering": ("-created_at", "-pk")},
        ),
        migrations.CreateModel(
            name="LegalHold",
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
                ("target_type", models.CharField(max_length=120)),
                ("target_id", models.CharField(max_length=128)),
                ("reason", models.CharField(max_length=500)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("released_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="legal_holds_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="RetentionDecision",
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
                ("target_type", models.CharField(max_length=120)),
                ("target_id", models.CharField(max_length=128)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("PREVIEWED", "Previsualizada"),
                            ("APPROVED", "Aprobada"),
                            ("EXECUTED", "Ejecutada"),
                        ],
                        default="PREVIEWED",
                        max_length=12,
                    ),
                ),
                ("preview", models.JSONField(default=dict)),
                ("legal_hold_excluded", models.BooleanField(default=False)),
                ("reason", models.CharField(max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("executed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="retention_decisions_approved",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="decisions",
                        to="simple_crm_data_quality.retentioncategory",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="governanceauditevent",
            index=models.Index(
                fields=["target_type", "target_id", "created_at"],
                name="simple_crm__target__77f727_idx",
            ),
        ),
    ]
