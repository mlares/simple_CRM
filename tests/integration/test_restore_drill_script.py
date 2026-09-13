from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_restore_drill_is_explicitly_gated_and_database_name_scoped() -> None:
    script = (PROJECT_ROOT / "scripts/restore-drill.sh").read_text(encoding="utf-8")

    assert "SIMPLE_CRM_RESTORE_DRILL" in script
    assert "simple_crm_crm020_source" in script
    assert "simple_crm_crm020_restore" in script
    assert "pg_dump --format=custom" in script
    assert "pg_restore --clean" in script
    assert "SourceCanonicalLink" in script
    assert "MetricDefinition" in script
    assert 'echo "$SOURCE_DATABASE_URL"' not in script
    assert 'echo "$RESTORE_DATABASE_URL"' not in script
