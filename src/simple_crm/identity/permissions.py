"""Stable role/action policy data for the identity boundary."""

from .models import Action

ROLE_ACTIONS: dict[str, tuple[str, ...]] = {
    "sales_representative": (
        Action.VIEW,
        Action.CREATE,
        Action.CHANGE,
    ),
    "sales_manager": (
        Action.VIEW,
        Action.CREATE,
        Action.CHANGE,
        Action.REASSIGN,
        Action.MERGE,
        Action.IMPORT,
        Action.RESOLVE_QUALITY,
    ),
    "data_steward": (
        Action.VIEW,
        Action.CHANGE,
        Action.IMPORT,
        Action.RESOLVE_QUALITY,
        Action.MANAGE_CATALOG,
    ),
    "report_viewer": (Action.VIEW,),
    "privacy_audit_reviewer": (Action.VIEW, Action.AUDIT_VIEW),
    "system_administrator": tuple(Action.values),
}

ROLE_LABELS = {
    "sales_representative": "Representante comercial",
    "sales_manager": "Gerente comercial",
    "data_steward": "Responsable de datos",
    "report_viewer": "Lector de reportes",
    "privacy_audit_reviewer": "Revisor de privacidad y auditoría",
    "system_administrator": "Administrador del sistema",
}
