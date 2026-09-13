"""Use PostgreSQL triggers for protections SQLite cannot demonstrate."""

from typing import Any

from django.db import migrations


CATALOG_TABLES = (
    "simple_crm_crm_campaign",
    "simple_crm_crm_leadstatus",
    "simple_crm_crm_interactionchannel",
    "simple_crm_crm_interactionoutcome",
    "simple_crm_crm_specialty",
    "simple_crm_crm_country",
    "simple_crm_crm_province",
    "simple_crm_crm_locality",
)


def install_postgres_guards(apps: Any, schema_editor: Any) -> None:
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE FUNCTION simple_crm_catalog_guard() RETURNS trigger AS $$
            BEGIN
                IF TG_OP = 'DELETE' THEN
                    RAISE EXCEPTION 'Catalog rows are historical and cannot be deleted';
                END IF;
                IF NEW.code IS DISTINCT FROM OLD.code THEN
                    RAISE EXCEPTION 'Catalog stable codes cannot be changed';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            CREATE FUNCTION simple_crm_catalog_audit_guard() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'Catalog audit rows are append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        for table in CATALOG_TABLES:
            cursor.execute(
                f"CREATE TRIGGER {table}_guard BEFORE UPDATE OR DELETE ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION simple_crm_catalog_guard()"
            )
        cursor.execute(
            "CREATE TRIGGER simple_crm_crm_catalogauditentry_guard "
            "BEFORE UPDATE OR DELETE ON simple_crm_crm_catalogauditentry "
            "FOR EACH ROW EXECUTE FUNCTION simple_crm_catalog_audit_guard()"
        )


def remove_postgres_guards(apps: Any, schema_editor: Any) -> None:
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        for table in CATALOG_TABLES:
            cursor.execute(f"DROP TRIGGER IF EXISTS {table}_guard ON {table}")
        cursor.execute(
            "DROP TRIGGER IF EXISTS simple_crm_crm_catalogauditentry_guard "
            "ON simple_crm_crm_catalogauditentry"
        )
        cursor.execute("DROP FUNCTION IF EXISTS simple_crm_catalog_guard()")
        cursor.execute("DROP FUNCTION IF EXISTS simple_crm_catalog_audit_guard()")


class Migration(migrations.Migration):
    dependencies = [("simple_crm_crm", "0002_seed_baseline_catalogs")]

    operations = [migrations.RunPython(install_postgres_guards, remove_postgres_guards)]
