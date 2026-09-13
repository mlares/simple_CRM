from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_postgres_security_verifier_is_opt_in_and_non_disclosing() -> None:
    script = (PROJECT_ROOT / "scripts" / "verify-postgres-security.sh").read_text(
        encoding="utf-8"
    )

    assert "SIMPLE_CRM_POSTGRES_SECURITY_ACCEPTANCE" in script
    assert "simple_crm_crm019_security_test" in script
    assert "PostgreSQL 18 is required" in script
    assert "CREATE ROLE" in script
    assert "NOBYPASSRLS" in script
    assert "ENABLE ROW LEVEL SECURITY" in script
    assert "current_setting('simple_crm.campaign_id', true)" in script
    assert "has_table_privilege" in script
    assert "Web role can create database roles" in script
    assert 'echo "$DATABASE_URL"' not in script
    assert 'print(os.environ["DATABASE_URL"])' not in script
    assert "CRM019_WEB_PASSWORD" in script
