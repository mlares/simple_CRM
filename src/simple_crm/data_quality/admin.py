"""Read-oriented data-steward surface for import staging and lineage."""

from django.contrib import admin
from django.http import HttpRequest

from .models import (
    CandidateMatch,
    ImportAuditEvent,
    ImportBatch,
    QualityAuditEvent,
    QualityIssue,
    SourceCanonicalLink,
    SourceDocument,
    SourceRecord,
)


@admin.register(SourceDocument)
class SourceDocumentAdmin(admin.ModelAdmin):
    list_display = ("filename", "size_bytes", "checksum", "uploaded_by", "uploaded_at")
    search_fields = ("filename", "checksum")
    readonly_fields = (
        "filename",
        "content_type",
        "size_bytes",
        "checksum",
        "content",
        "uploaded_by",
        "uploaded_at",
    )


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "source_document",
        "parser_version",
        "application_version",
        "status",
        "import_actor",
        "approved_by",
        "created_at",
    )
    list_filter = ("status", "parser_version", "application_version")
    search_fields = ("checksum", "source_document__filename")
    readonly_fields = (
        "source_document",
        "checksum",
        "parser_version",
        "application_version",
        "status",
        "import_actor",
        "approved_by",
        "approved_at",
        "applied_at",
        "error_summary",
        "preview_counts",
        "created_at",
        "updated_at",
    )


@admin.register(SourceRecord)
class SourceRecordAdmin(admin.ModelAdmin):
    list_display = (
        "batch",
        "sheet_name",
        "row_number",
        "classification",
        "source_coordinate",
    )
    list_filter = ("classification", "sheet_name")
    search_fields = ("source_coordinate", "rejection_reason")
    readonly_fields = (
        "batch",
        "sheet_name",
        "row_number",
        "source_coordinate",
        "raw_payload",
        "raw_checksum",
        "classification",
        "errors",
        "warnings",
        "canonical_links",
        "rejection_reason",
        "created_at",
    )


@admin.register(SourceCanonicalLink)
class SourceCanonicalLinkAdmin(admin.ModelAdmin):
    list_display = (
        "source_record",
        "target_type",
        "target_id",
        "relation",
        "created_at",
    )
    list_filter = ("target_type", "relation")
    readonly_fields = (
        "source_record",
        "target_type",
        "target_id",
        "relation",
        "evidence",
        "created_at",
    )


@admin.register(ImportAuditEvent)
class ImportAuditEventAdmin(admin.ModelAdmin):
    list_display = ("batch", "action", "actor", "created_at")
    list_filter = ("action", "created_at")
    readonly_fields = ("batch", "actor", "action", "reason", "details", "created_at")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: ImportAuditEvent | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: ImportAuditEvent | None = None
    ) -> bool:
        return False


@admin.register(QualityIssue)
class QualityIssueAdmin(admin.ModelAdmin):
    list_display = (
        "rule_code",
        "severity",
        "state",
        "target_type",
        "target_id",
        "owner",
        "created_at",
    )
    list_filter = ("severity", "state", "rule_code")
    search_fields = ("rule_code", "target_type", "target_id")
    readonly_fields = (
        "rule_code",
        "severity",
        "state",
        "source_record",
        "target_type",
        "target_id",
        "owner",
        "decision",
        "acceptance_reason",
        "created_at",
        "updated_at",
        "resolved_at",
    )


@admin.register(CandidateMatch)
class CandidateMatchAdmin(admin.ModelAdmin):
    list_display = (
        "survivor",
        "candidate",
        "match_type",
        "confidence",
        "state",
        "reviewed_by",
    )
    list_filter = ("match_type", "state")
    readonly_fields = (
        "survivor",
        "candidate",
        "match_type",
        "confidence",
        "evidence",
        "state",
        "source_record",
        "reviewed_by",
        "reviewed_at",
        "review_reason",
        "created_at",
    )


@admin.register(QualityAuditEvent)
class QualityAuditEventAdmin(admin.ModelAdmin):
    list_display = ("action", "actor", "target_type", "target_id", "created_at")
    list_filter = ("action", "target_type")
    readonly_fields = (
        "action",
        "actor",
        "target_type",
        "target_id",
        "reason",
        "before_state",
        "after_state",
        "source_evidence",
        "created_at",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: QualityAuditEvent | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: QualityAuditEvent | None = None
    ) -> bool:
        return False
