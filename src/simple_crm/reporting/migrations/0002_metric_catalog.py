from datetime import date
from typing import Any

from django.db import migrations, models


METRICS = [
    (
        "CONTACTABLE_LEAD",
        "Lead contactable",
        "Reporting",
        "Lead con al menos un contacto válido y no suprimido.",
        "Leads contactables",
        "Leads visibles",
        {"contact_quality": "VALID"},
    ),
    (
        "CONTACTED_LEAD",
        "Lead contactado",
        "Reporting",
        "Lead con una interacción de contacto válida en el período.",
        "Leads con interacción elegible",
        "Leads visibles",
        {"exclude_placeholder": True},
    ),
    (
        "RESPONSE_RATE",
        "Tasa de respuesta",
        "Reporting",
        "Respuesta entrante sobre interacciones salientes elegibles.",
        "Respuestas entrantes",
        "Interacciones salientes elegibles",
        {"exclude_placeholder": True},
    ),
    (
        "STALE_LEAD",
        "Lead estancado",
        "Reporting",
        "Lead sin actualización dentro del umbral operativo.",
        "Leads estancados",
        "Leads visibles",
        {"stale_days": 14},
    ),
    (
        "STAGE_AGE",
        "Antigüedad de etapa",
        "Reporting",
        "Días desde la última entrada a la etapa actual.",
        "Días acumulados por etapa",
        "Leads visibles por etapa",
        {"source": "stage_history"},
    ),
    (
        "OVERDUE_TASK",
        "Tarea vencida",
        "Reporting",
        "Tarea abierta con fecha anterior al día local.",
        "Tareas abiertas vencidas",
        "Tareas visibles",
        {"local_date": True},
    ),
    (
        "COHORT_CONVERSION",
        "Conversión de cohorte",
        "Reporting",
        "Leads cerrados sobre leads creados en el período.",
        "Leads cerrados",
        "Leads creados en la cohorte",
        {"closed_stage": "CERRADO"},
    ),
]


def seed_metrics(apps: Any, schema_editor: Any) -> None:
    model = apps.get_model("simple_crm_reporting", "MetricDefinition")
    for code, label, owner, description, numerator, denominator, rules in METRICS:
        model.objects.get_or_create(
            code=code,
            defaults={
                "label": label,
                "owner": owner,
                "description": description,
                "numerator": numerator,
                "denominator": denominator,
                "inclusion_rules": rules,
                "timeframe_semantics": "Las fechas usan el día local de Córdoba; las interacciones usan occurrence_date.",
                "version": 1,
                "effective_from": date(2026, 1, 1),
            },
        )


class Migration(migrations.Migration):
    dependencies = [("simple_crm_reporting", "0001_saved_views")]

    operations = [
        migrations.CreateModel(
            name="MetricDefinition",
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
                ("owner", models.CharField(max_length=160)),
                ("description", models.TextField()),
                ("numerator", models.CharField(max_length=300)),
                ("denominator", models.CharField(max_length=300)),
                ("inclusion_rules", models.JSONField(default=dict)),
                ("timeframe_semantics", models.CharField(max_length=300)),
                ("version", models.PositiveIntegerField(default=1)),
                ("effective_from", models.DateField(default=date.today)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ("code",),
                "verbose_name": "Definición de métrica",
                "verbose_name_plural": "Definiciones de métricas",
            },
        ),
        migrations.AddConstraint(
            model_name="metricdefinition",
            constraint=models.CheckConstraint(
                condition=models.Q(("code__gt", "")),
                name="reporting_metric_code_not_empty",
            ),
        ),
        migrations.AddConstraint(
            model_name="metricdefinition",
            constraint=models.CheckConstraint(
                condition=models.Q(("label__gt", "")),
                name="reporting_metric_label_not_empty",
            ),
        ),
        migrations.RunPython(seed_metrics, migrations.RunPython.noop),
    ]
