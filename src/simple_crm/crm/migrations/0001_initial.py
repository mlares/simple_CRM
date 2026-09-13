"""Create the controlled CRM catalog tables and audit ledger."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Campaign",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=40, unique=True)),
                ("label", models.CharField(max_length=120)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("accepts_new_leads", models.BooleanField(default=True)),
            ],
            options={"verbose_name": "Campaña", "verbose_name_plural": "Campañas", "ordering": ("sort_order", "label", "code"), "constraints": [models.CheckConstraint(condition=models.Q(("code__gt", "")), name="simple_crm_crm_campaign_code_not_empty"), models.CheckConstraint(condition=models.Q(("label__gt", "")), name="simple_crm_crm_campaign_label_not_empty")]},
        ),
        migrations.CreateModel(
            name="Country",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=40, unique=True)),
                ("label", models.CharField(max_length=120)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("is_domestic", models.BooleanField(default=False)),
            ],
            options={"verbose_name": "País", "verbose_name_plural": "Países", "ordering": ("sort_order", "label", "code"), "constraints": [models.CheckConstraint(condition=models.Q(("code__gt", "")), name="simple_crm_crm_country_code_not_empty"), models.CheckConstraint(condition=models.Q(("label__gt", "")), name="simple_crm_crm_country_label_not_empty")]},
        ),
        migrations.CreateModel(
            name="InteractionChannel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=40, unique=True)),
                ("label", models.CharField(max_length=120)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("allows_inbound", models.BooleanField(default=True)),
            ],
            options={"verbose_name": "Canal de interacción", "verbose_name_plural": "Canales de interacción", "ordering": ("sort_order", "label", "code"), "constraints": [models.CheckConstraint(condition=models.Q(("code__gt", "")), name="simple_crm_crm_interactionchannel_code_not_empty"), models.CheckConstraint(condition=models.Q(("label__gt", "")), name="simple_crm_crm_interactionchannel_label_not_empty")]},
        ),
        migrations.CreateModel(
            name="InteractionOutcome",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=40, unique=True)),
                ("label", models.CharField(max_length=120)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("requires_follow_up", models.BooleanField(default=False)),
            ],
            options={"verbose_name": "Resultado de interacción", "verbose_name_plural": "Resultados de interacción", "ordering": ("sort_order", "label", "code"), "constraints": [models.CheckConstraint(condition=models.Q(("code__gt", "")), name="simple_crm_crm_interactionoutcome_code_not_empty"), models.CheckConstraint(condition=models.Q(("label__gt", "")), name="simple_crm_crm_interactionoutcome_label_not_empty")]},
        ),
        migrations.CreateModel(
            name="LeadStatus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=40, unique=True)),
                ("label", models.CharField(max_length=120)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("is_closed", models.BooleanField(default=False)),
            ],
            options={"verbose_name": "Estado de lead", "verbose_name_plural": "Estados de lead", "ordering": ("sort_order", "label", "code"), "constraints": [models.CheckConstraint(condition=models.Q(("code__gt", "")), name="simple_crm_crm_leadstatus_code_not_empty"), models.CheckConstraint(condition=models.Q(("label__gt", "")), name="simple_crm_crm_leadstatus_label_not_empty")]},
        ),
        migrations.CreateModel(
            name="Province",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=40, unique=True)),
                ("label", models.CharField(max_length=120)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("is_capital_region", models.BooleanField(default=False)),
                ("country", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="provinces", to="simple_crm_crm.country")),
            ],
            options={"verbose_name": "Provincia", "verbose_name_plural": "Provincias", "ordering": ("sort_order", "label", "code")},
        ),
        migrations.CreateModel(
            name="Locality",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=40, unique=True)),
                ("label", models.CharField(max_length=120)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("is_capital", models.BooleanField(default=False)),
                ("province", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="localities", to="simple_crm_crm.province")),
            ],
            options={"verbose_name": "Localidad", "verbose_name_plural": "Localidades", "ordering": ("sort_order", "label", "code")},
        ),
        migrations.CreateModel(
            name="Specialty",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=40, unique=True)),
                ("label", models.CharField(max_length=120)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("is_clinical", models.BooleanField(default=True)),
            ],
            options={"verbose_name": "Especialidad", "verbose_name_plural": "Especialidades", "ordering": ("sort_order", "label", "code"), "constraints": [models.CheckConstraint(condition=models.Q(("code__gt", "")), name="simple_crm_crm_specialty_code_not_empty"), models.CheckConstraint(condition=models.Q(("label__gt", "")), name="simple_crm_crm_specialty_label_not_empty")]},
        ),
        migrations.CreateModel(
            name="CatalogAuditEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("catalog_model", models.CharField(max_length=80)),
                ("catalog_code", models.CharField(max_length=40)),
                ("action", models.CharField(choices=[("created", "Creado"), ("updated", "Actualizado"), ("activated", "Activado"), ("deactivated", "Desactivado")], max_length=16)),
                ("changes", models.JSONField(default=dict)),
                ("snapshot", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="catalog_audit_entries", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Auditoría de catálogo", "verbose_name_plural": "Auditoría de catálogos", "ordering": ("-created_at", "-pk"), "indexes": [models.Index(fields=["catalog_model", "catalog_code"], name="simple_crm__catalog_7f49f2_idx")]},
        ),
        migrations.AddConstraint(model_name="province", constraint=models.CheckConstraint(condition=models.Q(("code__gt", "")), name="simple_crm_crm_province_code_not_empty")),
        migrations.AddConstraint(model_name="province", constraint=models.CheckConstraint(condition=models.Q(("label__gt", "")), name="simple_crm_crm_province_label_not_empty")),
        migrations.AddConstraint(model_name="province", constraint=models.UniqueConstraint(fields=("country", "label"), name="crm_province_country_label_unique")),
        migrations.AddConstraint(model_name="locality", constraint=models.CheckConstraint(condition=models.Q(("code__gt", "")), name="simple_crm_crm_locality_code_not_empty")),
        migrations.AddConstraint(model_name="locality", constraint=models.CheckConstraint(condition=models.Q(("label__gt", "")), name="simple_crm_crm_locality_label_not_empty")),
        migrations.AddConstraint(model_name="locality", constraint=models.UniqueConstraint(fields=("province", "label"), name="crm_locality_province_label_unique")),
    ]
