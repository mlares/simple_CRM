# Harness checkpoints

These are objective checks for a healthy generated project.

## C1 — Contract

- [ ] `AGENTS.md`, `feature_list.json`, `progress/current.md`, and
      `harness.json` exist.
- [ ] The role specifications exist under `agents/roles/`.
- [ ] `./init.sh` exits successfully.

## C2 — State

- [ ] There is at most one `in_progress` feature.
- [ ] Feature ids are unique.
- [ ] A feature is not marked `done` without acceptance criteria and a validation
      report.

## C3 — Scope and quality

- [ ] The implementation follows `docs/architecture.md`.
- [ ] The implementation follows `docs/conventions.md`.
- [ ] No unrelated feature is mixed into the current session.

## C4 — Evidence

- [ ] Every completed feature has executable verification or an explicitly
      documented non-executable verification strategy.
- [ ] The latest implementation and validation reports are present in
      `progress/`.

## C5 — Handoff

- [ ] `progress/current.md` describes the active session or is reset.
- [ ] `progress/history.md` contains the latest completed session summary.
- [ ] No temporary or debug artifacts are left behind.
