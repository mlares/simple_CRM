"""Validate the provider-neutral harness metadata."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VALID_STATUSES = {
    "pending",
    "in_progress",
    "review",
    "changes_requested",
    "done",
    "blocked",
}
ACTIVE_STATUSES = {"in_progress", "review", "changes_requested"}
DEPENDENCY_GATED_STATUSES = ACTIVE_STATUSES | {"done"}
LEGAL_TRANSITIONS = {
    "pending": {"in_progress", "blocked"},
    "in_progress": {"review", "changes_requested", "blocked"},
    "review": {"done", "changes_requested"},
    "changes_requested": {"in_progress", "blocked"},
    "blocked": {"in_progress"},
    "done": set(),
}
REQUIRED_FILES = (
    "AGENTS.md",
    "harness.json",
    "feature_list.json",
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
REPORT_STATES = {
    "review": ("implementation_report",),
    "changes_requested": ("implementation_report", "validation_report"),
    "done": ("implementation_report", "validation_report"),
}
POSITIVE_EVIDENCE_RESULTS = {"approved", "pass", "passed", "satisfied"}
POLICY_ROLES = ("orchestrator", "implementer", "validator", "explorer")
REQUIRED_ASSIGNMENT_ROLES = POLICY_ROLES[:3]
ASSIGNMENT_SOURCES = {"role_default", "override"}


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object, rejecting arrays and scalar roots."""
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def _is_nonblank_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _relative_file(root: Path, value: object) -> Path | None:
    """Resolve a path only when its real target remains inside ``root``."""
    if not _is_nonblank_string(value):
        return None
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    try:
        resolved_root = root.resolve()
        resolved_path = (resolved_root / relative).resolve()
        resolved_path.relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved_path


def _string_list(
    value: object,
    *,
    field: str,
    errors: list[str],
    allow_empty: bool = False,
) -> list[str] | None:
    """Validate a deterministic list of unique, exact, nonblank strings."""
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "a list" if allow_empty else "a non-empty list"
        errors.append(f"{field} must be {qualifier}")
        return None

    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not _is_nonblank_string(item):
            errors.append(f"{field}[{index}] must be a nonblank string")
            continue
        if item != item.strip() or "\n" in item or "\r" in item:
            errors.append(f"{field}[{index}] must be an exact single-line string")
            continue
        if item in seen:
            errors.append(f"{field} contains duplicate value: {item}")
            continue
        seen.add(item)
        result.append(item)
    return result


def _canonical_report_path(feature_id: str, report_key: str) -> str:
    prefix = "impl" if report_key == "implementation_report" else "validation"
    return f"progress/{prefix}_{feature_id}.md"


def _acceptance_evidence_is_concrete(report_text: str, acceptance_id: str) -> bool:
    """Find a populated positive row in any appended evidence section."""
    section_marker = "## Acceptance evidence"
    for appended_section in report_text.split(section_marker)[1:]:
        section = appended_section.split("\n## ", maxsplit=1)[0]
        for line in section.splitlines():
            if "|" not in line:
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not cells or cells[0].strip("`") != acceptance_id:
                continue
            values = cells[1:]
            normalized = {value.strip("`").casefold() for value in values}
            has_positive_result = bool(normalized & POSITIVE_EVIDENCE_RESULTS)
            has_concrete_detail = any(
                value.strip("`").casefold()
                not in POSITIVE_EVIDENCE_RESULTS | {"", "-", "n/a", "none", "todo"}
                for value in values
            )
            if (
                len(values) >= 2
                and all(values)
                and has_positive_result
                and has_concrete_detail
            ):
                return True
    return False


def _validation_verdict(report_text: str) -> str | None:
    marker = "## Verdict"
    if marker not in report_text:
        return None
    section = report_text.split(marker, maxsplit=1)[1]
    section = section.split("\n## ", maxsplit=1)[0]
    for line in section.splitlines():
        verdict = line.strip().strip("`")
        if verdict:
            return verdict
    return None


def _validate_agent_policy(harness: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    """Validate and return the persisted policy used by active task envelopes."""
    policy = harness.get("agent_policy")
    if not isinstance(policy, dict):
        errors.append("harness.json.agent_policy must be an object")
        return {}

    models = policy.get("supported_models")
    if not isinstance(models, dict) or not models:
        errors.append("harness.json.agent_policy.supported_models must be a non-empty object")
        models = {}
    for model, model_metadata in models.items():
        if not _is_nonblank_string(model):
            errors.append("harness.json.agent_policy.supported_models keys must be nonblank")
            continue
        if not isinstance(model_metadata, dict):
            errors.append(
                "harness.json.agent_policy.supported_models."
                f"{model} must be an object"
            )
            continue
        _string_list(
            model_metadata.get("reasoning_efforts"),
            field=(
                "harness.json.agent_policy.supported_models."
                f"{model}.reasoning_efforts"
            ),
            errors=errors,
        )

    role_defaults = policy.get("role_defaults")
    if not isinstance(role_defaults, dict):
        errors.append("harness.json.agent_policy.role_defaults must be an object")
        return {}
    for role in POLICY_ROLES:
        default = role_defaults.get(role)
        prefix = f"harness.json.agent_policy.role_defaults.{role}"
        if not isinstance(default, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _validate_supported_assignment(
            default,
            prefix=prefix,
            models=models,
            errors=errors,
        )
    return policy


def _validate_supported_assignment(
    assignment: dict[str, Any],
    *,
    prefix: str,
    models: object,
    errors: list[str],
) -> None:
    """Ensure an assignment names a supported model and effort combination."""
    model = assignment.get("model")
    if not _is_nonblank_string(model):
        errors.append(f"{prefix}.model must be a nonblank string")
        return
    if not isinstance(models, dict) or model not in models:
        errors.append(f"{prefix}.model is unsupported: {model}")
        return
    model_metadata = models[model]
    supported_efforts = (
        model_metadata.get("reasoning_efforts") if isinstance(model_metadata, dict) else None
    )
    effort = assignment.get("reasoning_effort")
    if not _is_nonblank_string(effort):
        errors.append(f"{prefix}.reasoning_effort must be a nonblank string")
    elif not isinstance(supported_efforts, list) or effort not in supported_efforts:
        errors.append(f"{prefix}.reasoning_effort is unsupported for {model}: {effort}")


def _validate_harness(harness: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    if harness.get("schema_version") != 1:
        errors.append("harness.json.schema_version must be 1")
    if harness.get("primary_branch") != "master":
        errors.append("harness.json.primary_branch must be master")

    test_command = harness.get("test_command")
    if not _is_nonblank_string(test_command):
        errors.append("harness.json.test_command must be a nonblank deterministic command")
    elif test_command != test_command.strip() or "\n" in test_command or "\r" in test_command:
        errors.append("harness.json.test_command must be an exact single-line command")
    return _validate_agent_policy(harness, errors)


def _register_id(
    value: object,
    *,
    kind: str,
    owner: str,
    seen_ids: dict[str, tuple[str, str]],
    errors: list[str],
) -> str | None:
    if not _is_nonblank_string(value):
        errors.append(f"{kind} id for {owner} must be a nonblank string")
        return None
    identifier = value.strip()
    if identifier in seen_ids:
        first_kind, first_owner = seen_ids[identifier]
        errors.append(
            f"duplicate {kind} id: {identifier} "
            f"(first used as {first_kind} id for {first_owner})"
        )
    else:
        seen_ids[identifier] = (kind, owner)
    return identifier


def _validate_status_history(
    feature_id: str, status: object, history: object, errors: list[str]
) -> None:
    if history is None and status == "pending":
        return
    if not isinstance(history, list) or not history:
        errors.append(f"feature {feature_id} status_history must be a non-empty list")
        return

    if history[0] != "pending":
        errors.append(f"feature {feature_id} status_history must start with pending")
    for index, history_status in enumerate(history):
        if history_status not in VALID_STATUSES:
            errors.append(
                f"feature {feature_id} status_history[{index}] has invalid status: "
                f"{history_status}"
            )
    for previous, current in zip(history, history[1:]):  # noqa: RUF007 - Python 3.9 CLI
        if (
            previous in VALID_STATUSES
            and current in VALID_STATUSES
            and current not in LEGAL_TRANSITIONS[previous]
        ):
            errors.append(
                f"illegal status transition for feature {feature_id}: "
                f"{previous} -> {current}"
            )
    if history[-1] != status:
        errors.append(
            f"feature {feature_id} status_history ends with {history[-1]!r}, "
            f"not current status {status!r}"
        )


def _validate_task_envelope(
    root: Path,
    agent_policy: dict[str, Any],
    feature: dict[str, Any],
    feature_id: str,
    requirement_ids: set[str],
    acceptance_ids: set[str],
    dependencies: list[str],
    errors: list[str],
) -> None:
    canonical_path = f"progress/tasks/{feature_id}.json"
    envelope_value = feature.get("task_envelope")
    if envelope_value != canonical_path:
        errors.append(
            f"active feature {feature_id} task_envelope must be {canonical_path}"
        )
        return
    envelope_path = _relative_file(root, envelope_value)
    if envelope_path is None or not envelope_path.is_file():
        errors.append(f"missing task envelope for active feature {feature_id}: {canonical_path}")
        return
    try:
        envelope = load_json(envelope_path)
    except Exception as exc:  # noqa: BLE001 - return a useful metadata diagnostic
        errors.append(f"invalid task envelope for active feature {feature_id}: {exc}")
        return

    prefix = f"task envelope for active feature {feature_id}"
    if envelope.get("schema_version") != 1:
        errors.append(f"{prefix} schema_version must be 1")
    if envelope.get("feature_id") != feature_id:
        errors.append(f"{prefix} feature_id must be {feature_id}")

    envelope_requirements = _string_list(
        envelope.get("requirement_ids"), field=f"{prefix}.requirement_ids", errors=errors
    )
    if envelope_requirements is not None:
        for requirement_id in envelope_requirements:
            if requirement_id not in requirement_ids:
                errors.append(f"{prefix} references unknown requirement: {requirement_id}")

    envelope_acceptance = _string_list(
        envelope.get("acceptance_ids"), field=f"{prefix}.acceptance_ids", errors=errors
    )
    if envelope_acceptance is not None:
        for acceptance_id in envelope_acceptance:
            if acceptance_id not in acceptance_ids:
                errors.append(f"{prefix} references unknown acceptance criterion: {acceptance_id}")

    envelope_dependencies = _string_list(
        envelope.get("dependencies"),
        field=f"{prefix}.dependencies",
        errors=errors,
        allow_empty=True,
    )
    if envelope_dependencies is not None and envelope_dependencies != dependencies:
        errors.append(f"{prefix}.dependencies must exactly match feature depends_on")

    allowed_scope = _string_list(
        envelope.get("allowed_scope"), field=f"{prefix}.allowed_scope", errors=errors
    )
    out_of_scope = _string_list(
        envelope.get("out_of_scope"), field=f"{prefix}.out_of_scope", errors=errors
    )
    if allowed_scope is not None and out_of_scope is not None:
        overlap = sorted(set(allowed_scope) & set(out_of_scope))
        if overlap:
            errors.append(f"{prefix} scope overlap: {', '.join(overlap)}")

    if not _is_nonblank_string(envelope.get("baseline_revision")):
        errors.append(f"{prefix}.baseline_revision must be a nonblank string")

    for report_key in ("implementation_report", "validation_report"):
        expected = _canonical_report_path(feature_id, report_key)
        if envelope.get(report_key) != expected:
            errors.append(f"{prefix}.{report_key} must be {expected}")

    implementer = envelope.get("implementer")
    validator = envelope.get("validator")
    if not _is_nonblank_string(implementer):
        errors.append(f"{prefix}.implementer must be a nonblank string")
    if not _is_nonblank_string(validator):
        errors.append(f"{prefix}.validator must be a nonblank string")
    if _is_nonblank_string(implementer) and implementer == validator:
        errors.append(f"{prefix} implementer and validator must be distinct agents")

    _validate_agent_assignments(
        envelope,
        prefix=prefix,
        agent_policy=agent_policy,
        errors=errors,
    )

    _string_list(
        envelope.get("verification_commands"),
        field=f"{prefix}.verification_commands",
        errors=errors,
    )


def _validate_agent_assignments(
    envelope: dict[str, Any],
    *,
    prefix: str,
    agent_policy: dict[str, Any],
    errors: list[str],
) -> None:
    """Check explicit runtime assignments against the persisted role policy."""
    assignments = envelope.get("agent_assignments")
    if not isinstance(assignments, dict):
        errors.append(f"{prefix}.agent_assignments must be an object")
        return

    role_defaults = agent_policy.get("role_defaults")
    models = agent_policy.get("supported_models")
    for role in REQUIRED_ASSIGNMENT_ROLES:
        if role not in assignments:
            errors.append(f"{prefix}.agent_assignments is missing required role: {role}")

    for role, assignment in assignments.items():
        assignment_prefix = f"{prefix}.agent_assignments.{role}"
        if role not in POLICY_ROLES:
            errors.append(f"{assignment_prefix} has unsupported role")
            continue
        if not isinstance(assignment, dict):
            errors.append(f"{assignment_prefix} must be an object")
            continue
        if not _is_nonblank_string(assignment.get("agent_id")):
            errors.append(f"{assignment_prefix}.agent_id must be a nonblank string")
        _validate_supported_assignment(
            assignment,
            prefix=assignment_prefix,
            models=models,
            errors=errors,
        )

        source = assignment.get("source")
        if source not in ASSIGNMENT_SOURCES:
            errors.append(
                f"{assignment_prefix}.source must be one of: "
                "role_default, override"
            )
            continue
        if source == "override":
            if not _is_nonblank_string(assignment.get("override_reason")):
                errors.append(
                    f"{assignment_prefix}.override_reason must be nonblank for override"
                )
            continue

        default = role_defaults.get(role) if isinstance(role_defaults, dict) else None
        if not isinstance(default, dict) or (
            assignment.get("model") != default.get("model")
            or assignment.get("reasoning_effort") != default.get("reasoning_effort")
        ):
            errors.append(f"{assignment_prefix} must match the {role} role default")

    for role in ("implementer", "validator"):
        assignment = assignments.get(role)
        if isinstance(assignment, dict) and _is_nonblank_string(envelope.get(role)):
            if assignment.get("agent_id") != envelope[role]:
                errors.append(f"{prefix}.{role} must match its agent assignment")

    implementer_assignment = assignments.get("implementer")
    validator_assignment = assignments.get("validator")
    if isinstance(implementer_assignment, dict) and isinstance(validator_assignment, dict):
        if (
            _is_nonblank_string(implementer_assignment.get("agent_id"))
            and implementer_assignment.get("agent_id") == validator_assignment.get("agent_id")
        ):
            errors.append(f"{prefix} implementer and validator assignments must be distinct agents")


def _validate_report_paths(
    root: Path,
    feature: dict[str, Any],
    feature_id: str,
    status: str,
    acceptance_ids: list[str],
    errors: list[str],
) -> None:
    report_texts: dict[str, str] = {}
    for report_key in REPORT_STATES.get(status, ()):
        expected = _canonical_report_path(feature_id, report_key)
        report_value = feature.get(report_key)
        if report_value != expected:
            errors.append(
                f"feature {feature_id} in {status} must set {report_key} to {expected}"
            )
            continue
        report_path = _relative_file(root, report_value)
        if report_path is None or not report_path.is_file():
            errors.append(f"missing {report_key} for feature {feature_id}: {expected}")
            continue
        report_texts[report_key] = report_path.read_text(encoding="utf-8")

    if status != "done":
        return
    validation_text = report_texts.get("validation_report")
    if validation_text is not None and _validation_verdict(validation_text) != "APPROVED":
        errors.append(f"validation report for done feature {feature_id} must have verdict APPROVED")

    for report_key in ("implementation_report", "validation_report"):
        report_text = report_texts.get(report_key)
        if report_text is None:
            continue
        report_label = {
            "implementation_report": "implementation",
            "validation_report": "validation",
        }[report_key]
        for acceptance_id in acceptance_ids:
            if not _acceptance_evidence_is_concrete(report_text, acceptance_id):
                errors.append(
                    f"{report_label} report for done feature {feature_id} has no "
                    f"concrete evidence for {acceptance_id}"
                )


def _dependency_cycles(
    feature_order: list[str], dependencies: dict[str, list[str]]
) -> list[list[str]]:
    cycles: list[list[str]] = []
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(feature_id: str) -> None:
        state[feature_id] = 1
        stack.append(feature_id)
        for dependency in dependencies.get(feature_id, []):
            if dependency not in dependencies:
                continue
            if state.get(dependency, 0) == 0:
                visit(dependency)
            elif state.get(dependency) == 1:
                start = stack.index(dependency)
                cycles.append([*stack[start:], dependency])
        stack.pop()
        state[feature_id] = 2

    for feature_id in feature_order:
        if state.get(feature_id, 0) == 0:
            visit(feature_id)
    return cycles


def check(root: Path | None = None) -> list[str]:
    """Return deterministic metadata diagnostics for ``root`` or this harness."""
    checked_root = ROOT if root is None else Path(root)
    errors: list[str] = []
    for relative_path in REQUIRED_FILES:
        if not (checked_root / relative_path).is_file():
            errors.append(f"missing required file: {relative_path}")

    try:
        harness = load_json(checked_root / "harness.json")
    except Exception as exc:  # noqa: BLE001 - make the CLI diagnostic useful
        errors.append(f"invalid harness.json: {exc}")
        harness = {}
    agent_policy = _validate_harness(harness, errors)

    try:
        feature_data = load_json(checked_root / "feature_list.json")
    except Exception as exc:  # noqa: BLE001 - make the CLI diagnostic useful
        errors.append(f"invalid feature_list.json: {exc}")
        feature_data = {}

    features = feature_data.get("features", [])
    if not isinstance(features, list):
        errors.append("feature_list.json.features must be a list")
        features = []

    seen_ids: dict[str, tuple[str, str]] = {}
    feature_by_id: dict[str, dict[str, Any]] = {}
    feature_order: list[str] = []
    requirements_by_feature: dict[str, set[str]] = {}
    acceptance_by_feature: dict[str, list[str]] = {}
    dependencies_by_feature: dict[str, list[str]] = {}
    active_features: list[str] = []

    for index, feature in enumerate(features):
        if not isinstance(feature, dict):
            errors.append(f"feature_list.json.features[{index}] must be an object")
            continue
        feature_id = _register_id(
            feature.get("id"),
            kind="feature",
            owner=f"features[{index}]",
            seen_ids=seen_ids,
            errors=errors,
        )
        if feature_id is None:
            continue
        if feature_id not in feature_by_id:
            feature_by_id[feature_id] = feature
            feature_order.append(feature_id)

        status = feature.get("status")
        if status not in VALID_STATUSES:
            errors.append(f"invalid status for feature {feature_id}: {status}")
        elif status in ACTIVE_STATUSES:
            active_features.append(feature_id)
        _validate_status_history(feature_id, status, feature.get("status_history"), errors)

        requirement_ids: set[str] = set()
        requirements = feature.get("requirements")
        if not isinstance(requirements, list):
            errors.append(f"feature {feature_id}.requirements must be a list")
            requirements = []
        for requirement_index, requirement in enumerate(requirements):
            if not isinstance(requirement, dict):
                errors.append(
                    f"feature {feature_id}.requirements[{requirement_index}] must be an object"
                )
                continue
            requirement_id = _register_id(
                requirement.get("id"),
                kind="requirement",
                owner=feature_id,
                seen_ids=seen_ids,
                errors=errors,
            )
            if requirement_id is not None:
                requirement_ids.add(requirement_id)
        requirements_by_feature[feature_id] = requirement_ids

        acceptance_ids: list[str] = []
        acceptance = feature.get("acceptance")
        if not isinstance(acceptance, list) or not acceptance:
            errors.append(f"feature {feature_id}.acceptance must be a non-empty list")
            acceptance = []
        for acceptance_index, criterion in enumerate(acceptance):
            if not isinstance(criterion, dict):
                errors.append(
                    f"feature {feature_id}.acceptance[{acceptance_index}] must be an object"
                )
                continue
            acceptance_id = _register_id(
                criterion.get("id"),
                kind="acceptance",
                owner=feature_id,
                seen_ids=seen_ids,
                errors=errors,
            )
            if acceptance_id is not None:
                acceptance_ids.append(acceptance_id)
        acceptance_by_feature[feature_id] = acceptance_ids

        dependencies = _string_list(
            feature.get("depends_on"),
            field=f"feature {feature_id}.depends_on",
            errors=errors,
            allow_empty=True,
        )
        dependencies_by_feature[feature_id] = dependencies or []
        if dependencies is not None and feature_id in dependencies:
            errors.append(f"feature {feature_id} cannot depend on itself")

    if len(active_features) > 1:
        errors.append(f"more than one active feature: {', '.join(active_features)}")

    for feature_id in feature_order:
        feature = feature_by_id[feature_id]
        status = feature.get("status")
        dependencies = dependencies_by_feature[feature_id]
        for dependency in dependencies:
            if dependency not in feature_by_id:
                errors.append(f"feature {feature_id} has missing dependency: {dependency}")
            elif status in DEPENDENCY_GATED_STATUSES:
                dependency_status = feature_by_id[dependency].get("status")
                if dependency_status != "done":
                    errors.append(
                        f"feature {feature_id} in {status} requires dependency {dependency} "
                        f"to be done, found {dependency_status}"
                    )

        if status in ACTIVE_STATUSES:
            _validate_task_envelope(
                checked_root,
                agent_policy,
                feature,
                feature_id,
                requirements_by_feature[feature_id],
                set(acceptance_by_feature[feature_id]),
                dependencies,
                errors,
            )
        if status in REPORT_STATES:
            _validate_report_paths(
                checked_root,
                feature,
                feature_id,
                status,
                acceptance_by_feature[feature_id],
                errors,
            )

    for cycle in _dependency_cycles(feature_order, dependencies_by_feature):
        errors.append(f"dependency cycle: {' -> '.join(cycle)}")

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
