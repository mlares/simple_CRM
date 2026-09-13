from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_operations_verifier_requires_non_root_image_and_recovery_contract() -> None:
    script = (PROJECT_ROOT / "scripts" / "verify-operations.sh").read_text(
        encoding="utf-8"
    )
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "USER 10001:10001" in script
    assert "Dockerfile" in script
    assert "restore-drill.sh" in script
    assert "verify-production-image.sh" in script
    assert "USER 10001:10001" in dockerfile
    assert "uv.lock" in dockerfile
    assert "DJANGO_STATIC_ROOT=/app/staticfiles" in dockerfile
    assert "XDG_RUNTIME_DIR=/tmp/simplecrm-runtime" in dockerfile
    assert "run_worker" in dockerfile or "run_worker" in (
        PROJECT_ROOT / "docker/entrypoint.sh"
    ).read_text(encoding="utf-8")
    assert "runserver" not in dockerfile


def test_observability_contract_contains_required_sli_names() -> None:
    content = (PROJECT_ROOT / "ops/observability.yaml").read_text(encoding="utf-8")
    for name in (
        "availability",
        "latency",
        "error_rate",
        "database_saturation",
        "job_backlog",
        "import_failures",
        "backup_freshness",
    ):
        assert f"  {name}:" in content
