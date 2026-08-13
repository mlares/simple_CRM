from importlib import import_module
from inspect import getsource


def test_postgres_catalog_guard_migration_covers_codes_and_audit_rows() -> None:
    migration = import_module("simple_crm.crm.migrations.0003_postgres_catalog_guards")

    assert len(migration.CATALOG_TABLES) == 8
    assert "simple_crm_crm_campaign" in migration.CATALOG_TABLES
    assert "simple_crm_crm_catalogauditentry" in getsource(
        migration.install_postgres_guards
    )
