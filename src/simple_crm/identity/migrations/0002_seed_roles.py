"""Seed the fixed business role catalog and action matrix."""

from typing import Any

from django.db import migrations


ROLE_ACTIONS = {
    "sales_representative": ("view", "create", "change"),
    "sales_manager": (
        "view",
        "create",
        "change",
        "reassign",
        "merge",
        "import",
        "resolve_quality",
    ),
    "data_steward": (
        "view",
        "change",
        "import",
        "resolve_quality",
        "manage_catalog",
    ),
    "report_viewer": ("view",),
    "privacy_audit_reviewer": ("view", "audit_view"),
    "system_administrator": (
        "view",
        "create",
        "change",
        "reassign",
        "merge",
        "import",
        "resolve_quality",
        "audit_view",
        "bulk_export",
        "manage_catalog",
        "elevate_access",
    ),
}

ROLE_LABELS = {
    "sales_representative": "Representante comercial",
    "sales_manager": "Gerente comercial",
    "data_steward": "Responsable de datos",
    "report_viewer": "Lector de reportes",
    "privacy_audit_reviewer": "Revisor de privacidad y auditoría",
    "system_administrator": "Administrador del sistema",
}


def seed_roles(apps: Any, schema_editor: Any) -> None:
    role_model = apps.get_model("simple_crm_identity", "Role")
    permission_model = apps.get_model("simple_crm_identity", "RolePermission")
    for code, label in ROLE_LABELS.items():
        role, _ = role_model.objects.get_or_create(code=code, defaults={"label": label})
        for action in ROLE_ACTIONS[code]:
            permission_model.objects.get_or_create(role=role, action=action)


def unseed_roles(apps: Any, schema_editor: Any) -> None:
    role_model = apps.get_model("simple_crm_identity", "Role")
    role_model.objects.filter(code__in=ROLE_LABELS).delete()


class Migration(migrations.Migration):
    dependencies = [("simple_crm_identity", "0001_initial")]

    operations = [migrations.RunPython(seed_roles, unseed_roles)]
