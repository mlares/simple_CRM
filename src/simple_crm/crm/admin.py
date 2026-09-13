"""Admin maintenance surface for the temporary Data Stewards boundary."""

from typing import cast

from django.contrib import admin
from django.db import models
from django.http import HttpRequest

from .models import (
    Address,
    Campaign,
    CatalogAuditEntry,
    CatalogBase,
    ContactPoint,
    Country,
    InteractionChannel,
    InteractionOutcome,
    Lead,
    LeadAssignment,
    LeadParty,
    LeadStageHistory,
    LeadStatus,
    Locality,
    Organization,
    OrganizationPerson,
    Party,
    PartyAlias,
    PartyContactPoint,
    PartySpecialty,
    Person,
    Province,
    Specialty,
)


class CatalogAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "label")
    ordering = ("sort_order", "label", "code")

    def get_readonly_fields(
        self, request: HttpRequest, obj: CatalogBase | None = None
    ) -> tuple[str, ...]:
        return ("code",) if obj is not None else ()

    def has_delete_permission(
        self, request: HttpRequest, obj: CatalogBase | None = None
    ) -> bool:
        return False

    def save_model(
        self,
        request: HttpRequest,
        obj: CatalogBase,
        form: object,
        change: bool,
    ) -> None:
        obj.save(actor=cast(models.Model, request.user))


class CatalogAuditEntryAdmin(admin.ModelAdmin):
    list_display = ("catalog_model", "catalog_code", "action", "actor", "created_at")
    readonly_fields = (
        "catalog_model",
        "catalog_code",
        "action",
        "actor",
        "changes",
        "snapshot",
        "created_at",
    )
    search_fields = ("catalog_model", "catalog_code")
    list_filter = ("action", "catalog_model")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: CatalogAuditEntry | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: CatalogAuditEntry | None = None
    ) -> bool:
        return False


for catalog_model in (
    Campaign,
    LeadStatus,
    InteractionChannel,
    InteractionOutcome,
    Specialty,
    Country,
    Province,
    Locality,
):
    admin.site.register(catalog_model, CatalogAdmin)

admin.site.register(CatalogAuditEntry, CatalogAuditEntryAdmin)


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "party_type",
        "data_readiness",
        "lifecycle",
        "version",
    )
    list_filter = ("party_type", "data_readiness", "lifecycle")
    search_fields = ("display_name", "canonical_name")
    readonly_fields = ("canonical_name", "version", "created_at", "updated_at")


@admin.register(ContactPoint)
class ContactPointAdmin(admin.ModelAdmin):
    list_display = (
        "kind",
        "raw_value",
        "normalized_value",
        "quality_state",
        "is_suppressed",
    )
    list_filter = ("kind", "quality_state", "is_suppressed", "is_active")
    search_fields = ("raw_value", "normalized_value")
    readonly_fields = ("normalized_value", "quality_state", "created_at", "updated_at")


admin.site.register((Person, Organization, OrganizationPerson))
admin.site.register((PartyContactPoint, PartySpecialty, Address, PartyAlias))


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "lead_number",
        "campaign",
        "current_stage",
        "data_readiness",
        "lifecycle",
        "version",
    )
    list_filter = ("campaign", "current_stage", "data_readiness", "lifecycle")
    search_fields = ("lead_number",)
    readonly_fields = ("lead_number", "version", "created_at", "updated_at")


@admin.register(LeadAssignment)
class LeadAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "lead",
        "identity",
        "assignment_role",
        "assigned_at",
        "unassigned_at",
    )
    list_filter = ("assignment_role", "unassigned_at")
    readonly_fields = (
        "lead",
        "identity",
        "assignment_role",
        "assigned_at",
        "unassigned_at",
        "assigned_by",
    )


@admin.register(LeadParty)
class LeadPartyAdmin(admin.ModelAdmin):
    list_display = ("lead", "party", "party_role")
    list_filter = ("party_role",)
    readonly_fields = ("lead", "party", "party_role")


@admin.register(LeadStageHistory)
class LeadStageHistoryAdmin(admin.ModelAdmin):
    list_display = ("lead", "from_stage", "to_stage", "occurred_at", "actor")
    list_filter = ("to_stage", "occurred_at")
    readonly_fields = (
        "lead",
        "from_stage",
        "to_stage",
        "occurred_at",
        "actor",
        "reason",
        "transition_fields",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: LeadStageHistory | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: LeadStageHistory | None = None
    ) -> bool:
        return False
