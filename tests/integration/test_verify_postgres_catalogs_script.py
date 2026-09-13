from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_catalog_postgres_verifier_is_dedicated_gated_and_non_disclosing() -> None:
    script = (PROJECT_ROOT / "scripts" / "verify-postgres-catalogs.sh").read_text(
        encoding="utf-8"
    )

    assert "SIMPLE_CRM_POSTGRES_ACCEPTANCE" in script
    assert "simple_crm_crm004_test" in script
    assert "PostgreSQL 18 is required" in script
    assert "Dedicated database must be empty before acceptance" in script
    assert "Duplicate code was accepted" in script
    assert "Unknown foreign key was accepted" in script
    assert "Database allowed a code change" in script
    assert "Database allowed audit mutation" in script
    assert 'echo "$DATABASE_URL"' not in script
    assert 'print(os.environ["DATABASE_URL"])' not in script
