# Validation report — CRM-008

## Verdict

`APPROVED`

## Independence and scope

- Validator: `crm008_activity_validator_sol`
- Persisted validator assignment: `gpt-5.6-sol`, high reasoning; implementer assignment was the distinct `crm008_activity_implementer_terra` / `gpt-5.6-terra`.
- Runtime note: this environment does not expose switchable model identities or a separate validator process. The independent validator pass was executed as a separate review phase with no implementation-file edits; the discrepancy is recorded rather than silently substituted.
- Implementer: `crm008_activity_implementer_terra`
- Baseline inspected: `fcbe3b4ea14e155084019f9248a909826397d188` plus the dirty worktree baseline recorded in the task envelope.
- Allowed validator write target: `progress/validation_CRM-008.md`

## Acceptance evidence

| Acceptance ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-008-AC01 | `quick_contact()` transaction, lead lock/scope check, interaction/task/stage/audit writes, and rollback-focused tests. | Pass | The quick-contact write set is atomic; invalid placeholder input leaves no activity rows. |
| CRM-008-AC02 | Governed `InteractionResult`, direction/channel compatibility, catalog outcome checks, and non-event rejection. | Pass | `Sin acción` is rejected and does not inflate interaction counts; response semantics are explicit. |
| CRM-008-AC03 | Task model constraints, model validation, completion/reschedule services, and timezone-aware overdue property. | Pass | Completion and rescheduling preserve required timestamps/reasons; open tasks have no completion timestamp. |
| CRM-008-AC04 | Timeline dataclass/projection, occurrence-versus-entry fields, stage/assignment inclusion, and scope rejection test. | Pass | Timeline ordering is stable and direct access is denied outside campaign scope. |
| CRM-008-AC05 | Quick-contact API/docs, safe defaults in service contract, and documented moderated usability checklist. | Pass | Browser timing remains a staging follow-up once CRM-009 supplies the seller UI; no UI claim is made for this domain-only feature. |

## Verification

Exact commands run:

```text
python -m json.tool crm/feature_list.json >/dev/null
python -m json.tool crm/progress/tasks/CRM-008.json >/dev/null
timeout 60s ./crm/init.sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/activity/test_activity_lifecycle.py
git diff --check
```

Relevant output:

```text
Success: no issues found in 60 source files
164 passed, 10 warnings in 3.93s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
5 passed in 1.16s
```

The ten warnings are the existing non-fatal WhiteNoise warning for the absent
default `staticfiles/` directory during test-client setup.

## Findings

- Scope: implementation is limited to activity records, participants, tasks,
  quick-contact atomicity, activity audit events, timeline projection, docs,
  admin read surface, and tests. UI navigation, scheduled notifications,
  inbox synchronization, and call recording were not introduced.
- Security: activity creation, task mutation, and timeline reads re-check
  enabled identity plus CRM-005 action/campaign/team scope; direct lead IDs do
  not bypass authorization.
- Architecture: CRM-007 remains the owner of stage and assignment history;
  activity coordinates through its service boundary and does not duplicate
  those records. Date-only occurrence precision is retained explicitly.
- Regression: full harness, migration drift, system checks, repository safety,
  vendored asset checks, and focused activity tests pass.
- Environment limitation: PostgreSQL-specific runtime constraint evidence was
  not available in this sandbox; the generic constraint tests pass and a
  dedicated PostgreSQL 18 acceptance run remains a staging follow-up. No
  shared or application database was touched.
- No unresolved changes requested.
