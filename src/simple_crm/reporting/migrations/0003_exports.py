from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("simple_crm_reporting", "0002_metric_catalog"),
        ("simple_crm_identity", "0002_seed_roles"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ExportRequest",
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
                    "format",
                    models.CharField(
                        choices=[("CSV", "CSV"), ("XLSX", "XLSX")], max_length=8
                    ),
                ),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pendiente"),
                            ("PROCESSING", "Procesando"),
                            ("READY", "Lista"),
                            ("FAILED", "Fallida"),
                            ("EXPIRED", "Vencida"),
                        ],
                        default="PENDING",
                        max_length=16,
                    ),
                ),
                ("idempotency_key", models.CharField(max_length=160, unique=True)),
                ("definition_snapshot", models.JSONField(default=dict)),
                ("fields", models.JSONField(default=list)),
                ("scope_snapshot", models.JSONField(default=dict)),
                ("reason", models.CharField(blank=True, max_length=500)),
                ("file_payload", models.BinaryField(blank=True, null=True)),
                ("checksum", models.CharField(blank=True, max_length=64)),
                ("row_count", models.PositiveIntegerField(default=0)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("last_error", models.CharField(blank=True, max_length=500)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="export_requests",
                        to="simple_crm_identity.identityprofile",
                    ),
                ),
            ],
            options={
                "ordering": ("-requested_at", "-pk"),
                "verbose_name": "Solicitud de exportación",
                "verbose_name_plural": "Solicitudes de exportación",
            },
        ),
        migrations.CreateModel(
            name="ExportAuditEvent",
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
                ("action", models.CharField(max_length=32)),
                ("metadata", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "export_request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="audit_events",
                        to="simple_crm_reporting.exportrequest",
                    ),
                ),
            ],
            options={"ordering": ("created_at", "pk")},
        ),
    ]
