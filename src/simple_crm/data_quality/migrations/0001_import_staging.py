"""Create lossless source-document, import, and lineage tables."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="ImportBatch",
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
                ("checksum", models.CharField(max_length=64)),
                ("parser_version", models.CharField(max_length=80)),
                ("application_version", models.CharField(max_length=80)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("UPLOADED", "Subido"),
                            ("STAGED", "En staging"),
                            ("VALIDATED", "Validado"),
                            ("CANDIDATE_MATCHED", "Candidatos identificados"),
                            ("APPROVED", "Aprobado"),
                            ("APPLYING", "Aplicando"),
                            ("APPLIED", "Aplicado"),
                            ("RECONCILED", "Reconciliado"),
                            ("FAILED", "Fallido"),
                        ],
                        default="UPLOADED",
                        max_length=24,
                    ),
                ),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("applied_at", models.DateTimeField(blank=True, null=True)),
                ("error_summary", models.JSONField(default=dict)),
                ("preview_counts", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="import_batches_approved",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "import_actor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="import_batches_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Lote de importación",
                "verbose_name_plural": "Lotes de importación",
                "ordering": ("-created_at", "-pk"),
            },
        ),
        migrations.CreateModel(
            name="ImportAuditEvent",
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
                ("reason", models.CharField(blank=True, max_length=500)),
                ("details", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="import_audit_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="audit_events",
                        to="simple_crm_data_quality.importbatch",
                    ),
                ),
            ],
            options={
                "verbose_name": "Auditoría de importación",
                "verbose_name_plural": "Auditorías de importación",
                "ordering": ("created_at", "pk"),
            },
        ),
        migrations.CreateModel(
            name="SourceDocument",
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
                ("filename", models.CharField(max_length=255)),
                (
                    "content_type",
                    models.CharField(
                        default="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        max_length=120,
                    ),
                ),
                ("size_bytes", models.PositiveIntegerField()),
                ("checksum", models.CharField(max_length=64, unique=True)),
                ("content", models.BinaryField()),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="source_documents_uploaded",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Documento fuente",
                "verbose_name_plural": "Documentos fuente",
                "ordering": ("-uploaded_at", "-pk"),
            },
        ),
        migrations.AddField(
            model_name="importbatch",
            name="source_document",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="batches",
                to="simple_crm_data_quality.sourcedocument",
            ),
        ),
        migrations.CreateModel(
            name="SourceRecord",
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
                ("sheet_name", models.CharField(max_length=120)),
                ("row_number", models.PositiveIntegerField()),
                ("source_coordinate", models.CharField(max_length=32)),
                ("raw_payload", models.JSONField(default=dict)),
                ("raw_checksum", models.CharField(max_length=64)),
                (
                    "classification",
                    models.CharField(
                        choices=[
                            ("NEW", "Nuevo"),
                            ("UPDATE", "Actualización"),
                            ("DUPLICATE", "Duplicado"),
                            ("WARNING", "Advertencia"),
                            ("ERROR", "Error"),
                            ("UNMATCHED", "Sin coincidencia"),
                            ("APPLIED", "Aplicado"),
                        ],
                        default="NEW",
                        max_length=16,
                    ),
                ),
                ("errors", models.JSONField(default=list)),
                ("warnings", models.JSONField(default=list)),
                ("canonical_links", models.JSONField(default=list)),
                ("rejection_reason", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="source_records",
                        to="simple_crm_data_quality.importbatch",
                    ),
                ),
            ],
            options={
                "verbose_name": "Registro fuente",
                "verbose_name_plural": "Registros fuente",
                "ordering": ("sheet_name", "row_number", "pk"),
            },
        ),
        migrations.CreateModel(
            name="SourceCanonicalLink",
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
                ("relation", models.CharField(max_length=40)),
                ("evidence", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "source_record",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="canonical_links_rows",
                        to="simple_crm_data_quality.sourcerecord",
                    ),
                ),
            ],
            options={
                "verbose_name": "Vínculo fuente-canónico",
                "verbose_name_plural": "Vínculos fuente-canónico",
            },
        ),
        migrations.AddConstraint(
            model_name="importbatch",
            constraint=models.UniqueConstraint(
                fields=("checksum", "parser_version", "application_version"),
                name="dq_import_batch_version_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="sourcerecord",
            constraint=models.UniqueConstraint(
                fields=("batch", "sheet_name", "row_number"),
                name="dq_source_record_coordinate_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="sourcecanonicallink",
            constraint=models.UniqueConstraint(
                fields=("source_record", "target_type", "target_id", "relation"),
                name="dq_source_canonical_link_unique",
            ),
        ),
    ]
