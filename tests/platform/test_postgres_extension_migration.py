from importlib import import_module

from django.contrib.postgres.operations import TrigramExtension


def test_platform_migration_enables_pg_trgm() -> None:
    migration = import_module(
        "simple_crm.platform.migrations.0001_enable_pg_trgm"
    ).Migration

    assert migration.initial is True
    assert migration.dependencies == []
    assert len(migration.operations) == 1
    assert isinstance(migration.operations[0], TrigramExtension)
