"""Bounded read surface for activity records."""

from django.contrib import admin
from django.http import HttpRequest

from .models import ActivityAuditEvent, Interaction, InteractionParticipant, Task


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = (
        "lead",
        "occurrence_date",
        "occurrence_time",
        "direction",
        "channel",
        "outcome",
        "result",
        "actor",
    )
    list_filter = ("direction", "result", "channel", "outcome")
    search_fields = ("lead__lead_number", "note")
    readonly_fields = (
        "lead",
        "occurrence_date",
        "occurrence_time",
        "direction",
        "channel",
        "outcome",
        "result",
        "note",
        "actor",
        "source",
        "created_at",
    )


@admin.register(InteractionParticipant)
class InteractionParticipantAdmin(admin.ModelAdmin):
    list_display = ("interaction", "party", "participant_role")
    list_filter = ("participant_role",)
    readonly_fields = ("interaction", "party", "participant_role")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("lead", "description", "owner", "due_date", "status", "priority")
    list_filter = ("status", "priority", "due_date")
    search_fields = ("lead__lead_number", "description")
    readonly_fields = (
        "lead",
        "owner",
        "description",
        "due_date",
        "status",
        "priority",
        "completed_at",
        "completion_note",
        "rescheduled_at",
        "reschedule_reason",
        "originating_interaction",
        "created_at",
        "updated_at",
    )


@admin.register(ActivityAuditEvent)
class ActivityAuditEventAdmin(admin.ModelAdmin):
    list_display = ("lead", "action", "actor", "created_at")
    list_filter = ("action", "created_at")
    readonly_fields = (
        "lead",
        "interaction",
        "task",
        "actor",
        "action",
        "details",
        "created_at",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: ActivityAuditEvent | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: ActivityAuditEvent | None = None
    ) -> bool:
        return False
