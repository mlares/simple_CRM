"""Create the identity, role, team, scope, and elevation tables."""

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("simple_crm_crm", "0003_postgres_catalog_guards"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Role",
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
                ("code", models.CharField(max_length=50, unique=True)),
                ("label", models.CharField(max_length=120)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Rol",
                "verbose_name_plural": "Roles",
                "ordering": ("code",),
            },
        ),
        migrations.CreateModel(
            name="Team",
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
                ("code", models.CharField(max_length=50, unique=True)),
                ("label", models.CharField(max_length=120)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Equipo",
                "verbose_name_plural": "Equipos",
                "ordering": ("label", "code"),
            },
        ),
        migrations.CreateModel(
            name="IdentityProfile",
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
                    "oidc_subject",
                    models.CharField(
                        blank=True, max_length=255, null=True, unique=True
                    ),
                ),
                ("display_name", models.CharField(blank=True, max_length=160)),
                ("disabled_at", models.DateTimeField(blank=True, null=True)),
                ("disabled_reason", models.CharField(blank=True, max_length=500)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="identity_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Identidad",
                "verbose_name_plural": "Identidades",
            },
        ),
        migrations.CreateModel(
            name="TemporaryElevation",
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
                    "action",
                    models.CharField(
                        choices=[
                            ("view", "Ver"),
                            ("create", "Crear"),
                            ("change", "Modificar"),
                            ("reassign", "Reasignar"),
                            ("merge", "Fusionar"),
                            ("import", "Importar"),
                            ("resolve_quality", "Resolver calidad"),
                            ("audit_view", "Ver auditoría"),
                            ("bulk_export", "Exportar en bloque"),
                            ("manage_catalog", "Administrar catálogos"),
                            ("elevate_access", "Elevar acceso"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "scope_type",
                    models.CharField(
                        choices=[
                            ("global", "Global"),
                            ("team", "Equipo"),
                            ("campaign", "Campaña"),
                            ("object", "Objeto"),
                        ],
                        max_length=16,
                    ),
                ),
                ("object_id", models.CharField(blank=True, max_length=128, null=True)),
                ("reason", models.CharField(max_length=500)),
                ("starts_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField()),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "approved_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="approved_identity_elevations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "campaign",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="identity_elevations",
                        to="simple_crm_crm.campaign",
                    ),
                ),
                (
                    "content_type",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "identity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="elevations",
                        to="simple_crm_identity.identityprofile",
                    ),
                ),
                (
                    "team",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="elevations",
                        to="simple_crm_identity.team",
                    ),
                ),
            ],
            options={
                "verbose_name": "Elevación temporal",
                "verbose_name_plural": "Elevaciones temporales",
            },
        ),
        migrations.CreateModel(
            name="ElevationUse",
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
                    "action",
                    models.CharField(
                        choices=[
                            ("view", "Ver"),
                            ("create", "Crear"),
                            ("change", "Modificar"),
                            ("reassign", "Reasignar"),
                            ("merge", "Fusionar"),
                            ("import", "Importar"),
                            ("resolve_quality", "Resolver calidad"),
                            ("audit_view", "Ver auditoría"),
                            ("bulk_export", "Exportar en bloque"),
                            ("manage_catalog", "Administrar catálogos"),
                            ("elevate_access", "Elevar acceso"),
                        ],
                        max_length=32,
                    ),
                ),
                ("reason", models.CharField(max_length=500)),
                (
                    "scope_type",
                    models.CharField(
                        choices=[
                            ("global", "Global"),
                            ("team", "Equipo"),
                            ("campaign", "Campaña"),
                            ("object", "Objeto"),
                        ],
                        max_length=16,
                    ),
                ),
                ("scope_snapshot", models.JSONField(default=dict)),
                ("occurred_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="elevation_uses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "approved_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="approved_elevation_uses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "elevation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="uses",
                        to="simple_crm_identity.temporaryelevation",
                    ),
                ),
            ],
            options={
                "verbose_name": "Uso de elevación",
                "verbose_name_plural": "Usos de elevación",
                "ordering": ("-occurred_at", "-pk"),
            },
        ),
        migrations.CreateModel(
            name="RoleAssignment",
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
                ("starts_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                (
                    "identity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="role_assignments",
                        to="simple_crm_identity.identityprofile",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assignments",
                        to="simple_crm_identity.role",
                    ),
                ),
            ],
            options={
                "verbose_name": "Asignación de rol",
                "verbose_name_plural": "Asignaciones de roles",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("identity", "role"),
                        name="identity_role_assignment_unique",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("ends_at__isnull", True),
                            ("ends_at__gt", models.F("starts_at")),
                            _connector="OR",
                        ),
                        name="identity_role_assignment_dates_valid",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="RolePermission",
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
                    "action",
                    models.CharField(
                        choices=[
                            ("view", "Ver"),
                            ("create", "Crear"),
                            ("change", "Modificar"),
                            ("reassign", "Reasignar"),
                            ("merge", "Fusionar"),
                            ("import", "Importar"),
                            ("resolve_quality", "Resolver calidad"),
                            ("audit_view", "Ver auditoría"),
                            ("bulk_export", "Exportar en bloque"),
                            ("manage_catalog", "Administrar catálogos"),
                            ("elevate_access", "Elevar acceso"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="action_permissions",
                        to="simple_crm_identity.role",
                    ),
                ),
            ],
            options={
                "verbose_name": "Permiso de acción por rol",
                "verbose_name_plural": "Permisos de acción por rol",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("role", "action"), name="identity_role_action_unique"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="ScopeGrant",
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
                    "scope_type",
                    models.CharField(
                        choices=[
                            ("global", "Global"),
                            ("team", "Equipo"),
                            ("campaign", "Campaña"),
                            ("object", "Objeto"),
                        ],
                        max_length=16,
                    ),
                ),
                ("object_id", models.CharField(blank=True, max_length=128, null=True)),
                ("starts_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                (
                    "campaign",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="simple_crm_crm.campaign",
                    ),
                ),
                (
                    "content_type",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "identity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scope_grants",
                        to="simple_crm_identity.identityprofile",
                    ),
                ),
                (
                    "team",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="simple_crm_identity.team",
                    ),
                ),
            ],
            options={
                "verbose_name": "Alcance de identidad",
                "verbose_name_plural": "Alcances de identidades",
                "indexes": [
                    models.Index(
                        fields=["identity", "scope_type"],
                        name="simple_crm__identit_64cb6d_idx",
                    ),
                    models.Index(
                        fields=["content_type", "object_id"],
                        name="simple_crm__content_cc8852_idx",
                    ),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(
                                ("campaign__isnull", True),
                                ("content_type__isnull", True),
                                ("object_id__isnull", True),
                                ("scope_type", "global"),
                                ("team__isnull", True),
                            ),
                            models.Q(
                                ("campaign__isnull", True),
                                ("content_type__isnull", True),
                                ("object_id__isnull", True),
                                ("scope_type", "team"),
                                ("team__isnull", False),
                            ),
                            models.Q(
                                ("campaign__isnull", False),
                                ("content_type__isnull", True),
                                ("object_id__isnull", True),
                                ("scope_type", "campaign"),
                                ("team__isnull", True),
                            ),
                            models.Q(
                                ("campaign__isnull", True),
                                ("content_type__isnull", False),
                                ("object_id__isnull", False),
                                ("scope_type", "object"),
                                ("team__isnull", True),
                            ),
                            _connector="OR",
                        ),
                        name="identity_scope_grant_shape_valid",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("expires_at__isnull", True),
                            ("expires_at__gt", models.F("starts_at")),
                            _connector="OR",
                        ),
                        name="identity_scope_grant_dates_valid",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="TeamMembership",
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
                ("starts_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                (
                    "identity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="team_memberships",
                        to="simple_crm_identity.identityprofile",
                    ),
                ),
                (
                    "team",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="memberships",
                        to="simple_crm_identity.team",
                    ),
                ),
            ],
            options={
                "verbose_name": "Membresía de equipo",
                "verbose_name_plural": "Membresías de equipos",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("identity", "team"),
                        name="identity_team_membership_unique",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("ends_at__isnull", True),
                            ("ends_at__gt", models.F("starts_at")),
                            _connector="OR",
                        ),
                        name="identity_team_membership_dates_valid",
                    ),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="temporaryelevation",
            constraint=models.CheckConstraint(
                condition=models.Q(("expires_at__gt", models.F("starts_at"))),
                name="identity_elevation_dates_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="temporaryelevation",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("campaign__isnull", True),
                        ("content_type__isnull", True),
                        ("object_id__isnull", True),
                        ("scope_type", "global"),
                        ("team__isnull", True),
                    ),
                    models.Q(
                        ("campaign__isnull", True),
                        ("content_type__isnull", True),
                        ("object_id__isnull", True),
                        ("scope_type", "team"),
                        ("team__isnull", False),
                    ),
                    models.Q(
                        ("campaign__isnull", False),
                        ("content_type__isnull", True),
                        ("object_id__isnull", True),
                        ("scope_type", "campaign"),
                        ("team__isnull", True),
                    ),
                    models.Q(
                        ("campaign__isnull", True),
                        ("content_type__isnull", False),
                        ("object_id__isnull", False),
                        ("scope_type", "object"),
                        ("team__isnull", True),
                    ),
                    _connector="OR",
                ),
                name="identity_elevation_scope_shape_valid",
            ),
        ),
    ]
