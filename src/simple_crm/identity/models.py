"""Identity, role, team, scope, and elevation persistence."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from simple_crm.crm.models import Campaign


class Action(models.TextChoices):
    """Business actions are intentionally finer grained than Django CRUD."""

    VIEW = "view", "Ver"
    CREATE = "create", "Crear"
    CHANGE = "change", "Modificar"
    REASSIGN = "reassign", "Reasignar"
    MERGE = "merge", "Fusionar"
    IMPORT = "import", "Importar"
    RESOLVE_QUALITY = "resolve_quality", "Resolver calidad"
    AUDIT_VIEW = "audit_view", "Ver auditoría"
    BULK_EXPORT = "bulk_export", "Exportar en bloque"
    MANAGE_CATALOG = "manage_catalog", "Administrar catálogos"
    ELEVATE_ACCESS = "elevate_access", "Elevar acceso"


class ScopeType(models.TextChoices):
    GLOBAL = "global", "Global"
    TEAM = "team", "Equipo"
    CAMPAIGN = "campaign", "Campaña"
    OBJECT = "object", "Objeto"


class Role(models.Model):
    code = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("code",)
        verbose_name = "Rol"
        verbose_name_plural = "Roles"

    def __str__(self) -> str:
        return self.label


class IdentityProfile(models.Model):
    """CRM identity state attached to Django's account boundary."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="identity_profile",
    )
    oidc_subject = models.CharField(max_length=255, unique=True, null=True, blank=True)
    display_name = models.CharField(max_length=160, blank=True)
    disabled_at = models.DateTimeField(null=True, blank=True)
    disabled_reason = models.CharField(max_length=500, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Identidad"
        verbose_name_plural = "Identidades"

    @property
    def is_enabled(self) -> bool:
        return self.user.is_active and self.disabled_at is None

    def disable(self, reason: str) -> None:
        if not reason.strip():
            raise ValidationError("La baja de identidad requiere un motivo.")
        self.disabled_at = timezone.now()
        self.disabled_reason = reason.strip()
        self.save(update_fields=("disabled_at", "disabled_reason", "updated_at"))
        if self.user.is_active:
            self.user.is_active = False
            self.user.save(update_fields=("is_active",))

    def enable(self) -> None:
        self.disabled_at = None
        self.disabled_reason = ""
        self.save(update_fields=("disabled_at", "disabled_reason", "updated_at"))
        if not self.user.is_active:
            self.user.is_active = True
            self.user.save(update_fields=("is_active",))

    def __str__(self) -> str:
        return self.display_name or self.user.get_username()


class RolePermission(models.Model):
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="action_permissions"
    )
    action = models.CharField(max_length=32, choices=Action.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("role", "action"), name="identity_role_action_unique"
            )
        ]
        verbose_name = "Permiso de acción por rol"
        verbose_name_plural = "Permisos de acción por rol"

    def __str__(self) -> str:
        return f"{self.role}: {self.get_action_display()}"


class RoleAssignment(models.Model):
    identity = models.ForeignKey(
        IdentityProfile, on_delete=models.CASCADE, related_name="role_assignments"
    )
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="assignments")
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("identity", "role"), name="identity_role_assignment_unique"
            ),
            models.CheckConstraint(
                condition=Q(ends_at__isnull=True) | Q(ends_at__gt=F("starts_at")),
                name="identity_role_assignment_dates_valid",
            ),
        ]
        verbose_name = "Asignación de rol"
        verbose_name_plural = "Asignaciones de roles"


class Team(models.Model):
    code = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("label", "code")
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"

    def __str__(self) -> str:
        return self.label


class TeamMembership(models.Model):
    identity = models.ForeignKey(
        IdentityProfile, on_delete=models.CASCADE, related_name="team_memberships"
    )
    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="memberships")
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("identity", "team"), name="identity_team_membership_unique"
            ),
            models.CheckConstraint(
                condition=Q(ends_at__isnull=True) | Q(ends_at__gt=F("starts_at")),
                name="identity_team_membership_dates_valid",
            ),
        ]
        verbose_name = "Membresía de equipo"
        verbose_name_plural = "Membresías de equipos"


class ScopeGrant(models.Model):
    identity = models.ForeignKey(
        IdentityProfile, on_delete=models.CASCADE, related_name="scope_grants"
    )
    scope_type = models.CharField(max_length=16, choices=ScopeType.choices)
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.PROTECT)
    campaign = models.ForeignKey(
        Campaign, null=True, blank=True, on_delete=models.PROTECT
    )
    content_type = models.ForeignKey(
        ContentType, null=True, blank=True, on_delete=models.PROTECT
    )
    object_id = models.CharField(max_length=128, null=True, blank=True)
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)

    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        scope_type=ScopeType.GLOBAL,
                        team__isnull=True,
                        campaign__isnull=True,
                        content_type__isnull=True,
                        object_id__isnull=True,
                    )
                    | Q(
                        scope_type=ScopeType.TEAM,
                        team__isnull=False,
                        campaign__isnull=True,
                        content_type__isnull=True,
                        object_id__isnull=True,
                    )
                    | Q(
                        scope_type=ScopeType.CAMPAIGN,
                        team__isnull=True,
                        campaign__isnull=False,
                        content_type__isnull=True,
                        object_id__isnull=True,
                    )
                    | Q(
                        scope_type=ScopeType.OBJECT,
                        team__isnull=True,
                        campaign__isnull=True,
                        content_type__isnull=False,
                        object_id__isnull=False,
                    )
                ),
                name="identity_scope_grant_shape_valid",
            ),
            models.CheckConstraint(
                condition=Q(expires_at__isnull=True) | Q(expires_at__gt=F("starts_at")),
                name="identity_scope_grant_dates_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("identity", "scope_type")),
            models.Index(fields=("content_type", "object_id")),
        ]
        verbose_name = "Alcance de identidad"
        verbose_name_plural = "Alcances de identidades"


class TemporaryElevation(models.Model):
    identity = models.ForeignKey(
        IdentityProfile, on_delete=models.CASCADE, related_name="elevations"
    )
    action = models.CharField(max_length=32, choices=Action.choices)
    scope_type = models.CharField(max_length=16, choices=ScopeType.choices)
    team = models.ForeignKey(
        Team, null=True, blank=True, on_delete=models.PROTECT, related_name="elevations"
    )
    campaign = models.ForeignKey(
        Campaign,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="identity_elevations",
    )
    content_type = models.ForeignKey(
        ContentType, null=True, blank=True, on_delete=models.PROTECT
    )
    object_id = models.CharField(max_length=128, null=True, blank=True)
    reason = models.CharField(max_length=500)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_identity_elevations",
    )
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(expires_at__gt=F("starts_at")),
                name="identity_elevation_dates_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        scope_type=ScopeType.GLOBAL,
                        team__isnull=True,
                        campaign__isnull=True,
                        content_type__isnull=True,
                        object_id__isnull=True,
                    )
                    | Q(
                        scope_type=ScopeType.TEAM,
                        team__isnull=False,
                        campaign__isnull=True,
                        content_type__isnull=True,
                        object_id__isnull=True,
                    )
                    | Q(
                        scope_type=ScopeType.CAMPAIGN,
                        team__isnull=True,
                        campaign__isnull=False,
                        content_type__isnull=True,
                        object_id__isnull=True,
                    )
                    | Q(
                        scope_type=ScopeType.OBJECT,
                        team__isnull=True,
                        campaign__isnull=True,
                        content_type__isnull=False,
                        object_id__isnull=False,
                    )
                ),
                name="identity_elevation_scope_shape_valid",
            ),
        ]
        verbose_name = "Elevación temporal"
        verbose_name_plural = "Elevaciones temporales"


class ElevationUse(models.Model):
    """Append-only evidence of each authorization decision using an elevation."""

    elevation = models.ForeignKey(
        TemporaryElevation, on_delete=models.PROTECT, related_name="uses"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="elevation_uses",
    )
    action = models.CharField(max_length=32, choices=Action.choices)
    reason = models.CharField(max_length=500)
    scope_type = models.CharField(max_length=16, choices=ScopeType.choices)
    scope_snapshot = models.JSONField(default=dict)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_elevation_uses",
    )
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-occurred_at", "-pk")
        verbose_name = "Uso de elevación"
        verbose_name_plural = "Usos de elevación"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk:
            raise ValidationError("La auditoría de elevaciones es inmutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("La auditoría de elevaciones es inmutable.")
