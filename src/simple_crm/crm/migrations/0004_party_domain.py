"""Create parties, subtypes, contact points, relationships, and provenance."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("simple_crm_crm", "0003_postgres_catalog_guards")]

    operations = [
        migrations.CreateModel(
            name="Organization",
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
                ("legal_name", models.CharField(blank=True, max_length=240)),
                ("organization_type", models.CharField(blank=True, max_length=100)),
            ],
            options={
                "verbose_name": "Organización",
                "verbose_name_plural": "Organizaciones",
            },
        ),
        migrations.CreateModel(
            name="Person",
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
                ("honorific", models.CharField(blank=True, max_length=40)),
                ("given_names", models.CharField(blank=True, max_length=160)),
                ("family_names", models.CharField(blank=True, max_length=160)),
            ],
            options={
                "verbose_name": "Persona",
                "verbose_name_plural": "Personas",
            },
        ),
        migrations.CreateModel(
            name="ContactPoint",
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
                    "kind",
                    models.CharField(
                        choices=[
                            ("EMAIL", "Correo electrónico"),
                            ("PHONE", "Teléfono"),
                            ("WHATSAPP", "WhatsApp"),
                            ("WEBSITE", "Sitio web"),
                            ("SOCIAL", "Red social"),
                        ],
                        max_length=16,
                    ),
                ),
                ("platform", models.CharField(blank=True, max_length=80)),
                ("raw_value", models.CharField(max_length=500)),
                (
                    "normalized_value",
                    models.CharField(
                        blank=True, db_index=True, max_length=500, null=True
                    ),
                ),
                ("phone_extension", models.CharField(blank=True, max_length=20)),
                (
                    "quality_state",
                    models.CharField(
                        choices=[
                            ("UNREVIEWED", "Sin revisar"),
                            ("VALID", "Válido"),
                            ("INVALID", "Inválido"),
                            ("AMBIGUOUS", "Ambiguo"),
                        ],
                        default="UNREVIEWED",
                        max_length=16,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("is_suppressed", models.BooleanField(default=False)),
                ("suppression_reason", models.CharField(blank=True, max_length=300)),
                ("provenance", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Punto de contacto",
                "verbose_name_plural": "Puntos de contacto",
                "indexes": [
                    models.Index(
                        fields=["kind", "normalized_value"],
                        name="simple_crm__kind_a7f05e_idx",
                    )
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("raw_value__gt", "")),
                        name="crm_contact_raw_not_empty",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("is_suppressed", False),
                            ("suppression_reason__gt", ""),
                            _connector="OR",
                        ),
                        name="crm_contact_suppression_reason_required",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="Party",
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
                    "party_type",
                    models.CharField(
                        choices=[("PERSON", "Persona"), ("ORGANIZATION", "Organización")],
                        max_length=16,
                    ),
                ),
                ("display_name", models.CharField(max_length=240)),
                (
                    "canonical_name",
                    models.CharField(db_index=True, max_length=240),
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
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="party",
                        to="simple_crm_crm.organization",
                    ),
                ),
                (
                    "person",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="party",
                        to="simple_crm_crm.person",
                    ),
                ),
            ],
            options={
                "verbose_name": "Parte",
                "verbose_name_plural": "Partes",
                "ordering": ("canonical_name", "pk"),
            },
        ),
        migrations.CreateModel(
            name="Address",
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
                ("address_line", models.CharField(blank=True, max_length=300)),
                ("sales_region", models.CharField(blank=True, max_length=120)),
                ("is_primary", models.BooleanField(default=False)),
                (
                    "country",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="party_addresses",
                        to="simple_crm_crm.country",
                    ),
                ),
                (
                    "locality",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="party_addresses",
                        to="simple_crm_crm.locality",
                    ),
                ),
                (
                    "province",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="party_addresses",
                        to="simple_crm_crm.province",
                    ),
                ),
                (
                    "party",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="addresses",
                        to="simple_crm_crm.party",
                    ),
                ),
            ],
            options={
                "verbose_name": "Domicilio",
                "verbose_name_plural": "Domicilios",
            },
        ),
        migrations.CreateModel(
            name="OrganizationPerson",
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
                ("relationship_type", models.CharField(default="AFFILIATED", max_length=60)),
                ("role_title", models.CharField(blank=True, max_length=160)),
                ("area_title", models.CharField(blank=True, max_length=160)),
                ("valid_from", models.DateField(blank=True, null=True)),
                ("valid_to", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="organization_relationships",
                        to="simple_crm_crm.party",
                    ),
                ),
                (
                    "person",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="organization_affiliations",
                        to="simple_crm_crm.party",
                    ),
                ),
            ],
            options={
                "verbose_name": "Relación organización-persona",
                "verbose_name_plural": "Relaciones organización-persona",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("organization", "person", "relationship_type"),
                        name="crm_organization_person_unique",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("valid_to__isnull", True),
                            ("valid_from__isnull", True),
                            ("valid_to__gte", models.F("valid_from")),
                            _connector="OR",
                        ),
                        name="crm_organization_person_dates_valid",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("organization", models.F("person")), _negated=True
                        ),
                        name="crm_organization_person_distinct",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="PartyAlias",
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
                ("alias_value", models.CharField(max_length=240)),
                ("alias_normalized", models.CharField(max_length=240)),
                ("alias_type", models.CharField(default="SOURCE_NAME", max_length=60)),
                ("provenance", models.JSONField(default=dict)),
                (
                    "party",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="aliases",
                        to="simple_crm_crm.party",
                    ),
                ),
            ],
            options={
                "verbose_name": "Alias de parte",
                "verbose_name_plural": "Aliases de partes",
                "indexes": [
                    models.Index(
                        fields=["alias_normalized"],
                        name="simple_crm__alias_n_b05f54_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("party", "alias_normalized", "alias_type"),
                        name="crm_party_alias_unique",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="PartyContactPoint",
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
                ("purpose", models.CharField(blank=True, max_length=100)),
                ("is_primary", models.BooleanField(default=False)),
                ("is_verified", models.BooleanField(default=False)),
                ("verification_note", models.CharField(blank=True, max_length=300)),
                (
                    "contact_point",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="party_links",
                        to="simple_crm_crm.contactpoint",
                    ),
                ),
                (
                    "party",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="contact_point_links",
                        to="simple_crm_crm.party",
                    ),
                ),
            ],
            options={
                "verbose_name": "Contacto de parte",
                "verbose_name_plural": "Contactos de partes",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("party", "contact_point"),
                        name="crm_party_contact_point_unique",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="PartySpecialty",
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
                ("raw_label", models.CharField(blank=True, max_length=160)),
                (
                    "party",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="specialties",
                        to="simple_crm_crm.party",
                    ),
                ),
                (
                    "specialty",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="party_links",
                        to="simple_crm_crm.specialty",
                    ),
                ),
            ],
            options={
                "verbose_name": "Especialidad de parte",
                "verbose_name_plural": "Especialidades de partes",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("party", "specialty"),
                        name="crm_party_specialty_unique",
                    )
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="party",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("organization__isnull", True),
                        ("party_type", "PERSON"),
                        ("person__isnull", False),
                    ),
                    models.Q(
                        ("organization__isnull", False),
                        ("party_type", "ORGANIZATION"),
                        ("person__isnull", True),
                    ),
                    _connector="OR",
                ),
                name="crm_party_exactly_one_subtype",
            ),
        ),
        migrations.AddConstraint(
            model_name="party",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("display_name__gt", ""), ("canonical_name__gt", "")
                ),
                name="crm_party_names_not_empty",
            ),
        ),
    ]
