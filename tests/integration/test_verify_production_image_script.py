from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_production_image_verifier_covers_rendered_page_static_manifest_and_runtime() -> (
    None
):
    script = (PROJECT_ROOT / "scripts" / "verify-production-image.sh").read_text(
        encoding="utf-8"
    )
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    entrypoint = (PROJECT_ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")

    assert "docker build" in script
    assert '"${BASE_URL}/"' in script
    assert "bootstrap\\.min" in script
    assert "staticfiles.json" in script
    assert "test -w /tmp/simplecrm-runtime" in script
    assert "test -S /tmp/simplecrm-runtime/gunicorn.ctl" in script
    assert "DJANGO_STATIC_ROOT=/app/staticfiles" in dockerfile
    assert "XDG_RUNTIME_DIR=/tmp/simplecrm-runtime" in dockerfile
    assert "--worker-tmp-dir" in entrypoint
