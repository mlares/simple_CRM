"""Focused regression checks for the canonical agent workflow contract."""

from pathlib import Path

CRM_ROOT = Path(__file__).parents[1]


def read(relative_path: str) -> str:
    return (CRM_ROOT / relative_path).read_text(encoding="utf-8")


def test_canonical_workflow_roles_and_changes_loop_are_documented() -> None:
    agents_contract = read("AGENTS.md")

    for role in ("orchestrator", "implementer", "validator", "explorer"):
        assert (CRM_ROOT / "agents" / "roles" / f"{role}.md").is_file()
    assert "orchestrator -> explorer (optional) -> implementer -> validator" in agents_contract
    assert "changes_requested -> in_progress" in agents_contract


def test_validator_write_boundary_is_explicit() -> None:
    validator_contract = read("agents/roles/validator.md")

    assert "must not be the\nfeature's implementer" in validator_contract
    assert "may write only `progress/validation_<feature>.md`" in validator_contract
    assert "never\nedits application, implementation, configuration, feature-state, or session" in validator_contract


def test_explorer_uses_only_canonical_orchestrator_vocabulary() -> None:
    explorer_contract = read("agents/roles/explorer.md")

    assert "leader" not in explorer_contract
    assert "path supplied by the orchestrator" in explorer_contract
    assert "reports inform the orchestrator" in explorer_contract


def test_blocked_implementer_reports_without_editing_session_state() -> None:
    implementer_contract = read("agents/roles/implementer.md")
    blocked_contract = implementer_contract.split("If blocked,", maxsplit=1)[1]

    assert "progress/impl_<feature>.md" in blocked_contract
    assert "hand that report to the orchestrator" in blocked_contract
    assert "Never\nedit the orchestrator-owned `progress/current.md`" in blocked_contract
    assert "blocked -> progress/impl_<feature>.md" in blocked_contract


def test_role_contracts_require_persisted_assignments_and_runtime_reporting() -> None:
    agents_contract = read("AGENTS.md")

    assert "`harness.json` is the persisted source" in agents_contract
    assert "actual model and reasoning effort used" in " ".join(agents_contract.split())
    for role in ("orchestrator", "implementer", "validator", "explorer"):
        role_contract = read(f"agents/roles/{role}.md")
        assert "persisted assignment" in role_contract
        assert "actual model and reasoning effort" in role_contract


def test_adapters_require_the_persisted_runtime_assignment() -> None:
    for relative_path in (
        "CLAUDE.md",
        "adapters/codex.md",
        "adapters/copilot.md",
        "adapters/generic.md",
    ):
        adapter = read(relative_path)
        assert "persisted assignment" in adapter
        assert "actual model and reasoning effort" in " ".join(adapter.split())
