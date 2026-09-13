#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
python3 - <<'PY'
import base64
import hashlib
import json
from pathlib import Path
import sys

manifest = json.loads(Path("THIRD_PARTY_LICENSES/vendor-assets.json").read_text())
expected_assets = {
    ("Bootstrap", "5.3.8", "MIT", "The MIT License (MIT)"),
    ("HTMX", "2.0.10", "0BSD", "Zero-Clause BSD"),
}
actual_assets = {
    (asset["name"], asset["version"], asset["license"], asset["license_header"])
    for asset in manifest["assets"]
}
if actual_assets != expected_assets:
    print("vendored asset manifest has an unexpected provenance set", file=sys.stderr)
    raise SystemExit(1)
for asset in manifest["assets"]:
    path = Path(asset["local_path"])
    license_path = Path(asset["license_path"])
    if asset["status"] != "verified" or not path.is_file() or not license_path.is_file():
        print(f"vendored asset pending: {asset['name']} {asset['version']}", file=sys.stderr)
        raise SystemExit(2)
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != asset["sha256"]:
        print(f"vendored asset checksum mismatch: {asset['name']}", file=sys.stderr)
        raise SystemExit(1)
    sri = "sha384-" + base64.b64encode(hashlib.sha384(content).digest()).decode()
    if sri != asset["sri"]:
        print(f"vendored asset SRI mismatch: {asset['name']}", file=sys.stderr)
        raise SystemExit(1)
    license_digest = hashlib.sha256(license_path.read_bytes()).hexdigest()
    if license_digest != asset["license_sha256"]:
        print(f"vendored license checksum mismatch: {asset['name']}", file=sys.stderr)
        raise SystemExit(1)
    if not license_path.read_text(encoding="utf-8").startswith(asset["license_header"]):
        print(f"vendored license semantic mismatch: {asset['name']}", file=sys.stderr)
        raise SystemExit(1)
    if f"@{asset['version']}" not in asset["source_url"]:
        print(f"vendored asset provenance mismatch: {asset['name']}", file=sys.stderr)
        raise SystemExit(1)
print("vendored assets verified")
PY
