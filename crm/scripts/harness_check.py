"""Validate the provider-neutral harness metadata."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALID_STATUSES = {
    "pending",
    "in_progress",
    "review",
    "changes_requested",
    "done",
    "blocked",
}
REQUIRED_FILES = (
    "AGENTS.md",
    "harness.json",
    "feature_list.json",
    "progress/current.md",
    "progress/history.md",
    "agents/roles/leader.md",
    "agents/roles/implementer.md",
    "agents/roles/reviewer.md",
    "agents/roles/explorer.md",
)


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def check() -> list[str]:
    errors: list[str] = []
    for relative_path in REQUIRED_FILES:
        if not (ROOT / relative_path).is_file():
            errors.append(f"missing required file: {relative_path}")

    try:
        harness = load_json(ROOT / "harness.json")
    except Exception as exc:  # noqa: BLE001 - make the CLI diagnostic useful
        errors.append(f"invalid harness.json: {exc}")
        harness = {}

    try:
        feature_data = load_json(ROOT / "feature_list.json")
    except Exception as exc:  # noqa: BLE001 - make the CLI diagnostic useful
        errors.append(f"invalid feature_list.json: {exc}")
        feature_data = {}

    features = feature_data.get("features", [])
    if not isinstance(features, list):
        errors.append("feature_list.json.features must be a list")
        features = []

    seen_ids: set[str] = set()
    in_progress = 0
    for feature in features:
        if not isinstance(feature, dict):
            errors.append("every feature must be an object")
            continue
        feature_id = feature.get("id")
        feature_key = repr(feature_id)
        if feature_key in seen_ids:
            errors.append(f"duplicate feature id: {feature_id}")
        seen_ids.add(feature_key)
        status = feature.get("status")
        if status not in VALID_STATUSES:
            errors.append(f"invalid status for feature {feature_id}: {status}")
        if status == "in_progress":
            in_progress += 1
        if status == "done":
            acceptance = feature.get("acceptance")
            if not isinstance(acceptance, list) or not acceptance:
                errors.append(f"done feature {feature_id} has no acceptance criteria")
            for report_key in ("implementation_report", "review_report"):
                report = feature.get(report_key)
                if not isinstance(report, str) or not report:
                    errors.append(f"done feature {feature_id} has no {report_key}")
                elif not (ROOT / report).is_file():
                    errors.append(f"missing {report_key} for done feature {feature_id}: {report}")

    if in_progress > 1:
        errors.append("more than one feature is in_progress")

    if harness.get("schema_version") != 1:
        errors.append("harness.json.schema_version must be 1")
    if not isinstance(harness.get("test_command", ""), str):
        errors.append("harness.json.test_command must be a string")
    return errors


def main() -> int:
    errors = check()
    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        return 1
    print("[OK] harness metadata is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
