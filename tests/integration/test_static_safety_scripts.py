import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_static_collection_and_repository_safety_verifiers_pass() -> None:
    environment = {**os.environ, "PYTHON_BIN": sys.executable}
    static = subprocess.run(
        ["bash", "scripts/verify-static.sh"],
        cwd=PROJECT_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    safety = subprocess.run(
        ["bash", "scripts/verify-repository-safety.sh"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert static.returncode == 0, static.stderr
    assert safety.returncode == 0, safety.stderr


def test_vendored_asset_verifier_accepts_verified_official_bytes() -> None:
    result = subprocess.run(
        ["bash", "scripts/verify-vendored-assets.sh"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "vendored assets verified"
