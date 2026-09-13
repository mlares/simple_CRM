"""Bounded administrative surface for identity stewardship."""

from django.contrib import admin

from .models import (
    ElevationUse,
    IdentityProfile,
    Role,
    RoleAssignment,
    RolePermission,
    ScopeGrant,
    Team,
    TeamMembership,
    TemporaryElevation,
)


@admin.register(IdentityProfile)
class IdentityProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "disabled_at", "updated_at")
    search_fields = ("user__username", "user__email", "display_name", "oidc_subject")
    readonly_fields = ("updated_at",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "is_active")
    search_fields = ("code", "label")


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "action")
    list_filter = ("action", "role")


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("identity", "role", "starts_at", "ends_at")
    list_filter = ("role",)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "is_active")
    search_fields = ("code", "label")


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("identity", "team", "starts_at", "ends_at")
    list_filter = ("team",)


@admin.register(ScopeGrant)
class ScopeGrantAdmin(admin.ModelAdmin):
    list_display = (
        "identity",
        "scope_type",
        "team",
        "campaign",
        "starts_at",
        "expires_at",
    )
    list_filter = ("scope_type",)


@admin.register(TemporaryElevation)
class TemporaryElevationAdmin(admin.ModelAdmin):
    list_display = (
        "identity",
        "action",
        "scope_type",
        "approved_by",
        "starts_at",
        "expires_at",
        "revoked_at",
    )
    list_filter = ("action", "scope_type")
    readonly_fields = ("created_at",)


@admin.register(ElevationUse)
class ElevationUseAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "approved_by", "occurred_at")
    readonly_fields = (
        "elevation",
        "actor",
        "action",
        "reason",
        "scope_type",
        "scope_snapshot",
        "approved_by",
        "occurred_at",
    )

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object | None = None) -> bool:
        return False
