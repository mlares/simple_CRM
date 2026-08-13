from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_postgres_verifier_is_explicitly_gated_and_non_disclosing() -> None:
    script = (PROJECT_ROOT / "scripts" / "verify-postgres.sh").read_text(
        encoding="utf-8"
    )

    assert "SIMPLE_CRM_POSTGRES_ACCEPTANCE" in script
    assert "simple_crm_crm003_test" in script
    assert "PostgreSQL 18 is required" in script
    assert "SHOW server_version_num" in script
    assert 'call_command("migrate"' in script
    assert "Second migration run was not a no-op" in script
    assert "pg_trgm" in script
    assert 'echo "$DATABASE_URL"' not in script
    assert 'print(os.environ["DATABASE_URL"])' not in script
