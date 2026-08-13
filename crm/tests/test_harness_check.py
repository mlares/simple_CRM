"""Executable contract tests for the agent-delivery harness metadata."""

import json
import shutil
import subprocess
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest

CRM_ROOT = Path(__file__).parents[1]
HARNESS_CHECK_PATH = CRM_ROOT / "scripts" / "harness_check.py"
CHECKER = run_path(HARNESS_CHECK_PATH)
check: Callable[[Path | None], list[str]] = CHECKER["check"]
load_json: Callable[[Path], dict[str, Any]] = CHECKER["load_json"]
relative_file: Callable[[Path, object], Path | None] = CHECKER["_relative_file"]
acceptance_evidence_is_concrete: Callable[[str, str], bool] = CHECKER[
    "_acceptance_evidence_is_concrete"
]

REQUIRED_FIXTURE_FILES = (
    "AGENTS.md",
    "progress/current.md",
    "progress/history.md",
    "agents/roles/orchestrator.md",
    "agents/roles/implementer.md",
    "agents/roles/validator.md",
    "agents/roles/explorer.md",
    "progress/templates/task_envelope.json",
    "progress/templates/implementation_report.md",
    "progress/templates/validation_report.md",
)
AGENT_POLICY = {
    "supported_models": {
        model: {
            "reasoning_efforts": ["none", "low", "medium", "high", "xhigh", "max"]
        }
        for model in ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna")
    },
    "role_defaults": {
        "orchestrator": {"model": "gpt-5.6-sol", "reasoning_effort": "high"},
        "implementer": {"model": "gpt-5.6-terra", "reasoning_effort": "high"},
        "validator": {"model": "gpt-5.6-sol", "reasoning_effort": "high"},
        "explorer": {"model": "gpt-5.6-luna", "reasoning_effort": "medium"},
    },
}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def make_feature(
    feature_id: str = "CRM-TEST",
    *,
    status: str = "pending",
    depends_on: list[str] | None = None,
) -> dict[str, Any]:
    feature: dict[str, Any] = {
        "id": feature_id,
        "status": status,
        "depends_on": [] if depends_on is None else depends_on,
        "requirements": [{"id": f"{feature_id}-R01", "statement": "Requirement"}],
        "acceptance": [{"id": f"{feature_id}-AC01", "criterion": "Criterion"}],
    }
    histories = {
        "in_progress": ["pending", "in_progress"],
        "review": ["pending", "in_progress", "review"],
        "changes_requested": [
            "pending",
            "in_progress",
            "review",
            "changes_requested",
        ],
        "done": ["pending", "in_progress", "review", "done"],
        "blocked": ["pending", "blocked"],
    }
    if status in histories:
        feature["status_history"] = histories[status]
    return feature


def make_envelope(feature: dict[str, Any]) -> dict[str, Any]:
    feature_id = feature["id"]
    return {
        "schema_version": 1,
        "feature_id": feature_id,
        "requirement_ids": [item["id"] for item in feature["requirements"]],
        "acceptance_ids": [item["id"] for item in feature["acceptance"]],
        "dependencies": feature["depends_on"],
        "allowed_scope": ["crm/allowed.py"],
        "out_of_scope": ["crm/excluded.py"],
        "baseline_revision": "0123456789abcdef",
        "implementation_report": f"progress/impl_{feature_id}.md",
        "validation_report": f"progress/validation_{feature_id}.md",
        "implementer": "implementer-agent",
        "validator": "validator-agent",
        "agent_assignments": {
            "orchestrator": {
                "agent_id": "orchestrator-agent",
                "model": "gpt-5.6-sol",
                "reasoning_effort": "high",
                "source": "role_default",
            },
            "implementer": {
                "agent_id": "implementer-agent",
                "model": "gpt-5.6-terra",
                "reasoning_effort": "high",
                "source": "role_default",
            },
            "validator": {
                "agent_id": "validator-agent",
                "model": "gpt-5.6-sol",
                "reasoning_effort": "high",
                "source": "role_default",
            },
        },
        "verification_commands": [
            "cd crm && ./init.sh",
            "UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q",
        ],
    }


def activate(root: Path, feature: dict[str, Any]) -> dict[str, Any]:
    feature_id = feature["id"]
    envelope_path = f"progress/tasks/{feature_id}.json"
    feature["task_envelope"] = envelope_path
    envelope = make_envelope(feature)
    write_json(root / envelope_path, envelope)
    return envelope


def implementation_report(feature: dict[str, Any], *, evidence: bool = True) -> str:
    rows = []
    if evidence:
        rows = [
            f"| `{item['id']}` | `crm/implementation.py` implements the criterion | "
            "`pytest -q` passes | Pass |"
            for item in feature["acceptance"]
        ]
    return "\n".join(
        [
            f"# Implementation report — {feature['id']}",
            "",
            "## Acceptance evidence",
            "",
            "| Acceptance ID | Implementation evidence | Verification evidence | Result |",
            "| --- | --- | --- | --- |",
            *rows,
            "",
            "## Verification",
            "",
            "`pytest -q` exited 0.",
        ]
    )


def validation_report(
    feature: dict[str, Any], *, verdict: str = "APPROVED", evidence: bool = True
) -> str:
    rows = []
    if evidence:
        rows = [
            f"| `{item['id']}` | `crm/implementation.py` and its test | Pass | None |"
            for item in feature["acceptance"]
        ]
    return "\n".join(
        [
            f"# Validation report — {feature['id']}",
            "",
            "## Verdict",
            "",
            f"`{verdict}`",
            "",
            "## Acceptance evidence",
            "",
            "| Acceptance ID | Evidence inspected | Result | Finding |",
            "| --- | --- | --- | --- |",
            *rows,
            "",
            "## Verification",
            "",
            "`pytest -q` exited 0.",
        ]
    )


def add_reports(
    root: Path,
    feature: dict[str, Any],
    *,
    verdict: str = "APPROVED",
    implementation_evidence: bool = True,
    validation_evidence: bool = True,
) -> None:
    feature_id = feature["id"]
    implementation_path = f"progress/impl_{feature_id}.md"
    validation_path = f"progress/validation_{feature_id}.md"
    feature["implementation_report"] = implementation_path
    feature["validation_report"] = validation_path
    (root / implementation_path).write_text(
        implementation_report(feature, evidence=implementation_evidence), encoding="utf-8"
    )
    (root / validation_path).write_text(
        validation_report(feature, verdict=verdict, evidence=validation_evidence),
        encoding="utf-8",
    )


def save_features(root: Path, features: list[dict[str, Any]]) -> None:
    write_json(root / "feature_list.json", {"schema_version": 2, "features": features})


@pytest.fixture
def harness_root(tmp_path: Path) -> Path:
    for relative_path in REQUIRED_FIXTURE_FILES:
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}" if path.suffix == ".json" else "fixture\n", encoding="utf-8")
    write_json(
        tmp_path / "harness.json",
        {
            "schema_version": 1,
            "primary_branch": "master",
            "test_command": "UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q",
            "agent_policy": deepcopy(AGENT_POLICY),
        },
    )
    save_features(tmp_path, [make_feature()])
    return tmp_path


def assert_error(root: Path, message: str) -> None:
    errors = check(root)
    assert any(message in error for error in errors), errors


def test_current_repository_metadata_is_valid() -> None:
    assert check(CRM_ROOT) == []


def test_isolated_pending_repository_is_valid(harness_root: Path) -> None:
    assert check(harness_root) == []


def test_isolated_active_repository_with_structured_envelope_is_valid(
    harness_root: Path,
) -> None:
    feature = make_feature(status="in_progress")
    activate(harness_root, feature)
    save_features(harness_root, [feature])

    assert check(harness_root) == []


def test_isolated_done_repository_with_approved_evidence_is_valid(
    harness_root: Path,
) -> None:
    feature = make_feature(status="done")
    add_reports(harness_root, feature)
    save_features(harness_root, [feature])

    assert check(harness_root) == []


def test_system_python_validates_done_state_reports(harness_root: Path) -> None:
    feature = make_feature(status="done")
    add_reports(harness_root, feature)
    save_features(harness_root, [feature])
    system_python = shutil.which("python3")
    assert system_python is not None
    closure_check = (
        "from pathlib import Path; "
        "from runpy import run_path; "
        "import sys; "
        "module = run_path(sys.argv[1]); "
        "errors = module['check'](Path(sys.argv[2])); "
        "print(errors); "
        "raise SystemExit(bool(errors))"
    )

    result = subprocess.run(
        [system_python, "-c", closure_check, str(HARNESS_CHECK_PATH), str(harness_root)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "[]"
    checker_source = HARNESS_CHECK_PATH.read_text(encoding="utf-8")
    assert ".removesuffix(" not in checker_source
    assert ".removeprefix(" not in checker_source


@pytest.mark.parametrize(
    "relative_path",
    [
        "agents/roles/orchestrator.md",
        "agents/roles/implementer.md",
        "agents/roles/validator.md",
        "agents/roles/explorer.md",
        "progress/templates/task_envelope.json",
        "progress/templates/implementation_report.md",
        "progress/templates/validation_report.md",
    ],
)
def test_canonical_roles_and_templates_are_required(
    harness_root: Path, relative_path: str
) -> None:
    (harness_root / relative_path).unlink()

    assert_error(harness_root, f"missing required file: {relative_path}")


def test_load_json_rejects_a_non_object(tmp_path: Path) -> None:
    invalid_json = tmp_path / "list.json"
    invalid_json.write_text("[]", encoding="utf-8")

    with pytest.raises(TypeError, match="must contain a JSON object"):
        load_json(invalid_json)


def test_relative_file_accepts_a_real_path_inside_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    target = root / "progress" / "report.md"
    target.parent.mkdir(parents=True)
    target.write_text("evidence\n", encoding="utf-8")

    assert relative_file(root, "progress/report.md") == target.resolve()


def test_relative_file_accepts_an_in_root_symlink(tmp_path: Path) -> None:
    root = tmp_path / "root"
    target = root / "evidence" / "report.md"
    link = root / "progress" / "report.md"
    target.parent.mkdir(parents=True)
    link.parent.mkdir(parents=True)
    target.write_text("evidence\n", encoding="utf-8")
    link.symlink_to(target)

    assert relative_file(root, "progress/report.md") == target.resolve()


def test_relative_file_rejects_a_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside-report.md"
    link = root / "progress" / "report.md"
    link.parent.mkdir(parents=True)
    outside.write_text("untrusted evidence\n", encoding="utf-8")
    link.symlink_to(outside)

    assert relative_file(root, "progress/report.md") is None


@pytest.mark.parametrize("id_kind", ["feature", "requirement", "acceptance"])
def test_duplicate_ids_are_rejected(harness_root: Path, id_kind: str) -> None:
    first = make_feature("CRM-A")
    second = make_feature("CRM-B")
    if id_kind == "feature":
        second["id"] = first["id"]
    elif id_kind == "requirement":
        second["requirements"][0]["id"] = first["requirements"][0]["id"]
    else:
        second["acceptance"][0]["id"] = first["acceptance"][0]["id"]
    save_features(harness_root, [first, second])

    assert_error(harness_root, f"duplicate {id_kind} id")


def test_missing_dependency_is_rejected(harness_root: Path) -> None:
    save_features(harness_root, [make_feature(depends_on=["CRM-MISSING"])])

    assert_error(harness_root, "has missing dependency: CRM-MISSING")


def test_dependency_field_must_be_a_list(harness_root: Path) -> None:
    feature = make_feature()
    feature["depends_on"] = "CRM-A"
    save_features(harness_root, [feature])

    assert_error(harness_root, ".depends_on must be a list")


def test_duplicate_dependency_is_rejected(harness_root: Path) -> None:
    dependency = make_feature("CRM-A")
    feature = make_feature("CRM-B", depends_on=["CRM-A", "CRM-A"])
    save_features(harness_root, [dependency, feature])

    assert_error(harness_root, ".depends_on contains duplicate value: CRM-A")


def test_self_dependency_is_rejected(harness_root: Path) -> None:
    save_features(harness_root, [make_feature(depends_on=["CRM-TEST"])])

    assert_error(harness_root, "feature CRM-TEST cannot depend on itself")


def test_dependency_cycle_is_rejected(harness_root: Path) -> None:
    first = make_feature("CRM-A", depends_on=["CRM-B"])
    second = make_feature("CRM-B", depends_on=["CRM-A"])
    save_features(harness_root, [first, second])

    assert_error(harness_root, "dependency cycle: CRM-A -> CRM-B -> CRM-A")


@pytest.mark.parametrize("status", ["in_progress", "done"])
def test_active_or_done_feature_requires_completed_dependencies(
    harness_root: Path, status: str
) -> None:
    dependency = make_feature("CRM-A")
    feature = make_feature("CRM-B", status=status, depends_on=["CRM-A"])
    if status == "in_progress":
        activate(harness_root, feature)
    else:
        add_reports(harness_root, feature)
    save_features(harness_root, [dependency, feature])

    assert_error(harness_root, "requires dependency CRM-A to be done")


def test_more_than_one_active_feature_is_rejected(harness_root: Path) -> None:
    first = make_feature("CRM-A", status="in_progress")
    second = make_feature("CRM-B", status="review")
    activate(harness_root, first)
    activate(harness_root, second)
    second["implementation_report"] = "progress/impl_CRM-B.md"
    (harness_root / second["implementation_report"]).write_text(
        implementation_report(second), encoding="utf-8"
    )
    save_features(harness_root, [first, second])

    assert_error(harness_root, "more than one active feature: CRM-A, CRM-B")


def test_illegal_status_transition_is_rejected(harness_root: Path) -> None:
    feature = make_feature(status="done")
    feature["status_history"] = ["pending", "done"]
    add_reports(harness_root, feature)
    save_features(harness_root, [feature])

    assert_error(harness_root, "illegal status transition for feature CRM-TEST")


def test_status_history_must_match_current_status(harness_root: Path) -> None:
    feature = make_feature(status="pending")
    feature["status_history"] = ["pending", "in_progress"]
    save_features(harness_root, [feature])

    assert_error(harness_root, "not current status 'pending'")


@pytest.mark.parametrize("test_command", ["", "   ", "pytest -q\nruff check ."])
def test_blank_or_inexact_test_command_is_rejected(
    harness_root: Path, test_command: str
) -> None:
    harness = load_json(harness_root / "harness.json")
    harness["test_command"] = test_command
    write_json(harness_root / "harness.json", harness)

    assert_error(harness_root, "harness.json.test_command must be")


def test_primary_branch_must_be_master(harness_root: Path) -> None:
    harness = load_json(harness_root / "harness.json")
    harness["primary_branch"] = "main"
    write_json(harness_root / "harness.json", harness)

    assert_error(harness_root, "harness.json.primary_branch must be master")


def test_agent_policy_has_the_canonical_role_defaults(harness_root: Path) -> None:
    policy = load_json(harness_root / "harness.json")["agent_policy"]

    assert policy["role_defaults"] == {
        "orchestrator": {"model": "gpt-5.6-sol", "reasoning_effort": "high"},
        "implementer": {"model": "gpt-5.6-terra", "reasoning_effort": "high"},
        "validator": {"model": "gpt-5.6-sol", "reasoning_effort": "high"},
        "explorer": {"model": "gpt-5.6-luna", "reasoning_effort": "medium"},
    }


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda policy: policy.pop("supported_models"),
            "supported_models must be a non-empty object",
        ),
        (
            lambda policy: policy["role_defaults"].pop("explorer"),
            "role_defaults.explorer must be an object",
        ),
        (
            lambda policy: policy["role_defaults"]["implementer"].update(
                {"model": "unsupported"}
            ),
            "role_defaults.implementer.model is unsupported",
        ),
    ],
)
def test_invalid_agent_policy_is_rejected(
    harness_root: Path, mutate: Callable[[dict[str, Any]], None], message: str
) -> None:
    harness = load_json(harness_root / "harness.json")
    mutate(harness["agent_policy"])
    write_json(harness_root / "harness.json", harness)

    assert_error(harness_root, message)


def test_active_feature_requires_task_envelope_reference(harness_root: Path) -> None:
    save_features(harness_root, [make_feature(status="in_progress")])

    assert_error(harness_root, "task_envelope must be progress/tasks/CRM-TEST.json")


def test_missing_task_envelope_file_is_rejected(harness_root: Path) -> None:
    feature = make_feature(status="in_progress")
    feature["task_envelope"] = "progress/tasks/CRM-TEST.json"
    save_features(harness_root, [feature])

    assert_error(harness_root, "missing task envelope for active feature CRM-TEST")


def test_invalid_task_envelope_json_is_rejected(harness_root: Path) -> None:
    feature = make_feature(status="in_progress")
    feature["task_envelope"] = "progress/tasks/CRM-TEST.json"
    envelope = harness_root / feature["task_envelope"]
    envelope.parent.mkdir(parents=True, exist_ok=True)
    envelope.write_text("not json", encoding="utf-8")
    save_features(harness_root, [feature])

    assert_error(harness_root, "invalid task envelope for active feature CRM-TEST")


@pytest.mark.parametrize(
    ("field", "invalid_value", "message"),
    [
        ("schema_version", 2, "schema_version must be 1"),
        ("feature_id", "CRM-WRONG", "feature_id must be CRM-TEST"),
        ("requirement_ids", ["CRM-UNKNOWN-R01"], "unknown requirement"),
        ("acceptance_ids", ["CRM-UNKNOWN-AC01"], "unknown acceptance criterion"),
        ("dependencies", ["CRM-OTHER"], "must exactly match feature depends_on"),
        ("allowed_scope", [], ".allowed_scope must be a non-empty list"),
        ("out_of_scope", [], ".out_of_scope must be a non-empty list"),
        ("baseline_revision", "", ".baseline_revision must be a nonblank string"),
        ("implementation_report", "impl.md", ".implementation_report must be"),
        ("validation_report", "validation.md", ".validation_report must be"),
        ("implementer", "", ".implementer must be a nonblank string"),
        ("validator", "", ".validator must be a nonblank string"),
        ("verification_commands", [], ".verification_commands must be a non-empty list"),
        (
            "verification_commands",
            ["pytest -q\nruff check ."],
            ".verification_commands[0] must be an exact single-line string",
        ),
    ],
)
def test_invalid_task_envelope_fields_are_rejected(
    harness_root: Path, field: str, invalid_value: object, message: str
) -> None:
    feature = make_feature(status="in_progress")
    envelope = activate(harness_root, feature)
    envelope[field] = invalid_value
    write_json(harness_root / feature["task_envelope"], envelope)
    save_features(harness_root, [feature])

    assert_error(harness_root, message)


def test_task_envelope_rejects_overlapping_scope(harness_root: Path) -> None:
    feature = make_feature(status="in_progress")
    envelope = activate(harness_root, feature)
    envelope["out_of_scope"] = deepcopy(envelope["allowed_scope"])
    write_json(harness_root / feature["task_envelope"], envelope)
    save_features(harness_root, [feature])

    assert_error(harness_root, "scope overlap: crm/allowed.py")


def test_implementer_cannot_be_validator(harness_root: Path) -> None:
    feature = make_feature(status="in_progress")
    envelope = activate(harness_root, feature)
    envelope["validator"] = envelope["implementer"]
    write_json(harness_root / feature["task_envelope"], envelope)
    save_features(harness_root, [feature])

    assert_error(harness_root, "implementer and validator must be distinct agents")


@pytest.mark.parametrize("role", ["orchestrator", "implementer", "validator"])
def test_task_envelope_requires_each_active_role_assignment(
    harness_root: Path, role: str
) -> None:
    feature = make_feature(status="in_progress")
    envelope = activate(harness_root, feature)
    envelope["agent_assignments"].pop(role)
    write_json(harness_root / feature["task_envelope"], envelope)
    save_features(harness_root, [feature])

    assert_error(harness_root, f"agent_assignments is missing required role: {role}")


@pytest.mark.parametrize(
    ("role", "field", "invalid_value", "message"),
    [
        ("implementer", "model", "gpt-unknown", ".model is unsupported: gpt-unknown"),
        (
            "implementer",
            "reasoning_effort",
            "ultra",
            ".reasoning_effort is unsupported for gpt-5.6-terra: ultra",
        ),
        ("implementer", "source", "inherited", ".source must be one of"),
    ],
)
def test_task_envelope_rejects_unsupported_assignment_values(
    harness_root: Path, role: str, field: str, invalid_value: str, message: str
) -> None:
    feature = make_feature(status="in_progress")
    envelope = activate(harness_root, feature)
    envelope["agent_assignments"][role][field] = invalid_value
    write_json(harness_root / feature["task_envelope"], envelope)
    save_features(harness_root, [feature])

    assert_error(harness_root, message)


def test_role_default_assignment_must_match_the_persisted_default(
    harness_root: Path,
) -> None:
    feature = make_feature(status="in_progress")
    envelope = activate(harness_root, feature)
    envelope["agent_assignments"]["implementer"]["model"] = "gpt-5.6-sol"
    write_json(harness_root / feature["task_envelope"], envelope)
    save_features(harness_root, [feature])

    assert_error(
        harness_root,
        "agent_assignments.implementer must match the implementer role default",
    )


def test_override_requires_a_nonblank_reason(harness_root: Path) -> None:
    feature = make_feature(status="in_progress")
    envelope = activate(harness_root, feature)
    assignment = envelope["agent_assignments"]["implementer"]
    assignment.update({"model": "gpt-5.6-sol", "source": "override", "override_reason": " "})
    write_json(harness_root / feature["task_envelope"], envelope)
    save_features(harness_root, [feature])

    assert_error(harness_root, "override_reason must be nonblank for override")


def test_justified_override_is_valid(harness_root: Path) -> None:
    feature = make_feature(status="in_progress")
    envelope = activate(harness_root, feature)
    envelope["agent_assignments"]["implementer"].update(
        {
            "model": "gpt-5.6-sol",
            "source": "override",
            "override_reason": "Security-sensitive migration requires frontier review.",
        }
    )
    write_json(harness_root / feature["task_envelope"], envelope)
    save_features(harness_root, [feature])

    assert check(harness_root) == []


def test_agent_assignment_must_match_implementer_and_validator_fields(
    harness_root: Path,
) -> None:
    feature = make_feature(status="in_progress")
    envelope = activate(harness_root, feature)
    envelope["agent_assignments"]["implementer"]["agent_id"] = "other-agent"
    write_json(harness_root / feature["task_envelope"], envelope)
    save_features(harness_root, [feature])

    assert_error(harness_root, "implementer must match its agent assignment")


def test_implementer_and_validator_assignments_must_be_independent(
    harness_root: Path,
) -> None:
    feature = make_feature(status="in_progress")
    envelope = activate(harness_root, feature)
    envelope["validator"] = envelope["implementer"]
    envelope["agent_assignments"]["validator"]["agent_id"] = envelope["implementer"]
    write_json(harness_root / feature["task_envelope"], envelope)
    save_features(harness_root, [feature])

    assert_error(harness_root, "implementer and validator assignments must be distinct agents")


def test_review_requires_canonical_existing_implementation_report(
    harness_root: Path,
) -> None:
    feature = make_feature(status="review")
    activate(harness_root, feature)
    save_features(harness_root, [feature])

    assert_error(harness_root, "must set implementation_report to progress/impl_CRM-TEST.md")


def test_changes_requested_requires_validation_report(harness_root: Path) -> None:
    feature = make_feature(status="changes_requested")
    activate(harness_root, feature)
    feature["implementation_report"] = "progress/impl_CRM-TEST.md"
    (harness_root / feature["implementation_report"]).write_text(
        implementation_report(feature), encoding="utf-8"
    )
    save_features(harness_root, [feature])

    assert_error(harness_root, "must set validation_report to progress/validation_CRM-TEST.md")


@pytest.mark.parametrize("missing_report", ["implementation_report", "validation_report"])
def test_done_feature_requires_both_reports(
    harness_root: Path, missing_report: str
) -> None:
    feature = make_feature(status="done")
    add_reports(harness_root, feature)
    path = harness_root / feature[missing_report]
    path.unlink()
    save_features(harness_root, [feature])

    assert_error(harness_root, f"missing {missing_report} for feature CRM-TEST")


def test_done_feature_requires_exact_approved_verdict(harness_root: Path) -> None:
    feature = make_feature(status="done")
    add_reports(harness_root, feature, verdict="CHANGES_REQUESTED")
    save_features(harness_root, [feature])

    assert_error(harness_root, "must have verdict APPROVED")


@pytest.mark.parametrize("report_without_evidence", ["implementation", "validation"])
def test_done_feature_requires_acceptance_evidence_in_both_reports(
    harness_root: Path, report_without_evidence: str
) -> None:
    feature = make_feature(status="done")
    add_reports(
        harness_root,
        feature,
        implementation_evidence=report_without_evidence != "implementation",
        validation_evidence=report_without_evidence != "validation",
    )
    save_features(harness_root, [feature])

    assert_error(
        harness_root,
        f"{report_without_evidence} report for done feature CRM-TEST has no concrete evidence",
    )


def test_acceptance_id_mentioned_outside_evidence_table_is_not_evidence(
    harness_root: Path,
) -> None:
    feature = make_feature(status="done")
    add_reports(harness_root, feature, implementation_evidence=False)
    report_path = harness_root / feature["implementation_report"]
    report_path.write_text(
        report_path.read_text(encoding="utf-8") + "\nCRM-TEST-AC01 was discussed.\n",
        encoding="utf-8",
    )
    save_features(harness_root, [feature])

    assert_error(harness_root, "implementation report for done feature CRM-TEST")


def test_evidence_parser_scans_all_append_only_sections() -> None:
    report = """# Initial slice

## Acceptance evidence

| Acceptance ID | Evidence | Result |
| --- | --- | --- |
| `CRM-TEST-AC01` | TODO | Pending |

## Verification

Initial work was incomplete.

---

# Bounded revision

## Acceptance evidence

| Acceptance ID | Evidence | Result |
| --- | --- | --- |
| `CRM-TEST-AC01` | `test_revision` exercises the accepted behavior. | Pass |

## Verification

The revision passed.
"""

    assert acceptance_evidence_is_concrete(report, "CRM-TEST-AC01")


@pytest.mark.parametrize(
    "acceptance_id",
    ["CRM-001-AC01", "CRM-001-AC02", "CRM-001-AC03", "CRM-001-AC04"],
)
def test_actual_append_only_crm001_evidence_is_discoverable(
    acceptance_id: str,
) -> None:
    report = (CRM_ROOT / "progress" / "impl_CRM-001.md").read_text(encoding="utf-8")

    assert acceptance_evidence_is_concrete(report, acceptance_id)


def test_diagnostics_are_deterministic(harness_root: Path) -> None:
    first = make_feature("CRM-A", depends_on=["CRM-B"])
    second = make_feature("CRM-B", depends_on=["CRM-A"])
    save_features(harness_root, [first, second])

    assert check(harness_root) == check(harness_root)


def test_init_script_runs_checker_then_configured_verification() -> None:
    init_script = (CRM_ROOT / "init.sh").read_text(encoding="utf-8")
    checker_call = init_script.index("python3 scripts/harness_check.py")
    verification_call = init_script.index('sh -c "$TEST_COMMAND"')

    assert checker_call < verification_call
