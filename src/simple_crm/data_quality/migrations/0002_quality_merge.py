"""Create quality issues, match candidates, and immutable quality audit."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("simple_crm_crm", "0005_lead_domain"),
        ("simple_crm_data_quality", "0001_import_staging"),
        ("simple_crm_identity", "0002_seed_roles"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="QualityAuditEvent",
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
                ("action", models.CharField(max_length=40)),
                ("target_type", models.CharField(max_length=120)),
                ("target_id", models.CharField(max_length=128)),
                ("reason", models.CharField(max_length=500)),
                ("before_state", models.JSONField(default=dict)),
                ("after_state", models.JSONField(default=dict)),
                ("source_evidence", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="quality_audit_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Auditoría de calidad",
                "verbose_name_plural": "Auditorías de calidad",
                "ordering": ("created_at", "pk"),
            },
        ),
        migrations.CreateModel(
            name="CandidateMatch",
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
                    "match_type",
                    models.CharField(
                        choices=[
                            ("EXACT_EMAIL", "Email exacto"),
                            ("EXACT_PHONE", "Teléfono exacto"),
                            ("EXACT_SOURCE", "Identificador fuente exacto"),
                            ("FUZZY_NAME", "Nombre similar"),
                            ("FUZZY_ORGANIZATION", "Organización similar"),
                        ],
                        max_length=32,
                    ),
                ),
                ("confidence", models.DecimalField(decimal_places=4, max_digits=5)),
                ("evidence", models.JSONField(default=dict)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("REVIEW", "En revisión"),
                            ("APPROVED", "Aprobada"),
                            ("REJECTED", "Rechazada"),
                            ("APPLIED", "Aplicada"),
                        ],
                        default="REVIEW",
                        max_length=12,
                    ),
                ),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_reason", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "candidate",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="quality_duplicate_candidates",
                        to="simple_crm_crm.party",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="quality_matches_reviewed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "source_record",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="candidate_matches",
                        to="simple_crm_data_quality.sourcerecord",
                    ),
                ),
                (
                    "survivor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="quality_survivor_candidates",
                        to="simple_crm_crm.party",
                    ),
                ),
            ],
            options={
                "verbose_name": "Candidato de coincidencia",
                "verbose_name_plural": "Candidatos de coincidencia",
                "ordering": ("-confidence", "created_at", "pk"),
            },
        ),
        migrations.CreateModel(
            name="QualityIssue",
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
                ("rule_code", models.CharField(max_length=80)),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("ERROR", "Error"),
                            ("WARNING", "Advertencia"),
                            ("INFO", "Información"),
                        ],
                        max_length=12,
                    ),
                ),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("OPEN", "Abierta"),
                            ("RESOLVED", "Resuelta"),
                            ("ACCEPTED", "Aceptada"),
                            ("REOPENED", "Reabierta"),
                        ],
                        default="OPEN",
                        max_length=12,
                    ),
                ),
                ("target_type", models.CharField(blank=True, max_length=120)),
                ("target_id", models.CharField(blank=True, max_length=128)),
                ("decision", models.CharField(blank=True, max_length=40)),
                ("acceptance_reason", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="quality_issues_owned",
                        to="simple_crm_identity.identityprofile",
                    ),
                ),
                (
                    "source_record",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="quality_issues",
                        to="simple_crm_data_quality.sourcerecord",
                    ),
                ),
            ],
            options={
                "verbose_name": "Incidencia de calidad",
                "verbose_name_plural": "Incidencias de calidad",
                "ordering": ("severity", "created_at", "pk"),
                "indexes": [
                    models.Index(
                        fields=["state", "severity", "created_at"],
                        name="simple_crm__state_945404_idx",
                    ),
                    models.Index(
                        fields=["target_type", "target_id"],
                        name="simple_crm__target__655b87_idx",
                    ),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="candidatematch",
            constraint=models.UniqueConstraint(
                fields=("survivor", "candidate", "match_type"),
                name="dq_candidate_match_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="candidatematch",
            constraint=models.CheckConstraint(
                condition=models.Q(("confidence__gte", 0), ("confidence__lte", 1)),
                name="dq_candidate_confidence_range",
            ),
        ),
        migrations.AddConstraint(
            model_name="qualityissue",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("acceptance_reason__gt", ""), ("state", "ACCEPTED")),
                    models.Q(("state", "ACCEPTED"), _negated=True),
                    _connector="OR",
                ),
                name="dq_accepted_issue_reason_required",
            ),
        ),
    ]
